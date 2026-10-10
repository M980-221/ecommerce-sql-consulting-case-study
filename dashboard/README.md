# Olist Tableau dashboard gallery

[**Download the Tableau workbook**](https://github.com/M980-221/ecommerce-sql-consulting-case-study/raw/refs/heads/main/tableau/Olist_Commerce_Review_Validated.twbx) · [Opening instructions](../tableau/README.md#open-on-a-mac) · [SQL and Tableau walkthrough](../docs/16_tableau_dashboard.md)

The project's finished dashboard is a native Tableau workbook with **Sales**, **Delivery** and **Customers** views. It contains 21 editable worksheets, shared month/state controls and two embedded Hyper extracts.

## Dashboard screenshots

Captured directly from the finished workbook in **Tableau Public 2025.2 on Mac**. Every image uses **February 2017–July 2018 · All buyer states**. Click an image to open it at full resolution.

### Sales — volume, value and demand

**89,110 sales orders · 12,230,652.13 product value · 137.25 average order value**

Explore monthly product sales and compare contribution by product category and buyer state. Product value excludes freight and uses source monetary units.

[![Sales dashboard open in Tableau Public, showing 89,110 sales orders and monthly, category and state charts](../tableau/screenshots/sales-tableau.jpg)](../tableau/screenshots/sales-tableau.jpg)

### Delivery — late orders and delivery time

**89,102 eligible deliveries · 6,116 late orders · 6.86% late rate · 12.88 average days**

Compare lateness across purchase months, buyer states and categories. Rates use eligible deliveries within each group; category populations can overlap.

[![Delivery dashboard open in Tableau Public, showing a 6.86% late-delivery rate and comparisons by month, state and category](../tableau/screenshots/delivery-tableau.jpg)](../tableau/screenshots/delivery-tableau.jpg)

### Customers — reviews and repeat purchasing

**86,271 customers · 2,562 repeat customers · 2.97% repeat rate · 4.15 average review score**

Explore review-score distribution, monthly review scores and order frequency. Repeat purchasing is recalculated inside the selected period; missing reviews are excluded from the mean.

[![Customers dashboard open in Tableau Public, showing 86,271 customers, a 2.97% repeat rate and review-score charts](../tableau/screenshots/customers-tableau.jpg)](../tableau/screenshots/customers-tableau.jpg)

## Explore the workbook

1. Download `Olist_Commerce_Review_Validated.twbx` using the link above.
2. Open the file in Tableau Public and select a dashboard tab.
3. Use **Start Month**, **End Month** and **Buyer State** to explore a selection. Keep Start Month on or before End Month.
4. Try March 2018 with buyer state RJ, then return to the defaults. The [checked figures](../tableau/README.md#verified-figures) provide a comparison for both selections.

The images show the workbook running in Tableau; the interactive controls and editable worksheets are available in the downloaded file. See the [native verification record](../results/tableau_native_verification.json) for the checks performed.

<details>
<summary>Earlier web prototype and reproduction files</summary>

The HTML, CSS and JavaScript files in this folder belong to an earlier browser prototype. Its documentation and static previews are retained in [PROTOTYPE.md](PROTOTYPE.md). The current portfolio screenshots are the Tableau captures shown above.

</details>
