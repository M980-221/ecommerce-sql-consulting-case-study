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

Completed 1 October 2026. SQLite was selected as the project database. All eight selected source files were imported, with matching record counts and decoded field values. Environment details, import rules and evidence are recorded in [Part 2 setup](09_part2_setup.md).

**GitHub deliverables:** data/README.md, sql/01_setup.sql, sql/01_check_import.sql, scripts/build_database.py and the Part 2 verification outputs in results/.
**Done when:** all selected files are loaded and counts match the sources.

## Part 3 — Understand, clean and organise the data

Completed 6 October 2026. Profiled all 47 fields, verified keys and relationships, documented source exceptions, built cleaned views and an order model, and fixed the metric populations. Full-data validation passed 62 checks; 14 small automated tests also passed. See [Part 3 cleaning notes](10_part3_cleaning.md).

**GitHub deliverables:** sql/02_profile.sql, sql/02_cleaning.sql, sql/02_check_cleaning.sql, scripts/prepare_part3.py, tests/test_part3.py, docs/03_data_dictionary.md, docs/04_metric_definitions.md, docs/10_part3_cleaning.md, the relationship diagram in assets/ and Part 3 evidence in results/.

**Done when:** each table's grain and join relationships are understood.

## Part 4 — Analyse sales performance

Completed 8 October 2026. Five queries cover monthly sales, month-on-month growth, average order value across matched February–July periods, category contribution and buyer-state performance. All 139 output rows match an independent raw-record calculation. The sales run passed 15 checks and 10 sales test cases passed. See [Part 4 findings and walkthrough](11_part4_sales.md).

**GitHub deliverables:** sql/03_sales_analysis.sql, scripts/analyse_sales.py, scripts/sales_checks.py, tests/test_part4.py, docs/11_part4_sales.md and the five CSV outputs and validation evidence in results/.
**Done when:** each query answers a stated business question.

## Part 5 — Analyse delivery performance

Completed 8 October 2026. Five queries cover overall delivery outcomes, purchase-month patterns, buyer states, categories and seller investigation priorities. Category counts use one order per distinct category. The seller report uses only single-seller orders and a documented 100-order minimum, with coverage reported separately. All 310 result rows match independent raw-record calculations; 25 checks and 12 delivery test cases passed. See [Part 5 findings and walkthrough](12_part5_delivery.md).

**GitHub deliverables:** sql/04_delivery_analysis.sql, scripts/analyse_delivery.py, scripts/delivery_checks.py, tests/test_part5.py, docs/12_part5_delivery.md and the five CSV outputs and validation evidence in results/.
**Done when:** results include denominators and show association without claiming causation.

## Part 6 — Analyse customer experience

Completed 9 October 2026. Five queries cover review distribution and coverage, reviews by delivery outcome, the top 20 customers by observed product value, repeat purchases and buyer-state review patterns. Customer grouping uses customer_unique_id, with one eligible selected review per order. All 56 result rows match independent raw-record calculations; 26 checks and 12 customer test cases passed. See [Part 6 findings and walkthrough](13_part6_customers.md).

**GitHub deliverables:** sql/05_customer_analysis.sql, scripts/analyse_customers.py, scripts/customer_checks.py, tests/test_part6.py, docs/13_part6_customers.md and the five CSV outputs and validation evidence in results/.
**Done when:** repeat-customer and review metrics use the correct grain.

## Part 7 — Validate and improve SQL

Completed 9 October 2026. Checked join duplication, payment reconciliation and missingness against independent raw-record calculations. Traced five representative orders, added four reporting views and reconciled them to Parts 4–6. Measured an order-item lookup with and without an unnecessary TRIM predicate, using the existing index and identical result sets. Payment differences remain documented source exceptions with unconfirmed business causes. See [Part 7 walkthrough](14_part7_validation.md).

**GitHub deliverables:** sql/06_validation.sql, sql/07_reporting_views.sql, scripts/validate_part7.py, scripts/validation_checks.py, scripts/benchmark_part7.py, tests/test_part7_validation.py, tests/test_part7_reporting.py, docs/14_part7_validation.md, docs/05_validation_log.md and Part 7 evidence in results/.
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
