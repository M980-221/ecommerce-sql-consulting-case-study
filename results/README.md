# Verification results

The build script generates these Part 2 outputs:

| File | Contents |
|---|---|
| [part2_import_log.csv](part2_import_log.csv) | Source and imported counts, rejected records, file and row digests, SQLite version and import time |
| [part2_verification.json](part2_verification.json) | Field-preservation checks, database integrity, source totals, database hash and raw date range |
| [part2_validation.txt](part2_validation.txt) | Observed result sets from `sql/01_check_import.sql` |

All eight imports passed. These outputs verify the import; business analysis, cleaned-data validation and dashboard reconciliation are later stages.

To reproduce the evidence without replacing this snapshot, build with `--output ecommerce_olist_rebuilt.db --results-dir results/rebuilt`. Import timestamps and the database hash can change between runs.
