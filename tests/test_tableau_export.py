"""Tableau CSV semantics, using the same small raw fixture as the first export."""
import csv
import io
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from export_tableau import build_exports, csv_text, ORDER_FIELDS, CATEGORY_FIELDS
import test_part8_export as fixtures


class TableauExportTests(unittest.TestCase):
    # Reuse its raw orders and Part 3/7 setup, without inheriting its tests.
    setUp = fixtures.Part8ExportTests.setUp
    tearDown = fixtures.Part8ExportTests.tearDown
    add_order = fixtures.Part8ExportTests.add_order

    def test_explicit_keys_dates_and_customer_identity(self):
        reports, _, audit = build_exports(self.db)
        rows = reports["orders"]
        self.assertEqual([row["order_key"] for row in rows], [1, 2, 3, 4, 5])
        self.assertEqual([row["purchase_month"] for row in rows[:2]], ["2017-02-01", "2017-03-01"])
        self.assertEqual([row["buyer_state"] for row in rows[:2]], ["SP", "RJ"])
        self.assertEqual(rows[0]["customer_key"], rows[1]["customer_key"])
        self.assertNotEqual(rows[0]["customer_key"], rows[2]["customer_key"])
        self.assertEqual(audit["tableau_cells_checked"], 5 * 14 + 5 * 11)
        for source_id in ("ORDER_A", "CUSTOMER_A", "PERSISTENT_REPEAT", "REVIEW_A", "Private review text"):
            self.assertNotIn(source_id, json.dumps(reports))

    def test_review_eligibility_and_positive_delay_stay_separate(self):
        reports, _, _ = build_exports(self.db)
        rows = reports["orders"]
        self.assertIsNone(rows[0]["positive_delay_days"])
        self.assertEqual((rows[1]["positive_delay_days"], rows[1]["review_before_delivery"]), (2, 1))
        self.assertEqual((rows[2]["sales_eligible"], rows[2]["delivery_eligible"], rows[2]["review_eligible"]), (1, 0, 1))
        self.assertIsNone(rows[2]["delivery_seconds"])
        self.assertEqual((rows[3]["review_score"], rows[3]["review_eligible"]), (3, 0))
        self.assertEqual((rows[4]["sales_eligible"], rows[4]["delivery_eligible"]), (0, 1))
        self.assertIsNone(rows[4]["product_value_cents"])

    def test_category_csv_has_aggregates_and_nullable_delivery_only_value(self):
        reports, _, _ = build_exports(self.db)
        rows = reports["categories"]
        books = next(row for row in rows if row["order_key"] == 1 and row["category"] == "books")
        self.assertEqual((books["product_value_cents"], books["item_count"]), (2020, 2))
        self.assertEqual((books["delivery_eligible"], books["is_late"]), (1, 0))
        self.assertIsNone(books["positive_delay_days"])
        missing = next(row for row in rows if row["order_key"] == 5)
        self.assertEqual((missing["category"], missing["sales_eligible"], missing["item_count"]), ("Unknown category", 0, 0))
        raw = list(csv.DictReader(io.StringIO(csv_text(rows, CATEGORY_FIELDS))))
        raw_missing = next(row for row in raw if row["order_key"] == "5")
        self.assertEqual(raw_missing["product_value_cents"], "")
        self.assertEqual(raw_missing["item_count"], "0")
        self.assertEqual(raw_missing["purchase_month"], "2017-04-01")

    def test_empty_sources_still_have_the_correct_csv_headers(self):
        for table in ("order_reviews", "order_items", "orders"):
            self.db.execute("DELETE FROM " + table)
        reports, _, audit = build_exports(self.db)
        self.assertEqual(reports, {"orders": [], "categories": []})
        self.assertEqual(csv_text([], ORDER_FIELDS), ",".join(ORDER_FIELDS) + "\n")
        self.assertEqual(csv_text([], CATEGORY_FIELDS), ",".join(CATEGORY_FIELDS) + "\n")
        self.assertEqual(audit["tableau_cells_checked"], 0)


if __name__ == "__main__":
    unittest.main()
