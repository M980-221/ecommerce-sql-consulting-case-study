# Verification results

## Part 2

| File | Contents |
|---|---|
| [part2_import_log.csv](part2_import_log.csv) | Source/import counts, rejected records, source and row digests, environment and import time |
| [part2_verification.json](part2_verification.json) | Field preservation, integrity and source totals |
| [part2_validation.txt](part2_validation.txt) | Result sets from the import checks |

## Part 3

| File | Contents |
|---|---|
| [part3_profile.json](part3_profile.json) | Missingness and distinct counts for all 47 fields, exact duplicates and date ranges |
| [part3_validation.json](part3_validation.json) | 62 checks, source fingerprints, script hashes, keys, joins, exceptions and metric populations |
| [part3_validation.txt](part3_validation.txt) | Human-readable check results and the observed SQL outputs |
| [part3_tests.txt](part3_tests.txt) | Output from 14 small automated tests |

The import and Part 3 gates pass. Source exceptions remain documented, including missing dates/categories and payment differences; passing checks do not erase those limitations.

Reproduce Part 3 with `python3 scripts/prepare_part3.py`. To keep another evidence snapshot, use `--results-dir results/rebuilt/part3`. Rerunning unchanged SQL on the same source produces the same profile and validation results. Import timestamps and database hashes in a new Part 2 rebuild can differ.

## Part 4

| File | Contents |
|---|---|
| [Monthly sales](part4_monthly_sales.csv) | 18 months, order counts, exclusions, product sales and AOV |
| [Monthly growth](part4_monthly_growth.csv) | Previous-month comparisons for sales, orders and AOV |
| [Comparable periods](part4_comparable_periods.csv) | February–July in 2017 and 2018, with year-on-year changes |
| [Category sales](part4_category_sales.csv) | All 74 labels, distinct order counts, item counts, shares and cumulative shares |
| [Regional sales](part4_regional_sales.csv) | All 27 buyer states, orders, sales, AOV and sales shares |
| [Validation report](part4_validation.json) | 15 checks, source fingerprints, script/output hashes, totals and status counts |
| [Readable validation](part4_validation.txt) | Check results and output row counts |
| [Test results](part4_tests.txt) | 10 sales tests and 14 cleaning tests |

Run `python3 scripts/analyse_sales.py` after Part 3. Use `--results-dir results/rebuilt/part4` to save another run. The script reads the database without modifying it, then exports results only after every check passes. All 139 rows and 1,036 cells match a second calculation using raw records, Python grouping and Decimal.

Amounts use source monetary units and exclude freight. Exact amounts are preserved in the `_cents` columns. Blank CSV cells mean NULL, not zero. Shares and AOV are rounded to two decimal places; growth uses the unrounded underlying amounts. Category order counts overlap when an order contains more than one category.

Findings and output definitions are in [Part 4](../docs/11_part4_sales.md). Delivery, customer analysis and the dashboard are still to come.
