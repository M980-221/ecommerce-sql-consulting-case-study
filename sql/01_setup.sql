-- PART 2: SQLITE DATABASE SETUP
-- Creates empty raw tables. scripts/build_database.py loads the CSVs.
-- Run only in a NEW database. Existing tables cause an error; nothing is dropped.
-- Raw fields stay TEXT, including empty strings and source date strings.
-- Keys, numeric types, NULL rules and relationships are assessed in Part 3.

BEGIN;

CREATE TABLE orders (
    order_id TEXT,
    customer_id TEXT,
    order_status TEXT,
    order_purchase_timestamp TEXT,
    order_approved_at TEXT,
    order_delivered_carrier_date TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT
);

CREATE TABLE order_items (
    order_id TEXT,
    order_item_id TEXT,
    product_id TEXT,
    seller_id TEXT,
    shipping_limit_date TEXT,
    price TEXT,
    freight_value TEXT
);

CREATE TABLE customers (
    customer_id TEXT,
    customer_unique_id TEXT,
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT
);

-- Preserve the source spelling of the two *_lenght columns.
CREATE TABLE products (
    product_id TEXT,
    product_category_name TEXT,
    product_name_lenght TEXT,
    product_description_lenght TEXT,
    product_photos_qty TEXT,
    product_weight_g TEXT,
    product_length_cm TEXT,
    product_height_cm TEXT,
    product_width_cm TEXT
);

CREATE TABLE sellers (
    seller_id TEXT,
    seller_zip_code_prefix TEXT,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE order_payments (
    order_id TEXT,
    payment_sequential TEXT,
    payment_type TEXT,
    payment_installments TEXT,
    payment_value TEXT
);

CREATE TABLE order_reviews (
    review_id TEXT,
    order_id TEXT,
    review_score TEXT,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TEXT,
    review_answer_timestamp TEXT
);

CREATE TABLE category_translation (
    product_category_name TEXT,
    product_category_name_english TEXT
);

-- Audit metadata, not a ninth business dataset.
CREATE TABLE import_log (
    table_name TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_rows INTEGER NOT NULL,
    imported_rows INTEGER NOT NULL,
    rejected_rows INTEGER NOT NULL,
    source_sha256 TEXT NOT NULL,
    logical_rows_sha256 TEXT NOT NULL,
    sqlite_version TEXT NOT NULL,
    imported_at_utc TEXT NOT NULL
);

CREATE VIEW v_import_row_counts AS
SELECT 'orders' AS table_name, COUNT(*) AS database_rows FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'category_translation', COUNT(*) FROM category_translation;

COMMIT;
