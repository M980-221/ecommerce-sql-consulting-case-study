# Dashboard

Status: not built.

Part 7 supplies four checked SQLite views: `v_reporting_orders`, `v_reporting_sales_items`, `v_reporting_order_categories` and `v_reporting_customers`. Their grains and filters are documented in [Part 7](../docs/14_part7_validation.md). Use metric eligibility flags for order measures. The customer view covers the full reporting window; narrower date/state filters require regrouping eligible orders before calculating repeat customers.

Create three pages: Sales Performance, Delivery Performance and Customer Experience.

Save the editable dashboard source here when completed. Export readable screenshots into screenshots/ and link the best preview from the main README. Include the analysis period, metric definitions and a short guide to filters.

Validate all headline figures against the SQL outputs. Record any measures implemented in Power BI so calculations are reproducible.

If the editable file exceeds GitHub's size limits, follow docs/08_github_setup.md. Screenshots let visitors inspect the results without opening the source file.

