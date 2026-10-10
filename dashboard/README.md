# Olist Tableau dashboard gallery

[**Explore the interactive dashboard**](https://public.tableau.com/app/profile/mohammed.baquaysh/viz/Olist_Commerce_Review_Validated/Sales) · [Download the Tableau workbook](https://github.com/M980-221/ecommerce-sql-consulting-case-study/raw/refs/heads/main/tableau/Olist_Commerce_Review_Validated.twbx) · [Opening instructions](../tableau/README.md#open-on-a-mac) · [SQL and Tableau walkthrough](../docs/16_tableau_dashboard.md)

The project's finished dashboard is a native Tableau workbook with **Sales**, **Delivery** and **Customers** views. It contains 21 editable worksheets, shared month/state controls and two embedded Hyper extracts.

## Explore online

No installation is needed to use the published filters. Open a dashboard below, then change **Start month**, **End month** or **Buyer state**.

[Sales](https://public.tableau.com/app/profile/mohammed.baquaysh/viz/Olist_Commerce_Review_Validated/Sales) · [Delivery](https://public.tableau.com/app/profile/mohammed.baquaysh/viz/Olist_Commerce_Review_Validated/Delivery) · [Customers](https://public.tableau.com/app/profile/mohammed.baquaysh/viz/Olist_Commerce_Review_Validated/Customers)

## Dashboard screenshots

Captured directly in **Tableau presentation mode**, with the editing sidebar and toolbar hidden. The workbook was reviewed in **Tableau Public 2025.2 on Mac**. Every image uses **February 2017–July 2018 · All buyer states**. Click an image to open it at full resolution.

### Sales — volume, value and demand

**89,110 sales orders · 12,230,652.13 product value · 137.25 average order value**

Explore monthly product sales and compare contribution by product category and buyer state. Product value excludes freight and uses source monetary units.

[![Sales dashboard open in Tableau Public, showing 89,110 sales orders and monthly, category and state charts](../tableau/screenshots/sales-tableau.jpg)](../tableau/screenshots/sales-tableau.jpg)

### Delivery — late orders and delivery time

**89,102 eligible deliveries · 6,116 late orders · 6.86% late rate · 12.88 average days**

Compare lateness across purchase months, buyer states and categories. Labels show **late rate · late / eligible orders**, so a high rate can be assessed alongside its sample size. For example, **Home comfort 2 is 13.64%, based on 3 late deliveries out of 22**. Category populations can overlap.

[![Delivery dashboard open in Tableau Public, showing a 6.86% late-delivery rate and comparisons by month, state and category](../tableau/screenshots/delivery-tableau.jpg)](../tableau/screenshots/delivery-tableau.jpg)

### Customers — reviews and repeat purchasing

**86,271 customers · 2,562 repeat customers · 2.97% repeat rate · 4.15 average review score**

Explore review-score distribution, monthly review scores and order frequency. Repeat purchasing is recalculated inside the selected period; missing reviews are excluded from the mean.

[![Customers dashboard open in Tableau Public, showing 86,271 customers, a 2.97% repeat rate and review-score charts](../tableau/screenshots/customers-tableau.jpg)](../tableau/screenshots/customers-tableau.jpg)

## Explore the workbook

1. Open one of the live dashboard links above.
2. To edit the worksheets locally, download `Olist_Commerce_Review_Validated.twbx` and open it in Tableau Public.
3. Use **Start Month**, **End Month** and **Buyer State** to explore a selection. Keep Start Month on or before End Month.
4. Try March 2018 with buyer state RJ, then return to the defaults. The [checked figures](../tableau/README.md#verified-figures) provide a comparison for both selections.

The images show the workbook running in Tableau; interactive controls are available online, and editable worksheets are included in the download. See the [native verification record](../results/tableau_native_verification.json) for the checks performed.

<details>
<summary>Earlier web prototype and reproduction files</summary>

The HTML, CSS and JavaScript files in this folder belong to an earlier browser prototype. Its documentation and static previews are retained in [PROTOTYPE.md](PROTOTYPE.md). The current portfolio screenshots are the Tableau captures shown above.

</details>
