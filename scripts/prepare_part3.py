#!/usr/bin/env python3
"""Profile the raw Olist tables, build Part 3 views and save checked results.

Run after scripts/build_database.py. Uses the Python standard library only.
The source tables stay unchanged. Failed checks roll back the view changes.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

from build_database import FILES, digest_row

PROJECT = Path(__file__).resolve().parents[1]


def statements(path):
    statement = ""
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            yield statement
            statement = ""
    if statement.strip():
        raise ValueError(f"Incomplete SQL statement in {path.name}")


def result_sets(connection, path, progress=False):
    results = {}
    for statement in statements(path):
        match = re.search(r"^-- result: (\w+)$", statement, flags=re.MULTILINE)
        if not match:
            raise ValueError(f"Result name missing in {path.name}")
        if progress:
            print(f"Checking {match[1]}...", flush=True)
        cursor = connection.execute(statement)
        results[match[1]] = [dict(row) for row in cursor.fetchall()]
    return results


def source_fingerprints(connection):
    """Compare every decoded field with the import log, in original row order."""
    observed = []
    log = {r["table_name"]: dict(r) for r in connection.execute("SELECT * FROM import_log")}
    for table in FILES:
        digest = hashlib.sha256()
        rows = 0
        for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
            digest_row(digest, list(row))
            rows += 1
        if table not in log or rows != log[table]["source_rows"]:
            raise ValueError(f"Raw row count differs from the Part 2 import: {table}")
        if digest.hexdigest() != log[table]["logical_rows_sha256"]:
            raise ValueError(f"Raw field values differ from the Part 2 import: {table}")
        observed.append({"table_name": table, "source_rows": rows,
                         "logical_rows_sha256": digest.hexdigest(), "status": "PASS"})
    return observed


def validate(connection, profile, observed):
    gates = []

    def check(name, actual, expected):
        passed = actual == expected
        gates.append({"check": name, "actual": actual, "expected": expected,
                      "status": "PASS" if passed else "FAIL"})
        if not passed:
            raise ValueError(f"{name}: expected {expected!r}, got {actual!r}")

    for row in observed["row_counts"]:
        check(f"{row['table_name']}: clean rows retained", row["clean_rows"], row["raw_rows"])
    for row in observed["key_checks"]:
        check(f"{row['table_name']}: missing keys", row["missing_key_rows"], 0)
        check(f"{row['table_name']}: duplicate keys", row["duplicate_key_groups"], 0)
    for row in observed["relationships"]:
        check(row["relationship"], row["unmatched_rows"], 0)
    for row in profile["exact_duplicate_records"]:
        check(f"{row['table_name']}: exact duplicate records", row["duplicate_extra_rows"], 0)
    for name in ["numeric", "date"]:
        count = connection.execute(f"SELECT COUNT(*) FROM v_p3_{name}_issues").fetchone()[0]
        check(f"{name} format issues", count, 0)

    totals = observed["join_reconciliation"][0]
    for actual, expected in [("modeled_orders", "raw_orders"), ("distinct_modeled_orders", "raw_orders"),
                             ("joined_price_cents", "item_price_cents"),
                             ("joined_freight_cents", "item_freight_cents"),
                             ("joined_payment_cents", "source_payment_cents"),
                             ("labeled_products", "source_products")]:
        check(actual, totals[actual], totals[expected])

    # Decimal is an independent check on SQL's conversion and aggregation of money.
    for table, field, total in [("order_items", "price", "item_price_cents"),
                                 ("order_items", "freight_value", "item_freight_cents"),
                                 ("order_payments", "payment_value", "source_payment_cents")]:
        expected = sum(int(Decimal(row[0].strip()) * 100)
                       for row in connection.execute(f"SELECT {field} FROM {table}"))
        check(f"{field}: Decimal reconciliation", totals[total], expected)
        mismatches = sum(
            actual != int(Decimal(raw.strip()) * 100)
            for raw, actual in connection.execute(
                f"SELECT r.{field}, c.{field}_cents FROM {table} r "
                f"JOIN v_clean_{table} c ON c.order_id = TRIM(r.order_id) AND "
                + ("c.order_item_id = CAST(r.order_item_id AS INTEGER)" if table == "order_items"
                   else "c.payment_sequential = CAST(r.payment_sequential AS INTEGER)")
            )
        )
        check(f"{field}: every converted value matches Decimal", mismatches, 0)

    for table, field in [("order_items", "order_item_id"), ("order_payments", "payment_sequential")]:
        count = connection.execute(f"SELECT COUNT(*) FROM v_clean_{table} WHERE {field} < 1").fetchone()[0]
        check(f"{field}: nonpositive sequence", count, 0)
    check("sales orders without a customer identity",
          observed["populations"][0]["sales_without_customer_identity"], 0)
    selected = observed["review_selection"][0]
    check("review selection accounts for every source row",
          selected["selected_rows"] + selected["invalid_rows"]
          + selected["additional_valid_reviews_not_selected"], selected["source_review_rows"])
    check("SQLite integrity", [r[0] for r in connection.execute("PRAGMA integrity_check")], ["ok"])
    return gates


def prepare(args):
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError(f"Missing {database.name}; run scripts/build_database.py first")
    if sqlite3.sqlite_version_info < (3, 25, 0):
        raise RuntimeError("SQLite 3.25 or later is required for ROW_NUMBER()")
    connection = sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA temp_store = MEMORY")
    try:
        connection.execute("BEGIN IMMEDIATE")
        if [r[0] for r in connection.execute("PRAGMA integrity_check")] != ["ok"]:
            raise ValueError("Source database failed integrity_check; rebuild from the CSVs")
        before = source_fingerprints(connection)
        print("Raw counts and every field match the Part 2 import.", flush=True)
        profile = result_sets(connection, PROJECT / "sql/02_profile.sql", progress=True)
        for statement in statements(PROJECT / "sql/02_cleaning.sql"):
            connection.execute(statement)
        print("Clean views created; checking keys, relationships and totals.", flush=True)
        observed = result_sets(connection, PROJECT / "sql/02_check_cleaning.sql", progress=True)
        gates = validate(connection, profile, observed)
        after = source_fingerprints(connection)
        if after != before:
            raise ValueError("Source data changed during preparation")
        gates.append({"check": "raw fields unchanged after cleaning", "actual": True,
                      "expected": True, "status": "PASS"})
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()

    results = args.results_dir.resolve()
    results.mkdir(parents=True, exist_ok=True)
    scripts = ["sql/02_profile.sql", "sql/02_cleaning.sql", "sql/02_check_cleaning.sql",
               "scripts/prepare_part3.py"]
    report = {
        "part": 3, "status": "PASS", "python_version": sys.version.split()[0],
        "sqlite_version": sqlite3.sqlite_version, "source_tables": before,
        "script_sha256": {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
                          for name in scripts},
        "reporting_period": {"purchase_start_inclusive": "2017-02-01",
                             "purchase_end_exclusive": "2018-08-01"},
        "checks_passed": len(gates), "checks": gates, "observed": observed,
    }
    for name, content in [("part3_profile.json", profile), ("part3_validation.json", report)]:
        (results / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    output = ["PART 3 VALIDATION", f"PASS: {len(gates)} checks", ""]
    for gate in gates:
        output.append(f"{gate['status']}: {gate['check']} = {gate['actual']}")
    for name, rows in observed.items():
        output.extend(["", name])
        if rows:
            output.append(" | ".join(rows[0]))
            output.extend(" | ".join("NULL" if x is None else str(x) for x in row.values()) for row in rows)
    (results / "part3_validation.txt").write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"PASS: {len(gates)} checks. Raw tables unchanged; results saved.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    args = parser.parse_args()
    try:
        prepare(args)
    except Exception as exc:
        parser.exit(1, f"Part 3 failed: {exc}\n")


if __name__ == "__main__":
    main()
