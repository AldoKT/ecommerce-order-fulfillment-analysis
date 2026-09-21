"""Deterministic read-only validation for the Day 2 Power BI model pack."""

import math
from pathlib import Path

import pandas as pd


PROCESSED = Path("data/processed")
ABS_TOL = 1e-6
RATIO_EXPECTED = 0.16568
RATIO_ABS_TOL = 1e-5


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_tables() -> dict[str, pd.DataFrame]:
    names = {
        "fact_orders": "fact_orders.csv",
        "fact_order_items": "fact_order_items.csv",
        "dim_customers": "dim_customers.csv",
        "dim_products": "dim_products.csv",
        "dim_sellers": "dim_sellers.csv",
    }
    return {name: pd.read_csv(PROCESSED / filename) for name, filename in names.items()}


def normalize_nullable_boolean(series: pd.Series) -> pd.Series:
    values = series.map({True: True, False: False, "True": True, "False": False})
    values = values.where(series.notna())
    return values.astype("boolean")


def main() -> None:
    tables = load_tables()
    orders = tables["fact_orders"]
    items = tables["fact_order_items"]
    customers = tables["dim_customers"]
    products = tables["dim_products"]
    sellers = tables["dim_sellers"]

    expected_rows = {
        "fact_orders": 99_441,
        "fact_order_items": 112_650,
        "dim_customers": 99_441,
        "dim_products": 32_951,
        "dim_sellers": 3_095,
    }
    for name, expected in expected_rows.items():
        require(len(tables[name]) == expected, f"{name} row count changed")

    require(orders["order_id"].notna().all() and orders["order_id"].is_unique, "fact_orders.order_id key failure")
    require(
        not items[["order_id", "order_item_id"]].isna().any(axis=None)
        and not items.duplicated(["order_id", "order_item_id"]).any(),
        "fact_order_items composite key failure",
    )
    for frame, key in ((customers, "customer_id"), (products, "product_id"), (sellers, "seller_id")):
        require(frame[key].notna().all() and frame[key].is_unique, f"{key} dimension key failure")

    relationship_checks = {
        "customer_id one-to-one": (
            orders["customer_id"].notna().all()
            and orders["customer_id"].is_unique
            and customers["customer_id"].notna().all()
            and customers["customer_id"].is_unique
            and set(orders["customer_id"]) == set(customers["customer_id"])
        ),
        "order_id one-to-many": set(items["order_id"]).issubset(set(orders["order_id"])),
        "product_id one-to-many": set(items["product_id"]).issubset(set(products["product_id"])),
        "seller_id one-to-many": set(items["seller_id"]).issubset(set(sellers["seller_id"])),
    }
    for name, passed in relationship_checks.items():
        require(passed, f"relationship key failure: {name}")

    purchase_dates = pd.to_datetime(orders["purchase_date"], errors="coerce")
    purchase_timestamps = pd.to_datetime(orders["purchase_timestamp"], errors="coerce")
    date_min = purchase_dates.min()
    date_max = purchase_dates.max()
    require(purchase_dates.notna().all(), "purchase_date contains nulls")
    require(purchase_timestamps.notna().all(), "purchase_timestamp contains nulls")
    require(
        purchase_dates.dt.normalize().equals(purchase_timestamps.dt.normalize()),
        "purchase_date does not match purchase_timestamp calendar date",
    )
    require(date_min <= date_max, "invalid DimDate range")
    date_table = pd.date_range(date_min, date_max, freq="D")
    require(len(date_table) == (date_max - date_min).days + 1, "DimDate range is not contiguous")
    require(purchase_dates.isin(date_table).all(), "DimDate does not cover all purchase dates")
    month_number = date_table.month
    year_month_sort = date_table.year * 100 + date_table.month
    require(((month_number >= 1) & (month_number <= 12)).all(), "DimDate Month Number assumption failure")
    require((year_month_sort == (date_table.year * 100 + month_number)).all(), "DimDate Year Month Sort assumption failure")
    relationship_checks["DimDate Date one-to-many"] = date_table.is_unique and purchase_dates.isin(date_table).all()
    print_date_range = f"{date_min.date()} to {date_max.date()}"

    allowed_classifications = {"On Time", "Late", "Not Classified"}
    require(set(orders["delivery_classification"].dropna()).issubset(allowed_classifications), "classification value failure")
    classification_counts = orders["delivery_classification"].value_counts().reindex(sorted(allowed_classifications), fill_value=0)

    boolean_columns = [
        "valid_approval_sequence",
        "valid_preparation_sequence",
        "valid_transportation_sequence",
        "valid_total_lead_time_sequence",
    ]
    boolean_counts: dict[str, dict[str, int]] = {}
    for column in boolean_columns:
        normalized = normalize_nullable_boolean(orders[column])
        require(normalized.dropna().isin([True, False]).all(), f"invalid nullable Boolean values: {column}")
        boolean_counts[column] = {
            "true": int((normalized == True).sum()),
            "false": int((normalized == False).sum()),
            "null": int(normalized.isna().sum()),
        }

    total_lead_missing = orders["purchase_timestamp"].isna() | orders["delivery_timestamp"].isna()
    total_lead_flag = normalize_nullable_boolean(orders["valid_total_lead_time_sequence"])
    require(total_lead_flag.isna().equals(total_lead_missing), "total lead-time null behavior failure")
    purchase = pd.to_datetime(orders["purchase_timestamp"])
    delivery = pd.to_datetime(orders["delivery_timestamp"])
    invalid_total = purchase.notna() & delivery.notna() & delivery.lt(purchase)
    require(int((total_lead_flag == False).sum()) == int(invalid_total.sum()), "total lead-time invalid count failure")

    classified = orders["delivery_classification"].isin(["On Time", "Late"])
    on_time = orders["delivery_classification"].eq("On Time")
    late = orders["delivery_classification"].eq("Late")
    measures = {
        "Total Orders": int(len(orders)),
        "Delivered Orders": int(orders["order_status"].eq("delivered").sum()),
        "Classified Orders": int(classified.sum()),
        "On-Time Orders": int(on_time.sum()),
        "Late Orders": int(late.sum()),
        "On-Time Delivery Rate": float(on_time.sum() / classified.sum()),
        "Late Delivery Rate": float(late.sum() / classified.sum()),
        "Average Lead Time Days": float(orders["total_lead_time_days"].mean()),
        "Average Delay Days for Late Orders": float(orders.loc[late, "delay_days"].mean()),
        "Total Merchandise Value": float(items["price"].sum()),
        "Total Freight Value": float(items["freight_value"].sum()),
        "Total Payment Value": float(orders["payment_value"].sum()),
        "Average Review Score": float(orders["average_review_score"].mean()),
        "Total Items": int(len(items)),
        "Distinct Customers": int(customers["customer_unique_id"].nunique()),
        "Repeat Customers": int((customers.groupby("customer_unique_id").size() > 1).sum()),
    }
    measures["Freight-to-Merchandise Ratio"] = measures["Total Freight Value"] / measures["Total Merchandise Value"]
    require(measures["Classified Orders"] == measures["On-Time Orders"] + measures["Late Orders"], "classification measure reconciliation failure")
    require(measures["Total Items"] == len(items), "item measure grain failure")
    expected_merchandise = 13_591_643.70
    expected_freight = 2_251_909.54
    require(math.isclose(items["price"].sum(), expected_merchandise, rel_tol=0.0, abs_tol=ABS_TOL), "item merchandise total reconciliation failure")
    require(math.isclose(items["freight_value"].sum(), expected_freight, rel_tol=0.0, abs_tol=ABS_TOL), "item freight total reconciliation failure")
    require(math.isclose(orders["merchandise_value"].sum(), expected_merchandise, rel_tol=0.0, abs_tol=ABS_TOL), "order merchandise aggregate reconciliation failure")
    require(math.isclose(orders["freight_value"].sum(), expected_freight, rel_tol=0.0, abs_tol=ABS_TOL), "order freight aggregate reconciliation failure")
    require(
        math.isclose(
            measures["Freight-to-Merchandise Ratio"],
            RATIO_EXPECTED,
            rel_tol=0.0,
            abs_tol=RATIO_ABS_TOL,
        ),
        "Freight-to-Merchandise Ratio differs from the expected approximately 0.16568",
    )
    require(
        math.isclose(orders["merchandise_value"].sum(), measures["Total Merchandise Value"], rel_tol=0.0, abs_tol=ABS_TOL)
        and math.isclose(orders["freight_value"].sum(), measures["Total Freight Value"], rel_tol=0.0, abs_tol=ABS_TOL),
        "item-grain monetary reconciliation to order aggregates failure",
    )

    print("Power BI validation: PASS")
    print("Rows: " + ", ".join(f"{name}={count}" for name, count in expected_rows.items()))
    print("Relationships: " + ", ".join(f"{name}=PASS" for name in relationship_checks))
    print(f"DimDate range: {print_date_range} ({len(date_table)} dates; contiguous, Date table coverage verified)")
    print("Delivery classification: " + ", ".join(f"{name}={int(classification_counts[name])}" for name in sorted(allowed_classifications)))
    print("Nullable Boolean counts:")
    for column in boolean_columns:
        counts = boolean_counts[column]
        print(f"  {column}: true={counts['true']}, false={counts['false']}, null={counts['null']}")
    print("Measures:")
    for name, value in measures.items():
        if isinstance(value, float):
            print(f"  {name}: {value:.6f}")
        else:
            print(f"  {name}: {value}")
    print(f"Item totals reconcile: merchandise={items['price'].sum():.2f}, freight={items['freight_value'].sum():.2f}")
    print(f"Freight-to-Merchandise Ratio: {measures['Freight-to-Merchandise Ratio']:.8f} (expected approximately {RATIO_EXPECTED:.5f}, abs_tol={RATIO_ABS_TOL:g})")


if __name__ == "__main__":
    main()
