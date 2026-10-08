# Metric definitions

These definitions are implemented in Part 3 and used by the sales and delivery queries. They also apply to the customer analysis still to come. Counts below describe eligibility; findings are in [Part 4](11_part4_sales.md) and [Part 5](12_part5_delivery.md).

## Period and observation limits

Use purchases from **1 February 2017 through 31 July 2018**: `order_purchase_timestamp >= '2017-02-01' AND order_purchase_timestamp < '2018-08-01'`.

This gives 18 calendar months with activity on every day in the source. The 2016 records are sparse, and January 2017 starts on the 5th. August 2018 is reserved as a boundary month: delivered purchases end on the 29th and only five purchases appear on the final two days, all non-delivered. September and October have very few purchases. This is a conservative comparison window, not proof that the publisher captured every order. All boundary records remain available in the raw and clean views.

Eligibility uses the final status, deliveries and reviews present in the snapshot, including outcomes after the purchase window. It is not an as-of-month-end reconstruction. There is no supplied extraction timestamp or status history establishing a common follow-up horizon. Later purchasers also have less time to purchase again.

## Shared populations

| Population | SQL rule | Orders |
|---|---|---:|
| Full source | All rows of `v_order_analysis` | 99,441 |
| Reporting period | `in_reporting_period = 1` | 91,780 |
| Sales | `sales_eligible = 1` | 89,110 |
| Delivery | `delivery_eligible = 1` | 89,102 |
| Reviewed sales orders | `review_eligible = 1` | 88,494 |
| Delivery and review comparison | Both delivery and review flags equal 1 | 88,486 |
| Single-seller delivery orders | `seller_delivery_eligible = 1` | 87,946 |

- **Sales:** delivered orders purchased in the period, with at least one item and a valid item-value total. A missing delivery timestamp does not remove a sale. There are 2,670 non-delivered period orders, excluded from sales measures.
- **Delivery:** delivered orders purchased in the period, with valid purchase, actual-delivery and promised dates, actual delivery at or after purchase, and promised calendar day at or after purchase day. Eight delivered orders lack an actual date and are excluded. Carrier events are not used in these endpoint measures; their chronology problems remain flagged.
- **Reviews:** sales-eligible orders with a selected valid review. 616 sales orders have no eligible selected review. Lateness comparisons use the intersection with the delivery population.
- **Sellers:** delivery-eligible orders supplied by exactly one seller. Orders involving multiple sellers are excluded from seller attribution. Show coverage and sample size with each seller result.

## Measures

| Metric | Calculation and denominator |
|---|---|
| All period orders | `COUNT(*)` where `in_reporting_period = 1`; show the status breakdown |
| Delivered orders for sales | `COUNT(*)` where `sales_eligible = 1`; this matches all delivered period orders in this snapshot |
| Product sales value | `SUM(product_sales_cents) / 100.0` over sales-eligible orders; excludes freight |
| Average order value | `SUM(product_sales_cents) / 100.0 / NULLIF(COUNT(*), 0)` over that same sales population |
| Category contribution | Sum qualifying item `price_cents` by `category_label`, divided by total qualifying item value; keep missing/untranslated categories in the total |
| Regional sales | Sum order value by `customer_state` over sales-eligible orders; this describes the buyer's state |
| Late-delivery rate | `100.0 * SUM(is_late) / NULLIF(COUNT(*), 0)` over delivery-eligible orders |
| Average positive delay | `AVG(delay_days)` over delivery-eligible orders where `is_late = 1`; calendar days |
| Average delivery duration | `AVG(delivery_days)` over delivery-eligible orders; elapsed fractional days from purchase to receipt |
| Average review score | `AVG(review_score)` over review-eligible orders; one selected score per order |
| Low-score share | Percentage with selected score 1 or 2 over the same review population |
| Observed repeat-customer rate | Persistent customer IDs with at least two sales-eligible orders divided by IDs with at least one, using `customer_unique_id`; multiply by 100 |
| Monthly growth | `(current_value - prior_value) / NULLIF(prior_value, 0) * 100`; same population, consecutive months within the reporting period; first month is NULL |

All division by zero returns NULL, not a zero rate. Show eligible counts, excluded counts and the period beside headline measures. Category-level distinct order counts can overlap because one order can contain multiple categories; they must not be added to get total orders.

Part 4 compares **February–July 2017 with February–July 2018** for its year-on-year result. Each period contains six matching calendar months. Period AOV is total value divided by total orders, rather than an unweighted average of monthly AOVs. Growth uses unrounded amounts; only the displayed answer is rounded. Monthly outputs include all 18 calendar months, so LAG always refers to the preceding month. Rounded category or state shares may not add to exactly 100%.

## Delivery comparisons

- **On time includes early delivery and arrival at any time on the promised calendar date.** Lateness compares calendar dates, not the promise's midnight timestamp. Delivery duration uses elapsed recorded timestamps; positive delay uses whole calendar days after the promise.
- **Late-only averages:** average positive delay uses the number of late orders as its denominator. Non-late orders contribute NULL to that average. If a group has no late orders, its positive-delay average is NULL rather than zero.
- **Displayed precision:** rates and durations are shown to two decimal places. Positive delay is summed in whole calendar days; its mean uses integer arithmetic to round exact halfway values up, so 9.825 becomes 9.83. Rounding does not change the stored dates or the population.
- **Purchase months:** the monthly report contains all 18 reporting months and assigns orders by purchase date. Delivery outcomes recorded after the purchase window remain included; these are final-snapshot results, not month-end service levels with equal follow-up.
- **Regions:** group by the buyer's state and show all groups, with counts beside rates. Order counts, not percentages, are added across states.
- **Categories:** retain one row per distinct order/category pair before calculating delivery measures. Repeated items in the same category count once; an order with two categories appears in both groups. Unknown and untranslated categories stay included. Category counts therefore overlap and cannot be summed to obtain total orders. The allocation describes association with order-level delivery, not an individual item's delivery outcome.
- **Sellers:** retain only eligible orders with exactly one distinct seller, then use `HAVING COUNT(*) >= 100` for the published investigation table. Several items from the same seller still count as one order. Show the excluded multi-seller and lower-volume groups separately. The threshold is an exploratory reporting choice, not evidence of statistical significance.
- **Investigation order:** sort states, categories and sellers by late-order count descending, then unrounded late rate descending, then label/ID. Use counts and rates together; the ordering does not establish responsibility for delays or adjust for distance, order mix, purchase month or promised delivery time.

## Review selection

Retain a candidate only when its score is 1–5, its creation calendar date is not before the purchase date, its response timestamp is not before purchase, and the response is not before review creation. Creation timestamps are midnight dates, so comparing creation to the full purchase timestamp would incorrectly reject some same-day reviews.

For each order, select the latest valid response timestamp. Break ties using latest creation timestamp, then review ID ascending. Score is never a sorting criterion. The source has 99,224 review rows: 64 fail the chronology/score rule, 548 additional valid reviews are not selected, and 98,612 orders receive one selected review. No source review is deleted. Reviews may precede delivery; the later comparison describes an association, not a causal effect of lateness.

## Money and missing values

Store monetary amounts as integer hundredths (`*_cents`) and divide by 100.0 for display. Every conversion and total was checked against Python Decimal. The CSVs have no currency-code field; these outputs use **source monetary units**. A BRL label needs publisher confirmation before it is added to the dashboard. No conversion to SAR or USD is made.

Product sales value is not Olist commission revenue or profit. Freight and payments are separate measures. Missing payment totals stay NULL; they do not become zero. Known zero-value payment components are retained.

Payment reconciliation is a diagnostic, not the definition of product sales. Of 98,665 orders with items and payments, 98,089 reconcile exactly, 273 differ by one cent and 303 differ by more than one cent. Their values are preserved; causes require investigation in Part 7.

## Joins

For order measures, use `v_order_analysis`, which joins items and payments only after aggregating each to one row per order, and joins one selected review. For category/product sales, join eligible order IDs to item rows and `v_products_labeled`. Never sum an order's full value once for every item.

Evidence: [validation results](../results/part3_validation.json), [data dictionary](03_data_dictionary.md), [cleaning SQL](../sql/02_cleaning.sql).
