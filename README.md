# E-commerce Performance Review

A SQL consulting case study by Mohammed Baquaysh, using Olist's historical marketplace data to examine sales performance, delivery reliability and customer experience.

**Business question:** Where should an e-commerce manager focus first to improve sales performance, delivery reliability and customer experience?

**Current stage:** Parts 1–5 complete, including sales and delivery analysis. Customer experience is next.

## Sales findings

The February 2017–July 2018 reporting window contains **89,110 qualifying delivered orders** and **12,230,652.13 in product sales value**, with an average order value of **137.25**. Amounts use source monetary units and exclude freight.

- Comparing February–July in both years, product sales value increased **134.42%**, orders increased **130.80%**, and average order value increased **1.57%**. Most of the observed increase came from order volume.
- Health and beauty was the largest category by product sales value (**8.98%**). The ten largest categories accounted for **62.49%**.
- Buyers in São Paulo state accounted for **37.84%** of product sales value. This measures where existing sales came from, not the size of the untapped market.

Read the [sales analysis and SQL walkthrough](docs/11_part4_sales.md), or open the [monthly results](results/part4_monthly_sales.csv) and [equal-period comparison](results/part4_comparable_periods.csv). These are descriptive findings from a historical snapshot; the data does not establish what caused the growth.

## Delivery findings

Of **89,102 eligible delivered orders**, **6,116 arrived late (6.86%)**. Average delivery duration was **12.88 days**. Among the late orders, the average delay was **10.98 calendar days** beyond the promised date.

- March 2018 purchases had the highest observed late rate: **18.96%**, or **1,328 of 7,003** eligible orders.
- São Paulo had more late orders (**1,524**) than Rio de Janeiro (**1,450**), but Rio de Janeiro's late rate was higher: **12.61% versus 4.12%**. Counts show the number of affected orders; rates show how common lateness was within each state.
- The seller investigation table includes **190 sellers** with at least 100 eligible single-seller orders each. It covers **52,408 orders (58.82%)** of the delivery population. The results do not establish who caused a delay.

The analysis excludes 2,670 non-delivered period orders and eight delivered orders with missing actual-delivery dates. See the [delivery findings and SQL walkthrough](docs/12_part5_delivery.md) for the definitions, coverage and runnable examples.

## Completed work

- Defined six business questions, the intended stakeholder and working metric definitions.
- Imported eight source files into SQLite, preserving all 550,759 source records and 47 source columns.
- Verified source and database row counts, decoded field values and database integrity.
- Recorded source provenance, checksums, environment versions and reproducible import instructions.
- Profiled all 47 source fields and built cleaned views with a model containing exactly one row per order.
- Documented review selection, missing-data rules and the February 2017–July 2018 reporting window.
- Passed 62 Part 3 checks and 14 automated tests; order-join totals match the source.
- Completed five sales queries and exported their results. All 139 result rows match a separate calculation from raw records; 15 Part 4 checks and 10 sales test cases passed.
- Completed five delivery queries covering overall outcomes, purchase months, buyer states, categories and single-seller orders. All 310 result rows match independent raw-record calculations; 25 checks and 12 delivery test cases passed.

SQLite provides a portable database for this project. SQL defines the tables and inspection checks; a Python standard-library script handles CSV loading, including multiline reviews. Raw values remain TEXT. Part 3 views provide validated numeric values, NULL handling and metric-specific eligibility rules.

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
   python3 scripts/prepare_part3.py
   python3 scripts/analyse_sales.py
   python3 scripts/analyse_delivery.py
   ```

4. Open the resulting `ecommerce_olist.db` in a SQLite client and run:

   ```sql
   SELECT COUNT(*) AS total_orders FROM orders;
   ```

   Expected result for the recorded dataset version: `99441`. After Part 3, `SELECT COUNT(*) FROM v_order_analysis;` also returns `99441`. [Sqlime](https://sqlime.org/) supports opening a local SQLite file in the browser.

The loader refuses to overwrite an existing database. For a separate rebuild:

```bash
python3 scripts/build_database.py --output ecommerce_olist_rebuilt.db --results-dir results/rebuilt
```

Source CSVs and database files are excluded from Git. The source manifest records the version and file fingerprints used for the published results. Rebuild timestamps and database hashes can differ because the database records the import time.

## Part 3 outcome

The clean order model keeps all **99,441 orders** and combines customer details, item totals, payment totals and one valid review. The main comparison window contains **89,110 sales-eligible orders**. Missing delivery dates exclude eight of those from delivery measures.

Source exceptions are visible: 610 products have no category, 13 lack an English mapping, and 303 orders with items and payments differ by more than one cent. The original records remain unchanged.

![Data relationships](assets/olist_relationships.svg)

## Project documents

| Document | Purpose |
|---|---|
| [Business brief](docs/01_project_brief.md) | Decision, audience, questions and scope |
| [Project plan](docs/02_project_plan.md) | Ten-part delivery plan |
| [Part 2: setup and import](docs/09_part2_setup.md) | Environment, import decisions and verification |
| [Part 3: cleaning and model](docs/10_part3_cleaning.md) | Decisions, reproduction commands, checks and practice queries |
| [Part 4: sales analysis](docs/11_part4_sales.md) | Findings, five output tables and SQL practice |
| [Part 5: delivery analysis](docs/12_part5_delivery.md) | Lateness, delivery time, comparison groups and SQL practice |
| [Data dictionary](docs/03_data_dictionary.md) | All 47 fields, verified keys, derived views and relationship diagram |
| [Metric definitions](docs/04_metric_definitions.md) | Implemented reporting period, eligibility flags and denominators |
| [Validation log](docs/05_validation_log.md) | Completed checks and remaining validation |
| [SQL scripts](sql/README.md) | Executable setup and future analysis stages |

## Progress

- [x] Part 1: Define the business problem.
- [x] Part 2: Download data and create the database.
- [x] Part 3: Clean, model and document the data.
- [x] Part 4: Analyse sales performance.
- [x] Part 5: Analyse delivery performance.
- [ ] Part 6: Analyse customer experience.
- [ ] Part 7: Validate results and improve SQL.
- [ ] Part 8: Build and review the dashboard.
- [ ] Part 9: Develop recommendations and slides.
- [ ] Part 10: Prepare the completed portfolio.

Ten business queries are complete. Customer analysis comes next, followed by further validation, three dashboard pages, three recommendations and a five-slide presentation. Known source exceptions remain recorded in the Part 3 cleaning notes.

## Data attribution

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), version 2, downloaded on 1 October 2026. The dataset covers historical Brazilian marketplace activity. See [DATA_LICENSE.txt](DATA_LICENSE.txt) for the publisher's CC BY-NC-SA 4.0 licence.

This is an independent portfolio case study. Product sales value is reported separately from company revenue or profit.
