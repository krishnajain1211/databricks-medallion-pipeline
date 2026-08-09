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
-- Raw ingestion tables — schema mirrors source CSVs exactly.
-- All columns nullable to preserve seeded defects (NULLs, etc.) unchanged.

CREATE TABLE IF NOT EXISTS workspace.ecommerce_medallion.bronze_customers (
    customer_id       INT,
    customer_name     STRING,
    email             STRING,
    country           STRING,
    signup_date       DATE,
    customer_segment  STRING,
    lifetime_value    DECIMAL(10, 2)
)
USING DELTA
COMMENT 'Bronze: raw customers data ingested from customers.csv — no transformations applied';

CREATE TABLE IF NOT EXISTS workspace.ecommerce_medallion.bronze_orders (
    order_id      INT,
    customer_id   INT,
    order_date    DATE,
    product_id    INT,
    quantity      INT,
    unit_price    DECIMAL(10, 2),
    total_amount  DECIMAL(12, 2),
    order_status  STRING,
    payment_date  DATE            -- nullable: Pending orders have no payment date
)
USING DELTA
COMMENT 'Bronze: raw orders data ingested from orders.csv — no transformations applied';

CREATE TABLE IF NOT EXISTS workspace.ecommerce_medallion.bronze_products (
    product_id      INT,
    product_name    STRING,
    category        STRING,
    price           DECIMAL(10, 2),
    cost            DECIMAL(10, 2),
    stock_quantity  INT,
    reorder_level   INT
)
USING DELTA
COMMENT 'Bronze: raw products data ingested from products.csv — no transformations applied';

CREATE TABLE IF NOT EXISTS workspace.ecommerce_medallion.bronze_ingestion_log (
    table_name          STRING    NOT NULL,
    source_path         STRING    NOT NULL,
    row_count           BIGINT    NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Append-only log of every Bronze ingestion run: table name, source path, row count, timestamp';

-- ── SILVER TABLES ────────────────────────────────────────────────────────────
-- Mirror Bronze schemas exactly, plus a quality_check_result STRING column.
-- All rows preserved (FR-18); quality_check_result is 'PASSED' or a
-- comma-delimited list of failure codes (A-10).

CREATE TABLE IF NOT EXISTS workspace.ecommerce_medallion.silver_customers (
    customer_id           INT,
    customer_name         STRING,
    email                 STRING,
    country               STRING,
    signup_date           DATE,
    customer_segment      STRING,
    lifetime_value        DECIMAL(10, 2),
    quality_check_result  STRING    NOT NULL
)
USING DELTA
COMMENT 'Silver: customers with quality_check_result stamped on every row';

CREATE TABLE IF NOT EXISTS workspace.ecommerce_medallion.silver_orders (
    order_id              INT,
    customer_id           INT,
    order_date            DATE,
    product_id            INT,
    quantity              INT,
    unit_price            DECIMAL(10, 2),
    total_amount          DECIMAL(12, 2),
    order_status          STRING,
    payment_date          DATE,
    quality_check_result  STRING    NOT NULL
)
USING DELTA
COMMENT 'Silver: orders with quality_check_result stamped on every row';

CREATE TABLE IF NOT EXISTS workspace.ecommerce_medallion.silver_quality_metrics (
    check_name    STRING     NOT NULL,
    entity        STRING     NOT NULL,
    total_rows    BIGINT     NOT NULL,
    rows_passed   BIGINT     NOT NULL,
    rows_failed   BIGINT     NOT NULL,
    pass_rate_pct DOUBLE     NOT NULL,
    run_timestamp TIMESTAMP  NOT NULL
)
USING DELTA
COMMENT 'Per-check pass rates for the most recent Silver pipeline run';

-- ── GOLD TABLES ──────────────────────────────────────────────────────────────

-- Implementation will be added in Phase 4.
-- Planned tables:
--   workspace.ecommerce_medallion.gold_sales_by_product
--   workspace.ecommerce_medallion.gold_revenue_by_customer
--   workspace.ecommerce_medallion.gold_daily_weekly_trends
--   workspace.ecommerce_medallion.gold_customer_segmentation
