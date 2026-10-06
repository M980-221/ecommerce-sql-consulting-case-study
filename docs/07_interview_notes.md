# Technical walkthrough

Current scope: Parts 1–3 are complete. The repository covers the business brief, a verified import, data profiling, cleaning decisions and an order model. Business findings and the dashboard come later.

## Points to explain

- **The business question:** where an e-commerce manager should focus to improve sales performance, delivery reliability and customer experience. This is an independent case study using historical Olist data.
- **The setup:** eight source files were imported into SQLite, with all 550,759 rows and 47 source fields preserved. SQL defines the structures and checks; Python handles CSV parsing and runs the verification.
- **The row meanings:** orders have one row per order; items and payments can have several. Customer records link to orders, while customer_unique_id identifies a customer across orders.
- **The cleaning:** raw values remain available. Clean views handle blank fields and types, retain unknown categories, and apply documented review and date rules.
- **The joins:** item and payment totals are calculated separately before they are joined to orders. Reviews are reduced to one valid selection. The final model still has exactly 99,441 orders.
- **The evidence:** 62 full-data checks and 14 small test cases passed. Every money conversion was compared with Decimal, and item, freight and payment totals are unchanged by the joins.
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

## Questions to practise answering

1. What is the difference between WHERE and HAVING?
2. Why can three item rows joined to two payment rows produce six rows?
3. Why is customer_unique_id needed for repeat purchases?
4. Why was the latest valid review selected, and how are ties resolved?
5. Why can an order qualify for sales but not delivery-time analysis?
6. Why store monetary amounts as integer hundredths?
7. What do the passing checks establish, and which source limitations remain?

Use the actual scripts and results when demonstrating these points. The next stage is sales analysis; recommendations will follow the evidence.
