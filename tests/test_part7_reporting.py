"""Reporting grains and a repeatable lookup experiment on hand-calculated data."""
from pathlib import Path
import sqlite3
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from benchmark_part7 import benchmark
from prepare_part3 import result_sets, statements


class Part7ReportingTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript((PROJECT / "sql/01_setup.sql").read_text())
        self.db.executemany("INSERT INTO customers VALUES (?, ?, '01234', 'city', ?)", [
            ("CA", "PERSON1", "sp"), ("CB", "PERSON1", "rj"),
            ("CC", "PERSON2", " "), ("CD", "PERSON3", "sp"),
        ])
        self.db.executemany("INSERT INTO products VALUES (?, ?, '', '', '', '', '', '', '')", [
            ("B", "livros"), ("H", "casa"), ("M", " "), ("U", "pc_gamer"),
        ])
        self.db.executemany("INSERT INTO category_translation VALUES (?, ?)",
                            [("livros", "books"), ("casa", "home")])
        self.db.execute("INSERT INTO sellers VALUES ('S', '01234', 'city', 'sp')")
        self.add_order("A", "CA", [("B", "10.10"), ("B", "5.00"), ("H", "4.90")])
        self.add_order("B", "CB", [("M", "10.00")])
        self.add_order("C", "CC", [("U", "0.00")], actual="")
        self.add_order("D", "CD", [])
        self.add_order("X", "CA", [("B", "5.00")], status="canceled")
        self.add_order("BEFORE", "CA", [("B", "5.00")], purchase="2017-01-31 23:59:59")
        self.add_order("AFTER", "CA", [("B", "5.00")], purchase="2018-08-01 00:00:00",
                       actual="2018-08-03 00:00:00", promised="2018-08-03 00:00:00")
        for number in range(20):
            customer = f"OTHER{number:02}"
            self.db.execute("INSERT INTO customers VALUES (?, ?, '01234', 'city', 'sp')",
                            (customer, customer))
            self.add_order(customer, customer, [("B", "1.00")])
        self.db.executemany("INSERT INTO order_payments VALUES ('A', ?, 'credit_card', '1', ?)",
                            [("1", "10.00"), ("2", "13.00")])
        self.db.executemany("INSERT INTO order_reviews VALUES (?, 'A', ?, '', '', ?, ?)", [
            ("R1", "1", "2017-02-04 00:00:00", "2017-02-04 12:00:00"),
            ("R2", "5", "2017-02-05 00:00:00", "2017-02-05 12:00:00"),
        ])
        for path in ("sql/02_cleaning.sql", "sql/07_reporting_views.sql"):
            for statement in statements(PROJECT / path):
                self.db.execute(statement)
        self.db.execute("CREATE INDEX idx_item_order ON order_items(order_id)")
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def add_order(self, order_id, customer, items, status="delivered",
                  purchase="2017-02-01 00:00:00", actual="2017-02-03 00:00:00",
                  promised="2017-02-03 00:00:00"):
        self.db.execute("INSERT INTO orders VALUES (?, ?, ?, ?, '', '', ?, ?)",
                        (order_id, customer, status, purchase, actual, promised))
        self.db.executemany("INSERT INTO order_items VALUES (?, ?, ?, 'S', ?, ?, '1.00')", [
            (order_id, str(number), product, purchase, price)
            for number, (product, price) in enumerate(items, 1)
        ])

    def test_orders_keep_period_exclusions_without_child_fanout(self):
        rows = [dict(row) for row in self.db.execute("SELECT * FROM v_reporting_orders")]
        self.assertEqual(len(rows), 25)
        orders = {row["order_id"]: row for row in rows}
        self.assertEqual(len(orders), len(rows))
        self.assertNotIn("BEFORE", orders)
        self.assertNotIn("AFTER", orders)
        self.assertEqual((orders["A"]["product_sales_cents"], orders["A"]["item_count"],
                          orders["A"]["payment_count"], orders["A"]["review_score"]), (2000, 3, 2, 5))
        self.assertEqual((orders["C"]["sales_eligible"], orders["C"]["delivery_eligible"]), (1, 0))
        self.assertEqual((orders["D"]["sales_eligible"], orders["D"]["delivery_eligible"]), (0, 1))
        self.assertEqual(orders["X"]["sales_eligible"], 0)
        self.assertEqual(orders["C"]["customer_state"], "Unknown state")

    def test_item_grain_has_only_eligible_items_and_no_order_totals(self):
        rows = [dict(row) for row in self.db.execute("SELECT * FROM v_reporting_sales_items")]
        self.assertEqual(len(rows), 25)
        self.assertEqual(len({(row["order_id"], row["order_item_id"]) for row in rows}), 25)
        self.assertEqual(sum(row["price_cents"] for row in rows), 5000)
        self.assertEqual(len({row["order_id"] for row in rows}), 23)
        self.assertNotIn("product_sales_cents", rows[0])
        self.assertNotIn("review_score", rows[0])
        categories = {row["category_label"] for row in rows}
        self.assertEqual(categories, {"books", "home", "Unknown category", "Untranslated: pc_gamer"})

    def test_category_bridge_is_distinct_and_delivery_eligible(self):
        pairs = [tuple(row) for row in self.db.execute("SELECT * FROM v_reporting_order_categories")]
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertEqual(len(pairs), 24)
        self.assertEqual({category for order, category in pairs if order == "A"}, {"books", "home"})
        self.assertIn(("D", "Unknown category"), pairs)
        self.assertNotIn(("C", "Untranslated: pc_gamer"), pairs)
        self.assertFalse(any(order in {"X", "BEFORE", "AFTER"} for order, _ in pairs))

    def test_all_customers_group_persistent_identity_without_top_20_limit(self):
        rows = [dict(row) for row in self.db.execute("SELECT * FROM v_reporting_customers")]
        self.assertEqual(len(rows), 22)
        self.assertEqual(sum(row["sales_orders"] for row in rows), 23)
        self.assertEqual(sum(row["product_sales_cents"] for row in rows), 5000)
        self.assertEqual(sum(row["repeat_customer"] for row in rows), 1)
        customer = next(row for row in rows if row["customer_unique_id"] == "PERSON1")
        self.assertEqual((customer["sales_orders"], customer["product_sales_cents"],
                          customer["average_order_value"]), (2, 3000, 15.0))
        self.assertEqual((customer["reviewed_orders"], customer["review_score_sum"],
                          customer["average_review_score"], customer["review_coverage_pct"]), (1, 5, 5.0, 50.0))
        missing = next(row for row in rows if row["customer_unique_id"] == "PERSON2")
        self.assertIsNone(missing["average_review_score"])
        self.assertEqual(missing["product_sales_cents"], 0)

    def test_customer_view_reproduces_the_existing_part6_spending_output(self):
        expected = result_sets(self.db, PROJECT / "sql/05_customer_analysis.sql")["customer_spending"]
        rows = [dict(row) for row in self.db.execute("""
            SELECT * FROM v_reporting_customers
            ORDER BY product_sales_cents DESC, customer_unique_id ASC LIMIT 20
        """)]
        for observed, wanted in zip(rows, expected):
            self.assertEqual({field: observed[field] for field in wanted}, wanted)

    def test_views_can_be_rebuilt_without_changing_their_results_or_source_rows(self):
        before = list(self.db.execute("SELECT * FROM v_reporting_customers ORDER BY customer_unique_id"))
        source_count = self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        for statement in statements(PROJECT / "sql/07_reporting_views.sql"):
            self.db.execute(statement)
        self.assertEqual(list(self.db.execute("SELECT * FROM v_reporting_customers ORDER BY customer_unique_id")), before)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], source_count)

    def test_benchmark_balances_runs_checks_identity_and_uses_existing_index(self):
        self.db.execute("PRAGMA query_only = ON")
        report = benchmark(self.db, repetitions=4, warmups=1)
        self.assertEqual([case["result_rows"] for case in report["cases"]], [1, 3])
        for case in report["cases"]:
            self.assertTrue(case["result_identity_verified"])
            self.assertEqual(len(case["runs"]), 8)
            self.assertEqual({run["result_sha256"] for run in case["runs"]}, {case["result_sha256"]})
            self.assertEqual(sum(run["position"] == 1 and run["variant"] == "direct_lookup"
                                 for run in case["runs"]), 2)
            trimmed_plan = " ".join(str(row[-1]) for row in case["variants"]["trimmed_lookup"]["explain_query_plan"])
            direct_plan = " ".join(str(row[-1]) for row in case["variants"]["direct_lookup"]["explain_query_plan"])
            self.assertIn("SCAN order_items", trimmed_plan)
            self.assertIn("USING INDEX idx_item_order", direct_plan)
            for variant in case["variants"].values():
                self.assertEqual(len(variant["all_timings_ms"]), 4)
                self.assertGreaterEqual(variant["median_ms"], variant["min_ms"])

    def test_benchmark_rejects_ids_that_make_the_two_predicates_different(self):
        self.db.execute("UPDATE order_items SET order_id=' A ' WHERE order_id='A'")
        with self.assertRaisesRegex(ValueError, "without surrounding spaces"):
            benchmark(self.db, repetitions=2, warmups=1)

    def test_benchmark_rejects_unbalanced_iteration_counts(self):
        with self.assertRaisesRegex(ValueError, "even integer"):
            benchmark(self.db, repetitions=3, warmups=1)


if __name__ == "__main__":
    unittest.main()
