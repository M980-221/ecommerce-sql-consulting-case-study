# Native Tableau dashboard

The project now has a Tableau workbook for its sales, delivery and customer analysis. SQL prepares the checked data; Tableau supplies the worksheets, dashboard layouts and parameter-driven calculations. The workbook keeps the existing reporting period and metric definitions.

[Packaged workbook](../tableau/Olist_Commerce_Review.twbx) · [Editable workbook](../tableau/Olist_Commerce_Review.twb)

Target format: **Tableau workbook schema 26.1**, intended for Tableau Desktop Public Edition **2026.1 or newer**. Native compatibility and rendering have not yet been confirmed by opening the file in Tableau.

## Open and explore

Install the free [Tableau Desktop Public Edition for Mac](https://www.tableau.com/products/public/download), then open the packaged workbook with **File → Open**. The package contains the local CSV sources. The short [Mac guide](../tableau/README.md#open-on-a-mac) covers installation and opening; Tableau also documents [Mac installation](https://help.tableau.com/current/desktopdeploy/en-us/desktop_deploy_download_and_install.htm).

Choose **Sales**, **Delivery** or **Customers**, then use **Start Month**, **End Month** and **Buyer State**. The dates select purchase months, including both endpoints. Keep Start Month on or before End Month. Buyer State describes the customer's location, not the seller's.

Defaults are February 2017, July 2018 and **All**. If Start Month is later than End Month, the selection has no eligible rows; counts become zero and means/rates are undefined. The workbook does not automatically swap the endpoints.

These are workbook parameters used inside calculations. A parameter by itself does not filter records; the calculated selection rule applies its values to each source. Tableau documents this distinction in [Create Parameters](https://help.tableau.com/current/pro/desktop/en-us/parameters_create.htm).

The workbook contains **21 editable worksheets: 12 KPI sheets and nine charts**, arranged into the three dashboards below.

| Dashboard | Four KPI cards | Three charts |
|---|---|---|
| Sales | Sales orders, product sales value, average order value, selected orders across all statuses | Monthly product sales; product value by category; product value by buyer state |
| Delivery | Eligible deliveries, late orders, late-delivery rate, average delivery days | Late-delivery rate by purchase month, buyer state and category |
| Customers | Observed customers, repeat customers, observed repeat rate, average review score | Selected review scores; review score by purchase month; customer purchase frequency |

The packaged workbook includes both CSVs and `DATA_LICENSE.txt`. Its worksheets and calculated fields are editable Tableau objects, rather than pictures of charts. The order and category data sources remain separate so category memberships do not repeat order-level values.

The workbook hides individual worksheet tabs and presents the three dashboard tabs first. On a Mac, Control-click a dashboard tab and choose **Unhide All Sheets** to inspect the underlying sheets; Tableau documents this in [Manage Sheets](https://help.tableau.com/current/pro/desktop/en-us/environ_workbooksandsheets_sheets_hideshow.htm). Delivery chart tooltips are configured to include both late and eligible order counts, and the monthly review chart includes its reviewed-order count. These are workbook settings; their native rendering still needs verification.

## Figures to check first

Restore February 2017 through July 2018 and all buyer states, then compare the workbook with these SQL results:

| Measure | Full-period result |
|---|---:|
| Eligible sales orders | 89,110 |
| Product sales value, excluding freight | 12,230,652.13 source units |
| Average order value | 137.25 source units |
| Eligible delivery orders | 89,102 |
| Late orders | 6,116 (6.86%) |
| Average purchase-to-receipt duration | 12.88 days |
| Mean delay among late orders | 10.98 calendar days |
| Reviewed sales orders | 88,494 |
| Mean selected review score | 4.15 / 5 |
| Observed customers | 86,271 |
| Repeat customers | 2,562 (2.97%) |

The source evidence is in [Sales](11_part4_sales.md), [Delivery](12_part5_delivery.md) and [Customers](13_part6_customers.md). These are expected results from SQL, not figures confirmed by executing the native Tableau workbook.

For a second check, select **March 2018** at both month endpoints and **RJ**. The selection should have **864 eligible sales and delivery orders**, **298 late orders (34.49%)**, **850 customers** and **14 repeat customers**. Changing a parameter must update the denominator as well as the displayed value.

## Where SQL ends and Tableau calculations start

```sql
SELECT c.customer_unique_id,
       COUNT(*) AS selected_sales_orders
FROM v_reporting_orders o
JOIN v_clean_customers c ON c.customer_id = o.customer_id
WHERE o.sales_eligible = 1
  AND o.purchase_month = '2018-03'
  AND o.customer_state = 'RJ'
GROUP BY c.customer_unique_id
HAVING COUNT(*) >= 2
ORDER BY selected_sales_orders DESC, c.customer_unique_id;
```

Run this practice query in the prepared SQLite database. It returns **14 customers**, each with two eligible orders in March 2018/RJ.

- `o` and `c` are aliases. `JOIN` matches each order to its customer record using `customer_id`. That customer key is unique, so the lookup does not multiply orders.
- `WHERE` selects individual orders before grouping. It applies sales eligibility, month and buyer state.
- `GROUP BY` collects those orders by the persistent `customer_unique_id`. `HAVING` then keeps customer groups with at least two orders.
- The lookup is shown explicitly for practice. The reporting model already contains persistent customer identity; the Tableau export represents it with a numeric `customer_key`.

SQL performs the preparation: resolving row meaning, selecting reviews, checking eligibility and exporting the two flat sources. Tableau then evaluates calculations against those exported rows as the workbook parameters change. The CSVs are a data snapshot; changing a Tableau parameter does not rerun the project's SQLite scripts.

The workbook's **Customer Selected Orders** field is:

```tableau
{ FIXED [customer_key] :
    COUNTD(IF [Selected Sale] THEN [order_key] END)
}
```

`[Selected Sale]` means an order satisfies the shared month/state parameters and its sales eligibility flag. `FIXED [customer_key]` evaluates the order count for each persistent customer. `COUNTD` counts distinct order keys. The selection is inside this calculation, so changing the parameters changes the customer's count rather than reusing a full-period total.

The **Repeat Customers** field then uses that count:

```tableau
COUNTD(
    IF [Selected Sale] AND [Customer Selected Orders] >= 2
    THEN [customer_key]
    END
)
```

This counts each qualifying customer once. It corresponds to the group-size condition in the SQL `HAVING` example. A customer with two selected orders contributes one repeat customer, not two. The repeat rate divides that result by all customers with at least one selected sale, so its denominator is customers rather than orders.

The complete calculated-field definitions are in the [workbook builder](../scripts/build_tableau.py). These are the authored Tableau formulas; the validation described below checks their references and numerical specification without executing them in Tableau.

## Data and interpretation

| Source | Row meaning | Rows |
|---|---|---:|
| [orders.csv](../tableau/data/orders.csv) | One order purchased within the reporting window, retaining its eligibility flags | 91,780 |
| [categories.csv](../tableau/data/categories.csv) | One distinct order/category pair across the sales and delivery populations | 89,830 |

The category file carries category-level product values and the order's eligible delivery outcome. Its delivery-only subset contains 89,822 pairs. Money remains integer hundredths in the exported files, and elapsed delivery time remains integer seconds. Blank CSV cells represent missing values. Raw order/customer IDs and free-text reviews are omitted; numeric keys retain the grouping relationships needed for the analysis.

Missing reviews are excluded from score averages and low-score rates. They are not zero scores. Of the full-period late group's 5,972 selected reviews, 4,274 were submitted before receipt, so the comparison is not exclusively about post-delivery satisfaction. It describes an association, not proof that late delivery caused a lower score.

Repeat means at least two eligible orders from the same persistent customer within the chosen months and state. Filtering must change the repeat calculation; the full-period repeat flag cannot be reused. Same-day orders still count separately. Unequal observation time and incomplete customer histories mean this is not retention, churn or loyalty.

Delivery categories describe whether an order contains a category. Repeated items in one category count once, but an order with two categories appears in both groups. Product sales by category use item prices; repeating an entire order's value after a category join would inflate sales.

## Rebuild and validation

Rebuilding requires **Python 3.9 or newer** and `lxml` for schema validation. Install the latter in the Python environment with `python3 -m pip install lxml` if needed.

```bash
python3 scripts/export_tableau.py
python3 scripts/build_tableau.py --schema tableau/schema/twb_2026.1.0.xsd
python3 scripts/validate_tableau.py
python3 -m unittest discover -s tests -v
```

Run these from the repository root after preparing the project database and completing Part 7. The exporter writes the two CSV sources from checked SQL. The builder creates the workbook and packages it with those sources. The validator checks the files and structure outside Tableau; it does not launch the application.

The export and base builder use Python's standard library. The `--schema` option checks the workbook before writing it. Schema checks use the vendored Tableau files offline and verify their recorded hashes.

The [source export report](../results/tableau_export_validation.json) passed **2,273,050 cell comparisons** and **511 comparisons with published analysis totals**. It checks both CSVs after serialization, so empty cells retain missing values and numeric values remain unchanged. The database is opened read-only and all eight source-table fingerprints remain unchanged. A [text report](../results/tableau_export_validation.txt) is also supplied.

The [offline workbook validation](../results/tableau_validation.json) passed the official **26.1 XML schema** and checked the worksheet, calculated-field and parameter references. It confirmed the 21 worksheets, three dashboards and shared parameter definitions. The `.twbx` workbook, both CSV sources and data licence match the editable files byte for byte.

Independent Python calculations from the packaged CSVs matched SQLite across **eight filter scenarios and 13,487 compared values**, including the monthly-review and purchase-frequency charts, with **18 headline comparisons** to Parts 4–6. Cases include the full window, one month, SP, RJ, March 2018/RJ, February–July 2018, RR and an empty August 2017/RR selection. These are checks of the supplied data and numerical specification, not values captured from Tableau. The [text report](../results/tableau_validation.txt) records the results concisely.

The source-data and package checks run outside Tableau. An XML schema can check allowed elements and attributes; it cannot prove that a chart renders well, a calculated field evaluates successfully or a parameter affects every intended sheet. The native Tableau application was unavailable in the build environment, so those checks remain open.

When first opening the workbook on the Mac, inspect all three dashboard tabs, compare the full-period figures above, then test March 2018/RJ and a return to the defaults. Check that the mean review score excludes missing reviews and that repeat-customer counts respond to the selection. Only after those application checks should the workbook be described as tested in Tableau.

## Publish when ready

The workbook can be saved locally while it is being reviewed. To share a checked copy online from **Tableau Desktop Public Edition**, use **Server → Tableau Public → Save to Tableau Public**, sign in and give it a project title. The publishing process creates an extract. This route is documented in [Save Workbooks with Tableau Public](https://help.tableau.com/current/pro/desktop/en-us/publish_workbooks_tableaupublic.htm).

Tableau Public makes the workbook and its data publicly accessible. The workbook has not been published to a Tableau Public profile as part of these file-generation and validation steps.
