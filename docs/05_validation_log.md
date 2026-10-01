# Validation log

Status: Part 2 import validation completed on 1 October 2026. Cleaning and business metric validation remain pending.

| Check | Expected result | Status | Evidence |
|---|---|---|---|
| Imported row counts vs source files | Match or documented exclusions | PASS: 8/8 tables, 550,759 records, zero rejections | [Import log](../results/part2_import_log.csv) |
| Source field preservation | All decoded values retained | PASS: row digests match for all tables | [Verification report](../results/part2_verification.json) |
| SQLite file integrity | ok | PASS | [SQL check output](../results/part2_validation.txt) |
| Required identifier missingness | Investigated and handled explicitly | Pending | |
| Orders and other intended keys | Unique at the stated grain | Pending | |
| Foreign-key relationships | Unmatched rows investigated | Pending | |
| Multiple payments/items/reviews | Correctly handled before joins | Pending | |
| Product sales value before/after joins | No unintended inflation | Pending | |
| Order count before/after joins | Differences explained | Pending | |
| Delivery dates | Invalid or missing dates excluded consistently | Pending | |
| Review scores and duplicates | Valid scores and documented selection rule | Pending | |
| Repeat customers | customer_unique_id used | Pending | |
| Five manually checked orders | Calculations agree with source records | Pending | |
| Dashboard KPIs vs SQL outputs | Match for identical filters | Pending | |

## Performance experiment

Record query, database version, data size, execution plan, measured time before and after a change, and why the results remained identical. Only claim a speed improvement if measured.

## Decisions

Record issue, evidence, chosen rule, reason and affected row count.
