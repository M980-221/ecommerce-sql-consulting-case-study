# Data relationships

Part 3 relationship diagram, based on the verified source keys and joins:

![Olist table relationships](olist_relationships.svg)

- [SVG](olist_relationships.svg): editable vector diagram.
- [PNG](olist_relationships.png): image for slides or quick sharing.
- [Mermaid](olist_relationships.mmd): editable relationship definition.

The diagram shows validated keys, not primary-key constraints enforced on the raw tables. Customers are order-associated records; `customer_unique_id` connects identities across orders. Item and payment rows are aggregated before order-level reporting. See the [data dictionary](../docs/03_data_dictionary.md) for field definitions and exceptions.
