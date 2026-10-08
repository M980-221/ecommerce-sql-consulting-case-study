"""Recalculate delivery reports from raw rows using Python dates and grouping.

The check reads no prepared views and performs no SQL joins or aggregation.
Elapsed durations use integer seconds; rounding happens after each group total.
"""

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
import re


REPORTING_START = "2017-02-01"
REPORTING_END = "2018-08-01"
SELLER_MIN_ORDERS = 100
TIMESTAMP_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\Z")
TWO_PLACES = Decimal("0.01")


def display(value):
    if value is None:
        return None
    return float(Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def divide(numerator, denominator):
    return Decimal(numerator) / Decimal(denominator) if denominator else None


def parse_timestamp(raw, field):
    """Allow missing dates, but reject malformed or impossible nonblank dates."""
    value = (raw or "").strip()
    if not value:
        return None
    if not TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError("Invalid {}: {!r}".format(field, raw))
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise ValueError("Invalid {}: {!r}".format(field, raw)) from error
    if parsed.strftime("%Y-%m-%d %H:%M:%S") != value:
        raise ValueError("Invalid {}: {!r}".format(field, raw))
    return parsed


def valid_id(value, field):
    if value is None or not value.strip() or value != value.strip():
        raise ValueError("Invalid {}: {!r}".format(field, value))
    return value


def unique_lookup(rows, name):
    result = {}
    for key, value in rows:
        if key in result:
            raise ValueError("Duplicate {} key: {!r}".format(name, key))
        result[key] = value
    return result


def empty_group():
    return {"orders": 0, "late": 0, "seconds": 0, "positive_delay": 0}


def add_order(group, duration_seconds, delay_days):
    group["orders"] += 1
    group["seconds"] += duration_seconds
    if delay_days > 0:
        group["late"] += 1
        group["positive_delay"] += delay_days


def metrics(group):
    count, late = group["orders"], group["late"]
    return {
        "delivery_orders": count,
        "late_orders": late,
        "on_time_orders": count - late,
        "late_delivery_pct": display(divide(late * 100, count)),
        "average_delivery_days": display(divide(group["seconds"], count * 86400)),
        "average_positive_delay_days": display(divide(group["positive_delay"], late)),
    }


def priority_key(label, group):
    # Use the exact fraction so sorting never depends on the rounded percentage.
    return (-group["late"], -Fraction(group["late"], group["orders"]), label)


def build_expected(connection):
    """Return five expected reports, population counts and attribution coverage.

    Only raw columns are selected. Each eligible order contributes once to its
    buyer state and once to each distinct category it contains. Seller results
    include only single-seller orders, with at least 100 orders per seller.
    """
    translation = unique_lookup(
        (((source or "").strip(), (target or "").strip() or None)
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
        valid_id(product_id, "product_id")
        category = (raw_category or "").strip()
        if not category:
            label = "Unknown category"
        elif translation.get(category):
            label = translation[category]
        else:
            label = "Untranslated: " + category
        product_labels[product_id] = label

    customer_states = unique_lookup(
        ((valid_id(customer_id, "customer_id"),
          (state or "").strip().upper() or "Unknown state")
         for customer_id, state in connection.execute(
             "SELECT customer_id, customer_state FROM customers")),
        "customer",
    )
    seller_states = unique_lookup(
        ((valid_id(seller_id, "seller_id"),
          (state or "").strip().upper() or "Unknown state")
         for seller_id, state in connection.execute(
             "SELECT seller_id, seller_state FROM sellers")),
        "seller",
    )
    order_categories, order_sellers = defaultdict(set), defaultdict(set)
    for order_id, product_id, seller_id in connection.execute(
            "SELECT order_id, product_id, seller_id FROM order_items"):
        valid_id(order_id, "order_items.order_id")
        valid_id(product_id, "order_items.product_id")
        valid_id(seller_id, "order_items.seller_id")
        order_categories[order_id].add(product_labels.get(product_id, "Unknown category"))
        order_sellers[order_id].add(seller_id)

    month_names = ["{}-{:02d}".format(year, month)
                   for year in (2017, 2018) for month in range(1, 13)
                   if REPORTING_START[:7] <= "{}-{:02d}".format(year, month)
                   < REPORTING_END[:7]]
    months = {month: empty_group() for month in month_names}
    period_month_counts, status_counts = Counter(), Counter()
    states, categories, sellers = (defaultdict(empty_group) for _ in range(3))
    total = empty_group()
    coverage = {name: empty_group() for name in ("single", "multi", "none")}
    endpoint_issues = Counter()
    source_orders = 0
    seen_orders = set()
    category_memberships = multi_category_orders = untranslated_orders = 0
    start = datetime.strptime(REPORTING_START, "%Y-%m-%d")
    end = datetime.strptime(REPORTING_END, "%Y-%m-%d")

    for order_id, customer_id, status, purchased, actual, promised in connection.execute(
            "SELECT order_id, customer_id, order_status, order_purchase_timestamp, "
            "order_delivered_customer_date, order_estimated_delivery_date FROM orders"):
        source_orders += 1
        valid_id(order_id, "orders.order_id")
        valid_id(customer_id, "orders.customer_id")
        if order_id in seen_orders:
            raise ValueError("Duplicate order key: {!r}".format(order_id))
        seen_orders.add(order_id)
        # Check all source endpoint values, including excluded/boundary orders.
        purchased = parse_timestamp(purchased, "order_purchase_timestamp")
        actual = parse_timestamp(actual, "order_delivered_customer_date")
        promised = parse_timestamp(promised, "order_estimated_delivery_date")
        if purchased is None or not start <= purchased < end:
            continue
        month = purchased.strftime("%Y-%m")
        period_month_counts[month] += 1
        status = (status or "").strip().lower() or "Unknown status"
        status_counts[status] += 1
        if status != "delivered":
            continue
        if actual is None:
            endpoint_issues["delivered_missing_actual"] += 1
        if promised is None:
            endpoint_issues["delivered_missing_promise"] += 1
        if actual is not None and actual < purchased:
            endpoint_issues["delivered_actual_before_purchase"] += 1
        if promised is not None and promised.date() < purchased.date():
            endpoint_issues["delivered_promise_before_purchase_day"] += 1
        if (actual is None or promised is None or actual < purchased
                or promised.date() < purchased.date()):
            endpoint_issues["delivered_invalid_endpoints"] += 1
            continue

        elapsed = actual - purchased
        duration_seconds = elapsed.days * 86400 + elapsed.seconds
        delay_days = (actual.date() - promised.date()).days
        add_order(total, duration_seconds, delay_days)
        add_order(months[month], duration_seconds, delay_days)
        state = customer_states.get(customer_id, "Unknown state")
        add_order(states[state], duration_seconds, delay_days)
        labels = order_categories.get(order_id) or {"Unknown category"}
        category_memberships += len(labels)
        multi_category_orders += len(labels) > 1
        untranslated_orders += any(label.startswith("Untranslated: ") for label in labels)
        for label in labels:
            add_order(categories[label], duration_seconds, delay_days)

        seller_ids = order_sellers.get(order_id, set())
        if len(seller_ids) == 1:
            seller_id = next(iter(seller_ids))
            add_order(sellers[seller_id], duration_seconds, delay_days)
            add_order(coverage["single"], duration_seconds, delay_days)
        else:
            add_order(coverage["multi" if seller_ids else "none"],
                      duration_seconds, delay_days)

    monthly_delivery = []
    for month in month_names:
        group = months[month]
        row = {"month": month, "all_period_orders": period_month_counts[month],
               "delivery_orders": group["orders"],
               "excluded_orders": period_month_counts[month] - group["orders"]}
        row.update({key: value for key, value in metrics(group).items()
                    if key != "delivery_orders"})
        monthly_delivery.append(row)

    regional_delivery = [dict({"customer_state": state}, **metrics(states[state]))
                         for state in sorted(states, key=lambda x: priority_key(x, states[x]))]
    category_delivery = [dict({"category_label": label}, **metrics(categories[label]))
                         for label in sorted(categories, key=lambda x: priority_key(x, categories[x]))]
    included_sellers = {seller_id: group for seller_id, group in sellers.items()
                        if group["orders"] >= SELLER_MIN_ORDERS}
    seller_delivery = [dict({"seller_id": seller_id,
                             "seller_state": seller_states.get(seller_id, "Unknown state")},
                            **metrics(included_sellers[seller_id]))
                       for seller_id in sorted(included_sellers,
                                               key=lambda x: priority_key(x, included_sellers[x]))]
    reported_orders = sum(group["orders"] for group in included_sellers.values())
    reported_late = sum(group["late"] for group in included_sellers.values())
    count, late = total["orders"], total["late"]
    period_count = sum(period_month_counts.values())
    overall_delivery = {
        "period_start": REPORTING_START,
        "period_end_exclusive": REPORTING_END,
        "all_period_orders": period_count,
        "delivery_orders": count,
        "excluded_orders": period_count - count,
        "non_delivered_orders": period_count - status_counts["delivered"],
        "excluded_delivered_date_orders": endpoint_issues["delivered_invalid_endpoints"],
        "late_orders": late,
        "on_time_orders": count - late,
        "late_delivery_pct": display(divide(late * 100, count)),
        "on_time_delivery_pct": display(divide((count - late) * 100, count)),
        "average_delivery_days": display(divide(total["seconds"], count * 86400)),
        "average_positive_delay_days": display(divide(total["positive_delay"], late)),
        "single_seller_orders": coverage["single"]["orders"],
        "excluded_multi_seller_orders": coverage["multi"]["orders"],
        "excluded_no_seller_orders": coverage["none"]["orders"],
        "reported_sellers": len(included_sellers),
        "reported_seller_orders": reported_orders,
        "below_threshold_seller_orders": coverage["single"]["orders"] - reported_orders,
        "reported_seller_order_coverage_pct": display(divide(reported_orders * 100, count)),
    }
    overall = dict(overall_delivery)
    overall.update({
        "source_orders": source_orders,
        "outside_period_orders": source_orders - period_count,
        "delivered_period_orders": status_counts["delivered"],
        "non_delivered_period_orders": period_count - status_counts["delivered"],
        "seller_minimum_orders": SELLER_MIN_ORDERS,
        "all_single_sellers": len(sellers),
        "below_threshold_sellers": len(sellers) - len(included_sellers),
        "single_seller_late_orders": coverage["single"]["late"],
        "excluded_multi_seller_late_orders": coverage["multi"]["late"],
        "excluded_no_seller_late_orders": coverage["none"]["late"],
        "reported_seller_late_orders": reported_late,
        "below_threshold_seller_late_orders": coverage["single"]["late"] - reported_late,
        "single_seller_order_coverage_pct": display(divide(coverage["single"]["orders"] * 100, count)),
        "reported_seller_late_coverage_pct": display(divide(reported_late * 100, late)),
        "category_order_memberships": category_memberships,
        "multi_category_orders": multi_category_orders,
        "unknown_category_orders": categories.get("Unknown category", empty_group())["orders"],
        "untranslated_category_orders": untranslated_orders,
    })
    for issue in ("delivered_missing_actual", "delivered_missing_promise",
                  "delivered_actual_before_purchase", "delivered_promise_before_purchase_day",
                  "delivered_invalid_endpoints"):
        overall[issue] = endpoint_issues[issue]

    return {
        "overall": overall,
        "status_counts": dict(sorted(status_counts.items())),
        "reports": {
            "overall_delivery": [overall_delivery],
            "monthly_delivery": monthly_delivery,
            "regional_delivery": regional_delivery,
            "category_delivery": category_delivery,
            "seller_delivery": seller_delivery,
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
