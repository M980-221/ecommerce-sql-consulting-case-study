# Part 6 — Customer experience and repeat purchases

This stage looks at selected review scores, customer spending and repeat purchases. It uses the **89,110 sales-eligible orders** purchased from **1 February 2017 to 31 July 2018**. Delivery comparisons also require valid delivery dates.

## Run the analysis

```bash
python3 scripts/analyse_customers.py
python3 -m unittest discover -s tests -v
```

Run this from the repository folder after database setup, Part 3 preparation and Part 4 sales analysis. The script opens the database read-only, runs [the customer SQL](../sql/05_customer_analysis.sql), checks the results and exports five CSVs. Blank CSV cells mean SQL `NULL`, not zero.

## Questions and outputs

| Query | Question | Output and row meaning |
|---|---|---|
| Q11 | How are selected scores distributed, including missing reviews? | [Review distribution](../results/part6_review_distribution.csv): six rows, scores 1–5 plus a missing-review group |
| Q12 | How do reviews differ between on-time and late deliveries? | [Delivery and reviews](../results/part6_delivery_reviews.csv): two groups, with coverage and response timing counts |
| Q13 | Which customers have the highest observed product spending? | [Customer spending](../results/part6_customer_spending.csv): the top 20 persistent customer IDs, after aggregating all customers |
| Q14 | How many customers placed at least two eligible orders? | [Repeat customers](../results/part6_repeat_customers.csv): one summary row with customer, order and value totals |
| Q15 | Which buyer states account for the most low scores? | [Regional reviews](../results/part6_regional_reviews.csv): 27 states, with counts, coverage and rates |

## Results and interpretation

**Reviews cover 88,494 of 89,110 sales orders (99.31%).** Their mean selected score is **4.15 out of 5**. Scores of 1 or 2 account for **11,534 of 88,494 reviewed orders (13.03%)**; a missing score is not counted as a low score.

The missing-review group contains **616 orders**: **613 have no source review**, and **three have source reviews but no valid candidate**. Keeping this group makes the distribution account for every sales order. Shares of all sales orders and shares of reviewed orders use different denominators.

| Delivery group | Eligible orders | Reviewed orders | Mean score | Reviews scoring 1 or 2 | Low-score share of reviewed orders |
|---|---:|---:|---:|---:|---:|
| On time, including early | 82,986 | 82,514 | 4.28 | 7,731 | 9.37% |
| Late | 6,116 | 5,972 | 2.23 | 3,802 | 63.66% |

**Response timing matters: 4,274 of the 5,972 selected late-group responses (71.57%) were recorded before actual delivery.** The on-time group also includes 171 responses before delivery. This comparison is not a post-delivery-only satisfaction measure. It describes an association between eventual delivery status and selected reviews; it does not establish that lateness caused the score difference. Product, seller, region and purchase-month differences have not been controlled for.

The delivery comparison covers 89,102 sales orders, including 88,486 with a selected review. Eight sales orders lack delivery endpoints and are excluded from this comparison, although their reviews remain in the overall distribution. There are 472 missing reviews in the on-time group and 144 in the late group.

**There are 86,271 observed customers; 2,562 placed at least two eligible orders (2.97%).** Customers are grouped by `customer_unique_id`, which links them across order-specific customer records. Separate orders on the same day still count. Later purchasers have less time to order again, and orders outside the reporting window do not count. This is an observed repeat-purchase measure, not retention, churn or loyalty.

**The top 20 spending customers account for 106,622.48, or 0.87% of product value.** All 86,271 customers are aggregated before sorting and applying `LIMIT 20`. These are purchases observed in this window, not customer lifetime value. Amounts use source monetary units and exclude freight; they are not profit or Olist commission revenue.

**Regional counts and rates point to different priorities.** SP has more low-scoring orders: 3,937 of 36,745 reviewed orders (**10.71%**). RJ has fewer low-scoring orders but a higher share: 2,137 of 11,365 (**18.80%**). Keep the reviewed-order denominators and review coverage beside these comparisons. The table is ordered by low-score count, not by a claim that one state has the worst service.

## Review selection and calculations

- Part 3 checks that scores are 1–5 and review dates follow the documented purchase and response chronology. It selects the latest valid response per order, then latest creation date, then review ID ascending. The score itself never decides which review wins.
- The original reviews remain available. Joining all raw review rows would give some orders extra weight; `v_order_review` has at most one selected review per order.
- The review rule allows responses before delivery. The delivery table reports those counts rather than silently changing the selection rule for this analysis.
- Review coverage divides reviewed orders by all eligible sales orders in a group. Mean score and low-score share use reviewed orders only. An empty reviewed population produces `NULL`, not a zero score.
- Product value is summed as integer hundredths. Published means and percentages use integer arithmetic with half-up rounding to two decimal places; the practice averages below are left unrounded to keep the SQL readable.

## Two queries to practise

Run these against the prepared SQLite database. In SQLime, first load the database containing the Part 3 views.

```sql
SELECT customer_unique_id,
       COUNT(*) AS eligible_orders,
       SUM(product_sales_cents) / 100.0 AS observed_product_value
FROM v_order_analysis
WHERE sales_eligible = 1
GROUP BY customer_unique_id
HAVING COUNT(*) >= 2
ORDER BY eligible_orders DESC, customer_unique_id;
```

- `WHERE` first keeps eligible orders in the reporting window.
- `GROUP BY customer_unique_id` collects orders belonging to the same persistent customer. Grouping by `customer_id` would split that customer's order records.
- `COUNT(*)` counts their orders because the model has one row per order. `SUM` adds their product value.
- `HAVING` filters the completed customer groups, retaining only those with at least two orders. This is why the count condition belongs after grouping, not in `WHERE`.
- The query returns **2,562 customers**. The largest order count is **12**. Change the threshold to three and explain which customers disappear; the retained customers' order counts should not change.

```sql
SELECT COUNT(*) AS sales_orders,
       COUNT(r.review_score) AS reviewed_orders,
       COUNT(*) - COUNT(r.review_score) AS missing_review_orders,
       AVG(r.review_score) AS average_review_score
FROM v_order_analysis o
LEFT JOIN v_order_review r ON r.order_id = o.order_id
WHERE o.sales_eligible = 1;
```

- `o` and `r` are aliases for the order model and selected-review view. `order_id` is the matching key.
- `LEFT JOIN` keeps every eligible order, including orders without a selected review. The unique order key in `v_order_review` prevents the join from multiplying orders.
- `COUNT(*)` returns **89,110**; it counts all joined order rows. `COUNT(r.review_score)` returns **88,494** because it skips `NULL`. Their difference is **616** missing reviews.
- `AVG(r.review_score)` also skips `NULL` and returns approximately **4.145038**. Replacing missing scores with zero would lower the average by inventing ratings that customers never gave.
- The order model already includes the selected review; this explicit join is for practice. The main analysis uses the model's review fields without joining raw reviews again.

## Checks and next step

All **26 validation checks** passed. The [validation record](../results/part6_validation.json) compares all **56 exported rows and 534 cells** with independent calculations from raw records. It checks review selection, populations, spending totals, missing-review reasons and response timing. The [text results](../results/part6_validation.txt) show the checks without the full JSON structure. The [test run](../results/part6_tests.txt) passed all **48 tests: 12 customer tests and 36 earlier tests**.

The results remain subject to the source snapshot, missing reviews and uneven observation time. They do not establish complete customer histories or explain why a customer did not buy again. The delivery comparison is descriptive and includes responses submitted before receipt.

**Next: Part 7 — validation and SQL review.** Investigate payment differences, walk through selected orders manually and examine query performance before building the dashboard and final recommendations.
