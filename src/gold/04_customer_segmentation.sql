-- Databricks notebook source

-- COMMAND ----------

-- Purpose  : Gold Layer — Aggregation D: Customer Segmentation (FR-24)
--            Classifies every PASSED customer into one of four behaviour segments
--            and summarises the revenue profile of each segment.
-- Inputs   : workspace.ecommerce_medallion.silver_customers (PASSED rows only)
--            workspace.ecommerce_medallion.silver_orders    (PASSED rows — LEFT JOIN)
-- Outputs  : workspace.ecommerce_medallion.gold_customer_segmentation (Delta, overwrite)
-- Columns  : segment_type, customer_count, avg_revenue, total_revenue
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
--                Customers in silver_customers PASSED with no PASSED orders at all.
--
-- Phase    : Phase 4 — Gold Layer
-- Run      : Standalone in SQL editor, or %run from create_gold_tables.py

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.ecommerce_medallion.gold_customer_segmentation AS
WITH customer_revenue AS (
    -- One row per PASSED customer; 0-order customers retained via LEFT JOIN.
    SELECT
        c.customer_id,
        COALESCE(COUNT(DISTINCT o.order_id),  0)     AS total_orders,
        COALESCE(SUM(o.total_amount),         0)     AS total_revenue
    FROM workspace.ecommerce_medallion.silver_customers AS c
    LEFT JOIN workspace.ecommerce_medallion.silver_orders AS o
        ON  c.customer_id          = o.customer_id
        AND o.quality_check_result = 'PASSED'
    WHERE c.quality_check_result = 'PASSED'
    GROUP BY c.customer_id
),
customer_segments AS (
    SELECT
        customer_id,
        total_orders,
        total_revenue,
        CASE
            WHEN total_revenue  >  5000                       THEN 'High-Value'
            WHEN total_orders   >= 2 AND total_revenue <= 5000 THEN 'Repeat'
            WHEN total_orders   =  1                          THEN 'One-Time'
            ELSE                                                   'Inactive'
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

-- Smoke check: customer_count across all segments must equal the number of
-- PASSED customers in silver_customers.
SELECT
    SUM(customer_count)             AS total_customers_classified,
    ROUND(SUM(total_revenue), 2)    AS total_revenue_all_segments
FROM workspace.ecommerce_medallion.gold_customer_segmentation;
