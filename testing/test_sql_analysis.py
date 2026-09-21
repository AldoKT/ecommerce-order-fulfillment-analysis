"""Standard-library regression tests for the Day 3 in-memory SQLite analysis."""

from __future__ import annotations

import importlib.util
import math
import os
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
SPEC = importlib.util.spec_from_file_location("sql_analysis", ROOT / "python/04_sql_analysis.py")
assert SPEC and SPEC.loader
sql_analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sql_analysis)


class SqlAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.connection, cls.source_rows = sql_analysis.load_database()
        cls.results = sql_analysis.execute_queries(cls.connection)
        sql_analysis.validate_results(cls.connection, cls.results, cls.source_rows)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_required_processed_files_exist(self) -> None:
        for filename in ("fact_orders.csv", "fact_order_items.csv", "dim_customers.csv", "dim_products.csv", "dim_sellers.csv"):
            self.assertTrue((ROOT / "data/processed" / filename).is_file(), filename)

    def test_fact_order_keys_are_unique(self) -> None:
        orders = self.source_rows["fact_orders"]
        items = self.source_rows["fact_order_items"]
        self.assertEqual(len(orders), len({row["order_id"] for row in orders}))
        self.assertEqual(len(items), len({(row["order_id"], row["order_item_id"]) for row in items}))

    def test_headline_totals_equal_processed_totals(self) -> None:
        headline = self.results["overall_order_fulfillment_summary"][0]
        orders = self.source_rows["fact_orders"]
        self.assertEqual(headline["total_orders"], len(orders))
        self.assertEqual(headline["delivered_orders"], sum(row["order_status"] == "delivered" for row in orders))
        self.assertEqual(headline["classified_orders"], sum(row["delivery_classification"] in {"On Time", "Late"} for row in orders))

    def test_exact_query_names_and_result_schemas(self) -> None:
        self.assertEqual(set(sql_analysis.load_queries()), set(sql_analysis.EXPECTED_QUERY_COLUMNS))
        for name, rows in self.results.items():
            self.assertEqual(list(rows[0]), sql_analysis.EXPECTED_QUERY_COLUMNS[name])

    def test_monthly_totals_reconcile_to_overall(self) -> None:
        headline = self.results["overall_order_fulfillment_summary"][0]
        monthly = self.results["monthly_fulfillment_trend"]
        self.assertEqual(sum(row["total_orders"] for row in monthly), headline["total_orders"])

    def test_monthly_ordering_boundary_flags_and_ranking_rule(self) -> None:
        monthly = self.results["monthly_fulfillment_trend"]
        self.assertEqual([row["year_month"] for row in monthly], sorted(row["year_month"] for row in monthly))
        boundary = {row["year_month"] for row in monthly if row["is_boundary_month"] == 1}
        self.assertEqual(boundary, {"2016-09", "2018-10"})
        comparative = sql_analysis.comparative_months(monthly)
        self.assertTrue(all(row["is_boundary_month"] == 0 and row["classified_orders"] >= 100 for row in comparative))
        self.assertNotIn("2016-09", {row["year_month"] for row in comparative})
        self.assertNotIn("2018-10", {row["year_month"] for row in comparative})
        lowest = min(comparative, key=lambda row: (row["on_time_rate"], row["year_month"]))
        self.assertEqual(lowest["year_month"], "2018-03")

    def test_customer_state_totals_reconcile_to_overall(self) -> None:
        headline = self.results["overall_order_fulfillment_summary"][0]
        state_total = self.connection.execute("SELECT SUM(total_orders) FROM vw_customer_state_fulfillment").fetchone()[0]
        self.assertEqual(state_total, headline["total_orders"])

    def test_state_threshold_and_al_rate(self) -> None:
        states = self.results["customer_state_fulfillment_performance"]
        self.assertTrue(all(row["classified_orders"] >= 100 for row in states))
        alabama = next(row for row in states if row["customer_state"] == "AL")
        self.assertEqual((alabama["late_orders"], alabama["classified_orders"]), (85, 397))
        self.assertTrue(math.isclose(alabama["on_time_rate"], 0.7858942065, rel_tol=0.0, abs_tol=1e-10))

    def test_item_commercial_totals_reconcile(self) -> None:
        items = self.source_rows["fact_order_items"]
        expected_merchandise = sum(row["price"] or 0.0 for row in items)
        expected_freight = sum(row["freight_value"] or 0.0 for row in items)
        for query_name in ("product_category_commercial_performance", "seller_state_commercial_performance"):
            rows = self.results[query_name]
            self.assertEqual(sum(row["total_items"] for row in rows), len(items))
            self.assertTrue(math.isclose(sum(row["merchandise_value"] or 0.0 for row in rows), expected_merchandise, rel_tol=0.0, abs_tol=1e-6))
            self.assertTrue(math.isclose(sum(row["freight_value"] or 0.0 for row in rows), expected_freight, rel_tol=0.0, abs_tol=1e-6))

    def test_rate_denominators_exclude_not_classified_orders(self) -> None:
        headline = self.results["overall_order_fulfillment_summary"][0]
        self.assertEqual(headline["classified_orders"], headline["on_time_orders"] + headline["late_orders"])
        self.assertNotEqual(headline["classified_orders"], headline["total_orders"])
        self.assertTrue(math.isclose(headline["on_time_rate"], headline["on_time_orders"] / headline["classified_orders"], rel_tol=0.0, abs_tol=1e-12))

    def test_repeat_customer_and_nullable_lifecycle_semantics(self) -> None:
        repeat = self.results["customer_repeat_order_summary"][0]
        self.assertEqual(repeat["one_time_customers"] + repeat["repeat_customers"], repeat["distinct_customers"])
        self.assertEqual(repeat["repeat_customers"], 2_997)
        self.assertTrue(math.isclose(repeat["repeat_customer_rate"], 2_997 / 96_096, rel_tol=0.0, abs_tol=1e-12))
        orders = self.source_rows["fact_orders"]
        for field, expected in (("valid_preparation_sequence", (96_285, 1_359, 1_797)), ("valid_transportation_sequence", (96_452, 23, 2_966))):
            observed = (sum(row[field] == 1 for row in orders), sum(row[field] == 0 for row in orders), sum(row[field] is None for row in orders))
            self.assertEqual(observed, expected)

    @staticmethod
    def synthetic_connection() -> sqlite3.Connection:
        connection = sqlite3.connect(":memory:")
        connection.executescript("""
            CREATE TABLE fact_orders (
                order_id TEXT, customer_unique_id TEXT, customer_state TEXT, order_status TEXT,
                purchase_year_month TEXT, purchase_date TEXT, approval_timestamp TEXT,
                carrier_handoff_timestamp TEXT, delivery_timestamp TEXT, total_lead_time_days REAL,
                delay_days INTEGER, delivery_classification TEXT, valid_preparation_sequence INTEGER,
                valid_transportation_sequence INTEGER, payment_value REAL
            );
            CREATE TABLE fact_order_items (
                order_id TEXT, order_item_id INTEGER, product_id TEXT, seller_id TEXT,
                product_category_original TEXT, product_category_english TEXT,
                shipping_limit_timestamp TEXT, price REAL, freight_value REAL,
                customer_state TEXT, seller_state TEXT
            );
        """)
        connection.executescript((ROOT / "sql/01_analysis_views.sql").read_text(encoding="utf-8"))
        return connection

    def test_query_level_zero_denominator_protection(self) -> None:
        connection = self.synthetic_connection()
        try:
            connection.execute("INSERT INTO fact_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("o1", "c1", "SP", "created", "2020-01", "2020-01-01", None, None, None, None, None, "Not Classified", None, None, None))
            monthly = connection.execute(sql_analysis.load_queries()["monthly_fulfillment_trend"]).fetchone()
            self.assertIsNone(monthly[5])
            connection.execute("INSERT INTO fact_order_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("o1", 1, "p1", "s1", None, "Zero", None, 0.0, 4.0, "SP", "ZZ"))
            product = connection.execute(sql_analysis.load_queries()["product_category_commercial_performance"]).fetchone()
            seller = connection.execute(sql_analysis.load_queries()["seller_state_commercial_performance"]).fetchone()
            self.assertIsNone(product[4])
            self.assertIsNone(seller[4])
        finally:
            connection.close()

    def test_parser_handles_comments_ctes_and_duplicate_names(self) -> None:
        cte_text = """-- QUERY: cte_example\n-- an ordinary comment\nWITH values_cte AS (SELECT 1 AS value)\nSELECT value FROM values_cte;\n"""
        parsed = sql_analysis.parse_queries(cte_text)
        self.assertEqual(parsed["cte_example"], "WITH values_cte AS (SELECT 1 AS value)\nSELECT value FROM values_cte")
        duplicate_text = "-- QUERY: duplicate\nSELECT 1;\n-- QUERY: duplicate\nSELECT 2;\n"
        with self.assertRaisesRegex(AssertionError, "Duplicate query label: duplicate"):
            sql_analysis.parse_queries(duplicate_text)

    def test_generated_report_contains_required_sections(self) -> None:
        report = ROOT / "docs/sql-analysis.md"
        self.assertTrue(report.is_file())
        before = report.read_bytes()
        temporary_report = Path("temporary-test-output/sql-analysis.md")
        with patch.object(Path, "write_text", autospec=True) as write_text:
            sql_analysis.generate_report(self.results, temporary_report)
            self.assertEqual(write_text.call_args.args[0], temporary_report)
            contents = write_text.call_args.args[1]
        for heading in (
            "## Scope and analytical assumptions",
            "## Headline KPI results",
            "## Monthly fulfillment findings",
            "## Customer-state analysis",
            "## Product-category analysis",
            "## Seller-state analysis",
            "## Repeat-customer summary",
            "## Data-quality caveats",
            "## Business interpretation",
            "## Limitations",
            "## Reproducibility command",
        ):
            self.assertIn(heading, contents)
        self.assertEqual(report.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
