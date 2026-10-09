# Technical walkthrough

Current scope: Parts 1–7 are complete. The repository includes a verified SQLite model, fifteen business queries and combined validation. Part 8 now has a packaged Tableau workbook prepared for in-app verification. Payment exceptions remain documented. Final recommendations and slides are still to come.

## Points to explain

- **The business question:** where an e-commerce manager should focus to improve sales performance, delivery reliability and customer experience. This is an independent case study using historical Olist data.
- **The setup:** eight source files were imported into SQLite, with all 550,759 rows and 47 source fields preserved. SQL defines the structures and checks; Python handles CSV parsing and runs the verification.
- **The row meanings:** orders have one row per order; items and payments can have several. Customer records link to orders, while customer_unique_id identifies a customer across orders.
- **The cleaning:** raw values remain available. Clean views handle blank fields and types, retain unknown categories, and apply documented review and date rules.
- **The joins:** item and payment totals are calculated separately before they are joined to orders. Reviews are reduced to one valid selection. The final model still has exactly 99,441 orders.
- **The sales scope:** 89,110 eligible delivered orders purchased between 1 February 2017 and 31 July 2018. Product sales value is 12,230,652.13 source monetary units, excluding freight, with an average order value of 137.25. Another 2,670 orders in the period were not delivered in the snapshot and are excluded from sales.
- **The main finding:** comparing February–July in both years, product value increased by 134.42%, order counts by 130.80% and AOV by 1.57%. More recorded orders account for most of the value difference; this does not explain why orders increased.
- **The breakdowns:** health and beauty contributed 8.98% of product value; the ten largest categories contributed 62.49%. São Paulo accounted for 37.84% by buyer state. These are findings to investigate alongside delivery and customer experience, not evidence of an achieved business improvement.
- **The delivery result:** 6,116 of 89,102 eligible orders arrived after the promised calendar day (6.86%). Average delivery duration was 12.88 elapsed days; late orders averaged 10.98 calendar days beyond the promise. Receipt on the promised calendar day is on time. There are 2,678 exclusions: 2,670 non-delivered orders and eight delivered orders without a receipt date.
- **The delivery priorities:** March 2018 had 1,328 late orders out of 7,003 (18.96%). SP had more late orders than RJ, but RJ's rate was higher: 1,450 of 11,496 (12.61%), compared with SP's 1,524 of 36,952 (4.12%). Counts and rates answer different questions.
- **The seller scope:** only single-seller orders are attributed to a seller. Requiring at least 100 such eligible orders leaves 190 sellers covering 52,408 orders, or 58.82% of the full delivery population. This prioritises investigation; it does not assign blame or prove a difference is statistically significant.
- **The customer result:** 2,562 of 86,271 persistent customers placed at least two eligible orders (2.97%). This counts distinct orders within the window, including same-day orders. It is an observed repeat-purchase measure, not retention or loyalty; later customers have less follow-up time.
- **The review coverage:** 88,494 sales orders have a selected valid review, averaging 4.15 out of 5; 13.03% score 1 or 2. The remaining 616 orders comprise 613 with no source review and three with no valid review candidate. Missing scores stay missing.
- **The delivery/review association:** on-time reviewed orders average 4.28 and late reviewed orders 2.23. However, 4,274 of 5,972 selected late-group responses (71.57%) preceded actual delivery. This is not a post-delivery-only comparison and does not establish that lateness caused the difference.
- **The spending scope:** customers are aggregated by persistent ID before selecting the top 20 by product value. Their observed purchases account for 0.87% of product value in the reporting window. This is not lifetime value.
- **The evidence:** Part 3 passed 62 full-data checks and 14 small test cases. Every money conversion was compared with Decimal, and item, freight and payment totals are unchanged by the joins. Parts 4–6 compare their exports with independent raw-record calculations. See the [sales checks](../results/part4_validation.txt), [delivery checks](../results/part5_validation.txt) and [customer checks](../results/part6_validation.txt).
- **The reconciliation:** 98,665 orders have both items and payments. Of those, 98,089 match exactly, 273 differ by one cent and 303 by more than one cent. Independent raw-record arithmetic confirms the differences; it does not establish business causes. Payment totals do not replace item-based sales.
- **The order walkthrough:** order `03ecec245220b63fd7f68c1737ba99ba` has two items and two payments. Joining both child tables directly makes four rows and doubles each sum. Separate GROUP BY calculations give product value 298.90, freight 76.83 and payments 375.73, which reconcile exactly.
- **The reporting views:** order measures stay at one row per order; item prices stay at item grain. Delivery category membership is distinct by order and category. Customers are grouped across the full reporting window by persistent ID. Views are saved queries, not copied source records.
- **The performance experiment:** an unnecessary TRIM around a verified order ID forces a scan for the item lookup. Removing it lets SQLite use the existing index. Both variants return identical rows; alternating warm-cache timings show the difference for that lookup, not for every query.
- **The dashboard:** Tableau presents Sales, Delivery and Customers dashboards. SQL exports one row per order separately from one row per order/category. The workbook includes its CSVs and editable worksheets. Month and state parameters control the calculations; a customer-level FIXED expression counts eligible selected orders for repeat purchasing.
- **The dashboard checks:** all 2,273,050 Tableau export cells are compared with the validated reporting data, alongside 511 published-total checks. Workbook structure, packaged files and an independent calculation model are checked separately. These checks do not execute Tableau: opening the file and verifying actual displayed results and layout remain necessary. The earlier browser prototype has separate Node/SQL checks.
- **The limitations:** the reporting period is a conservative 18-month window; some dates and categories are missing, review selection is a modelling choice, and payment differences have unconfirmed causes. Results describe historical associations.

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

For delivery, run the seller `HAVING` and category `JOIN` examples in [Part 5 notes](12_part5_delivery.md#two-queries-to-practise). Explain how `AVG(CASE WHEN is_late = 1 THEN delay_days END)` excludes on-time orders, and why the category join needs one row per order and category before counting.

For customers, run the persistent-ID `GROUP BY`/`HAVING` and review `LEFT JOIN` examples in [Part 6 notes](13_part6_customers.md#two-queries-to-practise). Explain why `COUNT(*)` counts all sales orders but `COUNT(review_score)` and `AVG(review_score)` skip missing scores. Joining the selected-review view keeps one row per order; joining raw reviews can duplicate an order.

For validation, run the duplicate-ID `HAVING` and preaggregated `LEFT JOIN` examples in [Part 7](14_part7_validation.md). Explain why a duplicate check should return no rows, why missing payment totals stay NULL, and why COUNT(DISTINCT order_id) does not repair duplicated monetary sums.

## Questions to practise answering

1. **What is the difference between WHERE and HAVING?** Describe filtering individual eligible orders versus filtering states by their grouped counts.
2. **Why can three item rows joined to two payment rows produce six rows?** Each item matches both payments. Aggregate each source to one row per order before joining order totals.
3. **Why is customer_unique_id needed for repeat purchases?** It links the same customer across different order-linked customer IDs. Part 6 groups eligible orders by this persistent ID before counting repeat buyers.
4. **How is one review selected?** Keep valid candidates, then use latest response, latest creation and review ID as the tie-break order. The score does not decide the selection.
5. **Why can an order qualify for sales but not delivery timing?** A delivered order can have valid item values but no actual-delivery timestamp; there are eight such period orders.
6. **Why store money as integer hundredths?** Exact aggregation is possible before converting to display values. “Cents” names the storage scale; the CSVs have no currency code.
7. **Why compare February–July in both years?** The reporting window has different numbers of months in each year. Matching months improves comparability, but does not hold the seller or product mix constant.
8. **Why not average the monthly AOVs?** It gives each month equal weight regardless of orders. Divide combined product value by combined order count instead.
9. **Can category order counts be added?** No. An order containing two categories appears in both category counts. Item values can be added because each item belongs to one category group.
10. **What does LAG do?** It brings the previous ordered row's value onto the current row for the growth calculation. The calendar list keeps comparisons between consecutive months.
11. **Did the project increase sales by 134.42%?** No. That is an observed difference between two historical periods in the dataset, not an effect of this project or proof of market-wide growth.
12. **What remains uncertain after validation?** Source completeness, equal follow-up, missing fields, review-selection effects and the business causes of payment differences. Passing checks verify the calculations against the chosen rules.
13. **Can a slow delivery be on time?** Yes. Duration runs from purchase to receipt; lateness compares receipt with the promised calendar day. They measure different things.
14. **Why exclude orders with several sellers from seller comparisons?** The source gives one receipt date per order. It cannot show which seller's package, if any, caused the order-level delay.
15. **Why not sort sellers only by late rate?** A high rate can represent few affected orders. The report sorts by late count and shows both the rate and sample size. Its 100-order cutoff is a reporting choice, not a significance test.
16. **Why is 2.97% not a retention rate?** It counts customers with two or more eligible orders in one window, without a common starting cohort or equal follow-up. Separate same-day orders count too.
17. **Why not replace missing review scores with zero?** Zero would invent a rating. Keep the 616 unreviewed orders in the coverage calculation, but exclude missing scores from the mean and low-score denominator.
18. **Does the review comparison prove the effect of late delivery?** No. Other order characteristics differ, and 71.57% of the selected late-group responses were recorded before delivery. The result describes an association with eventual delivery status.
19. **What does the top-20 spending table leave out?** It is a ranked extract after aggregating every eligible customer. It covers 0.87% of observed product value and does not measure purchases outside the window or future lifetime value.

20. **Why not remove every payment mismatch?** Product sales are defined from eligible item prices. The 495 eligible sales orders with nonzero differences contribute 104,021.36 in product value; there is no established reason to remove that value. Keep the exception visible and seek source clarification.
21. **Why check IDs as well as counts?** Equal row counts could hide a missing order replaced by another ID. Part 7 compares the source and model ID sets in both directions using EXCEPT, as well as checking uniqueness and amounts.
22. **Did adding an index improve the project?** The lookup already had an index. The experiment changed the predicate so SQLite could use it, saved the execution plans and checked identical results. It does not measure an improvement in the full dashboard refresh.
23. **Can full-window customer totals follow any dashboard date filter?** No. For a narrower window, regroup the eligible order rows before deciding which customers made repeat purchases.

24. **Why does the repeat rate change after a date or state filter?** The dashboard first selects the eligible orders, then groups their persistent customer IDs. A customer with two orders across the full window might have only one in the selected slice. Reusing the full-window repeat flag would answer a different question.
25. **Why is a dashboard rate sometimes shown as a dash?** Its denominator is zero. Displaying zero would imply a measured rate, while the value is actually undefined.
26. **What does the Tableau verification prove?** The CSVs match the SQL reporting data, and the workbook structure and calculation model are checked. It does not prove Tableau has executed the workbook. Demonstrate the default figures, March 2018/RJ and the empty August 2017/RR selection in Tableau before presenting the dashboard as tested.
27. **Why use two Tableau data sources?** The category source can contain an order more than once. Keeping order-level KPIs on the order source prevents duplicated sales and review totals.
28. **Why put the selection inside FIXED?** FIXED groups by customer before ordinary dimension filters. Including the shared parameters in the counted orders ensures repeat purchases respond to the selection.
29. **Which work belongs to SQL and which to Tableau?** SQL establishes eligibility, keys and row meanings. Tableau uses those rows to calculate the active selection and draw the charts. Both are needed to explain the final result.

Practise opening the dashboard, changing one filter and explaining the new denominator before discussing a rate. Then run the matching SQL and Tableau examples in [Part 8](16_tableau_dashboard.md). Keep implementation, measured results and remaining verification distinct. Final recommendations and slides are next.
