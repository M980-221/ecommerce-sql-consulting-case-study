-- Part 6: customer experience and observed repeat purchases
-- Run after sql/02_cleaning.sql. Purchases: 1 Feb 2017 to 31 Jul 2018.
-- Use one row per sales-eligible order and the valid review selected in Part 3.
-- Missing reviews stay missing. Customer identity uses customer_unique_id.
-- Means and rates use integer half-up rounding to two decimal places.

-- result: review_distribution
-- Q11. How are selected review scores distributed, and how much is unreviewed?
-- Show every score, including zero counts. The last row has no review score.
WITH buckets(bucket_order, review_score, review_bucket) AS (
    VALUES (1, 1, '1'), (2, 2, '2'), (3, 3, '3'), (4, 4, '4'), (5, 5, '5'),
           (6, NULL, 'No eligible selected review')
), sales AS (
    SELECT review_score, review_eligible
    FROM v_order_analysis
    WHERE sales_eligible = 1
), counts AS (
    SELECT review_score, COUNT(*) AS sales_orders
    FROM sales
    GROUP BY review_score
), coverage AS (
    SELECT COUNT(*) AS total_sales_orders,
           COALESCE(SUM(review_eligible), 0) AS total_reviewed_orders
    FROM sales
)
SELECT b.review_bucket, b.review_score, COALESCE(c.sales_orders, 0) AS sales_orders,
       ((20000 * COALESCE(c.sales_orders, 0) + t.total_sales_orders)
         / (2 * NULLIF(t.total_sales_orders, 0))) / 100.0 AS share_of_sales_pct,
       CASE WHEN b.review_score IS NOT NULL THEN
           ((20000 * COALESCE(c.sales_orders, 0) + t.total_reviewed_orders)
             / (2 * NULLIF(t.total_reviewed_orders, 0))) / 100.0
       END AS share_of_reviewed_pct,
       t.total_sales_orders, t.total_reviewed_orders,
       t.total_sales_orders - t.total_reviewed_orders AS total_missing_review_orders,
       ((20000 * t.total_reviewed_orders + t.total_sales_orders)
         / (2 * NULLIF(t.total_sales_orders, 0))) / 100.0 AS review_coverage_pct
FROM buckets b
LEFT JOIN counts c ON c.review_score IS b.review_score
CROSS JOIN coverage t
ORDER BY b.bucket_order;

-- result: delivery_reviews
-- Q12. How do selected reviews differ between on-time and late deliveries?
-- Both sales and delivery eligibility are required. Review means use reviewed
-- orders only. Responses before receipt remain included and are counted below.
-- These groups show association; they do not measure the effect of a delay.
WITH delivery_groups(is_late, delivery_group) AS (
    VALUES (0, 'on_time'), (1, 'late')
), totals AS (
    SELECT is_late, COUNT(*) AS sales_orders,
           SUM(review_eligible) AS reviewed_orders,
           SUM(CASE WHEN review_eligible = 1 THEN review_score ELSE 0 END) AS review_score_sum,
           SUM(CASE WHEN review_score IN (1, 2) THEN 1 ELSE 0 END) AS low_score_orders,
           SUM(CASE WHEN review_eligible = 1
                          AND review_answer_timestamp < order_delivered_customer_date
                    THEN 1 ELSE 0 END) AS pre_delivery_review_orders
    FROM v_order_analysis
    WHERE sales_eligible = 1 AND delivery_eligible = 1
    GROUP BY is_late
)
SELECT g.delivery_group, COALESCE(t.sales_orders, 0) AS sales_orders,
       COALESCE(t.reviewed_orders, 0) AS reviewed_orders,
       COALESCE(t.sales_orders - t.reviewed_orders, 0) AS missing_review_orders,
       ((20000 * t.reviewed_orders + t.sales_orders)
         / (2 * NULLIF(t.sales_orders, 0))) / 100.0 AS review_coverage_pct,
       COALESCE(t.review_score_sum, 0) AS review_score_sum,
       ((200 * t.review_score_sum + t.reviewed_orders)
         / (2 * NULLIF(t.reviewed_orders, 0))) / 100.0 AS average_review_score,
       COALESCE(t.low_score_orders, 0) AS low_score_orders,
       ((20000 * t.low_score_orders + t.reviewed_orders)
         / (2 * NULLIF(t.reviewed_orders, 0))) / 100.0 AS low_score_pct,
       COALESCE(t.pre_delivery_review_orders, 0) AS pre_delivery_review_orders
FROM delivery_groups g
LEFT JOIN totals t ON t.is_late = g.is_late
ORDER BY g.is_late;

-- result: customer_spending
-- Q13. Which 20 observed customers have the highest product sales value?
-- Combine all eligible orders for each persistent ID before applying LIMIT.
-- This is spending observed within the reporting window, not lifetime value.
WITH totals AS (
    SELECT customer_unique_id, COUNT(*) AS sales_orders,
           SUM(product_sales_cents) AS product_sales_cents,
           MIN(order_purchase_timestamp) AS first_purchase_timestamp,
           MAX(order_purchase_timestamp) AS last_purchase_timestamp,
           SUM(review_eligible) AS reviewed_orders,
           SUM(CASE WHEN review_eligible = 1 THEN review_score ELSE 0 END) AS review_score_sum
    FROM v_order_analysis
    WHERE sales_eligible = 1
    GROUP BY customer_unique_id
)
SELECT customer_unique_id, sales_orders, product_sales_cents,
       product_sales_cents / 100.0 AS product_sales_value,
       ((2 * product_sales_cents + sales_orders)
         / (2 * NULLIF(sales_orders, 0))) / 100.0 AS average_order_value,
       first_purchase_timestamp, last_purchase_timestamp, reviewed_orders,
       ((20000 * reviewed_orders + sales_orders)
         / (2 * NULLIF(sales_orders, 0))) / 100.0 AS review_coverage_pct,
       ((200 * review_score_sum + reviewed_orders)
         / (2 * NULLIF(reviewed_orders, 0))) / 100.0 AS average_review_score
FROM totals
ORDER BY product_sales_cents DESC, customer_unique_id ASC
LIMIT 20;

-- result: repeat_customers
-- Q14. How many customers have at least two eligible orders in this window?
-- HAVING filters customer groups after counting their orders. Different
-- order IDs count separately even when their purchase timestamps are equal.
-- Later purchasers have less time to return; this is not a retention rate.
WITH customer_totals AS (
    SELECT customer_unique_id, COUNT(*) AS sales_orders,
           SUM(product_sales_cents) AS product_sales_cents
    FROM v_order_analysis
    WHERE sales_eligible = 1
    GROUP BY customer_unique_id
), repeat_buyers AS (
    SELECT customer_unique_id, COUNT(*) AS sales_orders,
           SUM(product_sales_cents) AS product_sales_cents
    FROM v_order_analysis
    WHERE sales_eligible = 1
    GROUP BY customer_unique_id
    HAVING COUNT(*) >= 2
), all_totals AS (
    SELECT COUNT(*) AS total_customers,
           COALESCE(SUM(sales_orders), 0) AS total_sales_orders,
           COALESCE(SUM(product_sales_cents), 0) AS total_product_sales_cents
    FROM customer_totals
), repeat_totals AS (
    SELECT COUNT(*) AS repeat_customers,
           COALESCE(SUM(sales_orders), 0) AS repeat_customer_orders,
           COALESCE(SUM(product_sales_cents), 0) AS repeat_product_sales_cents
    FROM repeat_buyers
)
SELECT '2017-02-01' AS period_start, '2018-08-01' AS period_end_exclusive,
       a.total_customers, a.total_customers - r.repeat_customers AS one_time_customers,
       r.repeat_customers,
       ((20000 * r.repeat_customers + a.total_customers)
         / (2 * NULLIF(a.total_customers, 0))) / 100.0 AS repeat_customer_pct,
       a.total_sales_orders,
       a.total_sales_orders - r.repeat_customer_orders AS one_time_customer_orders,
       r.repeat_customer_orders,
       a.total_product_sales_cents,
       a.total_product_sales_cents - r.repeat_product_sales_cents AS one_time_product_sales_cents,
       r.repeat_product_sales_cents,
       a.total_product_sales_cents / 100.0 AS total_product_sales_value,
       (a.total_product_sales_cents - r.repeat_product_sales_cents) / 100.0
           AS one_time_product_sales_value,
       r.repeat_product_sales_cents / 100.0 AS repeat_product_sales_value,
       ((20000 * r.repeat_customer_orders + a.total_sales_orders)
         / (2 * NULLIF(a.total_sales_orders, 0))) / 100.0 AS repeat_order_share_pct,
       ((20000 * r.repeat_product_sales_cents + a.total_product_sales_cents)
         / (2 * NULLIF(a.total_product_sales_cents, 0))) / 100.0 AS repeat_sales_share_pct
FROM all_totals a
CROSS JOIN repeat_totals r;

-- result: regional_reviews
-- Q15. Which buyer states account for the most low-scoring selected reviews?
-- Keep every state, including unknown. Coverage uses sales orders; score means
-- and low-score rates use reviewed orders. Counts and rates belong together.
WITH totals AS (
    SELECT COALESCE(NULLIF(TRIM(customer_state), ''), 'Unknown state') AS customer_state,
           COUNT(*) AS sales_orders, SUM(review_eligible) AS reviewed_orders,
           SUM(CASE WHEN review_eligible = 1 THEN review_score ELSE 0 END) AS review_score_sum,
           SUM(CASE WHEN review_score IN (1, 2) THEN 1 ELSE 0 END) AS low_score_orders
    FROM v_order_analysis
    WHERE sales_eligible = 1
    GROUP BY COALESCE(NULLIF(TRIM(customer_state), ''), 'Unknown state')
)
SELECT customer_state, sales_orders, reviewed_orders,
       sales_orders - reviewed_orders AS missing_review_orders,
       ((20000 * reviewed_orders + sales_orders)
         / (2 * NULLIF(sales_orders, 0))) / 100.0 AS review_coverage_pct,
       review_score_sum,
       ((200 * review_score_sum + reviewed_orders)
         / (2 * NULLIF(reviewed_orders, 0))) / 100.0 AS average_review_score,
       low_score_orders,
       ((20000 * low_score_orders + reviewed_orders)
         / (2 * NULLIF(reviewed_orders, 0))) / 100.0 AS low_score_pct
FROM totals
ORDER BY low_score_orders DESC,
         1.0 * low_score_orders / NULLIF(reviewed_orders, 0) DESC,
         customer_state ASC;
