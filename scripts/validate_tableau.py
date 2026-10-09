#!/usr/bin/env python3
"""Check Tableau package structure, references and data calculations offline.

The CSV calculations are independently checked against SQLite. XML schema and
reference checks are structural checks, not execution by the Tableau engine.
"""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
import zipfile

from lxml import etree
from prepare_part3 import source_fingerprints
from validate_dashboard import compare, expected_snapshot, published_checks

PROJECT = Path(__file__).resolve().parents[1]
TABLEAU = PROJECT / 'tableau'
SCHEMA = TABLEAU / 'schema/twb_2026.1.0.xsd'
WORKBOOK = 'Olist_Commerce_Review.twb'
PACKAGE = 'Olist_Commerce_Review.twbx'
ORDER_FIELDS = ('order_key', 'customer_key', 'purchase_month', 'buyer_state', 'order_status',
                'sales_eligible', 'delivery_eligible', 'review_eligible', 'product_value_cents',
                'delivery_seconds', 'is_late', 'positive_delay_days', 'review_score', 'review_before_delivery')
CATEGORY_FIELDS = ('order_key', 'category', 'purchase_month', 'buyer_state', 'sales_eligible',
                   'product_value_cents', 'item_count', 'delivery_eligible', 'is_late',
                   'delivery_seconds', 'positive_delay_days')
TEXT_FIELDS = {'purchase_month', 'buyer_state', 'order_status', 'category'}


def load_schema(path=SCHEMA):
    """Resolve the schema's two location-free imports without network access.

    Tableau's user namespace is an open extension point. Standard XML
    attributes have their normal XML types. The vendored XSD stays unchanged.
    """
    xs = 'http://www.w3.org/2001/XMLSchema'
    user = 'http://www.tableausoftware.com/xml/user'
    xml = 'http://www.w3.org/XML/1998/namespace'
    stubs = {
        user: '''<xs:schema xmlns:xs="{xs}" targetNamespace="{ns}" elementFormDefault="qualified">
          <xs:attributeGroup name="UserAttributes-AG"><xs:anyAttribute namespace="##any" processContents="lax"/></xs:attributeGroup>
          <xs:element name="localizable"><xs:complexType><xs:anyAttribute namespace="##any" processContents="lax"/></xs:complexType></xs:element>
        </xs:schema>'''.format(xs=xs, ns=user),
        xml: '''<xs:schema xmlns:xs="{xs}" targetNamespace="{ns}">
          <xs:attribute name="base" type="xs:anyURI"/>
          <xs:attribute name="lang"><xs:simpleType><xs:union memberTypes="xs:language"><xs:simpleType><xs:restriction base="xs:string"><xs:enumeration value=""/></xs:restriction></xs:simpleType></xs:union></xs:simpleType></xs:attribute>
          <xs:attribute name="space"><xs:simpleType><xs:restriction base="xs:NCName"><xs:enumeration value="default"/><xs:enumeration value="preserve"/></xs:restriction></xs:simpleType></xs:attribute>
          <xs:attribute name="id" type="xs:ID"/>
        </xs:schema>'''.format(xs=xs, ns=xml),
    }
    locations = {'urn:olist:tableau-schema-import:' + str(index): value
                 for index, value in enumerate(stubs.values())}
    by_namespace = dict(zip(stubs, locations))

    class Resolver(etree.Resolver):
        def resolve(self, url, public_id, context):
            if url in locations:
                return self.resolve_string(locations[url], context)
            raise ValueError('Unexpected external schema dependency: ' + url)

    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    parser.resolvers.add(Resolver())
    document = etree.fromstring(Path(path).read_bytes(), parser)
    for imported in document.findall('{' + xs + '}import'):
        namespace = imported.get('namespace')
        if namespace in by_namespace and not imported.get('schemaLocation'):
            imported.set('schemaLocation', by_namespace[namespace])
    return etree.XMLSchema(document)


def read_csv_bytes(content, fields):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
    if tuple(reader.fieldnames or ()) != fields:
        raise ValueError('Unexpected Tableau CSV columns')
    result = []
    for raw in reader:
        result.append({key: value if key in TEXT_FIELDS else int(value) if value else None
                       for key, value in raw.items()})
    return result


def ratio(numerator, denominator=1):
    if not denominator:
        return None
    return float((Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP))


def group():
    return {'all': 0, 'orders': 0, 'cents': 0, 'delivered': 0, 'late': 0, 'seconds': 0,
            'delay': 0, 'reviewed': 0, 'score': 0, 'low': 0, 'pre': 0,
            'non_delivered': 0, 'invalid_date': 0}


def add_delivery(target, row):
    if row['delivery_eligible'] == 1:
        target['delivered'] += 1
        target['seconds'] += row['delivery_seconds']
        if row['is_late'] == 1:
            target['late'] += 1
            target['delay'] += row['positive_delay_days']


def add_order(target, row):
    target['all'] += 1
    target['non_delivered'] += row['order_status'] != 'delivered'
    target['invalid_date'] += row['order_status'] == 'delivered' and row['delivery_eligible'] == 0
    add_delivery(target, row)
    if row['sales_eligible'] == 1:
        target['orders'] += 1
        target['cents'] += row['product_value_cents']
        if row['review_eligible'] == 1:
            target['reviewed'] += 1
            target['score'] += row['review_score']
            target['low'] += row['review_score'] in (1, 2)
            target['pre'] += row['delivery_eligible'] == 1 and row['review_before_delivery'] == 1


def delivery_result(g):
    return {'orders': g['delivered'], 'lateOrders': g['late'], 'onTimeOrders': g['delivered'] - g['late'],
            'latePct': ratio(g['late'] * 100, g['delivered']),
            'averageDays': ratio(g['seconds'], g['delivered'] * 86400),
            'averagePositiveDelayDays': ratio(g['delay'], g['late']),
            'elapsedSeconds': g['seconds'], 'positiveDelayDays': g['delay']}


def review_result(g):
    return {'salesOrders': g['orders'], 'reviewedOrders': g['reviewed'],
            'missingReviewOrders': g['orders'] - g['reviewed'],
            'reviewCoveragePct': ratio(g['reviewed'] * 100, g['orders']),
            'scoreSum': g['score'], 'averageScore': ratio(g['score'], g['reviewed']),
            'lowScoreOrders': g['low'], 'lowScorePct': ratio(g['low'] * 100, g['reviewed'])}


def csv_snapshot(orders, categories, filters, dimensions):
    """Compute the numerical specification from packaged CSVs using Python."""
    from fractions import Fraction
    months, states, labels = (dimensions[key] for key in ('months', 'states', 'categoryLabels'))
    first, last, state = filters['startMonth'], filters['endMonth'], filters['state']
    selected = {row['order_key']: row for row in orders
                if months[first] <= row['purchase_month'][:7] <= months[last]
                and (state == 'all' or row['buyer_state'] == states[state])}
    total = group()
    by_month = {month: group() for month in months[first:last + 1]}
    by_state, by_customer = defaultdict(group), defaultdict(group)
    distribution = Counter()
    comparison = {0: group(), 1: group()}
    for row in selected.values():
        add_order(total, row)
        add_order(by_month[row['purchase_month'][:7]], row)
        add_order(by_state[row['buyer_state']], row)
        if row['sales_eligible']:
            add_order(by_customer[row['customer_key']], row)
            distribution[row['review_score'] if row['review_eligible'] else None] += 1
            if row['delivery_eligible']:
                add_order(comparison[row['is_late']], row)
    category_sales = defaultdict(lambda: {'orders': 0, 'items': 0, 'cents': 0})
    category_deliveries = defaultdict(group)
    for row in categories:
        if row['order_key'] not in selected:
            continue
        if row['sales_eligible']:
            g = category_sales[row['category']]
            g['orders'] += 1
            g['items'] += row['item_count']
            g['cents'] += row['product_value_cents']
        if row['delivery_eligible']:
            add_delivery(category_deliveries[row['category']], row)

    sales_months = []
    delivery_months = []
    for month, g in by_month.items():
        sales_months.append({'monthIndex': months.index(month), 'month': month, 'allOrders': g['all'],
                             'orders': g['orders'], 'cents': g['cents'], 'value': ratio(g['cents'], 100),
                             'aov': ratio(g['cents'], g['orders'] * 100), 'excludedOrders': g['all'] - g['orders']})
        delivery_months.append(dict(monthIndex=months.index(month), month=month, allOrders=g['all'],
                                     excludedOrders=g['all'] - g['delivered'], **delivery_result(g)))
    sales_categories = []
    for label in sorted(category_sales, key=lambda k: (-category_sales[k]['cents'], k)):
        g = category_sales[label]
        sales_categories.append({'categoryId': labels.index(label), 'label': label, 'orders': g['orders'],
                                 'itemCount': g['items'], 'cents': g['cents'], 'value': ratio(g['cents'], 100),
                                 'sharePct': ratio(g['cents'] * 100, total['cents'])})
    sales_states = []
    for label in sorted(by_state, key=lambda k: (-by_state[k]['cents'], k)):
        g = by_state[label]
        if g['orders']:
            sales_states.append({'stateId': states.index(label), 'label': label, 'orders': g['orders'],
                                 'cents': g['cents'], 'value': ratio(g['cents'], 100),
                                 'aov': ratio(g['cents'], g['orders'] * 100),
                                 'sharePct': ratio(g['cents'] * 100, total['cents'])})

    def delivery_key(label, groups):
        g = groups[label]
        return (-g['late'], -Fraction(g['late'], g['delivered']) if g['delivered'] else 0, label)

    delivery_states = [dict(stateId=states.index(label), label=label, **delivery_result(by_state[label]))
                       for label in sorted(by_state, key=lambda k: delivery_key(k, by_state))
                       if by_state[label]['delivered']]
    delivery_categories = [dict(categoryId=labels.index(label), label=label, **delivery_result(category_deliveries[label]))
                           for label in sorted(category_deliveries, key=lambda k: delivery_key(k, category_deliveries))]
    review_distribution = [{'score': score, 'label': str(score) if score is not None else 'No eligible selected review',
                            'orders': distribution[score], 'shareOfSalesPct': ratio(distribution[score] * 100, total['orders']),
                            'shareOfReviewedPct': ratio(distribution[score] * 100, total['reviewed']) if score is not None else None}
                           for score in (1, 2, 3, 4, 5, None)]
    review_comparison = [dict(key=key, label=label, **review_result(comparison[flag]),
                             preDeliveryReviewOrders=comparison[flag]['pre'])
                        for flag, key, label in ((0, 'on_time', 'On time'), (1, 'late', 'Late'))]

    def review_key(label):
        g = by_state[label]
        return (-g['low'], not g['reviewed'], -Fraction(g['low'], g['reviewed']) if g['reviewed'] else 0, label)

    review_states = [dict(stateId=states.index(label), label=label, **review_result(by_state[label]))
                     for label in sorted(by_state, key=review_key) if by_state[label]['orders']]
    spenders = []
    for key in sorted(by_customer, key=lambda k: (-by_customer[k]['cents'], k))[:20]:
        g = by_customer[key]
        spenders.append({'customerId': key - 1, 'label': 'Customer ' + str(key).zfill(6), 'orders': g['orders'],
                         'cents': g['cents'], 'value': ratio(g['cents'], 100), 'aov': ratio(g['cents'], g['orders'] * 100),
                         'reviewedOrders': g['reviewed'], 'averageScore': ratio(g['score'], g['reviewed']),
                         'reviewCoveragePct': ratio(g['reviewed'] * 100, g['orders'])})
    repeat = [g for g in by_customer.values() if g['orders'] >= 2]
    repeat_orders = sum(g['orders'] for g in repeat)
    repeat_cents = sum(g['cents'] for g in repeat)
    return {
        'filters': filters, 'selectedOrders': total['all'],
        'sales': {'orders': total['orders'], 'cents': total['cents'], 'value': ratio(total['cents'], 100),
                  'aov': ratio(total['cents'], total['orders'] * 100), 'uniqueCustomers': len(by_customer),
                  'excludedOrders': total['all'] - total['orders'], 'monthly': sales_months,
                  'categories': sales_categories, 'states': sales_states},
        'delivery': dict(**delivery_result(total), excludedOrders=total['all'] - total['delivered'],
                         nonDeliveredOrders=total['non_delivered'], invalidDateOrders=total['invalid_date'],
                         monthly=delivery_months, states=delivery_states, categories=delivery_categories),
        'customers': dict(**review_result(total), uniqueCustomers=len(by_customer),
                          oneTimeCustomers=len(by_customer) - len(repeat), repeatCustomers=len(repeat),
                          repeatCustomerPct=ratio(len(repeat) * 100, len(by_customer)),
                          repeatOrders=repeat_orders, repeatCents=repeat_cents,
                          repeatOrderPct=ratio(repeat_orders * 100, total['orders']),
                          repeatSalesPct=ratio(repeat_cents * 100, total['cents']),
                          distribution=review_distribution, deliveryComparison=review_comparison,
                          states=review_states, topSpenders=spenders),
    }


def inspect_workbook(document):
    """Check the named references that the official XSD deliberately skips."""
    root = etree.fromstring(document, etree.XMLParser(no_network=True, resolve_entities=False))
    load_schema().assertValid(root)
    if root.tag != 'workbook' or root.get('version') != '26.1':
        raise ValueError('Expected a Tableau 26.1 workbook')
    sources = {node.get('name'): node for node in root.findall('./datasources/datasource')}
    if set(sources) != {'Parameters', 'olist.orders', 'olist.categories'}:
        raise ValueError('Expected two independent CSV sources and shared parameters')
    global_fields = {name: {col.get('name'): col for col in node.findall('./column')}
                     for name, node in sources.items()}
    if set(global_fields['Parameters']) != {'[StartMonth]', '[EndMonth]', '[BuyerState]'}:
        raise ValueError('Shared date/state parameters are missing')
    parameter_checks = []
    for name, datatype, default in (('[StartMonth]', 'date', '#2017-02-01#'),
                                     ('[EndMonth]', 'date', '#2018-07-01#'),
                                     ('[BuyerState]', 'string', '"All"')):
        column = global_fields['Parameters'][name]
        if column.get('datatype') != datatype or column.get('value') != default:
            raise ValueError('Wrong parameter type/default: ' + name)
        values = [member.get('value') for member in column.findall('./members/member')]
        if column.get('param-domain-type') != 'list' or not values or len(values) != len(set(values)) or default not in values:
            raise ValueError('Invalid parameter choice list: ' + name)
        parameter_checks.append({'name': name, 'datatype': datatype, 'default': default,
                                 'allowed_values': values})

    formula_count = reference_count = 0
    formula_evidence = []
    references = {}
    for source_name, fields in global_fields.items():
        references[source_name] = {}
        for name, column in fields.items():
            calculation = column.find('./calculation')
            if calculation is None:
                continue
            formula = calculation.get('formula', '')
            formula_count += 1
            refs = set()
            for first, second in re.findall(r'(\[[^\]]+\])(?:\.(\[[^\]]+\]))?', formula):
                if second:
                    target_source = first[1:-1]
                    if target_source not in global_fields or second not in global_fields[target_source]:
                        raise ValueError('Unknown qualified calculated-field reference: ' + first + '.' + second)
                    refs.add((target_source, second))
                else:
                    if first not in fields:
                        raise ValueError('Unknown calculated-field reference in {}.{}: {}'.format(source_name, name, first))
                    refs.add((source_name, first))
                reference_count += 1
            references[source_name][name] = refs
            formula_evidence.append({'source': source_name, 'field': name, 'formula': formula})

    def expanded(source, field, active=None):
        active = set() if active is None else set(active)
        key = (source, field)
        if key in active:
            raise ValueError('Circular calculated-field dependency: ' + str(key))
        active.add(key)
        result = set(references.get(source, {}).get(field, set()))
        for target in list(result):
            result.update(expanded(*target, active))
        return result

    for source, fields in references.items():
        for field in fields:
            expanded(source, field)
    lods = []
    for item in formula_evidence:
        if re.search(r'\{\s*FIXED\s+\[customer_key\]', item['formula'], re.I):
            required = {('Parameters', '[StartMonth]'), ('Parameters', '[EndMonth]'),
                        ('Parameters', '[BuyerState]'), ('olist.orders', '[sales_eligible]')}
            if not required.issubset(expanded(item['source'], item['field'])):
                raise ValueError('Customer FIXED calculation does not include all selection rules')
            if not re.search(r'COUNTD\s*\(', item['formula'], re.I):
                raise ValueError('Customer order LOD must count distinct order keys')
            lods.append(item['field'])
    if not lods:
        raise ValueError('No parameter-aware customer order LOD found')
    repeat_formula = global_fields['olist.orders']['[Repeat Customers]'].find('./calculation').get('formula')
    if not re.search(r'^COUNTD\s*\(.*\[Customer Selected Orders\]\s*>=\s*2.*THEN\s+\[customer_key\]',
                     repeat_formula, re.I | re.S):
        raise ValueError('Repeat customers must count distinct selected customer keys, not repeated order rows')

    source_paths = []
    for name in ('olist.orders', 'olist.categories'):
        source = sources[name]
        if source.findall('.//relation[@type="join"]'):
            raise ValueError('Order and category sources must not be physically joined')
        connections = source.findall('.//connection[@class="textscan"]')
        if len(connections) != 1:
            raise ValueError('Expected one text-file connection per data source')
        connection = connections[0]
        filename, directory = connection.get('filename', ''), connection.get('directory', '')
        path = PurePosixPath(directory) / filename
        if path.is_absolute() or '..' in path.parts or '\\' in str(path):
            raise ValueError('Workbook contains a nonportable file reference: ' + str(path))
        wanted = 'data/orders.csv' if name == 'olist.orders' else 'data/categories.csv'
        if str(path) != wanted:
            raise ValueError('Unexpected workbook file reference: ' + str(path))
        source_paths.append(str(path))
        expected_fields = ORDER_FIELDS if name == 'olist.orders' else CATEGORY_FIELDS
        for field in expected_fields:
            node = global_fields[name].get('[' + field + ']')
            datatype = 'date' if field == 'purchase_month' else 'string' if field in TEXT_FIELDS else 'integer'
            if node is None or node.get('datatype') != datatype:
                raise ValueError('Missing/mistyped CSV field: ' + name + '.' + field)

    worksheets = root.findall('./worksheets/worksheet')
    names = [node.get('name') for node in worksheets]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate worksheet names')
    dependency_count = shelf_reference_count = 0
    for sheet in worksheets:
        sheet_fields = {}
        for dependency in sheet.findall('.//datasource-dependencies'):
            source = dependency.get('datasource')
            if source not in sources:
                raise ValueError('Worksheet refers to an unknown data source')
            local = {node.get('name'): node for node in dependency.findall('./column')}
            for name, column in local.items():
                if name not in global_fields[source]:
                    raise ValueError('Worksheet contains an undeclared field: ' + source + '.' + name)
                declared = global_fields[source][name]
                local_calc, global_calc = column.find('./calculation'), declared.find('./calculation')
                if local_calc is not None and (global_calc is None or local_calc.get('formula') != global_calc.get('formula')):
                    raise ValueError('Worksheet calculation differs from its data source: ' + name)
                dependency_count += 1
            for instance in dependency.findall('./column-instance'):
                if instance.get('column') not in global_fields[source]:
                    raise ValueError('Column instance refers to a missing field: ' + str(instance.attrib))
                dependency_count += 1
            sheet_fields[source] = set(local) | {node.get('name') for node in dependency.findall('./column-instance')}
        # Shelves, mark encodings and filters refer to column instances, not
        # just to the original datasource fields.
        reference_texts = [sheet.findtext('./table/rows', ''), sheet.findtext('./table/cols', '')]
        reference_texts += [node.get('column', '') for node in sheet.findall('.//*[@column]')
                           if node.tag != 'column-instance']
        reference_texts += [node.text or '' for node in sheet.findall('.//formatted-text/run')]
        for text in reference_texts:
            for source, field in re.findall(r'\[([^\]]+)\]\.\[([^\]]+)\]', text):
                if '[' + field + ']' not in sheet_fields.get(source, set()):
                    raise ValueError('Worksheet shelf/mark refers to an undeclared instance: ' + source + '.' + field)
                shelf_reference_count += 1
        if not sheet.findtext('./table/rows') and not sheet.findtext('./table/cols') and sheet.findall('./table/view/filter'):
            raise ValueError('KPI worksheet filters would remove its empty-slice aggregate row')
    dashboards = root.findall('./dashboards/dashboard')
    if len(dashboards) != 3:
        raise ValueError('Expected Sales, Delivery and Customers dashboards')
    dashboard_sheets = []
    for dashboard in dashboards:
        parameter_controls = [zone.get('param') for zone in dashboard.findall('.//zone[@type-v2="paramctrl"]')]
        if set(parameter_controls) != {'[Parameters].' + name for name in global_fields['Parameters']} or len(parameter_controls) != 3:
            raise ValueError('Each dashboard must expose the three shared parameters')
        for zone in dashboard.findall('.//zone'):
            name = zone.get('name')
            if name and zone.get('type-v2') not in ('paramctrl', 'filter', 'text'):
                if name not in names:
                    raise ValueError('Dashboard references a missing worksheet: ' + name)
                dashboard_sheets.append(name)
    if set(dashboard_sheets) != set(names):
        raise ValueError('At least one worksheet is not connected to a dashboard')
    return {'official_xsd': 'PASS', 'version': '26.1', 'worksheets': names,
            'dashboards': [node.get('name') for node in dashboards], 'parameters': parameter_checks,
            'file_references': source_paths, 'calculated_fields': formula_count,
            'formula_references_checked': reference_count, 'worksheet_dependencies_checked': dependency_count,
            'shelf_mark_references_checked': shelf_reference_count,
            'customer_lod_fields': lods, 'formula_manifest': formula_evidence,
            'formula_execution': 'Not run in Tableau; references and customer selection invariants checked offline'}


def check_native_charts(connection, orders, scenario):
    """Check the two native charts that are not in the earlier metric schema."""
    selected = [row for row in orders
                if scenario['start_month'] <= row['purchase_month'] <= scenario['end_month']
                and (scenario['buyer_state'] == 'All' or row['buyer_state'] == scenario['buyer_state'])]
    customers = Counter(row['customer_key'] for row in selected if row['sales_eligible'])
    frequency = Counter(min(count, 4) for count in customers.values())
    actual_frequency = [{'orders_bucket': bucket, 'customers': count}
                        for bucket, count in sorted(frequency.items())]
    expected_frequency = [dict(row) for row in connection.execute('''
        WITH counts AS (
          SELECT customer_unique_id, COUNT(DISTINCT order_id) AS orders
          FROM qa_selected WHERE sales_eligible = 1 GROUP BY customer_unique_id
        ) SELECT CASE WHEN orders >= 4 THEN 4 ELSE orders END AS orders_bucket,
                 COUNT(*) AS customers
          FROM counts GROUP BY orders_bucket ORDER BY orders_bucket
    ''')]
    monthly = defaultdict(lambda: [0, 0])
    for row in selected:
        totals = monthly[row['purchase_month'][:7]]
        if row['sales_eligible'] and row['review_eligible']:
            totals[0] += 1
            totals[1] += row['review_score']
    actual_monthly = [{'month': month, 'reviewed_orders': totals[0], 'score_sum': totals[1],
                       'average_review_score': ratio(totals[1], totals[0])}
                      for month, totals in sorted(monthly.items())]
    expected_monthly = [dict(row) for row in connection.execute('''
        SELECT purchase_month AS month,
               SUM(CASE WHEN sales_eligible = 1 AND review_eligible = 1 THEN 1 ELSE 0 END) AS reviewed_orders,
               SUM(CASE WHEN sales_eligible = 1 AND review_eligible = 1 THEN review_score ELSE 0 END) AS score_sum
        FROM qa_selected GROUP BY purchase_month ORDER BY purchase_month
    ''')]
    for row in expected_monthly:
        count, score = row['reviewed_orders'], row['score_sum']
        row['average_review_score'] = ((200 * score + count) // (2 * count)) / 100 if count else None
    checked = compare(actual_frequency, expected_frequency, scenario['name'] + ' purchase frequency')
    checked += compare(actual_monthly, expected_monthly, scenario['name'] + ' monthly reviews')
    return checked, {'purchase_frequency': actual_frequency, 'monthly_reviews': actual_monthly}


def validate(args):
    provenance = json.loads((TABLEAU / 'schema/provenance.json').read_text())
    for name, evidence in provenance['files'].items():
        compare(hashlib.sha256((TABLEAU / 'schema' / name).read_bytes()).hexdigest(), evidence['sha256'], 'vendored ' + name)
    contents = {}
    with zipfile.ZipFile(TABLEAU / PACKAGE) as archive:
        names = archive.namelist()
        wanted = {WORKBOOK, 'data/orders.csv', 'data/categories.csv', 'DATA_LICENSE.txt'}
        if set(names) != wanted or len(names) != len(wanted) or archive.testzip() is not None:
            raise ValueError('Workbook package members or ZIP checksums are invalid')
        for name in names:
            contents[name] = archive.read(name)
            source_path = PROJECT / name if name == 'DATA_LICENSE.txt' else TABLEAU / name
            if contents[name] != source_path.read_bytes():
                raise ValueError('Packaged member differs from its editable source: ' + name)
    structure = inspect_workbook(contents[WORKBOOK])
    orders = read_csv_bytes(contents['data/orders.csv'], ORDER_FIELDS)
    categories = read_csv_bytes(contents['data/categories.csv'], CATEGORY_FIELDS)
    order_map = {row['order_key']: row for row in orders}
    if len(order_map) != len(orders):
        raise ValueError('Duplicate order keys in Tableau source')
    pairs = {(row['order_key'], row['category']) for row in categories}
    if len(pairs) != len(categories):
        raise ValueError('Duplicate order/category pairs in Tableau source')
    cents_by_order = Counter()
    for row in categories:
        if row['order_key'] not in order_map:
            raise ValueError('Category row references a missing order')
        order = order_map[row['order_key']]
        if (row['purchase_month'], row['buyer_state']) != (order['purchase_month'], order['buyer_state']):
            raise ValueError('Category selection fields differ from the order')
        if row['sales_eligible']:
            cents_by_order[row['order_key']] += row['product_value_cents']
    for row in orders:
        if row['sales_eligible'] and cents_by_order[row['order_key']] != row['product_value_cents']:
            raise ValueError('Category values do not reconcile for an eligible order')

    connection = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA temp_store = MEMORY')
        connection.execute('BEGIN')
        fingerprints = source_fingerprints(connection)
        with (PROJECT / 'results/part2_import_log.csv').open(encoding='utf-8', newline='') as handle:
            recorded = {row['table_name']: row['logical_rows_sha256'] for row in csv.DictReader(handle)}
        compare({row['table_name']: row['logical_rows_sha256'] for row in fingerprints}, recorded, 'source fingerprints')
        connection.execute("""CREATE TEMP TABLE qa_orders AS SELECT *, CASE WHEN delivery_eligible = 1 THEN
            CAST(STRFTIME('%s', order_delivered_customer_date) AS INTEGER)
            - CAST(STRFTIME('%s', order_purchase_timestamp) AS INTEGER) END AS elapsed_seconds
            FROM v_reporting_orders""")
        connection.execute('CREATE TEMP TABLE qa_items AS SELECT * FROM v_reporting_sales_items')
        connection.execute('CREATE TEMP TABLE qa_order_categories AS SELECT * FROM v_reporting_order_categories')
        connection.execute('CREATE INDEX qa_item_order ON qa_items(order_id)')
        connection.execute('CREATE INDEX qa_category_order ON qa_order_categories(order_id)')
        dimensions = {
            'months': [row[0] for row in connection.execute('SELECT DISTINCT purchase_month FROM qa_orders ORDER BY purchase_month')],
            'states': [row[0] for row in connection.execute('SELECT DISTINCT customer_state FROM qa_orders ORDER BY customer_state')],
            'categoryLabels': [row[0] for row in connection.execute('SELECT category_label FROM qa_items UNION SELECT category_label FROM qa_order_categories ORDER BY category_label')],
        }
        customer_ids = {row[0]: index for index, row in enumerate(connection.execute(
            'SELECT DISTINCT customer_unique_id FROM qa_orders ORDER BY customer_unique_id'))}
        compare(len(orders), connection.execute('SELECT COUNT(*) FROM qa_orders').fetchone()[0], 'order CSV rows')
        months, states = dimensions['months'], dimensions['states']
        expected_choices = {'[StartMonth]': ['#' + month + '-01#' for month in months],
                            '[EndMonth]': ['#' + month + '-01#' for month in months],
                            '[BuyerState]': ['"' + state + '"' for state in ['All'] + states]}
        for parameter in structure['parameters']:
            compare(parameter['allowed_values'], expected_choices[parameter['name']],
                    'parameter choices ' + parameter['name'])

        def scenario(name, start='2017-02', end='2018-07', state='All'):
            return {'name': name, 'start_month': start + '-01', 'end_month': end + '-01', 'buyer_state': state,
                    'filters': {'startMonth': months.index(start), 'endMonth': months.index(end),
                                'state': 'all' if state == 'All' else states.index(state)}}

        scenarios = [scenario('all'), scenario('march_2018', '2018-03', '2018-03'),
                     scenario('sao_paulo', state='SP'), scenario('rio_de_janeiro', state='RJ'),
                     scenario('march_2018_rj', '2018-03', '2018-03', 'RJ'),
                     scenario('february_to_july_2018', '2018-02', '2018-07'), scenario('roraima', state='RR'),
                     scenario('empty_august_2017_roraima', '2017-08', '2017-08', 'RR')]
        evidence = []
        prior = []
        for item in scenarios:
            print('Checking packaged CSVs against SQLite: ' + item['name'], flush=True)
            actual = csv_snapshot(orders, categories, item['filters'], dimensions)
            expected = expected_snapshot(connection, item['filters'], dimensions, customer_ids)
            cells = compare(actual, expected, item['name'])
            chart_cells, chart_evidence = check_native_charts(connection, orders, item)
            cells += chart_cells
            if item['name'] == 'all':
                prior = published_checks(actual)
            if item['name'].startswith('empty_'):
                compare(actual['selectedOrders'], 0, 'empty selected orders')
                for section, key in [('sales', 'aov'), ('delivery', 'latePct'), ('customers', 'averageScore'),
                                     ('customers', 'repeatCustomerPct')]:
                    compare(actual[section][key], None, 'empty ' + key)
            evidence.append(dict(item, status='PASS', values_checked=cells, native_chart_checks=chart_evidence,
                                 selected_orders=actual['selectedOrders'],
                                 sales_orders=actual['sales']['orders'], product_value_cents=actual['sales']['cents'],
                                 delivery_orders=actual['delivery']['orders'], reviewed_orders=actual['customers']['reviewedOrders'],
                                 customers=actual['customers']['uniqueCustomers'], repeat_customers=actual['customers']['repeatCustomers'],
                                 average_order_value=actual['sales']['aov'], late_pct=actual['delivery']['latePct'],
                                 average_delivery_days=actual['delivery']['averageDays'],
                                 average_positive_delay_days=actual['delivery']['averagePositiveDelayDays'],
                                 average_review_score=actual['customers']['averageScore'],
                                 repeat_customer_pct=actual['customers']['repeatCustomerPct']))
    finally:
        connection.close()
    dependencies = ['scripts/validate_tableau.py', 'scripts/validate_dashboard.py', 'scripts/build_tableau.py',
                    'scripts/export_tableau.py', 'scripts/prepare_part3.py', 'scripts/build_database.py',
                    'sql/07_reporting_views.sql', 'sql/09_tableau_export.sql',
                    'tableau/' + WORKBOOK, 'tableau/' + PACKAGE, 'tableau/schema/twb_2026.1.0.xsd',
                    'tableau/schema/LICENSE', 'tableau/schema/provenance.json', 'tableau/schema/README.md', 'DATA_LICENSE.txt',
                    'results/part4_validation.json', 'results/part5_validation.json', 'results/part6_validation.json']
    report = {
        'status': 'PASS', 'validation_scope': 'Offline CSV numerical checks and native workbook structure/reference checks',
        'tableau_engine_execution': False, 'tableau_desktop_open_test': False,
        'python_version': sys.version.split()[0], 'sqlite_version': sqlite3.sqlite_version,
        'lxml_version': '.'.join(str(value) for value in etree.LXML_VERSION),
        'source_tables': fingerprints, 'schema_provenance': provenance,
        'namespace_resolution': 'Only the declared location-free Tableau user and XML namespace imports receive offline stubs; no XSD rules removed',
        'structure': structure, 'package': {'members': list(contents), 'byte_identical_to_editable_sources': True},
        'input_sha256': {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()},
        'input_rows': {'orders': len(orders), 'order_category_pairs': len(categories)},
        'dependency_sha256': {name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in dependencies},
        'scenarios_passed': len(evidence), 'values_checked': sum(row['values_checked'] for row in evidence),
        'scenarios': evidence, 'published_metric_checks': prior,
        'limitations': ['Tableau has not evaluated the workbook calculations or rendered the dashboards in this environment.',
                        'XSD validation checks syntax, not Tableau application compatibility or visual layout.',
                        'CSV scenario results validate the numerical specification; they are not captured Tableau outputs.'],
    }
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / 'tableau_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lines = ['TABLEAU OFFLINE VALIDATION', 'PASS: official 2026.1 XSD and workbook references',
             'PASS: packaged TWB, two CSV files and data license match editable sources byte for byte',
             'PASS: {} CSV/SQLite scenarios, {} compared values'.format(len(evidence), report['values_checked']),
             'PASS: {} default metrics match Parts 4–6'.format(len(prior)), '']
    lines += ['PASS: {} — {} orders, {} compared values'.format(row['name'], row['selected_orders'], row['values_checked'])
              for row in evidence]
    lines += ['', 'Tableau execution and rendering were not performed. Numerical checks use the packaged CSVs, Python and SQLite.',
              'Opening the workbook in Tableau is still required to confirm native calculation compilation and visual layout.']
    (args.results_dir / 'tableau_validation.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('PASS: native package checks; {} CSV/SQLite scenarios / {} values.'.format(len(evidence), report['values_checked']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=PROJECT / 'ecommerce_olist.db')
    parser.add_argument('--results-dir', type=Path, default=PROJECT / 'results')
    args = parser.parse_args()
    try:
        validate(args)
    except (ValueError, OSError, sqlite3.Error, etree.Error, zipfile.BadZipFile, KeyError) as error:
        parser.exit(1, 'Tableau validation failed: {}\n'.format(error))


if __name__ == '__main__':
    main()
