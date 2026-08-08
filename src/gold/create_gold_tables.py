"""
Purpose : Orchestrate all four Gold layer aggregation tables in dependency order.
          Sources only Silver rows with quality_check_result = 'PASSED'.
Inputs  : workspace.ecommerce_medallion.silver_customers (Delta table)
          workspace.ecommerce_medallion.silver_orders    (Delta table)
          workspace.ecommerce_medallion.bronze_products  (Delta table, for product metadata)
Outputs : workspace.ecommerce_medallion.gold_sales_by_product      (Delta table)
          workspace.ecommerce_medallion.gold_revenue_by_customer    (Delta table)
          workspace.ecommerce_medallion.gold_daily_weekly_trends    (Delta table)
          workspace.ecommerce_medallion.gold_customer_segmentation  (Delta table)
Phase   : Phase 4 — Gold Layer
Run     : Execute as a Databricks notebook (top-level entry point for Gold)
"""

# ── Implementation will be added in Phase 4 ─────────────────────────────────
#
# Planned execution order:
#   1. %run / spark.sql from ./01_sales_by_product.sql
#   2. %run / spark.sql from ./02_revenue_by_customer.sql
#   3. %run / spark.sql from ./03_daily_weekly_trends.sql
#   4. %run / spark.sql from ./04_customer_segmentation.sql
#   5. Print row count for each Gold table as a smoke check
