# Part 4 — Sales performance

This stage answers five sales questions using the order model from Part 3. Purchases run from **1 February 2017 to 31 July 2018**. The measures use delivered, sales-eligible orders and product prices, excluding freight.

## Run the analysis

```bash
python3 scripts/analyse_sales.py
```

Run this from the repository folder after completing [database setup](09_part2_setup.md) and [Part 3 preparation](10_part3_cleaning.md). The script opens the database read-only, runs [the five SQL queries](../sql/03_sales_analysis.sql), checks the results and writes the CSV files below. A blank CSV cell means SQL `NULL`, not zero.

## Questions and outputs

| Query | Business question | Output and row meaning |
|---|---|---|
| Q1 | What were monthly product sales, order counts and average order value? | [Monthly sales](../results/part4_monthly_sales.csv): 18 rows, one per month; includes excluded order counts |
| Q2 | How did value, order volume and average order value change each month? | [Monthly growth](../results/part4_monthly_growth.csv): 18 rows, one per month |
| Q3 | How did the same six months compare between 2017 and 2018? | [Comparable periods](../results/part4_comparable_periods.csv): two rows, February–July of each year |
| Q4 | Which product categories contributed the most value? | [Category sales](../results/part4_category_sales.csv): 74 rows, including unknown and untranslated categories |
| Q5 | Where did buyers generating those sales live? | [Regional sales](../results/part4_regional_sales.csv): 27 rows, one per buyer state |

The first month's growth is `NULL` because there is no earlier month inside the reporting window. Rates also stay `NULL` when the comparison value is zero. A calendar month list ensures that a month with no sales would still appear.

## Results

| Measure | Result |
|---|---:|
| All orders purchased in the reporting period | 91,780 |
| Eligible delivered orders used for sales | 89,110 |
| Orders excluded from sales because their final status was not delivered | 2,670 |
| Product sales value | 12,230,652.13 |
| Average order value | 137.25 |

Money is shown in **source monetary units**. The source files do not contain a currency code. Product sales value excludes freight and is not Olist commission revenue or profit.

- **Order volume accounts for most of the difference between the matched periods.** February–July product sales rose from 2,326,958.07 in 2017 to 5,454,903.48 in 2018, an increase of **134.42%**. Eligible orders rose from 17,055 to 39,363 (**130.80%**), while average order value increased from 136.44 to 138.58 (**1.57%**, calculated before rounding).
- **November 2017 had the highest monthly product sales value:** **987,765.37** across 7,289 eligible orders. The data establish the peak; these queries do not establish what caused it.
- **Health and beauty led the categories**, contributing **1,097,800.05**, or **8.98%** of total product value. The ten largest categories together contributed **62.49%**.
- **São Paulo (SP) was the largest buyer state**, contributing **4,628,238.68**, or **37.84%** of product value, across 36,959 eligible orders. This is the buyer's location, not the seller's.

These results describe the available dataset. The matched comparison does not hold sellers, customers or products constant, and it does not establish market-wide growth. Delivery and customer results are still needed before choosing business recommendations.

## Why the calculations are set up this way

- **Equal periods:** the reporting window contains eleven months of 2017 and seven of 2018. Comparing those annual totals would mix different lengths and seasons. February–July uses the same six calendar months in each year; it does not remove changes in the mix of sellers or products.
- **Order-level measures:** `v_order_analysis` has one row per order. Monthly and regional totals can use `COUNT(*)` and sum each order's value once.
- **Item-level category measures:** an order can contain products from several categories. The category query joins to the item rows and sums `i.price_cents`. Summing the full order value after that join would repeat it for every item.
- **Overlapping category counts:** `COUNT(DISTINCT order_id)` counts each order once within a category. An order with a book and a toy still appears in two categories, so adding category order counts does not give the overall order count. Item values can be added across categories.
- **Weighted average order value:** overall AOV is total product value divided by total eligible orders. An average of monthly AOVs would give a quiet month the same weight as a busy month.
- **Exact totals:** money is summed as integer hundredths (`*_cents`). Division by 100 and rounding happen for display. Growth rates use unrounded AOV values, and category shares use all categories, including missing labels.

## SQL used

| SQL | What it does here |
|---|---|
| `WHERE`, `CASE` | Choose eligible orders and separate sales from excluded orders |
| `GROUP BY`, `COUNT`, `SUM`, `COUNT(DISTINCT ...)` | Build monthly, category and state totals |
| `JOIN`, `LEFT JOIN` | Match orders to items and product categories; retain months or labels without matches |
| `WITH`, `WITH RECURSIVE`, `UNION ALL` | Break queries into named steps and generate the calendar months |
| `LAG(...) OVER (...)` | Bring the preceding month's or period's value onto the current row |
| `SUM(...) OVER (...)` | Calculate the total denominator and cumulative category contribution |
| `NULLIF`, `COALESCE`, `ROUND` | Handle undefined rates, display missing categories and round results |
| `SUBSTR`, `DATE`, `ORDER BY` | Build month labels, advance the calendar and sort results |

`HAVING` is used in the practice query below. The main state report keeps every state; it has no minimum-order filter.

## Two queries to practise

Run these in SQLite after Part 3 preparation. For SQLime, load the prepared database containing the views first.

```sql
SELECT COALESCE(p.category_label, 'Unknown category') AS category,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM(i.price_cents) / 100.0, 2) AS product_sales_value
FROM v_order_analysis o
JOIN v_clean_order_items i ON i.order_id = o.order_id
LEFT JOIN v_products_labeled p ON p.product_id = i.product_id
WHERE o.sales_eligible = 1
GROUP BY COALESCE(p.category_label, 'Unknown category')
ORDER BY product_sales_value DESC
LIMIT 5;
```

- `o`, `i` and `p` are short names for the three views.
- The first `JOIN` matches each eligible order to its items using `order_id`. One order can produce several rows here.
- The `LEFT JOIN` looks up each item's category using `product_id` while keeping the item if a label is unavailable. `COALESCE` then displays “Unknown category”.
- `GROUP BY` collects the item rows into categories. `SUM(i.price_cents)` adds the individual product prices, not repeated order totals.
- `COUNT(DISTINCT o.order_id)` counts orders containing that category. `ORDER BY ... DESC` puts the largest value first, and `LIMIT 5` returns five categories.
- The first row should be `health_beauty`: **7,766 orders** and **1,097,800.05** in product sales value.

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

- `WHERE` filters individual orders before grouping. Here it retains only eligible sales orders.
- `GROUP BY` makes one group for each buyer state.
- `HAVING` filters the finished groups. Here a state must have at least 1,000 eligible orders to appear.
- AOV divides each state's product value by its order count. Every group contains at least 1,000 orders, so this denominator cannot be zero.
- This is a practice filter for comparing states with larger samples. It returns **12 states** and does not change the main 27-state report. A threshold alone does not establish statistical significance.

Try changing `1000` to `3000`. Before running it, predict whether the number of states will increase or decrease, and whether the retained states' AOV values should change.

## Checks and remaining limits

All **15 Part 4 checks** passed across **139 output rows and 1,036 cells**; the [test run](../results/part4_tests.txt) also passed all **10 sales tests and 14 cleaning tests**.

The [validation output](../results/part4_validation.json) records comparisons with calculations from the raw tables, checks that category and state product values reconcile to the overall total, and verifies the exported results. The [text version](../results/part4_validation.txt) is easier to scan. The analysis also checks the source fingerprints so changed input data cannot silently reuse the old results.

Passing these checks establishes consistency with the documented rules. It does not prove the source captured every order or resolve the 303 payment differences above one cent recorded in Part 3. Final statuses come from a snapshot, so the measures are not a reconstruction of what was known at each month-end. Unknown and untranslated categories remain in the totals.

**Next: Part 5 — delivery performance.** Measure delivery duration and lateness, compare regions, and define seller comparisons using single-seller orders. Keep those delivery populations separate from the sales population.
