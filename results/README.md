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

Findings and output definitions are in [Part 4](../docs/11_part4_sales.md). The delivery results are below; customer analysis and the dashboard are still to come.

## Part 5

| File | Contents |
|---|---|
| [Overall delivery](part5_overall_delivery.csv) | Eligible/excluded counts, late rate, duration, positive delay and seller coverage |
| [Monthly delivery](part5_monthly_delivery.csv) | All 18 purchase months and their final observed outcomes |
| [Regional delivery](part5_regional_delivery.csv) | All 27 buyer states, with counts and rates |
| [Category delivery](part5_category_delivery.csv) | 74 labels; one observation per distinct order and category |
| [Seller delivery](part5_seller_delivery.csv) | 190 sellers with at least 100 eligible single-seller orders each |
| [Validation report](part5_validation.json) | 25 checks, raw-record counts, source/script/output hashes and coverage |
| [Readable validation](part5_validation.txt) | Checks, report sizes and compared cell count |
| [Test results](part5_tests.txt) | 12 delivery tests plus 24 earlier tests |

Run `python3 scripts/analyse_delivery.py` after Part 3. Use `--results-dir results/rebuilt/part5` for another output folder. All 310 rows and 2,409 cells are compared with a separate calculation using raw records and Python dates before export. The database is opened read-only. Run all automated tests with `python3 -m unittest discover -s tests -v`.

Delivery duration uses elapsed recorded timestamps; positive delay uses calendar days and averages late orders only. Counts remain integers, while rates and durations are displayed to two decimal places. Exact halfway values in positive-delay means round up. Blank cells mean NULL, including a mean positive delay for a group with no late orders.

Category counts overlap across categories and must not be added as unique orders. The seller report excludes multi-seller orders and sellers below its stated sample threshold; coverage is in the overall report. Full definitions, findings and practice queries are in [Part 5](../docs/12_part5_delivery.md).
