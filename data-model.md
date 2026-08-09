# Data Model

> Field-level data dictionary, entity relationships, layer-by-layer row counts,
> and lineage notes. Updated incrementally as each phase completes.

## Entity Relationship Overview

```
customers (customer_id PK)
    ↑ FK
orders (order_id PK, customer_id FK, product_id FK)
    ↑ FK
products (product_id PK)
```

## Source Table Schemas

### customers.csv
| Field | Type | Constraints | Notes |
|---|---|---|---|
| customer_id | INT | PK | 10 rows intentionally duplicated |
| customer_name | STRING | NOT NULL | |
| email | STRING | nullable | 50 rows NULL; 40 rows malformed format |
| country | STRING | NOT NULL | |
| signup_date | DATE | NOT NULL | 20 rows future-dated (> today) |
| customer_segment | STRING | Premium/Standard/Basic | |
| lifetime_value | DECIMAL | NOT NULL | |

### orders.csv
| Field | Type | Constraints | Notes |
|---|---|---|---|
| order_id | INT | PK | 20 rows intentionally duplicated |
| customer_id | INT | FK → customers | 100 rows NULL; 50 rows orphan |
| order_date | DATE | NOT NULL | |
| product_id | INT | FK → products | 200 rows NULL; 30 rows orphan |
| quantity | INT | NOT NULL | 60 rows zero/negative |
| unit_price | DECIMAL | NOT NULL | 50 rows negative |
| total_amount | DECIMAL | NOT NULL | 40 rows mismatched (≠ quantity × unit_price) |
| order_status | STRING | Pending/Completed/Cancelled | |
| payment_date | DATE | nullable | 30 rows before order_date |

### products.csv
| Field | Type | Constraints | Notes |
|---|---|---|---|
| product_id | INT | PK | No seeded issues |
| product_name | STRING | NOT NULL | |
| category | STRING | NOT NULL | |
| price | DECIMAL | NOT NULL | |
| cost | DECIMAL | NOT NULL | |
| stock_quantity | INT | NOT NULL | |
| reorder_level | INT | NOT NULL | |

## Unity Catalog Naming

| Component | Value |
|---|---|
| Catalog | `workspace` |
| Schema | `ecommerce_medallion` |
| Volume path | `/Volumes/workspace/ecommerce_medallion/raw_data/` |
| Bronze tables | `workspace.ecommerce_medallion.bronze_customers` etc. |
| Silver tables | `workspace.ecommerce_medallion.silver_customers` etc. |
| Gold tables | `workspace.ecommerce_medallion.gold_sales_by_product` etc. |

## Layer-by-Layer Row Counts

Verified counts from Phase 2 (Bronze), Phase 3 (Silver), and Phase 4 (Gold) Databricks runs.

| Layer | Table | Row count | Notes |
|---|---|---|---|
| Source | customers.csv | 10,000 | 120 quality issues across 4 categories |
| Source | orders.csv | 100,000 | 580 quality issues across 9 categories |
| Source | products.csv | 500 | 0 quality issues |
| Bronze | bronze_customers | 10,000 | Raw copy, unchanged |
| Bronze | bronze_orders | 100,000 | Raw copy, unchanged |
| Bronze | bronze_products | 500 | Raw copy, unchanged |
| Silver | silver_customers | 10,000 | Same count as Bronze — no rows deleted; `quality_check_result` added; 9,880 PASSED |
| Silver | silver_orders | 100,000 | Same count as Bronze — no rows deleted; `quality_check_result` added; 99,420 PASSED |
| Gold | gold_sales_by_product | ≤ 500 | One row per distinct product present in PASSED orders |
| Gold | gold_revenue_by_customer | ~9,995 | 10,000 customers deduped to 9,995 unique customer_ids (G-08 fix); includes all unique customers |
| Gold | gold_daily_weekly_trends | 1,923 | 1,682 daily rows + 241 weekly rows; verified SEED=42 (see ai-prompts/gold-layer.md) |
| Gold | gold_customer_segmentation | 4 | Exactly 4 rows — one per segment type (High-Value, Repeat, One-Time, Inactive) |

## Silver → Gold Lineage

| Gold table | Source Silver columns | Join / filter |
|---|---|---|
| `gold_sales_by_product` | `silver_orders`: `product_id`, `order_id` (COUNT), `total_amount` (SUM, AVG) | INNER JOIN `bronze_products` on `product_id`; WHERE `quality_check_result = 'PASSED'` |
| `gold_revenue_by_customer` | `silver_customers`: `customer_id` (deduped), `customer_name`, `customer_segment`, `lifetime_value`; `silver_orders`: `customer_id` (JOIN key), `order_id` (COUNT), `total_amount` (SUM, AVG) | CTE deduplication on `customer_id`; orders side: WHERE `quality_check_result = 'PASSED'` |
| `gold_daily_weekly_trends` | `silver_orders`: `order_date` (GROUP BY day / ISO week), `total_amount` (SUM) | WHERE `quality_check_result = 'PASSED'`; UNION ALL of daily and weekly aggregations |
| `gold_customer_segmentation` | `silver_customers`: `customer_id` (deduped), `customer_segment`; `silver_orders`: `total_amount` (SUM per customer) | CTE deduplication on `customer_id`; revenue used to assign High-Value / Repeat / One-Time / Inactive tier |
