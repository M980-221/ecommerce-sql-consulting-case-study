-- Part 4: sales performance
-- Run after sql/02_cleaning.sql. Purchases: 1 Feb 2017 to 31 Jul 2018.
-- Sales use delivered, sales-eligible orders. Money is in source monetary units.
-- Integer cents are retained beside display values; freight is excluded.

-- result: monthly_sales
-- Q1. How much product value was sold each month, and across how many orders?
-- One row per month. Keep months with no sales so gaps remain visible.
WITH RECURSIVE months(month_start) AS (
    SELECT '2017-02-01'
    UNION ALL
    SELECT DATE(month_start, '+1 month')
    FROM months
    WHERE month_start < '2018-07-01'
), totals AS (
    SELECT SUBSTR(order_purchase_timestamp, 1, 7) AS month,
           COUNT(*) AS all_period_orders,
           SUM(sales_eligible) AS sales_orders,
           SUM(CASE WHEN sales_eligible = 1 THEN product_sales_cents ELSE 0 END)
               AS product_sales_cents
    FROM v_order_analysis
    WHERE in_reporting_period = 1
    GROUP BY SUBSTR(order_purchase_timestamp, 1, 7)
)
SELECT SUBSTR(m.month_start, 1, 7) AS month,
       COALESCE(t.all_period_orders, 0) AS all_period_orders,
       COALESCE(t.sales_orders, 0) AS sales_orders,
       COALESCE(t.all_period_orders - t.sales_orders, 0) AS excluded_orders,
       COALESCE(t.product_sales_cents, 0) AS product_sales_cents,
       COALESCE(t.product_sales_cents, 0) / 100.0 AS product_sales_value,
       ROUND(t.product_sales_cents / 100.0 / NULLIF(t.sales_orders, 0), 2)
           AS average_order_value
FROM months m
LEFT JOIN totals t ON t.month = SUBSTR(m.month_start, 1, 7)
ORDER BY month;

-- result: monthly_growth
-- Q2. Did sales change because of order volume, average order value, or both?
-- LAG compares consecutive calendar months, including months with no sales.
-- Use unrounded AOV for growth; round only the displayed answer.
WITH RECURSIVE months(month_start) AS (
    SELECT '2017-02-01'
    UNION ALL
    SELECT DATE(month_start, '+1 month')
    FROM months
    WHERE month_start < '2018-07-01'
), totals AS (
    SELECT SUBSTR(order_purchase_timestamp, 1, 7) AS month,
           COUNT(*) AS sales_orders,
           SUM(product_sales_cents) AS product_sales_cents
    FROM v_order_analysis
    WHERE sales_eligible = 1
    GROUP BY SUBSTR(order_purchase_timestamp, 1, 7)
), monthly AS (
    SELECT SUBSTR(m.month_start, 1, 7) AS month,
           COALESCE(t.sales_orders, 0) AS sales_orders,
           COALESCE(t.product_sales_cents, 0) AS product_sales_cents,
           t.product_sales_cents / 100.0 / NULLIF(t.sales_orders, 0)
               AS average_order_value
    FROM months m
    LEFT JOIN totals t ON t.month = SUBSTR(m.month_start, 1, 7)
), previous AS (
    SELECT *,
           LAG(product_sales_cents) OVER (ORDER BY month)
               AS previous_month_product_sales_cents,
           LAG(sales_orders) OVER (ORDER BY month) AS previous_month_sales_orders,
           LAG(average_order_value) OVER (ORDER BY month)
               AS previous_month_average_order_value
    FROM monthly
)
SELECT month, sales_orders, product_sales_cents,
       product_sales_cents / 100.0 AS product_sales_value,
       ROUND(average_order_value, 2) AS average_order_value,
       previous_month_product_sales_cents, previous_month_sales_orders,
       ROUND(previous_month_average_order_value, 2) AS previous_month_average_order_value,
       ROUND(100.0 * (product_sales_cents - previous_month_product_sales_cents)
             / NULLIF(previous_month_product_sales_cents, 0), 2) AS product_sales_mom_pct,
       ROUND(100.0 * (sales_orders - previous_month_sales_orders)
             / NULLIF(previous_month_sales_orders, 0), 2) AS orders_mom_pct,
       ROUND(100.0 * (average_order_value - previous_month_average_order_value)
             / NULLIF(previous_month_average_order_value, 0), 2) AS aov_mom_pct
FROM previous
ORDER BY month;

-- result: comparable_periods
-- Q3. How did sales change between the same six months in 2017 and 2018?
-- Compare February to July in both years, rather than unequal annual totals.
-- AOV is total product value divided by orders, not an average of monthly AOVs.
WITH periods(period_year, period_start, period_end_exclusive) AS (
    VALUES (2017, '2017-02-01', '2017-08-01'),
           (2018, '2018-02-01', '2018-08-01')
), totals AS (
    SELECT p.period_year, p.period_start, p.period_end_exclusive,
           COUNT(o.order_id) AS all_period_orders,
           COALESCE(SUM(o.sales_eligible), 0) AS sales_orders,
           COALESCE(SUM(CASE WHEN o.sales_eligible = 1
                             THEN o.product_sales_cents ELSE 0 END), 0)
               AS product_sales_cents
    FROM periods p
    LEFT JOIN v_order_analysis o
        ON o.order_purchase_timestamp >= p.period_start
       AND o.order_purchase_timestamp < p.period_end_exclusive
       AND o.in_reporting_period = 1
    GROUP BY p.period_year, p.period_start, p.period_end_exclusive
), values_by_period AS (
    SELECT *, product_sales_cents / 100.0 / NULLIF(sales_orders, 0)
                  AS average_order_value
    FROM totals
), previous AS (
    SELECT *,
           LAG(product_sales_cents) OVER (ORDER BY period_year)
               AS previous_year_product_sales_cents,
           LAG(sales_orders) OVER (ORDER BY period_year) AS previous_year_sales_orders,
           LAG(average_order_value) OVER (ORDER BY period_year)
               AS previous_year_average_order_value
    FROM values_by_period
)
SELECT period_year, period_start, period_end_exclusive, 6 AS calendar_months,
       all_period_orders, sales_orders,
       all_period_orders - sales_orders AS excluded_orders,
       product_sales_cents, product_sales_cents / 100.0 AS product_sales_value,
       ROUND(average_order_value, 2) AS average_order_value,
       previous_year_product_sales_cents, previous_year_sales_orders,
       ROUND(previous_year_average_order_value, 2) AS previous_year_average_order_value,
       ROUND(100.0 * (product_sales_cents - previous_year_product_sales_cents)
             / NULLIF(previous_year_product_sales_cents, 0), 2) AS product_sales_yoy_pct,
       ROUND(100.0 * (sales_orders - previous_year_sales_orders)
             / NULLIF(previous_year_sales_orders, 0), 2) AS orders_yoy_pct,
       ROUND(100.0 * (average_order_value - previous_year_average_order_value)
             / NULLIF(previous_year_average_order_value, 0), 2) AS aov_yoy_pct
FROM previous
ORDER BY period_year;

-- result: category_sales
-- Q4. Which categories account for the most product sales value?
-- Sum item prices here: repeating an order total for each item inflates sales.
-- One order may appear in several categories, so category order counts overlap.
-- Keep unknown/untranslated categories in both the rows and the denominator.
WITH totals AS (
    SELECT COALESCE(NULLIF(TRIM(p.category_label), ''), 'Unknown category') AS category_label,
           COUNT(DISTINCT i.order_id) AS sales_orders,
           COUNT(*) AS item_count,
           SUM(i.price_cents) AS product_sales_cents
    FROM v_order_analysis o
    JOIN v_clean_order_items i ON i.order_id = o.order_id
    LEFT JOIN v_products_labeled p ON p.product_id = i.product_id
    WHERE o.sales_eligible = 1
    GROUP BY COALESCE(NULLIF(TRIM(p.category_label), ''), 'Unknown category')
), shares AS (
    SELECT *,
           SUM(product_sales_cents) OVER () AS all_product_sales_cents,
           SUM(product_sales_cents) OVER (
               ORDER BY product_sales_cents DESC, category_label ASC
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS cumulative_product_sales_cents
    FROM totals
)
SELECT category_label, sales_orders, item_count, product_sales_cents,
       product_sales_cents / 100.0 AS product_sales_value,
       ROUND(100.0 * product_sales_cents / NULLIF(all_product_sales_cents, 0), 2)
           AS sales_share_pct,
       ROUND(100.0 * cumulative_product_sales_cents / NULLIF(all_product_sales_cents, 0), 2)
           AS cumulative_sales_share_pct
FROM shares
ORDER BY product_sales_cents DESC, category_label ASC;

-- result: regional_sales
-- Q5. Where do buyers generating product sales live, and how large are their orders?
-- Use the buyer's state and one row per eligible order. Keep unknown states.
WITH totals AS (
    SELECT COALESCE(NULLIF(TRIM(customer_state), ''), 'Unknown state') AS customer_state,
           COUNT(*) AS sales_orders,
           SUM(product_sales_cents) AS product_sales_cents
    FROM v_order_analysis
    WHERE sales_eligible = 1
    GROUP BY COALESCE(NULLIF(TRIM(customer_state), ''), 'Unknown state')
)
SELECT customer_state, sales_orders, product_sales_cents,
       product_sales_cents / 100.0 AS product_sales_value,
       ROUND(product_sales_cents / 100.0 / NULLIF(sales_orders, 0), 2) AS average_order_value,
       ROUND(100.0 * product_sales_cents
             / NULLIF(SUM(product_sales_cents) OVER (), 0), 2) AS sales_share_pct
FROM totals
ORDER BY product_sales_cents DESC, customer_state ASC;
