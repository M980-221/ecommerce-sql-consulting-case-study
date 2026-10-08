# Part 5 — Delivery performance

This stage measures delivery duration and lateness, then looks at purchase months, buyer states, product categories and sellers. It uses purchases from **1 February 2017 to 31 July 2018**, with the delivery rules agreed in Part 3.

## Run the analysis

```bash
python3 scripts/analyse_delivery.py
```

Run this from the repository folder after [database setup](09_part2_setup.md) and [Part 3 preparation](10_part3_cleaning.md). The script opens the database read-only, runs [the delivery SQL](../sql/04_delivery_analysis.sql), checks the results and exports five CSV files. A blank result cell means SQL `NULL`, not zero.

## Questions and outputs

| Query | Question | Output and row meaning |
|---|---|---|
| Q6 | How often were deliveries late, and how long did they take? | [Overall delivery](../results/part5_overall_delivery.csv): one row, including exclusions and seller coverage |
| Q7 | How did outcomes vary by purchase month? | [Monthly delivery](../results/part5_monthly_delivery.csv): all 18 months |
| Q8 | Which buyer states accounted for the most late orders? | [Regional delivery](../results/part5_regional_delivery.csv): 27 buyer states |
| Q9 | Which categories appeared in late orders? | [Category delivery](../results/part5_category_delivery.csv): 74 category labels, including missing and untranslated labels |
| Q10 | Which sellers' orders account for the most late deliveries? | [Seller delivery](../results/part5_seller_delivery.csv): 190 sellers with at least 100 eligible single-seller orders each |

## Results

| Measure | Result |
|---|---:|
| All purchases in the reporting period | 91,780 |
| Eligible delivered orders | 89,102 |
| Excluded orders | 2,678: 2,670 non-delivered and eight with no actual-delivery date |
| Late orders | 6,116 (6.86%) |
| On-time orders | 82,986 (93.14%) |
| Average time from purchase to receipt | 12.88 elapsed days |
| Average delay among late orders only | 10.98 calendar days beyond the promised date |

- **March 2018 had the highest late-delivery rate:** 1,328 of 7,003 eligible orders (**18.96%**). February 2018 was also elevated at 926 of 6,555 (**14.13%**). These are purchase-month groups using the final outcomes in the snapshot, not orders delivered during those months.
- **São Paulo had the most late orders, but Rio de Janeiro had a higher rate.** SP had 1,524 late deliveries among 36,952 eligible orders (**4.12%**); RJ had 1,450 among 11,496 (**12.61%**). Both count and rate matter when deciding what to investigate.
- **Bed, bath and table products appeared in the most late orders:** 659 of 8,669 eligible orders containing that category (**7.60%**). This associates a category with an order's delivery outcome; it does not identify which item caused a delay.
- **Seller `4a3ca9315b744ce9f8e9374361493884` had the most late orders in the seller report:** 163 among 1,604 eligible single-seller orders (**10.16%**). This is a starting point for checking routes, carriers and product mix, not evidence that the seller caused those delays.

## Definitions and coverage

- **Eligibility:** a delivered order must have valid purchase, receipt and promised dates, with receipt at or after purchase and the promised calendar day at or after the purchase day. The reporting interval is `[2017-02-01, 2018-08-01)`. The eight missing actual dates explain the difference from Part 4's 89,110 sales orders.
- **Late versus slow:** receipt on the promised calendar day counts as on time. Delivery duration uses the full purchase and receipt timestamps, so it includes fractions of a day. Positive delay uses calendar dates and averages only the late orders. A long delivery can still be on time if the promise allowed it.
- **Seller coverage:** 87,946 of the 89,102 eligible orders had one seller (**98.70%**); 1,156 involved multiple sellers and are excluded from seller attribution. None lacked a seller. The 100-order cutoff retains 190 sellers and 52,408 orders (**58.82%** of all eligible delivery orders); another 35,538 single-seller orders fall below it. The report covers 3,689 of the 6,116 late orders (**60.32%**).
- **Seller threshold and sorting:** 100 orders is an exploratory reporting cutoff, not a significance test. State, category and seller reports sort by late-order count first, then rate, to show where more observed late deliveries occurred. Rates and denominators remain visible; the seller report does not represent every seller or route.
- **Categories:** the joins first produce item rows, then `DISTINCT` keeps one row per order and category. Repeated items from one category must not increase its order count. An order with two categories still belongs to both groups. The 89,822 category memberships therefore cannot be summed as unique orders; they cover 89,102 orders. Missing categories are retained.

## SQL used

`WHERE` selects eligible orders; `GROUP BY`, `COUNT`, `SUM` and `AVG` calculate group results; `HAVING` applies the seller sample cutoff. `LEFT JOIN` adds item, category and seller details. `WITH` names intermediate steps, `DISTINCT` removes repeated order-category pairs, and a recursive calendar keeps every reporting month. `CASE` chooses which values enter an average. `NULLIF`, `COALESCE` and `ROUND` handle empty denominators, missing labels and display rounding.

## Two queries to practise

Run these against the prepared SQLite database. For SQLime, load the database containing the Part 3 views first.

```sql
SELECT single_seller_id AS seller_id,
       COUNT(*) AS delivery_orders,
       SUM(is_late) AS late_orders,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS late_pct,
       AVG(CASE WHEN is_late = 1 THEN delay_days END)
           AS average_positive_delay_days
FROM v_order_analysis
WHERE seller_delivery_eligible = 1
GROUP BY single_seller_id
HAVING COUNT(*) >= 100
ORDER BY late_orders DESC, late_pct DESC, seller_id;
```

- `WHERE` chooses individual eligible, single-seller orders **before** grouping. Their dates and purchase period have already been checked in the view.
- `GROUP BY` collects each seller's orders. `COUNT(*)` counts them; `SUM(is_late)` adds the 1/0 flag, so it counts late orders.
- `HAVING` filters the completed groups: keep a seller only if its count is at least 100. It is different from filtering an individual row with `WHERE`.
- `CASE` supplies `delay_days` only for late orders. Without an `ELSE`, other rows produce `NULL`, which `AVG` ignores. Adding `ELSE 0` would include on-time orders in the denominator and answer a different question.
- `AS` gives result columns readable aliases. `ORDER BY` puts the largest late counts first. This returns 190 sellers; the first has 1,604 orders, 163 late orders and an average positive delay of about 11.64 days.

This practice query leaves the `AVG` result unrounded. The published SQL rounds positive delay from the integer day total and late-order count, so halfway values such as 9.825 consistently display as 9.83 despite floating-point approximation.

Try changing `100` to `200`. Predict which sellers disappear. The measures for sellers that remain should stay the same because `HAVING` removes whole groups.

```sql
WITH order_categories AS (
    SELECT DISTINCT o.order_id,
           COALESCE(p.category_label, 'Unknown category') AS category,
           o.is_late
    FROM v_order_analysis o
    LEFT JOIN v_clean_order_items i ON i.order_id = o.order_id
    LEFT JOIN v_products_labeled p ON p.product_id = i.product_id
    WHERE o.delivery_eligible = 1
)
SELECT category, COUNT(*) AS delivery_orders,
       SUM(is_late) AS late_orders,
       ROUND(100.0 * SUM(is_late) / COUNT(*), 2) AS late_pct
FROM order_categories
GROUP BY category
ORDER BY late_orders DESC, late_pct DESC, category
LIMIT 5;
```

- `o`, `i` and `p` are short aliases for the views. The first join matches an order to its items with `order_id`; the second finds each item's category with `product_id`.
- `LEFT JOIN` keeps the order even if details are missing. `COALESCE` supplies the missing-category label.
- One order with three items in the same category initially creates three matching rows. `DISTINCT` reduces those to one order-category row before counting and summing the late flag.
- `WITH` names that intermediate result `order_categories`. The outer `GROUP BY` counts its rows by category. The first row is `bed_bath_table`: 8,669 orders, 659 late and 7.60% late.
- An order with a book and a toy contributes once to each category. Neither `DISTINCT` nor `GROUP BY` makes the categories mutually exclusive.

## Checks and limits

All **25 delivery checks** passed across **310 output rows and 2,409 cells**. The test run passed **36 tests: 12 delivery tests and 24 earlier cleaning and sales tests**.

The [validation output](../results/part5_validation.json) compares every exported result with an independent calculation from the raw records, including date rules, category deduplication and seller coverage. See the [text report](../results/part5_validation.txt) and [test results](../results/part5_tests.txt) for the recorded checks.

These are historical associations. Buyer and seller states differ, delivery routes and product mixes are not held constant, and the source has no common follow-up cutoff. The monthly figures use final snapshot outcomes, not what was known at each month-end. Carrier-event chronology issues remain flagged in Part 3 and are not used in these endpoint measures. Passing checks does not establish who caused a delay or whether changing an operation would improve it.

**Next: Part 6 — customer experience.** Compare review scores and observed repeat purchases, then examine whether late orders are associated with different review outcomes.
