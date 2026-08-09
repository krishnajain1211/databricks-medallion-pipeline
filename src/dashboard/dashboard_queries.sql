-- Purpose  : SQL queries for the five tiles of the Databricks SQL Dashboard.
--            Each query block is labelled with its tile number, visualization type,
--            and the exact Databricks chart configuration settings to use.
--            Copy each query verbatim into a Dashboard Dataset tab — see
--            src/dashboard/DASHBOARD_GUIDE.md for step-by-step setup.
-- Inputs   : workspace.ecommerce_medallion.gold_sales_by_product
--            workspace.ecommerce_medallion.gold_revenue_by_customer
--            workspace.ecommerce_medallion.gold_customer_segmentation
--            workspace.ecommerce_medallion.gold_daily_weekly_trends
--            workspace.ecommerce_medallion.silver_quality_metrics
-- Phase    : Phase 5 — Dashboard
-- Coverage : FR-28 (Tile 1), FR-29 (Tile 2), FR-30 (Tile 3),
--            P-04 bonus (Tile 4), bonus trend tile (Tile 5)

-- ─────────────────────────────────────────────────────────────────────────────
-- TILE 1 — Top 10 Products by Revenue (FR-28)
-- Chart type : Bar chart
-- X-axis     : product_name
-- Y-axis     : total_revenue
-- Group by   : category  (use colour series to distinguish categories)
-- Sort       : total_revenue DESC (already applied in ORDER BY)
-- Tooltip    : include total_orders and avg_order_value
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    product_name,
    category,
    total_orders,
    total_revenue,
    avg_order_value
FROM workspace.ecommerce_medallion.gold_sales_by_product
ORDER BY total_revenue DESC
LIMIT 10;

-- ─────────────────────────────────────────────────────────────────────────────
-- TILE 2 — Customer Revenue Distribution (FR-29)
-- Chart type : Histogram
-- X-axis     : total_revenue  (Databricks bins automatically — set bin size ~500)
-- Y-axis     : count (auto-computed by the histogram visualization)
-- Filter note: WHERE total_revenue > 0 excludes Inactive customers (0-order)
--              so the distribution is not skewed by a spike at zero.
--              Remove this filter if you want to show Inactive in the distribution.
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    customer_id,
    customer_segment,
    total_revenue,
    total_orders
FROM workspace.ecommerce_medallion.gold_revenue_by_customer
WHERE total_revenue > 0
ORDER BY total_revenue;

-- ─────────────────────────────────────────────────────────────────────────────
-- TILE 3 — Customer Segmentation Breakdown (FR-30)
-- Chart type : Pie chart
-- Label      : segment_type
-- Value      : customer_count
-- Tooltip    : include avg_revenue, total_revenue, pct_of_customers, pct_of_revenue
-- Sort order : High-Value → Repeat → One-Time → Inactive (ORDER BY applied)
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    segment_type,
    customer_count,
    avg_revenue,
    total_revenue,
    ROUND(100.0 * customer_count / SUM(customer_count) OVER (), 1) AS pct_of_customers,
    ROUND(100.0 * total_revenue  / SUM(total_revenue)  OVER (), 1) AS pct_of_revenue
FROM workspace.ecommerce_medallion.gold_customer_segmentation
ORDER BY
    CASE segment_type
        WHEN 'High-Value' THEN 1
        WHEN 'Repeat'     THEN 2
        WHEN 'One-Time'   THEN 3
        WHEN 'Inactive'   THEN 4
    END;

-- ─────────────────────────────────────────────────────────────────────────────
-- TILE 4 — Data Quality Pass Rate per Check (P-04 bonus tile)
-- Chart type : Bar chart (grouped by entity: customers / orders)
-- X-axis     : check_label  (check name + entity, e.g. "completeness (customers)")
-- Y-axis     : pass_rate_pct  (0–100 scale)
-- Reference  : Add a horizontal reference line at 100 to show the perfect-pass mark
-- Tooltip    : total_rows, rows_passed, rows_failed
-- Source     : silver_quality_metrics — reflects the most recent Silver pipeline run
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    CONCAT(check_name, ' (', entity, ')') AS check_label,
    check_name,
    entity,
    total_rows,
    rows_passed,
    rows_failed,
    pass_rate_pct
FROM workspace.ecommerce_medallion.silver_quality_metrics
ORDER BY entity, check_name;

-- ─────────────────────────────────────────────────────────────────────────────
-- TILE 5 — Daily Revenue Trend (bonus tile)
-- Chart type : Line chart
-- X-axis     : order_date  (DATE — ensure the axis is set to Date/Time type)
-- Y-axis     : total_revenue  (primary axis)
-- Y2-axis    : total_orders   (secondary axis, optional)
-- Source     : gold_daily_weekly_trends filtered to period_type = 'daily'
--              (weekly rows are excluded so the line chart stays at daily granularity)
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    period_start   AS order_date,
    total_orders,
    total_revenue,
    avg_order_value
FROM workspace.ecommerce_medallion.gold_daily_weekly_trends
WHERE period_type = 'daily'
ORDER BY order_date;
