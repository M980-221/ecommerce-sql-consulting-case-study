#!/usr/bin/env python3
"""Run the delivery queries and check every result against raw order records."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from analyse_sales import compare_rows, write_csv
from delivery_checks import build_expected
from prepare_part3 import result_sets, source_fingerprints

PROJECT = Path(__file__).resolve().parents[1]
REPORTS = ("overall_delivery", "monthly_delivery", "regional_delivery",
           "category_delivery", "seller_delivery")


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
        print("Source records checked. Running delivery queries...", flush=True)
        outputs = result_sets(connection, PROJECT / "sql/04_delivery_analysis.sql", progress=True)
        check("five named delivery outputs", list(outputs), list(REPORTS))
        expected = build_expected(connection)
        for name in REPORTS:
            compare_rows(name, outputs[name], expected["reports"][name])
            checks.append({"check": f"{name}: every cell matches the raw-record calculation",
                           "rows_checked": len(outputs[name]), "status": "PASS"})

        overall = outputs["overall_delivery"][0]
        for name in ("monthly_delivery", "regional_delivery"):
            for field in ("delivery_orders", "late_orders", "on_time_orders"):
                check(f"{name}: {field} reconcile to overall",
                      sum(row[field] for row in outputs[name]), overall[field])
        check("monthly period orders reconcile",
              sum(row["all_period_orders"] for row in outputs["monthly_delivery"]),
              overall["all_period_orders"])
        check("period inclusion and exclusion reconcile",
              overall["delivery_orders"] + overall["excluded_orders"], overall["all_period_orders"])
        check("exclusion reasons reconcile",
              overall["non_delivered_orders"] + overall["excluded_delivered_date_orders"],
              overall["excluded_orders"])
        check("late and on-time orders reconcile",
              overall["late_orders"] + overall["on_time_orders"], overall["delivery_orders"])
        check("seller subsets account for every delivery order",
              overall["single_seller_orders"] + overall["excluded_multi_seller_orders"]
              + overall["excluded_no_seller_orders"], overall["delivery_orders"])
        check("seller threshold exclusions reconcile",
              overall["reported_seller_orders"] + overall["below_threshold_seller_orders"],
              overall["single_seller_orders"])
        check("reported seller orders reconcile",
              sum(row["delivery_orders"] for row in outputs["seller_delivery"]),
              overall["reported_seller_orders"])
        check("reported seller count", len(outputs["seller_delivery"]), overall["reported_sellers"])
    finally:
        connection.close()

    destination = args.results_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        write_csv(destination / f"part5_{name}.csv", rows)
    scripts = ["sql/04_delivery_analysis.sql", "scripts/analyse_delivery.py",
               "scripts/delivery_checks.py", "scripts/analyse_sales.py",
               "scripts/prepare_part3.py", "scripts/build_database.py"]
    report = {
        "part": 5, "status": "PASS", "database_access": "read-only",
        "python_version": sys.version.split()[0], "sqlite_version": sqlite3.sqlite_version,
        "reporting_period": {"purchase_start_inclusive": "2017-02-01",
                             "purchase_end_exclusive": "2018-08-01"},
        "seller_minimum_orders": 100,
        "category_allocation": "one row per distinct eligible order and category; categories overlap",
        "time_units": {"delivery_duration": "elapsed days from recorded purchase to delivery timestamps",
                       "positive_delay": "calendar days after the promised date, late orders only"},
        "source_tables": fingerprints,
        "script_sha256": {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
                          for name in scripts},
        "output_sha256": {f"part5_{name}.csv": hashlib.sha256(
            (destination / f"part5_{name}.csv").read_bytes()).hexdigest() for name in REPORTS},
        "checks_passed": len(checks), "checks": checks,
        "overall": expected["overall"], "period_status_counts": expected["status_counts"],
        "output_rows": {name: len(rows) for name, rows in outputs.items()},
        "output_cells_checked": sum(len(row) for rows in outputs.values() for row in rows),
    }
    (destination / "part5_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["PART 5 DELIVERY VALIDATION", f"PASS: {len(checks)} checks", "",
             "Every output cell was compared with a separate calculation over raw records.",
             "Dates and durations were calculated independently with Python datetime.",
             "The database was opened read-only. Blank CSV values mean NULL.", ""]
    lines.extend(f"PASS: {item['check']}" for item in checks)
    lines.extend(["", "Output rows:"] + [f"{name}: {len(rows)}" for name, rows in outputs.items()])
    lines.append(f"Output cells checked: {report['output_cells_checked']}")
    (destination / "part5_validation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS: {len(checks)} checks; five CSV reports saved to {destination}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    args = parser.parse_args()
    try:
        analyse(args)
    except (ValueError, OSError, sqlite3.Error, RuntimeError) as exc:
        parser.exit(1, f"Part 5 failed: {exc}\n")


if __name__ == "__main__":
    main()
