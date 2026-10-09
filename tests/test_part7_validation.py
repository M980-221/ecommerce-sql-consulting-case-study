"""Small raw fixtures for reconciliation, missing data and unsafe join checks."""
from pathlib import Path
import sqlite3
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from prepare_part3 import result_sets, statements
from validation_checks import calculate_raw


class Part7ValidationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript((PROJECT / "sql/01_setup.sql").read_text())
        self.db.execute("INSERT INTO customers VALUES ('C', 'PERSON', '01234', 'city', 'sp')")
        self.db.execute("INSERT INTO products VALUES ('P', '', '', '', '', '', '', '', '')")
        self.db.execute("INSERT INTO sellers VALUES ('S', '01234', 'city', 'sp')")
        self.add_order("A", items=[("10.10", "1.20")] * 3,
                       payments=[("credit_card", "20.00"), ("voucher", "13.90")])
        self.add_order("ONE_PLUS", payments=[("credit_card", "11.01")])
        self.add_order("ONE_MINUS", payments=[("credit_card", "10.99")])
        self.add_order("ABOVE", items=[("20.00", "2.00")],
                       payments=[("voucher", "4.30"), ("credit_card", "20.00")])
        self.add_order("BELOW", items=[("30.00", "3.00")], payments=[("boleto", "31.00")])
        self.add_order("NO_ITEMS", items=[], payments=[("credit_card", "7.00")])
        self.add_order("NO_PAYMENT", items=[("5.00", "0.50")], payments=[], actual="")
        self.add_order("NO_BOTH", items=[], payments=[])
        self.add_order("ZERO", items=[("0.00", "0.00")], payments=[("voucher", "0.00")])
        self.add_order("OUTSIDE", purchase="2018-08-01 00:00:00", actual="2018-08-03 18:00:00",
                       promised="2018-08-03 00:00:00")
        self.add_order("CANCELED", status="canceled")
        self.add_review("A", "OLD", 1)
        self.add_review("A", "NEW", 5, answer="2017-02-05 12:00:00")
        self.add_review("ONE_PLUS", "GOOD", 2)
        self.add_review("ONE_MINUS", "BAD", 1, created="2017-01-31 00:00:00")
        self.db.commit()
        for statement in statements(PROJECT / "sql/02_cleaning.sql"):
            self.db.execute(statement)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def add_order(self, order_id, items=None, payments=None, purchase="2017-02-01 10:00:00",
                  actual="2017-02-03 18:00:00", promised="2017-02-03 00:00:00", status="delivered"):
        items = [("10.00", "1.00")] if items is None else items
        payments = [("credit_card", "11.00")] if payments is None else payments
        self.db.execute("INSERT INTO orders VALUES (?, 'C', ?, ?, '', '', ?, ?)",
                        (order_id, status, purchase, actual, promised))
        self.db.executemany("INSERT INTO order_items VALUES (?, ?, 'P', 'S', ?, ?, ?)", [
            (order_id, str(index), purchase, price, freight)
            for index, (price, freight) in enumerate(items, 1)
        ])
        self.db.executemany("INSERT INTO order_payments VALUES (?, ?, ?, '1', ?)", [
            (order_id, str(index), method, value) for index, (method, value) in enumerate(payments, 1)
        ])

    def add_review(self, order_id, review_id, score, created="2017-02-04 00:00:00",
                   answer="2017-02-04 12:00:00"):
        self.db.execute("INSERT INTO order_reviews VALUES (?, ?, ?, '', '', ?, ?)",
                        (review_id, order_id, str(score), created, answer))

    def checked_reports(self):
        sql = result_sets(self.db, PROJECT / "sql/06_validation.sql")
        self.assertEqual(sql, calculate_raw(self.db)["reports"])
        return sql

    def test_all_groups_match_independent_raw_calculation(self):
        reports = self.checked_reports()
        summary = {row["reconciliation_group"]: row for row in reports["reconciliation_summary"]}
        self.assertEqual({name: row["orders"] for name, row in summary.items()}, {
            "missing_items_and_payments": 1, "missing_items": 1, "missing_payments": 1,
            "exact_match": 4, "one_cent_difference": 2, "payment_below_expected": 1,
            "payment_above_expected": 1,
        })
        self.assertEqual(summary["one_cent_difference"]["net_difference_cents"], 0)
        self.assertEqual(summary["one_cent_difference"]["absolute_difference_cents"], 2)
        self.assertEqual(summary["payment_above_expected"]["net_difference_cents"], 230)
        self.assertEqual(summary["payment_below_expected"]["net_difference_cents"], -200)
        population = reports["population_validation"][0]
        self.assertEqual((population["source_orders"], population["model_rows"],
                          population["reporting_period_orders"], population["sales_orders"]), (11, 11, 10, 7))

    def test_missing_sides_stay_null_and_known_zero_stays_comparable(self):
        rows = {row["reconciliation_group"]: row for row in self.checked_reports()["reconciliation_summary"]}
        self.assertIsNone(rows["missing_items"]["expected_payment_cents"])
        self.assertEqual(rows["missing_items"]["payment_cents"], 700)
        self.assertEqual(rows["missing_payments"]["expected_payment_cents"], 550)
        self.assertIsNone(rows["missing_payments"]["payment_cents"])
        for group in ("missing_items", "missing_payments", "missing_items_and_payments"):
            self.assertIsNone(rows[group]["net_difference_cents"])
            self.assertIsNone(rows[group]["min_difference_cents"])
        self.assertEqual(rows["exact_match"]["orders"], 4)

    def test_three_items_two_payments_make_six_unsafe_rows(self):
        for table in ("order_reviews", "order_payments", "order_items", "orders"):
            self.db.execute("DELETE FROM " + table + " WHERE order_id != 'A'")
        row = self.checked_reports()["join_fanout_summary"][0]
        self.assertEqual((row["matched_orders"], row["correct_item_rows"],
                          row["correct_payment_rows"], row["unsafe_join_rows"]), (1, 3, 2, 6))
        self.assertEqual((row["correct_product_sales_cents"], row["unsafe_product_sales_cents"]), (3030, 6060))
        self.assertEqual((row["correct_freight_cents"], row["unsafe_freight_cents"]), (360, 720))
        self.assertEqual((row["correct_payment_cents"], row["unsafe_payment_cents"],
                          row["payment_overstatement_cents"]), (3390, 10170, 6780))

    def test_exception_details_are_sorted_and_patterns_preserve_observed_flags(self):
        self.db.execute("INSERT INTO order_payments VALUES ('ABOVE', '3', 'voucher', '1', '0.00')")
        reports = self.checked_reports()
        rows = reports["reconciliation_exceptions"]
        self.assertEqual([row["order_id"] for row in rows], ["ABOVE", "BELOW", "ONE_MINUS", "ONE_PLUS"])
        above = rows[0]
        self.assertEqual((above["difference_band"], above["difference_direction"], above["payment_methods"]),
                         ("over_one_cent", "above", "credit_card|voucher"))
        self.assertEqual((above["has_voucher"], above["zero_payment_components"], above["payment_count"]), (1, 1, 3))
        pattern = next(row for row in reports["reconciliation_patterns"]
                       if row["difference_band"] == "over_one_cent" and row["difference_direction"] == "above")
        self.assertEqual((pattern["multiple_payments"], pattern["multiple_items"], pattern["zero_payment_orders"]),
                         (1, 0, 1))

    def test_missingness_separates_absent_and_invalid_reviews(self):
        rows = {row["population"]: row for row in self.checked_reports()["missingness_by_population"]}
        self.assertEqual((rows["full_source"]["orders_without_source_review"],
                          rows["full_source"]["orders_without_selected_review"],
                          rows["full_source"]["orders_with_only_invalid_reviews"]), (8, 9, 1))
        self.assertEqual((rows["sales"]["orders"], rows["sales"]["orders_without_actual_delivery_date"]), (7, 1))
        self.assertEqual(rows["reviewed_sales"]["orders"], 2)
        self.assertEqual(rows["reviewed_sales"]["orders_without_selected_review"], 0)
        evidence = calculate_raw(self.db)["evidence"]["review_selection"]
        self.assertEqual(evidence, {"source_rows": 4, "invalid_rows": 1, "valid_rows": 3,
                                    "selected_rows": 2, "additional_valid_rows": 1})

    def test_independent_checker_detects_a_duplicated_prepared_order(self):
        expected = calculate_raw(self.db)["reports"]
        self.db.execute("CREATE TEMP VIEW v_order_analysis AS SELECT * FROM main.v_order_analysis "
                        "UNION ALL SELECT * FROM main.v_order_analysis WHERE order_id = 'A'")
        observed = result_sets(self.db, PROJECT / "sql/06_validation.sql")
        self.assertEqual(observed["population_validation"][0]["model_rows"], 12)
        self.assertEqual(observed["population_validation"][0]["model_distinct_orders"], 11)
        self.assertNotEqual(observed["population_validation"], expected["population_validation"])
        self.assertEqual(calculate_raw(self.db)["reports"], expected)

    def test_replaced_order_id_is_detected_with_counts_and_money_unchanged(self):
        expected = calculate_raw(self.db)["reports"]["population_validation"][0]
        self.db.execute("CREATE TEMP TABLE v_order_analysis AS SELECT * FROM main.v_order_analysis")
        self.db.execute("UPDATE temp.v_order_analysis SET order_id='FAKE_ORDER' WHERE order_id='A'")
        observed = result_sets(self.db, PROJECT / "sql/06_validation.sql")["population_validation"][0]
        changed_fields = {key for key in expected if observed[key] != expected[key]}
        self.assertEqual(changed_fields, {
            "source_orders_missing_from_model", "model_orders_missing_from_source",
        })
        self.assertEqual(observed["source_orders_missing_from_model"], 1)
        self.assertEqual(observed["model_orders_missing_from_source"], 1)
        self.assertNotEqual(observed, expected)

    def test_raw_checker_rejects_duplicate_composite_keys(self):
        self.db.execute("INSERT INTO order_payments SELECT * FROM order_payments WHERE order_id='BELOW'")
        with self.assertRaisesRegex(ValueError, "Duplicate order_payments key"):
            calculate_raw(self.db)

    def test_raw_checker_rejects_orphan_rows(self):
        self.db.execute("INSERT INTO order_items VALUES ('ORPHAN', '1', 'P', 'S', '2017-02-01 10:00:00', '1.00', '0.00')")
        with self.assertRaisesRegex(ValueError, "Unmatched items/orders"):
            calculate_raw(self.db)

    def test_decimal_values_do_not_create_artificial_cent_differences(self):
        self.add_order("DECIMAL", items=[("0.29", "0.07"), ("0.57", "0.13")],
                       payments=[("credit_card", "1.06")])
        reports = self.checked_reports()
        self.assertNotIn("DECIMAL", [row["order_id"] for row in reports["reconciliation_exceptions"]])
        exact = next(row for row in reports["reconciliation_summary"] if row["reconciliation_group"] == "exact_match")
        self.assertEqual(exact["orders"], 5)

    def test_empty_source_retains_groups_without_inventing_comparisons(self):
        for table in ("order_reviews", "order_payments", "order_items", "orders"):
            self.db.execute("DELETE FROM " + table)
        reports = self.checked_reports()
        self.assertEqual(reports["population_validation"][0]["model_rows"], 0)
        self.assertEqual(len(reports["reconciliation_summary"]), 7)
        for row in reports["reconciliation_summary"]:
            self.assertEqual(row["orders"], 0)
            self.assertIsNone(row["expected_payment_cents"])
            self.assertIsNone(row["net_difference_cents"])
        self.assertEqual(reports["reconciliation_exceptions"], [])
        self.assertEqual(reports["reconciliation_patterns"], [])
        self.assertEqual(reports["join_fanout_summary"][0]["unsafe_join_rows"], 0)
        self.assertEqual([row["orders"] for row in reports["missingness_by_population"]], [0] * 5)


if __name__ == "__main__":
    unittest.main()
