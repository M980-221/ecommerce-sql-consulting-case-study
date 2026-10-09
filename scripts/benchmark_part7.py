"""Compare two equivalent item-detail lookups using the existing order index."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
from time import perf_counter


PROJECT = Path(__file__).resolve().parents[1]
LOOKUP_COLUMNS = """order_id, order_item_id, product_id, seller_id,
       price_cents, freight_value_cents"""
QUERIES = {
    "trimmed_lookup": f"""SELECT {LOOKUP_COLUMNS}
FROM v_clean_order_items
WHERE TRIM(order_id) = ?
ORDER BY order_item_id, product_id, seller_id, price_cents, freight_value_cents""",
    "direct_lookup": f"""SELECT {LOOKUP_COLUMNS}
FROM v_clean_order_items
WHERE order_id = ?
ORDER BY order_item_id, product_id, seller_id, price_cents, freight_value_cents""",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                                     sort_keys=True).encode("utf-8")).hexdigest()


def lookup(connection, sql, order_id):
    cursor = connection.execute(sql, (order_id,))
    return [tuple(row) for row in cursor.fetchall()]


def benchmark(connection, repetitions=20, warmups=3):
    """Return timings and evidence; execute only SELECT and inspection PRAGMAs.

    Each repetition runs both variants. AB/BA alternation balances execution order.
    Timing covers execute plus full fetch; comparisons and hashes are untimed.
    The caller owns its connection and transaction. The CLI opens read-only.
    """
    if repetitions < 2 or repetitions % 2:
        raise ValueError("repetitions must be an even integer of at least 2")
    if warmups < 1:
        raise ValueError("warmups must be at least 1")
    invalid_ids = connection.execute("""
        SELECT COUNT(*) FROM order_items
        WHERE order_id IS NULL OR TRIM(order_id) = '' OR order_id != TRIM(order_id)
    """).fetchone()[0]
    if invalid_ids:
        raise ValueError("Lookup equivalence requires nonblank IDs without surrounding spaces")
    cases = []
    for label, condition, ordering in [
        ("single_item", "COUNT(*) = 1", "order_id ASC"),
        ("multiple_items", "COUNT(*) > 1", "item_count DESC, order_id ASC"),
    ]:
        row = connection.execute(f"""
            SELECT order_id, COUNT(*) AS item_count FROM order_items
            GROUP BY order_id HAVING {condition} ORDER BY {ordering} LIMIT 1
        """).fetchone()
        if row is None:
            raise ValueError(f"No {label} order exists for the benchmark")
        cases.append((label, row[0], row[1]))

    schema = [tuple(row) for row in connection.execute("""
        SELECT type, name, tbl_name, sql FROM sqlite_master
        ORDER BY type, name, tbl_name
    """)]
    report = {
        "experiment": "Order item detail lookup: trimmed predicate versus direct predicate",
        "purpose": "Retrieve the item rows for an order during the manual reconciliation walkthrough.",
        "scope": "A selective lookup on this SQLite snapshot; not the full analysis or dashboard refresh.",
        "precondition": "All source item order IDs are nonblank and have no surrounding spaces.",
        "invalid_order_ids": invalid_ids,
        "source_item_rows": connection.execute("SELECT COUNT(*) FROM order_items").fetchone()[0],
        "environment": {
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "schema_sha256": digest(schema),
            "page_size": connection.execute("PRAGMA page_size").fetchone()[0],
            "cache_size": connection.execute("PRAGMA cache_size").fetchone()[0],
            "automatic_index": connection.execute("PRAGMA automatic_index").fetchone()[0],
            "item_indexes": [dict(name=row[0], sql=row[1]) for row in connection.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='order_items' ORDER BY name")],
        },
        "method": {
            "timer": "time.perf_counter",
            "timed_work": "SQLite execute and full fetch; no result hashing or comparison inside timer",
            "cache": "Warm cache; no cache flush or cold-start claim",
            "warmups_per_variant_per_case": warmups,
            "measured_repetitions_per_variant_per_case": repetitions,
            "execution_order": "AB then BA on alternating repetitions",
            "mutations": "None; no tables, records or indexes are created or changed",
        },
        "limitations": [
            "Wall-clock timings depend on the machine, cache and concurrent work.",
            "The trimmed predicate is an intentionally inefficient diagnostic comparison, not a previously published analysis query.",
            "The direct predicate can use the existing order_items(order_id) index; no new index is proposed.",
            "The result does not establish an improvement for aggregate queries, larger datasets or other database engines.",
        ],
        "cases": [],
    }

    for label, order_id, item_count in cases:
        reference = lookup(connection, QUERIES["direct_lookup"], order_id)
        if len(reference) != item_count:
            raise AssertionError("Clean item lookup changed the source row count")
        reference_hash = digest(reference)
        case = {
            "case": label,
            "order_id": order_id,
            "selection": "First order ID with one item" if label == "single_item"
                         else "Largest item count, with order ID ascending as tiebreaker",
            "result_rows": len(reference),
            "result_sha256": reference_hash,
            "variants": {},
            "runs": [],
        }
        for name, sql in QUERIES.items():
            case["variants"][name] = {
                "sql": sql,
                "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                "parameters": [order_id],
                "explain_query_plan": [list(row) for row in connection.execute(
                    "EXPLAIN QUERY PLAN " + sql, (order_id,))],
            }
        for run in range(warmups):
            names = list(QUERIES) if run % 2 == 0 else list(reversed(QUERIES))
            for name in names:
                if lookup(connection, QUERIES[name], order_id) != reference:
                    raise AssertionError(f"{label}/{name}: warmup result differs")
        times = {name: [] for name in QUERIES}
        for run in range(repetitions):
            names = list(QUERIES) if run % 2 == 0 else list(reversed(QUERIES))
            for position, name in enumerate(names, 1):
                started = perf_counter()
                rows = lookup(connection, QUERIES[name], order_id)
                elapsed_ms = (perf_counter() - started) * 1000
                if rows != reference:
                    raise AssertionError(f"{label}/{name}: measured result differs")
                times[name].append(elapsed_ms)
                case["runs"].append({
                    "repetition": run + 1, "position": position, "variant": name,
                    "elapsed_ms": elapsed_ms, "result_rows": len(rows),
                    "result_sha256": digest(rows),
                })
        for name, timings in times.items():
            case["variants"][name].update({
                "min_ms": min(timings), "median_ms": statistics.median(timings),
                "max_ms": max(timings), "all_timings_ms": timings,
            })
        direct_median = statistics.median(times["direct_lookup"])
        case["median_ratio_trimmed_to_direct"] = (
            statistics.median(times["trimmed_lookup"]) / direct_median if direct_median else None)
        case["result_identity_verified"] = True
        report["cases"].append(case)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=PROJECT / "ecommerce_olist.db")
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--output", type=Path, help="Save JSON here; omitted means standard output")
    args = parser.parse_args()
    with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        report = benchmark(connection, args.repetitions, args.warmups)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
