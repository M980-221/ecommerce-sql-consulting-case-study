#!/usr/bin/env python3
"""Run the customer queries, check the populations and export the five reports."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from analyse_sales import compare_rows, write_csv
from customer_checks import build_expected
from prepare_part3 import result_sets, source_fingerprints

PROJECT = Path(__file__).resolve().parents[1]
REPORTS = ("review_distribution", "delivery_reviews", "customer_spending",
           "repeat_customers", "regional_reviews")


def analyse(args):
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError("Database missing; run build_database.py and prepare_part3.py first")
    if sqlite3.sqlite_version_info < (3, 25, 0):
        raise RuntimeError("SQLite 3.25 or later is required for the prepared order model")
    checks = []

    def check(name, actual, expected):
        if actual != expected:
            raise ValueError(f"{name}: expected {expected!r}, got {actual!r}")
        checks.append({"check": name, "actual": actual, "expected": expected, "status": "PASS"})

    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN")
        check("database integrity", [r[0] for r in connection.execute("PRAGMA integrity_check")], ["ok"])
        fingerprints = source_fingerprints(connection)
        check("raw tables match the import fingerprints", len(fingerprints), 8)
        with (PROJECT / "results/part2_import_log.csv").open(encoding="utf-8", newline="") as handle:
            recorded = {r["table_name"]: r["logical_rows_sha256"] for r in csv.DictReader(handle)}
        check("raw fields match the published source snapshot",
              {r["table_name"]: r["logical_rows_sha256"] for r in fingerprints}, recorded)
        counts = connection.execute(
            "SELECT COUNT(*), COUNT(DISTINCT order_id) FROM v_order_analysis").fetchone()
        source_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        check("order model row count", counts[0], source_count)
        check("order model distinct IDs", counts[1], source_count)
        print("Source records checked. Running customer queries...", flush=True)
        outputs = result_sets(connection, PROJECT / "sql/05_customer_analysis.sql", progress=True)
        check("five named customer outputs", list(outputs), list(REPORTS))
        expected = build_expected(connection)
        for name in REPORTS:
            compare_rows(name, outputs[name], expected["reports"][name])
            checks.append({"check": f"{name}: every cell matches the raw-record calculation",
                           "rows_checked": len(outputs[name]), "status": "PASS"})

        distribution = outputs["review_distribution"]
        totals = distribution[0]
        repeat = outputs["repeat_customers"][0]
        low_score_orders = sum(row["sales_orders"] for row in distribution
                               if row["review_score"] in (1, 2))
        score_sum = sum(row["review_score"] * row["sales_orders"] for row in distribution
                        if row["review_score"] is not None)
        check("review buckets account for every sales order",
              sum(row["sales_orders"] for row in distribution), totals["total_sales_orders"])
        check("scored buckets reconcile to reviewed orders",
              sum(row["sales_orders"] for row in distribution if row["review_score"] is not None),
              totals["total_reviewed_orders"])
        check("missing-review bucket reconciles",
              sum(row["sales_orders"] for row in distribution if row["review_score"] is None),
              totals["total_missing_review_orders"])
        for field, target in [("sales_orders", totals["total_sales_orders"]),
                              ("reviewed_orders", totals["total_reviewed_orders"]),
                              ("missing_review_orders", totals["total_missing_review_orders"]),
                              ("low_score_orders", low_score_orders), ("review_score_sum", score_sum)]:
            check(f"regional {field} reconcile", sum(row[field] for row in outputs["regional_reviews"]),
                  target)
        check("delivery comparison review coverage reconciles",
              sum(row["reviewed_orders"] + row["missing_review_orders"]
                  for row in outputs["delivery_reviews"]),
              sum(row["sales_orders"] for row in outputs["delivery_reviews"]))
        check("customer groups reconcile",
              repeat["one_time_customers"] + repeat["repeat_customers"], repeat["total_customers"])
        check("customer order groups reconcile",
              repeat["one_time_customer_orders"] + repeat["repeat_customer_orders"],
              repeat["total_sales_orders"])
        check("customer value groups reconcile",
              repeat["one_time_product_sales_cents"] + repeat["repeat_product_sales_cents"],
              repeat["total_product_sales_cents"])
        check("customer and review populations match",
              repeat["total_sales_orders"], totals["total_sales_orders"])
        # These published totals let customer spending tie back to the sales stage.
        sales_totals = json.loads((PROJECT / "results/part4_validation.json").read_text())["overall"]
        check("customer orders match Part 4", repeat["total_sales_orders"], sales_totals["sales_orders"])
        check("customer value matches Part 4", repeat["total_product_sales_cents"],
              sales_totals["product_sales_cents"])
    finally:
        connection.close()

    destination = args.results_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        write_csv(destination / f"part6_{name}.csv", rows)
    dependencies = ["sql/05_customer_analysis.sql", "scripts/analyse_customers.py",
                    "scripts/customer_checks.py", "scripts/analyse_sales.py", "scripts/sales_checks.py",
                    "scripts/delivery_checks.py", "scripts/prepare_part3.py", "scripts/build_database.py",
                    "results/part4_validation.json"]
    report = {
        "part": 6, "status": "PASS", "database_access": "read-only",
        "python_version": sys.version.split()[0], "sqlite_version": sqlite3.sqlite_version,
        "reporting_period": {"purchase_start_inclusive": "2017-02-01",
                             "purchase_end_exclusive": "2018-08-01"},
        "customer_identity": "customer_unique_id",
        "repeat_rule": "at least two sales-eligible orders in the reporting period",
        "customer_spending_output": "top 20 by product sales value, after grouping all eligible customers",
        "source_tables": fingerprints,
        "dependency_sha256": {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
                              for name in dependencies},
        "output_sha256": {f"part6_{name}.csv": hashlib.sha256(
            (destination / f"part6_{name}.csv").read_bytes()).hexdigest() for name in REPORTS},
        "checks_passed": len(checks), "checks": checks,
        "overall": expected["overall"], "period_status_counts": expected["status_counts"],
        "output_rows": {name: len(rows) for name, rows in outputs.items()},
        "output_cells_checked": sum(len(row) for rows in outputs.values() for row in rows),
    }
    (destination / "part6_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["PART 6 CUSTOMER VALIDATION", f"PASS: {len(checks)} checks", "",
             "Every output cell was compared with a separate calculation over raw records.",
             "Review selection, persistent customer groups and money totals were checked independently.",
             "The database was opened read-only. Blank CSV values mean NULL.", ""]
    lines.extend(f"PASS: {item['check']}" for item in checks)
    lines.extend(["", "Output rows:"] + [f"{name}: {len(rows)}" for name, rows in outputs.items()])
    lines.append(f"Output cells checked: {report['output_cells_checked']}")
    (destination / "part6_validation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS: {len(checks)} checks; five CSV reports saved to {destination}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    args = parser.parse_args()
    try:
        analyse(args)
    except (ValueError, OSError, sqlite3.Error, RuntimeError) as exc:
        parser.exit(1, f"Part 6 failed: {exc}\n")


if __name__ == "__main__":
    main()
