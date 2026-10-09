"""Export fixtures verify browser indexes without flattening order relationships."""
import json
from pathlib import Path
import sqlite3
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from export_dashboard import build_payload
from prepare_part3 import statements


class Part8ExportTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript((PROJECT / "sql/01_setup.sql").read_text())
        self.db.executemany("INSERT INTO customers VALUES (?, ?, '01234', 'Private city', ?)", [
            ("CUSTOMER_A", "PERSISTENT_REPEAT", "sp"),
            ("CUSTOMER_B", "PERSISTENT_REPEAT", "rj"),
            ("CUSTOMER_C", "PERSISTENT_SINGLE", "mg"),
        ])
        self.db.executemany("INSERT INTO products VALUES (?, ?, '', '', '', '', '', '', '')", [
            ("PRODUCT_B", "livros"), ("PRODUCT_H", "casa"),
        ])
        self.db.executemany("INSERT INTO category_translation VALUES (?, ?)", [("livros", "books"), ("casa", "home")])
        self.db.execute("INSERT INTO sellers VALUES ('SELLER', '01234', 'Private city', 'sp')")
        # Deliberately insert March before February; export indexes use order IDs.
        self.add_order("ORDER_B", "CUSTOMER_B", "2017-03-01 10:00:00", "2017-03-05 18:00:00",
                       "2017-03-03 00:00:00", items=[("PRODUCT_B", "10.00")])
        self.add_order("ORDER_A", "CUSTOMER_A", "2017-02-01 10:00:00", "2017-02-03 18:00:00",
                       "2017-02-03 00:00:00", items=[("PRODUCT_B", "10.10"), ("PRODUCT_B", "10.10"), ("PRODUCT_H", "5.00")])
        self.add_order("ORDER_C", "CUSTOMER_C", "2017-02-01 10:00:00", "", "2017-02-03 00:00:00",
                       items=[("PRODUCT_H", "5.00")])
        self.add_order("ORDER_D", "CUSTOMER_A", "2017-02-01 10:00:00", "2017-02-03 18:00:00",
                       "2017-02-03 00:00:00", items=[("PRODUCT_B", "20.00")], status="canceled")
        self.add_order("ORDER_E", "CUSTOMER_A", "2017-04-01 10:00:00", "2017-04-03 18:00:00",
                       "2017-04-03 00:00:00", items=[])
        self.add_order("ORDER_OUTSIDE", "CUSTOMER_A", "2018-08-01 00:00:00", "2018-08-03 18:00:00",
                       "2018-08-03 00:00:00", items=[("PRODUCT_B", "999.99")])
        self.db.executemany("INSERT INTO order_reviews VALUES (?, ?, ?, 'Private title', 'Private review text', ?, ?)", [
            ("REVIEW_A", "ORDER_A", "4", "2017-02-04 00:00:00", "2017-02-04 12:00:00"),
            ("REVIEW_B", "ORDER_B", "1", "2017-03-02 00:00:00", "2017-03-02 12:00:00"),
            ("REVIEW_C", "ORDER_C", "5", "2017-02-04 00:00:00", "2017-02-04 12:00:00"),
            ("REVIEW_D", "ORDER_D", "3", "2017-02-04 00:00:00", "2017-02-04 12:00:00"),
        ])
        self.db.commit()
        for filename in ("sql/02_cleaning.sql", "sql/07_reporting_views.sql"):
            for statement in statements(PROJECT / filename):
                self.db.execute(statement)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def add_order(self, order_id, customer, purchase, actual, promised, items, status="delivered"):
        self.db.execute("INSERT INTO orders VALUES (?, ?, ?, ?, '', '', ?, ?)",
                        (order_id, customer, status, purchase, actual, promised))
        self.db.executemany("INSERT INTO order_items VALUES (?, ?, ?, 'SELLER', ?, ?, '0.00')", [
            (order_id, str(index), product, purchase, price)
            for index, (product, price) in enumerate(items, 1)
        ])

    def test_customer_indexes_stay_stable_across_months_and_buyer_states(self):
        payload, audit = build_payload(self.db)
        fields = {name: index for index, name in enumerate(payload["fields"])}
        first, second = payload["orders"][:2]
        self.assertEqual((first[fields["month"]], second[fields["month"]]), (0, 1))
        self.assertEqual(payload["states"][first[fields["state"]]], "SP")
        self.assertEqual(payload["states"][second[fields["state"]]], "RJ")
        self.assertEqual(first[fields["customer"]], second[fields["customer"]])
        self.assertNotEqual(first[fields["customer"]], payload["orders"][2][fields["customer"]])
        self.assertEqual((payload["meta"]["customerCount"], audit["encoded_order_rows"]), (2, 5))

    def test_categories_keep_item_sums_and_distinct_delivery_memberships(self):
        payload, audit = build_payload(self.db)
        rows = payload["categories"]
        books = payload["categoryLabels"].index("books")
        home = payload["categoryLabels"].index("home")
        unknown = payload["categoryLabels"].index("Unknown category")
        self.assertIn([0, books, 2020, 2, 1], rows)
        self.assertIn([0, home, 500, 1, 1], rows)
        self.assertIn([4, unknown, None, 0, 1], rows)
        self.assertEqual(len({tuple(row[:2]) for row in rows}), len(rows))
        self.assertEqual(sum(row[2] for row in rows if row[0] == 0), 2520)
        self.assertEqual((len(rows), audit["encoded_cells_checked"]), (5, 85))

    def test_sales_delivery_and_selected_reviews_retain_different_eligibility(self):
        payload, _ = build_payload(self.db)
        orders = [dict(zip(payload["fields"], row)) for row in payload["orders"]]
        self.assertEqual((orders[0]["deliverySeconds"], orders[0]["late"]), (201600, 0))
        self.assertEqual((orders[1]["late"], orders[1]["delayDays"], orders[1]["preDeliveryReview"]), (1, 2, 1))
        self.assertEqual((orders[2]["sales"], orders[2]["delivery"], orders[2]["reviewScore"]), (1, 0, 5))
        self.assertIsNone(orders[2]["deliverySeconds"])
        self.assertEqual((orders[3]["sales"], orders[3]["delivery"], orders[3]["reviewScore"]), (0, 0, 3))
        self.assertEqual((orders[4]["sales"], orders[4]["delivery"], orders[4]["salesCents"]), (0, 1, None))
        self.assertEqual(sum(row["sales"] for row in orders), 3)
        self.assertEqual(sum(row["salesCents"] for row in orders if row["sales"]), 4020)

    def test_payload_omits_raw_identifiers_and_unneeded_text(self):
        payload, _ = build_payload(self.db)
        text = json.dumps(payload)
        for private_value in ("CUSTOMER_A", "PERSISTENT_REPEAT", "ORDER_A", "PRODUCT_B", "REVIEW_A",
                              "Private city", "Private title", "Private review text", "01234"):
            self.assertNotIn(private_value, text)
        self.assertNotIn("2018-08", payload["months"])
        self.assertEqual(payload["meta"]["schemaVersion"], 1)

    def test_empty_period_preserves_filter_calendar_and_schema(self):
        self.db.execute("DELETE FROM order_reviews")
        self.db.execute("DELETE FROM order_items")
        self.db.execute("DELETE FROM orders")
        payload, audit = build_payload(self.db)
        self.assertEqual((payload["orders"], payload["categories"]), ([], []))
        self.assertEqual((payload["states"], payload["statuses"], payload["categoryLabels"]), ([], [], []))
        self.assertEqual(len(payload["months"]), 18)
        self.assertEqual((payload["months"][0], payload["months"][-1]), ("2017-02", "2018-07"))
        self.assertEqual(audit["encoded_cells_checked"], 0)
        self.assertEqual(payload["meta"]["customerCount"], 0)


if __name__ == "__main__":
    unittest.main()
