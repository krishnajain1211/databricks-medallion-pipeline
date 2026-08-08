-- Purpose : DDL for all Bronze, Silver, and Gold Delta tables in the
--           workspace.ecommerce_medallion schema (Unity Catalog).
--           Also includes the bronze_ingestion_log and silver_quality_metrics tables.
-- Run     : Execute in a Databricks SQL Warehouse or notebook after the schema
--           and volume are created (see database/setup-notes.md).
-- Phase   : Phase 2 (Bronze tables) → Phase 3 (Silver) → Phase 4 (Gold)

-- ── CREATE SCHEMA ────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS workspace.ecommerce_medallion
COMMENT 'E-commerce medallion pipeline — Bronze, Silver, and Gold tables';

-- ── BRONZE TABLES ────────────────────────────────────────────────────────────

-- Implementation will be added in Phase 2.
-- Planned tables:
--   workspace.ecommerce_medallion.bronze_customers
--   workspace.ecommerce_medallion.bronze_orders
--   workspace.ecommerce_medallion.bronze_products
--   workspace.ecommerce_medallion.bronze_ingestion_log

-- ── SILVER TABLES ────────────────────────────────────────────────────────────

-- Implementation will be added in Phase 3.
-- Planned tables (mirror Bronze schema + quality_check_result STRING column):
--   workspace.ecommerce_medallion.silver_customers
--   workspace.ecommerce_medallion.silver_orders
--   workspace.ecommerce_medallion.silver_quality_metrics

-- ── GOLD TABLES ──────────────────────────────────────────────────────────────

-- Implementation will be added in Phase 4.
-- Planned tables:
--   workspace.ecommerce_medallion.gold_sales_by_product
--   workspace.ecommerce_medallion.gold_revenue_by_customer
--   workspace.ecommerce_medallion.gold_daily_weekly_trends
--   workspace.ecommerce_medallion.gold_customer_segmentation
