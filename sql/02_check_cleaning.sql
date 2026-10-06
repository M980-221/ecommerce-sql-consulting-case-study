-- PART 3: CHECKS AND OBSERVED EXCEPTIONS
-- Read-only. The runner treats core key/count/relationship failures as errors.
-- Documented source exceptions are reported separately from those gates.

-- result: row_counts
SELECT 'orders' AS table_name,
       (SELECT COUNT(*) FROM orders) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_orders) AS clean_rows
UNION ALL
SELECT 'order_items' AS table_name,
       (SELECT COUNT(*) FROM order_items) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_order_items) AS clean_rows
UNION ALL
SELECT 'customers' AS table_name,
       (SELECT COUNT(*) FROM customers) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_customers) AS clean_rows
UNION ALL
SELECT 'products' AS table_name,
       (SELECT COUNT(*) FROM products) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_products) AS clean_rows
UNION ALL
SELECT 'sellers' AS table_name,
       (SELECT COUNT(*) FROM sellers) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_sellers) AS clean_rows
UNION ALL
SELECT 'order_payments' AS table_name,
       (SELECT COUNT(*) FROM order_payments) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_order_payments) AS clean_rows
UNION ALL
SELECT 'order_reviews' AS table_name,
       (SELECT COUNT(*) FROM order_reviews) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_order_reviews) AS clean_rows
UNION ALL
SELECT 'category_translation' AS table_name,
       (SELECT COUNT(*) FROM category_translation) AS raw_rows,
       (SELECT COUNT(*) FROM v_clean_category_translation) AS clean_rows;

-- result: key_checks
SELECT 'orders' AS table_name, 'order_id' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_orders WHERE order_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT order_id FROM v_clean_orders
           GROUP BY order_id HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'order_items' AS table_name, 'order_id + order_item_id' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_order_items WHERE order_id IS NULL OR order_item_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT order_id, order_item_id FROM v_clean_order_items
           GROUP BY order_id, order_item_id HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'customers' AS table_name, 'customer_id' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_customers WHERE customer_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT customer_id FROM v_clean_customers
           GROUP BY customer_id HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'products' AS table_name, 'product_id' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_products WHERE product_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT product_id FROM v_clean_products
           GROUP BY product_id HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'sellers' AS table_name, 'seller_id' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_sellers WHERE seller_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT seller_id FROM v_clean_sellers
           GROUP BY seller_id HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'order_payments' AS table_name, 'order_id + payment_sequential' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_order_payments WHERE order_id IS NULL OR payment_sequential IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT order_id, payment_sequential FROM v_clean_order_payments
           GROUP BY order_id, payment_sequential HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'order_reviews' AS table_name, 'order_id + review_id' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_order_reviews WHERE order_id IS NULL OR review_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT order_id, review_id FROM v_clean_order_reviews
           GROUP BY order_id, review_id HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'category_translation' AS table_name, 'product_category_name' AS key_columns,
       (SELECT COUNT(*) FROM v_clean_category_translation WHERE product_category_name IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT product_category_name FROM v_clean_category_translation
           GROUP BY product_category_name HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'order_analysis' AS table_name, 'order_id' AS key_columns,
       (SELECT COUNT(*) FROM v_order_analysis WHERE order_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT order_id FROM v_order_analysis
           GROUP BY order_id HAVING COUNT(*) > 1)) AS duplicate_key_groups
UNION ALL
SELECT 'order_review' AS table_name, 'order_id' AS key_columns,
       (SELECT COUNT(*) FROM v_order_review WHERE order_id IS NULL) AS missing_key_rows,
       (SELECT COUNT(*) FROM (SELECT order_id FROM v_order_review
           GROUP BY order_id HAVING COUNT(*) > 1)) AS duplicate_key_groups;

-- result: relationships
SELECT 'orders.customer_id -> customers.customer_id' AS relationship, COUNT(*) AS unmatched_rows
FROM v_clean_orders a
LEFT JOIN v_clean_customers b ON a.customer_id = b.customer_id
WHERE b.customer_id IS NULL
UNION ALL
SELECT 'order_items.order_id -> orders.order_id' AS relationship, COUNT(*) AS unmatched_rows
FROM v_clean_order_items a
LEFT JOIN v_clean_orders b ON a.order_id = b.order_id
WHERE b.order_id IS NULL
UNION ALL
SELECT 'order_items.product_id -> products.product_id' AS relationship, COUNT(*) AS unmatched_rows
FROM v_clean_order_items a
LEFT JOIN v_clean_products b ON a.product_id = b.product_id
WHERE b.product_id IS NULL
UNION ALL
SELECT 'order_items.seller_id -> sellers.seller_id' AS relationship, COUNT(*) AS unmatched_rows
FROM v_clean_order_items a
LEFT JOIN v_clean_sellers b ON a.seller_id = b.seller_id
WHERE b.seller_id IS NULL
UNION ALL
SELECT 'order_payments.order_id -> orders.order_id' AS relationship, COUNT(*) AS unmatched_rows
FROM v_clean_order_payments a
LEFT JOIN v_clean_orders b ON a.order_id = b.order_id
WHERE b.order_id IS NULL
UNION ALL
SELECT 'order_reviews.order_id -> orders.order_id' AS relationship, COUNT(*) AS unmatched_rows
FROM v_clean_order_reviews a
LEFT JOIN v_clean_orders b ON a.order_id = b.order_id
WHERE b.order_id IS NULL;

-- result: source_issues
SELECT 'missing_product_category' AS issue, (SELECT COUNT(*) FROM v_clean_products WHERE product_category_name IS NULL) AS affected_rows_or_groups
UNION ALL
SELECT 'untranslated_product_category' AS issue, (SELECT COUNT(*) FROM v_products_labeled WHERE category_status = 'untranslated') AS affected_rows_or_groups
UNION ALL
SELECT 'missing_product_dimensions' AS issue, (SELECT COUNT(*) FROM v_clean_products WHERE product_weight_g IS NULL OR product_length_cm IS NULL OR product_height_cm IS NULL OR product_width_cm IS NULL) AS affected_rows_or_groups
UNION ALL
SELECT 'zero_product_weight' AS issue, (SELECT COUNT(*) FROM v_clean_products WHERE product_weight_g = 0) AS affected_rows_or_groups
UNION ALL
SELECT 'delivered_without_actual_date' AS issue, (SELECT COUNT(*) FROM v_clean_orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL) AS affected_rows_or_groups
UNION ALL
SELECT 'other_status_with_actual_date' AS issue, (SELECT COUNT(*) FROM v_clean_orders WHERE order_status != 'delivered' AND order_delivered_customer_date IS NOT NULL) AS affected_rows_or_groups
UNION ALL
SELECT 'actual_before_purchase' AS issue, (SELECT COUNT(*) FROM v_clean_orders WHERE order_delivered_customer_date < order_purchase_timestamp) AS affected_rows_or_groups
UNION ALL
SELECT 'estimated_day_before_purchase_day' AS issue, (SELECT COUNT(*) FROM v_clean_orders WHERE DATE(order_estimated_delivery_date) < DATE(order_purchase_timestamp)) AS affected_rows_or_groups
UNION ALL
SELECT 'carrier_before_purchase' AS issue, (SELECT COUNT(*) FROM v_clean_orders WHERE order_delivered_carrier_date < order_purchase_timestamp) AS affected_rows_or_groups
UNION ALL
SELECT 'carrier_before_approval' AS issue, (SELECT COUNT(*) FROM v_clean_orders WHERE order_delivered_carrier_date < order_approved_at) AS affected_rows_or_groups
UNION ALL
SELECT 'carrier_after_actual_delivery' AS issue, (SELECT COUNT(*) FROM v_clean_orders WHERE order_delivered_carrier_date > order_delivered_customer_date) AS affected_rows_or_groups
UNION ALL
SELECT 'shipping_limit_in_2020' AS issue, (SELECT COUNT(*) FROM v_clean_order_items WHERE shipping_limit_date >= '2020-01-01' AND shipping_limit_date < '2021-01-01') AS affected_rows_or_groups
UNION ALL
SELECT 'orders_with_multiple_reviews' AS issue, (SELECT COUNT(*) FROM (SELECT order_id FROM v_clean_order_reviews GROUP BY order_id HAVING COUNT(*) > 1)) AS affected_rows_or_groups
UNION ALL
SELECT 'review_ids_on_multiple_orders' AS issue, (SELECT COUNT(*) FROM (SELECT review_id FROM v_clean_order_reviews GROUP BY review_id HAVING COUNT(DISTINCT order_id) > 1)) AS affected_rows_or_groups
UNION ALL
SELECT 'invalid_review_chronology_or_score' AS issue, (SELECT COUNT(*) FROM v_review_candidates WHERE review_is_valid = 0) AS affected_rows_or_groups
UNION ALL
SELECT 'review_score_out_of_range' AS issue, (SELECT COUNT(*) FROM v_clean_order_reviews WHERE review_score NOT BETWEEN 1 AND 5 OR review_score IS NULL) AS affected_rows_or_groups
UNION ALL
SELECT 'zero_payment_amount' AS issue, (SELECT COUNT(*) FROM v_clean_order_payments WHERE payment_value_cents = 0) AS affected_rows_or_groups
UNION ALL
SELECT 'zero_payment_installments' AS issue, (SELECT COUNT(*) FROM v_clean_order_payments WHERE payment_installments = 0) AS affected_rows_or_groups
UNION ALL
SELECT 'undefined_payment_type' AS issue, (SELECT COUNT(*) FROM v_clean_order_payments WHERE payment_type = 'not_defined') AS affected_rows_or_groups
UNION ALL
SELECT 'orders_without_items' AS issue, (SELECT COUNT(*) FROM v_order_analysis WHERE item_count = 0) AS affected_rows_or_groups
UNION ALL
SELECT 'orders_without_payments' AS issue, (SELECT COUNT(*) FROM v_order_analysis WHERE payment_count = 0) AS affected_rows_or_groups
UNION ALL
SELECT 'orders_without_source_review' AS issue, (SELECT COUNT(*) FROM v_clean_orders o LEFT JOIN (SELECT DISTINCT order_id FROM v_clean_order_reviews) r ON r.order_id = o.order_id WHERE r.order_id IS NULL) AS affected_rows_or_groups
UNION ALL
SELECT 'orders_without_valid_selected_review' AS issue, (SELECT COUNT(*) FROM v_order_analysis WHERE review_score IS NULL) AS affected_rows_or_groups;

-- result: join_reconciliation
SELECT
    (SELECT COUNT(*) FROM orders) AS raw_orders,
    (SELECT COUNT(*) FROM v_order_analysis) AS modeled_orders,
    (SELECT COUNT(DISTINCT order_id) FROM v_order_analysis) AS distinct_modeled_orders,
    (SELECT SUM(price_cents) FROM v_clean_order_items) AS item_price_cents,
    (SELECT SUM(product_sales_cents) FROM v_order_analysis) AS joined_price_cents,
    (SELECT SUM(freight_value_cents) FROM v_clean_order_items) AS item_freight_cents,
    (SELECT SUM(freight_cents) FROM v_order_analysis) AS joined_freight_cents,
    (SELECT SUM(payment_value_cents) FROM v_clean_order_payments) AS source_payment_cents,
    (SELECT SUM(payment_cents) FROM v_order_analysis) AS joined_payment_cents,
    (SELECT COUNT(*) FROM products) AS source_products,
    (SELECT COUNT(*) FROM v_products_labeled) AS labeled_products;

-- result: populations
SELECT COUNT(*) AS all_orders,
    SUM(in_reporting_period) AS period_orders,
    SUM(in_reporting_period = 1 AND order_status = 'delivered') AS period_delivered_orders,
    SUM(sales_eligible) AS sales_eligible_orders,
    SUM(delivery_eligible) AS delivery_eligible_orders,
    SUM(review_eligible) AS reviewed_sales_orders,
    SUM(seller_delivery_eligible) AS single_seller_delivery_orders,
    SUM(delivery_eligible = 1 AND review_eligible = 1) AS delivery_and_review_orders,
    SUM(sales_eligible = 1 AND customer_unique_id IS NULL) AS sales_without_customer_identity
FROM v_order_analysis;

-- result: month_coverage
SELECT SUBSTR(order_purchase_timestamp, 1, 7) AS purchase_month,
    MIN(DATE(order_purchase_timestamp)) AS first_purchase_day,
    MAX(DATE(order_purchase_timestamp)) AS last_purchase_day,
    COUNT(DISTINCT DATE(order_purchase_timestamp)) AS days_with_orders,
    COUNT(*) AS orders, SUM(order_status = 'delivered') AS delivered_orders
FROM v_clean_orders GROUP BY purchase_month ORDER BY purchase_month;

-- result: review_selection
SELECT
    (SELECT COUNT(*) FROM order_reviews) AS source_review_rows,
    (SELECT COUNT(*) FROM v_review_candidates WHERE review_is_valid = 0) AS invalid_rows,
    (SELECT COUNT(*) FROM v_order_review) AS selected_rows,
    (SELECT COUNT(*) FROM v_review_candidates WHERE review_is_valid = 1)
      - (SELECT COUNT(*) FROM v_order_review) AS additional_valid_reviews_not_selected;

-- result: payment_reconciliation
SELECT COUNT(*) AS orders_with_items_and_payments,
    SUM(payment_difference_cents = 0) AS exact_matches,
    SUM(ABS(payment_difference_cents) = 1) AS one_cent_differences,
    SUM(ABS(payment_difference_cents) > 1) AS differences_over_one_cent,
    MIN(payment_difference_cents) AS min_difference_cents,
    MAX(payment_difference_cents) AS max_difference_cents
FROM v_order_analysis WHERE payment_difference_cents IS NOT NULL;

-- result: status_distribution
SELECT order_status, COUNT(*) AS orders,
    SUM(order_delivered_customer_date IS NULL) AS missing_actual_date
FROM v_clean_orders GROUP BY order_status ORDER BY order_status;

-- result: august_boundary_days
SELECT DATE(order_purchase_timestamp) AS purchase_day,
       COUNT(*) AS orders, SUM(order_status = 'delivered') AS delivered_orders
FROM v_clean_orders
WHERE order_purchase_timestamp >= '2018-08-27'
  AND order_purchase_timestamp < '2018-09-01'
GROUP BY purchase_day
ORDER BY purchase_day;
