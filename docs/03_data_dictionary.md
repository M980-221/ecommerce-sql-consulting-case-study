# Data dictionary and relationships

Status: initial map based on the published dataset. Verify types, counts, uniqueness and missingness after import.

| Table | Intended row meaning | Key or relationship to verify |
|---|---|---|
| orders | One order | order_id; joins customers through customer_id |
| order_items | One item within an order | order_id + order_item_id; links products and sellers |
| customers | Customer record associated with an order | customer_id joins orders; customer_unique_id identifies the person across orders |
| products | One product | product_id; category maps to translation table |
| sellers | One seller | seller_id |
| order_payments | One payment component of an order | order_id + payment_sequential; multiple rows may belong to one order |
| order_reviews | Review records associated with orders | Inspect duplicates and multiple reviews before selecting a rule |
| category_translation | Category name and English label | Verify uniqueness before joining product_category_name |

## Important fields to document

- Orders: order_id, customer_id, order_status, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date.
- Items: order_id, order_item_id, product_id, seller_id, price, freight_value.
- Customers: customer_id, customer_unique_id, customer_city, customer_state.
- Reviews: review_id, order_id, review_score and review timestamps.

## Complete after import

Record column name, source type, database type, business meaning, nullability, key role, source count and cleaning rule.

## Join design

Create order-level aggregates for items and payments before combining order-level measures. Review records also need an explicit order-level selection or aggregation rule. Do not assume that an order has just one item, payment, seller or review.

Save the completed database relationship diagram in assets/ and link it here.

