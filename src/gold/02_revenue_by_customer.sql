-- Databricks notebook source

-- COMMAND ----------

-- Purpose  : Gold Layer — Aggregation B: Revenue by Customer (FR-22)
--            One row per unique customer_id, with actual revenue metrics computed
--            from their PASSED orders.  Customers with no PASSED orders are
--            included (total_orders = 0, total_revenue = 0) so the downstream
--            segmentation table can classify them as Inactive.
-- Inputs   : workspace.ecommerce_medallion.silver_customers (ALL rows, deduped on customer_id)
--            workspace.ecommerce_medallion.silver_orders    (PASSED rows — LEFT JOIN)
-- Outputs  : workspace.ecommerce_medallion.gold_revenue_by_customer (Delta, overwrite)
-- Columns  : customer_id, customer_name, customer_segment,
--            total_orders, total_revenue, avg_order_value, lifetime_value_actual
-- Note     : lifetime_value_actual = the stored lifetime_value field from
--            silver_customers (the declared/estimated value in the customer record).
--            total_revenue = the computed SUM(total_amount) from PASSED orders.
--            Keeping both lets analysts compare declared vs. earned revenue.
--
-- Bug fix  : (2026-08-09) Original query used WHERE c.quality_check_result = 'PASSED',
--            which excluded ~120 customers whose records had defects (malformed email,
--            duplicate ID, etc.) even when those customers' orders passed all order-level
--            checks.  The FR-26 revenue cross-check exposed a $635,295.88 shortfall vs.
--            gold_sales_by_product.
--            Fix: use ROW_NUMBER() to pick one canonical record per customer_id from
--            silver_customers (handling the 20 seeded duplicate-ID rows, C-02), then
--            join ALL unique customers to PASSED orders.  A bad email does not invalidate
--            a real transaction that already passed order-level quality checks.
--            Documented as Gap G-08 in requirements-analysis.md.
--
-- JOIN note: quality_check_result = 'PASSED' filter on orders is in the ON clause
--            (not WHERE) to preserve 0-order customers in the LEFT JOIN result.
-- Phase    : Phase 4 — Gold Layer
-- Run      : Standalone in SQL editor, or %run from create_gold_tables.py

-- COMMAND ----------

CREATE OR REPLACE TABLE workspace.ecommerce_medallion.gold_revenue_by_customer AS
WITH customers_deduped AS (
    -- One canonical row per customer_id regardless of the customer record's quality.
    -- ROW_NUMBER() collapses the 20 seeded duplicate-ID rows (C-02) to a single row.
    -- All customers are included — a bad email (C-03/C-04) does not invalidate orders.
    SELECT
        customer_id,
        customer_name,
        customer_segment,
        lifetime_value,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY customer_id) AS _rn
    FROM workspace.ecommerce_medallion.silver_customers
    WHERE customer_id IS NOT NULL
)
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_segment,
    COALESCE(COUNT(DISTINCT o.order_id),    0)       AS total_orders,
    ROUND(COALESCE(SUM(o.total_amount),     0), 2)   AS total_revenue,
    ROUND(COALESCE(AVG(o.total_amount),     0), 2)   AS avg_order_value,
    c.lifetime_value                                  AS lifetime_value_actual
FROM customers_deduped AS c
LEFT JOIN workspace.ecommerce_medallion.silver_orders AS o
    ON  c.customer_id          = o.customer_id
    AND o.quality_check_result = 'PASSED'      -- in ON clause to keep 0-order customers
WHERE c._rn = 1
GROUP BY
    c.customer_id,
    c.customer_name,
    c.customer_segment,
    c.lifetime_value
ORDER BY total_revenue DESC;

-- COMMAND ----------

-- Smoke check: every unique customer should appear exactly once.
-- customer_rows should equal COUNT(DISTINCT customer_id) from silver_customers
-- (excluding NULL customer_id rows, if any).
SELECT
    COUNT(*)                         AS customer_rows,
    COUNT(DISTINCT customer_id)      AS unique_customers,
    ROUND(SUM(total_revenue),   2)   AS grand_total_revenue,
    ROUND(AVG(total_revenue),   2)   AS avg_revenue_per_customer,
    SUM(CASE WHEN total_orders = 0 THEN 1 ELSE 0 END) AS inactive_customers
FROM workspace.ecommerce_medallion.gold_revenue_by_customer;
