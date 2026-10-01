-- PART 2: SOURCE INSPECTION (SQLite)
-- Execute after building ecommerce_olist.db.
-- These queries inspect the raw import before cleaning and business analysis.

-- 1. Count imported orders. Expected for the recorded source version: 99441.
SELECT COUNT(*) AS total_orders FROM orders;

-- 2. Inspect the ten earliest purchase records.
SELECT order_id, order_status, order_purchase_timestamp
FROM orders
ORDER BY order_purchase_timestamp, order_id
LIMIT 10;

-- 3. List the eight source tables and row counts.
SELECT table_name, database_rows
FROM v_import_row_counts
ORDER BY table_name;

-- 4. Inspect the raw order-status distribution.
SELECT order_status, COUNT(*) AS number_of_orders
FROM orders
GROUP BY order_status
ORDER BY number_of_orders DESC, order_status;

-- 5. Inspect the orders table's columns and storage types.
PRAGMA table_info(orders);

-- All raw fields are TEXT. Type conversion and date rules are defined in Part 3.
