-- Databricks notebook source

-- COMMAND ----------

-- Purpose  : Gold Layer — Aggregation D: Customer Segmentation (FR-24)
--            Classifies every unique customer_id into one of four behaviour segments
--            and summarises the revenue profile of each segment.
-- Inputs   : workspace.ecommerce_medallion.silver_customers (ALL rows, deduped on customer_id)
--            workspace.ecommerce_medallion.silver_orders    (PASSED rows — LEFT JOIN)
-- Outputs  : workspace.ecommerce_medallion.gold_customer_segmentation (Delta, overwrite)
-- Columns  : segment_type, customer_count, avg_revenue, total_revenue
--
-- Bug fix  : (2026-08-09) Same root cause as 02_revenue_by_customer.sql — original
--            WHERE c.quality_check_result = 'PASSED' filter excluded customers with
--            record-level defects.  Fixed with the same ROW_NUMBER() deduplication CTE.
--            Documented as Gap G-08 in requirements-analysis.md.
--
-- Segmentation rules (mutually exclusive, applied in priority order):
--   High-Value : total_revenue > 5000
--                Customers whose earned revenue exceeds the approximate dataset
--                average (~$5,500/customer).  Threshold is a documented design
--                choice — adjust after reviewing the gold_revenue_by_customer
--                distribution to fit business criteria.
--   Repeat     : total_orders >= 2 AND total_revenue <= 5000
--                Frequent buyers who have not yet hit the High-Value threshold.
--   One-Time   : total_orders = 1
--                Customers with exactly one PASSED order.
--   Inactive   : total_orders = 0
--                Customers with no PASSED orders at all (either 0 orders or all failed).
--
-- Phase    : Phase 4 — Gold Layer
-- Run      : Standalone in SQL editor, or %run from create_gold_tables.py

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.ecommerce_medallion.gold_customer_segmentation AS
WITH customers_deduped AS (
    -- One canonical row per customer_id regardless of the customer record's quality.
    -- Mirrors the fix in 02_revenue_by_customer.sql — both tables must use the same
    -- customer population so segment counts are consistent with revenue_by_customer.
    SELECT
        customer_id,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY customer_id) AS _rn
    FROM workspace.ecommerce_medallion.silver_customers
    WHERE customer_id IS NOT NULL
),
customer_revenue AS (
    -- One row per unique customer; 0-order customers retained via LEFT JOIN.
    SELECT
        c.customer_id,
        COALESCE(COUNT(DISTINCT o.order_id),  0)     AS total_orders,
        COALESCE(SUM(o.total_amount),         0)     AS total_revenue
    FROM customers_deduped AS c
    LEFT JOIN workspace.ecommerce_medallion.silver_orders AS o
        ON  c.customer_id          = o.customer_id
        AND o.quality_check_result = 'PASSED'
    WHERE c._rn = 1
    GROUP BY c.customer_id
),
customer_segments AS (
    SELECT
        customer_id,
        total_orders,
        total_revenue,
        CASE
            WHEN total_revenue  >  5000                        THEN 'High-Value'
            WHEN total_orders   >= 2 AND total_revenue <= 5000 THEN 'Repeat'
            WHEN total_orders   =  1                           THEN 'One-Time'
            ELSE                                                    'Inactive'
        END AS segment_type
    FROM customer_revenue
)
SELECT
    segment_type,
    COUNT(*)                          AS customer_count,
    ROUND(AVG(total_revenue), 2)      AS avg_revenue,
    ROUND(SUM(total_revenue), 2)      AS total_revenue
FROM customer_segments
GROUP BY segment_type
ORDER BY
    CASE segment_type
        WHEN 'High-Value' THEN 1
        WHEN 'Repeat'     THEN 2
        WHEN 'One-Time'   THEN 3
        WHEN 'Inactive'   THEN 4
    END;

-- COMMAND ----------

-- Smoke check: sum of customer_count across all segments must equal
-- COUNT(DISTINCT customer_id) from silver_customers (excluding NULL customer_ids).
SELECT
    SUM(customer_count)             AS total_customers_classified,
    ROUND(SUM(total_revenue), 2)    AS total_revenue_all_segments
FROM workspace.ecommerce_medallion.gold_customer_segmentation;
