"""Recalculate Part 7 checks from raw records with Decimal money and Python dates.

No prepared view, SQL join or SQL aggregation is read here. The reports provide
an independent comparison for sql/06_validation.sql, including the deliberately
unsafe item/payment join. Existing parsers keep the accepted input formats.
"""
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal

from customer_checks import newer_review, score_value
from delivery_checks import parse_timestamp, valid_id
from sales_checks import as_cents


GROUPS = (
    "missing_items_and_payments", "missing_items", "missing_payments", "exact_match",
    "one_cent_difference", "payment_below_expected", "payment_above_expected",
)
POPULATIONS = ("full_source", "reporting_period", "sales", "delivery", "reviewed_sales")


def raw_rows(connection, table, fields):
    cursor = connection.execute("SELECT " + ", ".join(fields) + " FROM " + table)
    return [dict(zip(fields, row)) for row in cursor]


def nullable_sum(values):
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def integer_key(raw):
    value = Decimal((raw or "").strip())
    if not value.is_finite() or value < 0 or value != value.to_integral_value():
        raise ValueError("Invalid sequence: {!r}".format(raw))
    return int(value)


def require_unique(rows, fields, label, numeric_fields=()):
    seen = set()
    for row in rows:
        key = tuple(integer_key(row[field]) if field in numeric_fields
                    else valid_id(row[field], label + "." + field) for field in fields)
        if key in seen:
            raise ValueError("Duplicate {} key: {!r}".format(label, key))
        seen.add(key)
    return len(seen)


def require_relationship(rows, field, parent_keys, label):
    unmatched = sum(row[field] not in parent_keys for row in rows)
    if unmatched:
        raise ValueError("Unmatched {} rows: {}".format(label, unmatched))
    return unmatched


def classify(order):
    if not order["item_count"] and not order["payment_count"]:
        return "missing_items_and_payments"
    if not order["item_count"]:
        return "missing_items"
    if not order["payment_count"]:
        return "missing_payments"
    difference = order["difference_cents"]
    if difference == 0:
        return "exact_match"
    if abs(difference) == 1:
        return "one_cent_difference"
    return "payment_below_expected" if difference < 0 else "payment_above_expected"


def calculate_raw(connection):
    """Return {'reports': six ordered reports, 'evidence': raw audit facts}.

    This is read-only. Invalid keys, orphan rows, monetary formats or timestamp
    formats raise ValueError before a set of expected results can be published.
    """
    orders = raw_rows(connection, "orders", (
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_delivered_customer_date", "order_estimated_delivery_date"))
    items = raw_rows(connection, "order_items", (
        "order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"))
    payments = raw_rows(connection, "order_payments", (
        "order_id", "payment_sequential", "payment_type", "payment_value"))
    reviews = raw_rows(connection, "order_reviews", (
        "order_id", "review_id", "review_score", "review_creation_date", "review_answer_timestamp"))
    customers = raw_rows(connection, "customers", ("customer_id", "customer_unique_id"))
    products = raw_rows(connection, "products", ("product_id",))
    sellers = raw_rows(connection, "sellers", ("seller_id",))
    translation = raw_rows(connection, "category_translation", ("product_category_name",))
    tables = {"orders": orders, "order_items": items, "order_payments": payments,
              "order_reviews": reviews, "customers": customers, "products": products,
              "sellers": sellers, "category_translation": translation}
    unique_counts = {
        "orders": require_unique(orders, ("order_id",), "orders"),
        "customers": require_unique(customers, ("customer_id",), "customers"),
        "products": require_unique(products, ("product_id",), "products"),
        "sellers": require_unique(sellers, ("seller_id",), "sellers"),
        "order_items": require_unique(items, ("order_id", "order_item_id"), "order_items", ("order_item_id",)),
        "order_payments": require_unique(payments, ("order_id", "payment_sequential"), "order_payments", ("payment_sequential",)),
        "order_reviews": require_unique(reviews, ("order_id", "review_id"), "order_reviews"),
        "category_translation": require_unique(translation, ("product_category_name",), "category_translation"),
    }
    for customer in customers:
        valid_id(customer["customer_unique_id"], "customers.customer_unique_id")
    order_ids = {row["order_id"] for row in orders}
    relationship_checks = {
        "orders_to_customers": require_relationship(orders, "customer_id", {row["customer_id"] for row in customers}, "orders/customers"),
        "items_to_orders": require_relationship(items, "order_id", order_ids, "items/orders"),
        "items_to_products": require_relationship(items, "product_id", {row["product_id"] for row in products}, "items/products"),
        "items_to_sellers": require_relationship(items, "seller_id", {row["seller_id"] for row in sellers}, "items/sellers"),
        "payments_to_orders": require_relationship(payments, "order_id", order_ids, "payments/orders"),
        "reviews_to_orders": require_relationship(reviews, "order_id", order_ids, "reviews/orders"),
    }
    item_groups, payment_groups = defaultdict(list), defaultdict(list)
    for item in items:
        item_groups[item["order_id"]].append({
            "price": as_cents(item["price"]), "freight": as_cents(item["freight_value"]),
            "seller": item["seller_id"],
        })
    for payment in payments:
        payment_groups[payment["order_id"]].append({
            "value": as_cents(payment["payment_value"]),
            "method": (payment["payment_type"] or "").strip().lower() or None,
        })
    order_lookup = {order["order_id"]: order for order in orders}
    for order in orders:
        order["purchased"] = parse_timestamp(order["order_purchase_timestamp"], "order_purchase_timestamp")
        order["actual"] = parse_timestamp(order["order_delivered_customer_date"], "order_delivered_customer_date")
        order["promised"] = parse_timestamp(order["order_estimated_delivery_date"], "order_estimated_delivery_date")
    selected_reviews, source_review_counts = {}, Counter()
    invalid_review_rows = valid_review_rows = 0
    for review in reviews:
        order_id = review["order_id"]
        source_review_counts[order_id] += 1
        purchased = order_lookup[order_id]["purchased"]
        created = parse_timestamp(review["review_creation_date"], "review_creation_date")
        answer = parse_timestamp(review["review_answer_timestamp"], "review_answer_timestamp")
        score = score_value(review["review_score"])
        if (score is None or purchased is None or created is None or answer is None
                or created.date() < purchased.date() or answer < purchased or answer < created):
            invalid_review_rows += 1
            continue
        valid_review_rows += 1
        candidate = {"id": review["review_id"], "created": created, "answer": answer, "score": score}
        if newer_review(candidate, selected_reviews.get(order_id)):
            selected_reviews[order_id] = candidate

    start, end = datetime(2017, 2, 1), datetime(2018, 8, 1)
    calculated = []
    for order in orders:
        order_id = order["order_id"]
        item_rows, payment_rows = item_groups[order_id], payment_groups[order_id]
        price = sum(item["price"] for item in item_rows) if item_rows else None
        freight = sum(item["freight"] for item in item_rows) if item_rows else None
        paid = sum(payment["value"] for payment in payment_rows) if payment_rows else None
        expected = price + freight if item_rows else None
        purchased, actual, promised = order["purchased"], order["actual"], order["promised"]
        period = purchased is not None and start <= purchased < end
        status = (order["order_status"] or "").strip().lower() or None
        sale = period and status == "delivered" and bool(item_rows)
        delivery = (period and status == "delivered" and actual is not None and promised is not None
                    and actual >= purchased and promised.date() >= purchased.date())
        selected = selected_reviews.get(order_id)
        methods = sorted({payment["method"] for payment in payment_rows if payment["method"] is not None})
        row = {
            "order_id": order_id, "order_status": status,
            "order_purchase_timestamp": purchased.strftime("%Y-%m-%d %H:%M:%S") if purchased else None,
            "in_reporting_period": int(period), "sales_eligible": int(sale),
            "delivery_eligible": int(delivery), "review_eligible": int(sale and selected is not None),
            "seller_delivery_eligible": int(delivery and len({item["seller"] for item in item_rows}) == 1),
            "item_count": len(item_rows), "payment_count": len(payment_rows),
            "product_sales_cents": price, "freight_cents": freight,
            "expected_payment_cents": expected, "payment_cents": paid,
            "difference_cents": paid - expected if item_rows and payment_rows else None,
            "payment_methods": "|".join(methods) if methods else None,
            "has_voucher": int("voucher" in methods),
            "zero_payment_components": sum(payment["value"] == 0 for payment in payment_rows),
            "source_review_count": source_review_counts[order_id],
            "has_selected_review": selected is not None,
            "has_actual": actual is not None, "has_promised": promised is not None,
        }
        row["reconciliation_group"] = classify(row)
        calculated.append(row)

    source_price = sum(item["price"] for group in item_groups.values() for item in group)
    source_freight = sum(item["freight"] for group in item_groups.values() for item in group)
    source_paid = sum(payment["value"] for group in payment_groups.values() for payment in group)
    population = {
        "source_orders": len(orders), "model_rows": len(orders), "model_distinct_orders": len(orders),
        "source_orders_missing_from_model": 0, "model_orders_missing_from_source": 0,
        "reporting_period_orders": sum(row["in_reporting_period"] for row in calculated),
        "sales_orders": sum(row["sales_eligible"] for row in calculated),
        "delivery_orders": sum(row["delivery_eligible"] for row in calculated),
        "reviewed_sales_orders": sum(row["review_eligible"] for row in calculated),
        "delivery_review_orders": sum(row["delivery_eligible"] and row["review_eligible"] for row in calculated),
        "single_seller_delivery_orders": sum(row["seller_delivery_eligible"] for row in calculated),
        "sales_product_sales_cents": sum(row["product_sales_cents"] for row in calculated if row["sales_eligible"]),
        "source_product_sales_cents": source_price, "model_product_sales_cents": source_price,
        "source_freight_cents": source_freight, "model_freight_cents": source_freight,
        "source_payment_cents": source_paid, "model_payment_cents": source_paid,
        "source_review_rows": len(reviews), "selected_review_rows": len(selected_reviews),
    }
    summary = []
    for name in GROUPS:
        group = [row for row in calculated if row["reconciliation_group"] == name]
        differences = [row["difference_cents"] for row in group if row["difference_cents"] is not None]
        summary.append({
            "reconciliation_group": name, "orders": len(group),
            "reporting_period_orders": sum(row["in_reporting_period"] for row in group),
            "sales_orders": sum(row["sales_eligible"] for row in group),
            "item_rows": sum(row["item_count"] for row in group),
            "payment_rows": sum(row["payment_count"] for row in group),
            "expected_payment_cents": nullable_sum(row["expected_payment_cents"] for row in group),
            "payment_cents": nullable_sum(row["payment_cents"] for row in group),
            "net_difference_cents": sum(differences) if differences else None,
            "absolute_difference_cents": sum(abs(value) for value in differences) if differences else None,
            "min_difference_cents": min(differences) if differences else None,
            "max_difference_cents": max(differences) if differences else None,
        })
    exceptions, pattern_groups = [], defaultdict(list)
    detail_fields = (
        "order_id", "order_status", "order_purchase_timestamp", "in_reporting_period", "sales_eligible",
        "item_count", "payment_count", "product_sales_cents", "freight_cents", "expected_payment_cents",
        "payment_cents", "difference_cents", "difference_band", "difference_direction", "payment_methods",
        "has_voucher", "zero_payment_components",
    )
    for row in calculated:
        if row["difference_cents"] in (None, 0):
            continue
        row["difference_band"] = "one_cent" if abs(row["difference_cents"]) == 1 else "over_one_cent"
        row["difference_direction"] = "below" if row["difference_cents"] < 0 else "above"
        exceptions.append({field: row[field] for field in detail_fields})
        key = (row["difference_band"], row["difference_direction"], row["has_voucher"],
               int(row["payment_count"] > 1), int(row["item_count"] > 1))
        pattern_groups[key].append(row)
    exceptions.sort(key=lambda row: (-abs(row["difference_cents"]), row["order_id"]))
    patterns = []
    for key in sorted(pattern_groups):
        group = pattern_groups[key]
        patterns.append(dict(zip(("difference_band", "difference_direction", "has_voucher",
                                  "multiple_payments", "multiple_items"), key), **{
            "orders": len(group),
            "expected_payment_cents": sum(row["expected_payment_cents"] for row in group),
            "payment_cents": sum(row["payment_cents"] for row in group),
            "net_difference_cents": sum(row["difference_cents"] for row in group),
            "absolute_difference_cents": sum(abs(row["difference_cents"]) for row in group),
            "zero_payment_orders": sum(row["zero_payment_components"] > 0 for row in group),
        }))
    matched = [row for row in calculated if row["item_count"] and row["payment_count"]]
    fanout = {
        "matched_orders": len(matched),
        "orders_with_multiple_items": sum(row["item_count"] > 1 for row in matched),
        "orders_with_multiple_payments": sum(row["payment_count"] > 1 for row in matched),
        "orders_with_both_multiple": sum(row["item_count"] > 1 and row["payment_count"] > 1 for row in matched),
        "correct_item_rows": sum(row["item_count"] for row in matched),
        "correct_payment_rows": sum(row["payment_count"] for row in matched),
        "unsafe_join_rows": sum(row["item_count"] * row["payment_count"] for row in matched),
    }
    for short, value, multiplier in (("product_sales", "product_sales_cents", "payment_count"),
                                     ("freight", "freight_cents", "payment_count"),
                                     ("payment", "payment_cents", "item_count")):
        correct = sum(row[value] for row in matched)
        unsafe = sum(row[value] * row[multiplier] for row in matched)
        fanout["correct_" + short + "_cents"] = correct
        fanout["unsafe_" + short + "_cents"] = unsafe
        fanout[short + "_overstatement_cents"] = unsafe - correct
    missingness = []
    population_flags = {"reporting_period": "in_reporting_period", "sales": "sales_eligible",
                        "delivery": "delivery_eligible", "reviewed_sales": "review_eligible"}
    for name in POPULATIONS:
        group = calculated if name == "full_source" else [row for row in calculated if row[population_flags[name]]]
        missingness.append({
            "population": name, "orders": len(group),
            "orders_without_items": sum(row["item_count"] == 0 for row in group),
            "orders_without_payments": sum(row["payment_count"] == 0 for row in group),
            "orders_without_source_review": sum(row["source_review_count"] == 0 for row in group),
            "orders_without_selected_review": sum(not row["has_selected_review"] for row in group),
            "orders_with_only_invalid_reviews": sum(row["source_review_count"] > 0 and not row["has_selected_review"] for row in group),
            "orders_without_actual_delivery_date": sum(not row["has_actual"] for row in group),
            "orders_without_promised_delivery_date": sum(not row["has_promised"] for row in group),
        })
    return {
        "reports": {
            "population_validation": [population], "reconciliation_summary": summary,
            "reconciliation_patterns": patterns, "reconciliation_exceptions": exceptions,
            "join_fanout_summary": [fanout], "missingness_by_population": missingness,
        },
        "evidence": {
            "source_row_counts": {name: len(rows) for name, rows in tables.items()},
            "unique_key_counts": unique_counts, "unmatched_relationship_rows": relationship_checks,
            "review_selection": {"source_rows": len(reviews), "invalid_rows": invalid_review_rows,
                                 "valid_rows": valid_review_rows, "selected_rows": len(selected_reviews),
                                 "additional_valid_rows": valid_review_rows - len(selected_reviews)},
            "reconciliation": {"source_orders": len(orders), "matched_orders": len(matched),
                               "exception_orders": len(exceptions),
                               "exact_match_orders": sum(row["difference_cents"] == 0 for row in matched),
                               "one_cent_orders": sum(abs(row["difference_cents"]) == 1 for row in matched),
                               "larger_difference_orders": sum(abs(row["difference_cents"]) > 1 for row in matched)},
        },
    }
