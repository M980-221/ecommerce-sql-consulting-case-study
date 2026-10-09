-- Part 7: reporting views for the three planned dashboard pages.
-- Run after Part 3, in the validation runner's transaction.
-- Purchases: 1 Feb 2017 to 31 Jul 2018; final observed outcomes in the source.
-- Raw records, clean views and metric eligibility rules are unchanged.

DROP VIEW IF EXISTS v_reporting_customers;
DROP VIEW IF EXISTS v_reporting_order_categories;
DROP VIEW IF EXISTS v_reporting_sales_items;
DROP VIEW IF EXISTS v_reporting_orders;

-- Grain/key: one row per order_id, including excluded period orders.
-- Filter sales_eligible, delivery_eligible or review_eligible for each measure.
-- Sum money here before joining any item or category rows.
CREATE VIEW v_reporting_orders AS
SELECT order_id, customer_id, customer_unique_id, order_status,
       order_purchase_timestamp,
       SUBSTR(order_purchase_timestamp, 1, 7) AS purchase_month,
       order_approved_at, order_delivered_carrier_date,
       order_delivered_customer_date, order_estimated_delivery_date,
       customer_city,
       COALESCE(NULLIF(TRIM(customer_state), ''), 'Unknown state') AS customer_state,
       item_count, seller_count, single_seller_id,
       product_sales_cents, freight_cents, payment_count, payment_cents,
       review_id, review_score, review_creation_date, review_answer_timestamp,
       sales_eligible, delivery_eligible, review_eligible, seller_delivery_eligible,
       is_late, delivery_days, delay_days, payment_difference_cents
FROM v_order_analysis
WHERE in_reporting_period = 1;

-- Grain/key: one row per (order_id, order_item_id), sales-eligible orders only.
-- Item prices add to product sales; order counts require COUNT(DISTINCT order_id).
-- No order-level total is repeated here. Unknown categories remain included.
CREATE VIEW v_reporting_sales_items AS
SELECT i.order_id, i.order_item_id, i.product_id, i.seller_id,
       o.order_purchase_timestamp, o.purchase_month,
       o.customer_unique_id, o.customer_state,
       COALESCE(NULLIF(TRIM(p.category_label), ''), 'Unknown category') AS category_label,
       COALESCE(p.category_status, 'missing') AS category_status,
       i.price_cents, i.freight_value_cents
FROM v_reporting_orders o
JOIN v_clean_order_items i ON i.order_id = o.order_id
LEFT JOIN v_products_labeled p ON p.product_id = i.product_id
WHERE o.sales_eligible = 1;

-- Grain/key: one row per (order_id, category_label), delivery-eligible orders.
-- Join to reporting_orders for category delivery comparisons, not money totals.
-- One order can belong to several categories; category counts are not additive.
CREATE VIEW v_reporting_order_categories AS
SELECT DISTINCT o.order_id,
       COALESCE(NULLIF(TRIM(p.category_label), ''), 'Unknown category') AS category_label
FROM v_reporting_orders o
LEFT JOIN v_clean_order_items i ON i.order_id = o.order_id
LEFT JOIN v_products_labeled p ON p.product_id = i.product_id
WHERE o.delivery_eligible = 1;

-- Grain/key: one row per customer_unique_id with at least one eligible sale.
-- This covers the full reporting window, with no top-20 filter.
-- For a narrower date/state filter, regroup reporting_orders before counting
-- repeat customers; these full-window customer totals do not change with a slicer.
CREATE VIEW v_reporting_customers AS
WITH totals AS (
    SELECT customer_unique_id, COUNT(*) AS sales_orders,
           SUM(product_sales_cents) AS product_sales_cents,
           MIN(order_purchase_timestamp) AS first_purchase_timestamp,
           MAX(order_purchase_timestamp) AS last_purchase_timestamp,
           SUM(review_eligible) AS reviewed_orders,
           SUM(CASE WHEN review_eligible = 1 THEN review_score ELSE 0 END) AS review_score_sum,
           SUM(CASE WHEN review_eligible = 1 AND review_score IN (1, 2)
                    THEN 1 ELSE 0 END) AS low_score_orders
    FROM v_reporting_orders
    WHERE sales_eligible = 1
    GROUP BY customer_unique_id
)
SELECT customer_unique_id, sales_orders, product_sales_cents,
       product_sales_cents / 100.0 AS product_sales_value,
       ((2 * product_sales_cents + sales_orders)
         / (2 * NULLIF(sales_orders, 0))) / 100.0 AS average_order_value,
       first_purchase_timestamp, last_purchase_timestamp,
       reviewed_orders, review_score_sum, low_score_orders,
       ((20000 * reviewed_orders + sales_orders)
         / (2 * NULLIF(sales_orders, 0))) / 100.0 AS review_coverage_pct,
       ((200 * review_score_sum + reviewed_orders)
         / (2 * NULLIF(reviewed_orders, 0))) / 100.0 AS average_review_score,
       CASE WHEN sales_orders >= 2 THEN 1 ELSE 0 END AS repeat_customer
FROM totals;

