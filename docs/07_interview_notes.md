# Technical walkthrough

Current scope: Parts 1–4 are complete. The repository covers the business brief, a verified import, cleaning decisions, an order model and five sales queries with exported results. Delivery analysis, customer analysis and the dashboard are still to come.

## Points to explain

- **The business question:** where an e-commerce manager should focus to improve sales performance, delivery reliability and customer experience. This is an independent case study using historical Olist data.
- **The setup:** eight source files were imported into SQLite, with all 550,759 rows and 47 source fields preserved. SQL defines the structures and checks; Python handles CSV parsing and runs the verification.
- **The row meanings:** orders have one row per order; items and payments can have several. Customer records link to orders, while customer_unique_id identifies a customer across orders.
- **The cleaning:** raw values remain available. Clean views handle blank fields and types, retain unknown categories, and apply documented review and date rules.
- **The joins:** item and payment totals are calculated separately before they are joined to orders. Reviews are reduced to one valid selection. The final model still has exactly 99,441 orders.
- **The sales scope:** 89,110 eligible delivered orders purchased between 1 February 2017 and 31 July 2018. Product sales value is 12,230,652.13 source monetary units, excluding freight, with an average order value of 137.25. Another 2,670 orders in the period were not delivered in the snapshot and are excluded from sales.
- **The main finding:** comparing February–July in both years, product value increased by 134.42%, order counts by 130.80% and AOV by 1.57%. More recorded orders account for most of the value difference; this does not explain why orders increased.
- **The breakdowns:** health and beauty contributed 8.98% of product value; the ten largest categories contributed 62.49%. São Paulo accounted for 37.84% by buyer state. These are findings to investigate alongside delivery and customer experience, not evidence of an achieved business improvement.
- **The evidence:** Part 3 passed 62 full-data checks and 14 small test cases. Every money conversion was compared with Decimal, and item, freight and payment totals are unchanged by the joins. Part 4 compares the sales outputs with independent calculations from the raw tables and reconciles monthly, category and state totals. See the [Part 4 checks](../results/part4_validation.txt).
- **The limitations:** the reporting period is a conservative 18-month window; some dates and categories are missing, review selection is a modelling choice, and payment differences still need investigation. Results describe historical associations.

## SQL to demonstrate

```sql
SELECT order_id, COUNT(*) AS item_count
FROM v_clean_order_items
GROUP BY order_id
HAVING COUNT(*) > 1
ORDER BY item_count DESC
LIMIT 5;
```

Explain that GROUP BY makes one group per order and HAVING filters the item counts. Multiple item rows are expected, so these results are not automatically errors.

```sql
SELECT o.order_id, c.customer_state
FROM v_clean_orders o
JOIN v_clean_customers c ON o.customer_id = c.customer_id
LIMIT 5;
```

Explain the two table aliases, the matching customer_id and why the unique customer key prevents this join from multiplying orders. Then show the missing-category LEFT JOIN in [Part 3 notes](10_part3_cleaning.md#two-queries-to-practise).

```sql
SELECT COUNT(*) AS modeled_orders,
       COUNT(DISTINCT order_id) AS distinct_orders
FROM v_order_analysis;
```

Both results are 99,441. Explain why checking the row count alone is not enough: the monetary totals must also be reconciled.

```sql
SELECT customer_state,
       COUNT(*) AS orders,
       ROUND(SUM(product_sales_cents) / 100.0 / COUNT(*), 2)
           AS average_order_value
FROM v_order_analysis
WHERE sales_eligible = 1
GROUP BY customer_state
HAVING COUNT(*) >= 1000
ORDER BY average_order_value DESC;
```

This returns 12 states. Explain why `WHERE` chooses orders before grouping, while `HAVING` chooses states after counting their orders. The 1,000-order threshold is for practice; the main report includes all 27 states. Then demonstrate the category join in [Part 4 notes](11_part4_sales.md#two-queries-to-practise) and explain why it sums item prices.

## Questions to practise answering

1. **What is the difference between WHERE and HAVING?** Describe filtering individual eligible orders versus filtering states by their grouped counts.
2. **Why can three item rows joined to two payment rows produce six rows?** Each item matches both payments. Aggregate each source to one row per order before joining order totals.
3. **Why is customer_unique_id needed for repeat purchases?** It links the same customer across different order-linked customer IDs. Repeat purchasing is planned for Part 6.
4. **How is one review selected?** Keep valid candidates, then use latest response, latest creation and review ID as the tie-break order. The score does not decide the selection.
5. **Why can an order qualify for sales but not delivery timing?** A delivered order can have valid item values but no actual-delivery timestamp; there are eight such period orders.
6. **Why store money as integer hundredths?** Exact aggregation is possible before converting to display values. “Cents” names the storage scale; the CSVs have no currency code.
7. **Why compare February–July in both years?** The reporting window has different numbers of months in each year. Matching months improves comparability, but does not hold the seller or product mix constant.
8. **Why not average the monthly AOVs?** It gives each month equal weight regardless of orders. Divide combined product value by combined order count instead.
9. **Can category order counts be added?** No. An order containing two categories appears in both category counts. Item values can be added because each item belongs to one category group.
10. **What does LAG do?** It brings the previous ordered row's value onto the current row for the growth calculation. The calendar list keeps comparisons between consecutive months.
11. **Did the project increase sales by 134.42%?** No. That is an observed difference between two historical periods in the dataset, not an effect of this project or proof of market-wide growth.
12. **What remains uncertain after validation?** Source completeness, equal follow-up, missing fields, review-selection effects and payment reconciliation. Passing checks verify the calculations against the chosen rules.

Practise running the queries and explaining one result from each CSV without reading these notes. Keep claims about completed work separate from planned work. The next stage is delivery analysis; recommendations will follow the combined evidence.
