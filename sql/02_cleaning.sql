-- PART 3: DATA CLEANING AND ORDER MODEL
-- SQLite 3.25+; run with scripts/prepare_part3.py (transaction + validation).
-- In a SQL client: BEGIN; run this file and 02_check_cleaning.sql; COMMIT
-- only if the required checks pass. Use ROLLBACK if a check fails.
-- Raw tables are never updated or deleted. Only these project views are replaced.

DROP VIEW IF EXISTS v_order_analysis;
DROP VIEW IF EXISTS v_order_payment_totals;
DROP VIEW IF EXISTS v_order_item_totals;
DROP VIEW IF EXISTS v_order_review;
DROP VIEW IF EXISTS v_review_candidates;
DROP VIEW IF EXISTS v_products_labeled;
DROP VIEW IF EXISTS v_clean_category_translation;
DROP VIEW IF EXISTS v_clean_order_reviews;
DROP VIEW IF EXISTS v_clean_order_payments;
DROP VIEW IF EXISTS v_clean_sellers;
DROP VIEW IF EXISTS v_clean_products;
DROP VIEW IF EXISTS v_clean_customers;
DROP VIEW IF EXISTS v_clean_order_items;
DROP VIEW IF EXISTS v_clean_orders;
DROP VIEW IF EXISTS v_p3_date_issues;
DROP VIEW IF EXISTS v_p3_numeric_issues;

-- 1. Check formats before CAST. SQLite can otherwise turn bad text into zero.
-- Values must be nonnegative decimals, at most two decimal places and nine
-- digits before the decimal point. Integer fields may have only zero decimals.
-- Missing product attributes are allowed; transaction amounts and sequences are required.
CREATE VIEW v_p3_numeric_issues AS
WITH cells AS (
    SELECT 'order_items' AS table_name, 'order_item_id' AS column_name, rowid AS source_rowid,
           order_item_id AS raw_value, 'integer' AS expected_type, 1 AS required
    FROM order_items
    UNION ALL
    SELECT 'order_items' AS table_name, 'price' AS column_name, rowid AS source_rowid,
           price AS raw_value, 'money' AS expected_type, 1 AS required
    FROM order_items
    UNION ALL
    SELECT 'order_items' AS table_name, 'freight_value' AS column_name, rowid AS source_rowid,
           freight_value AS raw_value, 'money' AS expected_type, 1 AS required
    FROM order_items
    UNION ALL
    SELECT 'products' AS table_name, 'product_name_lenght' AS column_name, rowid AS source_rowid,
           product_name_lenght AS raw_value, 'integer' AS expected_type, 0 AS required
    FROM products
    UNION ALL
    SELECT 'products' AS table_name, 'product_description_lenght' AS column_name, rowid AS source_rowid,
           product_description_lenght AS raw_value, 'integer' AS expected_type, 0 AS required
    FROM products
    UNION ALL
    SELECT 'products' AS table_name, 'product_photos_qty' AS column_name, rowid AS source_rowid,
           product_photos_qty AS raw_value, 'integer' AS expected_type, 0 AS required
    FROM products
    UNION ALL
    SELECT 'products' AS table_name, 'product_weight_g' AS column_name, rowid AS source_rowid,
           product_weight_g AS raw_value, 'integer' AS expected_type, 0 AS required
    FROM products
    UNION ALL
    SELECT 'products' AS table_name, 'product_length_cm' AS column_name, rowid AS source_rowid,
           product_length_cm AS raw_value, 'integer' AS expected_type, 0 AS required
    FROM products
    UNION ALL
    SELECT 'products' AS table_name, 'product_height_cm' AS column_name, rowid AS source_rowid,
           product_height_cm AS raw_value, 'integer' AS expected_type, 0 AS required
    FROM products
    UNION ALL
    SELECT 'products' AS table_name, 'product_width_cm' AS column_name, rowid AS source_rowid,
           product_width_cm AS raw_value, 'integer' AS expected_type, 0 AS required
    FROM products
    UNION ALL
    SELECT 'order_payments' AS table_name, 'payment_sequential' AS column_name, rowid AS source_rowid,
           payment_sequential AS raw_value, 'integer' AS expected_type, 1 AS required
    FROM order_payments
    UNION ALL
    SELECT 'order_payments' AS table_name, 'payment_installments' AS column_name, rowid AS source_rowid,
           payment_installments AS raw_value, 'integer' AS expected_type, 1 AS required
    FROM order_payments
    UNION ALL
    SELECT 'order_payments' AS table_name, 'payment_value' AS column_name, rowid AS source_rowid,
           payment_value AS raw_value, 'money' AS expected_type, 1 AS required
    FROM order_payments
    UNION ALL
    SELECT 'order_reviews' AS table_name, 'review_score' AS column_name, rowid AS source_rowid,
           review_score AS raw_value, 'integer' AS expected_type, 1 AS required
    FROM order_reviews
), trimmed AS (
    SELECT *, NULLIF(TRIM(raw_value), '') AS value FROM cells
), split AS (
    SELECT *,
           CASE WHEN INSTR(value, '.') = 0 THEN value
                ELSE SUBSTR(value, 1, INSTR(value, '.') - 1) END AS whole,
           CASE WHEN INSTR(value, '.') = 0 THEN NULL
                ELSE SUBSTR(value, INSTR(value, '.') + 1) END AS fraction
    FROM trimmed
)
SELECT table_name, column_name, source_rowid, raw_value, expected_type
FROM split
WHERE (value IS NULL AND required = 1)
   OR (value IS NOT NULL AND (
       whole = '' OR LENGTH(whole) > 9 OR whole GLOB '*[^0-9]*'
       OR (fraction IS NOT NULL AND
           (LENGTH(fraction) NOT BETWEEN 1 AND 2 OR fraction GLOB '*[^0-9]*'))
       OR (expected_type = 'integer' AND fraction GLOB '*[^0]*')
   ));

-- Round-trip timestamps to catch malformed strings and impossible calendar dates.
-- Missing dates are handled by the individual metric eligibility rules below.
CREATE VIEW v_p3_date_issues AS
WITH cells AS (
    SELECT 'orders' AS table_name, 'order_purchase_timestamp' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(order_purchase_timestamp), '') AS value FROM orders
    UNION ALL
    SELECT 'orders' AS table_name, 'order_approved_at' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(order_approved_at), '') AS value FROM orders
    UNION ALL
    SELECT 'orders' AS table_name, 'order_delivered_carrier_date' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(order_delivered_carrier_date), '') AS value FROM orders
    UNION ALL
    SELECT 'orders' AS table_name, 'order_delivered_customer_date' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(order_delivered_customer_date), '') AS value FROM orders
    UNION ALL
    SELECT 'orders' AS table_name, 'order_estimated_delivery_date' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(order_estimated_delivery_date), '') AS value FROM orders
    UNION ALL
    SELECT 'order_items' AS table_name, 'shipping_limit_date' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(shipping_limit_date), '') AS value FROM order_items
    UNION ALL
    SELECT 'order_reviews' AS table_name, 'review_creation_date' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(review_creation_date), '') AS value FROM order_reviews
    UNION ALL
    SELECT 'order_reviews' AS table_name, 'review_answer_timestamp' AS column_name, rowid AS source_rowid,
           NULLIF(TRIM(review_answer_timestamp), '') AS value FROM order_reviews
)
SELECT * FROM cells
WHERE value IS NOT NULL
  AND (LENGTH(value) != 19 OR DATETIME(value, '+0 days') IS NULL
       OR DATETIME(value, '+0 days') != value);

-- Stop on unexpected input rather than publish misleading numeric or date values.
CREATE TEMP TABLE part3_format_guard (
    check_name TEXT,
    issue_count INTEGER CHECK (issue_count = 0)
);
INSERT INTO part3_format_guard SELECT 'numeric formats', COUNT(*) FROM v_p3_numeric_issues;
INSERT INTO part3_format_guard SELECT 'date formats', COUNT(*) FROM v_p3_date_issues;
INSERT INTO part3_format_guard SELECT 'orders: identifiers', COUNT(*) FROM orders
WHERE order_id IS NULL OR TRIM(order_id) = '' OR order_id != TRIM(order_id) OR customer_id IS NULL OR TRIM(customer_id) = '' OR customer_id != TRIM(customer_id);
INSERT INTO part3_format_guard SELECT 'order_items: identifiers', COUNT(*) FROM order_items
WHERE order_id IS NULL OR TRIM(order_id) = '' OR order_id != TRIM(order_id) OR product_id IS NULL OR TRIM(product_id) = '' OR product_id != TRIM(product_id) OR seller_id IS NULL OR TRIM(seller_id) = '' OR seller_id != TRIM(seller_id);
INSERT INTO part3_format_guard SELECT 'customers: identifiers', COUNT(*) FROM customers
WHERE customer_id IS NULL OR TRIM(customer_id) = '' OR customer_id != TRIM(customer_id) OR customer_unique_id IS NULL OR TRIM(customer_unique_id) = '' OR customer_unique_id != TRIM(customer_unique_id);
INSERT INTO part3_format_guard SELECT 'products: identifiers', COUNT(*) FROM products
WHERE product_id IS NULL OR TRIM(product_id) = '' OR product_id != TRIM(product_id);
INSERT INTO part3_format_guard SELECT 'sellers: identifiers', COUNT(*) FROM sellers
WHERE seller_id IS NULL OR TRIM(seller_id) = '' OR seller_id != TRIM(seller_id);
INSERT INTO part3_format_guard SELECT 'order_payments: identifiers', COUNT(*) FROM order_payments
WHERE order_id IS NULL OR TRIM(order_id) = '' OR order_id != TRIM(order_id);
INSERT INTO part3_format_guard SELECT 'order_reviews: identifiers', COUNT(*) FROM order_reviews
WHERE review_id IS NULL OR TRIM(review_id) = '' OR review_id != TRIM(review_id) OR order_id IS NULL OR TRIM(order_id) = '' OR order_id != TRIM(order_id);
DROP TABLE part3_format_guard;

-- 2. Normalise blanks, types and labels. Keep identifiers and ZIP prefixes as text.
-- Required IDs have passed the guard above and remain unchanged for indexed joins.
-- Monetary amounts use integer hundredths (the *_cents fields), after validation.
-- ROUND avoids truncating a binary floating-point approximation of e.g. 19.99.
CREATE VIEW v_clean_orders AS
SELECT order_id,
       customer_id,
       LOWER(NULLIF(TRIM(order_status), '')) AS order_status,
       NULLIF(TRIM(order_purchase_timestamp), '') AS order_purchase_timestamp,
       NULLIF(TRIM(order_approved_at), '') AS order_approved_at,
       NULLIF(TRIM(order_delivered_carrier_date), '') AS order_delivered_carrier_date,
       NULLIF(TRIM(order_delivered_customer_date), '') AS order_delivered_customer_date,
       NULLIF(TRIM(order_estimated_delivery_date), '') AS order_estimated_delivery_date
FROM orders;

CREATE VIEW v_clean_order_items AS
SELECT order_id,
       CAST(NULLIF(TRIM(order_item_id), '') AS INTEGER) AS order_item_id,
       product_id,
       seller_id,
       NULLIF(TRIM(shipping_limit_date), '') AS shipping_limit_date,
       CAST(ROUND(CAST(NULLIF(TRIM(price), '') AS REAL) * 100) AS INTEGER) AS price_cents,
       CAST(ROUND(CAST(NULLIF(TRIM(freight_value), '') AS REAL) * 100) AS INTEGER) AS freight_value_cents
FROM order_items;

CREATE VIEW v_clean_customers AS
SELECT customer_id,
       customer_unique_id,
       NULLIF(TRIM(customer_zip_code_prefix), '') AS customer_zip_code_prefix,
       NULLIF(TRIM(customer_city), '') AS customer_city,
       UPPER(NULLIF(TRIM(customer_state), '')) AS customer_state
FROM customers;

CREATE VIEW v_clean_products AS
SELECT product_id,
       NULLIF(TRIM(product_category_name), '') AS product_category_name,
       CAST(NULLIF(TRIM(product_name_lenght), '') AS INTEGER) AS product_name_lenght,
       CAST(NULLIF(TRIM(product_description_lenght), '') AS INTEGER) AS product_description_lenght,
       CAST(NULLIF(TRIM(product_photos_qty), '') AS INTEGER) AS product_photos_qty,
       CAST(NULLIF(TRIM(product_weight_g), '') AS INTEGER) AS product_weight_g,
       CAST(NULLIF(TRIM(product_length_cm), '') AS INTEGER) AS product_length_cm,
       CAST(NULLIF(TRIM(product_height_cm), '') AS INTEGER) AS product_height_cm,
       CAST(NULLIF(TRIM(product_width_cm), '') AS INTEGER) AS product_width_cm
FROM products;

CREATE VIEW v_clean_sellers AS
SELECT seller_id,
       NULLIF(TRIM(seller_zip_code_prefix), '') AS seller_zip_code_prefix,
       NULLIF(TRIM(seller_city), '') AS seller_city,
       UPPER(NULLIF(TRIM(seller_state), '')) AS seller_state
FROM sellers;

CREATE VIEW v_clean_order_payments AS
SELECT order_id,
       CAST(NULLIF(TRIM(payment_sequential), '') AS INTEGER) AS payment_sequential,
       LOWER(NULLIF(TRIM(payment_type), '')) AS payment_type,
       CAST(NULLIF(TRIM(payment_installments), '') AS INTEGER) AS payment_installments,
       CAST(ROUND(CAST(NULLIF(TRIM(payment_value), '') AS REAL) * 100) AS INTEGER) AS payment_value_cents
FROM order_payments;

CREATE VIEW v_clean_order_reviews AS
SELECT review_id,
       order_id,
       CAST(NULLIF(TRIM(review_score), '') AS INTEGER) AS review_score,
       NULLIF(TRIM(review_comment_title), '') AS review_comment_title,
       NULLIF(TRIM(review_comment_message), '') AS review_comment_message,
       NULLIF(TRIM(review_creation_date), '') AS review_creation_date,
       NULLIF(TRIM(review_answer_timestamp), '') AS review_answer_timestamp
FROM order_reviews;

CREATE VIEW v_clean_category_translation AS
SELECT NULLIF(TRIM(product_category_name), '') AS product_category_name,
       NULLIF(TRIM(product_category_name_english), '') AS product_category_name_english
FROM category_translation;

-- Lookup indexes match the unchanged identifiers in the clean views.
-- These are access paths, not a claim of measured performance improvement.
CREATE INDEX IF NOT EXISTS idx_p3_orders_order_id
    ON orders(order_id);
CREATE INDEX IF NOT EXISTS idx_p3_customers_customer_id
    ON customers(customer_id);
CREATE INDEX IF NOT EXISTS idx_p3_products_product_id
    ON products(product_id);
CREATE INDEX IF NOT EXISTS idx_p3_sellers_seller_id
    ON sellers(seller_id);
CREATE INDEX IF NOT EXISTS idx_p3_order_items_order_id
    ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_p3_order_payments_order_id
    ON order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_p3_order_reviews_order_id
    ON order_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_p3_category_translation_product_category_name
    ON category_translation(product_category_name);

-- 3. Keep products even when a category or English translation is missing.
CREATE VIEW v_products_labeled AS
SELECT p.*, t.product_category_name_english,
       CASE WHEN p.product_category_name IS NULL THEN 'Unknown category'
            WHEN t.product_category_name_english IS NULL
                THEN 'Untranslated: ' || p.product_category_name
            ELSE t.product_category_name_english END AS category_label,
       CASE WHEN p.product_category_name IS NULL THEN 'missing'
            WHEN t.product_category_name_english IS NULL THEN 'untranslated'
            ELSE 'translated' END AS category_status
FROM v_clean_products p
LEFT JOIN v_clean_category_translation t
    ON t.product_category_name = p.product_category_name;

-- 4. Select one valid review per order. A review ID alone is not unique here.
-- Creation is a calendar date recorded at midnight; compare it with purchase DATE.
CREATE VIEW v_review_candidates AS
SELECT r.*,
       CASE WHEN r.review_score BETWEEN 1 AND 5
                 AND DATE(r.review_creation_date) >= DATE(o.order_purchase_timestamp)
                 AND r.review_answer_timestamp >= o.order_purchase_timestamp
                 AND r.review_answer_timestamp >= r.review_creation_date
            THEN 1 ELSE 0 END AS review_is_valid
FROM v_clean_order_reviews r
LEFT JOIN v_clean_orders o ON o.order_id = r.order_id;

CREATE VIEW v_order_review AS
WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY order_id
               ORDER BY review_answer_timestamp DESC, review_creation_date DESC,
                        review_id ASC
           ) AS review_rank
    FROM v_review_candidates
    WHERE review_is_valid = 1
)
SELECT order_id, review_id, review_score,
       review_creation_date, review_answer_timestamp
FROM ranked
WHERE review_rank = 1;

-- 5. Aggregate each child table BEFORE joining. Three items and two payments
-- would otherwise create six rows and inflate both amounts.
CREATE VIEW v_order_item_totals AS
SELECT order_id, COUNT(*) AS item_count,
       COUNT(DISTINCT seller_id) AS seller_count,
       CASE WHEN COUNT(DISTINCT seller_id) = 1 THEN MIN(seller_id) END AS single_seller_id,
       SUM(price_cents) AS product_sales_cents,
       SUM(freight_value_cents) AS freight_cents
FROM v_clean_order_items
GROUP BY order_id;

CREATE VIEW v_order_payment_totals AS
SELECT order_id, COUNT(*) AS payment_count,
       SUM(payment_value_cents) AS payment_cents
FROM v_clean_order_payments
GROUP BY order_id;

-- 6. One row per order, including orders with no items, payments or valid reviews.
-- Main reporting period: 1 Feb 2017 through 31 Jul 2018, by purchase timestamp.
-- Keep boundary months in the database. Their exclusion is a reporting decision.
CREATE VIEW v_order_analysis AS
WITH joined AS (
    SELECT o.*, c.customer_unique_id, c.customer_city, c.customer_state,
           COALESCE(i.item_count, 0) AS item_count,
           COALESCE(i.seller_count, 0) AS seller_count, i.single_seller_id,
           i.product_sales_cents, i.freight_cents,
           COALESCE(p.payment_count, 0) AS payment_count, p.payment_cents,
           r.review_id, r.review_score, r.review_creation_date, r.review_answer_timestamp,
           CASE WHEN o.order_purchase_timestamp >= '2017-02-01'
                     AND o.order_purchase_timestamp < '2018-08-01'
                THEN 1 ELSE 0 END AS in_reporting_period
    FROM v_clean_orders o
    LEFT JOIN v_clean_customers c ON c.customer_id = o.customer_id
    LEFT JOIN v_order_item_totals i ON i.order_id = o.order_id
    LEFT JOIN v_order_payment_totals p ON p.order_id = o.order_id
    LEFT JOIN v_order_review r ON r.order_id = o.order_id
), eligible AS (
    SELECT *,
           CASE WHEN in_reporting_period = 1 AND order_status = 'delivered'
                     AND item_count > 0 AND product_sales_cents IS NOT NULL
                THEN 1 ELSE 0 END AS sales_eligible,
           CASE WHEN in_reporting_period = 1 AND order_status = 'delivered'
                     AND order_delivered_customer_date >= order_purchase_timestamp
                     AND DATE(order_estimated_delivery_date) >= DATE(order_purchase_timestamp)
                THEN 1 ELSE 0 END AS delivery_eligible
    FROM joined
)
SELECT *,
       CASE WHEN sales_eligible = 1 AND review_score IS NOT NULL
            THEN 1 ELSE 0 END AS review_eligible,
       CASE WHEN delivery_eligible = 1 AND seller_count = 1
            THEN 1 ELSE 0 END AS seller_delivery_eligible,
       CASE WHEN delivery_eligible = 1
            THEN CASE WHEN DATE(order_delivered_customer_date) > DATE(order_estimated_delivery_date)
                      THEN 1 ELSE 0 END END AS is_late,
       CASE WHEN delivery_eligible = 1
            THEN JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp)
            END AS delivery_days,
       CASE WHEN delivery_eligible = 1
            THEN CAST(JULIANDAY(DATE(order_delivered_customer_date))
                      - JULIANDAY(DATE(order_estimated_delivery_date)) AS INTEGER)
            END AS delay_days,
       CASE WHEN payment_count > 0 AND item_count > 0
            THEN payment_cents - product_sales_cents - freight_cents
            END AS payment_difference_cents
FROM eligible;
