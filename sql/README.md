# SQL scripts

Dialect: **SQLite**. The completed setup was executed with SQLite **3.53.1**.

| File | Purpose | Status |
|---|---|---|
| `00_first_queries.sql` | Raw record counts, sample rows, status distribution and columns | Executed |
| `01_setup.sql` | Eight source tables, audit table and live count view | Executed |
| `01_check_import.sql` | Live count comparison, integrity and timestamp range | Executed |
| `02_cleaning.sql` | Cleaning rules and curated data | Planned |
| `03_sales_analysis.sql` | Sales questions | Planned |
| `04_delivery_analysis.sql` | Delivery questions | Planned |
| `05_customer_analysis.sql` | Customer questions | Planned |
| `06_validation.sql` | Business metric validation and reconciliation | Planned |
| `07_reporting_views.sql` | Verified dashboard views | Planned |

Build the database with `python3 scripts/build_database.py`. The loader executes `01_setup.sql`, imports the CSVs and runs the inspection checks. The setup file is for an empty database and does not replace existing tables.

Once the database is open, statements from `00_first_queries.sql` and `01_check_import.sql` can be run individually in any compatible SQLite client. The remaining files contain planned tasks and are not completed analysis scripts.

All source fields are currently TEXT. Future analysis will use documented type conversions, eligibility rules and output grains. Items, payments and selected reviews must be aggregated appropriately before combining order-level measures.
