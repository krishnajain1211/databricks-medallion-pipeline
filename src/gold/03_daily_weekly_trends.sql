-- Databricks notebook source

-- COMMAND ----------

-- Purpose  : Gold Layer — Aggregation C: Daily and Weekly Revenue Trends (FR-23)
--            Produces one table with both daily and weekly aggregations, unified
--            via a period_type column.  Sourced from PASSED orders only.
-- Inputs   : workspace.ecommerce_medallion.silver_orders (PASSED rows only)
-- Outputs  : workspace.ecommerce_medallion.gold_daily_weekly_trends (Delta, overwrite)
-- Columns  : period_type ('daily' | 'weekly'), period_start (DATE),
--            total_orders, total_revenue, avg_order_value
-- Structure: UNION ALL of a daily GROUP BY and a weekly DATE_TRUNC GROUP BY.
--            Using period_type as a discriminator lets dashboard queries filter
--            to one granularity without needing two separate tables.
-- Phase    : Phase 4 — Gold Layer
-- Run      : Standalone in SQL editor, or %run from create_gold_tables.py

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.ecommerce_medallion.gold_daily_weekly_trends AS

-- Daily aggregation
SELECT
    'daily'                         AS period_type,
    order_date                      AS period_start,
    COUNT(DISTINCT order_id)        AS total_orders,
    ROUND(SUM(total_amount),  2)    AS total_revenue,
    ROUND(AVG(total_amount),  2)    AS avg_order_value
FROM workspace.ecommerce_medallion.silver_orders
WHERE quality_check_result = 'PASSED'
GROUP BY order_date

UNION ALL

-- Weekly aggregation (week starts on Monday per ISO standard)
SELECT
    'weekly'                                        AS period_type,
    CAST(DATE_TRUNC('WEEK', order_date) AS DATE)   AS period_start,
    COUNT(DISTINCT order_id)                        AS total_orders,
    ROUND(SUM(total_amount),  2)                   AS total_revenue,
    ROUND(AVG(total_amount),  2)                   AS avg_order_value
FROM workspace.ecommerce_medallion.silver_orders
WHERE quality_check_result = 'PASSED'
GROUP BY DATE_TRUNC('WEEK', order_date)

ORDER BY period_type, period_start;

-- COMMAND ----------

-- Smoke check: daily rows should equal distinct order_dates in PASSED orders;
-- weekly rows should equal distinct ISO weeks.
SELECT
    period_type,
    COUNT(*)                       AS period_count,
    ROUND(SUM(total_revenue), 2)   AS total_revenue_check,
    MIN(period_start)              AS earliest_period,
    MAX(period_start)              AS latest_period
FROM workspace.ecommerce_medallion.gold_daily_weekly_trends
GROUP BY period_type
ORDER BY period_type;
