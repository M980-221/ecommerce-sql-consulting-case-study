# SQL scripts

Dialect: **SQLite**. Executed with SQLite **3.53.1**. Part 3 uses window functions and requires SQLite 3.25 or later.

| File | Purpose | Status |
|---|---|---|
| `00_first_queries.sql` | Raw counts, sample rows, status distribution and columns | Executed |
| `01_setup.sql` | Eight raw tables, import log and live count view | Executed |
| `01_check_import.sql` | Source/import counts, integrity and timestamp range | Executed |
| `02_profile.sql` | Profile all 47 raw fields, exact duplicates and date ranges | Executed |
| `02_cleaning.sql` | Format guards, clean views, review selection and order model | Executed |
| `02_check_cleaning.sql` | Keys, relationships, totals, eligibility and source exceptions | Executed |
| `03_sales_analysis.sql` | Monthly sales and growth, matched-period AOV, categories and buyer states | Executed |
| `04_delivery_analysis.sql` | Lateness, duration, purchase months, buyer states, categories and single-seller comparisons | Executed |
| `05_customer_analysis.sql` | Reviews, delivery comparisons, customer spending, repeat purchases and regional reviews | Executed |
| `06_validation.sql` | Business metric validation, reconciliation investigation and manual examples | Planned |
| `07_reporting_views.sql` | Verified dashboard views | Planned |

Run `python3 scripts/build_database.py` for Part 2, then `python3 scripts/prepare_part3.py` for Part 3. Setup is for an empty database; Part 3 can be rerun and leaves the source records unchanged.

For Part 4, run `python3 scripts/analyse_sales.py`. It executes five standalone queries, compares every output cell with a separate raw-record calculation and exports the results as CSV. You can also run each statement from `03_sales_analysis.sql` in a SQLite editor. See the [sales walkthrough](../docs/11_part4_sales.md) for findings and practice with JOIN and HAVING.

For Part 5, run `python3 scripts/analyse_delivery.py`. It checks the five delivery outputs against an independent calculation using raw records and Python dates. Each statement in `04_delivery_analysis.sql` also runs on its own. See the [delivery walkthrough](../docs/12_part5_delivery.md) for category joins, late-only averages and the seller report's HAVING filter.

For Part 6, run `python3 scripts/analyse_customers.py`. It checks the five customer outputs using an independent raw-record calculation, including review selection and persistent customer identity. Customer orders and value also reconcile to the published Part 4 totals. Each statement in `05_customer_analysis.sql` runs separately. See the [customer walkthrough](../docs/13_part6_customers.md) for JOIN, missing reviews and repeat-customer HAVING examples.

The Part 3 runner validates the import fingerprints, profiles the data, applies the cleaning script in a transaction, checks the resulting model and commits only on success. Its independent Decimal checks cover every price, freight and payment conversion. See [run instructions](../docs/10_part3_cleaning.md#run-it) for use in a SQL editor.

`v_clean_<table_name>` keeps the source grain. `v_order_analysis` has one row per order; use its eligibility flags for the defined metrics. Monetary fields ending in `_cents` hold integer hundredths, not display-ready currency amounts.

Useful SQL in Part 3: `SELECT`, `WHERE`, `COUNT`, `DISTINCT`, `GROUP BY`, `HAVING`, `LEFT JOIN`, `SUM`, `MIN`, `MAX`, `CASE`, `NULLIF`, `COALESCE`, `TRIM`, `CAST`, `ROUND`, `WITH`, `ROW_NUMBER`, `CREATE VIEW`, `CREATE INDEX` and SQLite date functions. The [cleaning notes](../docs/10_part3_cleaning.md#two-queries-to-practise) walk through HAVING and LEFT JOIN examples.
