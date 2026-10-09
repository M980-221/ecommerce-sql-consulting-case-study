/* Browser report. Business calculations live in metrics.js; this file presents them. */
(function (root) {
  "use strict";

  const metricsLibrary = root.OlistMetrics || (typeof module !== "undefined" && module.exports ? require("./metrics.js") : null);

  const PAGES = {
    sales: { title: "Sales performance", subtitle: "Product value, order volume and where demand comes from." },
    delivery: { title: "Delivery performance", subtitle: "The delivery promise, actual arrival and where delays add up." },
    customers: { title: "Customer experience", subtitle: "Selected reviews, observed spending and repeat purchases." }
  };
  const STATE_NAMES = { AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia", CE: "Ceará", DF: "Federal District", ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MT: "Mato Grosso", MS: "Mato Grosso do Sul", MG: "Minas Gerais", PA: "Pará", PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RS: "Rio Grande do Sul", RO: "Rondônia", RR: "Roraima", SC: "Santa Catarina", SP: "São Paulo", SE: "Sergipe", TO: "Tocantins" };
  const nf = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const df = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const shortMonth = new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
  const longMonth = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
  const esc = value => String(value == null ? "" : value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const valid = value => value !== null && value !== undefined && Number.isFinite(Number(value));
  const number = value => valid(value) ? nf.format(value) : "—";
  const decimal = value => valid(value) ? df.format(value) : "—";
  const percent = value => valid(value) ? decimal(value) + "%" : "—";
  const compact = value => {
    if (!valid(value)) return "—";
    const x = Math.abs(value);
    return x >= 1000000 ? decimal(value / 1000000) + "M" : x >= 10000 ? decimal(value / 1000) + "K" : decimal(value);
  };
  const axisNumber = value => Math.abs(value) >= 1000000 ? (value / 1000000).toFixed(1) + "M" : Math.abs(value) >= 1000 ? (value / 1000).toFixed(0) + "K" : nf.format(value);
  const monthName = (value, full) => {
    if (!value || !/^\d{4}-\d{2}$/.test(value)) return "—";
    return (full ? longMonth : shortMonth).format(new Date(value + "-01T00:00:00Z"));
  };
  const categoryName = label => String(label || "Unknown category").replace(/_/g, " ").replace(/\b\w/g, x => x.toUpperCase());
  const stateName = label => STATE_NAMES[label] || label;
  const asArray = value => Array.isArray(value) ? value : [];
  const empty = message => `<p class="empty-note">${esc(message || "No eligible orders in this selection.")}</p>`;

  function filterLabels(snapshot, data) {
    const f = snapshot.filters;
    return { start: data.months[f.startMonth], end: data.months[f.endMonth], state: f.state === "all" ? "All buyer states" : data.states[f.state], months: f.endMonth - f.startMonth + 1 };
  }

  function card(label, value, note, index, unit) {
    return `<article class="kpi-card"><div class="kpi-label"><span>${esc(label)}</span><span class="kpi-index">0${index}</span></div><div class="kpi-value">${esc(value)}${unit ? `<span class="unit">${esc(unit)}</span>` : ""}</div><p class="kpi-note">${note}</p></article>`;
  }

  function panelHeader(kicker, title, subtitle, tag) {
    return `<div class="panel-header"><div><p class="section-kicker">${esc(kicker)}</p><h2>${esc(title)}</h2>${subtitle ? `<p class="panel-subtitle">${esc(subtitle)}</p>` : ""}</div>${tag ? `<span class="pill">${esc(tag)}</span>` : ""}</div>`;
  }

  function lineChart(rows, key, title, id, isPercent, compactLayout) {
    rows = asArray(rows);
    const values = rows.map(r => valid(r[key]) ? Number(r[key]) : null);
    const finiteValues = values.filter(v => v !== null);
    if (!rows.length || !finiteValues.length) return empty("No defined values to plot for this selection.");
    const W = compactLayout ? 360 : 730, H = compactLayout ? 270 : 254;
    const left = compactLayout ? 42 : 53, right = compactLayout ? 12 : 19, top = 17, bottom = 40;
    const plotW = W - left - right, plotH = H - top - bottom;
    const maxValue = Math.max(...finiteValues, 0);
    const maxY = maxValue > 0 ? maxValue * 1.13 : 1;
    const x = i => left + (rows.length === 1 ? plotW / 2 : i * plotW / (rows.length - 1));
    const y = value => top + plotH - value / maxY * plotH;
    let grid = "";
    for (let i = 0; i <= 4; i++) {
      const value = maxY * i / 4, yp = y(value);
      grid += `<line class="grid-line" x1="${left}" y1="${yp}" x2="${W - right}" y2="${yp}"/><text x="${left - 11}" y="${yp + 4}" text-anchor="end">${esc(isPercent ? value.toFixed(0) + "%" : axisNumber(value))}</text>`;
    }
    let lines = "", path = "", areas = "", segment = [];
    function flush() {
      if (!segment.length) return;
      const d = segment.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ");
      path += d + " ";
      areas += `<path d="${d} L${segment[segment.length - 1][0]},${top + plotH} L${segment[0][0]},${top + plotH} Z" fill="url(#${id}-fill)"/>`;
      segment = [];
    }
    values.forEach((value, i) => { if (value === null) flush(); else segment.push([x(i), y(value)]); });
    flush();
    lines += areas + `<path d="${path}" fill="none" stroke="#177c78" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>`;
    const peakIndex = values.indexOf(maxValue);
    values.forEach((value, i) => {
      if (value === null) return;
      const peak = i === peakIndex && maxValue > 0;
      lines += `<g tabindex="0" aria-label="${esc(monthName(rows[i].month, true) + ": " + (isPercent ? percent(value) : decimal(value)))}"><title>${esc(monthName(rows[i].month, true) + ": " + (isPercent ? percent(value) : decimal(value)))}</title><circle cx="${x(i)}" cy="${y(value)}" r="${peak ? 5 : 3.2}" fill="${peak ? "#c67840" : "#177c78"}" stroke="white" stroke-width="2"/></g>`;
    });
    const step = Math.max(1, Math.ceil(rows.length / (compactLayout ? 4 : 7)));
    let labels = "";
    rows.forEach((r, i) => {
      if (i % step === 0 || i === rows.length - 1) {
        if (i !== rows.length - 1 && rows.length - 1 - i < step / 2) return;
        labels += `<text class="axis-label" x="${x(i)}" y="${H - 15}" text-anchor="middle">${esc(monthName(r.month))}</text>`;
      }
    });
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${esc(title)}</title><desc id="${id}-desc">${esc(`${rows.length} purchase months. Highest displayed value ${isPercent ? percent(maxValue) : decimal(maxValue)}. Exact values are available in the table below.`)}</desc><defs><linearGradient id="${id}-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#82b5a1" stop-opacity=".24"/><stop offset="100%" stop-color="#82b5a1" stop-opacity=".015"/></linearGradient></defs>${grid}${lines}${labels}</svg>`;
  }

  function distributionChart(rows, compactLayout) {
    rows = asArray(rows);
    const W = compactLayout ? 360 : 730, rowH = 39, left = compactLayout ? 115 : 133, right = compactLayout ? 67 : 88, top = 8, H = top + rows.length * rowH + 5;
    const max = Math.max(1, ...rows.map(r => r.orders));
    let shapes = "";
    rows.forEach((r, i) => {
      const label = r.score === null ? "No selected review" : `${r.score} ${r.score === 1 ? "star" : "stars"}`;
      const fill = r.score === null ? "#bdc9bd" : r.score <= 2 ? "#c67840" : "#2b8173";
      const y = top + i * rowH;
      shapes += `<g tabindex="0" aria-label="${esc(label + ": " + number(r.orders) + " orders")}"><title>${esc(label + ": " + number(r.orders) + " orders; " + percent(r.shareOfSalesPct) + " of eligible sales")}</title><text x="${left - 13}" y="${y + 19}" text-anchor="end">${esc(label)}</text><rect x="${left}" y="${y + 3}" width="${W - left - right}" height="23" rx="3" fill="#f1f4ee"/><rect x="${left}" y="${y + 3}" width="${(W - left - right) * r.orders / max}" height="23" rx="3" fill="${fill}"/><text class="bar-value" x="${W - right + 12}" y="${y + 19}">${number(r.orders)}</text></g>`;
    });
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="review-bars-title review-bars-desc"><title id="review-bars-title">Selected review scores</title><desc id="review-bars-desc">Order counts for scores one to five, with missing selected reviews kept in a separate group.</desc>${shapes}</svg>`;
  }

  function table(headers, rows, className) {
    return `<div class="table-scroll ${className || ""}"><table class="rank-table"><thead><tr>${headers.map(h => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(cells => `<tr>${cells.map(cell => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }

  function dataDetails(label, headers, rows) {
    return `<details class="chart-data"><summary>${esc(label)}</summary>${table(headers, rows)}</details>`;
  }

  function rankedName(label, index, share, isState) {
    const name = isState ? `<span class="state-code">${esc(label)}</span>${esc(stateName(label))}` : esc(categoryName(label));
    const bar = valid(share) ? `<span class="rank-bar"><span style="width:${Math.max(0, Math.min(100, share))}%"></span></span>` : "";
    return `<div class="rank-name"><span class="rank-number">${String(index + 1).padStart(2, "0")}</span><span class="rank-label">${name}</span></div>${bar}`;
  }

  function rankPanel(config, options) {
    const rows = asArray(config.rows);
    const expanded = !!(options.expanded && options.expanded[config.id]);
    const limit = config.limit || 6;
    const shown = expanded ? rows : rows.slice(0, limit);
    return `<section class="panel">${panelHeader(config.kicker, config.title, config.subtitle, config.tag)}${rows.length ? table(config.headers, shown.map(config.cells), config.wide ? "wide" : "") : empty()}${config.note ? `<p class="small-note">${config.note}</p>` : ""}<div class="table-footer"><span>${number(shown.length)} of ${number(rows.length)} ${esc(config.noun || "groups")}</span>${rows.length > limit ? `<button type="button" class="text-button" data-expand="${esc(config.id)}" aria-expanded="${expanded}">${expanded ? "Show fewer" : "Show all " + rows.length}</button>` : ""}</div></section>`;
  }

  function salesPage(snapshot, data, options) {
    const s = snapshot.sales;
    const monthly = asArray(s.monthly), categories = asArray(s.categories), states = asArray(s.states);
    const peak = monthly.reduce((best, row) => row.cents > (best ? best.cents : -1) ? row : best, null);
    const leader = categories[0];
    const story = s.orders && peak
      ? `<p class="insight-main"><em>${esc(monthName(peak.month))}</em> leads this selection.</p><p class="insight-copy">${decimal(peak.value)} in product value across ${number(peak.orders)} eligible orders.</p>${leader ? `<div class="mini-stat-row"><span>Largest category<br>${esc(categoryName(leader.label))}</span><strong>${percent(leader.sharePct)}</strong></div>` : ""}`
      : `<p class="insight-main">No eligible sales in this selection.</p><p class="insight-copy">Change the purchase months or buyer state to explore another group of orders.</p>`;
    const charts = `<div class="report-grid"><section class="panel">${panelHeader("ORDER VALUE OVER TIME", "Monthly product value", "By purchase month · eligible delivered orders", monthly.length + " months")}<div class="chart-legend"><span><i class="legend-dot"></i>Product value</span><span><i class="legend-dot orange"></i>Highest month</span></div>${lineChart(monthly, "value", "Monthly product sales value", "sales-trend", false, options.compactCharts)}${dataDetails("View monthly values", ["Purchase month", "Orders", "Product value", "AOV"], monthly.map(r => [esc(monthName(r.month)), number(r.orders), decimal(r.value), decimal(r.aov)]))}</section><aside class="panel insight-panel">${panelHeader("IN THIS SELECTION", "A closer look", "", "")}${story}<p class="insight-footer">Product value reflects recorded item prices. A peak alone does not explain its cause or establish market-wide growth.</p></aside></div>`;
    return `<div class="kpi-grid">${card("Product value", compact(s.value), `<strong>${decimal(s.value)}</strong> source units · excludes freight`, 1)}${card("Eligible orders", number(s.orders), `${number(s.excludedOrders)} selected orders excluded from sales`, 2)}${card("Average order value", decimal(s.aov), "Product value ÷ eligible orders", 3)}${card("Observed customers", number(s.uniqueCustomers), "Persistent identities in eligible sales", 4)}</div>${!s.orders ? `<p class="empty-selection">No eligible sales orders in this selection. Undefined averages are shown as —.</p>` : ""}${charts}<div class="report-grid equal">${rankPanel({ id: "sales-categories", kicker: "CATEGORY MIX", title: "Where product value sits", subtitle: "Ranked by product value", headers: ["Category", "Product value", "Share"], rows: categories, noun: "categories", cells: (r, i) => [rankedName(r.label, i, r.sharePct, false), decimal(r.value), `<span class="rate-badge">${percent(r.sharePct)}</span>`], note: "Unknown and untranslated categories remain included. An order can appear in several categories; category order counts are not additive." }, options)}${rankPanel({ id: "sales-states", kicker: "BUYER LOCATION", title: "Sales by state", subtitle: "Buyer state · ranked by product value", headers: ["State", "Orders", "Product value"], rows: states, noun: "states", cells: (r, i) => [rankedName(r.label, i, null, true), number(r.orders), decimal(r.value)], note: "Location describes the buyer. State totals use each eligible order once." }, options)}</div>`;
  }

  function deliveryPage(snapshot, data, options) {
    const d = snapshot.delivery, monthly = asArray(d.monthly);
    const worst = monthly.filter(r => r.orders > 0).reduce((best, r) => !best || r.lateOrders > best.lateOrders ? r : best, null);
    const story = worst ? `<p class="insight-main"><em>${number(worst.lateOrders)} late orders</em> in ${esc(monthName(worst.month))}.</p><p class="insight-copy">The largest monthly late-order count in this selection: ${number(worst.lateOrders)} of ${number(worst.orders)} eligible orders (${percent(worst.latePct)}).</p>` : `<p class="insight-main">No delivery outcomes to compare.</p><p class="insight-copy">Choose a different period or buyer state.</p>`;
    return `<div class="kpi-grid">${card("Delivery orders", number(d.orders), `${number(d.excludedOrders)} selected orders excluded`, 1)}${card("Late delivery rate", percent(d.latePct), `${number(d.lateOrders)} late / ${number(d.orders)} eligible orders`, 2)}${card("Average duration", decimal(d.averageDays), "Elapsed time from purchase to receipt", 3, "days")}${card("Average positive delay", decimal(d.averagePositiveDelayDays), "Late orders only · beyond promised day", 4, "days")}</div>${!d.orders ? `<p class="empty-selection">No eligible delivery orders in this selection. Rates and averages remain undefined.</p>` : ""}<div class="report-grid"><section class="panel">${panelHeader("THE DELIVERY PROMISE", "Late deliveries over time", "Late-order share by purchase month", "Calendar-day promise")}<div class="chart-legend"><span><i class="legend-dot"></i>Late delivery rate</span><span><i class="legend-dot orange"></i>Highest rate</span></div>${lineChart(monthly, "latePct", "Monthly late delivery rate", "delivery-trend", true, options.compactCharts)}${dataDetails("View monthly values", ["Month", "Eligible", "Late", "Late rate"], monthly.map(r => [esc(monthName(r.month)), number(r.orders), number(r.lateOrders), percent(r.latePct)]))}</section><aside class="panel insight-panel">${panelHeader("IN THIS SELECTION", "Where delays add up", "", "")}${story}<div class="mini-stat-row"><span>On time, including early</span><strong>${number(d.onTimeOrders)}</strong></div><div class="mini-stat-row"><span>Delivered, invalid timing</span><strong>${number(d.invalidDateOrders)}</strong></div><p class="insight-footer">Duration and lateness measure different things. Delivery on the promised calendar day is on time, however long the journey took.</p></aside></div><div class="report-grid equal">${rankPanel({ id: "delivery-states", kicker: "REGIONAL COMPARISON", title: "Late orders by buyer state", subtitle: "Ranked by late-order count", headers: ["State", "Late / eligible", "Late rate"], rows: asArray(d.states), noun: "states", cells: (r, i) => [rankedName(r.label, i, null, true), `${number(r.lateOrders)} / ${number(r.orders)}`, `<span class="rate-badge warm">${percent(r.latePct)}</span>`], note: "A larger late-order count and a higher late rate answer different questions. Neither establishes why a delay happened." }, options)}${rankPanel({ id: "delivery-categories", kicker: "CATEGORY COMPARISON", title: "Delivery by product category", subtitle: "One observation per order and category", headers: ["Category", "Late / eligible", "Late rate"], rows: asArray(d.categories), noun: "categories", cells: (r, i) => [rankedName(r.label, i, null, false), `${number(r.lateOrders)} / ${number(r.orders)}`, `<span class="rate-badge warm">${percent(r.latePct)}</span>`], note: "Orders containing several categories appear in each one. Category counts overlap and must not be added to obtain total orders." }, options)}</div>`;
  }

  function reviewComparison(c) {
    const groups = asArray(c.deliveryComparison);
    const late = groups.find(r => r.key === "late");
    const timingPct = late && late.reviewedOrders ? metricsLibrary.halfUp(late.preDeliveryReviewOrders * 100, late.reviewedOrders) : null;
    const timing = late && late.reviewedOrders
      ? `<strong>${number(late.preDeliveryReviewOrders)} of ${number(late.reviewedOrders)} (${percent(timingPct)})</strong> selected late-group responses were submitted <strong>before delivery</strong>.`
      : "There are no reviewed late orders in this selection, so no timing share can be calculated.";
    return `<section class="panel comparison-panel">${panelHeader("DELIVERY & REVIEWS", "The same orders, two outcomes", "Scores use reviewed orders with valid delivery dates", "Association only")}<div class="comparison-wrap"><div class="table-scroll"><table class="comparison-table"><thead><tr><th scope="col">Delivery group</th><th scope="col">Mean / 5</th><th scope="col">Reviewed / eligible</th><th scope="col">Score 1 or 2</th></tr></thead><tbody>${groups.map(r => `<tr><td>${esc(r.label)}</td><td><span class="score ${r.key === "late" ? "late" : ""}">${decimal(r.averageScore)}</span><div class="score-mini-track ${r.key === "late" ? "late" : ""}"><span style="width:${valid(r.averageScore) ? Math.max(0, Math.min(100, r.averageScore / 5 * 100)) : 0}%"></span></div></td><td>${number(r.reviewedOrders)} / ${number(r.salesOrders)}</td><td>${percent(r.lowScorePct)}<br><small>${number(r.lowScoreOrders)} orders</small></td></tr>`).join("")}</tbody></table><p class="small-note">Missing reviews are excluded from means and low-score rates. Coverage can differ between groups.</p></div><aside class="timing-callout"><h3>Read the response timing first</h3><p>${timing}</p><p class="callout-foot">This is not a post-delivery-only satisfaction measure. The comparison does not establish that lateness caused a score difference.</p></aside></div></section>`;
  }

  function customersPage(snapshot, data, options) {
    const c = snapshot.customers;
    const repeatStory = c.uniqueCustomers
      ? `<p class="insight-main"><em>${percent(c.repeatCustomerPct)}</em> placed at least two eligible orders.</p><p class="insight-copy">${number(c.repeatCustomers)} repeat buyers among ${number(c.uniqueCustomers)} observed customers in the current selection.</p>`
      : `<p class="insight-main">No observed customers in this selection.</p><p class="insight-copy">Expand the purchase months or choose another buyer state.</p>`;
    return `<div class="kpi-grid">${card("Average review", decimal(c.averageScore), `${number(c.reviewedOrders)} selected valid reviews`, 1, "/ 5")}${card("Review coverage", percent(c.reviewCoveragePct), `${number(c.missingReviewOrders)} eligible orders without a selected review`, 2)}${card("Observed repeat buyers", percent(c.repeatCustomerPct), `${number(c.repeatCustomers)} / ${number(c.uniqueCustomers)} customers`, 3)}${card("Low-score share", percent(c.lowScorePct), `${number(c.lowScoreOrders)} reviews scored 1 or 2`, 4)}</div>${!c.salesOrders ? `<p class="empty-selection">No eligible customer orders in this selection. Repeat and review rates remain undefined.</p>` : ""}<div class="report-grid"><section class="panel">${panelHeader("SELECTED REVIEWS", "What the scores look like", "One selected review per eligible order", "Missing stays missing")}${distributionChart(c.distribution, options.compactCharts)}<p class="distribution-caption"><strong>${number(c.reviewedOrders)}</strong> reviewed orders; <strong>${number(c.missingReviewOrders)}</strong> without an eligible selected review. Missing scores are not zero ratings.</p>${dataDetails("View counts and shares", ["Score", "Orders", "% of reviewed", "% of sales"], asArray(c.distribution).map(r => [esc(r.score === null ? "No selected review" : r.score), number(r.orders), percent(r.shareOfReviewedPct), percent(r.shareOfSalesPct)]))}</section><aside class="panel insight-panel">${panelHeader("OBSERVED PURCHASING", "Who bought again?", "", "")}${repeatStory}<div class="mini-stat-row"><span>One eligible order</span><strong>${number(c.oneTimeCustomers)}</strong></div><div class="mini-stat-row"><span>Orders from repeat buyers</span><strong>${number(c.repeatOrders)}</strong></div><p class="insight-footer">This is not retention or loyalty. Same-day orders count; later buyers have less observation time. Repeat status is recalculated for the selected months and buyer state.</p></aside></div>${reviewComparison(c)}<div class="report-grid equal">${rankPanel({ id: "customer-states", kicker: "BUYER LOCATION", title: "Where low scores add up", subtitle: "Ranked by count of selected scores 1 or 2", headers: ["State", "Low / reviewed", "Low-score share"], rows: asArray(c.states), noun: "states", cells: (r, i) => [rankedName(r.label, i, null, true), `${number(r.lowScoreOrders)} / ${number(r.reviewedOrders)}`, `<span class="rate-badge warm">${percent(r.lowScorePct)}</span>`], note: "Keep counts and reviewed-order denominators together. See the CSV for review coverage in each state." }, options)}${rankPanel({ id: "customer-spending", kicker: "OBSERVED SPENDING", title: "Highest product spending", subtitle: "Top 20 after grouping all selected customers", headers: ["Customer", "Orders", "Product value"], rows: asArray(c.topSpenders), noun: "reported customers", limit: 6, cells: (r, i) => [`<div class="rank-name"><span class="rank-number">${String(i + 1).padStart(2, "0")}</span><span class="customer-tag">${esc(r.label)}</span></div>`, number(r.orders), decimal(r.value)], note: "Labels are anonymous. Spending covers this selection and excludes freight; it is not customer lifetime value." }, options)}</div>`;
  }

  function renderPage(page, snapshot, data, options) {
    if (!PAGES[page]) throw new Error("Unknown report page");
    options = options || {};
    return (page === "sales" ? salesPage : page === "delivery" ? deliveryPage : customersPage)(snapshot, data, options);
  }

  function csvCell(value) {
    if (value == null) return "";
    let text = String(value);
    if (typeof value === "string" && /^[=+@\-]/.test(text)) text = "'" + text;
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }

  function buildCsv(page, snapshot, data) {
    if (!PAGES[page]) throw new Error("Unknown report page");
    const f = filterLabels(snapshot, data);
    const rows = [["section", "dimension", "metric", "value", "unit", "from_month", "through_month", "buyer_state"]];
    const add = (section, dimension, metric, value, unit) => rows.push([section, dimension, metric, value, unit || "count", f.start, f.end, f.state]);
    const fields = (section, label, obj, pairs) => pairs.forEach(([key, unit]) => add(section, label, key, obj[key], unit));
    if (page === "sales") {
      const s = snapshot.sales;
      fields("headline", "selection", s, [["orders"], ["excludedOrders"], ["cents", "integer hundredths"], ["value", "source monetary units"], ["aov", "source monetary units per order"], ["uniqueCustomers"]]);
      asArray(s.monthly).forEach(r => fields("monthly_sales", r.month, r, [["allOrders"], ["orders"], ["excludedOrders"], ["cents", "integer hundredths"], ["value", "source monetary units"], ["aov", "source monetary units per order"]]));
      asArray(s.categories).forEach(r => fields("category_sales", r.label, r, [["orders"], ["itemCount"], ["cents", "integer hundredths"], ["value", "source monetary units"], ["sharePct", "percent"]]));
      asArray(s.states).forEach(r => fields("regional_sales", r.label, r, [["orders"], ["cents", "integer hundredths"], ["value", "source monetary units"], ["aov", "source monetary units per order"], ["sharePct", "percent"]]));
    } else if (page === "delivery") {
      const d = snapshot.delivery;
      const keys = [["orders"], ["lateOrders"], ["onTimeOrders"], ["latePct", "percent"], ["averageDays", "elapsed days"], ["averagePositiveDelayDays", "calendar days"]];
      fields("headline", "selection", d, keys.concat([["excludedOrders"], ["nonDeliveredOrders"], ["invalidDateOrders"]]));
      asArray(d.monthly).forEach(r => fields("monthly_delivery", r.month, r, keys));
      asArray(d.states).forEach(r => fields("regional_delivery", r.label, r, keys));
      asArray(d.categories).forEach(r => fields("category_delivery", r.label, r, keys));
    } else {
      const c = snapshot.customers;
      fields("headline", "selection", c, [["salesOrders"], ["reviewedOrders"], ["missingReviewOrders"], ["reviewCoveragePct", "percent"], ["averageScore", "score out of 5"], ["lowScoreOrders"], ["lowScorePct", "percent"], ["uniqueCustomers"], ["repeatCustomers"], ["repeatCustomerPct", "percent"], ["oneTimeCustomers"], ["repeatOrders"], ["repeatCents", "integer hundredths"]]);
      asArray(c.distribution).forEach(r => fields("review_distribution", r.label, r, [["orders"], ["shareOfSalesPct", "percent"], ["shareOfReviewedPct", "percent"]]));
      const reviewKeys = [["salesOrders"], ["reviewedOrders"], ["missingReviewOrders"], ["reviewCoveragePct", "percent"], ["averageScore", "score out of 5"], ["lowScoreOrders"], ["lowScorePct", "percent"]];
      asArray(c.deliveryComparison).forEach(r => fields("delivery_reviews", r.label, r, reviewKeys.concat([["preDeliveryReviewOrders"]])));
      asArray(c.states).forEach(r => fields("regional_reviews", r.label, r, reviewKeys));
      asArray(c.topSpenders).forEach(r => fields("top_customer_spending", r.label, r, [["orders"], ["cents", "integer hundredths"], ["value", "source monetary units"], ["aov", "source monetary units per order"], ["reviewedOrders"], ["averageScore", "score out of 5"], ["reviewCoveragePct", "percent"]]));
    }
    return rows.map(row => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
  }

  function init(options) {
    options = options || {};
    const doc = options.doc || root.document, win = options.win || root;
    const data = options.data || root.OLIST_DATA, metrics = options.metrics || root.OlistMetrics;
    if (!doc) throw new Error("A document is required to initialize the report");
    const byId = id => doc.getElementById(id);
    const report = byId("report");
    if (!report) throw new Error("Report container is missing");
    if (!data || !metrics || typeof metrics.compute !== "function" || !Array.isArray(data.months) || !data.months.length) {
      report.innerHTML = `<div class="error-card"><h2>The report could not load</h2><p>For the downloaded version, keep index.html, data.js, metrics.js, app.js and styles.css together, then reopen index.html. The project repository also contains the validated result tables.</p></div>`;
      report.setAttribute("aria-busy", "false");
      return null;
    }
    const controls = { from: byId("month-from"), to: byId("month-to"), state: byId("buyer-state"), reset: byId("reset"), download: byId("download") };
    const defaultFilters = { startMonth: 0, endMonth: data.months.length - 1, state: "all" };
    let filters = { ...defaultFilters }, page = "sales", snapshot, expanded = {};
    let compactCharts = (win.innerWidth || 1280) <= 680;
    const hash = win.location ? String(win.location.hash).replace(/^#/, "") : "";
    if (PAGES[hash]) page = hash;
    const monthOptions = data.months.map((m, i) => `<option value="${i}">${esc(monthName(m))}</option>`).join("");
    controls.from.innerHTML = monthOptions;
    controls.to.innerHTML = monthOptions;
    controls.state.innerHTML = `<option value="all">All buyer states</option>` + data.states.map((s, i) => `<option value="${i}">${esc(s === stateName(s) ? s : s + " · " + stateName(s))}</option>`).join("");
    [controls.from, controls.to, controls.state, controls.download].forEach(el => { el.disabled = false; });

    function normalizeFilters(next) {
      let startMonth = Number(next.startMonth), endMonth = Number(next.endMonth);
      if (!Number.isInteger(startMonth) || !Number.isInteger(endMonth)) throw new Error("Month filters must be integer indexes");
      startMonth = Math.min(data.months.length - 1, Math.max(0, startMonth));
      endMonth = Math.min(data.months.length - 1, Math.max(0, endMonth));
      if (startMonth > endMonth) endMonth = startMonth;
      let state = next.state;
      if (state !== "all") {
        state = Number(state);
        if (!Number.isInteger(state) || state < 0 || state >= data.states.length) throw new Error("Unknown buyer state");
      }
      return { startMonth, endMonth, state };
    }

    function draw() {
      const f = filterLabels(snapshot, data);
      byId("page-title").textContent = PAGES[page].title;
      byId("page-subtitle").textContent = PAGES[page].subtitle;
      doc.title = PAGES[page].title + " | Olist Commerce review";
      byId("selection-summary").textContent = `${f.months} ${f.months === 1 ? "month" : "months"} · ${f.state === "All buyer states" ? f.state : stateName(f.state)}`;
      byId("period-label").textContent = `Purchases: ${monthName(f.start, true)}${f.start === f.end ? "" : " — " + monthName(f.end, true)} · ${f.state}`;
      byId("unit-note").textContent = page === "delivery" ? "Final observed outcomes · promise uses calendar dates" : "Source monetary units · product value excludes freight";
      controls.from.value = String(filters.startMonth);
      controls.to.value = String(filters.endMonth);
      controls.state.value = String(filters.state);
      controls.reset.disabled = filters.startMonth === 0 && filters.endMonth === defaultFilters.endMonth && filters.state === "all";
      doc.querySelectorAll("[data-page]").forEach(el => {
        if (el.getAttribute("data-page") === page) el.setAttribute("aria-current", "page");
        else el.removeAttribute("aria-current");
      });
      report.innerHTML = renderPage(page, snapshot, data, { expanded, compactCharts });
      report.setAttribute("aria-busy", "false");
      byId("announcement").textContent = `${PAGES[page].title} updated. ${monthName(f.start)} through ${monthName(f.end)}. ${f.state}.`;
    }

    function setFilters(next) {
      filters = normalizeFilters({ ...filters, ...next });
      expanded = {};
      report.setAttribute("aria-busy", "true");
      snapshot = metrics.compute(data, filters);
      draw();
      return snapshot;
    }

    function setPage(nextPage, updateHash) {
      if (!PAGES[nextPage]) throw new Error("Unknown report page");
      page = nextPage;
      if (updateHash && win.location && win.location.hash !== "#" + page) win.location.hash = page;
      draw();
      return snapshot;
    }

    function reset() { return setFilters(defaultFilters); }

    function download() {
      const f = filterLabels(snapshot, data);
      const content = "\uFEFF" + buildCsv(page, snapshot, data);
      const name = `olist-${page}-${f.start}-to-${f.end}-${filters.state === "all" ? "all-states" : f.state.replace(/[^a-z0-9]+/gi, "-")}.csv`;
      const BlobType = win.Blob || root.Blob, URLType = win.URL || root.URL;
      const blob = new BlobType([content], { type: "text/csv;charset=utf-8;" });
      const url = URLType.createObjectURL(blob);
      const link = doc.createElement("a");
      link.href = url;
      link.download = name;
      link.hidden = true;
      doc.body.appendChild(link);
      link.click();
      link.remove();
      (win.setTimeout || root.setTimeout)(() => URLType.revokeObjectURL(url), 1000);
      byId("announcement").textContent = `Downloaded ${PAGES[page].title.toLowerCase()} for the current filters.`;
      return { filename: name, csv: content };
    }

    controls.from.addEventListener("change", () => {
      const startMonth = Number(controls.from.value);
      setFilters({ startMonth, endMonth: Math.max(startMonth, filters.endMonth) });
    });
    controls.to.addEventListener("change", () => {
      const endMonth = Number(controls.to.value);
      setFilters({ startMonth: Math.min(filters.startMonth, endMonth), endMonth });
    });
    controls.state.addEventListener("change", () => setFilters({ state: controls.state.value }));
    controls.reset.addEventListener("click", reset);
    controls.download.addEventListener("click", download);
    doc.querySelectorAll("[data-page]").forEach(el => el.addEventListener("click", event => {
      event.preventDefault();
      setPage(el.getAttribute("data-page"), true);
    }));
    report.addEventListener("click", event => {
      const button = event.target.closest ? event.target.closest("[data-expand]") : null;
      if (!button) return;
      const id = button.getAttribute("data-expand");
      expanded[id] = !expanded[id];
      draw();
      const replacement = report.querySelector(`[data-expand="${id}"]`);
      if (replacement && replacement.focus) replacement.focus();
    });
    if (win.addEventListener) win.addEventListener("hashchange", () => {
      const nextPage = String(win.location.hash).replace(/^#/, "");
      if (PAGES[nextPage] && nextPage !== page) setPage(nextPage, false);
    });
    if (win.addEventListener) win.addEventListener("resize", () => {
      const nextCompact = (win.innerWidth || 1280) <= 680;
      if (nextCompact !== compactCharts) { compactCharts = nextCompact; draw(); }
    });
    setFilters(defaultFilters);
    return { setPage, setFilters, reset, download, getState: () => ({ page, filters: { ...filters }, snapshot }) };
  }

  const api = { renderPage, buildCsv, init, PAGES, format: { number, decimal, percent, compact, monthName, categoryName, stateName }, filterLabels };
  root.OlistDashboard = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root.document) {
    const start = () => {
      try { api.controller = init(); }
      catch (error) {
        const report = root.document.getElementById("report");
        if (report) { report.innerHTML = `<div class="error-card"><h2>The report could not be prepared</h2><p>Reopen the page with all dashboard files available, or review the validated tables in the project repository.</p></div>`; report.setAttribute("aria-busy", "false"); }
        if (root.console) root.console.error(error);
      }
    };
    if (root.document.readyState === "loading") root.document.addEventListener("DOMContentLoaded", start, { once: true });
    else start();
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
