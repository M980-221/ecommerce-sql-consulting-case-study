-- PART 3: SOURCE PROFILE
-- Run before cleaning. All queries are read-only.

-- result: column_profile
SELECT 'orders' AS table_name, 'order_id' AS column_name, COUNT(*) AS source_rows,
       SUM(order_id IS NULL OR TRIM(order_id) = '') AS missing_rows,
       SUM(COALESCE(order_id != TRIM(order_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_id), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'customer_id' AS column_name, COUNT(*) AS source_rows,
       SUM(customer_id IS NULL OR TRIM(customer_id) = '') AS missing_rows,
       SUM(COALESCE(customer_id != TRIM(customer_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(customer_id), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_status' AS column_name, COUNT(*) AS source_rows,
       SUM(order_status IS NULL OR TRIM(order_status) = '') AS missing_rows,
       SUM(COALESCE(order_status != TRIM(order_status), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_status), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_purchase_timestamp' AS column_name, COUNT(*) AS source_rows,
       SUM(order_purchase_timestamp IS NULL OR TRIM(order_purchase_timestamp) = '') AS missing_rows,
       SUM(COALESCE(order_purchase_timestamp != TRIM(order_purchase_timestamp), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_purchase_timestamp), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_approved_at' AS column_name, COUNT(*) AS source_rows,
       SUM(order_approved_at IS NULL OR TRIM(order_approved_at) = '') AS missing_rows,
       SUM(COALESCE(order_approved_at != TRIM(order_approved_at), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_approved_at), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_delivered_carrier_date' AS column_name, COUNT(*) AS source_rows,
       SUM(order_delivered_carrier_date IS NULL OR TRIM(order_delivered_carrier_date) = '') AS missing_rows,
       SUM(COALESCE(order_delivered_carrier_date != TRIM(order_delivered_carrier_date), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_delivered_carrier_date), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_delivered_customer_date' AS column_name, COUNT(*) AS source_rows,
       SUM(order_delivered_customer_date IS NULL OR TRIM(order_delivered_customer_date) = '') AS missing_rows,
       SUM(COALESCE(order_delivered_customer_date != TRIM(order_delivered_customer_date), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_delivered_customer_date), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_estimated_delivery_date' AS column_name, COUNT(*) AS source_rows,
       SUM(order_estimated_delivery_date IS NULL OR TRIM(order_estimated_delivery_date) = '') AS missing_rows,
       SUM(COALESCE(order_estimated_delivery_date != TRIM(order_estimated_delivery_date), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_estimated_delivery_date), '')) AS distinct_nonblank_values
FROM orders
UNION ALL
SELECT 'order_items' AS table_name, 'order_id' AS column_name, COUNT(*) AS source_rows,
       SUM(order_id IS NULL OR TRIM(order_id) = '') AS missing_rows,
       SUM(COALESCE(order_id != TRIM(order_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_id), '')) AS distinct_nonblank_values
FROM order_items
UNION ALL
SELECT 'order_items' AS table_name, 'order_item_id' AS column_name, COUNT(*) AS source_rows,
       SUM(order_item_id IS NULL OR TRIM(order_item_id) = '') AS missing_rows,
       SUM(COALESCE(order_item_id != TRIM(order_item_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_item_id), '')) AS distinct_nonblank_values
FROM order_items
UNION ALL
SELECT 'order_items' AS table_name, 'product_id' AS column_name, COUNT(*) AS source_rows,
       SUM(product_id IS NULL OR TRIM(product_id) = '') AS missing_rows,
       SUM(COALESCE(product_id != TRIM(product_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_id), '')) AS distinct_nonblank_values
FROM order_items
UNION ALL
SELECT 'order_items' AS table_name, 'seller_id' AS column_name, COUNT(*) AS source_rows,
       SUM(seller_id IS NULL OR TRIM(seller_id) = '') AS missing_rows,
       SUM(COALESCE(seller_id != TRIM(seller_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(seller_id), '')) AS distinct_nonblank_values
FROM order_items
UNION ALL
SELECT 'order_items' AS table_name, 'shipping_limit_date' AS column_name, COUNT(*) AS source_rows,
       SUM(shipping_limit_date IS NULL OR TRIM(shipping_limit_date) = '') AS missing_rows,
       SUM(COALESCE(shipping_limit_date != TRIM(shipping_limit_date), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(shipping_limit_date), '')) AS distinct_nonblank_values
FROM order_items
UNION ALL
SELECT 'order_items' AS table_name, 'price' AS column_name, COUNT(*) AS source_rows,
       SUM(price IS NULL OR TRIM(price) = '') AS missing_rows,
       SUM(COALESCE(price != TRIM(price), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(price), '')) AS distinct_nonblank_values
FROM order_items
UNION ALL
SELECT 'order_items' AS table_name, 'freight_value' AS column_name, COUNT(*) AS source_rows,
       SUM(freight_value IS NULL OR TRIM(freight_value) = '') AS missing_rows,
       SUM(COALESCE(freight_value != TRIM(freight_value), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(freight_value), '')) AS distinct_nonblank_values
FROM order_items
UNION ALL
SELECT 'customers' AS table_name, 'customer_id' AS column_name, COUNT(*) AS source_rows,
       SUM(customer_id IS NULL OR TRIM(customer_id) = '') AS missing_rows,
       SUM(COALESCE(customer_id != TRIM(customer_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(customer_id), '')) AS distinct_nonblank_values
FROM customers
UNION ALL
SELECT 'customers' AS table_name, 'customer_unique_id' AS column_name, COUNT(*) AS source_rows,
       SUM(customer_unique_id IS NULL OR TRIM(customer_unique_id) = '') AS missing_rows,
       SUM(COALESCE(customer_unique_id != TRIM(customer_unique_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(customer_unique_id), '')) AS distinct_nonblank_values
FROM customers
UNION ALL
SELECT 'customers' AS table_name, 'customer_zip_code_prefix' AS column_name, COUNT(*) AS source_rows,
       SUM(customer_zip_code_prefix IS NULL OR TRIM(customer_zip_code_prefix) = '') AS missing_rows,
       SUM(COALESCE(customer_zip_code_prefix != TRIM(customer_zip_code_prefix), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(customer_zip_code_prefix), '')) AS distinct_nonblank_values
FROM customers
UNION ALL
SELECT 'customers' AS table_name, 'customer_city' AS column_name, COUNT(*) AS source_rows,
       SUM(customer_city IS NULL OR TRIM(customer_city) = '') AS missing_rows,
       SUM(COALESCE(customer_city != TRIM(customer_city), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(customer_city), '')) AS distinct_nonblank_values
FROM customers
UNION ALL
SELECT 'customers' AS table_name, 'customer_state' AS column_name, COUNT(*) AS source_rows,
       SUM(customer_state IS NULL OR TRIM(customer_state) = '') AS missing_rows,
       SUM(COALESCE(customer_state != TRIM(customer_state), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(customer_state), '')) AS distinct_nonblank_values
FROM customers
UNION ALL
SELECT 'products' AS table_name, 'product_id' AS column_name, COUNT(*) AS source_rows,
       SUM(product_id IS NULL OR TRIM(product_id) = '') AS missing_rows,
       SUM(COALESCE(product_id != TRIM(product_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_id), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_category_name' AS column_name, COUNT(*) AS source_rows,
       SUM(product_category_name IS NULL OR TRIM(product_category_name) = '') AS missing_rows,
       SUM(COALESCE(product_category_name != TRIM(product_category_name), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_category_name), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_name_lenght' AS column_name, COUNT(*) AS source_rows,
       SUM(product_name_lenght IS NULL OR TRIM(product_name_lenght) = '') AS missing_rows,
       SUM(COALESCE(product_name_lenght != TRIM(product_name_lenght), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_name_lenght), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_description_lenght' AS column_name, COUNT(*) AS source_rows,
       SUM(product_description_lenght IS NULL OR TRIM(product_description_lenght) = '') AS missing_rows,
       SUM(COALESCE(product_description_lenght != TRIM(product_description_lenght), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_description_lenght), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_photos_qty' AS column_name, COUNT(*) AS source_rows,
       SUM(product_photos_qty IS NULL OR TRIM(product_photos_qty) = '') AS missing_rows,
       SUM(COALESCE(product_photos_qty != TRIM(product_photos_qty), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_photos_qty), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_weight_g' AS column_name, COUNT(*) AS source_rows,
       SUM(product_weight_g IS NULL OR TRIM(product_weight_g) = '') AS missing_rows,
       SUM(COALESCE(product_weight_g != TRIM(product_weight_g), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_weight_g), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_length_cm' AS column_name, COUNT(*) AS source_rows,
       SUM(product_length_cm IS NULL OR TRIM(product_length_cm) = '') AS missing_rows,
       SUM(COALESCE(product_length_cm != TRIM(product_length_cm), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_length_cm), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_height_cm' AS column_name, COUNT(*) AS source_rows,
       SUM(product_height_cm IS NULL OR TRIM(product_height_cm) = '') AS missing_rows,
       SUM(COALESCE(product_height_cm != TRIM(product_height_cm), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_height_cm), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'products' AS table_name, 'product_width_cm' AS column_name, COUNT(*) AS source_rows,
       SUM(product_width_cm IS NULL OR TRIM(product_width_cm) = '') AS missing_rows,
       SUM(COALESCE(product_width_cm != TRIM(product_width_cm), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_width_cm), '')) AS distinct_nonblank_values
FROM products
UNION ALL
SELECT 'sellers' AS table_name, 'seller_id' AS column_name, COUNT(*) AS source_rows,
       SUM(seller_id IS NULL OR TRIM(seller_id) = '') AS missing_rows,
       SUM(COALESCE(seller_id != TRIM(seller_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(seller_id), '')) AS distinct_nonblank_values
FROM sellers
UNION ALL
SELECT 'sellers' AS table_name, 'seller_zip_code_prefix' AS column_name, COUNT(*) AS source_rows,
       SUM(seller_zip_code_prefix IS NULL OR TRIM(seller_zip_code_prefix) = '') AS missing_rows,
       SUM(COALESCE(seller_zip_code_prefix != TRIM(seller_zip_code_prefix), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(seller_zip_code_prefix), '')) AS distinct_nonblank_values
FROM sellers
UNION ALL
SELECT 'sellers' AS table_name, 'seller_city' AS column_name, COUNT(*) AS source_rows,
       SUM(seller_city IS NULL OR TRIM(seller_city) = '') AS missing_rows,
       SUM(COALESCE(seller_city != TRIM(seller_city), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(seller_city), '')) AS distinct_nonblank_values
FROM sellers
UNION ALL
SELECT 'sellers' AS table_name, 'seller_state' AS column_name, COUNT(*) AS source_rows,
       SUM(seller_state IS NULL OR TRIM(seller_state) = '') AS missing_rows,
       SUM(COALESCE(seller_state != TRIM(seller_state), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(seller_state), '')) AS distinct_nonblank_values
FROM sellers
UNION ALL
SELECT 'order_payments' AS table_name, 'order_id' AS column_name, COUNT(*) AS source_rows,
       SUM(order_id IS NULL OR TRIM(order_id) = '') AS missing_rows,
       SUM(COALESCE(order_id != TRIM(order_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_id), '')) AS distinct_nonblank_values
FROM order_payments
UNION ALL
SELECT 'order_payments' AS table_name, 'payment_sequential' AS column_name, COUNT(*) AS source_rows,
       SUM(payment_sequential IS NULL OR TRIM(payment_sequential) = '') AS missing_rows,
       SUM(COALESCE(payment_sequential != TRIM(payment_sequential), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(payment_sequential), '')) AS distinct_nonblank_values
FROM order_payments
UNION ALL
SELECT 'order_payments' AS table_name, 'payment_type' AS column_name, COUNT(*) AS source_rows,
       SUM(payment_type IS NULL OR TRIM(payment_type) = '') AS missing_rows,
       SUM(COALESCE(payment_type != TRIM(payment_type), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(payment_type), '')) AS distinct_nonblank_values
FROM order_payments
UNION ALL
SELECT 'order_payments' AS table_name, 'payment_installments' AS column_name, COUNT(*) AS source_rows,
       SUM(payment_installments IS NULL OR TRIM(payment_installments) = '') AS missing_rows,
       SUM(COALESCE(payment_installments != TRIM(payment_installments), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(payment_installments), '')) AS distinct_nonblank_values
FROM order_payments
UNION ALL
SELECT 'order_payments' AS table_name, 'payment_value' AS column_name, COUNT(*) AS source_rows,
       SUM(payment_value IS NULL OR TRIM(payment_value) = '') AS missing_rows,
       SUM(COALESCE(payment_value != TRIM(payment_value), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(payment_value), '')) AS distinct_nonblank_values
FROM order_payments
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_id' AS column_name, COUNT(*) AS source_rows,
       SUM(review_id IS NULL OR TRIM(review_id) = '') AS missing_rows,
       SUM(COALESCE(review_id != TRIM(review_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(review_id), '')) AS distinct_nonblank_values
FROM order_reviews
UNION ALL
SELECT 'order_reviews' AS table_name, 'order_id' AS column_name, COUNT(*) AS source_rows,
       SUM(order_id IS NULL OR TRIM(order_id) = '') AS missing_rows,
       SUM(COALESCE(order_id != TRIM(order_id), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(order_id), '')) AS distinct_nonblank_values
FROM order_reviews
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_score' AS column_name, COUNT(*) AS source_rows,
       SUM(review_score IS NULL OR TRIM(review_score) = '') AS missing_rows,
       SUM(COALESCE(review_score != TRIM(review_score), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(review_score), '')) AS distinct_nonblank_values
FROM order_reviews
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_comment_title' AS column_name, COUNT(*) AS source_rows,
       SUM(review_comment_title IS NULL OR TRIM(review_comment_title) = '') AS missing_rows,
       SUM(COALESCE(review_comment_title != TRIM(review_comment_title), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(review_comment_title), '')) AS distinct_nonblank_values
FROM order_reviews
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_comment_message' AS column_name, COUNT(*) AS source_rows,
       SUM(review_comment_message IS NULL OR TRIM(review_comment_message) = '') AS missing_rows,
       SUM(COALESCE(review_comment_message != TRIM(review_comment_message), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(review_comment_message), '')) AS distinct_nonblank_values
FROM order_reviews
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_creation_date' AS column_name, COUNT(*) AS source_rows,
       SUM(review_creation_date IS NULL OR TRIM(review_creation_date) = '') AS missing_rows,
       SUM(COALESCE(review_creation_date != TRIM(review_creation_date), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(review_creation_date), '')) AS distinct_nonblank_values
FROM order_reviews
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_answer_timestamp' AS column_name, COUNT(*) AS source_rows,
       SUM(review_answer_timestamp IS NULL OR TRIM(review_answer_timestamp) = '') AS missing_rows,
       SUM(COALESCE(review_answer_timestamp != TRIM(review_answer_timestamp), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(review_answer_timestamp), '')) AS distinct_nonblank_values
FROM order_reviews
UNION ALL
SELECT 'category_translation' AS table_name, 'product_category_name' AS column_name, COUNT(*) AS source_rows,
       SUM(product_category_name IS NULL OR TRIM(product_category_name) = '') AS missing_rows,
       SUM(COALESCE(product_category_name != TRIM(product_category_name), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_category_name), '')) AS distinct_nonblank_values
FROM category_translation
UNION ALL
SELECT 'category_translation' AS table_name, 'product_category_name_english' AS column_name, COUNT(*) AS source_rows,
       SUM(product_category_name_english IS NULL OR TRIM(product_category_name_english) = '') AS missing_rows,
       SUM(COALESCE(product_category_name_english != TRIM(product_category_name_english), 0)) AS rows_with_outer_spaces,
       COUNT(DISTINCT NULLIF(TRIM(product_category_name_english), '')) AS distinct_nonblank_values
FROM category_translation;

-- result: exact_duplicate_records
SELECT 'orders' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM orders
      GROUP BY order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date HAVING COUNT(*) > 1)
UNION ALL
SELECT 'order_items' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM order_items
      GROUP BY order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value HAVING COUNT(*) > 1)
UNION ALL
SELECT 'customers' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM customers
      GROUP BY customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state HAVING COUNT(*) > 1)
UNION ALL
SELECT 'products' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM products
      GROUP BY product_id, product_category_name, product_name_lenght, product_description_lenght, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm HAVING COUNT(*) > 1)
UNION ALL
SELECT 'sellers' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM sellers
      GROUP BY seller_id, seller_zip_code_prefix, seller_city, seller_state HAVING COUNT(*) > 1)
UNION ALL
SELECT 'order_payments' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM order_payments
      GROUP BY order_id, payment_sequential, payment_type, payment_installments, payment_value HAVING COUNT(*) > 1)
UNION ALL
SELECT 'order_reviews' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM order_reviews
      GROUP BY review_id, order_id, review_score, review_comment_title, review_comment_message, review_creation_date, review_answer_timestamp HAVING COUNT(*) > 1)
UNION ALL
SELECT 'category_translation' AS table_name, COALESCE(SUM(n - 1), 0) AS duplicate_extra_rows
FROM (SELECT COUNT(*) AS n FROM category_translation
      GROUP BY product_category_name, product_category_name_english HAVING COUNT(*) > 1);

-- result: date_ranges
SELECT 'orders' AS table_name, 'order_purchase_timestamp' AS column_name,
       MIN(NULLIF(TRIM(order_purchase_timestamp), '')) AS first_value,
       MAX(NULLIF(TRIM(order_purchase_timestamp), '')) AS last_value FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_approved_at' AS column_name,
       MIN(NULLIF(TRIM(order_approved_at), '')) AS first_value,
       MAX(NULLIF(TRIM(order_approved_at), '')) AS last_value FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_delivered_carrier_date' AS column_name,
       MIN(NULLIF(TRIM(order_delivered_carrier_date), '')) AS first_value,
       MAX(NULLIF(TRIM(order_delivered_carrier_date), '')) AS last_value FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_delivered_customer_date' AS column_name,
       MIN(NULLIF(TRIM(order_delivered_customer_date), '')) AS first_value,
       MAX(NULLIF(TRIM(order_delivered_customer_date), '')) AS last_value FROM orders
UNION ALL
SELECT 'orders' AS table_name, 'order_estimated_delivery_date' AS column_name,
       MIN(NULLIF(TRIM(order_estimated_delivery_date), '')) AS first_value,
       MAX(NULLIF(TRIM(order_estimated_delivery_date), '')) AS last_value FROM orders
UNION ALL
SELECT 'order_items' AS table_name, 'shipping_limit_date' AS column_name,
       MIN(NULLIF(TRIM(shipping_limit_date), '')) AS first_value,
       MAX(NULLIF(TRIM(shipping_limit_date), '')) AS last_value FROM order_items
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_creation_date' AS column_name,
       MIN(NULLIF(TRIM(review_creation_date), '')) AS first_value,
       MAX(NULLIF(TRIM(review_creation_date), '')) AS last_value FROM order_reviews
UNION ALL
SELECT 'order_reviews' AS table_name, 'review_answer_timestamp' AS column_name,
       MIN(NULLIF(TRIM(review_answer_timestamp), '')) AS first_value,
       MAX(NULLIF(TRIM(review_answer_timestamp), '')) AS last_value FROM order_reviews;

