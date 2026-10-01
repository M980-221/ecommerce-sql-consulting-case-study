# E-commerce Performance Review

A SQL consulting case study by Mohammed Baquaysh, using Olist's historical marketplace data to examine sales performance, delivery reliability and customer experience.

**Business question:** Where should an e-commerce manager focus first to improve sales performance, delivery reliability and customer experience?

**Current stage:** Business brief and database setup complete. Data cleaning and business analysis are next.

## Completed work

- Defined six business questions, the intended stakeholder and working metric definitions.
- Imported eight source files into SQLite, preserving all 550,759 source records and 47 source columns.
- Verified source and database row counts, decoded field values and database integrity.
- Recorded source provenance, checksums, environment versions and reproducible import instructions.

SQLite provides a portable database for this project. SQL defines the tables and inspection checks; a Python standard-library script handles CSV loading, including multiline reviews. Raw values remain TEXT until the cleaning stage establishes conversion and exclusion rules.

## Import results

| Table | Source records | Imported records | Rejected |
|---|---:|---:|---:|
| `orders` | 99,441 | 99,441 | 0 |
| `order_items` | 112,650 | 112,650 | 0 |
| `customers` | 99,441 | 99,441 | 0 |
| `products` | 32,951 | 32,951 | 0 |
| `sellers` | 3,095 | 3,095 | 0 |
| `order_payments` | 103,886 | 103,886 | 0 |
| `order_reviews` | 99,224 | 99,224 | 0 |
| `category_translation` | 71 | 71 | 0 |
| **Total** | **550,759** | **550,759** | **0** |

All eight tables matched their sources. The total is a count across tables; the dataset contains **99,441 orders**. SQLite's integrity check returned `ok`.

Evidence: [import log](results/part2_import_log.csv), [verification report](results/part2_verification.json) and [SQL check output](results/part2_validation.txt).

## Reproduce the setup

Requirements: Python 3.8 or later. The loader uses the standard library, so no additional Python packages are needed.

1. Clone this repository:

   ```bash
   git clone https://github.com/M980-221/ecommerce-sql-consulting-case-study.git
   cd ecommerce-sql-consulting-case-study
   ```

2. Download the [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Extract the eight files listed in [data/README.md](data/README.md) into `data/raw/`.

3. Build and verify the database:

   ```bash
   python3 scripts/build_database.py
   ```

4. Open the resulting `ecommerce_olist.db` in a SQLite client and run:

   ```sql
   SELECT COUNT(*) AS total_orders FROM orders;
   ```

   Expected result for the recorded dataset version: `99441`. [Sqlime](https://sqlime.org/) supports opening a local SQLite file in the browser.

The loader refuses to overwrite an existing database. For a separate rebuild:

```bash
python3 scripts/build_database.py --output ecommerce_olist_rebuilt.db --results-dir results/rebuilt
```

Source CSVs and database files are excluded from Git. The source manifest records the version and file fingerprints used for the published results. Rebuild timestamps and database hashes can differ because the database records the import time.

## Project documents

| Document | Purpose |
|---|---|
| [Business brief](docs/01_project_brief.md) | Decision, audience, questions and scope |
| [Project plan](docs/02_project_plan.md) | Ten-part delivery plan |
| [Part 2: setup and import](docs/09_part2_setup.md) | Environment, import decisions and verification |
| [Data dictionary](docs/03_data_dictionary.md) | Initial table map; cleaning-stage checks pending |
| [Metric definitions](docs/04_metric_definitions.md) | Working measures and denominators |
| [Validation log](docs/05_validation_log.md) | Completed checks and remaining validation |
| [SQL scripts](sql/README.md) | Executable setup and future analysis stages |

## Progress

- [x] Part 1: Define the business problem.
- [x] Part 2: Download data and create the database.
- [ ] Part 3: Clean, model and document the data.
- [ ] Part 4: Analyse sales performance.
- [ ] Part 5: Analyse delivery performance.
- [ ] Part 6: Analyse customer experience.
- [ ] Part 7: Validate results and improve SQL.
- [ ] Part 8: Build and review the dashboard.
- [ ] Part 9: Develop recommendations and slides.
- [ ] Part 10: Prepare the completed portfolio.

The remaining scope is approximately 15–20 business queries, three dashboard pages, three evidence-based recommendations and a five-slide presentation. Business findings will be added after cleaning and validation.

## Data attribution

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), version 2, downloaded on 1 October 2026. The dataset covers historical Brazilian marketplace activity. See [DATA_LICENSE.txt](DATA_LICENSE.txt) for the publisher's CC BY-NC-SA 4.0 licence.

This is an independent portfolio case study. Product sales value will be reported separately from company revenue or profit.
