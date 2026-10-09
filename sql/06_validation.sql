-- Part 7: validation and payment reconciliation
-- Run after Part 3. The source tables and their values are left unchanged.
-- Difference means payment minus product value minus freight, in integer cents.
-- A difference records an observed mismatch, not its business cause.

-- result: population_validation
-- Check the exact order-ID set, one row per order, and preserved source money.
SELECT (SELECT COUNT(*) FROM orders) AS source_orders,
       COUNT(*) AS model_rows, COUNT(DISTINCT order_id) AS model_distinct_orders,
       (SELECT COUNT(*) FROM (
           SELECT order_id FROM orders EXCEPT SELECT order_id FROM v_order_analysis
       )) AS source_orders_missing_from_model,
       (SELECT COUNT(*) FROM (
           SELECT order_id FROM v_order_analysis EXCEPT SELECT order_id FROM orders
       )) AS model_orders_missing_from_source,
       COALESCE(SUM(in_reporting_period), 0) AS reporting_period_orders,
       COALESCE(SUM(sales_eligible), 0) AS sales_orders,
       COALESCE(SUM(delivery_eligible), 0) AS delivery_orders,
       COALESCE(SUM(review_eligible), 0) AS reviewed_sales_orders,
       COALESCE(SUM(CASE WHEN delivery_eligible = 1 AND review_eligible = 1 THEN 1 ELSE 0 END), 0)
           AS delivery_review_orders,
       COALESCE(SUM(seller_delivery_eligible), 0) AS single_seller_delivery_orders,
       COALESCE(SUM(CASE WHEN sales_eligible = 1 THEN product_sales_cents ELSE 0 END), 0)
           AS sales_product_sales_cents,
       (SELECT COALESCE(SUM(price_cents), 0) FROM v_clean_order_items) AS source_product_sales_cents,
       COALESCE(SUM(product_sales_cents), 0) AS model_product_sales_cents,
       (SELECT COALESCE(SUM(freight_value_cents), 0) FROM v_clean_order_items) AS source_freight_cents,
       COALESCE(SUM(freight_cents), 0) AS model_freight_cents,
       (SELECT COALESCE(SUM(payment_value_cents), 0) FROM v_clean_order_payments) AS source_payment_cents,
       COALESCE(SUM(payment_cents), 0) AS model_payment_cents,
       (SELECT COUNT(*) FROM order_reviews) AS source_review_rows,
       (SELECT COUNT(*) FROM v_order_review) AS selected_review_rows
FROM v_order_analysis;

-- result: reconciliation_summary
-- Keep missing sides separate: an absent payment is not a zero payment.
-- Only orders with both items and payment rows have a comparable difference.
WITH groups(group_order, reconciliation_group) AS (
    VALUES (1, 'missing_items_and_payments'), (2, 'missing_items'),
           (3, 'missing_payments'), (4, 'exact_match'),
           (5, 'one_cent_difference'), (6, 'payment_below_expected'),
           (7, 'payment_above_expected')
), classified AS (
    SELECT *,
           CASE WHEN item_count = 0 AND payment_count = 0 THEN 'missing_items_and_payments'
                WHEN item_count = 0 THEN 'missing_items'
                WHEN payment_count = 0 THEN 'missing_payments'
                WHEN payment_difference_cents = 0 THEN 'exact_match'
                WHEN ABS(payment_difference_cents) = 1 THEN 'one_cent_difference'
                WHEN payment_difference_cents < -1 THEN 'payment_below_expected'
                ELSE 'payment_above_expected' END AS reconciliation_group
    FROM v_order_analysis
)
SELECT g.reconciliation_group, COUNT(o.order_id) AS orders,
       COALESCE(SUM(o.in_reporting_period), 0) AS reporting_period_orders,
       COALESCE(SUM(o.sales_eligible), 0) AS sales_orders,
       COALESCE(SUM(o.item_count), 0) AS item_rows,
       COALESCE(SUM(o.payment_count), 0) AS payment_rows,
       SUM(o.product_sales_cents + o.freight_cents) AS expected_payment_cents,
       SUM(o.payment_cents) AS payment_cents,
       SUM(o.payment_difference_cents) AS net_difference_cents,
       SUM(ABS(o.payment_difference_cents)) AS absolute_difference_cents,
       MIN(o.payment_difference_cents) AS min_difference_cents,
       MAX(o.payment_difference_cents) AS max_difference_cents
FROM groups g
LEFT JOIN classified o ON o.reconciliation_group = g.reconciliation_group
GROUP BY g.group_order, g.reconciliation_group
ORDER BY g.group_order;

-- result: reconciliation_patterns
-- Describe combinations that occur in mismatched orders without assigning causes.
WITH payment_flags AS (
    SELECT order_id,
           MAX(CASE WHEN payment_type = 'voucher' THEN 1 ELSE 0 END) AS has_voucher,
           SUM(CASE WHEN payment_value_cents = 0 THEN 1 ELSE 0 END) AS zero_payment_components
    FROM v_clean_order_payments
    GROUP BY order_id
), exceptions AS (
    SELECT o.*,
           CASE WHEN ABS(o.payment_difference_cents) = 1 THEN 'one_cent' ELSE 'over_one_cent' END
               AS difference_band,
           CASE WHEN o.payment_difference_cents < 0 THEN 'below' ELSE 'above' END AS difference_direction,
           p.has_voucher, p.zero_payment_components,
           CASE WHEN o.payment_count > 1 THEN 1 ELSE 0 END AS multiple_payments,
           CASE WHEN o.item_count > 1 THEN 1 ELSE 0 END AS multiple_items
    FROM v_order_analysis o
    JOIN payment_flags p ON p.order_id = o.order_id
    WHERE o.payment_difference_cents != 0
)
SELECT difference_band, difference_direction, has_voucher, multiple_payments, multiple_items,
       COUNT(*) AS orders,
       SUM(product_sales_cents + freight_cents) AS expected_payment_cents,
       SUM(payment_cents) AS payment_cents,
       SUM(payment_difference_cents) AS net_difference_cents,
       SUM(ABS(payment_difference_cents)) AS absolute_difference_cents,
       SUM(CASE WHEN zero_payment_components > 0 THEN 1 ELSE 0 END) AS zero_payment_orders
FROM exceptions
GROUP BY difference_band, difference_direction, has_voucher, multiple_payments, multiple_items
ORDER BY difference_band, difference_direction, has_voucher, multiple_payments, multiple_items;

-- result: reconciliation_exceptions
-- Export every comparable nonzero difference, including the one-cent cases.
-- Payment methods are distinct and alphabetically ordered for reproducible output.
WITH methods AS (
    SELECT order_id, GROUP_CONCAT(payment_type, '|') AS payment_methods
    FROM (SELECT DISTINCT order_id, payment_type FROM v_clean_order_payments
          ORDER BY order_id, payment_type)
    GROUP BY order_id
), payment_flags AS (
    SELECT order_id,
           MAX(CASE WHEN payment_type = 'voucher' THEN 1 ELSE 0 END) AS has_voucher,
           SUM(CASE WHEN payment_value_cents = 0 THEN 1 ELSE 0 END) AS zero_payment_components
    FROM v_clean_order_payments
    GROUP BY order_id
)
SELECT o.order_id, o.order_status, o.order_purchase_timestamp,
       o.in_reporting_period, o.sales_eligible, o.item_count, o.payment_count,
       o.product_sales_cents, o.freight_cents,
       o.product_sales_cents + o.freight_cents AS expected_payment_cents,
       o.payment_cents, o.payment_difference_cents AS difference_cents,
       CASE WHEN ABS(o.payment_difference_cents) = 1 THEN 'one_cent' ELSE 'over_one_cent' END
           AS difference_band,
       CASE WHEN o.payment_difference_cents < 0 THEN 'below' ELSE 'above' END AS difference_direction,
       m.payment_methods, p.has_voucher, p.zero_payment_components
FROM v_order_analysis o
JOIN methods m ON m.order_id = o.order_id
JOIN payment_flags p ON p.order_id = o.order_id
WHERE o.payment_difference_cents != 0
ORDER BY ABS(o.payment_difference_cents) DESC, o.order_id ASC;

-- result: join_fanout_summary
-- Demonstrate the unsafe many-to-many item/payment join using source-grain rows.
-- Compare the same matched orders with their correctly aggregated order totals.
-- The unsafe amounts below are diagnostic examples, never reporting measures.
WITH correct AS (
    SELECT COUNT(*) AS matched_orders,
           COALESCE(SUM(CASE WHEN item_count > 1 THEN 1 ELSE 0 END), 0) AS orders_with_multiple_items,
           COALESCE(SUM(CASE WHEN payment_count > 1 THEN 1 ELSE 0 END), 0) AS orders_with_multiple_payments,
           COALESCE(SUM(CASE WHEN item_count > 1 AND payment_count > 1 THEN 1 ELSE 0 END), 0)
               AS orders_with_both_multiple,
           COALESCE(SUM(item_count), 0) AS correct_item_rows,
           COALESCE(SUM(payment_count), 0) AS correct_payment_rows,
           COALESCE(SUM(product_sales_cents), 0) AS correct_product_sales_cents,
           COALESCE(SUM(freight_cents), 0) AS correct_freight_cents,
           COALESCE(SUM(payment_cents), 0) AS correct_payment_cents
    FROM v_order_analysis
    WHERE item_count > 0 AND payment_count > 0
), unsafe AS (
    SELECT COUNT(*) AS unsafe_join_rows,
           COALESCE(SUM(i.price_cents), 0) AS unsafe_product_sales_cents,
           COALESCE(SUM(i.freight_value_cents), 0) AS unsafe_freight_cents,
           COALESCE(SUM(p.payment_value_cents), 0) AS unsafe_payment_cents
    FROM orders o
    JOIN v_clean_order_items i ON i.order_id = o.order_id
    JOIN v_clean_order_payments p ON p.order_id = o.order_id
)
SELECT c.matched_orders, c.orders_with_multiple_items, c.orders_with_multiple_payments,
       c.orders_with_both_multiple, c.correct_item_rows, c.correct_payment_rows,
       u.unsafe_join_rows, c.correct_product_sales_cents, u.unsafe_product_sales_cents,
       u.unsafe_product_sales_cents - c.correct_product_sales_cents AS product_sales_overstatement_cents,
       c.correct_freight_cents, u.unsafe_freight_cents,
       u.unsafe_freight_cents - c.correct_freight_cents AS freight_overstatement_cents,
       c.correct_payment_cents, u.unsafe_payment_cents,
       u.unsafe_payment_cents - c.correct_payment_cents AS payment_overstatement_cents
FROM correct c CROSS JOIN unsafe u;

-- result: missingness_by_population
-- Missingness depends on the population. Distinguish absent source reviews from
-- source reviews that exist but leave no eligible selected review.
WITH populations(population_order, population) AS (
    VALUES (1, 'full_source'), (2, 'reporting_period'), (3, 'sales'),
           (4, 'delivery'), (5, 'reviewed_sales')
), source_reviews AS (
    SELECT order_id, COUNT(*) AS source_review_count FROM order_reviews GROUP BY order_id
)
SELECT p.population, COUNT(o.order_id) AS orders,
       COALESCE(SUM(CASE WHEN o.item_count = 0 THEN 1 ELSE 0 END), 0) AS orders_without_items,
       COALESCE(SUM(CASE WHEN o.payment_count = 0 THEN 1 ELSE 0 END), 0) AS orders_without_payments,
       COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL AND r.order_id IS NULL THEN 1 ELSE 0 END), 0)
           AS orders_without_source_review,
       COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL AND o.review_id IS NULL THEN 1 ELSE 0 END), 0)
           AS orders_without_selected_review,
       COALESCE(SUM(CASE WHEN r.order_id IS NOT NULL AND o.review_id IS NULL THEN 1 ELSE 0 END), 0)
           AS orders_with_only_invalid_reviews,
       COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL AND o.order_delivered_customer_date IS NULL
                        THEN 1 ELSE 0 END), 0) AS orders_without_actual_delivery_date,
       COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL AND o.order_estimated_delivery_date IS NULL
                        THEN 1 ELSE 0 END), 0) AS orders_without_promised_delivery_date
FROM populations p
LEFT JOIN v_order_analysis o
    ON p.population = 'full_source'
    OR (p.population = 'reporting_period' AND o.in_reporting_period = 1)
    OR (p.population = 'sales' AND o.sales_eligible = 1)
    OR (p.population = 'delivery' AND o.delivery_eligible = 1)
    OR (p.population = 'reviewed_sales' AND o.review_eligible = 1)
LEFT JOIN source_reviews r ON r.order_id = o.order_id
GROUP BY p.population_order, p.population
ORDER BY p.population_order;
