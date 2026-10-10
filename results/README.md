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

Findings and output definitions are in [Part 4](../docs/11_part4_sales.md). The delivery, customer and dashboard results are below.

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

## Part 6

| File | Contents |
|---|---|
| [Review distribution](part6_review_distribution.csv) | Scores 1–5 plus missing eligible reviews; shares and coverage |
| [Delivery and reviews](part6_delivery_reviews.csv) | On-time and late groups, review denominators, scores and response timing |
| [Customer spending](part6_customer_spending.csv) | Top 20 persistent customer IDs by product value within the reporting window |
| [Repeat customers](part6_repeat_customers.csv) | All eligible customers, one-time/repeat groups, order counts and product value |
| [Regional reviews](part6_regional_reviews.csv) | All 27 buyer states, review coverage, score totals and low-score counts |
| [Validation report](part6_validation.json) | 26 checks, independent totals, review-selection accounting and file hashes |
| [Readable validation](part6_validation.txt) | Checks, report sizes and compared cell count |
| [Test results](part6_tests.txt) | 12 customer tests plus 36 earlier tests |

Run `python3 scripts/analyse_customers.py` after Part 3 preparation. The runner also checks customer totals against the published Part 4 evidence. Use `--results-dir results/rebuilt/part6` for another output folder. All 56 rows and 534 cells match a separate calculation using raw records, Python grouping, dates and Decimal. Run the full test suite with `python3 -m unittest discover -s tests -v`.

Review means and low-score shares exclude missing reviews. The missing-review bucket has a blank score and a blank share of reviewed orders. Other blank cells represent undefined values, not zero. Part 6 display ratios use exact half-up rounding to two decimal places; integer counts, score sums and monetary hundredths remain available.

The spending table applies its top-20 limit after grouping all eligible customers. The repeat summary still includes the entire customer population. Repeat means at least two eligible order IDs within the window; it does not measure retention or churn. The delivery comparison retains valid selected reviews submitted before receipt and reports their counts. Full definitions and practice queries are in [Part 6](../docs/13_part6_customers.md).

## Part 7

| File | Contents |
|---|---|
| [Population validation](part7_population_validation.csv) | Source/model grain, IDs checked in both directions, metric populations, source monetary totals and selected-review counts |
| [Reconciliation summary](part7_reconciliation_summary.csv) | Exact matches, one-cent and larger differences, and missing item/payment sides |
| [Reconciliation patterns](part7_reconciliation_patterns.csv) | Difference direction, vouchers, multiple items/payments and zero payment components |
| [Reconciliation exceptions](part7_reconciliation_exceptions.csv) | Every comparable nonzero difference: 576 orders, including all 273 one-cent cases |
| [Unsafe join demonstration](part7_join_fanout_summary.csv) | Correct source totals beside the inflated amounts from an intentionally unsafe item/payment join |
| [Missingness by population](part7_missingness_by_population.csv) | Missing items, payments, reviews and dates across five defined populations |
| [Five order walkthroughs](part7_order_walkthroughs.json) | Raw item/payment/review rows, checked arithmetic and eligibility for five selected orders |
| [Lookup performance](part7_performance.json) | Equivalent trimmed/direct predicates, query plans, result checks, warm-cache timings and environment |
| [Validation report](part7_validation.json) | 34 checks, raw-record comparisons, reporting-view checks, fingerprints, dependencies and output hashes |
| [Readable validation](part7_validation.txt) | Check results, CSV row/cell counts and reporting-view sizes |
| [Test results](part7_tests.txt) | 11 validation tests, nine reporting tests and 48 earlier tests; all 68 passed |

Run `python3 scripts/validate_part7.py` after preparing the database and completing Parts 4–6. Use `--results-dir results/rebuilt/part7` for another evidence folder. The runner recalculates the six CSV outputs independently from raw records, traces the five orders and checks reporting aggregates against the published Parts 4–6 files. It also runs the lookup benchmark. To repeat only that experiment without changing the database, run `python3 scripts/benchmark_part7.py`; JSON is printed to standard output unless `--output` is supplied.

All **34 checks** passed, with **604 CSV rows and 10,111 cells** matching the independent calculation. The full test suite passed **68 tests**. Run it with `python3 -m unittest discover -s tests -v`.

Part 7 creates four reporting views in a transaction and confirms that the source records, existing tables, indexes and analytical views are unchanged. The views contain **91,780 period orders, 101,825 sales items, 89,822 delivery order/category pairs and 86,271 persistent sales customers**. Each has a documented grain; counts across categories overlap, and customer summaries describe the full window. The raw-table fingerprints are checked before and after view creation.

Payment differences are `payments - product prices - freight`, in integer hundredths. A blank cell means `NULL`, including a comparison with a missing side. The 303 larger differences remain source exceptions with unconfirmed causes; no amounts or eligibility rules were changed. The unsafe join output deliberately demonstrates repeated amounts and is not a production reporting result.

Benchmark timings describe a selective order-item lookup using the existing index, with three warmups and 20 measured runs per variant and case. Every result is checked for equality. The experiment does not claim that aggregate queries or dashboard refreshes improve by the same amount, and its timings will vary by environment.

Findings, five worked examples and practice SQL are in [Part 7](../docs/14_part7_validation.md). The Part 8 checks below cover dashboard headline values and filter behaviour.

## Part 8

| File | Contents |
|---|---|
| [Export validation](part8_export_validation.json) | 1,550,510 encoded cells and 511 published count/money comparisons; source fingerprints and data hash |
| [Readable export checks](part8_export_validation.txt) | Export sizes, row counts and preservation checks |
| [Dashboard calculations](part8_validation.json) | Eight filter scenarios and 13,129 fields compared with independent SQLite results; 18 published default metrics |
| [Readable calculation checks](part8_validation.txt) | Scenario populations, empty selection and verification scope |
| [Python tests](part8_python_tests.txt) | Five exporter fixtures and 68 earlier tests; all 73 pass |
| [JavaScript metric tests](part8_js_tests.txt) | 13 fixtures for filtering, customer identity, weighted means, category allocation and rounding |
| [Interface fixture tests](part8_ui_tests.txt) | Nine Node DOM-fixture tests for templates, navigation, filters, reset, CSV download and empty/error states |

Run `python3 scripts/export_dashboard.py`, then `python3 scripts/validate_dashboard.py` with Node.js available. The first command writes the checked browser data; the second executes the actual JavaScript calculations and compares them with SQLite groups. Both open the database read-only. Counts and monetary hundredths remain exact. Undefined means and rates remain NULL and are displayed as dashes.

Run the suites with `python3 -m unittest discover -s tests -v`, `node --test tests/test_dashboard.mjs` and `node --test tests/test_dashboard_ui.mjs`. The interface tests use a small DOM fixture in Node, not a real browser. CSS rendering and manual accessibility checks remain outstanding because the required browser-testing capability was unavailable.

The [three SVG previews](../dashboard/screenshots/) are generated from the actual default calculation results with `python3 scripts/render_dashboard_previews.py`. They are labelled static data previews and are not browser screenshots. See [Part 8](../docs/15_part8_dashboard.md) and [web prototype instructions](../dashboard/PROTOTYPE.md).

The [deployment record](part8_deployment.json) identifies the private hosted version and the hashes of its deployed assets. Native hosting status confirms publication; it does not replace browser visual testing.

## Tableau revision of Part 8

| File | Evidence |
|---|---|
| `tableau_export_validation.json` / `.txt` | Read-only export, source fingerprints, 2,273,050 checked cells and 511 published-total reconciliations |
| `tableau_validation.json` / `.txt` | Workbook/schema/package checks and independent calculation-model comparisons; see report for exact scope |

The original draft uses `tableau/data/orders.csv`, `tableau/data/categories.csv` and `tableau/Olist_Commerce_Review.twbx`. The finished `tableau/Olist_Commerce_Review_Validated.twbx` was subsequently opened, saved and checked in Tableau Public 2025.2 on Mac. All 12 KPI cards matched the full-period and March 2018/RJ references. See the [native verification record](tableau_native_verification.json) and [actual Tableau screenshots](../tableau/README.md#dashboard-screenshots). The earlier JavaScript checks apply only to the browser prototype.
