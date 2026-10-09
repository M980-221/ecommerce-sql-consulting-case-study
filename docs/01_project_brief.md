# Part 1 — Business brief

**Working title:** E-commerce Performance Review: A SQL Consulting Case Study  
**Type:** Independent portfolio project using public historical data  
**Owner:** Mohammed Baquaysh  
**Date:** 30 September 2026  
**Status:** Parts 1–8 implemented. The three dashboard pages were added on 10 October 2026, using the validated reporting views. Calculations are checked against SQL; browser visual testing remains outstanding. Recommendations and slides are next.

## Business situation

An online marketplace brings customers and sellers together. Its managers need to understand where sales come from, where deliveries fall short, and how customer experience differs across orders.

For this case study, a hypothetical management team has limited time and resources and wants three priorities for investigation or improvement. This is a decision-making scenario, not evidence that Olist has these problems today or has commissioned this work. We will not assume that sales are declining or delivery service is poor before analysing the data.

## Objective

Identify three evidence-based priorities for marketplace sales performance, delivery reliability and customer experience.

**Main question:** Where should an e-commerce manager focus first to improve sales performance, delivery reliability and customer experience?

Each recommendation must include the supporting evidence, a proposed action, a responsible business function, a success measure and a limitation.

## Stakeholder

The intended reader is an e-commerce operations or commercial manager. The final explanation should be understandable without reading the SQL. No client relationship is claimed.

## Questions

| Business question | Planned evidence | Decision it can inform |
|---|---|---|
| How do sales change across complete months? | Delivered orders, product sales value, average order value and growth | Which periods need further commercial investigation? |
| Which product categories and customer states contribute most to sales? | Sales contribution and order counts | Where should managers investigate demand and service capacity first? |
| Where are late deliveries concentrated? | Late-order counts, rates and delay severity by customer state | Which delivery issues deserve operational attention? |
| Which sellers warrant further investigation? | Delivery performance for single-seller orders, with sample sizes | Which seller relationships should operations review? |
| How do review scores differ between late and on-time deliveries? | Average score, low-score share and reviewed-order counts | Is delivery reliability a plausible priority for a customer-experience pilot? |
| How often do identifiable customers purchase again? | Repeat-customer counts and rates in the observation window | What further retention analysis or customer research is justified? |

Around 15–20 useful SQL queries will answer these six questions. Query count is a scope guide, not a target to inflate.

## Scope

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

Use orders, order items, customers, products, sellers, payments, reviews and category translations. Payments support validation and reconciliation; they are not an extra copy of item sales.

Produce SQL setup, cleaning, analysis, validation and reporting views; a data dictionary and relationship diagram; three dashboard pages (sales, delivery, customer experience); three recommendations; and a five-slide presentation. The slides cover the business problem, sales, delivery, customer experience and recommendations.

Use the historical period actually present in the data. Identify incomplete months and delivery follow-up before comparisons. Keep product sales value separate from company revenue or profit.

The geography is the Brazilian marketplace in this dataset. Findings will not be presented as evidence about Saudi customers.

**Outside this version:** machine learning, forecasting, a live application, detailed geolocation, advertising attribution, profit calculations and production deployment. These would make the one-month project unnecessarily large or require data not established as available.

## Working measurement rules

Part 3 implements the detailed [metric definitions](04_metric_definitions.md), including a February 2017–July 2018 purchase window and separate sales, delivery and review populations. The table below summarises the business measures.

| Measure | Working definition |
|---|---|
| Product sales value | Sum of item prices for qualifying delivered orders, excluding freight; not company revenue or profit |
| Delivered orders | Distinct qualifying delivered order IDs, with exclusions reported |
| Average order value | Product sales value divided by the same population of delivered orders |
| Late-delivery rate | Orders arriving after the promised calendar date divided by delivered orders with valid actual and promised dates |
| Delay severity | Positive calendar-day delay among late orders, accompanied by the number of affected orders |
| Average review score | Mean valid score after one documented review-selection rule per order |
| Low-score share | Orders with a selected review score of 1 or 2 divided by eligible reviewed orders |
| Observed repeat-customer rate | Customers with at least two qualifying delivered orders divided by customers with at least one, using customer_unique_id within the stated window |

Report the period, eligible sample size and important exclusions. Compare complete periods and disclose unequal time available for customers to purchase again.

Aggregate item, payment and review records to the required level before combining them, so joins do not multiply sales or order counts. Attribute order-level delivery and review measures to sellers only in the single-seller-order subset, and state its coverage.

Lateness and review scores may be associated; this does not establish causation. Historical repeat purchasing is not a complete lifetime-retention measure.

## Completion criteria

- Scripts and import instructions let another person reproduce the analysis.
- Metric definitions and exclusions are documented.
- Query outputs pass the validation checks.
- Dashboard figures match the SQL results.
- Recommendations cite the queries and figures supporting them.
- The final presentation states limitations and proposed next steps.

Prioritise recommendations using the number of affected orders or customers, size of the observed problem, confidence in the evidence and feasibility of action. Flag small groups rather than ranking them as reliable findings. Do not claim achieved sales growth or delivery improvements because no intervention has been implemented.

## Time and next step

Target: four weeks, approximately 40–60 hours after learning SQL fundamentals.

- Week 1: business brief, data import, inspection and documentation.
- Week 2: sales, delivery and customer SQL analysis.
- Week 3: validation and dashboard.
- Week 4: recommendations, presentation and portfolio.

**Part 1 outcome:** the decision, audience, questions, boundaries and completion criteria are defined.

**Part 2 outcome:** SQLite selected; eight source files imported and verified. See [database setup and import](09_part2_setup.md) for the environment, source counts and evidence.

**Part 3 outcome:** cleaned views and a verified order model are complete, with documented exceptions, relationships and metric rules. See [Part 3 cleaning notes](10_part3_cleaning.md).

**Part 4 outcome:** five sales queries are complete, with checked outputs for monthly performance, growth, matched-period AOV, categories and buyer states. See [sales findings](11_part4_sales.md).

**Part 5 outcome:** five delivery queries are complete, with defined exclusions, category counting rules and single-seller coverage. See [delivery findings](12_part5_delivery.md).

**Part 6 outcome:** five customer queries are complete, with review coverage, delivery comparisons, persistent customer spending and observed repeat purchases. See [customer findings](13_part6_customers.md).

**Part 7 outcome:** payment differences investigated, five orders traced, four reporting views checked against the published analysis, and one indexed lookup measured. The source does not establish the business causes of the payment differences. See [validation and SQL review](14_part7_validation.md).

**Part 8 outcome:** a browser dashboard with Sales, Delivery and Customer pages, month/state filters and CSV downloads. The calculation code is compared with SQLite under different selections. Static previews are labelled as such; live browser visual and manual accessibility checks remain open. See [the dashboard walkthrough](15_part8_dashboard.md).

**Next step:** select three evidence-based recommendations and prepare five slides in Part 9.
