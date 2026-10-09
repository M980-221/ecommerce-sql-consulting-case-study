# Olist Tableau dashboard

The native Tableau workbook contains three dashboards: **Sales**, **Delivery** and **Customers**. Each uses the project's checked SQL data and the shared **Start Month**, **End Month** and **Buyer State** parameters.

[Download the packaged workbook](Olist_Commerce_Review.twbx) · [Editable workbook source](Olist_Commerce_Review.twb)

The workbook targets Tableau's **26.1 schema**. Use Tableau Desktop Public Edition **2026.1 or newer**; opening and compatibility still require the native application check described below.

## Open on a Mac

1. Install the free [Tableau Desktop Public Edition](https://www.tableau.com/products/public/download). Open the downloaded `.dmg`, launch its `.pkg` installer and follow the prompts. Tableau's [installation guide](https://help.tableau.com/current/desktopdeploy/en-us/desktop_deploy_download_and_install.htm) covers the Mac steps.
2. Download the packaged `.twbx` workbook using the link above. If GitHub shows a file page, use its download button to save the file itself.
3. Open Tableau Public, choose **File → Open**, then select the `.twbx`. The package contains its CSV data; opening it does not require the project database or a Python setup.
4. Select the Sales, Delivery or Customers dashboard tab. Set the three parameters to explore a purchase-month range and buyer state. Use the default February 2017–July 2018 and all states for the full-period results.

Keep Start Month on or before End Month. A reversed range gives an empty selection rather than swapping the controls automatically.

The `.twbx` combines the workbook and local data in one file. The editable `.twb` is also supplied; keep its neighbouring `data` folder if opening that version. See Tableau's [packaged-workbook documentation](https://help.tableau.com/current/pro/desktop/en-us/save_savework_packagedworkbooks.htm).

## Read the figures

- Sales use eligible delivered orders and item prices, excluding freight. Monetary values use source units.
- Delivery timing has its own eligibility rule. Receipt on the promised day is on time; average positive delay uses late orders only.
- Selected reviews are averaged over reviewed orders. Missing reviews remain missing; responses may precede delivery.
- Customer repeats are recalculated inside the selected months and state. A customer needs at least two selected eligible orders; this is not a retention measure.
- Category delivery counts overlap when an order contains more than one category. They cannot be added as unique orders.

There are **21 editable worksheets: 12 KPI sheets and nine charts**, arranged as four KPI cards and three charts on each dashboard. Sales charts show monthly product value and category/state contribution. Delivery charts compare late rates by purchase month, state and category. Customer charts show review scores, their monthly mean and purchase frequency.

The three dashboard tabs form the main interface; individual worksheet tabs are hidden. To inspect their calculations on a Mac, Control-click a dashboard tab and choose **Unhide All Sheets**. See Tableau's [sheet-management guide](https://help.tableau.com/current/pro/desktop/en-us/environ_workbooksandsheets_sheets_hideshow.htm).

The packaged file contains the workbook, both CSV sources and `DATA_LICENSE.txt`. The two sources retain different row meanings; the order source supplies order/customer measures, while the category source supplies category measures.

## Validation status

The [source export checks](../results/tableau_export_validation.json) passed **2,273,050 cell comparisons** and **511 published-result comparisons**. The package uses 91,780 order rows and 89,830 order/category pairs, with unchanged source fingerprints.

The [offline workbook validation](../results/tableau_validation.json) passed the official **26.1 XML schema** and checked workbook references. The packaged workbook, two CSVs and data licence match the editable files byte for byte. Independent calculations from the packaged CSVs matched SQLite in **eight filter scenarios and 13,487 values**, including monthly reviews and purchase frequency, with **18 headline comparisons** against the earlier analysis. See the [readable results](../results/tableau_validation.txt).

The data, workbook XML, schema and package checks do **not** establish that Tableau has opened or rendered the workbook correctly. The native application was unavailable in the build environment. Formula execution, dashboard layout and parameter interactions therefore still need a check inside Tableau on the Mac. No Tableau screenshots or successful native runtime check are claimed.

The full [Tableau walkthrough](../docs/16_tableau_dashboard.md) includes reference figures, SQL practice, rebuild commands and the remaining application checks. It also explains how to publish from Public Edition after reviewing the workbook. Published Tableau Public workbooks and their data are openly accessible, as explained in [Tableau's publishing guide](https://help.tableau.com/current/pro/desktop/en-us/publish_workbooks_tableaupublic.htm).
