"""Recalculate sales reports from raw rows using Python grouping and Decimal.

This deliberately avoids the project's views and reporting SQL. It provides a
second calculation of every aggregate, including category and state totals.
"""

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re


REPORTING_START = "2017-02-01"
REPORTING_END = "2018-08-01"
MONEY_PATTERN = re.compile(r"[0-9]{1,9}(?:\.[0-9]{1,2})?\Z")
TWO_PLACES = Decimal("0.01")


def display(value):
    """Round only at the output boundary; keep intermediate maths exact."""
    if value is None:
        return None
    return float(Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def divide(numerator, denominator):
    return Decimal(numerator) / Decimal(denominator) if denominator else None


def growth(current, previous):
    if current is None or previous is None or previous == 0:
        return None
    return display((current - previous) / previous * 100)


def as_cents(raw):
    value = (raw or "").strip()
    if not MONEY_PATTERN.fullmatch(value):
        raise ValueError("Invalid raw item price: {!r}".format(raw))
    return int(Decimal(value) * 100)


def unique_lookup(rows, name):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError("Duplicate {} key: {!r}".format(name, key))
        result[key] = value
    return result


def build_expected(connection):
    """Return the five expected reports and population counts.

    The connection can be read-only. Only raw tables are read, with no SQL
    aggregation or joins. Invalid item prices stop validation, as in Part 3.
    """
    translation = unique_lookup(
        ((str(source).strip(), (target or "").strip() or None)
         for source, target in connection.execute(
             "SELECT product_category_name, product_category_name_english "
             "FROM category_translation")),
        "translation",
    )
    raw_products = unique_lookup(
        connection.execute("SELECT product_id, product_category_name FROM products"),
        "product",
    )
    product_labels = {}
    for product_id, raw_category in raw_products.items():
        category = (raw_category or "").strip()
        if not category:
            label = "Unknown category"
        elif translation.get(category):
            label = translation[category]
        else:
            label = "Untranslated: " + category
        product_labels[product_id] = label

    customer_states = unique_lookup(
        ((customer_id, (state or "").strip().upper() or "Unknown state")
         for customer_id, state in connection.execute(
             "SELECT customer_id, customer_state FROM customers")),
        "customer",
    )

    items_by_order = defaultdict(list)
    for order_id, product_id, price in connection.execute(
            "SELECT order_id, product_id, price FROM order_items"):
        items_by_order[order_id].append((product_id, as_cents(price)))

    month_names = ["{}-{:02d}".format(year, month)
                   for year in (2017, 2018) for month in range(1, 13)
                   if REPORTING_START[:7] <= "{}-{:02d}".format(year, month)
                   < REPORTING_END[:7]]
    month_counts = Counter({month: 0 for month in month_names})
    month_sales_counts = Counter({month: 0 for month in month_names})
    month_values = Counter({month: 0 for month in month_names})
    status_counts = Counter()
    category_values, category_items = Counter(), Counter()
    category_orders = defaultdict(set)
    state_values, state_orders = Counter(), Counter()
    seen_orders, eligible_orders = set(), set()
    missing_items_delivered = 0
    source_orders = 0

    for order_id, customer_id, status, purchased in connection.execute(
            "SELECT order_id, customer_id, order_status, "
            "order_purchase_timestamp FROM orders"):
        source_orders += 1
        if order_id in seen_orders:
            raise ValueError("Duplicate order key: {!r}".format(order_id))
        seen_orders.add(order_id)
        purchased = (purchased or "").strip()
        if not purchased:
            continue
        parsed = datetime.strptime(purchased, "%Y-%m-%d %H:%M:%S")
        if parsed.strftime("%Y-%m-%d %H:%M:%S") != purchased:
            raise ValueError("Invalid purchase timestamp: {!r}".format(purchased))
        if not REPORTING_START <= purchased < REPORTING_END:
            continue
        month = purchased[:7]
        month_counts[month] += 1
        status = (status or "").strip().lower() or "Unknown status"
        status_counts[status] += 1
        if status != "delivered":
            continue
        items = items_by_order.get(order_id)
        if not items:
            missing_items_delivered += 1
            continue
        eligible_orders.add(order_id)
        value = sum(cents for _, cents in items)
        month_sales_counts[month] += 1
        month_values[month] += value
        state = customer_states.get(customer_id, "Unknown state")
        state_orders[state] += 1
        state_values[state] += value
        for product_id, cents in items:
            label = product_labels.get(product_id, "Unknown category")
            category_values[label] += cents
            category_items[label] += 1
            category_orders[label].add(order_id)

    total_cents = sum(month_values.values())
    sales_count = len(eligible_orders)
    period_count = sum(month_counts.values())
    monthly_sales, monthly_growth = [], []
    previous_value, previous_count, previous_aov = None, None, None
    for month in month_names:
        count, value = month_sales_counts[month], month_values[month]
        aov = divide(value, count * 100)
        monthly_sales.append({
            "month": month,
            "all_period_orders": month_counts[month],
            "sales_orders": count,
            "excluded_orders": month_counts[month] - count,
            "product_sales_cents": value,
            "product_sales_value": display(Decimal(value) / 100),
            "average_order_value": display(aov),
        })
        monthly_growth.append({
            "month": month,
            "sales_orders": count,
            "product_sales_cents": value,
            "product_sales_value": display(Decimal(value) / 100),
            "average_order_value": display(aov),
            "previous_month_product_sales_cents": previous_value,
            "previous_month_sales_orders": previous_count,
            "previous_month_average_order_value": display(previous_aov),
            "product_sales_mom_pct": growth(Decimal(value), previous_value),
            "orders_mom_pct": growth(Decimal(count), previous_count),
            "aov_mom_pct": growth(aov, previous_aov),
        })
        previous_value, previous_count, previous_aov = value, count, aov

    comparable_periods = []
    previous_value, previous_count, previous_aov = None, None, None
    for year in (2017, 2018):
        months = ["{}-{:02d}".format(year, month) for month in range(2, 8)]
        count = sum(month_sales_counts[month] for month in months)
        all_count = sum(month_counts[month] for month in months)
        value = sum(month_values[month] for month in months)
        aov = divide(value, count * 100)
        comparable_periods.append({
            "period_year": year,
            "period_start": "{}-02-01".format(year),
            "period_end_exclusive": "{}-08-01".format(year),
            "calendar_months": 6,
            "all_period_orders": all_count,
            "sales_orders": count,
            "excluded_orders": all_count - count,
            "product_sales_cents": value,
            "product_sales_value": display(Decimal(value) / 100),
            "average_order_value": display(aov),
            "previous_year_product_sales_cents": previous_value,
            "previous_year_sales_orders": previous_count,
            "previous_year_average_order_value": display(previous_aov),
            "product_sales_yoy_pct": growth(Decimal(value), previous_value),
            "orders_yoy_pct": growth(Decimal(count), previous_count),
            "aov_yoy_pct": growth(aov, previous_aov),
        })
        previous_value, previous_count, previous_aov = value, count, aov

    category_sales, cumulative = [], 0
    for label in sorted(category_values, key=lambda x: (-category_values[x], x)):
        value = category_values[label]
        cumulative += value
        category_sales.append({
            "category_label": label,
            "sales_orders": len(category_orders[label]),
            "item_count": category_items[label],
            "product_sales_cents": value,
            "product_sales_value": display(Decimal(value) / 100),
            "sales_share_pct": display(divide(value * 100, total_cents)),
            "cumulative_sales_share_pct": display(divide(cumulative * 100, total_cents)),
        })

    regional_sales = []
    for state in sorted(state_values, key=lambda x: (-state_values[x], x)):
        value, count = state_values[state], state_orders[state]
        regional_sales.append({
            "customer_state": state,
            "sales_orders": count,
            "product_sales_cents": value,
            "product_sales_value": display(Decimal(value) / 100),
            "average_order_value": display(divide(value, count * 100)),
            "sales_share_pct": display(divide(value * 100, total_cents)),
        })

    return {
        "overall": {
            "period_start": REPORTING_START,
            "period_end_exclusive": REPORTING_END,
            "source_orders": source_orders,
            "all_period_orders": period_count,
            "outside_period_orders": source_orders - period_count,
            "sales_orders": sales_count,
            "excluded_orders": period_count - sales_count,
            "delivered_orders_without_items": missing_items_delivered,
            "item_count": sum(category_items.values()),
            "product_sales_cents": total_cents,
            "product_sales_value": display(Decimal(total_cents) / 100),
            "average_order_value": display(divide(total_cents, sales_count * 100)),
        },
        "status_counts": dict(sorted(status_counts.items())),
        "reports": {
            "monthly_sales": monthly_sales,
            "monthly_growth": monthly_growth,
            "comparable_periods": comparable_periods,
            "category_sales": category_sales,
            "regional_sales": regional_sales,
        },
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    import sqlite3

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        result = build_expected(db)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["overall"], indent=2))
