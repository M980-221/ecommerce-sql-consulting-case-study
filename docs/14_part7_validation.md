# Part 7 — Validation and SQL review

This stage checks how the sales, delivery and customer results fit together. It investigates the payment differences left open in Part 3, traces five orders back to their source rows and prepares reporting views for the dashboard.

## Reproduce the work

```bash
python3 scripts/validate_part7.py
python3 scripts/benchmark_part7.py
python3 -m unittest discover -s tests -v
```

Run these from the repository folder after preparing the database and completing the analyses in Parts 4–6. The validation runner creates the reporting views in a transaction and rolls back if validation fails. It compares source fingerprints before and after the work. It also saves a benchmark run; the standalone benchmark command prints a fresh measurement without replacing the saved evidence. Another machine or run can give different timings.

## What the checks establish

The order model must have one row per order. Product values, freight and payments must match totals calculated separately from their source rows. Sales, delivery and review populations must keep the same exclusions used in the published analyses. Unknown categories and missing reviews remain visible.

An order count alone cannot establish that a join is correct. A query could lose one order and duplicate another while returning the same number of rows. The checks therefore compare identifiers, row counts and monetary totals.

The [population output](../results/part7_population_validation.csv) retains **89,110 sales orders**, **89,102 delivery orders** and **88,494 reviewed sales orders**. The [missingness output](../results/part7_missingness_by_population.csv) separates full-source, reporting-period, sales, delivery and reviewed-sales populations rather than treating missingness as one universal count.

The [unsafe-join experiment](../results/part7_join_fanout_summary.csv) uses the same **98,665 full-source orders with both item and payment rows** on each side of the comparison. A direct item/payment join produces 117,601 rows. It overstates product value by **617,606.61** and payments by **4,461,854.54** source monetary units. These are deliberately incorrect diagnostic sums; the reporting model aggregates each child table before joining.

All **34 checks passed**. The six validation outputs contain **604 rows and 10,111 cells**, matching independent raw-record calculations. The [validation record](../results/part7_validation.json) also records the reporting-view checks and unchanged source fingerprints; the [text results](../results/part7_validation.txt) are easier to scan. All **68 tests** across Parts 3–7 passed in the [saved test run](../results/part7_tests.txt).

## Payment reconciliation

The difference is **payment total minus product value minus freight**, calculated in integer hundredths. A positive difference means recorded payments exceed item prices plus freight; a negative difference means they fall short. This comparison uses the full source population, not just the reporting-period sales subset.

| Source outcome | All source orders | Sales-eligible orders | Signed difference, source units |
|---|---:|---:|---:|
| Exact match | 98,089 | 88,615 | 0.00 |
| Difference of one hundredth | 273 | 234 | -0.67 |
| Payment below item value plus freight by more than one hundredth | 39 | 18 | -199.08 |
| Payment above item value plus freight by more than one hundredth | 264 | 243 | +3,070.14 |
| Missing items | 775 | 0 | NULL |
| Missing payments | 1 | 0 | NULL |

The **98,665 orders with both sides present** contain 98,089 exact matches, 273 one-cent differences and **303 larger differences**. The 576 nonzero differences net to **+2,870.39**; their absolute differences sum to **3,271.95**. A net figure alone hides amounts that offset one another. These are recorded differences, not a loss or profit estimate.

All 273 one-cent differences occur on multi-item orders. Of the 303 larger differences, 286 have only one payment row and seven include a voucher. These patterns do not identify a cause. The exact raw-record arithmetic shows that the differences exist before joining the reporting model; duplicate joins or vouchers do not provide a general explanation.

Within the sales population, **495 orders** have a nonzero difference and contribute **104,021.36** in product value (**0.85%** of sales). This includes 261 orders with larger differences. Their valid item prices remain included under the established sales rule; payment agreement was never a sales eligibility condition.

Evidence: [seven reconciliation groups](../results/part7_reconciliation_summary.csv), [observed patterns](../results/part7_reconciliation_patterns.csv) and [all 576 comparable exceptions](../results/part7_reconciliation_exceptions.csv). The summary also retains an empty “missing items and payments” group so the classification is explicit.

An order without item or payment rows cannot be treated as an exact match. Its missing side remains `NULL`; replacing that side with zero would change the question being checked.

Amounts are preserved even when they disagree. The source does not provide the accounting history needed to establish every cause, such as whether an adjustment, refund or different transaction scope was involved. A diagnostic pattern is evidence for investigation, not proof of a particular cause. Product sales still use item prices; the reconciliation does not redefine sales as payments.

## Five orders traced to the source

Amounts below are in source monetary units; the checks use exact integer hundredths.

| Case and order ID | Products | Freight | Payments | Difference |
|---|---:|---:|---:|---:|
| Exact: `00010242fe8c5a6d1ba2dd792cb16214` | 58.90 | 13.29 | 72.19 | 0.00 |
| Multiple items/payments: `03ecec245220b63fd7f68c1737ba99ba` | 298.90 | 76.83 | 375.73 | 0.00 |
| One cent: `153b80864a22f0638fef4339488a2cf3` | 378.00 | 43.36 | 421.35 | -0.01 |
| Larger difference: `00789ce015e7e5791c7914f32bb4fad4` | 154.00 | 14.83 | 190.81 | +21.98 |
| No payment row: `bfbd0f9bdef84302105ad712db648a6c` | 134.97 | 8.49 | NULL | NULL |

1. **Exact:** one item and one payment. The payment records two installments, which does not mean two payment rows. The order arrived on 20 September 2017, before the 29 September promise, and has a selected score of 5.
2. **Multiple items/payments:** product prices are 189.00 + 109.90; freight is 58.78 + 18.05. A 319.34 card payment plus a 56.39 voucher totals 375.73. Joining the two item rows directly to the two payment rows creates four rows, inflating product value to 597.80 and payments to 751.46. The order arrived on 21 June 2018, before the 17 July promise, and has a selected score of 3. Its two sellers exclude it from single-seller delivery attribution.
3. **One cent:** two items at 189.00 and two freight amounts of 21.68 total 421.36, while the single payment is 421.35. Ten installments are recorded on that payment row. The order arrived on 28 November 2017, before the 13 December promise, and has a selected score of 5. The one-cent difference is preserved.
4. **Larger difference:** 154.00 + 14.83 gives 168.83; one recorded payment is 190.81. Ten installments are recorded, but the source does not establish the cause of the extra 21.98. The order arrived on 17 July 2017, before the 20 July promise, and has a selected score of 5.
5. **Missing payment:** three items at 44.99 plus three freight amounts of 2.83 total 143.46. No payment row exists. This purchase was made on 15 September 2016, outside the reporting window. It arrived on 9 November, 36 days after the 4 October promise. Its valid score-1 response was submitted on 7 October, before receipt. Source records and the selected review remain available, while the order is excluded from the main period reports.

The [five source walkthroughs](../results/part7_order_walkthroughs.json) contain the item and payment rows, review IDs, scores, dates and checked model values behind these examples.

These examples are selected to test different behaviours rather than estimate how common they are. Item and payment amounts are summed independently before comparing them with the model. Review histories are checked against the same latest-valid-review rule used in Parts 3 and 6. Dates are checked against the stated eligibility and calendar-day lateness rules.

## Reporting views

| View | Rows | One row represents | Intended use |
|---|---:|---|---|
| `v_reporting_orders` | 91,780 | An order purchased in the reporting period | Sales, delivery and review measures, using the relevant eligibility flags |
| `v_reporting_sales_items` | 101,825 | An eligible sales item, keyed by `order_id` and `order_item_id` | Product/category values from item prices; no repeated whole-order total |
| `v_reporting_order_categories` | 89,822 | A distinct delivery-eligible order/category pair | Connect delivery orders to their categories; this bridge has no monetary measures |
| `v_reporting_customers` | 86,271 | A persistent customer with at least one eligible sales order | Observed spending and repeat purchases across all such customers, without a top-20 limit |

Definitions are in [the reporting SQL](../sql/07_reporting_views.sql). Item and customer product totals both reconcile to **1,223,065,213 integer hundredths**. Customer totals contain 89,110 orders and 2,562 repeat IDs.

Choose a view whose row meaning matches the measure. Adding order values after joining to item rows repeats an order's value for every item. Category membership counts can also overlap across categories, even when each order/category pair is unique. Views make the validated logic reusable; they do not turn overlapping counts into additive measures.

The customer view contains full-window totals. For a narrower date or state selection, regroup the filtered order rows before calculating repeat customers; a dashboard filter cannot retroactively change a precomputed full-window repeat flag.

The dashboard still needs its own checks after it is built. Matching the SQL views now does not verify future dashboard filters, relationships or visual calculations.

## Performance experiment

The experiment retrieves one order's item details. It compares `WHERE TRIM(order_id) = ?` with `WHERE order_id = ?` in the same query. Source IDs were first checked to be nonblank and free of surrounding spaces, so removing `TRIM` preserves the result for this dataset.

The trimmed predicate is an intentionally inefficient comparison, not a previously published analysis query. Its plan scans `order_items`; the direct predicate searches the existing `idx_p3_order_items_order_id` index. The benchmark creates no new index and changes no source data.

Two deterministic cases are measured: one item and 21 items. Each variant gets three warm-up executions followed by 20 measured executions per case. The order alternates between trimmed/direct and direct/trimmed. Timing covers query execution and fetching every row; result comparisons are outside the timer. Every result must match exactly. This uses a warm cache, without a cold-start claim.

The saved run used Python 3.12.14 and SQLite 3.53.1. Median elapsed times were:

| Lookup case | Rows returned | Trimmed predicate | Direct predicate |
|---|---:|---:|---:|
| `00010242fe8c5a6d1ba2dd792cb16214` | 1 | 9.1386 ms | 0.0163 ms |
| `8272b63d03f5f79c56e9e4120aec44ef` | 21 | 7.8501 ms | 0.0365 ms |

The direct lookup was faster in both measured cases and returned identical rows. This supports keeping already-validated identifier columns unwrapped in this selective lookup so the existing index can be used.

The [benchmark record](../results/part7_performance.json) includes every timing, SQL text, parameters, result hashes, execution plans and environment details. The [benchmark script](../scripts/benchmark_part7.py) can repeat the measurement.

The comparison must return exactly the same result before a speed difference is useful. Timings describe this query, database and execution environment; they are not a general claim that every query becomes faster.

## Two queries to practise

```sql
SELECT order_id, COUNT(*) AS rows_per_order
FROM v_order_analysis
GROUP BY order_id
HAVING COUNT(*) > 1;
```

- `GROUP BY` collects rows for each order ID. `COUNT(*)` counts the rows in each group.
- `HAVING` keeps only groups with more than one row. The verified model returns **no rows**, because each existing order appears once.
- `WHERE` filters individual rows before grouping; `HAVING` filters the grouped counts. This check does not detect missing orders, so source-to-model key and total checks are still needed.

```sql
SELECT o.order_id, i.item_count, p.payment_count,
       i.product_sales_cents, i.freight_cents, p.payment_cents,
       p.payment_cents - i.product_sales_cents - i.freight_cents
           AS difference_cents
FROM v_clean_orders o
LEFT JOIN v_order_item_totals i ON i.order_id = o.order_id
LEFT JOIN v_order_payment_totals p ON p.order_id = o.order_id
WHERE o.order_id = '03ecec245220b63fd7f68c1737ba99ba';
```

- `o`, `i` and `p` name the orders, item totals and payment totals. `order_id` connects the same order across the views.
- Each totals view has already grouped its source rows by order. The joins therefore match one item-total row to one payment-total row, even though this order has two source rows on each side.
- The result is **two items, two payments, 29,890 product cents, 7,683 freight cents and 37,573 payment cents**, with a difference of **zero**.
- `LEFT JOIN` retains an order when one side is missing. Try the missing-payment ID above: payment and difference should be `NULL`, not zero.
- `WHERE` chooses the individual order before returning the result. No `HAVING` is needed here because the grouping was already done inside the totals views.

## What remains uncertain

Passing validation shows that the outputs follow the documented rules and reconcile to the supplied records. It does not establish that the source contains every transaction or a complete history for each customer.

- The reporting window is conservative, and the final-status snapshot does not give every customer the same follow-up time.
- Payment differences remain source exceptions unless the available records establish their cause; no amount is edited merely to make totals agree.
- The delivery/review comparison remains descriptive. Of 5,972 reviewed late orders, 4,274 selected responses were submitted before receipt, so the result is not a post-delivery-only satisfaction measure.
- Repeat customers are people with at least two eligible orders in the window, including same-day orders. The measure does not establish retention, churn or loyalty.

**Next: Part 8 — the dashboard.** Build the sales, delivery and customer pages from the validated outputs, then check each headline and filter against the SQL results.
