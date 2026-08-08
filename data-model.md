# Data Model

> Field-level data dictionary, entity relationships, layer-by-layer row counts,
> and lineage notes. Updated incrementally as each phase completes.

## Entity Relationship Overview

_[Text-based ERD and Mermaid diagram to be added in Phase 0 / Phase 2.]_

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

_[To be filled in as each phase completes — see P-02 in requirements-analysis.md.]_

| Layer | Table | Row count | Notes |
|---|---|---|---|
| Source | customers.csv | 10,000 | 120 quality issues |
| Source | orders.csv | 100,000 | 580 quality issues |
| Source | products.csv | 500 | 0 quality issues |
| Bronze | bronze_customers | _TBD Phase 2_ | Raw copy, unchanged |
| Bronze | bronze_orders | _TBD Phase 2_ | Raw copy, unchanged |
| Bronze | bronze_products | _TBD Phase 2_ | Raw copy, unchanged |
| Silver | silver_customers | _TBD Phase 3_ | Includes quality_check_result |
| Silver | silver_orders | _TBD Phase 3_ | Includes quality_check_result |
| Gold | gold_sales_by_product | _TBD Phase 4_ | Aggregated from Silver PASSED |
| Gold | gold_revenue_by_customer | _TBD Phase 4_ | Aggregated from Silver PASSED |
| Gold | gold_daily_weekly_trends | _TBD Phase 4_ | Aggregated from Silver PASSED |
| Gold | gold_customer_segmentation | _TBD Phase 4_ | Aggregated from Silver PASSED |

## Silver → Gold Lineage

_[Which Silver columns feed which Gold fields — to be documented in Phase 4.]_
