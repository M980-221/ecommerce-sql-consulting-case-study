# Technical walkthrough

Current scope: Parts 1 and 2 are complete. The repository demonstrates problem definition, database setup, source preservation and import verification.

## Business context

The case study asks where an e-commerce manager should focus to improve sales performance, delivery reliability and customer experience. Six questions and working metric definitions are recorded in the business brief. Recommendations depend on later analysis.

## Explain and demonstrate

| Topic | Explanation | Repository evidence |
|---|---|---|
| Environment choice | SQLite provides a portable database and supports local and browser clients | `docs/09_part2_setup.md` |
| SQL and Python roles | SQL defines tables and checks; Python parses and loads the CSV files | `sql/01_setup.sql`, `scripts/build_database.py` |
| Raw storage | Source fields remain TEXT so import does not silently change values | `sql/01_setup.sql` |
| CSV handling | A CSV parser handles embedded commas, quoted fields and multiline reviews | `scripts/build_database.py` |
| Record counts | All 550,759 source records across eight tables were imported, including 99,441 orders | `results/part2_import_log.csv` |
| Verification | Source/database counts, decoded-row digests and database integrity were checked | `results/part2_verification.json` |
| Next step | Profile keys, blanks, duplicates, dates and relationships before writing business metrics | `docs/02_project_plan.md` |

## Demonstration queries

Open the database and explain these two queries:

```sql
SELECT COUNT(*) AS total_orders FROM orders;

SELECT table_name, database_rows
FROM v_import_row_counts
ORDER BY table_name;
```

Then open `sql/01_check_import.sql` and explain how the live counts are compared with the source counts.

## Questions to prepare

- Why is a raw TEXT import useful, and what work must happen before analysis?
- Why does counting text lines give the wrong answer for some review CSVs?
- What does a matching checksum establish, and what does it not establish?
- What is the difference between 550,759 records and 99,441 orders?
- Why can joining items and payments directly multiply rows?
- What checks should be completed before enforcing primary and foreign keys?

Business findings, dashboards and recommendations will be added as those stages are completed.
