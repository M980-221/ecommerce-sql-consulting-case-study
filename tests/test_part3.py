"""Small examples that catch wrong totals, dates, missingness and review choices."""
from pathlib import Path
import sqlite3
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from prepare_part3 import result_sets, statements, validate


class Part3Tests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript((PROJECT / "sql/01_setup.sql").read_text())
        self.db.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", [
            ("C1", "PERSON1", "01234", "sao paulo", "sp"),
            ("C2", "PERSON1", "01234", "sao paulo", "sp"),
        ])
        self.db.execute("INSERT INTO sellers VALUES ('S1', '01234', 'sao paulo', 'sp')")
        self.db.execute("INSERT INTO products VALUES ('P1', '', '', '', '', '', '', '', '')")
        self.db.execute("INSERT INTO category_translation VALUES ('livros', 'books')")
        self.db.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
            (order, customer, "delivered", "2017-02-01 10:00:00", "2017-02-01 10:30:00",
             "2017-02-01 15:00:00", "2017-02-02 18:00:00", "2017-02-02 00:00:00")
            for order, customer in [("O1", "C1"), ("O2", "C2")]
        ])
        self.db.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?)", [
            ("O1", str(n), "P1", "S1", "2017-02-03 00:00:00", "10.10", "1.20")
            for n in range(1, 4)
        ])
        self.db.executemany("INSERT INTO order_payments VALUES (?, ?, ?, ?, ?)", [
            ("O1", "1", "credit_card", "1", "20.00"),
            ("O1", "2", "voucher", "1", "13.90"),
        ])
        self.db.executemany("INSERT INTO order_reviews VALUES (?, ?, ?, ?, ?, ?, ?)", [
            ("R1", "O1", "1", "", " earlier ", "2017-02-03 00:00:00", "2017-02-03 12:00:00"),
            ("R2", "O1", "5", "", " later ", "2017-02-04 00:00:00", "2017-02-04 12:00:00"),
        ])

    def tearDown(self):
        self.db.close()

    def build(self):
        self.db.commit()
        self.db.execute("BEGIN")
        try:
            for sql in statements(PROJECT / "sql/02_cleaning.sql"):
                self.db.execute(sql)
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def order(self, order_id="O1"):
        return self.db.execute("SELECT * FROM v_order_analysis WHERE order_id = ?", (order_id,)).fetchone()

    def test_three_items_two_payments_do_not_multiply_money(self):
        self.build()
        row = self.order()
        self.assertEqual((row["item_count"], row["payment_count"]), (3, 2))
        self.assertEqual((row["product_sales_cents"], row["freight_cents"], row["payment_cents"]),
                         (3030, 360, 3390))
        self.assertEqual(row["payment_difference_cents"], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM v_order_analysis").fetchone()[0], 2)

    def test_missing_children_are_retained_without_inventing_zero_money(self):
        self.build()
        row = self.order("O2")
        self.assertEqual(row["payment_count"], 0)
        self.assertIsNone(row["payment_cents"])
        self.assertIsNone(row["review_score"])
        self.assertEqual(row["sales_eligible"], 0)

    def test_review_rule_selects_latest_response(self):
        self.build()
        self.assertEqual(self.order()["review_id"], "R2")
        self.assertEqual(self.order()["review_score"], 5)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM order_reviews").fetchone()[0], 2)

    def test_latest_invalid_review_does_not_replace_a_valid_one(self):
        self.db.execute("INSERT INTO order_reviews VALUES ('R3', 'O1', '2', '', '', '2017-01-31 00:00:00', '2017-02-05 12:00:00')")
        self.build()
        self.assertEqual(self.order()["review_id"], "R2")
        self.assertEqual(self.db.execute("SELECT review_is_valid FROM v_review_candidates WHERE review_id='R3'").fetchone()[0], 0)

    def test_review_tie_has_a_stable_id_tiebreaker(self):
        self.db.execute("INSERT INTO order_reviews VALUES ('R0', 'O1', '3', '', '', '2017-02-04 00:00:00', '2017-02-04 12:00:00')")
        self.build()
        self.assertEqual(self.order()["review_id"], "R0")

    def test_review_id_can_appear_on_different_orders(self):
        self.db.execute("INSERT INTO order_reviews VALUES ('R1', 'O2', '4', '', '', '2017-02-03 00:00:00', '2017-02-03 12:00:00')")
        self.build()
        self.assertEqual(self.order("O2")["review_id"], "R1")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM v_order_review").fetchone()[0], 2)

    def test_promised_calendar_day_is_on_time(self):
        self.build()
        self.assertEqual(self.order()["is_late"], 0)
        self.assertEqual(self.order()["delay_days"], 0)
        self.db.execute("UPDATE orders SET order_delivered_customer_date='2017-02-03 00:00:00' WHERE order_id='O1'")
        self.assertEqual(self.order()["is_late"], 1)
        self.assertEqual(self.order()["delay_days"], 1)

    def test_missing_delivery_date_only_excludes_delivery_metrics(self):
        self.db.execute("UPDATE orders SET order_delivered_customer_date='' WHERE order_id='O1'")
        self.build()
        row = self.order()
        self.assertEqual(row["sales_eligible"], 1)
        self.assertEqual(row["delivery_eligible"], 0)
        self.assertIsNone(row["is_late"])

    def test_category_gaps_keep_products(self):
        self.db.execute("INSERT INTO products VALUES ('P2', 'pc_gamer', '', '', '', '', '', '', '')")
        self.build()
        labels = dict(self.db.execute("SELECT product_id, category_label FROM v_products_labeled"))
        self.assertEqual(labels, {"P1": "Unknown category", "P2": "Untranslated: pc_gamer"})

    def test_bad_number_aborts_and_restores_previous_views(self):
        self.build()
        self.db.execute("UPDATE order_items SET price='12oops' WHERE order_item_id='1'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.build()
        self.assertIsNotNone(self.db.execute("SELECT name FROM sqlite_master WHERE name='v_order_analysis'").fetchone())

    def test_impossible_calendar_date_aborts(self):
        self.db.execute("UPDATE orders SET order_delivered_customer_date='2017-02-30 10:00:00' WHERE order_id='O1'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.build()

    def test_blanks_and_postal_codes(self):
        self.build()
        product = self.db.execute("SELECT * FROM v_clean_products").fetchone()
        self.assertIsNone(product["product_weight_g"])
        self.assertEqual(self.db.execute("SELECT customer_zip_code_prefix FROM v_clean_customers LIMIT 1").fetchone()[0], "01234")
        self.assertEqual(self.db.execute("SELECT review_comment_message FROM order_reviews WHERE review_id='R2'").fetchone()[0], " later ")
        self.assertEqual(self.db.execute("SELECT review_comment_message FROM v_clean_order_reviews WHERE review_id='R2'").fetchone()[0], "later")

    def test_reporting_window_has_an_exclusive_end(self):
        self.db.execute("UPDATE orders SET order_purchase_timestamp='2018-08-01 00:00:00' WHERE order_id='O2'")
        self.build()
        self.assertEqual(self.order()["in_reporting_period"], 1)
        self.assertEqual(self.order("O2")["in_reporting_period"], 0)

    def test_all_validation_gates_run_on_small_data(self):
        self.build()
        profile = result_sets(self.db, PROJECT / "sql/02_profile.sql")
        observed = result_sets(self.db, PROJECT / "sql/02_check_cleaning.sql")
        self.assertTrue(all(g["status"] == "PASS" for g in validate(self.db, profile, observed)))


if __name__ == "__main__":
    unittest.main()
