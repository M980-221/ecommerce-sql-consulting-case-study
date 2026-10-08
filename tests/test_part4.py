"""Hand-calculated cases for sales totals, comparison periods and denominators."""
from pathlib import Path
import sqlite3
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from prepare_part3 import result_sets


class Part4Tests(unittest.TestCase):
    def setUp(self):
        # Part 3 already tests the eligibility rules. These fixtures test how
        # the analysis uses that prepared order and item data.
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE v_order_analysis (
                order_id TEXT PRIMARY KEY,
                order_purchase_timestamp TEXT,
                in_reporting_period INTEGER,
                sales_eligible INTEGER,
                product_sales_cents INTEGER,
                customer_state TEXT
            );
            CREATE TABLE v_clean_order_items (
                order_id TEXT, order_item_id INTEGER,
                product_id TEXT, price_cents INTEGER
            );
            CREATE TABLE v_products_labeled (
                product_id TEXT PRIMARY KEY, category_label TEXT
            );
        """)
        self.db.executemany("INSERT INTO v_products_labeled VALUES (?, ?)", [
            ("B", "books"), ("H", "home"),
            ("M", "Unknown category"), ("U", "Untranslated: pc_gamer"),
        ])
        self.db.executemany("INSERT INTO v_order_analysis VALUES (?, ?, ?, ?, ?, ?)", [
            ("O1", "2017-02-01 00:00:00", 1, 1, 3000, "SP"),
            ("O2", "2017-02-28 23:59:59", 1, 1, 1000, "RJ"),
            ("X1", "2017-02-15 10:00:00", 1, 0, 99900, "SP"),
            ("X2", "2017-02-20 10:00:00", 1, 0, None, "SP"),
            ("O3", "2017-03-01 00:00:00", 1, 1, 2000, "SP"),
            ("O4", "2017-05-01 00:00:00", 1, 1, 0, "SP"),
            ("O5", "2017-06-01 00:00:00", 1, 1, 1000, None),
            ("O6", "2017-07-01 00:00:00", 1, 1, 1000, "  "),
            ("O7", "2017-08-01 00:00:00", 1, 1, 100000, "SP"),
            ("O8", "2018-01-01 00:00:00", 1, 1, 50000, "SP"),
            ("O9", "2018-02-01 00:00:00", 1, 1, 9000, "SP"),
            ("O10", "2018-02-01 12:00:00", 1, 1, 3000, "RJ"),
            ("O11", "2018-07-31 23:59:59", 1, 1, 4, "MG"),
            ("BEFORE", "2017-01-31 23:59:59", 0, 0, 1000000, "SP"),
            ("AFTER", "2018-08-01 00:00:00", 0, 0, 1000000, "SP"),
        ])
        self.db.executemany("INSERT INTO v_clean_order_items VALUES (?, ?, ?, ?)", [
            ("O1", 1, "B", 1000), ("O1", 2, "B", 500), ("O1", 3, "H", 1500),
            ("O2", 1, "B", 1000), ("X1", 1, "B", 99900),
            ("O3", 1, "H", 2000), ("O4", 1, "B", 0),
            ("O5", 1, "M", 1000), ("O6", 1, "U", 1000),
            ("O7", 1, "H", 100000), ("O8", 1, "B", 50000),
            ("O9", 1, "H", 9000), ("O10", 1, "B", 3000),
            ("O11", 1, "NO_LOOKUP_ROW", 4),
            ("BEFORE", 1, "B", 1000000), ("AFTER", 1, "H", 1000000),
        ])

    def tearDown(self):
        self.db.close()

    def results(self):
        return result_sets(self.db, PROJECT / "sql/03_sales_analysis.sql")

    def clear_orders(self):
        self.db.execute("DELETE FROM v_order_analysis")
        self.db.execute("DELETE FROM v_clean_order_items")

    def test_months_keep_empty_months_and_reporting_boundaries(self):
        rows = self.results()["monthly_sales"]
        self.assertEqual(len(rows), 18)
        self.assertEqual((rows[0]["month"], rows[-1]["month"]), ("2017-02", "2018-07"))
        february = rows[0]
        self.assertEqual((february["all_period_orders"], february["sales_orders"],
                          february["excluded_orders"]), (4, 2, 2))
        self.assertEqual((february["product_sales_cents"], february["average_order_value"]),
                         (4000, 20.0))
        april = rows[2]
        self.assertEqual((april["month"], april["all_period_orders"], april["sales_orders"],
                          april["product_sales_cents"]), ("2017-04", 0, 0, 0))
        self.assertIsNone(april["average_order_value"])
        self.assertEqual(rows[-1]["product_sales_cents"], 4)
        self.assertEqual(sum(row["product_sales_cents"] for row in rows), 170004)
        self.assertEqual(sum(row["sales_orders"] for row in rows), 11)

    def test_growth_uses_previous_calendar_month_not_previous_sale(self):
        rows = {row["month"]: row for row in self.results()["monthly_growth"]}
        self.assertEqual((rows["2017-03"]["product_sales_mom_pct"],
                          rows["2017-03"]["orders_mom_pct"],
                          rows["2017-03"]["aov_mom_pct"]), (-50.0, -50.0, 0.0))
        self.assertEqual(rows["2017-04"]["product_sales_mom_pct"], -100.0)
        self.assertEqual(rows["2017-05"]["previous_month_sales_orders"], 0)
        self.assertIsNone(rows["2017-05"]["orders_mom_pct"])
        self.assertIsNone(rows["2017-06"]["product_sales_mom_pct"])
        self.assertIsNone(rows["2017-06"]["aov_mom_pct"])
        self.assertEqual(rows["2017-06"]["orders_mom_pct"], 0.0)
        for field in ("product_sales_mom_pct", "orders_mom_pct", "aov_mom_pct"):
            self.assertIsNone(rows["2017-02"][field])

    def test_equal_six_month_periods_and_weighted_aov(self):
        earlier, later = self.results()["comparable_periods"]
        self.assertEqual((earlier["period_start"], earlier["period_end_exclusive"]),
                         ("2017-02-01", "2017-08-01"))
        self.assertEqual((earlier["calendar_months"], later["calendar_months"]), (6, 6))
        self.assertEqual((earlier["product_sales_cents"], earlier["sales_orders"],
                          earlier["all_period_orders"], earlier["excluded_orders"]), (8000, 6, 8, 2))
        self.assertEqual(earlier["average_order_value"], 13.33)
        self.assertEqual((later["product_sales_cents"], later["sales_orders"]), (12004, 3))
        self.assertEqual(later["average_order_value"], 40.01)
        self.assertEqual((later["product_sales_yoy_pct"], later["orders_yoy_pct"],
                          later["aov_yoy_pct"]), (50.05, -50.0, 200.1))
        for field in ("product_sales_yoy_pct", "orders_yoy_pct", "aov_yoy_pct"):
            self.assertIsNone(earlier[field])

    def test_item_prices_and_distinct_orders_prevent_category_overcount(self):
        rows = self.results()["category_sales"]
        categories = {row["category_label"]: row for row in rows}
        books = categories["books"]
        self.assertEqual((books["product_sales_cents"], books["sales_orders"],
                          books["item_count"]), (55500, 5, 6))
        self.assertEqual(categories["home"]["product_sales_cents"], 112500)
        self.assertEqual(sum(row["product_sales_cents"] for row in rows), 170004)
        # O1 has two categories, so its order count appears in both rows.
        self.assertEqual(sum(row["sales_orders"] for row in rows), 12)
        self.assertEqual(sum(row["item_count"] for row in rows), 13)

    def test_missing_and_untranslated_categories_stay_in_shares(self):
        rows = self.results()["category_sales"]
        categories = {row["category_label"]: row for row in rows}
        self.assertEqual(categories["Unknown category"]["product_sales_cents"], 1004)
        self.assertEqual(categories["Untranslated: pc_gamer"]["product_sales_cents"], 1000)
        self.assertEqual(categories["home"]["sales_share_pct"], 66.17)
        self.assertEqual(rows[-1]["cumulative_sales_share_pct"], 100.0)

    def test_buyer_states_count_orders_once_and_keep_unknowns(self):
        rows = self.results()["regional_sales"]
        states = {row["customer_state"]: row for row in rows}
        self.assertEqual((states["SP"]["product_sales_cents"], states["SP"]["sales_orders"]),
                         (164000, 6))
        self.assertEqual((states["Unknown state"]["product_sales_cents"],
                          states["Unknown state"]["sales_orders"]), (2000, 2))
        self.assertEqual(states["MG"]["average_order_value"], 0.04)
        self.assertEqual(sum(row["sales_orders"] for row in rows), 11)
        self.assertEqual(sum(row["product_sales_cents"] for row in rows), 170004)

    def test_tied_categories_have_stable_running_shares(self):
        self.clear_orders()
        self.db.executemany("INSERT INTO v_order_analysis VALUES (?, ?, 1, 1, 100, 'SP')", [
            ("H1", "2017-02-01"), ("B1", "2017-02-01"),
        ])
        self.db.executemany("INSERT INTO v_clean_order_items VALUES (?, 1, ?, 100)", [
            ("H1", "H"), ("B1", "B"),
        ])
        rows = self.results()["category_sales"]
        self.assertEqual([row["category_label"] for row in rows], ["books", "home"])
        self.assertEqual([row["cumulative_sales_share_pct"] for row in rows], [50.0, 100.0])

    def test_zero_value_sales_have_zero_aov_but_undefined_shares_and_growth(self):
        self.clear_orders()
        self.db.execute("INSERT INTO v_order_analysis VALUES ('Z', '2017-02-01', 1, 1, 0, 'SP')")
        self.db.execute("INSERT INTO v_clean_order_items VALUES ('Z', 1, 'B', 0)")
        results = self.results()
        self.assertEqual(results["monthly_sales"][0]["average_order_value"], 0.0)
        self.assertIsNone(results["category_sales"][0]["sales_share_pct"])
        self.assertIsNone(results["category_sales"][0]["cumulative_sales_share_pct"])
        self.assertIsNone(results["regional_sales"][0]["sales_share_pct"])
        self.assertIsNone(results["comparable_periods"][1]["product_sales_yoy_pct"])
        self.assertIsNone(results["comparable_periods"][1]["aov_yoy_pct"])

    def test_growth_uses_unrounded_aov(self):
        self.clear_orders()
        self.db.executemany("INSERT INTO v_order_analysis VALUES (?, ?, 1, 1, ?, 'SP')", [
            ("A1", "2017-02-01", 101), ("A2", "2017-02-01", 100), ("A3", "2017-02-01", 100),
            ("B1", "2017-03-01", 101), ("B2", "2017-03-01", 101), ("B3", "2017-03-01", 101),
        ])
        march = self.results()["monthly_growth"][1]
        # Exact AOV growth is 2 / 301 * 100 = 0.6645%, which rounds to 0.66%.
        # Using displayed AOVs of 1.00 and 1.01 would instead give 1.00%.
        self.assertEqual(march["aov_mom_pct"], 0.66)
        self.assertEqual(march["average_order_value"], 1.01)
        self.assertEqual(march["previous_month_average_order_value"], 1.0)

    def test_empty_source_preserves_time_periods_without_inventing_aov(self):
        self.clear_orders()
        results = self.results()
        self.assertEqual(len(results["monthly_sales"]), 18)
        self.assertEqual(len(results["comparable_periods"]), 2)
        for row in results["monthly_sales"]:
            self.assertEqual((row["all_period_orders"], row["sales_orders"],
                              row["product_sales_cents"]), (0, 0, 0))
            self.assertIsNone(row["average_order_value"])
        for row in results["comparable_periods"]:
            self.assertEqual(row["sales_orders"], 0)
            self.assertIsNone(row["average_order_value"])
            self.assertIsNone(row["product_sales_yoy_pct"])
        self.assertEqual(results["category_sales"], [])
        self.assertEqual(results["regional_sales"], [])


if __name__ == "__main__":
    unittest.main()
