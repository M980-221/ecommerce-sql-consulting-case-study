#!/usr/bin/env python3
"""Export the validated reporting window as a compact, local JavaScript dataset.

The connection is read-only. Raw fingerprints are checked before exporting;
encoding is reversible and every encoded cell is checked against the SQL rows.
Published Part 4-7 counts and money provide additional reconciliation checks.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

from prepare_part3 import result_sets, source_fingerprints

PROJECT = Path(__file__).resolve().parents[1]
FIELDS = ("month", "state", "customer", "status", "salesCents", "sales", "delivery", "late",
          "deliverySeconds", "delayDays", "reviewScore", "preDeliveryReview")
CATEGORY_FIELDS = ("order", "category", "salesCents", "itemCount", "delivery")
MONTHS = tuple(f"{year}-{month:02d}" for year, months in ((2017, range(2, 13)), (2018, range(1, 8)))
               for month in months)
ORDER_SOURCE_FIELDS = ("purchase_month", "customer_state", "customer_unique_id", "order_status",
                       "product_sales_cents", "sales_eligible", "delivery_eligible", "is_late",
                       "delivery_seconds", "delay_days", "review_score", "pre_delivery_review")


def build_payload(connection):
    """Return (payload, audit); fixtures can call this without import metadata.

    Order indexes follow sorted source IDs. Customer indexes follow sorted
    persistent IDs across the whole window and stay stable when filters change.
    The raw identifiers are used only during encoding and are not published.
    """
    outputs = result_sets(connection, PROJECT / "sql/08_dashboard_export.sql")
    source_orders, source_categories = outputs["dashboard_orders"], outputs["dashboard_categories"]
    states = sorted({row["customer_state"] for row in source_orders})
    statuses = sorted({row["order_status"] for row in source_orders})
    customer_ids = {row["customer_unique_id"] for row in source_orders}
    if any(not isinstance(value, str) or not value for value in customer_ids):
        raise ValueError("Reporting orders contain a missing persistent customer ID")
    customers = sorted(customer_ids)
    labels = sorted({row["category_label"] for row in source_categories})
    order_ids = [row["order_id"] for row in source_orders]
    if len(order_ids) != len(set(order_ids)):
        raise ValueError("Reporting orders contain duplicate IDs")
    dictionaries = (MONTHS, states, customers, statuses)
    indexes = [{value: index for index, value in enumerate(values)} for values in dictionaries]
    order_index = {value: index for index, value in enumerate(order_ids)}
    category_index = {value: index for index, value in enumerate(labels)}
    orders = []
    cells_checked = 0
    for source in source_orders:
        encoded = [indexes[index][source[field]] if index < 4 else source[field]
                   for index, field in enumerate(ORDER_SOURCE_FIELDS)]
        for index, (field, value) in enumerate(zip(ORDER_SOURCE_FIELDS, encoded)):
            decoded = dictionaries[index][value] if index < 4 else value
            if decoded != source[field]:
                raise ValueError("Order encoding changed " + field)
            cells_checked += 1
        if any(value is not None and (not isinstance(value, int) or abs(value) > 2**53 - 1)
               for value in encoded):
            raise ValueError("An order value cannot be represented exactly as a JavaScript integer")
        orders.append(encoded)
    categories, seen = [], set()
    for source in source_categories:
        key = (source["order_id"], source["category_label"])
        if key in seen:
            raise ValueError("Duplicate exported order/category pair")
        seen.add(key)
        row = [order_index[source["order_id"]], category_index[source["category_label"]],
               source["product_sales_cents"], source["item_count"], source["delivery_eligible"]]
        decoded = [order_ids[row[0]], labels[row[1]], *row[2:]]
        if decoded != [source[field] for field in ("order_id", "category_label", "product_sales_cents",
                                                   "item_count", "delivery_eligible")]:
            raise ValueError("Category encoding changed a value")
        if any(value is not None and (not isinstance(value, int) or abs(value) > 2**53 - 1)
               for value in row):
            raise ValueError("A category value cannot be represented exactly as a JavaScript integer")
        cells_checked += len(row)
        categories.append(row)
    payload = {
        "meta": {
            "schemaVersion": 1, "periodStart": "2017-02-01", "periodEndExclusive": "2018-08-01",
            "moneyLabel": "source monetary units", "orderCount": len(orders),
            "categoryRowCount": len(categories), "customerCount": len(customers),
            "observationNote": "Final observed outcomes for purchases in the selected window; follow-up time varies.",
            "customerNote": "Repeat buyers have at least two eligible orders in the active selection; this is not lifetime retention.",
        },
        "fields": list(FIELDS), "orders": orders, "categoryFields": list(CATEGORY_FIELDS),
        "categories": categories, "months": list(MONTHS), "states": states,
        "statuses": statuses, "categoryLabels": labels,
    }
    audit = {"encoded_order_rows": len(orders), "encoded_category_rows": len(categories),
             "encoded_cells_checked": cells_checked, "order_key_count": len(set(order_ids)),
             "category_key_count": len(seen)}
    return payload, audit


def csv_rows(filename):
    with (PROJECT / "results" / filename).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def reconcile_published(payload):
    """Check exported rows against the existing stage totals, before writing."""
    checks = []

    def check(label, actual, expected):
        if actual != expected:
            raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")
        checks.append({"check": label, "actual": actual, "expected": expected, "status": "PASS"})

    field = {name: index for index, name in enumerate(payload["fields"])}
    orders = payload["orders"]
    sales = [row for row in orders if row[field["sales"]] == 1]
    delivery = [row for row in orders if row[field["delivery"]] == 1]
    reviewed = [row for row in sales if row[field["reviewScore"]] is not None]
    monthly = defaultdict(lambda: {"all_period_orders": 0, "sales_orders": 0, "product_sales_cents": 0})
    regional = defaultdict(lambda: {"sales_orders": 0, "product_sales_cents": 0})
    customers = defaultdict(lambda: {"orders": 0, "cents": 0})
    for row in orders:
        month = payload["months"][row[field["month"]]]
        monthly[month]["all_period_orders"] += 1
        if row[field["sales"]]:
            cents = row[field["salesCents"]]
            monthly[month]["sales_orders"] += 1
            monthly[month]["product_sales_cents"] += cents
            state = payload["states"][row[field["state"]]]
            regional[state]["sales_orders"] += 1
            regional[state]["product_sales_cents"] += cents
            customers[row[field["customer"]]]["orders"] += 1
            customers[row[field["customer"]]]["cents"] += cents
    for source in csv_rows("part4_monthly_sales.csv"):
        for name in ("all_period_orders", "sales_orders", "product_sales_cents"):
            check("Part 4 month " + source["month"] + " " + name,
                  monthly[source["month"]][name], int(source[name]))
    published_regions = csv_rows("part4_regional_sales.csv")
    check("Part 4 buyer-state labels", sorted(regional), sorted(row["customer_state"] for row in published_regions))
    for source in published_regions:
        for name in ("sales_orders", "product_sales_cents"):
            check("Part 4 state " + source["customer_state"] + " " + name,
                  regional[source["customer_state"]][name], int(source[name]))
    categories = defaultdict(lambda: {"sales_orders": set(), "item_count": 0, "product_sales_cents": 0,
                                       "delivery_orders": 0, "late_orders": 0})
    per_order_sales = Counter()
    for order_index, category_index, cents, item_count, delivery_member in payload["categories"]:
        order = orders[order_index]
        group = categories[payload["categoryLabels"][category_index]]
        if cents is not None:
            if not order[field["sales"]]:
                raise ValueError("Category sales reference an ineligible order")
            group["sales_orders"].add(order_index)
            group["item_count"] += item_count
            group["product_sales_cents"] += cents
            per_order_sales[order_index] += cents
        if delivery_member:
            if not order[field["delivery"]]:
                raise ValueError("Category delivery references an ineligible order")
            group["delivery_orders"] += 1
            group["late_orders"] += order[field["late"]]
    sales_indexes = {index for index, order in enumerate(orders) if order[field["sales"]]}
    check("Category sales cover every eligible order", set(per_order_sales) == sales_indexes, True)
    check("Every order's category values sum to its product value",
          all(value == orders[index][field["salesCents"]] for index, value in per_order_sales.items()), True)
    for source in csv_rows("part4_category_sales.csv"):
        group = categories[source["category_label"]]
        for name in ("sales_orders", "item_count", "product_sales_cents"):
            value = len(group[name]) if name == "sales_orders" else group[name]
            check("Part 4 category " + source["category_label"] + " " + name, value, int(source[name]))
    for source in csv_rows("part5_category_delivery.csv"):
        for name in ("delivery_orders", "late_orders"):
            check("Part 5 category " + source["category_label"] + " " + name,
                  categories[source["category_label"]][name], int(source[name]))
    totals = csv_rows("part5_overall_delivery.csv")[0]
    check("Part 5 reporting orders", len(orders), int(totals["all_period_orders"]))
    check("Part 5 delivery orders", len(delivery), int(totals["delivery_orders"]))
    check("Part 5 late orders", sum(row[field["late"]] for row in delivery), int(totals["late_orders"]))
    score_counts = Counter(row[field["reviewScore"]] for row in sales)
    for source in csv_rows("part6_review_distribution.csv"):
        score = int(source["review_score"]) if source["review_score"] else None
        check("Part 6 score bucket " + source["review_bucket"], score_counts[score], int(source["sales_orders"]))
    repeat = [group for group in customers.values() if group["orders"] >= 2]
    repeat_totals = csv_rows("part6_repeat_customers.csv")[0]
    for name, value in (("total_customers", len(customers)), ("repeat_customers", len(repeat)),
                        ("total_sales_orders", len(sales)),
                        ("repeat_customer_orders", sum(group["orders"] for group in repeat)),
                        ("total_product_sales_cents", sum(group["cents"] for group in customers.values())),
                        ("repeat_product_sales_cents", sum(group["cents"] for group in repeat))):
        check("Part 6 " + name, value, int(repeat_totals[name]))
    review_delivery = csv_rows("part6_delivery_reviews.csv")
    for source in review_delivery:
        late = source["delivery_group"] == "late"
        group = [row for row in sales if row[field["delivery"]] and row[field["late"]] == late]
        reviewed_group = [row for row in group if row[field["reviewScore"]] is not None]
        for name, value in (("sales_orders", len(group)), ("reviewed_orders", len(reviewed_group)),
                            ("review_score_sum", sum(row[field["reviewScore"]] for row in reviewed_group)),
                            ("low_score_orders", sum(row[field["reviewScore"]] <= 2 for row in reviewed_group)),
                            ("pre_delivery_review_orders", sum(row[field["preDeliveryReview"]] for row in reviewed_group))):
            check("Part 6 " + source["delivery_group"] + " " + name, value, int(source[name]))
    p7 = csv_rows("part7_population_validation.csv")[0]
    for name, value in (("reporting_period_orders", len(orders)), ("sales_orders", len(sales)),
                        ("delivery_orders", len(delivery)), ("reviewed_sales_orders", len(reviewed)),
                        ("sales_product_sales_cents", sum(row[field["salesCents"]] for row in sales))):
        check("Part 7 " + name, value, int(p7[name]))
    return checks


def export_dashboard(args):
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError("Database missing; complete Parts 2-7 before exporting")
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN")
        if [row[0] for row in connection.execute("PRAGMA integrity_check")] != ["ok"]:
            raise ValueError("SQLite integrity check failed")
        fingerprints = source_fingerprints(connection)
        with (PROJECT / "results/part2_import_log.csv").open(encoding="utf-8", newline="") as handle:
            recorded = {row["table_name"]: row["logical_rows_sha256"] for row in csv.DictReader(handle)}
        if {row["table_name"]: row["logical_rows_sha256"] for row in fingerprints} != recorded:
            raise ValueError("Raw fingerprints differ from the published source snapshot")
        print("Source snapshot verified. Encoding dashboard rows...", flush=True)
        payload, audit = build_payload(connection)
        checks = reconcile_published(payload)
        if source_fingerprints(connection) != fingerprints:
            raise ValueError("Raw records changed while exporting")
        connection.rollback()
    finally:
        connection.close()
    source_digest = hashlib.sha256(json.dumps(fingerprints, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    payload["meta"]["sourceFingerprintSha256"] = source_digest
    document = "globalThis.OLIST_DATA=" + json.dumps(payload, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + ";\n"
    # Confirm JSON serialization preserves each value before the file is written.
    if json.loads(document[len("globalThis.OLIST_DATA="):-2]) != payload:
        raise ValueError("JavaScript serialization changed the export")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
    report = {
        "status": "PASS", "schema_version": 1, "source_fingerprints": fingerprints,
        "raw_records_unchanged": True, "database_opened_read_only": True,
        **audit, "published_total_checks": len(checks), "checks": checks,
        "export_bytes": len(document.encode("utf-8")), "export_sha256": digest,
        "sql_sha256": hashlib.sha256((PROJECT / "sql/08_dashboard_export.sql").read_bytes()).hexdigest(),
        "period_start": payload["meta"]["periodStart"], "period_end_exclusive": payload["meta"]["periodEndExclusive"],
        "money_label": payload["meta"]["moneyLabel"],
        "order_fields": list(FIELDS), "category_fields": list(CATEGORY_FIELDS),
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "part8_export_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = (f"Part 8 export: PASS\nOrders: {audit['encoded_order_rows']:,}\n"
               f"Order/category pairs: {audit['encoded_category_rows']:,}\n"
               f"Encoded cells checked: {audit['encoded_cells_checked']:,}\n"
               f"Published count/money checks: {len(checks)}\n"
               f"Raw tables: eight fingerprints match; database opened read-only\n"
               f"Export bytes: {report['export_bytes']:,}\nExport SHA-256: {digest}\n")
    (args.results_dir / "part8_export_validation.txt").write_text(summary, encoding="utf-8")
    print(summary, end="")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--output", type=Path, default=PROJECT / "dashboard/data.js")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    export_dashboard(parser.parse_args())
