#!/usr/bin/env python3
"""Compare dashboard calculations with SQLite for full and filtered populations.

Node runs the actual dashboard JavaScript. Expected results are independently
grouped in SQLite from the reporting views. This checks data and calculations;
it does not test browser layout, controls or hosting.
"""
import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

from prepare_part3 import source_fingerprints


PROJECT = Path(__file__).resolve().parents[1]
FIELDS = ['month', 'state', 'customer', 'status', 'salesCents', 'sales', 'delivery',
          'late', 'deliverySeconds', 'delayDays', 'reviewScore', 'preDeliveryReview']
CATEGORY_FIELDS = ['order', 'category', 'salesCents', 'itemCount', 'delivery']

AGGREGATES = """
    COUNT(*) AS all_orders,
    COALESCE(SUM(sales_eligible), 0) AS sales_orders,
    COALESCE(SUM(CASE WHEN sales_eligible = 1 THEN product_sales_cents ELSE 0 END), 0) AS cents,
    COUNT(DISTINCT CASE WHEN sales_eligible = 1 THEN customer_unique_id END) AS customers,
    COALESCE(SUM(delivery_eligible), 0) AS delivery_orders,
    COALESCE(SUM(CASE WHEN delivery_eligible = 1 AND is_late = 1 THEN 1 ELSE 0 END), 0) AS late_orders,
    COALESCE(SUM(CASE WHEN delivery_eligible = 1 THEN elapsed_seconds ELSE 0 END), 0) AS seconds,
    COALESCE(SUM(CASE WHEN delivery_eligible = 1 AND is_late = 1 THEN delay_days ELSE 0 END), 0) AS delay_days,
    COALESCE(SUM(CASE WHEN order_status != 'delivered' THEN 1 ELSE 0 END), 0) AS non_delivered,
    COALESCE(SUM(CASE WHEN order_status = 'delivered' AND delivery_eligible = 0 THEN 1 ELSE 0 END), 0) AS invalid_dates,
    COALESCE(SUM(review_eligible), 0) AS reviewed,
    COALESCE(SUM(CASE WHEN review_eligible = 1 THEN review_score ELSE 0 END), 0) AS score_sum,
    COALESCE(SUM(CASE WHEN review_eligible = 1 AND review_score IN (1, 2) THEN 1 ELSE 0 END), 0) AS low_scores,
    COALESCE(SUM(CASE WHEN sales_eligible = 1 AND delivery_eligible = 1 AND review_eligible = 1
                       AND review_answer_timestamp < order_delivered_customer_date THEN 1 ELSE 0 END), 0) AS pre_delivery
"""


def rounded(numerator, denominator=1):
    if not denominator:
        return None
    return float((Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP))


def one(connection, query, parameters=()):
    return dict(connection.execute(query, parameters).fetchone())


def rows(connection, query, parameters=()):
    return [dict(row) for row in connection.execute(query, parameters)]


def delivery_metrics(group):
    count, late = group['delivery_orders'], group['late_orders']
    return {
        'orders': count, 'lateOrders': late, 'onTimeOrders': count - late,
        'latePct': rounded(late * 100, count),
        'averageDays': rounded(group['seconds'], count * 86400),
        'averagePositiveDelayDays': rounded(group['delay_days'], late),
        'elapsedSeconds': group['seconds'], 'positiveDelayDays': group['delay_days'],
    }


def review_metrics(group):
    count, reviewed = group['sales_orders'], group['reviewed']
    return {
        'salesOrders': count, 'reviewedOrders': reviewed,
        'missingReviewOrders': count - reviewed,
        'reviewCoveragePct': rounded(reviewed * 100, count),
        'scoreSum': group['score_sum'], 'averageScore': rounded(group['score_sum'], reviewed),
        'lowScoreOrders': group['low_scores'],
        'lowScorePct': rounded(group['low_scores'] * 100, reviewed),
    }


def expected_snapshot(connection, filters, dimensions, customer_ids):
    """Group the selected SQLite rows without reading dashboard data or code."""
    months, states, labels = (dimensions[key] for key in ('months', 'states', 'categoryLabels'))
    start, end, state_id = filters['startMonth'], filters['endMonth'], filters['state']
    selected_months = months[start:end + 1]
    where = 'purchase_month >= ? AND purchase_month <= ?'
    parameters = [months[start], months[end]]
    if state_id != 'all':
        where += ' AND customer_state = ?'
        parameters.append(states[state_id])
    # Keep filter values bound as parameters in a temporary selection.
    connection.execute('DROP TABLE IF EXISTS temp.qa_selected')
    connection.execute('CREATE TEMP TABLE qa_selected AS SELECT * FROM qa_orders WHERE ' + where,
                       parameters)
    connection.execute('CREATE INDEX qa_selected_order ON qa_selected(order_id)')
    total = one(connection, 'SELECT ' + AGGREGATES + ' FROM qa_selected')
    monthly_groups = {row['purchase_month']: row for row in rows(
        connection, 'SELECT purchase_month, ' + AGGREGATES +
        ' FROM qa_selected GROUP BY purchase_month')}
    empty = {field: 0 for field in total}
    sales_months, delivery_months = [], []
    for month in selected_months:
        group = monthly_groups.get(month, empty)
        index = months.index(month)
        sales_months.append({
            'monthIndex': index, 'month': month, 'allOrders': group['all_orders'],
            'orders': group['sales_orders'], 'cents': group['cents'],
            'value': rounded(group['cents'], 100),
            'aov': rounded(group['cents'], group['sales_orders'] * 100),
            'excludedOrders': group['all_orders'] - group['sales_orders'],
        })
        delivery_months.append(dict(
            monthIndex=index, month=month, allOrders=group['all_orders'],
            excludedOrders=group['all_orders'] - group['delivery_orders'],
            **delivery_metrics(group)))

    sales_categories = []
    for group in rows(connection, """
            SELECT i.category_label, COUNT(DISTINCT i.order_id) AS orders,
                   COUNT(*) AS item_count, SUM(i.price_cents) AS cents
            FROM qa_items i JOIN qa_selected o ON o.order_id = i.order_id
            GROUP BY i.category_label ORDER BY cents DESC, i.category_label ASC"""):
        label = group['category_label']
        sales_categories.append({
            'categoryId': labels.index(label), 'label': label, 'orders': group['orders'],
            'itemCount': group['item_count'], 'cents': group['cents'],
            'value': rounded(group['cents'], 100),
            'sharePct': rounded(group['cents'] * 100, total['cents']),
        })

    sales_states = []
    for group in rows(connection, 'SELECT customer_state, ' + AGGREGATES + """
            FROM qa_selected WHERE sales_eligible = 1 GROUP BY customer_state
            ORDER BY cents DESC, customer_state ASC"""):
        label = group['customer_state']
        sales_states.append({
            'stateId': states.index(label), 'label': label, 'orders': group['sales_orders'],
            'cents': group['cents'], 'value': rounded(group['cents'], 100),
            'aov': rounded(group['cents'], group['sales_orders'] * 100),
            'sharePct': rounded(group['cents'] * 100, total['cents']),
        })

    delivery_states = []
    for group in rows(connection, 'SELECT customer_state, ' + AGGREGATES + """
            FROM qa_selected WHERE delivery_eligible = 1 GROUP BY customer_state
            ORDER BY late_orders DESC, 1.0 * late_orders / NULLIF(delivery_orders, 0) DESC,
                     customer_state ASC"""):
        label = group['customer_state']
        delivery_states.append(dict(stateId=states.index(label), label=label,
                                    **delivery_metrics(group)))

    delivery_categories = []
    for group in rows(connection, 'SELECT c.category_label, ' + AGGREGATES + """
            FROM qa_order_categories c JOIN qa_selected o ON o.order_id = c.order_id
            WHERE delivery_eligible = 1 GROUP BY c.category_label
            ORDER BY late_orders DESC, 1.0 * late_orders / NULLIF(delivery_orders, 0) DESC,
                     c.category_label ASC"""):
        label = group['category_label']
        delivery_categories.append(dict(categoryId=labels.index(label), label=label,
                                        **delivery_metrics(group)))

    review_distribution = []
    counts = {row['review_score']: row['orders'] for row in rows(connection, """
        SELECT CASE WHEN review_eligible = 1 THEN review_score END AS review_score,
               COUNT(*) AS orders FROM qa_selected WHERE sales_eligible = 1
        GROUP BY CASE WHEN review_eligible = 1 THEN review_score END""")}
    for score in (1, 2, 3, 4, 5, None):
        count = counts.get(score, 0)
        review_distribution.append({
            'score': score, 'label': str(score) if score is not None else 'No eligible selected review',
            'orders': count, 'shareOfSalesPct': rounded(count * 100, total['sales_orders']),
            'shareOfReviewedPct': rounded(count * 100, total['reviewed']) if score is not None else None,
        })

    delivery_comparison = []
    for flag, key, label in ((0, 'on_time', 'On time'), (1, 'late', 'Late')):
        group = one(connection, 'SELECT ' + AGGREGATES + """ FROM qa_selected
            WHERE sales_eligible = 1 AND delivery_eligible = 1 AND is_late = ?""", (flag,))
        delivery_comparison.append(dict(key=key, label=label, **review_metrics(group),
                                        preDeliveryReviewOrders=group['pre_delivery']))

    review_states = []
    for group in rows(connection, 'SELECT customer_state, ' + AGGREGATES + """
            FROM qa_selected WHERE sales_eligible = 1 GROUP BY customer_state
            ORDER BY low_scores DESC, 1.0 * low_scores / NULLIF(reviewed, 0) DESC,
                     customer_state ASC"""):
        label = group['customer_state']
        review_states.append(dict(stateId=states.index(label), label=label, **review_metrics(group)))

    repeat = one(connection, """
        WITH customer_totals AS (
            SELECT customer_unique_id, COUNT(*) AS orders, SUM(product_sales_cents) AS cents
            FROM qa_selected WHERE sales_eligible = 1 GROUP BY customer_unique_id
        ) SELECT COUNT(*) AS customers,
            COALESCE(SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END), 0) AS repeats,
            COALESCE(SUM(CASE WHEN orders >= 2 THEN orders ELSE 0 END), 0) AS repeat_orders,
            COALESCE(SUM(CASE WHEN orders >= 2 THEN cents ELSE 0 END), 0) AS repeat_cents
        FROM customer_totals""")
    spenders = []
    for group in rows(connection, 'SELECT customer_unique_id, ' + AGGREGATES + """
            FROM qa_selected WHERE sales_eligible = 1 GROUP BY customer_unique_id
            ORDER BY cents DESC, customer_unique_id ASC LIMIT 20"""):
        index = customer_ids[group['customer_unique_id']]
        spenders.append({
            'customerId': index, 'label': 'Customer ' + str(index + 1).zfill(6),
            'orders': group['sales_orders'], 'cents': group['cents'],
            'value': rounded(group['cents'], 100),
            'aov': rounded(group['cents'], group['sales_orders'] * 100),
            'reviewedOrders': group['reviewed'],
            'averageScore': rounded(group['score_sum'], group['reviewed']),
            'reviewCoveragePct': rounded(group['reviewed'] * 100, group['sales_orders']),
        })

    return {
        'filters': filters,
        'selectedOrders': total['all_orders'],
        'sales': {
            'orders': total['sales_orders'], 'cents': total['cents'],
            'value': rounded(total['cents'], 100),
            'aov': rounded(total['cents'], total['sales_orders'] * 100),
            'uniqueCustomers': total['customers'],
            'excludedOrders': total['all_orders'] - total['sales_orders'],
            'monthly': sales_months, 'categories': sales_categories, 'states': sales_states,
        },
        'delivery': dict(
            **delivery_metrics(total),
            excludedOrders=total['all_orders'] - total['delivery_orders'],
            nonDeliveredOrders=total['non_delivered'], invalidDateOrders=total['invalid_dates'],
            monthly=delivery_months, states=delivery_states, categories=delivery_categories),
        'customers': dict(
            **review_metrics(total), uniqueCustomers=repeat['customers'],
            oneTimeCustomers=repeat['customers'] - repeat['repeats'],
            repeatCustomers=repeat['repeats'],
            repeatCustomerPct=rounded(repeat['repeats'] * 100, repeat['customers']),
            repeatOrders=repeat['repeat_orders'], repeatCents=repeat['repeat_cents'],
            repeatOrderPct=rounded(repeat['repeat_orders'] * 100, total['sales_orders']),
            repeatSalesPct=rounded(repeat['repeat_cents'] * 100, total['cents']),
            distribution=review_distribution, deliveryComparison=delivery_comparison,
            states=review_states, topSpenders=spenders),
    }


def compare(actual, expected, path='result'):
    """Compare every member, including order, nulls and exact integer amounts."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError('{}: field names differ: {} / {}'.format(path, list(actual), list(expected)))
        return sum(compare(actual[key], value, path + '.' + key) for key, value in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError('{}: row count differs'.format(path))
        return sum(compare(a, e, '{}[{}]'.format(path, index))
                   for index, (a, e) in enumerate(zip(actual, expected)))
    if isinstance(expected, float):
        valid = (isinstance(actual, (int, float)) and math.isfinite(actual)
                 and math.isclose(actual, expected, rel_tol=0, abs_tol=0.00000001))
    else:
        valid = actual == expected
    if not valid:
        raise ValueError('{}: expected {!r}, got {!r}'.format(path, expected, actual))
    return 1


NODE_RUNNER = r"""
const fs = require('node:fs');
const options = JSON.parse(fs.readFileSync(0, 'utf8'));
require(options.data);
const metrics = require(options.metrics);
const payload = globalThis.OLIST_DATA;
if (!payload) throw new Error('OLIST_DATA was not loaded');
function checkFinite(value, path) {
  if (typeof value === 'number' && !Number.isFinite(value)) {
    throw new Error(path + ' is NaN or infinite');
  }
  if (value && typeof value === 'object') {
    for (const [key, nested] of Object.entries(value)) checkFinite(nested, path + '.' + key);
  }
}
checkFinite(payload, 'data');
const snapshots = {};
for (const scenario of options.scenarios) {
  const output = metrics.compute(payload, scenario.filters);
  checkFinite(output, scenario.name);
  snapshots[scenario.name] = output;
}
process.stdout.write(JSON.stringify({
  nodeVersion: process.version,
  dimensions: Object.fromEntries(['months','states','statuses','categoryLabels'].map(key=>[key,payload[key]])),
  fields: payload.fields, categoryFields: payload.categoryFields,
  orderRows: payload.orders.length, categoryRows: payload.categories.length,
  snapshots
}));
"""


def published_checks(snapshot):
    previous = {part: json.loads((PROJECT / 'results' / ('part{}_validation.json'.format(part))).read_text())['overall']
                for part in (4, 5, 6)}
    mappings = {
        4: [('sales', 'orders', 'sales_orders'), ('sales', 'cents', 'product_sales_cents'),
            ('sales', 'aov', 'average_order_value')],
        5: [('delivery', 'orders', 'delivery_orders'), ('delivery', 'lateOrders', 'late_orders'),
            ('delivery', 'latePct', 'late_delivery_pct'), ('delivery', 'averageDays', 'average_delivery_days'),
            ('delivery', 'averagePositiveDelayDays', 'average_positive_delay_days')],
        6: [('customers', 'reviewedOrders', 'reviewed_orders'),
            ('customers', 'missingReviewOrders', 'missing_review_orders'),
            ('customers', 'reviewCoveragePct', 'review_coverage_pct'),
            ('customers', 'scoreSum', 'review_score_sum'), ('customers', 'averageScore', 'average_review_score'),
            ('customers', 'lowScoreOrders', 'low_score_orders'), ('customers', 'lowScorePct', 'low_score_pct'),
            ('customers', 'uniqueCustomers', 'total_customers'),
            ('customers', 'repeatCustomers', 'repeat_customers'),
            ('customers', 'repeatCustomerPct', 'repeat_customer_pct')],
    }
    checks = []
    for part, fields in mappings.items():
        for section, field, source in fields:
            observed, expected = snapshot[section][field], previous[part][source]
            compare(observed, expected, 'published part{}.{}'.format(part, source))
            checks.append({'part': part, 'metric': section + '.' + field,
                           'actual': observed, 'published': expected, 'status': 'PASS'})
    return checks


def validate(args):
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError('Database missing; prepare Parts 2, 3 and 7 first')
    node = shutil.which(args.node)
    if node is None:
        raise RuntimeError('Node.js is needed to run the actual dashboard calculation code')
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA temp_store = MEMORY')
        connection.execute('BEGIN')
        if [row[0] for row in connection.execute('PRAGMA integrity_check')] != ['ok']:
            raise ValueError('SQLite integrity check failed')
        fingerprints = source_fingerprints(connection)
        with (PROJECT / 'results/part2_import_log.csv').open(encoding='utf-8', newline='') as handle:
            recorded = {row['table_name']: row['logical_rows_sha256'] for row in csv.DictReader(handle)}
        compare({row['table_name']: row['logical_rows_sha256'] for row in fingerprints},
                recorded, 'published source fingerprints')
        connection.execute("""CREATE TEMP TABLE qa_orders AS SELECT *,
            CASE WHEN delivery_eligible = 1 THEN
                CAST(STRFTIME('%s', order_delivered_customer_date) AS INTEGER)
                - CAST(STRFTIME('%s', order_purchase_timestamp) AS INTEGER)
            END AS elapsed_seconds FROM v_reporting_orders""")
        connection.execute('CREATE TEMP TABLE qa_items AS SELECT * FROM v_reporting_sales_items')
        connection.execute('CREATE TEMP TABLE qa_order_categories AS SELECT * FROM v_reporting_order_categories')
        connection.execute('CREATE INDEX qa_item_order ON qa_items(order_id)')
        connection.execute('CREATE INDEX qa_category_order ON qa_order_categories(order_id)')
        dimensions = {
            'months': [row[0] for row in connection.execute('SELECT DISTINCT purchase_month FROM qa_orders ORDER BY purchase_month')],
            'states': [row[0] for row in connection.execute('SELECT DISTINCT customer_state FROM qa_orders ORDER BY customer_state')],
            'statuses': [row[0] for row in connection.execute('SELECT DISTINCT order_status FROM qa_orders ORDER BY order_status')],
            'categoryLabels': [row[0] for row in connection.execute(
                'SELECT category_label FROM qa_items UNION SELECT category_label FROM qa_order_categories ORDER BY category_label')],
        }
        customer_ids = {row[0]: index for index, row in enumerate(connection.execute(
            'SELECT DISTINCT customer_unique_id FROM qa_orders ORDER BY customer_unique_id'))}
        months, states = dimensions['months'], dimensions['states']

        def scenario(name, start='2017-02', end='2018-07', state='all'):
            return {'name': name, 'description': '{} through {}, buyer state {}'.format(start, end, state),
                    'filters': {'startMonth': months.index(start), 'endMonth': months.index(end),
                                'state': 'all' if state == 'all' else states.index(state)}}

        scenarios = [scenario('all'), scenario('march_2018', '2018-03', '2018-03'),
                     scenario('sao_paulo', state='SP'), scenario('rio_de_janeiro', state='RJ'),
                     scenario('march_2018_rj', '2018-03', '2018-03', 'RJ'),
                     scenario('february_to_july_2018', '2018-02', '2018-07'),
                     scenario('roraima', state='RR'),
                     scenario('empty_august_2017_roraima', '2017-08', '2017-08', 'RR')]
        options = {'data': str((PROJECT / 'dashboard/data.js').resolve()),
                   'metrics': str((PROJECT / 'dashboard/metrics.js').resolve()), 'scenarios': scenarios}
        print('Checking dashboard JavaScript with Node...', flush=True)
        process = subprocess.run([node, '-e', NODE_RUNNER], input=json.dumps(options),
                                 text=True, capture_output=True, check=True, timeout=120)
        browser_math = json.loads(process.stdout)
        compare(browser_math['dimensions'], dimensions, 'data dictionaries')
        compare(browser_math['fields'], FIELDS, 'order field contract')
        compare(browser_math['categoryFields'], CATEGORY_FIELDS, 'category field contract')
        order_count = connection.execute('SELECT COUNT(*) FROM qa_orders').fetchone()[0]
        compare(browser_math['orderRows'], order_count, 'exported order rows')
        expected_category_count = connection.execute("""SELECT COUNT(*) FROM (
            SELECT order_id, category_label FROM qa_items
            UNION SELECT order_id, category_label FROM qa_order_categories)""").fetchone()[0]
        compare(browser_math['categoryRows'], expected_category_count, 'exported category rows')
        evidence = []
        for item in scenarios:
            print('Checking {} against SQLite...'.format(item['name']), flush=True)
            expected = expected_snapshot(connection, item['filters'], dimensions, customer_ids)
            actual = browser_math['snapshots'][item['name']]
            cells = compare(actual, expected, item['name'])
            evidence.append(dict(item, status='PASS', cells_checked=cells,
                                 selected_orders=actual['selectedOrders'],
                                 sales_orders=actual['sales']['orders'], product_sales_cents=actual['sales']['cents'],
                                 delivery_orders=actual['delivery']['orders'], reviewed_orders=actual['customers']['reviewedOrders'],
                                 customers=actual['customers']['uniqueCustomers'],
                                 repeat_customers=actual['customers']['repeatCustomers'],
                                 headline_metrics={
                                     'average_order_value': actual['sales']['aov'],
                                     'late_delivery_pct': actual['delivery']['latePct'],
                                     'average_delivery_days': actual['delivery']['averageDays'],
                                     'average_positive_delay_days': actual['delivery']['averagePositiveDelayDays'],
                                     'review_coverage_pct': actual['customers']['reviewCoveragePct'],
                                     'average_review_score': actual['customers']['averageScore'],
                                     'low_score_pct': actual['customers']['lowScorePct'],
                                     'repeat_customer_pct': actual['customers']['repeatCustomerPct'],
                                 },
                                 group_rows={
                                     'months': len(actual['sales']['monthly']),
                                     'sales_categories': len(actual['sales']['categories']),
                                     'sales_states': len(actual['sales']['states']),
                                     'delivery_categories': len(actual['delivery']['categories']),
                                     'review_states': len(actual['customers']['states']),
                                     'top_customers': len(actual['customers']['topSpenders']),
                                 },
                                 snapshot_sha256=hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()))
        empty = browser_math['snapshots']['empty_august_2017_roraima']
        compare(empty['selectedOrders'], 0, 'empty slice really has no orders')
        for section, fields in {'sales': ['aov'], 'delivery': ['latePct', 'averageDays', 'averagePositiveDelayDays'],
                                'customers': ['reviewCoveragePct', 'averageScore', 'lowScorePct', 'repeatCustomerPct']}.items():
            for field in fields:
                compare(empty[section][field], None, 'empty slice {}.{}'.format(section, field))
        prior = published_checks(browser_math['snapshots']['all'])
    finally:
        connection.close()

    dependencies = ['dashboard/data.js', 'dashboard/metrics.js', 'scripts/validate_dashboard.py',
                    'sql/07_reporting_views.sql', 'sql/08_dashboard_export.sql',
                    'scripts/prepare_part3.py', 'scripts/build_database.py',
                    'results/part2_import_log.csv',
                    'results/part4_validation.json', 'results/part5_validation.json',
                    'results/part6_validation.json']
    report = {
        'part': 8, 'status': 'PASS', 'scope': 'dashboard data and calculations in Node; independent SQLite comparisons',
        'database_access': 'read-only; temporary tables held in the validation connection',
        'python_version': sys.version.split()[0], 'sqlite_version': sqlite3.sqlite_version,
        'node_version': browser_math['nodeVersion'], 'source_tables': fingerprints,
        'dependency_sha256': {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in dependencies},
        'input_contract': {'status': 'PASS', 'order_rows': order_count, 'category_rows': expected_category_count,
                           'dimensions_match_sqlite': True, 'fields_match_contract': True},
        'scenarios_passed': len(evidence), 'cells_checked': sum(item['cells_checked'] for item in evidence),
        'scenarios': evidence, 'published_metric_checks_passed': len(prior), 'published_metric_checks': prior,
        'nonfinite_numbers': 'None in exported inputs or calculated snapshots; checked before JSON serialization',
        'empty_slice': 'August 2017, RR has zero source orders; undefined means and rates remain null',
        'limitations': ['Browser rendering, control interactions, accessibility and hosting were not tested by this script.'],
    }
    destination = args.results_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'part8_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lines = ['PART 8 DASHBOARD CALCULATION VALIDATION',
             'PASS: {} filter scenarios; {} compared values'.format(len(evidence), report['cells_checked']),
             'PASS: {} default metrics match published Parts 4–6'.format(len(prior)), '',
             'Node executed dashboard/metrics.js using dashboard/data.js.',
             'Expected groups and totals were calculated independently in SQLite.',
             'All counts, cents, timing sums, means, rates, category/state rows and customer groups matched.', '']
    lines.extend('PASS: {} — {} orders, {} values checked'.format(
        item['description'], item['selected_orders'], item['cells_checked']) for item in evidence)
    lines.extend(['', 'PASS: no NaN or infinite numbers before JSON serialization.',
                  'PASS: empty August 2017 / RR slice retains null means and rates.', '',
                  'Scope: data and calculation checks only. Browser rendering, controls, accessibility and hosting are untested here.'])
    (destination / 'part8_validation.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('PASS: {} scenarios / {} values; {} published metric checks.'.format(
        len(evidence), report['cells_checked'], len(prior)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=PROJECT / 'ecommerce_olist.db')
    parser.add_argument('--results-dir', type=Path, default=PROJECT / 'results')
    parser.add_argument('--node', default='node')
    args = parser.parse_args()
    try:
        validate(args)
    except (ValueError, KeyError, OSError, sqlite3.Error, RuntimeError,
            subprocess.SubprocessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            parser.exit(1, 'Dashboard validation failed: {}\n'.format(error.stderr))
        parser.exit(1, 'Dashboard validation failed: {}\n'.format(error))


if __name__ == '__main__':
    main()
