# Validation log

Parts 2–7 are complete. Part 8 is complete: the workbook was executed, saved and visually reviewed in Tableau Public 2025.2 on Mac, then published to Tableau Public on 10 October 2026. The source export, offline workbook checks and native verification are recorded below. Earlier browser-prototype checks are retained as separate evidence. Part 3 passed **62 checks** and 14 synthetic test cases. Part 4 passed **15 checks** and 10 sales test cases; Part 5 passed **25 checks** and 12 delivery test cases. On 9 October 2026, Part 6 passed **26 checks** and 12 customer test cases; all **48 tests** passed together at that stage. Part 7 investigates payment reconciliation, traces five orders to their source records and checks reporting views against the combined business analysis.

Part 7 passed **34 checks** across **604 CSV rows and 10,111 cells**. The combined test run passed **68 tests: 20 Part 7 tests and 48 earlier tests**.

| Check | Result | Evidence |
|---|---|---|
| Imported rows and source values | 550,759 records; all field digests match | `results/part2_verification.json` |
| Raw records unchanged by cleaning | All eight post-cleaning digests match the Part 2 import | `results/part3_validation.json` |
| Clean views preserve raw row counts | All eight counts match | Part 3 `row_counts` |
| Required and composite keys | No missing keys or duplicate groups | Part 3 `key_checks` |
| Exact duplicate source records | None across all eight tables | `results/part3_profile.json` |
| Core relationships | Zero unmatched rows across six order/customer/item/product/seller/payment/review links | Part 3 `relationships` |
| Category enrichment | All 32,951 products retained; 610 missing categories and 13 untranslated | Part 3 `source_issues`, `join_reconciliation` |
| Numeric and timestamp formats | No unexpected nonblank formats | Part 3 checks |
| Every monetary conversion | Matches Python Decimal | Part 3 Decimal checks |
| Order model grain | 99,441 rows, 99,441 distinct order IDs | Part 3 `join_reconciliation` |
| Item, freight and payment totals after joins | Exact agreement with separate source totals | Part 3 `join_reconciliation` |
| Review selection accounting | 99,224 = 64 invalid + 548 additional valid + 98,612 selected | Part 3 `review_selection` |
| Delivery eligibility | 89,102 eligible; eight delivered period orders lack an actual timestamp | Part 3 `populations` |
| Repeat-customer identity | Model includes customer_unique_id; no sales order lacks it | Part 3 checks |
| SQLite integrity | ok | Part 3 checks |
| Small edge-case tests | 14 passed | `results/part3_tests.txt` |
| Sales output cells | All 139 rows / 1,036 cells match a separate raw-table Python and Decimal calculation | `results/part4_validation.json`; `scripts/sales_checks.py` |
| Sales totals by month, category and state | All reconcile to 1,223,065,213 integer hundredths | Part 4 validation |
| Sales population and state totals | 89,110 eligible orders; 2,670 period orders excluded | Part 4 validation |
| Sales edge cases and regression tests | 10 sales tests plus 14 cleaning tests passed | `results/part4_tests.txt` |
| Delivery output cells | All 310 rows / 2,409 cells match raw-table Python date calculations | `results/part5_validation.json`; `scripts/delivery_checks.py` |
| Delivery counts and exclusions | 89,102 eligible; 6,116 late; 2,670 non-delivered plus eight missing actual dates excluded | Part 5 overall and validation outputs |
| Monthly and state delivery totals | Included, late and on-time counts reconcile to the overall report | Part 5 validation |
| Category allocation | Repeated items removed at order/category grain; 89,822 memberships across 89,102 orders | Part 5 category output and validation |
| Seller coverage and cutoff | 87,946 single-seller orders; 1,156 multi-seller orders excluded; 190 sellers / 52,408 orders meet the 100-order minimum | Part 5 overall, seller and validation outputs |
| Delivery edge cases and regression tests | 12 delivery tests plus 24 earlier tests passed | `results/part5_tests.txt` |
| Customer output cells | All 56 rows / 534 cells match independent raw-record calculations | `results/part6_validation.json`; `scripts/customer_checks.py` |
| Review coverage and selection | 88,494 reviewed sales orders; 616 missing eligible reviews; raw review selection independently reproduced | Part 6 distribution and validation outputs |
| Customer identity and repeats | 86,271 persistent IDs; 2,562 with at least two eligible orders | Part 6 repeat-customer output |
| Spending reconciliation | All customer groups sum to 89,110 orders and 1,223,065,213 integer hundredths, matching Part 4 | Part 6 validation |
| Review comparison coverage and timing | 88,486 reviewed orders have delivery eligibility; 4,445 selected responses precede receipt | Part 6 delivery-review output and validation |
| Customer edge cases and regression tests | 12 customer tests plus 36 earlier tests passed | `results/part6_tests.txt` |
| Part 7 output cells | All 604 rows / 10,111 cells match independent raw-record calculations | `results/part7_validation.json`; `scripts/validation_checks.py` |
| Source/model order IDs | Zero source IDs absent from the model and zero model IDs absent from the source; distinct counts also match | `results/part7_population_validation.csv` |
| Source payment reconciliation investigation | 98,665 comparable orders: 98,089 exact matches, 273 one-cent differences and 303 larger differences; causes remain unconfirmed | `results/part7_reconciliation_summary.csv`; `results/part7_reconciliation_exceptions.csv` |
| Reconciliation patterns and missingness | All nonzero differences exported; absent items/payments stay separate from exact matches; missingness reported by five populations | `results/part7_reconciliation_patterns.csv`; `results/part7_missingness_by_population.csv` |
| Five order walkthroughs | Exact match, multiple items/payments, one-cent difference, larger difference and absent payment traced to raw rows | `results/part7_order_walkthroughs.json`; [Part 7 notes](14_part7_validation.md#five-orders-traced-to-the-source) |
| Unsafe join demonstration | Deliberate item/payment join repeats source amounts; the correctly aggregated reporting model is unchanged | `results/part7_join_fanout_summary.csv` |
| Reporting view grains | 91,780 orders; 101,825 sales items; 89,822 order/category pairs; 86,271 persistent customers; keys checked at each grain | Part 7 `reporting_view_rows` and checks |
| Reporting aggregates | Monthly/category sales and delivery, state reviews and customer totals match the published Parts 4–6 results | `results/part7_validation.json` |
| Source and schema preservation | Fingerprints checked before/after; reporting views created in a transaction; existing tables, indexes and analytical views unchanged | Part 7 checks and `source_tables` |
| Order-item lookup experiment | Both query variants return identical results in single-item and multiple-item cases; existing index inspected | `results/part7_performance.json` |
| Part 7 edge cases and regressions | 11 validation tests, nine reporting tests and 48 earlier tests passed | `results/part7_tests.txt` |
| Dashboard calculation code | Eight full/filtered/empty selections; 13,129 values match independent SQLite groups, and 18 default metrics match Parts 4–6 | `results/part8_validation.json` |
| Dashboard data export | 91,780 order rows, 89,830 category pairs and 1,550,510 decoded cells checked; 511 published count/money comparisons pass | `results/part8_export_validation.json` |
| Browser rendering and manual accessibility | Open: required browser-testing capability unavailable; static data previews are not browser screenshots | [Part 8 verification scope](15_part8_dashboard.md) |

## Remaining source exceptions

Part 4 opens the database read-only and verifies every raw-table fingerprint against the published Part 2 snapshot. Its independent check uses raw records, Python grouping and Decimal; it does not reuse the analytical views or SQL aggregates. The five CSV outputs retain exact integer amounts beside display values. Blank CSV cells represent NULL, including growth with no prior period or a zero denominator.

Part 5 also reads the database without modifying it. Its second calculation uses raw records and Python datetime, with elapsed seconds for delivery duration and calendar-date differences for lateness. It independently builds category memberships and seller groups. The check caught a mean positive delay of exactly 9.825 days that SQLite's two-place ROUND displayed as 9.82. The report now rounds integer delay totals consistently to 9.83, with a dedicated test. NULL still represents an undefined late-only mean when no late orders exist.

Part 6 independently selects reviews from the raw history, then groups raw orders by persistent customer ID. It reproduces the full-source selection accounting: 99,224 review rows = 64 invalid + 548 additional valid rows + 98,612 selected reviews. In the sales population, 613 orders have no source review and three have only ineligible reviews. Missing reviews stay outside score averages. Tests cover changing customer_id for the same person, repeated items/payments/reviews, review ties, same-time orders, reporting boundaries and applying the top-20 limit after aggregation. Exact halfway scores, rates and AOV round up consistently.

The [cleaning decision table](10_part3_cleaning.md#decisions-and-evidence) records how missing categories, review chronology, inconsistent delivery events, zero payments and future shipping deadlines are handled. No values were changed merely to make a check pass.

The reporting window, review selection and metric-specific exclusions are part of the analysis definition. They should accompany any later comparisons or recommendations.

## Part 7 reconciliation and reporting checks

The six validation outputs are recalculated independently from raw records with Python grouping, dates and Decimal money. The checker does not read prepared views or use SQL joins or aggregates. It verifies source keys and relationships, reproduces review selection and compares every exported cell. The population query also checks order IDs in both directions between source and model: equal counts alone could hide one lost ID and one unexpected ID. Separate reporting-view checks compare counts and exact monetary/score totals with the published Parts 4–6 files.

The **576 nonzero payment differences** consist of 273 one-cent cases and 303 larger cases. Their signed sum is **+2,870.39** source monetary units and their absolute sum is **3,271.95**. All one-cent cases have multiple items, but that association does not establish why the source values differ. Missing sides remain `NULL` rather than being replaced with zero. In the sales population, 495 affected orders contribute 104,021.36 in product value. No monetary value or eligibility rule was changed to force agreement.

Five selected orders have their item, payment and review rows recorded beside independently checked totals and eligibility flags. They include an order with two items and two payments: a direct item/payment join would make four rows. That intentionally unsafe query is a diagnostic example, not a failure in the published model. The model aggregates the sources separately before joining.

The reporting views retain distinct row meanings: one order, one sales item, one delivery order/category pair and one persistent sales customer. Category memberships overlap across categories. Full-window customer totals also need to be recalculated from filtered orders when a future dashboard changes the date or state selection. SQL checks do not verify future dashboard relationships, filters or displayed measures.

Run `python3 scripts/validate_part7.py` from the repository folder after Parts 4–6. The runner verifies the source fingerprints against Part 2, applies the four reporting views transactionally and rolls back if a database check fails. It confirms that raw records and the pre-existing schema remain unchanged, then exports the evidence after validation succeeds. See [Part 7](14_part7_validation.md), [recorded checks](../results/part7_validation.txt) and [test results](../results/part7_tests.txt).

## Performance experiment

Part 7 compares an item-detail lookup using `TRIM(order_id) = ?` with `order_id = ?`. All source item order IDs were checked for blanks and surrounding spaces before treating the results as equivalent. The direct predicate can use the existing order-ID index added in Part 3; the experiment adds no index and changes no records.

The benchmark records `EXPLAIN QUERY PLAN`, environment details and timings for one single-item order and one multiple-item order. Each variant has three warmups and 20 measured runs per case, with alternating execution order; execute and full fetch are timed. Every run must return the same rows before a timing comparison is accepted. See [the recorded benchmark](../results/part7_performance.json).

| Lookup case | Trimmed predicate, median ms | Direct predicate, median ms |
|---|---:|---:|
| One item | 9.139 | 0.016 |
| 21 items | 7.850 | 0.037 |

This measures a narrow lookup against the current database with a warm cache. The trimmed predicate is an intentionally inefficient comparison, not a previously published analysis query. Results depend on the machine, cache and concurrent work; they do not establish a speed improvement for the full analysis, a dashboard refresh or another database engine.

## Part 8 dashboard checks

The export reads the database without changing it and checks every encoded cell before saving `dashboard/data.js`. Stable customer indexes preserve the same identity across months and states while omitting source IDs and unnecessary text. Category sales and delivery membership remain separate measures, even where they share a row.

Node executes the actual browser calculation module. A separate SQLite calculation checks every output field across eight selections, including all data, March 2018, SP, RJ, March 2018/RJ, February–July 2018, RR and an empty August 2017/RR slice. All 13,129 values agree. The empty slice has zero counts and NULL means/rates, with no NaN or Infinity. Eighteen default headlines also agree with the published analysis. See [dashboard validation](../results/part8_validation.txt).

The 13 metric fixture tests cover filtered customer regrouping, missing reviews, exact rounding, zero denominators and category allocation. Five exporter fixtures bring the Python suite to 73 passing tests. These calculation checks do not establish that CSS layouts or assistive-technology interactions work in a real browser. The three supplied SVGs are explicitly labelled static data previews.

Nine additional [interface fixture tests](../results/part8_ui_tests.txt) exercise the actual page templates and event handlers using a small DOM fixture in Node. They cover navigation, month/state changes, reset, crossed month endpoints, empty states, CSV Blob creation and URL cleanup, ranking expansion and missing-data recovery. This tests application wiring without claiming real-browser layout or accessibility coverage.

## Tableau workbook revision

The primary Part 8 deliverable is now a packaged Tableau workbook. The exporter compares all 2,273,050 CSV cells with the validated reporting data and reconciles 511 published totals. The database is opened read-only, all eight source fingerprints match the recorded snapshot, and no raw source values are changed. The two sources contain 91,780 orders and 89,830 order/category pairs.

See [Tableau export evidence](../results/tableau_export_validation.txt), [workbook verification](../results/tableau_validation.txt) and the [Tableau walkthrough](16_tableau_dashboard.md). Workbook schema/package checks and an independent calculation model are separate from Tableau runtime validation. The original draft's remaining native checks were completed for the finished package in the revision below. Earlier browser tests and previews do not verify the Tableau file.


## Tableau native verification — 10 October 2026

The finished [Tableau package](../tableau/Olist_Commerce_Review_Validated.twbx) was opened and saved in Tableau Public 2025.2 on Mac. All three dashboards were visually inspected. All 12 KPI cards matched their full-period reference values and their March 2018/RJ values; shared controls were exercised and the workbook was returned to its defaults. The package contains 21 worksheets, three dashboards, two Hyper extracts and the data licence.

See the [native verification record](../results/tableau_native_verification.json) for the package hash and observed values, and the [comparison table](../tableau/README.md#verified-figures). The application checks cover two selections and the dashboard layouts, not every possible combination or tooltip. The original CSV-based draft and its offline reports remain available separately.

## Tableau presentation and publication update — 10 October 2026

- Enlarged all three dashboards to 1400 × 850 and replaced the gallery with direct presentation-mode captures.
- Added readable field/category labels and compact k/M axes; exact amounts remain in tooltips. The Health & beauty tooltip shows 1,097,800.05.
- Made late/eligible counts visible beside delivery rates. The default Home comfort 2 result is 3 / 22 (13.64%). Monthly labels may be suppressed to prevent overlap; counts remain available in tooltips.
- Rechecked all 12 KPI cards at the default selection and March 2018/RJ. The original calculation definitions and embedded Hyper files are unchanged; four display measures reference existing calculations for axis formatting.
- Saved the final package through Tableau and published [the interactive workbook](https://public.tableau.com/app/profile/mohammed.baquaysh/viz/Olist_Commerce_Review_Validated/Sales). See the [native verification record](../results/tableau_native_verification.json) for the current package fingerprint and check scope.
