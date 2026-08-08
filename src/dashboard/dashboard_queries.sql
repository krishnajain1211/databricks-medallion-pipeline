-- Purpose : SQL queries for the Databricks SQL Dashboard.
--           Provides 3 required visualisation queries plus 1 bonus quality
--           metrics tile (Polish opportunity P-04).
-- Inputs  : workspace.ecommerce_medallion.gold_sales_by_product
--           workspace.ecommerce_medallion.gold_revenue_by_customer
--           workspace.ecommerce_medallion.gold_customer_segmentation
--           workspace.ecommerce_medallion.silver_quality_metrics
-- Phase   : Phase 5 — Dashboard

-- ── Implementation will be added in Phase 5 ─────────────────────────────────

-- Query 1: Top 10 products by revenue (bar chart)
-- Visualisation: Bar chart — product_name on x-axis, total_revenue on y-axis

-- Query 2: Customer revenue distribution (histogram)
-- Visualisation: Histogram — total_revenue buckets, customer_count on y-axis

-- Query 3: Customer segmentation breakdown (pie chart)
-- Visualisation: Pie chart — segment_type slices, customer_count values

-- Query 4 (bonus P-04): Quality metrics pass rate per check (bar chart)
-- Visualisation: Bar chart — check_name on x-axis, pass_rate_pct on y-axis
-- Source: workspace.ecommerce_medallion.silver_quality_metrics
