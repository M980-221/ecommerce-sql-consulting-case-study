-- Part 5: delivery performance
-- Run after sql/02_cleaning.sql. Purchases: 1 Feb 2017 to 31 Jul 2018.
-- Lateness compares calendar dates; duration measures elapsed fractional days.
-- Positive delay averages late orders only. An undefined average stays NULL.
-- Integer delay totals use half-up rounding to two decimals; 9.825 becomes 9.83.

-- result: overall_delivery
-- Q6. How often did eligible orders arrive late, and how long did delivery take?
-- Keep excluded orders and seller-report coverage beside the headline measures.
WITH period_orders AS (
    SELECT * FROM v_order_analysis WHERE in_reporting_period = 1
), totals AS (
    SELECT COUNT(*) AS all_period_orders,
           COALESCE(SUM(delivery_eligible), 0) AS delivery_orders,
           COALESCE(SUM(CASE WHEN order_status = 'delivered' THEN 0 ELSE 1 END), 0)
               AS non_delivered_orders,
           COALESCE(SUM(CASE WHEN order_status = 'delivered' AND delivery_eligible = 0
                             THEN 1 ELSE 0 END), 0) AS excluded_delivered_date_orders,
           COALESCE(SUM(CASE WHEN delivery_eligible = 1 THEN is_late ELSE 0 END), 0)
               AS late_orders,
           AVG(CASE WHEN delivery_eligible = 1 THEN delivery_days END)
               AS average_delivery_days,
           SUM(CASE WHEN delivery_eligible = 1 AND is_late = 1 THEN delay_days ELSE 0 END)
               AS positive_delay_days,
           COALESCE(SUM(seller_delivery_eligible), 0) AS single_seller_orders,
           COALESCE(SUM(CASE WHEN delivery_eligible = 1 AND seller_count > 1
                             THEN 1 ELSE 0 END), 0) AS excluded_multi_seller_orders,
           COALESCE(SUM(CASE WHEN delivery_eligible = 1 AND seller_count = 0
                             THEN 1 ELSE 0 END), 0) AS excluded_no_seller_orders
    FROM period_orders
), seller_counts AS (
    SELECT single_seller_id, COUNT(*) AS delivery_orders
    FROM period_orders
    WHERE seller_delivery_eligible = 1
    GROUP BY single_seller_id
), seller_coverage AS (
    SELECT COALESCE(SUM(CASE WHEN delivery_orders >= 100 THEN 1 ELSE 0 END), 0)
               AS reported_sellers,
           COALESCE(SUM(CASE WHEN delivery_orders >= 100 THEN delivery_orders ELSE 0 END), 0)
               AS reported_seller_orders,
           COALESCE(SUM(CASE WHEN delivery_orders < 100 THEN delivery_orders ELSE 0 END), 0)
               AS below_threshold_seller_orders
    FROM seller_counts
)
SELECT '2017-02-01' AS period_start, '2018-08-01' AS period_end_exclusive,
       t.all_period_orders, t.delivery_orders,
       t.all_period_orders - t.delivery_orders AS excluded_orders,
       t.non_delivered_orders, t.excluded_delivered_date_orders,
       t.late_orders, t.delivery_orders - t.late_orders AS on_time_orders,
       ROUND(100.0 * t.late_orders / NULLIF(t.delivery_orders, 0), 2) AS late_delivery_pct,
       ROUND(100.0 * (t.delivery_orders - t.late_orders)
             / NULLIF(t.delivery_orders, 0), 2) AS on_time_delivery_pct,
       ROUND(t.average_delivery_days, 2) AS average_delivery_days,
       ((200 * t.positive_delay_days + t.late_orders)
         / (2 * NULLIF(t.late_orders, 0))) / 100.0 AS average_positive_delay_days,
       t.single_seller_orders, t.excluded_multi_seller_orders, t.excluded_no_seller_orders,
       s.reported_sellers, s.reported_seller_orders, s.below_threshold_seller_orders,
       ROUND(100.0 * s.reported_seller_orders / NULLIF(t.delivery_orders, 0), 2)
           AS reported_seller_order_coverage_pct
FROM totals t
CROSS JOIN seller_coverage s;

-- result: monthly_delivery
-- Q7. How did delivery outcomes vary by purchase month?
-- Include all 18 months. These are final observed outcomes, not month-end snapshots.
WITH RECURSIVE months(month_start) AS (
    SELECT '2017-02-01'
    UNION ALL
    SELECT DATE(month_start, '+1 month')
    FROM months
    WHERE month_start < '2018-07-01'
), totals AS (
    SELECT SUBSTR(order_purchase_timestamp, 1, 7) AS month,
           COUNT(*) AS all_period_orders,
           SUM(delivery_eligible) AS delivery_orders,
           SUM(CASE WHEN delivery_eligible = 1 THEN is_late ELSE 0 END) AS late_orders,
           AVG(CASE WHEN delivery_eligible = 1 THEN delivery_days END)
               AS average_delivery_days,
           SUM(CASE WHEN delivery_eligible = 1 AND is_late = 1 THEN delay_days ELSE 0 END)
               AS positive_delay_days
    FROM v_order_analysis
    WHERE in_reporting_period = 1
    GROUP BY SUBSTR(order_purchase_timestamp, 1, 7)
)
SELECT SUBSTR(m.month_start, 1, 7) AS month,
       COALESCE(t.all_period_orders, 0) AS all_period_orders,
       COALESCE(t.delivery_orders, 0) AS delivery_orders,
       COALESCE(t.all_period_orders - t.delivery_orders, 0) AS excluded_orders,
       COALESCE(t.late_orders, 0) AS late_orders,
       COALESCE(t.delivery_orders - t.late_orders, 0) AS on_time_orders,
       ROUND(100.0 * t.late_orders / NULLIF(t.delivery_orders, 0), 2) AS late_delivery_pct,
       ROUND(t.average_delivery_days, 2) AS average_delivery_days,
       ((200 * t.positive_delay_days + t.late_orders)
         / (2 * NULLIF(t.late_orders, 0))) / 100.0 AS average_positive_delay_days
FROM months m
LEFT JOIN totals t ON t.month = SUBSTR(m.month_start, 1, 7)
ORDER BY month;

-- result: regional_delivery
-- Q8. Which buyer states account for the most late orders?
-- Show all states and their sample sizes. Small groups can have unstable rates.
WITH totals AS (
    SELECT COALESCE(NULLIF(TRIM(customer_state), ''), 'Unknown state') AS customer_state,
           COUNT(*) AS delivery_orders, SUM(is_late) AS late_orders,
           AVG(delivery_days) AS average_delivery_days,
           SUM(CASE WHEN is_late = 1 THEN delay_days ELSE 0 END) AS positive_delay_days
    FROM v_order_analysis
    WHERE delivery_eligible = 1
    GROUP BY COALESCE(NULLIF(TRIM(customer_state), ''), 'Unknown state')
)
SELECT customer_state, delivery_orders, late_orders,
       delivery_orders - late_orders AS on_time_orders,
       ROUND(100.0 * late_orders / NULLIF(delivery_orders, 0), 2) AS late_delivery_pct,
       ROUND(average_delivery_days, 2) AS average_delivery_days,
       ((200 * positive_delay_days + late_orders)
         / (2 * NULLIF(late_orders, 0))) / 100.0 AS average_positive_delay_days
FROM totals
ORDER BY late_orders DESC, 1.0 * late_orders / delivery_orders DESC, customer_state ASC;

-- result: category_delivery
-- Q9. Which product categories appear in orders with late delivery?
-- Count an order once per distinct category, even if several items share it.
-- Categories overlap; these counts cannot be added to get total orders.
-- Missing item/product/category details remain in Unknown category.
WITH order_categories AS (
    SELECT DISTINCT o.order_id,
           COALESCE(NULLIF(TRIM(p.category_label), ''), 'Unknown category') AS category_label,
           o.is_late, o.delivery_days, o.delay_days
    FROM v_order_analysis o
    LEFT JOIN v_clean_order_items i ON i.order_id = o.order_id
    LEFT JOIN v_products_labeled p ON p.product_id = i.product_id
    WHERE o.delivery_eligible = 1
), totals AS (
    SELECT category_label, COUNT(*) AS delivery_orders, SUM(is_late) AS late_orders,
           AVG(delivery_days) AS average_delivery_days,
           SUM(CASE WHEN is_late = 1 THEN delay_days ELSE 0 END) AS positive_delay_days
    FROM order_categories
    GROUP BY category_label
)
SELECT category_label, delivery_orders, late_orders,
       delivery_orders - late_orders AS on_time_orders,
       ROUND(100.0 * late_orders / NULLIF(delivery_orders, 0), 2) AS late_delivery_pct,
       ROUND(average_delivery_days, 2) AS average_delivery_days,
       ((200 * positive_delay_days + late_orders)
         / (2 * NULLIF(late_orders, 0))) / 100.0 AS average_positive_delay_days
FROM totals
ORDER BY late_orders DESC, 1.0 * late_orders / delivery_orders DESC, category_label ASC;

-- result: seller_delivery
-- Q10. Which sellers' single-seller orders account for the most late deliveries?
-- HAVING requires at least 100 eligible orders, an exploratory reporting cutoff.
-- It does not establish statistical significance or identify who caused a delay.
-- Order-level receipt dates cannot attribute delays within multi-seller orders.
WITH totals AS (
    SELECT o.single_seller_id AS seller_id,
           COALESCE(NULLIF(TRIM(s.seller_state), ''), 'Unknown state') AS seller_state,
           COUNT(*) AS delivery_orders, SUM(o.is_late) AS late_orders,
           AVG(o.delivery_days) AS average_delivery_days,
           SUM(CASE WHEN o.is_late = 1 THEN o.delay_days ELSE 0 END) AS positive_delay_days
    FROM v_order_analysis o
    LEFT JOIN v_clean_sellers s ON s.seller_id = o.single_seller_id
    WHERE o.seller_delivery_eligible = 1
    GROUP BY o.single_seller_id,
             COALESCE(NULLIF(TRIM(s.seller_state), ''), 'Unknown state')
    HAVING COUNT(*) >= 100
)
SELECT seller_id, seller_state, delivery_orders, late_orders,
       delivery_orders - late_orders AS on_time_orders,
       ROUND(100.0 * late_orders / NULLIF(delivery_orders, 0), 2) AS late_delivery_pct,
       ROUND(average_delivery_days, 2) AS average_delivery_days,
       ((200 * positive_delay_days + late_orders)
         / (2 * NULLIF(late_orders, 0))) / 100.0 AS average_positive_delay_days
FROM totals
ORDER BY late_orders DESC, 1.0 * late_orders / delivery_orders DESC, seller_id ASC;
