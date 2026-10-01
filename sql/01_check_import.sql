-- PART 2: READ-ONLY IMPORT CHECKS (SQLite)
-- Run each numbered statement separately in the browser.

-- 1. Counts should match for all eight files; every status should be PASS.
-- Count the live tables again, rather than relying on recorded loaded counts.
SELECT
    c.table_name,
    l.source_rows,
    c.database_rows,
    c.database_rows - l.source_rows AS difference,
    l.rejected_rows,
    CASE
        WHEN l.source_rows = c.database_rows
         AND l.imported_rows = c.database_rows
         AND l.rejected_rows = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM v_import_row_counts AS c
LEFT JOIN import_log AS l ON l.table_name = c.table_name
ORDER BY c.table_name;

-- 2. Expected: 8.
SELECT COUNT(*) AS source_tables_recorded FROM import_log;

-- 3. Expected: ok.
PRAGMA integrity_check;

-- 4. Raw timestamp boundaries before eligibility filters.
-- This does not establish complete analysis months.
SELECT
    MIN(NULLIF(order_purchase_timestamp, '')) AS first_raw_purchase,
    MAX(NULLIF(order_purchase_timestamp, '')) AS last_raw_purchase
FROM orders;

-- 5. Browser engine version may differ from the recorded build version.
SELECT sqlite_version() AS current_sqlite_version;
