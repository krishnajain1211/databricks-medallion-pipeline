# databricks-medallion-pipeline

> End-to-end Databricks Medallion Architecture pipeline (Bronze → Silver → Gold → Dashboard)
> for an e-commerce sales use case, built as part of an AI-capability assessment.
> All data is synthetic. No real customer or PII data is used anywhere in this project.

---

## Quick Start

### Prerequisites

- **Databricks Free Edition** (serverless) — Community Edition was retired January 1, 2026
- Unity Catalog enabled with catalog `workspace` already created
- Python 3.x with `pandas`, `numpy`, and `faker` installed locally (for data generation only)
- `pytest` installed locally (for Tier 1 tests only)

### Step 1 — Generate sample data (local)

```bash
pip install pandas numpy faker
python src/data_generation/generate_sample_data.py
```

Outputs three CSVs to `data/`: `customers.csv` (10,000 rows), `orders.csv` (100,000 rows),
`products.csv` (500 rows). A defect verification table is printed — all 13 categories should
show `True` in the `match` column.

### Step 2 — Create the Databricks environment

Run the following SQL in a Databricks SQL editor (or use the UI — see `database/setup-notes.md`):

```sql
CREATE SCHEMA IF NOT EXISTS workspace.ecommerce_medallion;
CREATE VOLUME IF NOT EXISTS workspace.ecommerce_medallion.raw_data;
```

Then upload the three CSVs to the Volume:
- **UI:** Catalog → workspace → ecommerce_medallion → raw_data → Upload
- **CLI:** `databricks fs cp data/customers.csv dbfs:/Volumes/workspace/ecommerce_medallion/raw_data/`

Full setup instructions (including verification steps) in `database/setup-notes.md`.

### Step 3 — Import notebooks into Databricks

Import the following files as Databricks notebooks (they use `# Databricks notebook source`
format and can be imported directly via the Databricks UI or Git integration):

```
src/bronze/ingest_all.py
src/silver/create_silver_tables.py
src/gold/create_gold_tables.py
tests/integration_test_silver_gold.py
```

### Step 4 — Run the pipeline in order

| Step | Notebook | Expected output |
|---|---|---|
| 1 | `src/bronze/ingest_all.py` | 3 Bronze Delta tables; ingestion log populated |
| 2 | `src/silver/create_silver_tables.py` | 2 Silver Delta tables; quality metrics table; `quality_check_result` on every row |
| 3 | `src/gold/create_gold_tables.py` | 4 Gold Delta tables; FR-26 revenue cross-check prints PASS |
| 4 | Dashboard | Attach `src/dashboard/dashboard_queries.sql` queries to a new Databricks SQL Dashboard — see `src/dashboard/DASHBOARD_GUIDE.md` |

### Step 5 — Run local tests

```bash
pytest tests/ -v
```

All 21 tests should pass in under 1 second. These tests run against the local CSVs in `data/`
and require no Databricks connection.

### Step 6 — Run integration tests (optional, requires live pipeline)

Run `tests/integration_test_silver_gold.py` as a Databricks notebook after Steps 1–3.
Final cell should print `ALL PASSED`.

---

## Repository Structure

```
databricks-medallion-pipeline/
├── README.md                               # This file
├── candidate-info.md                       # Submitter details and dashboard URL
├── tool-workflow.md                        # Part A: AI Workflow Foundation
├── requirements-analysis.md               # Full requirement analysis, gap log, assumptions
├── design-notes.md                         # Architecture and design decisions
├── data-model.md                           # ERD, schemas, row counts, Silver→Gold lineage
├── data-quality-strategy.md               # Four quality checks + verified metrics
├── debugging-notes.md                     # Chronological bug log (9 entries)
├── reflection.md                           # Honest AI-assisted workflow reflection
├── final-ai-usage-summary.md              # Executive summary of AI usage end-to-end
│
├── src/
│   ├── data_generation/
│   │   ├── generate_sample_data.py        # Generates 3 CSVs with 700 seeded defects (SEED=42)
│   │   └── DATA_GENERATION_NOTES.md       # 13-section breakdown of every defect category
│   ├── bronze/
│   │   ├── 01_ingest_customers.py         # Databricks notebook: ingest customers CSV → Delta
│   │   ├── 02_ingest_orders.py            # Databricks notebook: ingest orders CSV → Delta
│   │   ├── 03_ingest_products.py          # Databricks notebook: ingest products CSV → Delta
│   │   └── ingest_all.py                  # Orchestrator: runs all three ingest notebooks
│   ├── silver/
│   │   ├── 01_quality_completeness.py     # Check: NULL in critical fields
│   │   ├── 02_quality_uniqueness.py       # Check: duplicate PKs
│   │   ├── 03_quality_type_validation.py  # Check: malformed email, future dates, bad numerics
│   │   ├── 04_quality_referential_integrity.py  # Check: orphan FK values
│   │   ├── 05_quality_business_logic.py   # Check: amount mismatch, payment before order
│   │   └── create_silver_tables.py        # Orchestrator: runs all checks, writes Silver tables
│   ├── gold/
│   │   ├── 01_sales_by_product.sql        # Aggregation: product revenue and order volume
│   │   ├── 02_revenue_by_customer.sql     # Aggregation: per-customer revenue (G-08 fix applied)
│   │   ├── 03_daily_weekly_trends.sql     # Aggregation: daily and weekly revenue trends
│   │   ├── 04_customer_segmentation.sql   # Aggregation: High-Value/Repeat/One-Time/Inactive
│   │   └── create_gold_tables.py          # Orchestrator: runs all SQL + FR-26 cross-check
│   └── dashboard/
│       ├── dashboard_queries.sql           # Five SQL queries for Databricks SQL Dashboard tiles
│       └── DASHBOARD_GUIDE.md             # Step-by-step instructions to build the dashboard
│
├── data/
│   ├── customers.csv                       # 10,000 rows, 120 seeded quality issues
│   ├── orders.csv                          # 100,000 rows, 580 seeded quality issues
│   └── products.csv                        # 500 rows, 0 quality issues
│
├── database/
│   ├── schema.sql                          # CREATE TABLE DDL for all Bronze/Silver/Gold tables
│   ├── setup-notes.md                      # Databricks environment setup guide (6 steps)
│   └── seed-data-notes.md                 # Seed data overview and quality issue rationale
│
├── tests/
│   ├── test_data_quality.py               # 16 pytest tests: Silver checks vs seeded defects
│   ├── test_transformations.py            # 5 pytest tests: Gold aggregation logic
│   └── integration_test_silver_gold.py    # Databricks integration notebook (7 assertion sections)
│
├── docs/
│   └── assessment-requirements.md         # Original assessment specification
│
├── ai-prompts/                             # Full AI prompt history — one file per phase
│   ├── requirement-analysis.md
│   ├── data-generation.md
│   ├── bronze-layer.md
│   ├── silver-layer.md
│   ├── gold-layer.md
│   ├── dashboard.md
│   ├── debugging.md                        # Index pointing to debugging entries in layer files
│   ├── testing.md
│   └── documentation.md
│
└── tool-specific/
    └── cursor-workflow/
        ├── project-context.md              # Project setup context provided to Cursor
        ├── spec.md                         # Technical specification used in prompts
        ├── cursor-rules-or-instructions.md # .cursor/rules/ persistent project constraints
        └── task-breakdown.md              # Phase-by-phase task log with results
```

---

## Pipeline Overview

```
CSV files (data/)
      │
      ▼  src/bronze/ingest_all.py
  Bronze Delta tables
  (raw, unchanged, + ingestion metadata)
      │
      ▼  src/silver/create_silver_tables.py
  Silver Delta tables
  (all rows preserved; quality_check_result column on every row)
  + silver_quality_metrics table (pass rate per check)
      │
      ▼  src/gold/create_gold_tables.py
  Gold Delta tables (PASSED rows only)
  ├── gold_sales_by_product        (≤500 rows)
  ├── gold_revenue_by_customer     (~9,995 rows)
  ├── gold_daily_weekly_trends     (1,923 rows)
  └── gold_customer_segmentation   (4 rows)
      │
      ▼  Databricks SQL Dashboard
  5 tiles: Top Products · Revenue Distribution · Segmentation ·
           Quality Checks · Daily Revenue Trend
```

### Data Quality Design

The Silver layer **flags bad rows — it never deletes them.** Every row in
`silver_customers` and `silver_orders` carries a `quality_check_result` column:
- `PASSED` — row passed all applicable checks
- `FAILED_COMPLETENESS`, `FAILED_UNIQUENESS`, `FAILED_TYPE_VALIDATION`,
  `FAILED_REFERENTIAL_INTEGRITY`, `FAILED_BUSINESS_LOGIC` — stamped on failing rows
- Multiple failures are comma-delimited (e.g., `FAILED_COMPLETENESS,FAILED_UNIQUENESS`)

Gold tables source only `quality_check_result = 'PASSED'` rows from Silver, with one
exception: the customer dimension is deduplicated by `customer_id` regardless of the
customer record's quality result (a customer with a bad email address still has valid
transactions — see Gap G-08 in `requirements-analysis.md`).

### Known Limitations

- The `$5,000` High-Value customer segmentation threshold was set based on estimated
  average revenue. A data-derived threshold (e.g., p75 of `gold_revenue_by_customer`)
  would be more defensible for a real business deployment.
- `create_gold_tables.py` uses `overwrite` mode — re-running the Gold layer replaces
  all Gold tables. This is intentional for a batch pipeline but would need adjustment
  for incremental loads.
