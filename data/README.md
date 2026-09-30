# Data source

Source: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Publisher: Olist. Approximately 100,000 anonymised orders from 2016–2018.

Download the source data from its official page, following its access and licence terms. Keep original files unchanged in raw/. Working copies can go in processed/. These local data folders are excluded from normal commits.

## Selected files

| Source file | Proposed database table |
|---|---|
| olist_orders_dataset.csv | orders |
| olist_order_items_dataset.csv | order_items |
| olist_customers_dataset.csv | customers |
| olist_products_dataset.csv | products |
| olist_sellers_dataset.csv | sellers |
| olist_order_payments_dataset.csv | order_payments |
| olist_order_reviews_dataset.csv | order_reviews |
| product_category_name_translation.csv | category_translation |

The first version uses customer/seller state and city fields; detailed geolocation data is outside its scope.

## Import log to complete

Record the download date, dataset version, source filenames, row counts, database system/version, file encoding, import command or steps, and any rejected records.

No source data has been downloaded or analysed in this starter.

