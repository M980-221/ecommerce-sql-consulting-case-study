"""Customer-analysis cases built from raw orders, items, payments and reviews."""
from pathlib import Path
import sqlite3
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from prepare_part3 import result_sets, statements


class Part6Tests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript((PROJECT / "sql/01_setup.sql").read_text())
        self.db.executemany("INSERT INTO customers VALUES (?, ?, '01234', 'city', ?)", [
            ("C1", "PERSON1", "sp"), ("C2", "PERSON1", "sp"),
            ("C3", "PERSON2", "rj"), ("C4", "PERSON3", "  "),
            ("C5", "PERSON4", "mg"), ("C6", "PERSON5", "sp"),
            ("C7", "PERSON6", "rj"), ("C8", "PERSON7", "mg"),
        ])
        self.db.execute("INSERT INTO products VALUES ('P', '', '', '', '', '', '', '', '')")
        self.db.execute("INSERT INTO sellers VALUES ('S', '01234', 'city', 'sp')")
        self.add_order("A", "C1", prices=("10.10", "10.10", "10.10"))
        self.add_order("B", "C2", actual="2017-02-05 18:00:00", prices=("20.00",))
        self.add_order("C", "C3")
        self.add_order("D", "C4")
        self.add_order("E", "C5", actual="")
        self.add_order("F", "C6")
        self.add_order("G", "C7", purchase="2017-02-02 10:00:00",
                       actual="2017-02-01 18:00:00")
        self.add_order("H", "C8", actual="2017-02-05 18:00:00")
        self.add_order("BEFORE", "C3", purchase="2017-01-31 23:59:59")
        self.add_order("AFTER", "C3", purchase="2018-08-01 00:00:00",
                       actual="2018-08-03 18:00:00", promised="2018-08-03 00:00:00")
        self.add_order("CANCELED", "C3", status="canceled")
        self.add_order("NO_ITEMS", "C3", prices=())
        self.db.executemany("INSERT INTO order_payments VALUES ('A', ?, ?, '1', ?)", [
            ("1", "credit_card", "20.00"), ("2", "voucher", "10.30"),
        ])
        self.add_review("A", 1, review_id="A_old")
        self.add_review("A", 5, review_id="A_z", created="2017-02-05 00:00:00",
                        answer="2017-02-05 12:00:00")
        self.add_review("A", 3, review_id="A_a", created="2017-02-05 00:00:00",
                        answer="2017-02-05 12:00:00")
        self.add_review("A", 1, review_id="A_invalid", created="2017-01-31 00:00:00",
                        answer="2017-02-06 12:00:00")
        self.add_review("B", 1, created="2017-02-02 00:00:00", answer="2017-02-02 12:00:00")
        self.add_review("C", 2)
        self.add_review("E", 5)
        self.add_review("F", 0)
        self.add_review("G", 4)
        self.add_review("H", 1, created="2017-01-31 00:00:00", answer="2017-02-06 12:00:00")
        self.add_review("BEFORE", 1)
        self.add_review("AFTER", 1, created="2018-08-04 00:00:00", answer="2018-08-04 12:00:00")
        self.add_review("CANCELED", 1)
        self.add_review("NO_ITEMS", 2)
        self.db.commit()
        for statement in statements(PROJECT / "sql/02_cleaning.sql"):
            self.db.execute(statement)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def add_order(self, order_id, customer="C1", purchase="2017-02-01 10:00:00",
                  actual="2017-02-03 18:00:00", promised="2017-02-03 00:00:00",
                  status="delivered", prices=("10.00",)):
        self.db.execute("INSERT INTO orders VALUES (?, ?, ?, ?, '', '', ?, ?)",
                        (order_id, customer, status, purchase, actual, promised))
        self.db.executemany("INSERT INTO order_items VALUES (?, ?, 'P', 'S', ?, ?, '0.00')", [
            (order_id, str(index), purchase, price) for index, price in enumerate(prices, 1)
        ])

    def add_review(self, order_id, score, review_id=None, created="2017-02-04 00:00:00",
                   answer="2017-02-04 12:00:00"):
        self.db.execute("INSERT INTO order_reviews VALUES (?, ?, ?, '', '', ?, ?)",
                        (review_id or "R_" + order_id, order_id, str(score), created, answer))

    def results(self):
        return result_sets(self.db, PROJECT / "sql/05_customer_analysis.sql")

    def clear_orders(self):
        for table in ("orders", "order_items", "order_payments", "order_reviews"):
            self.db.execute("DELETE FROM " + table)

    def test_score_distribution_keeps_missing_reviews_separate(self):
        rows = self.results()["review_distribution"]
        self.assertEqual([row["review_score"] for row in rows], [1, 2, 3, 4, 5, None])
        self.assertEqual([row["sales_orders"] for row in rows], [1, 1, 1, 1, 1, 3])
        self.assertEqual(rows[0]["share_of_sales_pct"], 12.5)
        self.assertEqual(rows[0]["share_of_reviewed_pct"], 20.0)
        self.assertEqual(rows[-1]["share_of_sales_pct"], 37.5)
        self.assertIsNone(rows[-1]["share_of_reviewed_pct"])
        self.assertEqual((rows[0]["total_sales_orders"], rows[0]["total_reviewed_orders"],
                          rows[0]["total_missing_review_orders"], rows[0]["review_coverage_pct"]),
                         (8, 5, 3, 62.5))

    def test_items_payments_and_review_history_do_not_multiply_orders(self):
        results = self.results()
        person = results["customer_spending"][0]
        self.assertEqual((person["customer_unique_id"], person["sales_orders"],
                          person["product_sales_cents"], person["average_order_value"]),
                         ("PERSON1", 2, 5030, 25.15))
        self.assertEqual((person["reviewed_orders"], person["average_review_score"]), (2, 2.0))
        summary = results["repeat_customers"][0]
        self.assertEqual((summary["total_sales_orders"], summary["total_product_sales_cents"]),
                         (8, 11030))

    def test_latest_valid_review_and_id_tie_break_are_used(self):
        selected = self.db.execute("SELECT * FROM v_order_review WHERE order_id='A'").fetchone()
        self.assertEqual((selected["review_id"], selected["review_score"]), ("A_a", 3))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM order_reviews WHERE order_id='A'")
                         .fetchone()[0], 4)
        score_three = self.results()["review_distribution"][2]
        self.assertEqual(score_three["sales_orders"], 1)
        # A later valid response changes the selected score without adding an order.
        self.add_review("A", 4, review_id="A_new", created="2017-02-06 00:00:00",
                        answer="2017-02-06 12:00:00")
        rows = self.results()["review_distribution"]
        self.assertEqual((rows[2]["sales_orders"], rows[3]["sales_orders"]), (0, 2))
        self.assertEqual(rows[0]["total_sales_orders"], 8)

    def test_zero_score_and_invalid_chronology_are_missing_not_low_scores(self):
        selected = self.db.execute("SELECT order_id FROM v_order_review WHERE order_id IN ('F','H')")
        self.assertEqual(selected.fetchall(), [])
        self.add_review("D", 1, review_id="D_before_purchase", created="2017-02-01 00:00:00",
                        answer="2017-02-01 09:00:00")
        self.add_review("D", 2, review_id="D_before_creation", created="2017-02-05 00:00:00",
                        answer="2017-02-04 12:00:00")
        rows = self.results()["review_distribution"]
        self.assertEqual((rows[0]["sales_orders"], rows[1]["sales_orders"],
                          rows[-1]["sales_orders"]), (1, 1, 3))

    def test_delivery_review_denominators_and_pre_delivery_context(self):
        on_time, late = self.results()["delivery_reviews"]
        self.assertEqual((on_time["delivery_group"], late["delivery_group"]), ("on_time", "late"))
        self.assertEqual((on_time["sales_orders"], on_time["reviewed_orders"],
                          on_time["missing_review_orders"], on_time["review_coverage_pct"]),
                         (4, 2, 2, 50.0))
        self.assertEqual((on_time["review_score_sum"], on_time["average_review_score"],
                          on_time["low_score_orders"], on_time["low_score_pct"]), (5, 2.5, 1, 50.0))
        self.assertEqual((late["sales_orders"], late["reviewed_orders"], late["low_score_pct"],
                          late["pre_delivery_review_orders"]), (2, 1, 100.0, 1))
        self.assertEqual(on_time["pre_delivery_review_orders"], 0)

    def test_missing_or_backwards_delivery_dates_do_not_remove_valid_reviews(self):
        flags = [tuple(row) for row in self.db.execute(
            "SELECT sales_eligible, delivery_eligible, review_eligible FROM v_order_analysis "
            "WHERE order_id IN ('E', 'G') ORDER BY order_id")]
        self.assertEqual(flags, [(1, 0, 1), (1, 0, 1)])
        results = self.results()
        self.assertEqual(results["review_distribution"][0]["total_reviewed_orders"], 5)
        self.assertEqual(sum(row["reviewed_orders"] for row in results["delivery_reviews"]), 3)

    def test_repeat_identity_same_time_orders_and_observation_boundaries(self):
        row = self.results()["repeat_customers"][0]
        self.assertEqual((row["period_start"], row["period_end_exclusive"]),
                         ("2017-02-01", "2018-08-01"))
        self.assertEqual((row["total_customers"], row["one_time_customers"],
                          row["repeat_customers"], row["repeat_customer_pct"]), (7, 6, 1, 14.29))
        self.assertEqual((row["one_time_customer_orders"], row["repeat_customer_orders"],
                          row["one_time_product_sales_cents"], row["repeat_product_sales_cents"]),
                         (6, 2, 6000, 5030))
        self.assertEqual((row["repeat_order_share_pct"], row["repeat_sales_share_pct"]), (25.0, 45.6))
        person = self.results()["customer_spending"][0]
        self.assertEqual(person["first_purchase_timestamp"], person["last_purchase_timestamp"])
        # PERSON2 has only one eligible order; its other orders are excluded.
        other = next(r for r in self.results()["customer_spending"] if r["customer_unique_id"] == "PERSON2")
        self.assertEqual(other["sales_orders"], 1)

    def test_regions_keep_unknown_state_and_use_reviewed_denominators(self):
        rows = self.results()["regional_reviews"]
        self.assertEqual([row["customer_state"] for row in rows], ["RJ", "SP", "MG", "Unknown state"])
        states = {row["customer_state"]: row for row in rows}
        self.assertEqual((states["SP"]["sales_orders"], states["SP"]["reviewed_orders"],
                          states["SP"]["low_score_pct"], states["SP"]["review_coverage_pct"]),
                         (3, 2, 50.0, 66.67))
        self.assertEqual(states["Unknown state"]["missing_review_orders"], 1)
        self.assertIsNone(states["Unknown state"]["average_review_score"])
        self.assertIsNone(states["Unknown state"]["low_score_pct"])

    def test_top_twenty_limit_follows_full_customer_aggregation(self):
        self.clear_orders()
        for index in range(21):
            customer = f"U{index:02d}"
            self.db.execute("INSERT INTO customers VALUES (?, ?, '01234', 'city', 'SP')",
                            (customer, customer))
            self.add_order(customer, customer, prices=("100.00",))
        self.add_order("SMALL1", "C1", prices=("60.00",))
        self.add_order("SMALL2", "C2", prices=("60.00",))
        results = self.results()
        rows = results["customer_spending"]
        self.assertEqual(len(rows), 20)
        self.assertEqual((rows[0]["customer_unique_id"], rows[0]["product_sales_cents"]),
                         ("PERSON1", 12000))
        self.assertEqual(rows[-1]["customer_unique_id"], "U18")
        self.assertEqual(results["repeat_customers"][0]["total_customers"], 22)
        self.assertEqual(results["repeat_customers"][0]["total_sales_orders"], 23)

    def test_empty_population_retains_score_and_delivery_groups(self):
        self.clear_orders()
        results = self.results()
        self.assertEqual(len(results["review_distribution"]), 6)
        for row in results["review_distribution"]:
            self.assertEqual(row["sales_orders"], 0)
            self.assertIsNone(row["share_of_sales_pct"])
            self.assertIsNone(row["share_of_reviewed_pct"])
        self.assertEqual(len(results["delivery_reviews"]), 2)
        for row in results["delivery_reviews"]:
            self.assertEqual((row["sales_orders"], row["reviewed_orders"], row["review_score_sum"]), (0, 0, 0))
            self.assertIsNone(row["average_review_score"])
            self.assertIsNone(row["low_score_pct"])
        row = results["repeat_customers"][0]
        self.assertEqual((row["total_customers"], row["total_product_sales_cents"]), (0, 0))
        for field in ("repeat_customer_pct", "repeat_order_share_pct", "repeat_sales_share_pct"):
            self.assertIsNone(row[field])
        self.assertEqual(results["customer_spending"], [])
        self.assertEqual(results["regional_reviews"], [])

    def test_unreviewed_zero_value_sale_has_zero_coverage_but_no_mean(self):
        self.clear_orders()
        self.add_order("ZERO", prices=("0.00",))
        results = self.results()
        on_time, late = results["delivery_reviews"]
        self.assertEqual((on_time["sales_orders"], on_time["reviewed_orders"],
                          on_time["review_coverage_pct"]), (1, 0, 0.0))
        self.assertIsNone(on_time["average_review_score"])
        self.assertIsNone(on_time["low_score_pct"])
        self.assertEqual(late["sales_orders"], 0)
        self.assertIsNone(late["review_coverage_pct"])
        self.assertEqual(results["customer_spending"][0]["average_order_value"], 0.0)
        self.assertIsNone(results["repeat_customers"][0]["repeat_sales_share_pct"])
        self.assertEqual(results["repeat_customers"][0]["repeat_customer_pct"], 0.0)

    def test_exact_halfway_score_rate_and_money_round_up(self):
        self.clear_orders()
        # 116 / 32 = 3.625; one low score out of 32 is 3.125%.
        scores = [1] + [4] * 22 + [3] * 9
        for index, score in enumerate(scores):
            order = f"ROUND{index:02d}"
            self.add_order(order, prices=("1.16" if index == 0 else "1.00",))
            self.add_review(order, score)
        results = self.results()
        self.assertEqual(results["review_distribution"][0]["share_of_reviewed_pct"], 3.13)
        for name in ("delivery_reviews", "regional_reviews"):
            self.assertEqual(results[name][0]["average_review_score"], 3.63)
            self.assertEqual(results[name][0]["low_score_pct"], 3.13)
        customer = results["customer_spending"][0]
        self.assertEqual(customer["average_review_score"], 3.63)
        # 32.16 / 32 = 1.005; display half-up as 1.01, keeping cents exact.
        self.assertEqual(customer["product_sales_cents"], 3216)
        self.assertEqual(customer["average_order_value"], 1.01)


if __name__ == "__main__":
    unittest.main()
