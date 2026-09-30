# Ten-part project plan

Estimated effort: 40–60 hours after learning SQL fundamentals. Aim for 10–15 hours per week.

| Week | Parts | Main outcome |
|---|---|---|
| 1 | 1–3 | Business brief, working database and documented data |
| 2 | 4–6 | Sales, delivery and customer analysis |
| 3 | 7–8 | Verified results and dashboard |
| 4 | 9–10 | Recommendations, public portfolio and interview preparation |

## Part 1 — Define the business problem

Review the project brief and agree on the questions, metrics and exclusions.

**GitHub deliverable:** docs/01_project_brief.md.  
**Done when:** the intended decision and project boundaries are clear.

## Part 2 — Download data and create the database

Choose the same SQL database used for course practice. Record its version, create the database and import the eight selected files. Record source row counts.

**GitHub deliverables:** data/README.md and sql/01_setup.sql.  
**Done when:** all selected files are loaded and counts match the sources.

## Part 3 — Understand, clean and organise the data

Inspect keys, missing values, duplicate records, dates and relationships. Document cleaning rules. Build a relationship diagram and finalise metric definitions.

**GitHub deliverables:** sql/02_cleaning.sql, docs/03_data_dictionary.md, docs/04_metric_definitions.md and a diagram in assets/.  
**Done when:** each table's grain and join relationships are understood.

## Part 4 — Analyse sales performance

Write about five queries covering product sales value, orders, average order value, category contribution and regional performance. Compare complete periods.

**GitHub deliverable:** sql/03_sales_analysis.sql with documented output tables.  
**Done when:** each query answers a stated business question.

## Part 5 — Analyse delivery performance

Write about five queries for delivery times, lateness, regional differences and seller investigation priorities. Use eligible delivered orders and report exclusions. For seller attribution, define a single-seller-order subset.

**GitHub deliverable:** sql/04_delivery_analysis.sql.  
**Done when:** results include denominators and show association without claiming causation.

## Part 6 — Analyse customer experience

Write about five queries comparing review scores, customer spending and observed repeat purchases. Use customer_unique_id and a documented review-selection rule.

**GitHub deliverable:** sql/05_customer_analysis.sql.  
**Done when:** repeat-customer and review metrics use the correct grain.

## Part 7 — Validate and improve SQL

Check join duplication, financial reconciliation, missingness and selected manual examples. Investigate one slow query and document any measured optimisation.

**GitHub deliverables:** sql/06_validation.sql, sql/07_reporting_views.sql and docs/05_validation_log.md.  
**Done when:** all critical checks pass or exceptions are explained.

## Part 8 — Build the dashboard

Create three pages: sales, delivery and customer experience. Check every headline number against the SQL outputs. Export screenshots for people viewing GitHub.

**GitHub deliverables:** dashboard source file, dashboard/README.md and dashboard/screenshots/.  
**Done when:** another person can understand the views and definitions.

## Part 9 — Develop recommendations

Choose three important findings. For each, state the evidence, recommended action, proposed owner, success measure and limitation. Prepare five slides.

**GitHub deliverables:** docs/06_findings_recommendations.md and presentation files.  
**Done when:** every recommendation is traceable to validated results.

## Part 10 — Prepare the public portfolio

Update the main README with the actual tools, reproduction steps, findings and screenshots. Practise explaining the project in three minutes. Review the finished repository before presenting it to employers.

**GitHub deliverables:** final README, interview notes and release version.  
**Done when:** repository links work, files are organised and completion claims match the work.

## Suggested commits

1. Add project brief and four-week plan
2. Add database schema and import instructions
3. Add cleaning rules and metric definitions
4. Add sales analysis
5. Add delivery and customer analysis
6. Validate query results and add reporting views
7. Add dashboard source and previews
8. Add recommendations and presentation
9. Finalise portfolio documentation

