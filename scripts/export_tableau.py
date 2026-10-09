#!/usr/bin/env python3
"""Export two checked CSV sources for the Tableau workbook.

The database is opened read-only. Every SQL output cell is checked against the
previously validated order/category encoding, and published Parts 4-7 totals
are reconciled again. No browser files are required to run this exporter.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3

from export_dashboard import build_payload, reconcile_published
from prepare_part3 import result_sets, source_fingerprints

PROJECT = Path(__file__).resolve().parents[1]
ORDER_FIELDS = (
    "order_key", "customer_key", "purchase_month", "buyer_state", "order_status",
    "sales_eligible", "delivery_eligible", "review_eligible", "product_value_cents",
    "delivery_seconds", "is_late", "positive_delay_days", "review_score", "review_before_delivery",
)
CATEGORY_FIELDS = (
    "order_key", "category", "purchase_month", "buyer_state", "sales_eligible",
    "product_value_cents", "item_count", "delivery_eligible", "is_late",
    "delivery_seconds", "positive_delay_days",
)
TEXT_FIELDS = {"buyer_state", "order_status", "category"}
DATE_FIELDS = {"purchase_month"}


def expected_from_payload(payload):
    """Re-express the checked compact encoding using explicit Tableau columns."""
    indexes = {field: index for index, field in enumerate(payload["fields"])}
    orders = []
    for index, values in enumerate(payload["orders"]):
        row = {field: values[position] for field, position in indexes.items()}
        orders.append({
            "order_key": index + 1, "customer_key": row["customer"] + 1,
            "purchase_month": payload["months"][row["month"]] + "-01",
            "buyer_state": payload["states"][row["state"]],
            "order_status": payload["statuses"][row["status"]],
            "sales_eligible": row["sales"], "delivery_eligible": row["delivery"],
            "review_eligible": int(row["sales"] == 1 and row["reviewScore"] is not None),
            "product_value_cents": row["salesCents"], "delivery_seconds": row["deliverySeconds"],
            "is_late": row["late"],
            "positive_delay_days": row["delayDays"] if row["delivery"] == 1 and row["late"] == 1 else None,
            "review_score": row["reviewScore"], "review_before_delivery": row["preDeliveryReview"],
        })
    categories = []
    for order_index, category_index, cents, items, delivery in payload["categories"]:
        order = orders[order_index]
        categories.append({
            "order_key": order_index + 1, "category": payload["categoryLabels"][category_index],
            "purchase_month": order["purchase_month"], "buyer_state": order["buyer_state"],
            "sales_eligible": int(cents is not None), "product_value_cents": cents, "item_count": items,
            "delivery_eligible": delivery, "is_late": order["is_late"] if delivery else None,
            "delivery_seconds": order["delivery_seconds"] if delivery else None,
            "positive_delay_days": order["positive_delay_days"] if delivery else None,
        })
    return {"orders": orders, "categories": categories}


def build_exports(connection):
    """Return the two source tables and an audit; compatible with raw fixtures."""
    reports = result_sets(connection, PROJECT / "sql/09_tableau_export.sql")
    payload, encoding_audit = build_payload(connection)
    expected = expected_from_payload(payload)
    cells = 0
    for name, fields in (("orders", ORDER_FIELDS), ("categories", CATEGORY_FIELDS)):
        observed = reports[name]
        if len(observed) != len(expected[name]):
            raise ValueError("Tableau " + name + " row count differs from the checked source")
        for index, (actual, wanted) in enumerate(zip(observed, expected[name])):
            if tuple(actual) != fields or actual != wanted:
                raise ValueError(f"Tableau {name} row {index + 1} differs from the checked source")
            cells += len(fields)
    return reports, payload, {**encoding_audit, "tableau_cells_checked": cells}


def csv_text(rows, fields):
    """Serialize NULL as an empty CSV cell and verify typed values after reading."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    document = buffer.getvalue()
    decoded = []
    for raw in csv.DictReader(io.StringIO(document)):
        decoded.append({field: raw[field] if field in TEXT_FIELDS | DATE_FIELDS
                        else int(raw[field]) if raw[field] else None for field in fields})
    if decoded != rows:
        raise ValueError("CSV serialization changed a source value")
    return document


def export(args):
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
        print("Source snapshot verified. Building Tableau sources...", flush=True)
        reports, payload, audit = build_exports(connection)
        checks = reconcile_published(payload)
        if source_fingerprints(connection) != fingerprints:
            raise ValueError("Raw records changed while exporting")
        connection.rollback()
    finally:
        connection.close()
    texts = {name: csv_text(reports[name], fields)
             for name, fields in (("orders", ORDER_FIELDS), ("categories", CATEGORY_FIELDS))}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, document in texts.items():
        target = args.output_dir / (name + ".csv")
        with target.open("w", encoding="utf-8", newline="") as handle:
            handle.write(document)
        files[name] = {"file": "tableau/data/" + target.name, "rows": len(reports[name]),
                       "bytes": len(document.encode("utf-8")),
                       "sha256": hashlib.sha256(document.encode("utf-8")).hexdigest()}
    field_types = {field: "date" if field in DATE_FIELDS else "string" if field in TEXT_FIELDS else "integer"
                   for field in dict.fromkeys(ORDER_FIELDS + CATEGORY_FIELDS)}
    report = {
        "status": "PASS", "source_fingerprints": fingerprints,
        "database_opened_read_only": True, "raw_records_unchanged": True,
        **audit, "published_total_checks": len(checks), "checks": checks,
        "csv_round_trip": "Every decoded CSV cell equals the checked SQL value",
        "period_start": "2017-02-01", "period_end_exclusive": "2018-08-01",
        "money_label": "source monetary units", "files": files,
        "order_fields": list(ORDER_FIELDS), "category_fields": list(CATEGORY_FIELDS),
        "field_types": field_types,
        "source_identifiers_exported": False,
        "sql_sha256": hashlib.sha256((PROJECT / "sql/09_tableau_export.sql").read_bytes()).hexdigest(),
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "tableau_export_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = ("Tableau source export: PASS\n"
               f"Orders: {files['orders']['rows']:,}; bytes: {files['orders']['bytes']:,}\n"
               f"Order/category pairs: {files['categories']['rows']:,}; bytes: {files['categories']['bytes']:,}\n"
               f"Tableau cells checked: {audit['tableau_cells_checked']:,}\n"
               f"Published count/money checks: {len(checks)}\n"
               "Raw tables: eight fingerprints match; database opened read-only\n"
               "CSV NULL values, integer keys and source cents retained; raw identifiers omitted\n")
    (args.results_dir / "tableau_export_validation.txt").write_text(summary, encoding="utf-8")
    print(summary, end="")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "tableau/data")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    export(parser.parse_args())
