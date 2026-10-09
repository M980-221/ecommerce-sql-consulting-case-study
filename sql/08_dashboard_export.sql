-- Part 8: compact inputs for the local dashboard.
-- Run after Part 7. No source rows or reporting views are changed.
-- The exporter replaces identifiers with stable integer indexes; the browser
-- keeps one row per order and recomputes customer groups after filtering.

-- result: dashboard_orders
-- Include excluded period orders so coverage remains visible in every slice.
SELECT order_id, customer_unique_id, purchase_month, customer_state,
       COALESCE(order_status, 'Unknown status') AS order_status,
       product_sales_cents, sales_eligible, delivery_eligible, is_late,
       CASE WHEN delivery_eligible = 1 THEN
           CAST(STRFTIME('%s', order_delivered_customer_date) AS INTEGER)
           - CAST(STRFTIME('%s', order_purchase_timestamp) AS INTEGER)
       END AS delivery_seconds,
       delay_days, review_score,
       CASE WHEN review_score IS NOT NULL
                  AND review_answer_timestamp < order_delivered_customer_date
            THEN 1 ELSE 0 END AS pre_delivery_review
FROM v_reporting_orders
ORDER BY order_id;

-- result: dashboard_categories
-- Sales amounts belong to items. Delivery belongs to a distinct order/category
-- pair, including orders without items. Keep the two measures separate.
WITH sales AS (
    SELECT order_id, category_label, SUM(price_cents) AS product_sales_cents,
           COUNT(*) AS item_count
    FROM v_reporting_sales_items
    GROUP BY order_id, category_label
), category_keys AS (
    SELECT order_id, category_label FROM sales
    UNION
    SELECT order_id, category_label FROM v_reporting_order_categories
)
SELECT k.order_id, k.category_label, s.product_sales_cents,
       COALESCE(s.item_count, 0) AS item_count,
       CASE WHEN d.order_id IS NOT NULL THEN 1 ELSE 0 END AS delivery_eligible
FROM category_keys k
LEFT JOIN sales s ON s.order_id = k.order_id AND s.category_label = k.category_label
LEFT JOIN v_reporting_order_categories d
    ON d.order_id = k.order_id AND d.category_label = k.category_label
ORDER BY k.order_id, k.category_label;
