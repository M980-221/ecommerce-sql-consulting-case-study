# Data dictionary and relationships

Part 3 completed on 6 October 2026. The eight raw tables contain 550,759 rows and 47 source columns. Every raw field remains TEXT. The views below provide cleaned values without editing the source records.

![Olist relationship diagram](../assets/olist_relationships.svg)

[PNG](../assets/olist_relationships.png) · [Editable SVG](../assets/olist_relationships.svg) · [Mermaid source](../assets/olist_relationships.mmd)

## Row meanings and keys

The keys in this table were checked for missingness and duplication. They describe the data; the raw tables do not declare primary or foreign-key constraints. The runner refuses to publish a model when a required key or core relationship check fails.

| Raw table | Rows | One row represents | Verified key |
|---|---:|---|---|
| `orders` | 99,441 | One order | `order_id` |
| `order_items` | 112,650 | One item within an order | `order_id + order_item_id` |
| `customers` | 99,441 | One customer record associated with an order | `customer_id` |
| `products` | 32,951 | One product | `product_id` |
| `sellers` | 3,095 | One seller | `seller_id` |
| `order_payments` | 103,886 | One payment component | `order_id + payment_sequential` |
| `order_reviews` | 99,224 | One review record associated with an order | `order_id + review_id` |
| `category_translation` | 71 | One category-to-English mapping | `product_category_name` |

There are 99,441 distinct `customer_id` values and 96,096 distinct `customer_unique_id` values. The customer-record-to-order link is 1:1 in this snapshot. A repeat customer has different customer records with the same persistent identity.

`review_id` alone repeats across orders: 789 IDs occur on multiple orders. The composite key is unique. Repeated `order_id` values in items, payments and reviews are expected; they do not by themselves identify duplicate records.

All six core foreign-key checks have zero unmatched rows. Category mapping is optional: 610 products lack a category and 13 products have a category absent from the translation table.

## Column definitions

Each raw table maps to `v_clean_<table_name>`. Missing counts below include NULL and text that becomes empty after trimming ordinary outer spaces. Non-key text uses `NULLIF(TRIM(value), '')`. Required string identifiers are checked for blanks and outer spaces, then retained unchanged. ZIP prefixes remain TEXT.

Timestamps remain validated `YYYY-MM-DD HH:MM:SS` text, which SQLite's date functions can read. Integer and monetary strings are checked before conversion. The `_cents` suffix means hundredths of the source monetary unit; it does not establish a currency code.

### `orders` → `v_clean_orders`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `order_id` | `order_id` / TEXT | 0 | Order identifier; links the order and its child records. |
| `customer_id` | `customer_id` / TEXT | 0 | Customer record for this order; join orders to customers with this field. |
| `order_status` | `order_status` / TEXT | 0 | Recorded order status. Lowercase; only delivered qualifies for the main measures. |
| `order_purchase_timestamp` | `order_purchase_timestamp` / TEXT | 0 | Purchase timestamp; assigns the order to the reporting period. |
| `order_approved_at` | `order_approved_at` / TEXT | 160 | Approval timestamp. Missing values remain unknown. |
| `order_delivered_carrier_date` | `order_delivered_carrier_date` / TEXT | 1,783 | Recorded handover to carrier. Chronology exceptions are flagged. |
| `order_delivered_customer_date` | `order_delivered_customer_date` / TEXT | 2,965 | Actual delivery timestamp; required for delivery measures. |
| `order_estimated_delivery_date` | `order_estimated_delivery_date` / TEXT | 0 | Promised delivery date, stored at midnight. Compare calendar dates for lateness. |

### `order_items` → `v_clean_order_items`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `order_id` | `order_id` / TEXT | 0 | Order identifier; links the order and its child records. |
| `order_item_id` | `order_item_id` / INTEGER | 0 | Item sequence within the order; not a product ID. Convert to INTEGER. |
| `product_id` | `product_id` / TEXT | 0 | Product identifier; links items to products. |
| `seller_id` | `seller_id` / TEXT | 0 | Seller identifier; links items to sellers. |
| `shipping_limit_date` | `shipping_limit_date` / TEXT | 0 | Seller shipping deadline. Four 2020 values are flagged; unused in headline metrics. |
| `price` | `price_cents` / INTEGER | 0 | Item product value; validate, multiply by 100 and round to integer hundredths. |
| `freight_value` | `freight_value_cents` / INTEGER | 0 | Freight assigned to the item; same hundredths conversion, separate from product value. |

### `customers` → `v_clean_customers`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `customer_id` | `customer_id` / TEXT | 0 | Customer record for this order; join orders to customers with this field. |
| `customer_unique_id` | `customer_unique_id` / TEXT | 0 | Persistent customer identity across orders; use for repeat-customer calculations. |
| `customer_zip_code_prefix` | `customer_zip_code_prefix` / TEXT | 0 | Postal prefix; retain as TEXT so leading zeros are not lost. |
| `customer_city` | `customer_city` / TEXT | 0 | Customer city label. Trim outer spaces; no spelling or accent mapping. |
| `customer_state` | `customer_state` / TEXT | 0 | Customer state abbreviation; trim and uppercase. |

### `products` → `v_clean_products`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `product_id` | `product_id` / TEXT | 0 | Product identifier; links items to products. |
| `product_category_name` | `product_category_name` / TEXT | 610 | Portuguese category key. Blank becomes NULL; missing translations stay identifiable. |
| `product_name_lenght` | `product_name_lenght` / INTEGER | 610 | Product name length. Preserve the source column spelling; INTEGER or NULL. |
| `product_description_lenght` | `product_description_lenght` / INTEGER | 610 | Description length. Preserve the source column spelling; INTEGER or NULL. |
| `product_photos_qty` | `product_photos_qty` / INTEGER | 610 | Number of product photos; INTEGER or NULL. |
| `product_weight_g` | `product_weight_g` / INTEGER | 2 | Product weight in grams. Missing stays NULL; four zero values remain flagged. |
| `product_length_cm` | `product_length_cm` / INTEGER | 2 | Product length in centimetres; INTEGER or NULL. |
| `product_height_cm` | `product_height_cm` / INTEGER | 2 | Product height in centimetres; INTEGER or NULL. |
| `product_width_cm` | `product_width_cm` / INTEGER | 2 | Product width in centimetres; INTEGER or NULL. |

### `sellers` → `v_clean_sellers`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `seller_id` | `seller_id` / TEXT | 0 | Seller identifier; links items to sellers. |
| `seller_zip_code_prefix` | `seller_zip_code_prefix` / TEXT | 0 | Seller postal prefix; retain as TEXT. |
| `seller_city` | `seller_city` / TEXT | 0 | Seller city label. Trim outer spaces; no spelling or accent mapping. |
| `seller_state` | `seller_state` / TEXT | 0 | Seller state abbreviation; trim and uppercase. |

### `order_payments` → `v_clean_order_payments`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `order_id` | `order_id` / TEXT | 0 | Order identifier; links the order and its child records. |
| `payment_sequential` | `payment_sequential` / INTEGER | 0 | Payment sequence within the order; INTEGER. An order can have several components. |
| `payment_type` | `payment_type` / TEXT | 0 | Payment method; lowercase. Keep and flag not_defined. |
| `payment_installments` | `payment_installments` / INTEGER | 0 | Recorded installment count; INTEGER. Keep and flag zero, rather than inventing a value. |
| `payment_value` | `payment_value_cents` / INTEGER | 0 | Value of this payment component; convert to integer hundredths. |

### `order_reviews` → `v_clean_order_reviews`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `review_id` | `review_id` / TEXT | 0 | Review identifier; only unique here when combined with order_id. |
| `order_id` | `order_id` / TEXT | 0 | Order identifier; links the order and its child records. |
| `review_score` | `review_score` / INTEGER | 0 | Rating from 1 to 5; INTEGER. Invalid scores are ineligible for selection. |
| `review_comment_title` | `review_comment_title` / TEXT | 87,658 | Optional review title. Trim outer spaces; empty text becomes NULL. |
| `review_comment_message` | `review_comment_message` / TEXT | 58,256 | Optional review text. Trim outer spaces; preserve internal text and line breaks. |
| `review_creation_date` | `review_creation_date` / TEXT | 0 | Review creation day recorded at midnight; compare with the purchase calendar day. |
| `review_answer_timestamp` | `review_answer_timestamp` / TEXT | 0 | Response timestamp. Used to select the latest valid review for an order. |

### `category_translation` → `v_clean_category_translation`

| Source field (TEXT) | Clean field / type | Missing source rows | Meaning and rule |
|---|---|---:|---|
| `product_category_name` | `product_category_name` / TEXT | 0 | Unique nonblank Portuguese category key for the English mapping. |
| `product_category_name_english` | `product_category_name_english` / TEXT | 0 | Publisher-supplied English category label; no invented translations. |

## Derived views

| View | Grain | Purpose |
|---|---|---|
| `v_p3_numeric_issues`, `v_p3_date_issues` | One invalid source cell | Explain format failures before conversion; both are empty in this snapshot |
| `v_products_labeled` | One product | Attach English category labels with a LEFT JOIN; preserve missing and untranslated categories |
| `v_review_candidates` | One source review | Flag eligibility using score and chronology |
| `v_order_review` | At most one valid review per order | Latest response, then creation timestamp, then review ID ascending |
| `v_order_item_totals` | One order with items | Item count, seller count, single seller ID, product value and freight |
| `v_order_payment_totals` | One order with payments | Payment-component count and total amount |
| `v_order_analysis` | Exactly one row per source order | Combine customer identity, item totals, payment totals and the selected review; apply reporting flags |
| `v_reporting_orders` | One row per purchase-window order: 91,780 rows | Includes excluded orders; filter the eligibility flag required by each measure |
| `v_reporting_sales_items` | One row per eligible `(order_id, order_item_id)`: 101,825 rows | Add item prices; count distinct orders; no repeated order total |
| `v_reporting_order_categories` | One row per delivery-eligible `(order_id, category_label)`: 89,822 rows | Category delivery membership; orders can overlap across categories |
| `v_reporting_customers` | One row per persistent customer with an eligible sale: 86,271 rows | Full-window counts, spending and review totals, plus repeat flag; no top-20 limit |

The Part 7 reporting views are defined in [reporting SQL](../sql/07_reporting_views.sql). They retain the Part 3 metric rules. Customer totals cover the entire reporting window; narrower dashboard filters require regrouping the eligible orders. Counts of orders across different category rows are not additive.

### Fields added to the order model

| Fields | Meaning |
|---|---|
| `customer_unique_id`, `customer_city`, `customer_state` | Customer identity and location from the matching record |
| `item_count`, `seller_count`, `single_seller_id` | Items, distinct sellers and the seller ID only when exactly one seller supplies the order |
| `product_sales_cents`, `freight_cents` | Sum of item prices and freight separately; NULL when the order has no items |
| `payment_count`, `payment_cents` | Component count and payment total; missing payment total stays NULL |
| `review_id`, `review_score`, `review_creation_date`, `review_answer_timestamp` | Selected valid review; NULL when none qualifies |
| `in_reporting_period` | Purchase timestamp is at least 2017-02-01 and before 2018-08-01 |
| `sales_eligible`, `delivery_eligible`, `review_eligible`, `seller_delivery_eligible` | 0/1 flags implementing the metric populations |
| `is_late` | 1 if the actual delivery calendar day is after the promised day; 0 if on time; NULL if ineligible |
| `delivery_days` | Fractional elapsed days from purchase to actual delivery, for eligible delivery orders |
| `delay_days` | Actual calendar day minus promised day; negative is early, positive is late; NULL if ineligible |
| `payment_difference_cents` | Payment total minus item value and freight, when both sides exist |

Use the [metric definitions](04_metric_definitions.md) for the exact populations and [cleaning notes](10_part3_cleaning.md) for the decisions. Field-level evidence is in [part3_profile.json](../results/part3_profile.json).
