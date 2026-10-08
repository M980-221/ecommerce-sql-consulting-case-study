"""Hand-calculated delivery cases, from raw dates and items to final reports."""
from pathlib import Path
import sqlite3
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from prepare_part3 import result_sets, statements


class Part5Tests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript((PROJECT / "sql/01_setup.sql").read_text())
        self.db.executemany("INSERT INTO customers VALUES (?, ?, '01234', 'city', ?)", [
            ("SP", "PERSON_SP", "sp"), ("RJ", "PERSON_RJ", "rj"),
            ("MG", "PERSON_MG", "mg"), ("BLANK", "PERSON_BLANK", "  "),
        ])
        self.db.executemany("INSERT INTO products VALUES (?, ?, '', '', '', '', '', '', '')", [
            ("B", "livros"), ("H", "casa"), ("M", " "), ("U", "pc_gamer"),
        ])
        self.db.executemany("INSERT INTO category_translation VALUES (?, ?)", [
            ("livros", "books"), ("casa", "home"),
        ])
        self.db.executemany("INSERT INTO sellers VALUES (?, '01234', 'city', ?)", [
            ("S1", "sp"), ("S2", "rj"),
        ])
        self.add_order("A", "2017-02-01 12:00:00", "2017-02-03 18:00:00",
                       "2017-02-03 00:00:00", items=[("B", "S1"), ("B", "S1"), ("H", "S1")])
        self.add_order("B", "2017-02-02 12:00:00", "2017-02-06 12:00:00",
                       "2017-02-04 00:00:00", items=[("B", "S1")])
        self.add_order("C", "2017-03-01 00:00:00", "2017-03-04 00:00:00",
                       "2017-03-03 00:00:00", customer="RJ", items=[("B", "S1"), ("H", "S2")])
        self.add_order("D", "2017-03-02 00:00:00", "2017-03-03 00:00:00",
                       "2017-03-04 00:00:00", customer="MG")
        self.add_order("E", "2017-02-28 23:59:59", "2017-03-02 23:59:59",
                       "2017-03-03 00:00:00", customer="BLANK", items=[("M", "S2")])
        self.add_order("F", "2018-07-31 23:59:59", "2018-08-02 23:59:59",
                       "2018-08-02 00:00:00", customer="BLANK", items=[("U", "S3")])
        self.add_order("CANCELED", "2017-02-10 00:00:00", "2017-02-20 00:00:00",
                       "2017-02-11 00:00:00", status="canceled", items=[("B", "S1")])
        self.add_order("MISSING_DATE", "2017-02-10 00:00:00", "",
                       "2017-02-11 00:00:00", items=[("B", "S1")])
        self.add_order("BEFORE", "2017-01-31 23:59:59", "2017-02-02 00:00:00",
                       "2017-02-01 00:00:00", items=[("B", "S1")])
        self.add_order("AFTER", "2018-08-01 00:00:00", "2018-08-03 00:00:00",
                       "2018-08-02 00:00:00", items=[("B", "S1")])
        self.db.commit()
        for statement in statements(PROJECT / "sql/02_cleaning.sql"):
            self.db.execute(statement)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def add_order(self, order_id, purchase, actual, promised, customer="SP",
                  status="delivered", items=()):
        self.db.execute("INSERT INTO orders VALUES (?, ?, ?, ?, '', '', ?, ?)",
                        (order_id, customer, status, purchase, actual, promised))
        self.db.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, '1.00', '0.00')", [
            (order_id, str(index), product, seller, purchase)
            for index, (product, seller) in enumerate(items, 1)
        ])

    def results(self):
        return result_sets(self.db, PROJECT / "sql/04_delivery_analysis.sql")

    def clear_orders(self):
        self.db.execute("DELETE FROM orders")
        self.db.execute("DELETE FROM order_items")

    def test_headline_counts_exclusions_and_distinct_seller_coverage(self):
        row = self.results()["overall_delivery"][0]
        self.assertEqual((row["all_period_orders"], row["delivery_orders"], row["excluded_orders"]),
                         (8, 6, 2))
        self.assertEqual((row["non_delivered_orders"], row["excluded_delivered_date_orders"]), (1, 1))
        self.assertEqual((row["late_orders"], row["on_time_orders"],
                          row["late_delivery_pct"], row["on_time_delivery_pct"]), (2, 4, 33.33, 66.67))
        # Six durations: 2.25, 4, 3, 1, 2 and 2 elapsed days.
        self.assertEqual(row["average_delivery_days"], 2.38)
        self.assertEqual((row["single_seller_orders"], row["excluded_multi_seller_orders"],
                          row["excluded_no_seller_orders"]), (4, 1, 1))
        self.assertEqual((row["reported_sellers"], row["reported_seller_orders"],
                          row["below_threshold_seller_orders"],
                          row["reported_seller_order_coverage_pct"]), (0, 0, 4, 0.0))

    def test_all_calendar_months_and_exclusive_reporting_boundaries(self):
        rows = self.results()["monthly_delivery"]
        self.assertEqual(len(rows), 18)
        self.assertEqual((rows[0]["month"], rows[-1]["month"]), ("2017-02", "2018-07"))
        february = rows[0]
        self.assertEqual((february["all_period_orders"], february["delivery_orders"],
                          february["excluded_orders"], february["late_orders"]), (5, 3, 2, 1))
        self.assertEqual((february["average_delivery_days"],
                          february["average_positive_delay_days"]), (2.75, 2.0))
        self.assertEqual(sum(row["all_period_orders"] for row in rows), 8)
        self.assertEqual(sum(row["delivery_orders"] for row in rows), 6)
        # The July purchase remains eligible even though it arrived in August.
        self.assertEqual((rows[-1]["delivery_orders"], rows[-1]["late_orders"]), (1, 0))
        self.assertIsNone(rows[-1]["average_positive_delay_days"])
        april = rows[2]
        self.assertEqual((april["delivery_orders"], april["late_orders"], april["on_time_orders"]),
                         (0, 0, 0))
        for field in ("late_delivery_pct", "average_delivery_days", "average_positive_delay_days"):
            self.assertIsNone(april[field])
        # The lower boundary itself is included, the preceding second is not.
        self.db.execute("UPDATE orders SET order_purchase_timestamp='2017-02-01 00:00:00' WHERE order_id='BEFORE'")
        self.assertEqual(self.results()["overall_delivery"][0]["delivery_orders"], 7)

    def test_receipt_late_in_the_promised_day_is_still_on_time(self):
        self.db.execute("UPDATE orders SET order_delivered_customer_date='2017-02-03 23:59:59' WHERE order_id='A'")
        self.assertEqual(self.results()["overall_delivery"][0]["late_orders"], 2)
        self.db.execute("UPDATE orders SET order_delivered_customer_date='2017-02-04 00:00:00' WHERE order_id='A'")
        row = self.results()["overall_delivery"][0]
        self.assertEqual((row["late_orders"], row["average_positive_delay_days"]), (3, 1.33))

    def test_positive_delay_averages_only_late_orders(self):
        # Late orders are two and one days late; early deliveries cannot offset them.
        self.assertEqual(self.results()["overall_delivery"][0]["average_positive_delay_days"], 1.5)
        self.db.execute("UPDATE orders SET order_estimated_delivery_date='2017-03-20 00:00:00' WHERE order_id='D'")
        self.assertEqual(self.results()["overall_delivery"][0]["average_positive_delay_days"], 1.5)

    def test_categories_deduplicate_repeated_items_but_keep_cross_category_orders(self):
        rows = self.results()["category_delivery"]
        categories = {row["category_label"]: row for row in rows}
        self.assertEqual((categories["books"]["delivery_orders"], categories["books"]["late_orders"]), (3, 2))
        self.assertEqual(categories["books"]["late_delivery_pct"], 66.67)
        self.assertEqual(categories["books"]["average_delivery_days"], 3.08)
        self.assertEqual((categories["home"]["delivery_orders"], categories["home"]["late_orders"]), (2, 1))
        self.assertEqual(sum(row["delivery_orders"] for row in rows), 8)
        self.assertEqual(sum(row["late_orders"] for row in rows), 3)

    def test_missing_categories_products_and_items_remain_visible(self):
        categories = {row["category_label"]: row for row in self.results()["category_delivery"]}
        self.assertEqual(categories["Unknown category"]["delivery_orders"], 2)
        self.assertEqual(categories["Untranslated: pc_gamer"]["delivery_orders"], 1)
        self.db.execute("UPDATE order_items SET product_id='NO_LOOKUP' WHERE order_id='E'")
        categories = {row["category_label"]: row for row in self.results()["category_delivery"]}
        self.assertEqual(categories["Unknown category"]["delivery_orders"], 2)
        self.assertIsNone(categories["Unknown category"]["average_positive_delay_days"])

    def test_buyer_states_preserve_unknowns_and_sort_by_late_count_then_rate(self):
        rows = self.results()["regional_delivery"]
        self.assertEqual([row["customer_state"] for row in rows], ["RJ", "SP", "MG", "Unknown state"])
        states = {row["customer_state"]: row for row in rows}
        self.assertEqual((states["SP"]["delivery_orders"], states["SP"]["late_orders"]), (2, 1))
        self.assertEqual(states["Unknown state"]["delivery_orders"], 2)
        self.assertEqual(sum(row["delivery_orders"] for row in rows), 6)
        self.assertEqual(sum(row["late_orders"] for row in rows), 2)

    def test_seller_cutoff_is_100_orders_not_items_and_reports_excluded_coverage(self):
        self.clear_orders()
        for seller, count in [("S1", 100), ("S2", 99), ("S3", 100)]:
            for number in range(count):
                self.add_order(f"{seller}_{number}", "2017-02-01 00:00:00",
                               "2017-02-06 00:00:00" if number == 0 else "2017-02-03 00:00:00",
                               "2017-02-04 00:00:00", items=[("B", seller), ("B", seller)])
        self.add_order("MULTI", "2017-02-01 00:00:00", "2017-02-06 00:00:00",
                       "2017-02-04 00:00:00", items=[("B", "S1"), ("B", "S2")])
        self.add_order("NO_ITEMS", "2017-02-01 00:00:00", "2017-02-06 00:00:00", "2017-02-04 00:00:00")
        results = self.results()
        rows = results["seller_delivery"]
        self.assertEqual([row["seller_id"] for row in rows], ["S1", "S3"])
        self.assertEqual([row["delivery_orders"] for row in rows], [100, 100])
        self.assertEqual([row["late_orders"] for row in rows], [1, 1])
        self.assertEqual(rows[1]["seller_state"], "Unknown state")
        row = results["overall_delivery"][0]
        self.assertEqual((row["delivery_orders"], row["single_seller_orders"],
                          row["excluded_multi_seller_orders"], row["excluded_no_seller_orders"]),
                         (301, 299, 1, 1))
        self.assertEqual((row["reported_sellers"], row["reported_seller_orders"],
                          row["below_threshold_seller_orders"],
                          row["reported_seller_order_coverage_pct"]), (2, 200, 99, 66.45))

    def test_no_late_orders_have_zero_rate_and_undefined_positive_delay(self):
        self.db.execute("UPDATE orders SET order_estimated_delivery_date=SUBSTR(order_delivered_customer_date, 1, 10) || ' 00:00:00' WHERE order_id IN ('B', 'C')")
        row = self.results()["overall_delivery"][0]
        self.assertEqual((row["late_orders"], row["late_delivery_pct"], row["on_time_delivery_pct"]), (0, 0.0, 100.0))
        self.assertIsNone(row["average_positive_delay_days"])

    def test_positive_delay_rounds_exact_half_hundredths_up(self):
        self.clear_orders()
        for number in range(100):
            actual = ("2017-02-12 00:00:00" if number < 39 else
                      "2017-02-05 00:00:00" if number == 39 else "2017-02-02 00:00:00")
            self.add_order(str(number), "2017-02-01 00:00:00", actual,
                           "2017-02-02 00:00:00", items=[("B", "S1")])
        # 39 * 10 + 3 = 393 days across 40 late orders: 9.825 rounds to 9.83.
        for name, rows in self.results().items():
            self.assertEqual(rows[0]["average_positive_delay_days"], 9.83, name)

    def test_empty_source_preserves_periods_and_undefined_rates(self):
        self.clear_orders()
        results = self.results()
        row = results["overall_delivery"][0]
        for field in ("all_period_orders", "delivery_orders", "excluded_orders", "late_orders",
                      "on_time_orders", "reported_sellers", "reported_seller_orders"):
            self.assertEqual(row[field], 0)
        for field in ("late_delivery_pct", "on_time_delivery_pct", "average_delivery_days",
                      "average_positive_delay_days", "reported_seller_order_coverage_pct"):
            self.assertIsNone(row[field])
        self.assertEqual(len(results["monthly_delivery"]), 18)
        for name in ("regional_delivery", "category_delivery", "seller_delivery"):
            self.assertEqual(results[name], [])

    def test_period_orders_with_no_eligible_deliveries_keep_exclusions(self):
        self.db.execute("UPDATE orders SET order_status='canceled'")
        row = self.results()["overall_delivery"][0]
        self.assertEqual((row["all_period_orders"], row["delivery_orders"], row["excluded_orders"]), (8, 0, 8))
        self.assertEqual((row["non_delivered_orders"], row["excluded_delivered_date_orders"]), (8, 0))
        self.assertIsNone(row["late_delivery_pct"])
        self.assertIsNone(row["average_delivery_days"])


if __name__ == "__main__":
    unittest.main()
