# Part 8 — Earlier web prototype

The primary dashboard deliverable is now the [Tableau workbook](16_tableau_dashboard.md). This page records the earlier browser implementation and its verification scope.


This stage turns the sales, delivery and customer analysis into three browser pages. The dashboard uses the checked Part 7 reporting views and keeps the same reporting period and eligibility rules. It runs locally from the downloaded repository, with no application installation or database connection needed to view it.

[Open the hosted dashboard](https://olist-commerce-review.mohammed-baquaysh.chatgpt.site) — **private, owner-only access**. The public repository copy can be downloaded and opened locally using the steps below.

## Open and use it

1. On GitHub, choose **Code → Download ZIP**, then unzip the repository.
2. Open the `dashboard` folder and double-click `index.html`. On a Mac, you can also right-click the file and choose **Open With → Safari** or another modern browser. Keep the other dashboard files in the same folder.
3. Choose **Sales**, **Delivery** or **Customers**. Set the first purchase month, last purchase month and buyer state; changes apply immediately.
4. Use **Reset filters** to restore February 2017 through July 2018 and all buyer states. If the start and end months cross, the other endpoint moves to the same month to keep a valid interval.
5. Expand the metric definitions when interpreting a result. **Download CSV** exports the current page and selection; ranking exports include all available rows, except the spending table's defined top-20 selection.

The month endpoints are inclusive in the controls. For example, March through March 2018 means purchases on or after `2018-03-01` and before `2018-04-01`. Switching pages preserves the filters. The state is the buyer's state, not the seller's.

## What each page answers

| Page | Main question | Measures |
|---|---|---|
| Sales performance | How much product value did eligible orders generate? | Product sales, order count, AOV and monthly/category/state comparisons |
| Delivery performance | How often were eligible orders late, and how long did delivery take? | Late counts and rates, elapsed delivery duration, late-only positive delay and delivery comparisons |
| Customer experience | What do selected reviews and observed repeat purchases show? | Review coverage, score distribution, delivery/review comparison, spending and repeat customers |

With the default filters, these figures provide a starting check against the earlier analysis:

| Measure | Full-period result | Evidence |
|---|---:|---|
| Eligible sales orders | 89,110 | [Monthly sales](../results/part4_monthly_sales.csv) |
| Product sales value | 12,230,652.13 | [Part 4](11_part4_sales.md) |
| Average order value | 137.25 | [Part 4](11_part4_sales.md) |
| Eligible delivery orders | 89,102 | [Overall delivery](../results/part5_overall_delivery.csv) |
| Late orders | 6,116 (6.86%) | [Overall delivery](../results/part5_overall_delivery.csv) |
| Average delivery duration | 12.88 days | [Overall delivery](../results/part5_overall_delivery.csv) |
| Reviewed sales orders | 88,494, with a mean score of 4.15 | [Part 6](13_part6_customers.md) |
| Observed customers | 86,271 | [Repeat customers](../results/part6_repeat_customers.csv) |
| Repeat customers | 2,562 (2.97%) | [Repeat customers](../results/part6_repeat_customers.csv) |

Amounts use **source monetary units**, not an assumed currency. Product value excludes freight and is not profit or Olist commission revenue. Filters change both the numerator and the relevant denominator; they do not merely hide rows from a fixed total.

## Definitions that matter when filtering

- **Sales and delivery have different populations.** Delivered orders with valid item value count towards sales. Timing measures also require valid delivery endpoints, leaving eight full-period sales orders outside delivery analysis.
- **On time includes arrival on the promised calendar day.** Duration is elapsed time from purchase to receipt; positive delay is calendar days beyond the promise, averaged among late orders only. A long delivery can still be on time.
- **Customer repeats are recalculated from the selected orders.** The dashboard groups eligible orders by persistent customer identity after applying the month and state filters. A person with two orders across the full window may have only one inside the selection and will then count as a one-time customer. Full-period repeat flags are not reused for a smaller selection.
- **Categories can overlap.** Repeated items from one category count once for delivery, but an order containing two categories appears in both. Adding category delivery counts does not give total unique orders. Sales category values use individual item prices, so order totals are not repeated for each item.
- **Missing reviews are not zero ratings.** The selected-review population excludes missing reviews from score averages and low-score rates. No eligible reviews means an undefined average, displayed as a dash. An empty selection similarly has zero counts and undefined rates rather than an invented zero rate.
- **Review timing limits interpretation.** The full-period late group contains 5,972 reviewed orders, including 4,274 responses submitted before receipt. The delivery/review comparison retains these under the agreed selection rule. It describes an association with eventual delivery status, not a post-delivery-only satisfaction measure or a causal effect.
- **Repeat purchases are observed within this window.** The measure is not retention, churn or lifetime value. The source snapshot does not provide equal follow-up time for every customer.

## Rebuild and check

```bash
python3 scripts/export_dashboard.py
python3 scripts/validate_dashboard.py
node --test tests/test_dashboard.mjs
node --test tests/test_dashboard_ui.mjs
python3 -m unittest discover -s tests -v
```

Run these from the repository folder after preparing the database and completing Part 7. Viewing the dashboard needs only the exported files; rebuilding requires the project database and Python, while the JavaScript tests require Node.js.

The exporter reads the reporting views into `dashboard/data.js`: **91,780 period orders and 89,830 order/category pairs** covering the union of sales and delivery populations. The delivery-only subset still has 89,822 category pairs, as reported in Part 7. The payload preserves integer monetary hundredths, delivery seconds, selected review scores and eligibility fields. Persistent customer indexes support regrouping under filters. Raw order/customer IDs, review text, city and ZIP fields are omitted.

`dashboard/metrics.js` calculates the same measures for the browser and the JavaScript tests. It aggregates unrounded integers first, then applies exact half-up rounding to displayed ratios. `dashboard/app.js` handles the controls, charts, tables and CSV downloads. All assets load locally; there is no CDN, fetch request or server dependency for the downloaded dashboard.

The [export validation](../results/part8_export_validation.json) checked **1,550,510 encoded cells** and **511 comparisons with the published analysis**, with matching keys and unchanged source records. The [text report](../results/part8_export_validation.txt) gives a shorter record. The exported file is approximately 5.66 MB.

The [calculation validation](../results/part8_validation.json) passed **eight filter scenarios and 13,129 compared cells**, plus **18 headline comparisons** with Parts 4–6. Scenarios cover the full window, one month, SP, RJ, a combined month/state filter, February–July 2018, the smaller RR population and an empty August 2017/RR selection. The [text report](../results/part8_validation.txt) records the results without the full JSON detail.

All **13 JavaScript fixture tests** passed, covering filter boundaries, missing reviews, overlapping categories, weighted averages, rounding and customer regrouping. The **73 Python tests** also passed, including five export tests and the 68 earlier tests. See the [JavaScript results](../results/part8_js_tests.txt) and [Python results](../results/part8_python_tests.txt).

Another **nine interface tests** passed using a **simulated DOM in Node**, covering control handlers, navigation, reset, crossed month endpoints, ranking expansion, empty results, loading errors and CSV blob creation. See [the interface test results](../results/part8_ui_tests.txt). This tests application logic without opening a real browser.

## Previews and remaining browser checks

Static data previews: [Sales](../dashboard/screenshots/sales-preview.svg) · [Delivery](../dashboard/screenshots/delivery-preview.svg) · [Customers](../dashboard/screenshots/customers-preview.svg).

Regenerate them from the dashboard's default metrics with `python3 scripts/render_dashboard_previews.py`.

The images in `dashboard/screenshots/` are **static data previews, not screenshots captured from the running browser dashboard**. They help GitHub readers inspect the headline results. They do not verify the HTML layout or interactive controls.

Automated checks compare the exported data and calculated measures with SQL, including filtered selections and edge cases. Direct checks in a real browser have not been completed. In particular, local Safari behaviour, chart layout at different window sizes, keyboard navigation, page switching and downloaded CSV behaviour still need a direct browser check. The simulated DOM tests do not establish that browser rendering or interactions have passed.

## Two queries to explain in an interview

```sql
SELECT COUNT(*) AS delivery_orders,
       COALESCE(SUM(is_late), 0) AS late_orders,
       100.0 * SUM(is_late) / NULLIF(COUNT(*), 0) AS late_delivery_pct
FROM v_reporting_orders
WHERE delivery_eligible = 1
  AND order_purchase_timestamp >= '2018-03-01'
  AND order_purchase_timestamp < '2018-04-01'
  AND customer_state = 'RJ';
```

`WHERE` performs the same selection as choosing March 2018 and RJ in the dashboard. `COUNT(*)` counts the eligible orders; `SUM(is_late)` counts late orders because the flag is 1 or 0. `COALESCE` returns a zero late count for an empty selection, while `NULLIF` leaves its rate undefined. This practice query leaves the percentage unrounded; the dashboard rounds at display time.

This returns **864 eligible delivery orders and 298 late orders**, a rate of approximately **34.49%**. Compare it with the Delivery page after applying the same filters.

```sql
SELECT customer_unique_id, COUNT(*) AS sales_orders
FROM v_reporting_orders
WHERE sales_eligible = 1
  AND order_purchase_timestamp >= '2018-03-01'
  AND order_purchase_timestamp < '2018-04-01'
  AND customer_state = 'RJ'
GROUP BY customer_unique_id
HAVING COUNT(*) >= 2
ORDER BY sales_orders DESC, customer_unique_id;
```

Here, `WHERE` selects individual orders first. `GROUP BY` collects those orders for each persistent customer, and `HAVING` retains customer groups with at least two selected orders. This is why the dashboard must calculate repeats again when a filter changes. The query returns repeat customers, not every customer; the repeat percentage still needs all selected customers as its denominator.

This returns **14 repeat customers**, each with two eligible orders in this selection. Try extending the month range and explain why a customer's classification can change.

**Next: Part 9 — recommendations.** Combine the validated sales, delivery and customer findings into three proposed actions, with owners, success measures and limits.
