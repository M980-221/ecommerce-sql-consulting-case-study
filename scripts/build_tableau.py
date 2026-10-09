"""Build the editable Tableau workbook and package its two verified CSV sources.

The XML patterns follow Tableau's published workbook schema and chart samples.
Local schema checks do not execute calculations or render views in Tableau.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
VERSION = "26.1"
WORKBOOK_NAME = "Olist_Commerce_Review"
PALETTE = {"background": "#f7f5ef", "navy": "#183449", "teal": "#087f83", "copper": "#bb6845"}
USER_NS = "http://www.tableausoftware.com/xml/user"
ET.register_namespace("user", USER_NS)

ORDER_TYPES = {
    "order_key": "integer", "customer_key": "integer", "purchase_month": "date",
    "buyer_state": "string", "order_status": "string", "sales_eligible": "integer",
    "delivery_eligible": "integer", "review_eligible": "integer", "product_value_cents": "integer",
    "delivery_seconds": "integer", "is_late": "integer", "positive_delay_days": "integer",
    "review_score": "integer", "review_before_delivery": "integer",
}
CATEGORY_TYPES = {
    "order_key": "integer", "category": "string", "purchase_month": "date",
    "buyer_state": "string", "sales_eligible": "integer", "product_value_cents": "integer",
    "item_count": "integer", "delivery_eligible": "integer", "is_late": "integer",
    "delivery_seconds": "integer", "positive_delay_days": "integer",
}


def node(parent, tag, text=None, **attributes):
    element = ET.SubElement(parent, tag, {key.replace("_", "-"): str(value) for key, value in attributes.items()})
    if text is not None:
        element.text = str(text)
    return element


def identity(parent, label):
    node(parent, "simple-id", uuid="{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "olist-tableau/" + label)).upper() + "}")


def bracket(name):
    return "[" + name + "]"


def literal(value, datatype):
    return "#" + value + "#" if datatype == "date" else '"' + value.replace('"', '\\"') + '"'


def parameter(name, caption, datatype, values, default):
    column = ET.Element("column", {
        "name": bracket(name), "caption": caption, "datatype": datatype,
        "param-domain-type": "list", "role": "measure",
        "type": "ordinal" if datatype == "date" else "nominal",
        "value": literal(default, datatype),
    })
    ET.SubElement(column, "calculation", {"class": "tableau", "formula": literal(default, datatype)})
    members = node(column, "members")
    for value in values:
        node(members, "member", value=literal(value, datatype), alias=value[:7] if datatype == "date" else value)
    return column


def calculation(name, formula, datatype="real", dimension=False, number_format=None):
    column = ET.Element("column", {
        "name": bracket(name), "caption": name, "datatype": datatype,
        "role": "dimension" if dimension else "measure",
        "type": "nominal" if dimension else "quantitative",
    })
    if number_format:
        column.set("default-format", number_format)
    ET.SubElement(column, "calculation", {"class": "tableau", "formula": formula})
    return column


def ratio(numerator, denominator, percent=False):
    # A percent field is stored as a fraction and formatted p2, avoiding a second
    # multiplication by 100 in Tableau's number formatting.
    scale = 20000 if percent else 200
    divisor = 10000 if percent else 100
    return f"IF {denominator} > 0 THEN FLOOR(({scale} * {numerator} + {denominator}) / (2.0 * {denominator})) / {divisor}.0 END"


def calculated_columns(source):
    selected = ("[purchase_month] >= DATETRUNC('month', [Parameters].[StartMonth]) "
                "AND [purchase_month] <= DATETRUNC('month', [Parameters].[EndMonth]) "
                "AND ([Parameters].[BuyerState] = 'All' OR [buyer_state] = [Parameters].[BuyerState])")
    specs = [
        ("Selected", selected, "boolean", True, None),
        ("Selected Sale", "[Selected] AND [sales_eligible] = 1", "boolean", True, None),
        ("Selected Delivery", "[Selected] AND [delivery_eligible] = 1", "boolean", True, None),
        ("Selected Orders", "COUNTD(IF [Selected] THEN [order_key] END)", "integer", False, "n0"),
        ("Sales Orders", "COUNTD(IF [Selected Sale] THEN [order_key] END)", "integer", False, "n0"),
        ("Sales Cents", "SUM(IF [Selected Sale] THEN [product_value_cents] ELSE 0 END)", "integer", False, "n0"),
        ("Product Sales Value", "[Sales Cents] / 100.0", "real", False, "n2"),
        ("Average Order Value", "IF [Sales Orders] > 0 THEN FLOOR((2 * [Sales Cents] + [Sales Orders]) / (2.0 * [Sales Orders])) / 100.0 END", "real", False, "n2"),
        ("Delivery Orders", "COUNTD(IF [Selected Delivery] THEN [order_key] END)", "integer", False, "n0"),
        ("Late Orders", "COUNTD(IF [Selected Delivery] AND [is_late] = 1 THEN [order_key] END)", "integer", False, "n0"),
        ("Late Delivery Rate", ratio("[Late Orders]", "[Delivery Orders]", True), "real", False, "p2"),
        ("Delivery Seconds", "SUM(IF [Selected Delivery] THEN [delivery_seconds] ELSE 0 END)", "integer", False, "n0"),
        ("Delivery Denominator", "86400 * [Delivery Orders]", "integer", False, "n0"),
        ("Average Delivery Days", ratio("[Delivery Seconds]", "[Delivery Denominator]"), "real", False, "n2"),
        ("Positive Delay Days", "SUM(IF [Selected Delivery] AND [is_late] = 1 THEN [positive_delay_days] ELSE 0 END)", "integer", False, "n0"),
        ("Average Positive Delay", ratio("[Positive Delay Days]", "[Late Orders]"), "real", False, "n2"),
    ]
    if source == "orders":
        specs.extend([
            ("Selected Review", "[Selected Sale] AND [review_eligible] = 1", "boolean", True, None),
            ("Reviewed Orders", "COUNTD(IF [Selected Review] THEN [order_key] END)", "integer", False, "n0"),
            ("Review Score Sum", "SUM(IF [Selected Review] THEN [review_score] ELSE 0 END)", "integer", False, "n0"),
            ("Average Review Score", ratio("[Review Score Sum]", "[Reviewed Orders]"), "real", False, "n2"),
            ("Review Coverage", ratio("[Reviewed Orders]", "[Sales Orders]", True), "real", False, "p2"),
            ("Low Score Orders", "COUNTD(IF [Selected Review] AND [review_score] <= 2 THEN [order_key] END)", "integer", False, "n0"),
            ("Low Score Rate", ratio("[Low Score Orders]", "[Reviewed Orders]", True), "real", False, "p2"),
            ("Pre Delivery Reviewed Orders", "COUNTD(IF [Selected Review] AND [Selected Delivery] AND [review_before_delivery] = 1 THEN [order_key] END)", "integer", False, "n0"),
            ("Customers", "COUNTD(IF [Selected Sale] THEN [customer_key] END)", "integer", False, "n0"),
            ("Customer Selected Orders", "{ FIXED [customer_key] : COUNTD(IF [Selected Sale] THEN [order_key] END) }", "integer", False, "n0"),
            ("Repeat Customers", "COUNTD(IF [Selected Sale] AND [Customer Selected Orders] >= 2 THEN [customer_key] END)", "integer", False, "n0"),
            ("Repeat Customer Rate", ratio("[Repeat Customers]", "[Customers]", True), "real", False, "p2"),
            ("Purchase Frequency", "IF [Customer Selected Orders] = 1 THEN '1 order' ELSEIF [Customer Selected Orders] = 2 THEN '2 orders' ELSEIF [Customer Selected Orders] = 3 THEN '3 orders' ELSEIF [Customer Selected Orders] >= 4 THEN '4+ orders' END", "string", True, None),
            ("Review Bucket", "IF [review_eligible] = 1 THEN STR([review_score]) ELSE 'No selected review' END", "string", True, None),
        ])
    return [calculation(*spec) for spec in specs]


def datasource(parent, source, types):
    datasource_id = "olist." + source
    result = node(parent, "datasource", caption="Olist " + source, inline="true", name=datasource_id, version=VERSION)
    connection = ET.SubElement(result, "connection", {
        "class": "textscan", "directory": "data", "filename": source + ".csv", "password": "", "server": "",
    })
    relation = node(connection, "relation", name=source + ".csv", table=bracket(source + "#csv"), type="table")
    columns = node(relation, "columns", character_set="UTF-8", header="yes", locale="en_US", separator=",", text_qualifier='"')
    for ordinal, (name, datatype) in enumerate(types.items()):
        node(columns, "column", datatype=datatype, name=name, ordinal=ordinal)
    metadata = node(connection, "metadata-records")
    for ordinal, (name, datatype) in enumerate(types.items()):
        record = ET.SubElement(metadata, "metadata-record", {"class": "column"})
        for tag, value in [("remote-name", name), ("remote-type", {"integer": 20, "date": 133, "string": 129}[datatype]),
                           ("local-name", bracket(name)), ("parent-name", bracket(source + "#csv")),
                           ("remote-alias", name), ("ordinal", ordinal), ("local-type", datatype),
                           ("aggregation", "Year" if datatype == "date" else "Count" if datatype == "string" or name.endswith("_key") else "Sum"),
                           ("contains-null", "true")]:
            node(record, tag, value)
    node(result, "aliases", enabled="yes")
    declarations = []
    for name, datatype in types.items():
        dimension = datatype in {"string", "date"} or name.endswith("_key")
        column = node(result, "column", name=bracket(name), datatype=datatype,
                      role="dimension" if dimension else "measure",
                      type="ordinal" if datatype == "date" else "nominal" if dimension else "quantitative")
        declarations.append(column)
    for column in calculated_columns(source):
        result.append(column)
        declarations.append(column)
    return datasource_id, declarations


def instance(parent, name, metric=False, date=False):
    identifier = f"[{'usr' if metric else 'none'}:{name}:{'qk' if metric or date else 'nk'}]"
    node(parent, "column-instance", column=bracket(name), derivation="User" if metric else "None",
         name=identifier, pivot="key", type="quantitative" if metric or date else "nominal")
    return identifier


def style_rule(parent, element, formats):
    rule = node(parent, "style-rule", element=element)
    for attr, value in formats:
        node(rule, "format", attr=attr, value=value)


def worksheet(parent, spec, datasource_id, declarations, parameters):
    sheet = node(parent, "worksheet", name=spec["name"])
    layout = node(sheet, "layout-options")
    text = node(node(layout, "title"), "formatted-text")
    node(text, "run", spec["title"], bold="true", fontsize="12", fontcolor=PALETTE["navy"])
    table = node(sheet, "table")
    view = node(table, "view")
    sources = node(view, "datasources")
    node(sources, "datasource", name=datasource_id, caption="Olist " + spec["source"])
    node(sources, "datasource", name="Parameters")
    parameter_dependencies = node(view, "datasource-dependencies", datasource="Parameters")
    for parameter_column in parameters:
        parameter_dependencies.append(deepcopy(parameter_column))
    dependencies = node(view, "datasource-dependencies", datasource=datasource_id)
    for column in declarations:
        dependencies.append(deepcopy(column))
    metric_instance = instance(dependencies, spec["metric"], metric=True)
    metric_reference = bracket(datasource_id) + "." + metric_instance
    dimension_reference = None
    if spec.get("dimension"):
        dimension_instance = instance(dependencies, spec["dimension"], date=spec["kind"] == "line")
        dimension_reference = bracket(datasource_id) + "." + dimension_instance
    tooltip_fields = []
    if spec["kind"] != "kpi" and spec["page"] == "Delivery":
        tooltip_fields = ["Delivery Orders", "Late Orders"]
    elif spec["kind"] != "kpi" and spec["metric"] == "Average Review Score":
        tooltip_fields = ["Reviewed Orders"]
    tooltip_references = [
        (name, bracket(datasource_id) + "." + instance(dependencies, name, metric=True))
        for name in tooltip_fields
    ]
    if spec["kind"] != "kpi":
        filter_name = "Selected Sale" if spec.get("sales_only") else "Selected"
        selected_instance = instance(dependencies, filter_name)
        selected_reference = bracket(datasource_id) + "." + selected_instance
        filter_element = ET.SubElement(view, "filter", {"class": "categorical", "column": selected_reference})
        node(filter_element, "groupfilter", function="member", level=selected_instance, member="true")
        if spec["kind"] == "bar" and not spec.get("natural_order"):
            node(view, "computed-sort", column=dimension_reference, direction="DESC", using=metric_reference)
        slices = node(view, "slices")
        node(slices, "column", selected_reference)
    node(view, "aggregation", value="true")
    style = node(table, "style")
    style_rule(style, "worksheet", [("display-field-labels", "false")])
    style_rule(style, "table", [("font-family", "Arial"), ("font-size", "10"), ("color", PALETTE["navy"]), ("background-color", "#ffffff")])
    style_rule(style, "gridline", [("line-visibility", "off")])
    panes = node(table, "panes")
    pane = node(panes, "pane", selection_relaxation_option="selection-relaxation-allow")
    node(node(pane, "view"), "breakdown", value="auto")
    ET.SubElement(pane, "mark", {"class": {"kpi": "Automatic", "line": "Line", "bar": "Bar"}[spec["kind"]]})
    if spec["kind"] == "kpi":
        node(node(pane, "encodings"), "text", column=metric_reference)
        formatted = node(node(pane, "customized-label"), "formatted-text")
        node(formatted, "run", spec["title"].upper() + "\n", fontsize="10", fontcolor=PALETTE["navy"])
        node(formatted, "run", "<" + metric_reference + ">", bold="true", fontsize="26", fontcolor=PALETTE["teal"])
        node(formatted, "run", "\n" + spec.get("note", "Selected purchase window"), fontsize="9", fontcolor=PALETTE["copper"])
    elif tooltip_references:
        encodings = node(pane, "encodings")
        for _, reference in tooltip_references:
            node(encodings, "tooltip", column=reference)
        formatted = node(node(pane, "customized-tooltip"), "formatted-text")
        node(formatted, "run", "<" + dimension_reference + ">\n", bold="true")
        node(formatted, "run", spec["metric"] + ": <" + metric_reference + ">\n")
        for label, reference in tooltip_references:
            node(formatted, "run", label + ": <" + reference + ">\n")
    pane_style = node(pane, "style")
    style_rule(pane_style, "mark", [("mark-color", PALETTE["copper"] if spec["page"] == "Delivery" else PALETTE["teal"]),
                                      ("mark-labels-show", "true" if spec["kind"] == "kpi" else "false")])
    if spec["kind"] == "kpi":
        node(table, "rows")
        node(table, "cols")
    elif spec["kind"] == "line":
        node(table, "rows", metric_reference)
        node(table, "cols", dimension_reference)
    else:
        node(table, "rows", dimension_reference)
        node(table, "cols", metric_reference)
    identity(sheet, "worksheet/" + spec["name"])


def sheet_specs():
    definitions = {
        "Sales": [
            ("kpi", "Sales orders", "Sales Orders", None, "Eligible delivered orders"),
            ("kpi", "Product sales value", "Product Sales Value", None, "Source units; freight excluded"),
            ("kpi", "Average order value", "Average Order Value", None, "Product value / sales orders"),
            ("kpi", "Selected orders", "Selected Orders", None, "All statuses in this selection"),
            ("line", "Monthly product sales", "Product Sales Value", "purchase_month", ""),
            ("bar", "Product value by category", "Product Sales Value", "category", ""),
            ("bar", "Product value by buyer state", "Product Sales Value", "buyer_state", ""),
        ],
        "Delivery": [
            ("kpi", "Eligible deliveries", "Delivery Orders", None, "Valid delivered-order endpoints"),
            ("kpi", "Late orders", "Late Orders", None, "After the promised calendar day"),
            ("kpi", "Late delivery rate", "Late Delivery Rate", None, "Late / eligible delivery orders"),
            ("kpi", "Average delivery days", "Average Delivery Days", None, "Elapsed purchase-to-receipt days"),
            ("line", "Late delivery rate by purchase month", "Late Delivery Rate", "purchase_month", ""),
            ("bar", "Late delivery rate by buyer state", "Late Delivery Rate", "buyer_state", ""),
            ("bar", "Late delivery rate by category", "Late Delivery Rate", "category", ""),
        ],
        "Customers": [
            ("kpi", "Observed customers", "Customers", None, "Persistent IDs with eligible sales"),
            ("kpi", "Repeat customers", "Repeat Customers", None, "At least two selected sales orders"),
            ("kpi", "Observed repeat rate", "Repeat Customer Rate", None, "Repeat IDs / observed customer IDs"),
            ("kpi", "Average review score", "Average Review Score", None, "One selected valid review per order"),
            ("bar", "Selected review scores", "Sales Orders", "Review Bucket", ""),
            ("line", "Review score by purchase month", "Average Review Score", "purchase_month", ""),
            ("bar", "Customer purchase frequency", "Customers", "Purchase Frequency", ""),
        ],
    }
    result = []
    for page, rows in definitions.items():
        for kind, title, metric, dimension, note in rows:
            result.append({"page": page, "name": page + " | " + title, "kind": kind,
                           "title": title, "metric": metric, "dimension": dimension, "note": note,
                           "source": "categories" if dimension == "category" else "orders",
                           "sales_only": dimension in {"Review Bucket", "Purchase Frequency"},
                           "natural_order": dimension in {"Review Bucket", "Purchase Frequency"}})
    return result


def dashboard(parent, page, specs, parameters, first_zone):
    result = node(parent, "dashboard", name=page)
    style_rule(node(result, "style"), "table", [("background-color", PALETTE["background"])])
    node(result, "size", sizing_mode="fixed", minwidth="1400", maxwidth="1400", minheight="1000", maxheight="1000")
    node(node(result, "datasources"), "datasource", name="Parameters")
    dependencies = node(result, "datasource-dependencies", datasource="Parameters")
    for column in parameters:
        dependencies.append(deepcopy(column))
    zones = node(result, "zones")
    zone_id = first_zone

    def zone(x, y, w, h, kind, **attributes):
        nonlocal zone_id
        zone_id += 1
        # Tableau's normal dashboard coordinates span 0..100000 on each axis.
        element = node(zones, "zone", id=zone_id, x=round(x / 1400 * 100000), y=round(y / 1000 * 100000),
                       w=round(w / 1400 * 100000), h=round(h / 1000 * 100000), type_v2=kind, **attributes)
        return element

    title = zone(30, 20, 1340, 54, "text")
    node(node(title, "formatted-text"), "run", "OLIST  /  " + page.upper(), bold="true", fontsize="25", fontcolor=PALETTE["navy"])
    subtitle = zone(30, 73, 1340, 32, "text")
    subtitles = {"Sales": "Product value, order volume and where demand comes from",
                 "Delivery": "Observed delivery outcomes, grouped by purchase date",
                 "Customers": "Selected reviews and repeat purchases within the chosen window"}
    node(node(subtitle, "formatted-text"), "run", subtitles[page], fontsize="12", fontcolor=PALETTE["copper"])
    for position, name in enumerate(("StartMonth", "EndMonth", "BuyerState")):
        zone(30 + position * 450, 113, 425, 67, "paramctrl", param="[Parameters]." + bracket(name), mode="compact")
    for index, spec in enumerate(specs[:4]):
        zone(30 + index * 340, 192, 320, 120, "visual", name=spec["name"], show_title="false")
    charts = specs[4:]
    # Review distribution gets the wide first chart; it uses the same chart grid.
    zone(30, 332, 1340, 270, "visual", name=charts[0]["name"], show_title="true")
    zone(30, 620, 660, 290, "visual", name=charts[1]["name"], show_title="true")
    zone(710, 620, 660, 290, "visual", name=charts[2]["name"], show_title="true")
    footnotes = {
        "Sales": "Source monetary units; product value excludes freight and is not commission revenue or profit. Category orders can overlap. Scroll categorical charts to inspect every group.",
        "Delivery": "Rates describe association, not responsibility. Small groups can have unstable rates. Category counts overlap; the delivery date belongs to the order. On time includes the promised calendar day.",
        "Customers": "Observed repeats are not retention or lifetime value. Reviews may precede receipt. Frequency uses the selected window; later buyers have less follow-up. Missing reviews are excluded from score means.",
    }
    footer = zone(30, 927, 1340, 55, "text")
    formatted = node(footer, "formatted-text")
    node(formatted, "run", footnotes[page] + "\nPurchase window: Feb 2017–Jul 2018. Final recorded outcomes; no common follow-up horizon. Empty selections show zero counts and undefined averages.",
         fontsize="9", fontcolor=PALETTE["navy"])
    identity(result, "dashboard/" + page)
    return zone_id


def windows(parent, specs):
    for spec in specs:
        window = ET.SubElement(parent, "window", {"class": "worksheet", "name": spec["name"], "hidden": "true"})
        cards = node(window, "cards")
        left = node(cards, "edge", name="left")
        strip = node(left, "strip", size="160")
        for card in ("pages", "filters", "marks"):
            node(strip, "card", type=card)
        top = node(cards, "edge", name="top")
        for card in ("columns", "rows", "title"):
            node(node(top, "strip", size="31" if card == "title" else "2147483647"), "card", type=card)
        node(node(window, "viewpoint"), "zoom", type="fit-width" if spec["kind"] == "bar" else "entire-view")
        identity(window, "window/" + spec["name"])
    for page in ("Sales", "Delivery", "Customers"):
        window = ET.SubElement(parent, "window", {"class": "dashboard", "name": page, "maximized": "true"})
        viewpoints = node(window, "viewpoints")
        for spec in specs:
            if spec["page"] == page:
                viewpoint = node(viewpoints, "viewpoint", name=spec["name"])
                node(viewpoint, "zoom", type="fit-width" if spec["kind"] == "bar" else "entire-view")
        node(window, "active", id="-1")
        identity(window, "window/dashboard/" + page)


def build(output_dir, schema_path=None):
    output_dir = Path(output_dir)
    csv_paths = [output_dir / "data/orders.csv", output_dir / "data/categories.csv"]
    with csv_paths[0].open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(ORDER_TYPES):
            raise ValueError("orders.csv columns do not match the native workbook contract")
        rows = list(reader)
    with csv_paths[1].open(newline="", encoding="utf-8") as handle:
        if next(csv.reader(handle)) != list(CATEGORY_TYPES):
            raise ValueError("categories.csv columns do not match the native workbook contract")
    months = sorted({row["purchase_month"] for row in rows})
    states = sorted({row["buyer_state"] for row in rows})
    if len(months) != 18 or months[0] != "2017-02-01" or months[-1] != "2018-07-01":
        raise ValueError("Expected the agreed 18 purchase months")
    parameters = [parameter("StartMonth", "Start month", "date", months, months[0]),
                  parameter("EndMonth", "End month", "date", months, months[-1]),
                  parameter("BuyerState", "Buyer state", "string", ["All"] + states, "All")]
    workbook = ET.Element("workbook", {"original-version": VERSION, "version": VERSION,
        "source-build": "0.0.0 (0000.0.0.0)", "xmlns:user": USER_NS})
    node(node(workbook, "document-format-change-manifest"), "ManifestByVersion")
    node(workbook, "preferences")
    sources = node(workbook, "datasources")
    parameters_source = node(sources, "datasource", hasconnection="false", inline="true", name="Parameters", version=VERSION)
    node(parameters_source, "aliases", enabled="yes")
    for column in parameters:
        parameters_source.append(deepcopy(column))
    source_info = {"orders": datasource(sources, "orders", ORDER_TYPES),
                   "categories": datasource(sources, "categories", CATEGORY_TYPES)}
    specs = sheet_specs()
    sheets = node(workbook, "worksheets")
    for spec in specs:
        datasource_id, columns = source_info[spec["source"]]
        worksheet(sheets, spec, datasource_id, columns, parameters)
    dashboards = node(workbook, "dashboards")
    last_zone = 0
    for page in ("Sales", "Delivery", "Customers"):
        last_zone = dashboard(dashboards, page, [spec for spec in specs if spec["page"] == page], parameters, last_zone)
    windows(node(workbook, "windows"), specs)
    explanation = node(workbook, "explain-data", enabled_for_viewer="false", extreme_values_enabled_for_all="false")
    node(explanation, "explanation-types")
    ET.indent(workbook, space="  ")
    xml_bytes = ET.tostring(workbook, encoding="utf-8", xml_declaration=True) + b"\n"
    twb_path = output_dir / (WORKBOOK_NAME + ".twb")
    twbx_path = output_dir / (WORKBOOK_NAME + ".twbx")
    if schema_path:
        from lxml import etree
        from validate_tableau import load_schema
        schema = load_schema(schema_path)
        schema.assertValid(etree.fromstring(xml_bytes))
    twb_path.write_bytes(xml_bytes)
    # Fixed archive metadata keeps rerunning the build byte-for-byte repeatable.
    with zipfile.ZipFile(twbx_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in [twb_path] + csv_paths:
            info = zipfile.ZipInfo(path.relative_to(output_dir).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        license_info = zipfile.ZipInfo("DATA_LICENSE.txt", date_time=(2026, 1, 1, 0, 0, 0))
        license_info.compress_type = zipfile.ZIP_DEFLATED
        license_info.external_attr = 0o644 << 16
        archive.writestr(license_info, (PROJECT / "DATA_LICENSE.txt").read_bytes())
    return {"workbook": str(twb_path), "package": str(twbx_path), "version": VERSION,
            "worksheets": len(specs), "dashboards": 3, "parameters": 3,
            "schema_validated": bool(schema_path), "native_runtime_validated": False,
            "twb_sha256": hashlib.sha256(xml_bytes).hexdigest(),
            "twbx_sha256": hashlib.sha256(twbx_path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "tableau")
    parser.add_argument("--schema", type=Path, help="Optional official XSD; needs lxml and validate_tableau.py")
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir, args.schema), indent=2))


if __name__ == "__main__":
    main()
