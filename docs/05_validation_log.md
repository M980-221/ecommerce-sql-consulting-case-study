# Validation log

Parts 2 and 3 are complete. The full Part 3 run passed **62 checks** on 6 October 2026. Its 14 synthetic test cases also passed. Part 7 will investigate the remaining business reconciliation questions and validate the analysis outputs.

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
| Source payment reconciliation investigation | Open: 273 one-cent differences and 303 larger differences | Part 3 `payment_reconciliation`; investigate in Part 7 |
| Five manual order walkthroughs | Pending Part 7 | |
| Business query and dashboard figures | Pending analysis/dashboard stages | |

## Remaining source exceptions

The [cleaning decision table](10_part3_cleaning.md#decisions-and-evidence) records how missing categories, review chronology, inconsistent delivery events, zero payments and future shipping deadlines are handled. No values were changed merely to make a check pass.

The reporting window, review selection and metric-specific exclusions are part of the analysis definition. They should accompany any later comparisons or recommendations.

## Performance experiment

Lookup indexes are included in Part 3 to support joins on the verified string IDs. A repeatable before/after timing experiment with an execution plan remains Part 7 work. No percentage speed improvement is claimed.
