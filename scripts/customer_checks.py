"""Recalculate customer reports from raw orders, items, customers and reviews.

Review selection, customer grouping and report calculations use Python rather
than the prepared views. Counts and money remain integers until display.
"""

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fractions import Fraction

from delivery_checks import parse_timestamp, valid_id
from sales_checks import as_cents


REPORTING_START = "2017-02-01"
REPORTING_END = "2018-08-01"
TOP_CUSTOMERS = 20
TWO_PLACES = Decimal("0.01")


def ratio(numerator, denominator):
    """Round a ratio to two decimal places, with exact halfway values up."""
    if not denominator:
        return None
    value = Decimal(numerator) / Decimal(denominator)
    return float(value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def score_value(raw):
    """An eligible review needs an integer score from one to five."""
    try:
        value = Decimal((raw or "").strip())
    except InvalidOperation:
        return None
    if not value.is_finite() or value != value.to_integral_value() or not 1 <= value <= 5:
        return None
    return int(value)


def empty_group():
    return {"orders": 0, "reviewed": 0, "score_sum": 0, "low": 0, "pre_delivery": 0}


def add_order(group, review, actual):
    group["orders"] += 1
    if review is not None:
        group["reviewed"] += 1
        group["score_sum"] += review["score"]
        group["low"] += review["score"] <= 2
        group["pre_delivery"] += actual is not None and review["answer"] < actual


def metrics(group):
    count, reviewed = group["orders"], group["reviewed"]
    return {
        "sales_orders": count,
        "reviewed_orders": reviewed,
        "missing_review_orders": count - reviewed,
        "review_coverage_pct": ratio(reviewed * 100, count),
        "review_score_sum": group["score_sum"],
        "average_review_score": ratio(group["score_sum"], reviewed),
        "low_score_orders": group["low"],
        "low_score_pct": ratio(group["low"] * 100, reviewed),
    }


def newer_review(candidate, selected):
    if selected is None:
        return True
    candidate_dates = (candidate["answer"], candidate["created"])
    selected_dates = (selected["answer"], selected["created"])
    return (candidate_dates > selected_dates or
            (candidate_dates == selected_dates and candidate["id"] < selected["id"]))


def region_priority(label, group):
    reviewed = group["reviewed"]
    rate = Fraction(group["low"], reviewed) if reviewed else Fraction(0)
    # SQL puts NULL after numeric values in descending rate order.
    return (-group["low"], reviewed == 0, -rate, label)


def build_expected(connection):
    """Return five reports, population counts and review-selection coverage.

    Every SELECT reads raw columns without joins or aggregation. One review is
    chosen per order before orders are grouped by persistent customer ID.
    """
    customers = {}
    for customer_id, persistent_id, state in connection.execute(
            "SELECT customer_id, customer_unique_id, customer_state FROM customers"):
        valid_id(customer_id, "customers.customer_id")
        valid_id(persistent_id, "customers.customer_unique_id")
        if customer_id in customers:
            raise ValueError("Duplicate customer_id: {!r}".format(customer_id))
        customers[customer_id] = (persistent_id, (state or "").strip().upper() or "Unknown state")

    item_values, item_counts = Counter(), Counter()
    for order_id, raw_price in connection.execute("SELECT order_id, price FROM order_items"):
        valid_id(order_id, "order_items.order_id")
        item_values[order_id] += as_cents(raw_price)
        item_counts[order_id] += 1

    orders = {}
    for order_id, customer_id, status, purchased, actual, promised in connection.execute(
            "SELECT order_id, customer_id, order_status, order_purchase_timestamp, "
            "order_delivered_customer_date, order_estimated_delivery_date FROM orders"):
        valid_id(order_id, "orders.order_id")
        valid_id(customer_id, "orders.customer_id")
        if order_id in orders:
            raise ValueError("Duplicate order_id: {!r}".format(order_id))
        orders[order_id] = {
            "customer_id": customer_id,
            "status": (status or "").strip().lower() or "Unknown status",
            "purchased": parse_timestamp(purchased, "order_purchase_timestamp"),
            "actual": parse_timestamp(actual, "order_delivered_customer_date"),
            "promised": parse_timestamp(promised, "order_estimated_delivery_date"),
        }

    selected_reviews = {}
    seen_review_keys = set()
    source_reviews_by_order, valid_reviews_by_order = Counter(), Counter()
    source_review_rows = invalid_review_rows = 0
    for review_id, order_id, raw_score, created, answer in connection.execute(
            "SELECT review_id, order_id, review_score, review_creation_date, "
            "review_answer_timestamp FROM order_reviews"):
        source_review_rows += 1
        valid_id(review_id, "order_reviews.review_id")
        valid_id(order_id, "order_reviews.order_id")
        key = (order_id, review_id)
        if key in seen_review_keys:
            raise ValueError("Duplicate order/review key: {!r}".format(key))
        seen_review_keys.add(key)
        source_reviews_by_order[order_id] += 1
        created = parse_timestamp(created, "review_creation_date")
        answer = parse_timestamp(answer, "review_answer_timestamp")
        score = score_value(raw_score)
        purchased = orders.get(order_id, {}).get("purchased")
        if (score is None or purchased is None or created is None or answer is None
                or created.date() < purchased.date() or answer < purchased or answer < created):
            invalid_review_rows += 1
            continue
        valid_reviews_by_order[order_id] += 1
        candidate = {"id": review_id, "score": score, "created": created, "answer": answer}
        if newer_review(candidate, selected_reviews.get(order_id)):
            selected_reviews[order_id] = candidate

    total = empty_group()
    states = defaultdict(empty_group)
    delivery = {label: empty_group() for label in ("on_time", "late")}
    customer_groups = {}
    score_counts, status_counts = Counter(), Counter()
    start = datetime.strptime(REPORTING_START, "%Y-%m-%d")
    end = datetime.strptime(REPORTING_END, "%Y-%m-%d")
    period_count = delivered_without_items = total_value = 0
    sales_without_source_review = sales_with_only_invalid_review = 0
    sales_with_multiple_source_reviews = sales_with_multiple_valid_reviews = 0
    sales_without_delivery_endpoints = reviewed_without_delivery_endpoints = 0

    for order_id, order in orders.items():
        purchased = order["purchased"]
        if purchased is None or not start <= purchased < end:
            continue
        period_count += 1
        status_counts[order["status"]] += 1
        if order["status"] != "delivered":
            continue
        if not item_counts[order_id]:
            delivered_without_items += 1
            continue
        if order["customer_id"] not in customers:
            raise ValueError("Sales order has no customer: {!r}".format(order_id))
        persistent_id, state = customers[order["customer_id"]]
        value = item_values[order_id]
        total_value += value
        review = selected_reviews.get(order_id)
        actual, promised = order["actual"], order["promised"]
        add_order(total, review, actual)
        add_order(states[state], review, actual)
        score_counts[review["score"] if review is not None else None] += 1
        sales_without_source_review += not source_reviews_by_order[order_id]
        sales_with_only_invalid_review += bool(source_reviews_by_order[order_id]) and review is None
        sales_with_multiple_source_reviews += source_reviews_by_order[order_id] > 1
        sales_with_multiple_valid_reviews += valid_reviews_by_order[order_id] > 1
        if (actual is not None and promised is not None and actual >= purchased
                and promised.date() >= purchased.date()):
            label = "late" if actual.date() > promised.date() else "on_time"
            add_order(delivery[label], review, actual)
        else:
            sales_without_delivery_endpoints += 1
            reviewed_without_delivery_endpoints += review is not None

        if persistent_id not in customer_groups:
            customer_groups[persistent_id] = dict(empty_group(), cents=0, first=purchased, last=purchased)
        customer = customer_groups[persistent_id]
        add_order(customer, review, actual)
        customer["cents"] += value
        customer["first"] = min(customer["first"], purchased)
        customer["last"] = max(customer["last"], purchased)

    count, reviewed = total["orders"], total["reviewed"]
    review_distribution = [{
        "review_bucket": str(score) if score is not None else "No eligible selected review",
        "review_score": score,
        "sales_orders": score_counts[score],
        "share_of_sales_pct": ratio(score_counts[score] * 100, count),
        "share_of_reviewed_pct": ratio(score_counts[score] * 100, reviewed) if score is not None else None,
        "total_sales_orders": count,
        "total_reviewed_orders": reviewed,
        "total_missing_review_orders": count - reviewed,
        "review_coverage_pct": ratio(reviewed * 100, count),
    } for score in (1, 2, 3, 4, 5, None)]

    delivery_reviews = []
    for label, group in delivery.items():
        row = dict(delivery_group=label, **metrics(group))
        row["pre_delivery_review_orders"] = group["pre_delivery"]
        delivery_reviews.append(row)

    ranked_customers = sorted(customer_groups,
                              key=lambda key: (-customer_groups[key]["cents"], key))
    customer_spending = []
    for customer_id in ranked_customers[:TOP_CUSTOMERS]:
        group = customer_groups[customer_id]
        customer_spending.append({
            "customer_unique_id": customer_id,
            "sales_orders": group["orders"],
            "product_sales_cents": group["cents"],
            "product_sales_value": ratio(group["cents"], 100),
            "average_order_value": ratio(group["cents"], group["orders"] * 100),
            "first_purchase_timestamp": group["first"].strftime("%Y-%m-%d %H:%M:%S"),
            "last_purchase_timestamp": group["last"].strftime("%Y-%m-%d %H:%M:%S"),
            "reviewed_orders": group["reviewed"],
            "review_coverage_pct": ratio(group["reviewed"] * 100, group["orders"]),
            "average_review_score": ratio(group["score_sum"], group["reviewed"]),
        })

    repeat = [group for group in customer_groups.values() if group["orders"] >= 2]
    customer_count = len(customer_groups)
    repeat_orders = sum(group["orders"] for group in repeat)
    repeat_cents = sum(group["cents"] for group in repeat)
    repeat_customers = {
        "period_start": REPORTING_START,
        "period_end_exclusive": REPORTING_END,
        "total_customers": customer_count,
        "one_time_customers": customer_count - len(repeat),
        "repeat_customers": len(repeat),
        "repeat_customer_pct": ratio(len(repeat) * 100, customer_count),
        "total_sales_orders": count,
        "one_time_customer_orders": count - repeat_orders,
        "repeat_customer_orders": repeat_orders,
        "total_product_sales_cents": total_value,
        "one_time_product_sales_cents": total_value - repeat_cents,
        "repeat_product_sales_cents": repeat_cents,
        "total_product_sales_value": ratio(total_value, 100),
        "one_time_product_sales_value": ratio(total_value - repeat_cents, 100),
        "repeat_product_sales_value": ratio(repeat_cents, 100),
        "repeat_order_share_pct": ratio(repeat_orders * 100, count),
        "repeat_sales_share_pct": ratio(repeat_cents * 100, total_value),
    }

    regional_reviews = [dict(customer_state=state, **metrics(states[state]))
                        for state in sorted(states, key=lambda key: region_priority(key, states[key]))]
    top_value = sum(row["product_sales_cents"] for row in customer_spending)
    overall = {
        "period_start": REPORTING_START,
        "period_end_exclusive": REPORTING_END,
        "source_orders": len(orders),
        "all_period_orders": period_count,
        "outside_period_orders": len(orders) - period_count,
        "sales_orders": count,
        "excluded_period_orders": period_count - count,
        "delivered_orders_without_items": delivered_without_items,
        "product_sales_cents": total_value,
        "product_sales_value": ratio(total_value, 100),
        "total_customers": customer_count,
        "repeat_customers": len(repeat),
        "repeat_customer_pct": ratio(len(repeat) * 100, customer_count),
        "average_customer_product_value": ratio(total_value, customer_count * 100),
        "reviewed_orders": reviewed,
        "missing_review_orders": count - reviewed,
        "review_coverage_pct": ratio(reviewed * 100, count),
        "review_score_sum": total["score_sum"],
        "average_review_score": ratio(total["score_sum"], reviewed),
        "low_score_orders": total["low"],
        "low_score_pct": ratio(total["low"] * 100, reviewed),
        "sales_without_source_review": sales_without_source_review,
        "sales_with_only_invalid_review": sales_with_only_invalid_review,
        "sales_with_multiple_source_reviews": sales_with_multiple_source_reviews,
        "sales_with_multiple_valid_reviews": sales_with_multiple_valid_reviews,
        "sales_delivery_eligible_orders": sum(group["orders"] for group in delivery.values()),
        "sales_delivery_reviewed_orders": sum(group["reviewed"] for group in delivery.values()),
        "sales_without_delivery_endpoints": sales_without_delivery_endpoints,
        "reviewed_without_delivery_endpoints": reviewed_without_delivery_endpoints,
        "pre_delivery_review_orders": sum(group["pre_delivery"] for group in delivery.values()),
        "top_customer_limit": TOP_CUSTOMERS,
        "reported_customers": len(customer_spending),
        "reported_customer_orders": sum(row["sales_orders"] for row in customer_spending),
        "reported_customer_product_sales_cents": top_value,
        "reported_customer_sales_share_pct": ratio(top_value * 100, total_value),
        "source_review_rows": source_review_rows,
        "invalid_review_rows": invalid_review_rows,
        "valid_review_rows": source_review_rows - invalid_review_rows,
        "selected_review_orders": len(selected_reviews),
        "additional_valid_review_rows": source_review_rows - invalid_review_rows - len(selected_reviews),
        "source_orders_without_any_review": sum(not source_reviews_by_order[key] for key in orders),
        "source_orders_without_selected_review": len(orders) - len(selected_reviews),
    }
    return {
        "overall": overall,
        "status_counts": dict(sorted(status_counts.items())),
        "reports": {
            "review_distribution": review_distribution,
            "delivery_reviews": delivery_reviews,
            "customer_spending": customer_spending,
            "repeat_customers": [repeat_customers],
            "regional_reviews": regional_reviews,
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
