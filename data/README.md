# Data source and import

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

Version used: **2**. Downloaded: **1 October 2026**.

Licence: **CC BY-NC-SA 4.0**; see [DATA_LICENSE.txt](../DATA_LICENSE.txt).

## Required files

Download the dataset from its official page and extract these files into `data/raw/`. Raw data is not committed to this repository.

| CSV filename | SQLite table | Source records |
|---|---|---:|
| `product_category_name_translation.csv` | `category_translation` | 71 |
| `olist_customers_dataset.csv` | `customers` | 99,441 |
| `olist_order_items_dataset.csv` | `order_items` | 112,650 |
| `olist_order_payments_dataset.csv` | `order_payments` | 103,886 |
| `olist_order_reviews_dataset.csv` | `order_reviews` | 99,224 |
| `olist_orders_dataset.csv` | `orders` | 99,441 |
| `olist_products_dataset.csv` | `products` | 32,951 |
| `olist_sellers_dataset.csv` | `sellers` | 3,095 |

Detailed geolocation is outside the project scope. Keep downloaded files unchanged. The [source manifest](source_manifest.json) identifies the exact source snapshot using SHA-256 hashes.

## Build

From the repository root:

```bash
python3 scripts/build_database.py
```

The standard-library loader requires Python 3.8 or later. It creates `ecommerce_olist.db`, loads all eight files and saves verification evidence in `results/`. Use `--raw-dir PATH` for a different source folder. If a database already exists, choose a new `--output` path.

## Import rules and results

All 550,759 records and 47 source columns were preserved. Every source field is stored as TEXT; blank fields remain empty strings. The CSV parser preserves quoted commas, accents and multiline reviews. No records were rejected or removed.

Record counts and decoded-value digests matched for every table. Database integrity returned `ok`. See the [Part 2 record](../docs/09_part2_setup.md), [import log](../results/part2_import_log.csv) and [verification report](../results/part2_verification.json).

Column types, missing-value treatment, key constraints and cleaning rules are finalised in Part 3.
