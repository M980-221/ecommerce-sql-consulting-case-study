-- Tableau inputs, rebuilt from the validated Part 7 reporting views.
-- Stable integer keys replace the source identifiers. Both sources contain
-- purchases from 1 Feb 2017 through 31 Jul 2018, with final observed outcomes.

-- result: orders
-- One row per order. Filter date/state first, then regroup customer_key when
-- calculating observed repeat customers. Missing money and scores stay NULL.
SELECT ROW_NUMBER() OVER (ORDER BY order_id) AS order_key,
       DENSE_RANK() OVER (ORDER BY customer_unique_id) AS customer_key,
       purchase_month || '-01' AS purchase_month,
       customer_state AS buyer_state,
       COALESCE(order_status, 'Unknown status') AS order_status,
       sales_eligible, delivery_eligible, review_eligible,
       product_sales_cents AS product_value_cents,
       CASE WHEN delivery_eligible = 1 THEN
           CAST(STRFTIME('%s', order_delivered_customer_date) AS INTEGER)
           - CAST(STRFTIME('%s', order_purchase_timestamp) AS INTEGER)
       END AS delivery_seconds,
       is_late,
       CASE WHEN delivery_eligible = 1 AND is_late = 1 THEN delay_days END AS positive_delay_days,
       review_score,
       CASE WHEN review_score IS NOT NULL
                  AND review_answer_timestamp < order_delivered_customer_date
            THEN 1 ELSE 0 END AS review_before_delivery
FROM v_reporting_orders
ORDER BY order_id;

-- result: categories
-- One row per order/category. Item value sums within each category; an order
-- with several categories appears in each. Do not sum these category counts
-- to obtain overall orders. Delivery-only pairs have NULL sales value.
WITH order_keys AS (
    SELECT ROW_NUMBER() OVER (ORDER BY order_id) AS order_key, order_id,
           purchase_month, customer_state, is_late, delay_days,
           CASE WHEN delivery_eligible = 1 THEN
               CAST(STRFTIME('%s', order_delivered_customer_date) AS INTEGER)
               - CAST(STRFTIME('%s', order_purchase_timestamp) AS INTEGER)
           END AS delivery_seconds
    FROM v_reporting_orders
), sales AS (
    SELECT order_id, category_label, SUM(price_cents) AS product_value_cents,
           COUNT(*) AS item_count
    FROM v_reporting_sales_items
    GROUP BY order_id, category_label
), category_keys AS (
    SELECT order_id, category_label FROM sales
    UNION
    SELECT order_id, category_label FROM v_reporting_order_categories
)
SELECT o.order_key, k.category_label AS category,
       o.purchase_month || '-01' AS purchase_month, o.customer_state AS buyer_state,
       CASE WHEN s.order_id IS NOT NULL THEN 1 ELSE 0 END AS sales_eligible,
       s.product_value_cents, COALESCE(s.item_count, 0) AS item_count,
       CASE WHEN d.order_id IS NOT NULL THEN 1 ELSE 0 END AS delivery_eligible,
       CASE WHEN d.order_id IS NOT NULL THEN o.is_late END AS is_late,
       CASE WHEN d.order_id IS NOT NULL THEN o.delivery_seconds END AS delivery_seconds,
       CASE WHEN d.order_id IS NOT NULL AND o.is_late = 1 THEN o.delay_days END AS positive_delay_days
FROM category_keys k
JOIN order_keys o ON o.order_id = k.order_id
LEFT JOIN sales s ON s.order_id = k.order_id AND s.category_label = k.category_label
LEFT JOIN v_reporting_order_categories d
    ON d.order_id = k.order_id AND d.category_label = k.category_label
ORDER BY o.order_key, k.category_label;
