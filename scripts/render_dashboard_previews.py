#!/usr/bin/env python3
"""Render three static data previews from the dashboard's actual default metrics.

Run from the repository with: python3 scripts/render_dashboard_previews.py
Node evaluates the same data and metric modules as the dashboard. These SVGs are
data illustrations, not browser screenshots or evidence of browser testing.
The renderer uses Python's standard library and writes only the three SVG files.
"""

import html
import json
import math
from pathlib import Path
import subprocess


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / "dashboard" / "screenshots"
WIDTH, HEIGHT = 1400, 1040
COLORS = {
    "navy": "#173c43", "teal": "#177c78", "muted": "#6a7b7c",
    "background": "#f6f7f3", "paper": "#ffffff", "rule": "#e1e7e0",
    "soft": "#e7f2ec", "amber": "#c67840", "soft_amber": "#fcf0e4",
}
SOURCE = "https://github.com/M980-221/ecommerce-sql-consulting-case-study"


def escape(value):
    return html.escape(str(value), quote=True)


def number(value, places=0):
    return "—" if value is None else f"{value:,.{places}f}"


def percentage(value):
    return number(value, 2) + "%" if value is not None else "—"


def human_label(value):
    return str(value).replace("_", " ")


class Canvas:
    def __init__(self, title, description):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
            f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="description">{escape(description)}</desc>',
            '<style>text{font-family:Inter,Aptos,"Segoe UI",Arial,sans-serif;font-variant-numeric:tabular-nums}</style>',
        ]
        self.rect(0, 0, WIDTH, HEIGHT, COLORS["background"])

    def rect(self, x, y, width, height, fill, radius=0, stroke=None):
        outline = f' stroke="{stroke}"' if stroke else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                          f'rx="{radius}" fill="{fill}"{outline}/>')

    def text(self, x, y, value, size=14, color=None, weight=400, anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" '
                          f'font-weight="{weight}" text-anchor="{anchor}" '
                          f'fill="{color or COLORS["navy"]}">{escape(value)}</text>')

    def line(self, x1, y1, x2, y2, color=None, width=1):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                          f'stroke="{color or COLORS["rule"]}" stroke-width="{width}"/>')

    def begin_group(self, label):
        self.parts.append(f'<g role="group" aria-label="{escape(label)}"><title>{escape(label)}</title>')

    def end_group(self):
        self.parts.append("</g>")

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n", encoding="utf-8")


def frame(page, title, subtitle, description):
    canvas = Canvas(title + " — Olist static data preview", description)
    canvas.rect(64, 29, 9, 24, COLORS["teal"], 2)
    canvas.text(85, 47, "OLIST  /  E-COMMERCE ANALYSIS", 14, weight=700)
    canvas.text(1336, 47, "Mohammed Baquaysh  ·  SQL portfolio", 13, COLORS["muted"], anchor="end")
    canvas.line(64, 72, 1336, 72)
    canvas.text(64, 125, title, 36, weight=700)
    canvas.text(64, 156, subtitle, 15, COLORS["muted"])
    canvas.rect(938, 95, 398, 34, COLORS["soft"], 17)
    canvas.text(1137, 117, "Static data preview · Full reporting window", 12,
                COLORS["teal"], 700, "middle")
    for index, label in enumerate(("Sales", "Delivery", "Customers")):
        x = 64 + index * 143
        active = label.lower() == page
        canvas.text(x, 203, label, 15, COLORS["teal"] if active else COLORS["muted"],
                    700 if active else 400)
        if active:
            canvas.line(x, 213, x + 90, 213, COLORS["teal"], 3)
    canvas.text(1336, 203, "Purchases: 1 Feb 2017 – 31 Jul 2018", 13,
                COLORS["muted"], anchor="end")
    canvas.line(64, 228, 1336, 228)
    canvas.line(64, 987, 1336, 987)
    canvas.text(64, 1012, "Source: validated Olist SQL case study · Current dashboard data", 12,
                COLORS["muted"])
    canvas.parts.append(f'<a href="{SOURCE}">')
    canvas.text(1336, 1012, "github.com/M980-221/ecommerce-sql-consulting-case-study", 12,
                COLORS["teal"], anchor="end")
    canvas.parts.append("</a>")
    return canvas


def kpi(canvas, index, label, value, note, secondary=None):
    x = 64 + index * 324
    canvas.rect(x, 250, 300, 124, COLORS["paper"], 10, COLORS["rule"])
    canvas.text(x + 22, 278, label.upper(), 11, COLORS["muted"], 700)
    canvas.text(x + 22, 323, value, 31 if len(value) > 11 else 35, weight=700)
    canvas.text(x + 22, 349, note, 11, COLORS["muted"])
    if secondary:
        canvas.text(x + 278, 349, secondary, 11, COLORS["teal"], anchor="end")


def panel(canvas, x, width, title, subtitle):
    canvas.rect(x, 398, width, 428, COLORS["paper"], 12, COLORS["rule"])
    canvas.text(x + 24, 433, title, 20, weight=700)
    canvas.text(x + 24, 459, subtitle, 12, COLORS["muted"])


def nice_max(value):
    if not value:
        return 1
    power = 10 ** math.floor(math.log10(value))
    return math.ceil(value / power * 2) / 2 * power


def monthly_chart(canvas, rows, field, title, subtitle, unit):
    panel(canvas, 64, 752, title, subtitle)
    values = [row[field] for row in rows]
    if not rows or any(value is None for value in values):
        raise ValueError("Default monthly preview requires complete monthly measures")
    x, y, width, height = 125, 498, 653, 226
    maximum = nice_max(max(values))
    for step in range(5):
        value = maximum * step / 4
        py = y + height - height * step / 4
        canvas.line(x, py, x + width, py)
        label = f"{value / 1000000:.2f}m" if unit == "money" else f"{value:g}%"
        canvas.text(x - 14, py + 4, label, 11, COLORS["muted"], anchor="end")
    points = [(x + i * width / max(len(rows) - 1, 1), y + height * (1 - value / maximum))
              for i, value in enumerate(values)]
    area = [(points[0][0], y + height)] + points + [(points[-1][0], y + height)]
    canvas.parts.append('<polygon points="' + " ".join(f"{px:.2f},{py:.2f}" for px, py in area)
                        + f'" fill="{COLORS["soft"]}"/>')
    canvas.parts.append('<polyline points="' + " ".join(f"{px:.2f},{py:.2f}" for px, py in points)
                        + f'" fill="none" stroke="{COLORS["teal"]}" stroke-width="3" '
                        'stroke-linejoin="round" stroke-linecap="round"/>')
    for index, (row, (px, py)) in enumerate(zip(rows, points)):
        exact = number(row[field], 2) + ("%" if unit == "percent" else " source units")
        canvas.begin_group(f'{row["month"]}: {exact}')
        canvas.parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4" '
                            f'fill="{COLORS["paper"]}" stroke="{COLORS["teal"]}" stroke-width="2"/>')
        canvas.end_group()
        if index % 3 == 0 or index == len(rows) - 1:
            year, month = row["month"].split("-")
            month_name = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[int(month) - 1]
            canvas.text(px, 750, month_name + " " + year[2:], 11, COLORS["muted"], anchor="middle")
    peak = max(range(len(rows)), key=lambda index: values[index])
    peak_label = percentage(values[peak]) if unit == "percent" else number(values[peak], 2)
    canvas.text(points[peak][0], max(points[peak][1] - 15, 485), peak_label, 12,
                COLORS["teal"], 700, "middle")
    canvas.text(88, 791, "Each point is one purchase month; outcomes use the final source snapshot.",
                11, COLORS["muted"])


def horizontal_chart(canvas, rows, field, title, subtitle, unit, count_field=None):
    panel(canvas, 840, 496, title, subtitle)
    shown = rows[:5]
    maximum = max(row[field] for row in shown) if shown else 1
    for index, row in enumerate(shown):
        y = 499 + index * 56
        label = human_label(row["label"])
        value = number(row[field], 2 if unit == "money" else 0)
        detail = "" if count_field is None else f' · {percentage(row[count_field])} late'
        canvas.begin_group(f"{label}: {value}{' source units' if unit == 'money' else ' orders'}{detail}")
        canvas.text(864, y, label, 12, weight=700)
        canvas.text(1312, y, value, 12, anchor="end")
        canvas.rect(864, y + 11, 448, 9, COLORS["soft"], 4)
        canvas.rect(864, y + 11, 448 * row[field] / maximum if maximum else 0,
                    9, COLORS["teal"], 4)
        if count_field is not None:
            canvas.text(1312, y + 36, percentage(row[count_field]) + " late", 11,
                        COLORS["muted"], anchor="end")
        canvas.end_group()
    canvas.text(864, 804, "Largest totals shown; group sizes matter.", 11, COLORS["muted"])


def note(canvas, heading, lines, warning=False):
    canvas.rect(64, 850, 1272, 116, COLORS["soft_amber"] if warning else COLORS["soft"], 10)
    canvas.rect(64, 865, 4, 86, COLORS["amber"] if warning else COLORS["teal"], 2)
    canvas.text(88, 878, heading, 15, weight=700)
    for index, line in enumerate(lines):
        canvas.text(88, 904 + index * 22, line, 13, COLORS["muted"])


def sales_preview(metrics):
    sales = metrics["sales"]
    canvas = frame("sales", "Sales performance", "Product value, order volume and the categories behind sales.",
                   "Static data preview of sales measures, computed from the current dashboard modules for the full reporting window. "
                   "Monetary values are source units, excluding freight; they are not commission revenue or profit.")
    kpi(canvas, 0, "Product sales value", number(sales["value"], 2), "Source monetary units · excludes freight")
    kpi(canvas, 1, "Sales orders", number(sales["orders"]), "Delivered orders with qualifying items")
    kpi(canvas, 2, "Average order value", number(sales["aov"], 2), "Product sales value ÷ sales orders")
    kpi(canvas, 3, "Customers", number(sales["uniqueCustomers"]), "Distinct persistent customer IDs")
    monthly_chart(canvas, sales["monthly"], "value", "Product sales by month",
                  "Source monetary units · 18 calendar months", "money")
    horizontal_chart(canvas, sales["categories"], "value", "Leading categories",
                     "Top five by product sales value", "money")
    note(canvas, "Read the sales figures in context", [
        f'{number(sales["excludedOrders"])} period orders are excluded by the sales rule. All source records remain available.',
        "Sales use item prices, exclude freight and retain source payment differences; payment totals do not redefine sales.",
        "This static preview shows the full window. The live dashboard recalculates its supported filters.",
    ])
    return canvas


def delivery_preview(metrics):
    delivery = metrics["delivery"]
    canvas = frame("delivery", "Delivery performance", "How often orders arrived late, and where the late-order totals are concentrated.",
                   "Static data preview of eligible delivered orders for the full reporting window. Lateness compares calendar dates. "
                   "Delivery duration is elapsed time; positive delay averages late orders only.")
    kpi(canvas, 0, "Eligible deliveries", number(delivery["orders"]), "Valid purchase, receipt and promise dates")
    kpi(canvas, 1, "Late delivery rate", percentage(delivery["latePct"]), number(delivery["lateOrders"]) + " late orders")
    kpi(canvas, 2, "Delivery duration", number(delivery["averageDays"], 2) + " days", "Average elapsed purchase-to-receipt time")
    kpi(canvas, 3, "Delay when late", number(delivery["averagePositiveDelayDays"], 2) + " days", "Average positive calendar-day delay")
    monthly_chart(canvas, delivery["monthly"], "latePct", "Late delivery by month",
                  "Percentage of eligible delivered orders", "percent")
    horizontal_chart(canvas, delivery["states"], "lateOrders", "Late orders by buyer state",
                     "Top five by late-order count; rate shown below", "count", "latePct")
    note(canvas, "A late-order total is a starting point for investigation", [
        f'{number(delivery["excludedOrders"])} period orders are excluded: {number(delivery["nonDeliveredOrders"])} non-delivered and '
        f'{number(delivery["invalidDateOrders"])} delivered orders without valid endpoint dates.',
        "An order received on its promised calendar day is on time. State results describe the buyer location, not a cause of delay.",
        "Monthly outcomes use final observed deliveries, including receipts after the purchase window.",
    ])
    return canvas


def review_distribution(canvas, rows):
    panel(canvas, 64, 752, "Selected review scores", "One selected valid review per reviewed sales order")
    x, baseline, plot_width, plot_height = 114, 727, 654, 218
    maximum = max(20000, math.ceil(max(row["orders"] for row in rows) / 20000) * 20000)
    for step in range(5):
        value = maximum * step / 4
        py = baseline - plot_height * step / 4
        canvas.line(x, py, x + plot_width, py)
        canvas.text(x - 12, py + 4, number(value / 1000, 0) + "k", 11,
                    COLORS["muted"], anchor="end")
    step_width = plot_width / len(rows)
    for index, row in enumerate(rows):
        center = x + (index + 0.5) * step_width
        height = row["orders"] / maximum * plot_height
        canvas.begin_group(f'{row["score"]} stars: {number(row["orders"])} reviews; '
                           f'{percentage(row["shareOfReviewedPct"])} of reviewed orders')
        canvas.rect(center - 35, baseline - height, 70, height,
                    COLORS["amber"] if row["score"] <= 2 else COLORS["teal"], 4)
        canvas.text(center, baseline - height - 12, number(row["orders"]), 12, weight=700, anchor="middle")
        canvas.text(center, 752, str(row["score"]) + (" star" if row["score"] == 1 else " stars"),
                    12, COLORS["muted"], anchor="middle")
        canvas.end_group()
    canvas.text(88, 791, "Low scores are 1 or 2. Orders without an eligible review remain excluded here.",
                11, COLORS["muted"])


def review_comparison(canvas, rows):
    panel(canvas, 840, 496, "Delivery and reviews", "Average selected score · reviewed orders only")
    shown = [row for row in rows if row["key"] in ("on_time", "late")]
    if len(shown) != 2:
        raise ValueError("Expected on_time and late review-comparison groups")
    shown.sort(key=lambda row: row["key"] != "on_time")
    for index, row in enumerate(shown):
        y = 506 + index * 115
        score = row["averageScore"]
        label = "On-time deliveries" if row["key"] == "on_time" else "Late deliveries"
        canvas.begin_group(f'{label}: average score {number(score, 2)} out of 5 across '
                           f'{number(row["reviewedOrders"])} reviewed orders; '
                           f'{number(row["preDeliveryReviewOrders"])} selected responses precede receipt')
        canvas.text(864, y, label, 14, weight=700)
        canvas.text(1312, y, number(score, 2) + " / 5", 16, weight=700, anchor="end")
        canvas.rect(864, y + 18, 448, 20, COLORS["soft"], 4)
        canvas.rect(864, y + 18, 448 * score / 5, 20,
                    COLORS["teal"] if row["key"] == "on_time" else COLORS["amber"], 4)
        canvas.text(864, y + 61, number(row["reviewedOrders"]) + " reviewed orders", 12,
                    COLORS["muted"])
        canvas.end_group()
    canvas.text(864, 778, "Descriptive association; review timing varies.", 11, COLORS["muted"])
    canvas.text(864, 798, "This does not establish a causal effect.", 11, COLORS["muted"])


def customers_preview(metrics):
    customers = metrics["customers"]
    canvas = frame("customers", "Customers and reviews", "Observed repeat purchases and selected review scores across the reporting window.",
                   "Static data preview for customers with eligible sales. Repeat means at least two eligible orders in the window, "
                   "including same-day purchases; this is not a retention or churn measure. Review comparisons are descriptive.")
    kpi(canvas, 0, "Customers", number(customers["uniqueCustomers"]), "Distinct persistent customer IDs")
    kpi(canvas, 1, "Observed repeat rate", percentage(customers["repeatCustomerPct"]),
        number(customers["repeatCustomers"]) + " customers with 2+ eligible orders")
    kpi(canvas, 2, "Average review score", number(customers["averageScore"], 2) + " / 5",
        number(customers["reviewedOrders"]) + " reviewed sales orders")
    kpi(canvas, 3, "Low-score share", percentage(customers["lowScorePct"]),
        "Scores 1–2 among reviewed sales orders")
    review_distribution(canvas, [row for row in customers["distribution"] if row["score"] is not None])
    review_comparison(canvas, customers["deliveryComparison"])
    late = next(row for row in customers["deliveryComparison"] if row["key"] == "late")
    note(canvas, "Keep review timing and customer follow-up visible", [
        f'{number(customers["missingReviewOrders"])} sales orders have no eligible selected review; review coverage is '
        f'{percentage(customers["reviewCoveragePct"])}.',
        f'{number(late["preDeliveryReviewOrders"])} of {number(late["reviewedOrders"])} selected responses on reviewed late orders '
        "were submitted before receipt.",
        "Repeat purchasing is observed within this window; later purchasers have less time to buy again.",
    ], warning=True)
    return canvas


def main():
    script = "require(process.argv[1]); const api=require(process.argv[2]); console.log(JSON.stringify(api.compute(globalThis.OLIST_DATA)));"
    run = subprocess.run(["node", "-e", script, str(PROJECT / "dashboard/data.js"),
                          str(PROJECT / "dashboard/metrics.js")], check=True, capture_output=True, text=True)
    metrics = json.loads(run.stdout)
    previews = {"sales": sales_preview(metrics), "delivery": delivery_preview(metrics),
                "customers": customers_preview(metrics)}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for page, canvas in previews.items():
        path = OUTPUT / (page + "-preview.svg")
        canvas.save(path)
        print(path.relative_to(PROJECT))


if __name__ == "__main__":
    main()
