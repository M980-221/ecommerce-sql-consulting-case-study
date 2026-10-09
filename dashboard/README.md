# Olist dashboard

Three browser pages explore **Sales performance**, **Delivery performance** and **Customer experience** for purchases from February 2017 through July 2018. The dashboard uses the validated SQLite reporting data and the project's existing metric definitions.

[Open the hosted dashboard](https://olist-commerce-review.mohammed-baquaysh.chatgpt.site) — **private, owner-only access**. Anyone with the public repository files can open the downloaded copy locally.

## Open locally

1. Download the repository ZIP from GitHub and unzip it.
2. Open `dashboard/index.html` in a modern browser. On a Mac, double-click it or use **Open With → Safari**.
3. Keep the whole dashboard folder together. The page loads its data, styles and scripts from adjacent files and works offline after downloading.

No application installation, web server or database connection is needed to view the exported dashboard. Its editable source is HTML, CSS and JavaScript.

## Use the filters

- Choose the first and last **purchase month**, including both endpoints, and a **buyer state**. Changes apply immediately; page changes keep the selection.
- The default is February 2017 through July 2018 and all buyer states. **Reset filters** restores it. If month endpoints cross, the other endpoint adjusts to keep a valid range.
- **Download CSV** exports the current page and filters. Ranking exports retain all available rows except the customer spending table, which deliberately shows the top 20 after aggregation.
- Expand the definitions to check the population and denominator. Empty populations show zero counts and dashes for undefined rates and means.

Product value excludes freight and uses source monetary units. Delivery compares the recorded receipt date with the promised calendar day; same-day arrival is on time. Missing reviews are excluded from score averages rather than converted to zero. Customer repeats are regrouped from eligible orders inside the current selection, using persistent customer identity.

Category delivery counts overlap across categories, so they cannot be added to get unique orders. Selected reviews can precede delivery: 4,274 of the 5,972 reviewed late orders do so under the full-period filters. The comparison is descriptive and does not establish the effect of lateness on customer scores. Repeat purchases within the window do not measure retention or churn.

## Files and rebuilding

| File | Purpose |
|---|---|
| [index.html](index.html) | Dashboard entry page |
| [styles.css](styles.css) | Page layout, colours and responsive styles |
| [data.js](data.js) | Exported reporting data with compact order/category rows and persistent customer indexes |
| [metrics.js](metrics.js) | Shared aggregation, filtering and rounding functions |
| [app.js](app.js) | Page controls, charts, tables and CSV downloads |

```bash
python3 scripts/export_dashboard.py
python3 scripts/validate_dashboard.py
node --test tests/test_dashboard.mjs
node --test tests/test_dashboard_ui.mjs
python3 -m unittest discover -s tests -v
```

Run the commands from the repository root after Part 7. The first rebuilds the exported data from the prepared SQLite database; the next checks the dashboard calculations against SQL. Node.js is needed for the JavaScript fixture tests, not for viewing the dashboard.

The [export validation](../results/part8_export_validation.json) passed: **91,780 orders, 89,830 order/category pairs and 1,550,510 encoded cells** were checked, together with **511 published-result comparisons**. Category pairs cover the sales/delivery union; 89,822 belong to delivery-eligible orders. Source fingerprints are unchanged, and the exporter opens the database read-only.

The [calculation validation](../results/part8_validation.json) passed **eight filter scenarios, 13,129 compared cells and 18 headline comparisons** with the earlier analysis. All [13 JavaScript fixture tests](../results/part8_js_tests.txt) and [73 Python tests](../results/part8_python_tests.txt) passed. The scenarios include a combined month/state filter and a selection with no orders; customer counts are recomputed for each.

All [nine interface tests](../results/part8_ui_tests.txt) also passed. They exercise navigation, filter handlers, reset, ranking expansion, empty results, loading errors and CSV blob creation through a **simulated DOM in Node**, rather than a real browser session.

## Preview and verification limits

Static data previews: [Sales](screenshots/sales-preview.svg) · [Delivery](screenshots/delivery-preview.svg) · [Customers](screenshots/customers-preview.svg).

Regenerate them with `python3 scripts/render_dashboard_previews.py` from the repository root.

The images in `screenshots/` are **static data previews**, not captures from a running browser session. They show results for GitHub readers but do not establish that rendering or interactions have passed browser checks.

Browser rendering, local Safari behaviour, responsive layout, keyboard use, filter controls and CSV downloads have not been directly verified. Calculation tests and SQL comparisons do not replace those checks.

See [Part 8](../docs/15_part8_dashboard.md) for the full walkthrough and practice SQL, and [metric definitions](../docs/04_metric_definitions.md) for the populations and limitations.

