# Part 3 — Cleaning and data model

Completed on 6 October 2026 using SQLite 3.53.1. This stage prepares the data for the sales, delivery and customer questions. It does not yet claim business findings.

## What changed

The database now has cleaned views for all eight source tables and a model with exactly one row per order. The original 550,759 records and their field values are unchanged. All 47 source columns were profiled for blanks, outer spaces and distinct values. Keys, relationships, dates, numeric formats and exact duplicate records were also checked.

Most of the work was deciding how to use legitimate differences between tables. One order may have several items, several payment components and more than one review. Those rows need different treatment from an accidentally duplicated order.

## Decisions and evidence

| Issue | Observed | Decision and reason |
|---|---:|---|
| Duplicate full records or intended composite keys | 0 across eight tables | No deduplication of source tables is needed |
| Missing required identifiers or unmatched core relationships | 0 | Validate these as hard requirements before publishing the model |
| Blank categories | 610 products | Keep them and label them Unknown category so their sales are not lost |
| Missing English mappings | 13 products across two categories | Keep the original Portuguese category, prefixed with Untranslated; do not invent mappings |
| Missing physical measurements | 2 products | Keep NULL; do not replace unknown dimensions with zero |
| Zero weight | 4 products | Keep and flag; physical measurements are outside the current headline measures |
| Multiple reviews on one order | 547 orders | Select one latest valid response with a documented tie rule |
| Review ID reused on another order | 789 review IDs | Use the combination of order_id and review_id as the source key |
| Reviews with inconsistent chronology | 64 rows | Exclude from review selection; retain the original records |
| Delivered status with no actual delivery timestamp | 8 orders | Include in sales when otherwise eligible; exclude from delivery timing and lateness |
| Other status with an actual delivery date | 6 orders | Retain the status; exclude from delivered-order measures |
| Carrier event before purchase / before approval / after receipt | 166 / 1,359 / 23 orders | Keep separate flags; do not infer corrected timestamps. Counts can overlap |
| Shipping deadlines in 2020 | 4 item rows | Flag for investigation; do not use shipping deadlines as a delivery proxy |
| Zero payment amount / installments / undefined method | 9 / 2 / 3 payment rows | Preserve and report; these counts may overlap |
| Orders without items / payments / source reviews | 775 / 1 / 768 orders | LEFT JOIN keeps the order; missing amounts and reviews remain NULL |
| Payments differing from items plus freight by more than one cent | 303 orders | Preserve the amounts and record the open reconciliation work for Part 7 |

The two untranslated categories are `pc_gamer` (three products) and `portateis_cozinha_e_preparadores_de_alimentos` (ten products).

## Cleaning rules

1. Check numeric formats before casting. Required amounts and sequences cannot be blank. Accepted numeric text is nonnegative, with up to nine whole-number digits and two decimal places; integer fields allow only zero fractional digits. Unexpected formats stop preparation for investigation.
2. Convert valid prices, freight and payments into integer hundredths. This keeps aggregation exact for this dataset. Keep item/payment sequences, scores and product measurements as integers.
3. Check nonblank timestamps by round-tripping them through SQLite. Impossible dates and malformed strings stop preparation. Blank timestamps become NULL.
4. Check required text IDs for missing values and outer spaces. Keep valid IDs unchanged so joins can use ordinary indexes. Convert other empty text to NULL, trim outer spaces, and standardise status/payment labels to lowercase and state codes to uppercase. City spelling and accents are preserved.
5. Keep one valid review per order. Rank candidates by response timestamp descending, creation timestamp descending, then review ID ascending. Do not favour a particular score.
6. Aggregate items and payments separately by order, then LEFT JOIN those totals and the selected review to orders. Keep missing totals as NULL and use zero only for an absent child-row count.
7. Apply metric-specific eligibility flags. The main purchase window is February 2017–July 2018; the [metric definitions](04_metric_definitions.md) explain the boundary decision and every denominator.

The views are intended for this verified source snapshot. Rerun preparation and review the resulting checks whenever the imported data changes. The source file is not repaired by guessing new values.

## Run it

From the repository root, build Part 2 first if needed:

```bash
python3 scripts/build_database.py
python3 scripts/prepare_part3.py
python3 -m unittest discover -s tests -v
```

For an existing database with a different filename:

```bash
python3 scripts/prepare_part3.py --database ecommerce_olist_part3.db
```

Preparation uses a transaction. It commits the view/index changes only after validation; failures roll them back. It can be rerun on the same verified raw database. Use `--results-dir results/rebuilt/part3` to keep a separate evidence snapshot. Both scripts use the Python standard library. Python 3.8+ and SQLite 3.25+ are required; this run used Python 3.12.14 and SQLite 3.53.1.

To work in a SQLite SQL editor, open the database, run `sql/02_profile.sql`, then use `BEGIN;`, run `sql/02_cleaning.sql` and inspect `sql/02_check_cleaning.sql`. Commit only when the required key/count/relationship and total checks pass; otherwise run `ROLLBACK;`. The Python runner also verifies every raw field and independently checks money with Decimal, so it is the reference reproduction path.

## What was verified

- **62 checks passed** on the full dataset: source counts, raw field fingerprints, clean row counts, required/composite keys, core links, numeric/date formats, review accounting, join totals and SQLite integrity.
- The order model has **99,441 rows and 99,441 distinct order IDs**. Category enrichment keeps all 32,951 products.
- Item-price totals remain **1,359,164,370 hundredths**, freight **225,190,954**, and payments **1,600,887,212** before and after the order joins. These totals cover the full source, not just the reporting window.
- **14 small automated tests passed**, covering row multiplication, missing children, review choice and ties, reused review IDs, calendar-day lateness, missing delivery dates, category gaps, invalid input, unchanged raw text, postal codes and period boundaries.

The checks above do not mean the source is free of exceptions. The decision table records the exceptions that remain and how they are used or excluded. Five manual order walkthroughs, investigation of payment differences, the measured optimisation experiment and dashboard reconciliation remain Part 7 work.

Evidence: [validation JSON](../results/part3_validation.json), [readable check output](../results/part3_validation.txt), [source profile](../results/part3_profile.json), [test output](../results/part3_tests.txt).

## Two queries to practise

```sql
SELECT order_id, COUNT(*) AS item_count
FROM v_clean_order_items
GROUP BY order_id
HAVING COUNT(*) > 1
ORDER BY item_count DESC
LIMIT 5;
```

`GROUP BY` collects the item rows for each order. `COUNT(*)` counts those items. `HAVING` keeps groups with more than one item. It filters grouped results; these repeated order IDs are expected and do not mean the item table is duplicated.

```sql
SELECT p.product_id, p.product_category_name
FROM v_clean_products p
LEFT JOIN v_clean_category_translation t
    ON p.product_category_name = t.product_category_name
WHERE p.product_category_name IS NOT NULL
  AND t.product_category_name IS NULL;
```

The LEFT JOIN keeps every product and attaches a translation when the category matches. A NULL on the translation side identifies a missing match. The first WHERE condition separates an untranslated category from a missing category. This returns the 13 products needing a translation rule.

## Explain it in an interview

- The first check was what one row means in each table. That determines the keys and safe joins.
- The raw data was kept intact, with cleaned views supplying types, NULLs and useful labels.
- Review selection and missing-date exclusions were explicit rules, with counts recorded for each decision.
- Items and payments were totalled before joining, so one order stayed one row and the financial totals stayed unchanged.
- The reporting window and metric denominators were fixed before drawing conclusions.
- The checks and small test cases make those decisions reproducible. Sales and delivery findings come in the next stages.

SQLite references: [date functions](https://www.sqlite.org/lang_datefunc.html), [window functions](https://www.sqlite.org/windowfunctions.html). Source data and licence: [data README](../data/README.md).
