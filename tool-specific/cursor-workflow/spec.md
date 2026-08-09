# Design Specification

> Condensed design spec shared with Cursor at the start of coding phases.
> This is the "what to build" document — the source of truth for architecture
> decisions, naming conventions, and acceptance standards.

---

## Pipeline Architecture

```
CSV Files (Unity Catalog Volume)
        ↓  [Bronze: raw ingest, no transforms]
Bronze Delta Tables (bronze_*)
        ↓  [Silver: 4 quality checks + business logic, stamp quality_check_result]
Silver Delta Tables (silver_*)
        ↓  [Gold: aggregate PASSED rows only → 4 analyst tables]
Gold Delta Tables (gold_*)
        ↓  [Dashboard: 4 SQL tiles in Databricks SQL]
Databricks SQL Dashboard
```

---

## Unity Catalog Environment

| Setting | Value |
|---|---|
| Catalog | `workspace` |
| Schema | `ecommerce_medallion` |
| Volume name | `raw_data` |
| Volume path | `/Volumes/workspace/ecommerce_medallion/raw_data/` |
| Table pattern | `workspace.ecommerce_medallion.<table_name>` |

---

## Source Data Schemas

### customers.csv — 10,000 rows

| Field | Type | Notes |
|---|---|---|
| customer_id | INT | PK |
| customer_name | STRING | |
| email | STRING | nullable |
| country | STRING | |
| signup_date | DATE | |
| customer_segment | STRING | Premium / Standard / Basic |
| lifetime_value | DECIMAL | |

### orders.csv — 100,000 rows

| Field | Type | Notes |
|---|---|---|
| order_id | INT | PK |
| customer_id | INT | FK → customers |
| order_date | DATE | |
| product_id | INT | FK → products |
| quantity | INT | |
| unit_price | DECIMAL | |
| total_amount | DECIMAL | |
| order_status | STRING | Pending / Completed / Cancelled |
| payment_date | DATE | nullable |

### products.csv — 500 rows

| Field | Type | Notes |
|---|---|---|
| product_id | INT | PK |
| product_name | STRING | |
| category | STRING | |
| price | DECIMAL | |
| cost | DECIMAL | |
| stock_quantity | INT | |
| reorder_level | INT | |

---

## Silver Layer: Quality Check Specifications

All checks stamp `quality_check_result` on each row. Rows failing multiple checks
receive a comma-delimited code string (e.g., `FAILED_COMPLETENESS,FAILED_UNIQUENESS`).
Passing rows receive `PASSED`. No rows are deleted.

| Check | File | Code stamped | Seeded test cases |
|---|---|---|---|
| 1. Completeness | `01_quality_completeness.py` | `FAILED_COMPLETENESS` | 350 rows |
| 2. Uniqueness | `02_quality_uniqueness.py` | `FAILED_UNIQUENESS` | 30 rows |
| 3. Type Validation | `03_quality_type_validation.py` | `FAILED_TYPE_VALIDATION` | 170 rows |
| 4. Referential Integrity | `04_quality_referential_integrity.py` | `FAILED_REFERENTIAL_INTEGRITY` | 80 rows |
| 5. Business Logic (bonus) | `05_quality_business_logic.py` | `FAILED_BUSINESS_LOGIC` | 70 rows |

Schema contract validation (`00_schema_contract` step in `create_silver_tables.py`)
runs before all checks and fails fast if Bronze schemas have drifted.

---

## Gold Layer: Aggregation Table Specifications

All Gold tables source only Silver rows where `quality_check_result = 'PASSED'`.

| Table | Source | Key columns |
|---|---|---|
| `gold_sales_by_product` | silver_orders + bronze_products | product_id, product_name, category, total_orders, total_revenue, avg_order_value |
| `gold_revenue_by_customer` | silver_orders + silver_customers | customer_id, customer_name, customer_segment, total_orders, total_revenue, avg_order_value, lifetime_value_actual |
| `gold_daily_weekly_trends` | silver_orders | order_date, week_start_date, daily_revenue, weekly_revenue, daily_order_count, weekly_order_count |
| `gold_customer_segmentation` | silver_orders + silver_customers | segment_type, customer_count, avg_revenue, total_revenue |

Segmentation rules (to be finalised in Phase 4):
- **High-Value**: `total_revenue > 5000` (set in Phase 4; documented as tunable in SQL comment)
- **Repeat**: total_orders ≥ 2, not High-Value
- **One-Time**: total_orders = 1
- **Inactive**: in silver_customers but 0 PASSED orders

---

## Testing Approach

**Tier 1 (local pytest):** pandas reimplementation of each quality check logic,
loaded from `data/` CSVs. Asserts >= expected seeded failure count per check.
Run with: `pytest tests/ -v`

**Tier 2 (Databricks notebook):** `tests/integration_test_silver_gold.py` — queries
live Silver and Gold Delta tables and validates row counts and quality distributions.

---

## Naming Conventions

- Python files and variables: `snake_case`
- SQL identifiers: `snake_case`
- Table naming: `<layer>_<entity>` (e.g., `bronze_customers`, `silver_orders`)
- Quality codes: `FAILED_<CHECK_NAME>` in CAPS
- Git tags: `phase-N-<name>` (e.g., `phase-1-data-generation`)
- Commit messages: `feat(phase-N): <description>`

---

## Hard Rules (non-negotiable)

1. Silver layer NEVER deletes rows — only stamps `quality_check_result`
2. Every function and script has a docstring with Purpose, Inputs, Outputs
3. No real PII — all data is synthetic
4. Every non-trivial architectural decision is documented before coding
5. `workspace.ecommerce_medallion.<table>` namespace used throughout
