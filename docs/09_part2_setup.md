# Part 2 — Database setup and import

**Completed:** 1 October 2026

**Database:** SQLite 3.53.1

**Import runtime:** Python 3.12.14

**Source:** Olist dataset, version 2

## Objective

Create a reproducible database from the eight source files selected in the business brief and establish that the import preserved their records and values.

## Environment and design decisions

SQLite was selected because it stores the database in one portable file and supports local and browser SQL clients. The project SQL uses the SQLite dialect. Python handles CSV parsing and loading; it uses only standard-library modules.

The raw tables preserve all 47 source columns as TEXT. This retains identifiers, date strings, decimal strings, empty fields and the original column spelling. Empty CSV fields remain empty strings. Numeric types, SQL NULL conversions, duplicate rules and valid analysis dates will be established in Part 3.

Primary and foreign-key constraints are deferred for source tables until uniqueness and relationships have been profiled. The separate `import_log` audit table has a primary key on its table name. `v_import_row_counts` calculates current record counts from the eight source tables.

## Source acquisition

The official [Olist Kaggle dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) was downloaded on 1 October 2026. Kaggle metadata identified version 2. The selected CSVs were extracted unchanged into `data/raw/`; the detailed geolocation file was outside the agreed scope.

The [source manifest](../data/source_manifest.json) records filenames, file sizes, SHA-256 checksums, source URLs and the downloaded archive's checksum. The original CSVs and local database are excluded from Git and can be obtained or rebuilt using [the data instructions](../data/README.md).

## Import procedure

1. Check that all eight source files exist.
2. Create a new database using `sql/01_setup.sql`.
3. Validate CSV headers against the table definitions and count logical source records.
4. Load each file with parameterised inserts, preserving its decoded field values.
5. Compare loaded counts and row digests against the source, then check SQLite integrity.
6. Execute `sql/01_check_import.sql` and save the observed results.

The CSV parser handles quoted commas, accents and embedded newlines. No rows are filtered, deduplicated or silently skipped. A schema mismatch, malformed record or failed verification stops the build. An existing output database is never overwritten.

## Import results

| Table | Source records | Imported records | Rejected |
|---|---:|---:|---:|
| `orders` | 99,441 | 99,441 | 0 |
| `order_items` | 112,650 | 112,650 | 0 |
| `customers` | 99,441 | 99,441 | 0 |
| `products` | 32,951 | 32,951 | 0 |
| `sellers` | 3,095 | 3,095 | 0 |
| `order_payments` | 103,886 | 103,886 | 0 |
| `order_reviews` | 99,224 | 99,224 | 0 |
| `category_translation` | 71 | 71 | 0 |
| **Total** | **550,759** | **550,759** | **0** |

Counts exclude headers and represent logical CSV records, rather than physical text lines. This distinction matters for review comments containing newlines.

All source and database counts matched. For each table, a SHA-256 digest of every decoded row in source order matched the corresponding database digest. Source-file checksums were also unchanged during loading. `PRAGMA integrity_check` returned `ok`.

The raw purchase timestamp range is **2016-09-04 21:15:19** to **2018-10-17 17:30:18**. These boundaries do not establish complete reporting periods; the cleaning stage will assess coverage and delivery follow-up.

## Reproduction

Place the eight named CSV files in `data/raw/`, then run from the repository root:

```bash
python3 scripts/build_database.py
```

Outputs:

- `ecommerce_olist.db`: the populated database.
- `results/part2_import_log.csv`: table-level counts, checksums, version and import time.
- `results/part2_verification.json`: field-preservation and integrity outcomes, database hash and raw date range.
- `results/part2_validation.txt`: results of the supplied SQL checks.

For a separate run, use `--output ecommerce_olist_rebuilt.db --results-dir results/rebuilt`. New runs can have different database hashes because their audit records contain different import times. The source-file hashes and record counts identify the source snapshot.

`sql/01_setup.sql` defines an empty schema; CSV loading is performed by the Python script. Read-only inspection queries are in `sql/00_first_queries.sql`. Each statement can also be run in a SQLite client after opening the database.

## Handoff to Part 3

The import is complete. Next, profile identifiers, blanks, duplicate reviews, dates, numeric fields and relationships; define cleaning rules and complete the data dictionary. Import validation does not establish the validity of business metrics or join relationships.
