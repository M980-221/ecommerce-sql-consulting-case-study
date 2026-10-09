# Validation log

Parts 2–6 are complete. Part 3 passed **62 checks** and 14 synthetic test cases. Part 4 passed **15 checks** and 10 sales test cases; Part 5 passed **25 checks** and 12 delivery test cases. On 9 October 2026, Part 6 passed **26 checks** and 12 customer test cases. All **48 tests** passed together. Part 7 will investigate the remaining reconciliation questions and review the combined business analysis.

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
| Source payment reconciliation investigation | Open: 273 one-cent differences and 303 larger differences | Part 3 `payment_reconciliation`; investigate in Part 7 |
| Five manual order walkthroughs | Pending Part 7 | |
| Dashboard figures | Pending Parts 7–8 | |

## Remaining source exceptions

Part 4 opens the database read-only and verifies every raw-table fingerprint against the published Part 2 snapshot. Its independent check uses raw records, Python grouping and Decimal; it does not reuse the analytical views or SQL aggregates. The five CSV outputs retain exact integer amounts beside display values. Blank CSV cells represent NULL, including growth with no prior period or a zero denominator.

Part 5 also reads the database without modifying it. Its second calculation uses raw records and Python datetime, with elapsed seconds for delivery duration and calendar-date differences for lateness. It independently builds category memberships and seller groups. The check caught a mean positive delay of exactly 9.825 days that SQLite's two-place ROUND displayed as 9.82. The report now rounds integer delay totals consistently to 9.83, with a dedicated test. NULL still represents an undefined late-only mean when no late orders exist.

Part 6 independently selects reviews from the raw history, then groups raw orders by persistent customer ID. It reproduces the full-source selection accounting: 99,224 review rows = 64 invalid + 548 additional valid rows + 98,612 selected reviews. In the sales population, 613 orders have no source review and three have only ineligible reviews. Missing reviews stay outside score averages. Tests cover changing customer_id for the same person, repeated items/payments/reviews, review ties, same-time orders, reporting boundaries and applying the top-20 limit after aggregation. Exact halfway scores, rates and AOV round up consistently.

The [cleaning decision table](10_part3_cleaning.md#decisions-and-evidence) records how missing categories, review chronology, inconsistent delivery events, zero payments and future shipping deadlines are handled. No values were changed merely to make a check pass.

The reporting window, review selection and metric-specific exclusions are part of the analysis definition. They should accompany any later comparisons or recommendations.

## Performance experiment

Lookup indexes are included in Part 3 to support joins on the verified string IDs. A repeatable before/after timing experiment with an execution plan remains Part 7 work. No percentage speed improvement is claimed.
