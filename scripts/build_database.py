#!/usr/bin/env python3
"""Rebuild Part 2 from eight unchanged Olist CSVs; standard library only.

Run: python3 scripts/build_database.py
Existing databases are never overwritten. Use --output for a separate rebuild.
"""
import argparse
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[1]
FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_row(digest, row):
    digest.update(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    digest.update(b"\n")


def inspect_csv(path):
    count = 0
    digest = hashlib.sha256()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader)
        for row in reader:
            if len(row) != len(header):
                raise ValueError(f"{path.name}: wrong field count near physical line {reader.line_num}")
            digest_row(digest, row)
            count += 1
    return header, count, digest.hexdigest()


def run_checks(connection, path):
    """Execute the delivered check SQL and capture its actual result sets."""
    output = ["PART 2 IMPORT CHECKS", ""]
    statement = ""
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if not sqlite3.complete_statement(statement):
            continue
        cursor = connection.execute(statement)
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            if "status" in columns:
                if len(rows) != len(FILES) or any(row["status"] != "PASS" for row in rows):
                    raise ValueError("Live table counts failed import validation")
            output.append(" | ".join(columns))
            output.extend(" | ".join(str(value) for value in row) for row in rows)
            output.append("")
        statement = ""
    if statement.strip():
        raise ValueError(f"Incomplete SQL statement in {path.name}")
    return "\n".join(output).rstrip() + "\n"


def build(args):
    raw_dir, output, results = (p.resolve() for p in (args.raw_dir, args.output, args.results_dir))
    if output.exists():
        raise FileExistsError(f"Output exists: {output}. Choose a NEW --output filename.")
    for filename in FILES.values():
        if not (raw_dir / filename).is_file():
            raise FileNotFoundError(f"Missing {raw_dir / filename}")
    output.parent.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    imported_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    descriptor, name = tempfile.mkstemp(prefix=".olist-loading-", suffix=".db", dir=output.parent)
    os.close(descriptor)
    temporary = Path(name)
    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    checks = []
    try:
        connection.executescript((PROJECT / "sql/01_setup.sql").read_text(encoding="utf-8"))
        with connection:
            for table, filename in FILES.items():
                path = raw_dir / filename
                file_hash = sha256(path)
                header, source_count, logical_hash = inspect_csv(path)
                columns = [r["name"] for r in connection.execute(f'PRAGMA table_info("{table}")')]
                if header != columns:
                    raise ValueError(f"Header/schema mismatch: {filename}")
                placeholders = ",".join("?" for _ in header)
                insert_sql = f'INSERT INTO "{table}" VALUES ({placeholders})'
                # Preserve blank fields, accents, quoted commas and multiline text.
                # Do not trim, coerce types, filter or deduplicate source records.
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    reader = csv.reader(handle, strict=True)
                    next(reader)
                    while batch := list(itertools.islice(reader, 5000)):
                        connection.executemany(insert_sql, batch)
                loaded = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                db_digest = hashlib.sha256()
                for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                    digest_row(db_digest, list(row))
                if loaded != source_count or db_digest.hexdigest() != logical_hash:
                    raise ValueError(f"Import verification failed: {table}")
                if sha256(path) != file_hash:
                    raise ValueError(f"Source changed during import: {filename}")
                connection.execute(
                    "INSERT INTO import_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (table, filename, source_count, loaded, 0, file_hash, logical_hash,
                     sqlite3.sqlite_version, imported_at),
                )
                checks.append({"table_name": table, "source_rows": source_count,
                               "database_rows": loaded, "difference": loaded-source_count,
                               "rejected_rows": 0, "all_field_values_preserved": True,
                               "status": "PASS"})
                print(f"{table}: {source_count:,} source = {loaded:,} database; all values match")
        integrity = [r[0] for r in connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise ValueError(f"SQLite integrity failure: {integrity}")
        log = [dict(r) for r in connection.execute("SELECT * FROM import_log ORDER BY table_name")]
        purchase_range = dict(connection.execute(
            "SELECT MIN(NULLIF(order_purchase_timestamp,'')) AS first_raw_purchase, "
            "MAX(NULLIF(order_purchase_timestamp,'')) AS last_raw_purchase FROM orders"
        ).fetchone())
        validation_output = run_checks(connection, PROJECT / "sql/01_check_import.sql")
        connection.executescript((PROJECT / "sql/00_first_queries.sql").read_text(encoding="utf-8"))
        connection.close()
        connection = None
        # Exclusive creation protects an existing database, even during a race.
        try:
            with output.open("xb") as destination, temporary.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    destination.write(chunk)
        except FileExistsError:
            raise
        except BaseException:
            output.unlink(missing_ok=True)
            raise
        with (results / "part2_import_log.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(log[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(log)
        report = {
            "project": "E-commerce Performance Review: A SQL Consulting Case Study",
            "part": 2, "imported_at_utc": imported_at,
            "python_version": sys.version.split()[0], "sqlite_version": sqlite3.sqlite_version,
            "database": output.name, "database_sha256": sha256(output),
            "integrity_check": "ok", "source_tables": len(FILES),
            "source_records_total": sum(r["source_rows"] for r in checks),
            "counts_exclude_csv_headers": True,
            "csv_encoding": "UTF-8 (optional BOM accepted)",
            "storage_rule": "All source columns TEXT; empty fields stay empty strings",
            "field_verification": "SHA-256 of every decoded row, in source order, matches database",
            "checks": checks, "raw_purchase_timestamp_range": purchase_range,
            "business_analysis_status": "Not started; raw import only",
        }
        (results / "part2_verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (results / "part2_validation.txt").write_text(validation_output, encoding="utf-8")
        print(f"\nPASS: 8 tables; integrity_check=ok; database={output}")
    finally:
        if connection is not None:
            connection.close()
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=PROJECT / "data/raw")
    parser.add_argument("--output", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--results-dir", type=Path, default=PROJECT / "results")
    try:
        build(parser.parse_args())
    except Exception as exc:
        parser.exit(1, f"Import failed: {exc}\n")


if __name__ == "__main__":
    main()
