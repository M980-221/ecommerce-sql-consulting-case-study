#!/usr/bin/env python3
"""Check reconciliation and reporting views, then record an order-lookup benchmark."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from analyse_sales import compare_rows, write_csv
from benchmark_part7 import benchmark
from prepare_part3 import result_sets, source_fingerprints, statements
from validation_checks import calculate_raw

PROJECT = Path(__file__).resolve().parents[1]
REPORTS = ("population_validation", "reconciliation_summary", "reconciliation_patterns",
           "reconciliation_exceptions", "join_fanout_summary", "missingness_by_population")
WALKTHROUGHS = {
    "simple_exact": "00010242fe8c5a6d1ba2dd792cb16214",
    "two_items_two_payments": "03ecec245220b63fd7f68c1737ba99ba",
    "one_cent_difference": "153b80864a22f0638fef4339488a2cf3",
    "larger_difference": "00789ce015e7e5791c7914f32bb4fad4",
    "missing_payment": "bfbd0f9bdef84302105ad712db648a6c",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def published_rows(filename, fields):
    """Read only the exact dimensions/counts/cents needed for a comparison."""
    with (PROJECT / "results" / filename).open(encoding="utf-8", newline="") as handle:
        return [{field: (int(row[field]) if kind is int else row[field])
                 for field, kind in fields.items()} for row in csv.DictReader(handle)]


def check_reporting(connection, check):
    """Validate each reporting grain and compare aggregates with published outputs."""
    # Reuse one evaluation of each live view during this validation transaction.
    for suffix in ("orders", "sales_items", "order_categories", "customers"):
        connection.execute(f"CREATE TEMP TABLE part7_{suffix} AS SELECT * FROM v_reporting_{suffix}")

    def scalar(sql):
        return connection.execute(sql).fetchone()[0]

    def compare_published(name, sql, filename, fields, key):
        actual = [dict(r) for r in connection.execute(sql)]
        expected = published_rows(filename, fields)
        compare_rows(name, sorted(actual, key=key), sorted(expected, key=key))
        check(name, len(actual), len(expected))

    check("reporting orders: unique order IDs", scalar("SELECT COUNT(*) FROM part7_orders"),
          scalar("SELECT COUNT(DISTINCT order_id) FROM part7_orders"))
    check("reporting orders: exact period coverage", scalar("SELECT COUNT(*) FROM part7_orders"),
          scalar("SELECT COUNT(*) FROM v_order_analysis WHERE in_reporting_period=1"))
    check("reporting items: unique order/item pairs", scalar("SELECT COUNT(*) FROM part7_sales_items"),
          scalar("SELECT COUNT(*) FROM (SELECT order_id, order_item_id FROM part7_sales_items GROUP BY 1,2)"))
    check("reporting categories: unique order/category pairs",
          scalar("SELECT COUNT(*) FROM part7_order_categories"),
          scalar("SELECT COUNT(*) FROM (SELECT order_id, category_label FROM part7_order_categories GROUP BY 1,2)"))
    check("reporting customers: unique persistent IDs", scalar("SELECT COUNT(*) FROM part7_customers"),
          scalar("SELECT COUNT(DISTINCT customer_unique_id) FROM part7_customers"))
    check("reporting items: sales-eligible parents only", scalar("""SELECT COUNT(*) FROM part7_sales_items i
          LEFT JOIN part7_orders o ON o.order_id=i.order_id WHERE COALESCE(o.sales_eligible,0)<>1"""), 0)
    check("reporting categories: delivery-eligible parents only", scalar("""SELECT COUNT(*)
          FROM part7_order_categories c LEFT JOIN part7_orders o ON o.order_id=c.order_id
          WHERE COALESCE(o.delivery_eligible,0)<>1"""), 0)

    compare_published("reporting monthly sales match Part 4", """SELECT purchase_month AS month,
        SUM(sales_eligible) AS sales_orders,
        SUM(CASE WHEN sales_eligible=1 THEN product_sales_cents ELSE 0 END) AS product_sales_cents
        FROM part7_orders GROUP BY purchase_month""", "part4_monthly_sales.csv",
        {"month": str, "sales_orders": int, "product_sales_cents": int},
        lambda row: row["month"])
    compare_published("reporting category sales match Part 4", """SELECT category_label,
        COUNT(DISTINCT order_id) AS sales_orders, COUNT(*) AS item_count,
        SUM(price_cents) AS product_sales_cents FROM part7_sales_items GROUP BY category_label""",
        "part4_category_sales.csv",
        {"category_label": str, "sales_orders": int, "item_count": int, "product_sales_cents": int},
        lambda row: row["category_label"])
    compare_published("reporting monthly delivery matches Part 5", """SELECT purchase_month AS month,
        COUNT(*) AS delivery_orders, SUM(is_late) AS late_orders
        FROM part7_orders WHERE delivery_eligible=1 GROUP BY purchase_month""",
        "part5_monthly_delivery.csv",
        {"month": str, "delivery_orders": int, "late_orders": int},
        lambda row: row["month"])
    compare_published("reporting category delivery matches Part 5", """SELECT c.category_label,
        COUNT(*) AS delivery_orders, SUM(o.is_late) AS late_orders FROM part7_order_categories c
        JOIN part7_orders o ON o.order_id=c.order_id GROUP BY c.category_label""",
        "part5_category_delivery.csv",
        {"category_label": str, "delivery_orders": int, "late_orders": int},
        lambda row: row["category_label"])
    compare_published("reporting state reviews match Part 6", """SELECT customer_state,
        COUNT(*) AS sales_orders, COUNT(review_score) AS reviewed_orders,
        SUM(review_score) AS review_score_sum,
        SUM(CASE WHEN review_score IN (1,2) THEN 1 ELSE 0 END) AS low_score_orders
        FROM part7_orders WHERE sales_eligible=1 GROUP BY customer_state""",
        "part6_regional_reviews.csv",
        {"customer_state": str, "sales_orders": int, "reviewed_orders": int,
         "review_score_sum": int, "low_score_orders": int}, lambda row: row["customer_state"])

    repeat = published_rows("part6_repeat_customers.csv", {"total_customers": int,
        "repeat_customers": int, "total_sales_orders": int, "total_product_sales_cents": int})[0]
    for label, sql, field in (
        ("customer count", "COUNT(*)", "total_customers"),
        ("repeat customers", "SUM(CASE WHEN sales_orders>=2 THEN 1 ELSE 0 END)", "repeat_customers"),
        ("customer order count", "SUM(sales_orders)", "total_sales_orders"),
        ("customer product value", "SUM(product_sales_cents)", "total_product_sales_cents"),
    ):
        check(f"reporting {label} matches Part 6", scalar(f"SELECT {sql} FROM part7_customers"), repeat[field])
    compare_published("reporting customer top 20 matches Part 6", """SELECT customer_unique_id,
        sales_orders, product_sales_cents, reviewed_orders FROM part7_customers
        ORDER BY product_sales_cents DESC, customer_unique_id LIMIT 20""",
        "part6_customer_spending.csv", {"customer_unique_id": str, "sales_orders": int,
        "product_sales_cents": int, "reviewed_orders": int}, lambda row: row["customer_unique_id"])
    return {suffix: scalar(f"SELECT COUNT(*) FROM part7_{suffix}")
            for suffix in ("orders", "sales_items", "order_categories", "customers")}


def trace_orders(connection, check):
    """Save the raw rows behind five documented, deliberately chosen examples."""
    traces = []
    for label, order_id in WALKTHROUGHS.items():
        order = dict(connection.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone())
        customer = dict(connection.execute("""SELECT customer_id, customer_unique_id, customer_state
            FROM customers WHERE customer_id=?""", (order["customer_id"],)).fetchone())
        items = [dict(r) for r in connection.execute("""SELECT order_item_id,product_id,seller_id,price,
            freight_value FROM order_items WHERE order_id=? ORDER BY CAST(order_item_id AS INTEGER)""",
            (order_id,))]
        payments = [dict(r) for r in connection.execute("""SELECT payment_sequential,payment_type,
            payment_installments,payment_value FROM order_payments WHERE order_id=?
            ORDER BY CAST(payment_sequential AS INTEGER)""", (order_id,))]
        reviews = [dict(r) for r in connection.execute("""SELECT review_id,review_score,review_creation_date,
            review_answer_timestamp FROM order_reviews WHERE order_id=? ORDER BY review_id""",
            (order_id,))]
        def cents(rows, field):
            return sum(int(Decimal(row[field]) * 100) for row in rows) if rows else None
        product = cents(items, "price")
        freight = cents(items, "freight_value")
        payment = cents(payments, "payment_value")
        purchase = order["order_purchase_timestamp"]
        valid = [r for r in reviews if r["review_score"] in ("1", "2", "3", "4", "5")
                 and r["review_creation_date"][:10] >= purchase[:10]
                 and r["review_answer_timestamp"] >= purchase
                 and r["review_answer_timestamp"] >= r["review_creation_date"]]
        # Stable sorts implement latest answer, then creation, then smallest review ID.
        valid.sort(key=lambda r: r["review_id"])
        valid.sort(key=lambda r: r["review_creation_date"], reverse=True)
        valid.sort(key=lambda r: r["review_answer_timestamp"], reverse=True)
        expected = {"item_count": len(items), "payment_count": len(payments),
            "product_sales_cents": product, "freight_cents": freight, "payment_cents": payment,
            "payment_difference_cents": payment-product-freight if items and payments else None,
            "customer_unique_id": customer["customer_unique_id"],
            "review_id": valid[0]["review_id"] if valid else None}
        model = dict(connection.execute("SELECT * FROM v_order_analysis WHERE order_id=?", (order_id,)).fetchone())
        check(f"order walkthrough {label}: raw arithmetic and selected review",
              {key: model[key] for key in expected}, expected)
        traces.append({"example": label, "order": order, "customer": customer, "items": items,
            "payments": payments, "reviews": reviews, "checked_model_values": expected,
            "eligibility": {key: model[key] for key in ("in_reporting_period", "sales_eligible",
                "delivery_eligible", "review_eligible", "seller_delivery_eligible", "is_late", "delay_days")}})
    return traces


def validate(args):
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError("Run build_database.py and prepare_part3.py first")
    checks = []

    def check(name, actual, expected):
        if actual != expected:
            raise ValueError(f"{name}: expected {expected!r}, got {actual!r}")
        checks.append({"check": name, "actual": actual, "expected": expected, "status": "PASS"})

    connection = sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN IMMEDIATE")
        check("database integrity", [r[0] for r in connection.execute("PRAGMA integrity_check")], ["ok"])
        fingerprints = source_fingerprints(connection)
        with (PROJECT / "results/part2_import_log.csv").open(encoding="utf-8", newline="") as handle:
            recorded = {r["table_name"]: r["logical_rows_sha256"] for r in csv.DictReader(handle)}
        check("raw records match published Part 2 snapshot",
              {r["table_name"]: r["logical_rows_sha256"] for r in fingerprints}, recorded)
        print("Source records checked. Running Part 7 reconciliation...", flush=True)
        outputs = result_sets(connection, PROJECT / "sql/06_validation.sql", progress=True)
        check("six named validation outputs", list(outputs), list(REPORTS))
        expected = calculate_raw(connection)
        for name in REPORTS:
            compare_rows(name, outputs[name], expected["reports"][name])
            checks.append({"check": f"{name}: every cell matches raw-record calculation",
                           "rows_checked": len(outputs[name]), "status": "PASS"})
        traces = trace_orders(connection, check)

        print("Applying and checking reporting views...", flush=True)
        protected_schema_sql = """SELECT type, name, tbl_name, sql FROM sqlite_master
            WHERE name NOT GLOB 'v_reporting_*' ORDER BY type,name"""
        original_schema = [tuple(r) for r in connection.execute(protected_schema_sql)]
        for statement in statements(PROJECT / "sql/07_reporting_views.sql"):
            connection.execute(statement)
        reporting_counts = check_reporting(connection, check)
        check("existing tables, indexes and analytical views unchanged",
              [tuple(r) for r in connection.execute(protected_schema_sql)], original_schema)
        # Avoid copying every schema definition into the published check record.
        checks[-1]["actual"] = checks[-1]["expected"] = "unchanged"
        check("raw records unchanged after reporting view creation", source_fingerprints(connection), fingerprints)
        checks[-1]["actual"] = checks[-1]["expected"] = "all eight table fingerprints match"
        print("Measuring the two equivalent order-item lookups...", flush=True)
        performance = benchmark(connection)
        check("performance experiment: two cases with identical query results",
              [case["result_identity_verified"] for case in performance["cases"]], [True, True])
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    destination = args.results_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        write_csv(destination / f"part7_{name}.csv", rows)
    (destination / "part7_performance.json").write_text(
        json.dumps(performance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "part7_order_walkthroughs.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dependencies = ["sql/06_validation.sql", "sql/07_reporting_views.sql", "sql/02_cleaning.sql",
                    "scripts/validate_part7.py", "scripts/validation_checks.py",
                    "scripts/benchmark_part7.py", "scripts/analyse_sales.py",
                    "scripts/prepare_part3.py", "scripts/build_database.py",
                    "scripts/customer_checks.py", "scripts/delivery_checks.py", "scripts/sales_checks.py"]
    dependencies += [f"results/{name}" for name in (
        "part4_monthly_sales.csv", "part4_category_sales.csv", "part5_monthly_delivery.csv",
        "part5_category_delivery.csv", "part6_regional_reviews.csv",
        "part6_repeat_customers.csv", "part6_customer_spending.csv")]
    output_names = [f"part7_{name}.csv" for name in REPORTS] + ["part7_performance.json",
                                                           "part7_order_walkthroughs.json"]
    report = {"part": 7, "status": "PASS", "python_version": sys.version.split()[0],
        "sqlite_version": sqlite3.sqlite_version,
        "database_access": "reporting views created transactionally; source records unchanged",
        "source_tables": fingerprints, "checks_passed": len(checks), "checks": checks,
        "output_rows": {name: len(rows) for name, rows in outputs.items()},
        "output_cells_checked": sum(len(row) for rows in outputs.values() for row in rows),
        "reporting_view_rows": reporting_counts, "independent_evidence": expected["evidence"],
        "dependency_sha256": {name: digest(PROJECT / name) for name in dependencies},
        "output_sha256": {name: digest(destination / name) for name in output_names},
        "remaining_limitations": ["Source payment differences have no confirmed business cause.",
            "Benchmark timings are specific to this local warm-cache order lookup.",
            "Dashboard visuals and measures will be checked in Part 8."]}
    (destination / "part7_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["PART 7 VALIDATION", f"PASS: {len(checks)} checks", "",
             "All reconciliation report cells match independent raw-record calculations.",
             "Reporting views reconcile to the published Parts 4–6 outputs.",
             "Raw source records remain unchanged; payment exceptions remain visible.", ""]
    lines += [f"PASS: {row['check']}" for row in checks]
    lines += ["", "Output rows:"] + [f"{key}: {len(rows)}" for key, rows in outputs.items()]
    lines += [f"Output cells checked: {report['output_cells_checked']}", "", "Reporting view rows:"]
    lines += [f"{key}: {value}" for key, value in reporting_counts.items()]
    (destination / "part7_validation.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS: {len(checks)} checks; reporting views and evidence ready.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    args = parser.parse_args()
    try:
        validate(args)
    except (ValueError, OSError, sqlite3.Error, RuntimeError) as exc:
        parser.exit(1, f"Part 7 failed: {exc}\n")


if __name__ == "__main__":
    main()
