#!/usr/bin/env python3
"""Run the five sales queries, check them against raw records and export the results."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

from prepare_part3 import result_sets, source_fingerprints
from sales_checks import build_expected

PROJECT = Path(__file__).resolve().parents[1]
REPORTS = ("monthly_sales", "monthly_growth", "comparable_periods",
           "category_sales", "regional_sales")


def compare_rows(name, actual, expected):
    """Check every output cell; a mismatch stops the export."""
    if len(actual) != len(expected):
        raise ValueError(f"{name}: expected {len(expected)} rows, got {len(actual)}")
    for number, (got, want) in enumerate(zip(actual, expected), start=1):
        if set(got) != set(want):
            raise ValueError(f"{name}: output columns differ from the independent check")
        for field, value in want.items():
            observed = got[field]
            if isinstance(value, float):
                matches = (isinstance(observed, (int, float))
                           and math.isclose(observed, value, rel_tol=0, abs_tol=0.000001))
            else:
                matches = observed == value
            if not matches:
                raise ValueError(f"{name} row {number}, {field}: expected {value!r}, "
                                 f"got {observed!r}")


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"Cannot export an empty report: {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if value is None else
                             f"{value:.2f}" if isinstance(value, float) else value
                             for key, value in row.items()})


def analyse(args):
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError("Database missing; run build_database.py and prepare_part3.py first")
    if sqlite3.sqlite_version_info < (3, 25, 0):
        raise RuntimeError("SQLite 3.25 or later is required for the sales window functions")
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
        # Also tie this run to the source snapshot recorded in the repository.
        with (PROJECT / "results/part2_import_log.csv").open(encoding="utf-8", newline="") as handle:
            recorded = {r["table_name"]: r["logical_rows_sha256"] for r in csv.DictReader(handle)}
        check("raw fields match the published source snapshot",
              {r["table_name"]: r["logical_rows_sha256"] for r in fingerprints}, recorded)
        model_counts = connection.execute(
            "SELECT COUNT(*), COUNT(DISTINCT order_id) FROM v_order_analysis").fetchone()
        source_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        check("order model row count", model_counts[0], source_count)
        check("order model distinct IDs", model_counts[1], source_count)
        print("Source records checked. Running sales queries...", flush=True)
        outputs = result_sets(connection, PROJECT / "sql/03_sales_analysis.sql", progress=True)
        check("five named sales outputs", list(outputs), list(REPORTS))
        expected = build_expected(connection)
        for name in REPORTS:
            compare_rows(name, outputs[name], expected["reports"][name])
            checks.append({"check": f"{name}: every cell matches the raw-record calculation",
                           "rows_checked": len(outputs[name]), "status": "PASS"})
        monthly = outputs["monthly_sales"]
        sales_cents = sum(row["product_sales_cents"] for row in monthly)
        sales_orders = sum(row["sales_orders"] for row in monthly)
        check("category sales reconcile to monthly sales",
              sum(row["product_sales_cents"] for row in outputs["category_sales"]), sales_cents)
        check("regional sales reconcile to monthly sales",
              sum(row["product_sales_cents"] for row in outputs["regional_sales"]), sales_cents)
        check("regional orders reconcile to monthly orders",
              sum(row["sales_orders"] for row in outputs["regional_sales"]), sales_orders)
        check("monthly included and excluded orders reconcile",
              sum(row["sales_orders"] + row["excluded_orders"] for row in monthly),
              sum(row["all_period_orders"] for row in monthly))
    finally:
        connection.close()

    destination = args.results_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        write_csv(destination / f"part4_{name}.csv", rows)
    scripts = ["sql/03_sales_analysis.sql", "scripts/analyse_sales.py",
               "scripts/sales_checks.py", "scripts/prepare_part3.py", "scripts/build_database.py"]
    report = {
        "part": 4, "status": "PASS", "database_access": "read-only",
        "python_version": sys.version.split()[0], "sqlite_version": sqlite3.sqlite_version,
        "reporting_period": {"purchase_start_inclusive": "2017-02-01",
                             "purchase_end_exclusive": "2018-08-01"},
        "monetary_unit": "source monetary units; excludes freight",
        "source_tables": fingerprints,
        "script_sha256": {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
                          for name in scripts},
        "output_sha256": {f"part4_{name}.csv": hashlib.sha256(
            (destination / f"part4_{name}.csv").read_bytes()).hexdigest() for name in REPORTS},
        "checks_passed": len(checks), "checks": checks,
        "overall": expected["overall"], "period_status_counts": expected["status_counts"],
        "output_rows": {name: len(rows) for name, rows in outputs.items()},
    }
    (destination / "part4_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["PART 4 SALES VALIDATION", f"PASS: {len(checks)} checks", "",
             "Every output cell was compared with a separate Python calculation over raw records.",
             "The database was opened read-only. Blank CSV values mean NULL.", ""]
    lines.extend(f"PASS: {item['check']}" for item in checks)
    lines.extend(["", "Output rows:"] + [f"{name}: {len(rows)}" for name, rows in outputs.items()])
    (destination / "part4_validation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS: {len(checks)} checks; five CSV reports saved to {destination}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    args = parser.parse_args()
    try:
        analyse(args)
    except (ValueError, OSError, sqlite3.Error, RuntimeError) as exc:
        parser.exit(1, f"Part 4 failed: {exc}\n")


if __name__ == "__main__":
    main()
