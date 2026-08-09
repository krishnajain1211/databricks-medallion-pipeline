-- Databricks notebook source

-- COMMAND ----------

-- Purpose  : Gold Layer — Aggregation A: Sales by Product (FR-21)
--            Summarises order volume and revenue per product, sourced exclusively
--            from Silver rows with quality_check_result = 'PASSED'.
-- Inputs   : workspace.ecommerce_medallion.silver_orders   (PASSED rows only)
--            workspace.ecommerce_medallion.bronze_products  (product_name, category)
-- Outputs  : workspace.ecommerce_medallion.gold_sales_by_product (Delta, overwrite)
-- Columns  : product_id, product_name, category,
--            total_orders, total_revenue, avg_order_value
-- Join note: INNER JOIN to bronze_products is safe — all PASSED orders have a
--            valid product_id (orphan + NULL product_ids are flagged FAILED in Silver).
-- Phase    : Phase 4 — Gold Layer
-- Run      : Standalone in SQL editor, or %run from create_gold_tables.py

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.ecommerce_medallion.gold_sales_by_product AS
SELECT
    o.product_id,
    p.product_name,
    p.category,
    COUNT(DISTINCT o.order_id)      AS total_orders,
    ROUND(SUM(o.total_amount), 2)   AS total_revenue,
    ROUND(AVG(o.total_amount), 2)   AS avg_order_value
FROM workspace.ecommerce_medallion.silver_orders    AS o
INNER JOIN workspace.ecommerce_medallion.bronze_products AS p
    ON o.product_id = p.product_id
WHERE o.quality_check_result = 'PASSED'
GROUP BY
    o.product_id,
    p.product_name,
    p.category
ORDER BY total_revenue DESC;

-- COMMAND ----------

-- Smoke check: row count should equal number of distinct products that appear
-- in at least one PASSED order (≤ 500, since products.csv has 500 rows).
SELECT
    COUNT(*)                        AS product_rows,
    ROUND(SUM(total_revenue), 2)    AS grand_total_revenue,
    ROUND(AVG(avg_order_value), 2)  AS overall_avg_order_value
FROM workspace.ecommerce_medallion.gold_sales_by_product;
