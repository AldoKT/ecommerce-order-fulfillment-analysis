"""Run the Day 3 SQLite business analysis and regenerate its Markdown report."""

from __future__ import annotations

import csv
import math
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = Path("data/processed")
VIEWS_PATH = Path("sql/01_analysis_views.sql")
QUERIES_PATH = Path("sql/02_business_queries.sql")
REPORT_PATH = Path("docs/sql-analysis.md")
ABS_TOL = 1e-6
RATIO_EXPECTED = 0.16568
RATIO_ABS_TOL = 1e-5

TABLE_SCHEMAS: dict[str, list[tuple[str, str]]] = {
    "fact_orders": [
        ("order_id", "TEXT"), ("customer_id", "TEXT"), ("customer_unique_id", "TEXT"),
        ("customer_city", "TEXT"), ("customer_state", "TEXT"), ("order_status", "TEXT"),
        ("purchase_timestamp", "TEXT"), ("purchase_date", "TEXT"), ("purchase_year_month", "TEXT"),
        ("approval_timestamp", "TEXT"), ("carrier_handoff_timestamp", "TEXT"), ("delivery_timestamp", "TEXT"),
        ("estimated_delivery_date", "TEXT"), ("approval_hours", "REAL"), ("preparation_days", "REAL"),
        ("transportation_days", "REAL"), ("total_lead_time_days", "REAL"),
        ("delivery_variance_days", "INTEGER"), ("delay_days", "INTEGER"),
        ("delivery_classification", "TEXT"), ("valid_approval_sequence", "INTEGER"),
        ("valid_preparation_sequence", "INTEGER"), ("valid_transportation_sequence", "INTEGER"),
        ("valid_total_lead_time_sequence", "INTEGER"), ("item_count", "INTEGER"),
        ("seller_count", "INTEGER"), ("category_count", "INTEGER"), ("merchandise_value", "REAL"),
        ("freight_value", "REAL"), ("payment_record_count", "INTEGER"), ("payment_value", "REAL"),
        ("review_count", "INTEGER"), ("average_review_score", "REAL"), ("has_item_data", "INTEGER"),
        ("has_review_data", "INTEGER"),
    ],
    "fact_order_items": [
        ("order_id", "TEXT"), ("order_item_id", "INTEGER"), ("product_id", "TEXT"),
        ("seller_id", "TEXT"), ("product_category_original", "TEXT"),
        ("product_category_english", "TEXT"), ("shipping_limit_timestamp", "TEXT"),
        ("price", "REAL"), ("freight_value", "REAL"), ("customer_state", "TEXT"),
        ("seller_state", "TEXT"),
    ],
}

EXPECTED_QUERY_COLUMNS = {
    "overall_order_fulfillment_summary": ["total_orders", "delivered_orders", "classified_orders", "on_time_orders", "late_orders", "on_time_rate", "average_total_lead_time_days", "average_delay_days_late_orders"],
    "monthly_fulfillment_trend": ["year_month", "is_boundary_month", "total_orders", "classified_orders", "late_orders", "on_time_rate", "average_total_lead_time_days", "average_delay_days_late_orders"],
    "customer_state_fulfillment_performance": ["customer_state", "total_orders", "classified_orders", "late_orders", "on_time_rate", "average_total_lead_time_days", "average_delay_days_late_orders", "total_payment_value"],
    "order_status_distribution": ["order_status", "order_count", "percentage_of_all_orders"],
    "product_category_commercial_performance": ["product_category", "total_items", "merchandise_value", "freight_value", "freight_to_merchandise_ratio"],
    "seller_state_commercial_performance": ["seller_state", "total_items", "merchandise_value", "freight_value", "freight_to_merchandise_ratio"],
    "customer_repeat_order_summary": ["distinct_customers", "one_time_customers", "repeat_customers", "repeat_customer_rate", "maximum_orders_by_one_customer"],
    "data_quality_and_lifecycle_summary": ["missing_approval_timestamps", "missing_carrier_handoff_timestamps", "missing_delivery_timestamps", "orders_missing_any_lifecycle_timestamp", "invalid_preparation_sequences", "invalid_transportation_sequences", "not_classified_orders"],
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def convert_value(value: str, sqlite_type: str) -> Any:
    if value == "":
        return None
    if sqlite_type == "TEXT":
        return value
    if sqlite_type == "INTEGER":
        if value in {"True", "true"}:
            return 1
        if value in {"False", "false"}:
            return 0
        return int(float(value))
    if sqlite_type == "REAL":
        return float(value)
    raise ValueError(f"Unsupported SQLite type: {sqlite_type}")


def read_processed_table(table: str) -> list[dict[str, Any]]:
    path = PROCESSED / f"{table}.csv"
    require(path.is_file(), f"Required processed file is missing: {path}")
    schema = TABLE_SCHEMAS[table]
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == [name for name, _ in schema], f"Unexpected schema in {path}")
        return [{name: convert_value(row[name], sqlite_type) for name, sqlite_type in schema} for row in reader]


def load_database() -> tuple[sqlite3.Connection, dict[str, list[dict[str, Any]]]]:
    """Load native-grain processed facts into a transient in-memory SQLite database."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.row_factory = sqlite3.Row
        source_rows: dict[str, list[dict[str, Any]]] = {}
        for table, schema in TABLE_SCHEMAS.items():
            rows = read_processed_table(table)
            source_rows[table] = rows
            column_sql = ", ".join(f'"{name}" {sqlite_type}' for name, sqlite_type in schema)
            connection.execute(f'CREATE TABLE "{table}" ({column_sql})')
            placeholders = ", ".join("?" for _ in schema)
            insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'
            connection.executemany(insert_sql, [[row[name] for name, _ in schema] for row in rows])
        connection.executescript(VIEWS_PATH.read_text(encoding="utf-8"))
        return connection, source_rows
    except Exception:
        connection.close()
        raise


def parse_queries(text: str, expected_names: set[str] | None = None) -> dict[str, str]:
    """Parse labelled single-statement SQL blocks without silently accepting duplicates."""
    queries: dict[str, str] = {}
    pattern = re.compile(r"(?ms)^-- QUERY: (?P<name>[a-z0-9_]+)\n(?P<body>.*?)(?=^-- QUERY:|\Z)")
    for match in pattern.finditer(text):
        name = match.group("name")
        require(name not in queries, f"Duplicate query label: {name}")
        sql = re.sub(r"(?m)^--[^\n]*\n", "", match.group("body")).strip()
        require(sql.endswith(";"), f"Query {name} must end with a semicolon")
        statement = sql[:-1].strip()
        require(";" not in statement, f"Query {name} must contain exactly one SQL statement")
        queries[name] = statement
    if expected_names is not None:
        require(set(queries) == expected_names, "Business query labels do not match the required query set")
    return queries


def load_queries() -> dict[str, str]:
    return parse_queries(QUERIES_PATH.read_text(encoding="utf-8"), set(EXPECTED_QUERY_COLUMNS))


def execute_queries(connection: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {}
    for name, sql in load_queries().items():
        cursor = connection.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        require(list(rows[0]) == EXPECTED_QUERY_COLUMNS[name] if rows else False, f"Unexpected or empty output schema for {name}")
        results[name] = rows
    return results


def source_sum(rows: list[dict[str, Any]], field: str) -> float:
    return float(sum(row[field] or 0.0 for row in rows))


def comparative_months(monthly_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return complete-month rows suitable for rate comparison."""
    return [row for row in monthly_rows if row["is_boundary_month"] == 0 and row["classified_orders"] >= 100]


def validate_results(connection: sqlite3.Connection, results: dict[str, list[dict[str, Any]]], source_rows: dict[str, list[dict[str, Any]]]) -> None:
    orders = source_rows["fact_orders"]
    items = source_rows["fact_order_items"]
    require(len({row["order_id"] for row in orders}) == len(orders), "fact_orders order_id is not unique")
    require(len({(row["order_id"], row["order_item_id"]) for row in items}) == len(items), "fact_order_items composite key is not unique")
    headline = results["overall_order_fulfillment_summary"][0]
    require(headline["total_orders"] == len(orders), "SQL total orders does not reconcile to fact_orders")
    require(headline["delivered_orders"] == sum(row["order_status"] == "delivered" for row in orders), "SQL delivered orders does not reconcile")
    require(headline["classified_orders"] == sum(row["delivery_classification"] in {"On Time", "Late"} for row in orders), "SQL classified orders does not reconcile")
    require(headline["on_time_orders"] + headline["late_orders"] == headline["classified_orders"], "Classification denominator includes Not Classified orders")
    require(math.isclose(headline["on_time_rate"], headline["on_time_orders"] / headline["classified_orders"], rel_tol=0.0, abs_tol=ABS_TOL), "SQL on-time rate does not reconcile")

    for query_name, rate_column in (("monthly_fulfillment_trend", "on_time_rate"), ("customer_state_fulfillment_performance", "on_time_rate"), ("order_status_distribution", "percentage_of_all_orders"), ("product_category_commercial_performance", "freight_to_merchandise_ratio"), ("seller_state_commercial_performance", "freight_to_merchandise_ratio"), ("customer_repeat_order_summary", "repeat_customer_rate")):
        for row in results[query_name]:
            value = row[rate_column]
            require(value is None or 0.0 <= value <= 1.0, f"Out-of-range {rate_column} in {query_name}")

    monthly = results["monthly_fulfillment_trend"]
    require(sum(row["total_orders"] for row in monthly) == headline["total_orders"], "Monthly orders multiply or omit rows")
    require([row["year_month"] for row in monthly] == sorted(row["year_month"] for row in monthly), "Monthly rows are not chronological")
    boundary_months = [row for row in monthly if row["is_boundary_month"] == 1]
    require(boundary_months, "Monthly output has no boundary-month flags")
    require(all(row["classified_orders"] >= 100 for row in comparative_months(monthly)), "Comparative monthly output violates the minimum-volume rule")
    state_all_total = connection.execute("SELECT SUM(total_orders) FROM vw_customer_state_fulfillment").fetchone()[0]
    require(state_all_total == headline["total_orders"], "Customer-state rows multiply or omit orders")

    expected_merchandise = source_sum(items, "price")
    expected_freight = source_sum(items, "freight_value")
    for query_name in ("product_category_commercial_performance", "seller_state_commercial_performance"):
        rows = results[query_name]
        require(sum(row["total_items"] for row in rows) == len(items), f"{query_name} item count does not reconcile")
        require(math.isclose(sum(row["merchandise_value"] or 0.0 for row in rows), expected_merchandise, rel_tol=0.0, abs_tol=ABS_TOL), f"{query_name} merchandise total does not reconcile")
        require(math.isclose(sum(row["freight_value"] or 0.0 for row in rows), expected_freight, rel_tol=0.0, abs_tol=ABS_TOL), f"{query_name} freight total does not reconcile")
    ratio = expected_freight / expected_merchandise
    require(math.isclose(ratio, RATIO_EXPECTED, rel_tol=0.0, abs_tol=RATIO_ABS_TOL), "Item freight-to-merchandise ratio differs from expected approximately 0.16568")


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = ["| " + " | ".join(label for _, label in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in selected:
        rendered: list[str] = []
        for key, label in columns:
            value = row[key]
            if value is None:
                rendered.append("—")
            elif key in {"total_orders", "delivered_orders", "classified_orders", "on_time_orders", "late_orders", "total_items", "order_count", "distinct_customers", "one_time_customers", "repeat_customers", "maximum_orders_by_one_customer", "missing_approval_timestamps", "missing_carrier_handoff_timestamps", "missing_delivery_timestamps", "orders_missing_any_lifecycle_timestamp", "invalid_preparation_sequences", "invalid_transportation_sequences", "not_classified_orders"}:
                rendered.append(f"{int(value):,}")
            elif key in {"merchandise_value", "freight_value", "total_payment_value"}:
                rendered.append(f"R${value:,.2f}")
            elif key.endswith("_rate") or key.endswith("_ratio") or key == "percentage_of_all_orders":
                rendered.append(f"{value:.2%}")
            elif key.startswith("average_"):
                rendered.append(f"{value:.2f}")
            else:
                rendered.append(str(value))
        lines.append("| " + " | ".join(rendered) + " |")
    return "\n".join(lines)


def generate_report(results: dict[str, list[dict[str, Any]]], output_path: Path) -> None:
    headline = results["overall_order_fulfillment_summary"][0]
    monthly = results["monthly_fulfillment_trend"]
    boundary_months = [row["year_month"] for row in monthly if row["is_boundary_month"] == 1]
    monthly_low_rate = sorted(comparative_months(monthly), key=lambda row: (row["on_time_rate"], row["year_month"]))[:5]
    states = results["customer_state_fulfillment_performance"]
    status = results["order_status_distribution"]
    products = results["product_category_commercial_performance"]
    sellers = results["seller_state_commercial_performance"]
    repeat = results["customer_repeat_order_summary"]
    quality = results["data_quality_and_lifecycle_summary"]

    lines = [
        "# Day 3 SQL business analysis",
        "",
        "This report is generated deterministically by `python/04_sql_analysis.py`; it contains no execution timestamp.",
        "",
        "## Scope and analytical assumptions",
        "",
        "The analysis uses the processed order and order-item facts only. Delivery, payment, and review metrics remain at order grain. Product-category and seller-state commercial metrics use only item-grain price and freight values; merchandise value is revenue-like transaction value, not profit.",
        "",
        "## Source tables and grain",
        "",
        "| Source | Grain | Use |",
        "| --- | --- | --- |",
        "| `fact_orders.csv` | One row per order | fulfillment, status, payment, lifecycle, repeat-order summaries |",
        "| `fact_order_items.csv` | One row per `order_id` + `order_item_id` | product-category and seller-state commercial summaries |",
        "",
        "## Method",
        "",
        "The runner loads the two processed facts into an in-memory SQLite database using explicit practical column types, creates reusable views, executes all named queries, and reconciles results to the processed CSV source rows. No database file is created. All rate divisions use `NULLIF` to return null rather than raise or misstate a value when a denominator is zero.",
        "",
        "## Headline KPI results",
        "",
        markdown_table([headline], [("total_orders", "Total orders"), ("delivered_orders", "Delivered"), ("classified_orders", "Classified"), ("on_time_orders", "On time"), ("late_orders", "Late"), ("on_time_rate", "On-time rate",), ("average_total_lead_time_days", "Avg. lead time (days)"), ("average_delay_days_late_orders", "Avg. late delay (days)")]),
        "",
        "## Monthly fulfillment findings",
        "",
        f"Boundary months are **{', '.join(boundary_months)}**. They remain in the monthly SQL output for transparency but are flagged as partial boundary months and excluded from comparative rankings.",
        "",
        "Observed fact: the following are the five purchase months with the lowest on-time rate among non-boundary months having at least 100 classified orders.",
        "",
        markdown_table(monthly_low_rate, [("year_month", "Year month"), ("total_orders", "Orders"), ("classified_orders", "Classified"), ("late_orders", "Late"), ("on_time_rate", "On-time rate"), ("average_total_lead_time_days", "Avg. lead time (days)"), ("average_delay_days_late_orders", "Avg. late delay (days)")]),
        "",
        "## Customer-state analysis",
        "",
        "Observed fact: rate comparisons below apply the pre-defined minimum-volume rule of at least 100 classified orders.",
        "",
        markdown_table(states, [("customer_state", "Customer state"), ("total_orders", "Orders"), ("classified_orders", "Classified"), ("late_orders", "Late"), ("on_time_rate", "On-time rate"), ("average_total_lead_time_days", "Avg. lead time (days)"), ("average_delay_days_late_orders", "Avg. late delay (days)"), ("total_payment_value", "Payment value")], 10),
        "",
        "## Order-status analysis",
        "",
        markdown_table(status, [("order_status", "Order status"), ("order_count", "Orders"), ("percentage_of_all_orders", "Share of orders")]),
        "",
        "## Product-category analysis",
        "",
        "Observed fact: the table ranks categories by item-grain merchandise value. It does not attach delivery, payment, or review outcomes to categories.",
        "",
        markdown_table(products, [("product_category", "Product category"), ("total_items", "Items"), ("merchandise_value", "Merchandise value"), ("freight_value", "Freight value"), ("freight_to_merchandise_ratio", "Freight / merchandise")], 10),
        "",
        "## Seller-state analysis",
        "",
        "Observed fact: the table ranks seller states by item-grain merchandise value. It does not attach delivery, payment, or review outcomes to seller states.",
        "",
        markdown_table(sellers, [("seller_state", "Seller state"), ("total_items", "Items"), ("merchandise_value", "Merchandise value"), ("freight_value", "Freight value"), ("freight_to_merchandise_ratio", "Freight / merchandise")], 10),
        "",
        "## Repeat-customer summary",
        "",
        markdown_table(repeat, [("distinct_customers", "Distinct customers"), ("one_time_customers", "One-time customers"), ("repeat_customers", "Repeat customers"), ("repeat_customer_rate", "Repeat-customer rate"), ("maximum_orders_by_one_customer", "Maximum orders by one customer")]),
        "",
        "## Data-quality caveats",
        "",
        markdown_table(quality, [("missing_approval_timestamps", "Missing approval"), ("missing_carrier_handoff_timestamps", "Missing carrier handoff"), ("missing_delivery_timestamps", "Missing delivery"), ("orders_missing_any_lifecycle_timestamp", "Missing any lifecycle timestamp"), ("invalid_preparation_sequences", "Invalid preparation"), ("invalid_transportation_sequences", "Invalid transportation"), ("not_classified_orders", "Not classified")]),
        "",
        "Lifecycle averages use non-null valid durations created in Day 1. Not Classified orders are excluded from on-time rate denominators; diagnostic counts are retained rather than corrected or removed.",
        "",
        "## Business interpretation",
        "",
        f"Observed fact: {headline['late_orders']:,} of {headline['classified_orders']:,} classified orders are late, while {headline['total_orders'] - headline['classified_orders']:,} orders are Not Classified.",
        "",
        "Interpretation: delivery performance varies by time period and customer state in this observational dataset. These associations do not establish why delays occurred.",
        "",
        "Recommendation: use the lowest on-time-rate months and qualifying customer states as a prioritization list for operational investigation, then validate any proposed causes with process-level evidence before changing policy.",
        "",
        "## Limitations",
        "",
        "- The dataset is observational and anonymized; it cannot establish causation or operational accountability.",
        "- `customer_unique_id` is used only in aggregated repeat-order calculations; no individual customer identifiers are reported.",
        "- Payment, delivery, and review measures must not be analyzed by product category or seller state without a separately designed valid allocation method.",
        "- Merchandise value is not profit and does not account for costs, refunds, or margin.",
        "- Missing lifecycle timestamps and retained invalid sequences limit delivery-duration coverage.",
        "",
        "## Reproducibility command",
        "",
        "```powershell",
        "& .\\.venv\\Scripts\\python.exe python\\04_sql_analysis.py",
        "```",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError(f"Run this script from the repository root: {ROOT}")
    connection, source_rows = load_database()
    try:
        results = execute_queries(connection)
        validate_results(connection, results, source_rows)
        generate_report(results, REPORT_PATH)
    finally:
        connection.close()
    print("SQL analysis: PASS")
    print("Queries executed: " + ", ".join(load_queries()))
    print(f"Generated report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, sqlite3.Error, ValueError, RuntimeError) as error:
        print(f"SQL analysis: FAIL - {error}", file=sys.stderr)
        raise SystemExit(1)
