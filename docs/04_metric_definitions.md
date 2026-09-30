# Metric definitions

Status: proposed definitions. Confirm and record the final analysis period before running queries.

| Metric | Proposed definition | Important condition |
|---|---|---|
| All orders | Distinct order_id | Show included statuses and period |
| Delivered orders | Distinct orders marked delivered | Validate completion dates; report inconsistent rows |
| Product sales value | Sum of item prices for delivered orders | Excludes freight; not company revenue or profit |
| Average order value | Product sales value / delivered order count | Use identical populations in numerator and denominator |
| Late-delivery rate | Delivered orders arriving after the promised calendar date / delivered orders with both valid dates | Report eligible and excluded counts |
| Average delay | Mean positive calendar-day delay among late deliveries | Keep distinct from average delivery duration |
| Average delivery duration | Days from purchase to delivery for eligible orders | Inspect negative or implausible durations |
| Average review score | Mean score after applying a documented review rule | Show number of matched reviewed orders and missing reviews |
| Low-score share | Orders with a selected review score of 1 or 2 / eligible reviewed orders | Use the same review-selection rule as average review score |
| Observed repeat-customer rate | Customers with at least two qualifying orders / customers with at least one qualifying order | Use customer_unique_id; specify window and qualifying statuses |
| Monthly growth | (Current complete month value - previous complete month value) / previous value | Handle zero or missing previous values explicitly |

## Financial and time boundaries

- Keep prices in their original source currency and verify its label.
- Product sales value is not Olist's commission revenue or profit.
- Analyse freight amounts separately from product value.
- Do not infer margin without product costs and a defined cost basis.
- Flag partial months and orders without sufficient follow-up.
- Delivery and review patterns are associations; a pilot would be needed to test an intervention.
- For seller comparisons based on order-level delivery dates or reviews, use a documented single-seller subset or explain attribution limits.

