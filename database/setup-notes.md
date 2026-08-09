# Environment Setup Notes

> Step-by-step instructions for initialising the Databricks Free Edition workspace
> before running any pipeline scripts (FR-37).
>
> **Actual setup status:** Steps 1 and 2 below were completed manually via the
> Databricks UI during initial environment configuration — not via SQL. The
> equivalent SQL is included here for reproducibility and for any reviewer who
> wants to recreate the environment from scratch.

---

## Prerequisites

- Databricks Free Edition workspace (serverless) — active and accessible
- Unity Catalog enabled (default in Free Edition; `workspace` catalog pre-created)
- Git integration configured (Databricks Repos or workspace Git folder)
- Python 3.x with `pandas`, `numpy`, and `faker` installed locally (data generation only)

---

## Step 1: Create the Unity Catalog Schema

**Actual method used:** Created via Databricks UI → Data → Create Schema.
- Catalog: `workspace`  
- Schema name: `ecommerce_medallion`

**Equivalent SQL (run in a SQL Warehouse or notebook for reproducibility):**

```sql
CREATE SCHEMA IF NOT EXISTS workspace.ecommerce_medallion
COMMENT 'E-commerce medallion pipeline — Bronze, Silver, and Gold Delta tables';
```

---

## Step 2: Create the Unity Catalog Volume

**Actual method used:** Created via Databricks UI → Data → `ecommerce_medallion` schema
→ Create Volume.
- Volume name: `raw_data`
- Volume type: Managed

**Equivalent SQL:**

```sql
CREATE VOLUME IF NOT EXISTS workspace.ecommerce_medallion.raw_data
COMMENT 'Raw CSV source files uploaded before Bronze ingestion';
```

Volume path after creation: `/Volumes/workspace/ecommerce_medallion/raw_data/`

---

## Step 3: Upload CSV Files to the Volume

Upload the three generated CSVs from `data/` to the Volume using either method:

**Option A — Databricks UI:**
1. Navigate to Catalog → workspace → ecommerce_medallion → raw_data → Files
2. Click **Upload** and select each file

**Option B — Databricks CLI (requires `databricks` CLI installed and configured):**

```bash
databricks fs cp data/customers.csv  dbfs:/Volumes/workspace/ecommerce_medallion/raw_data/customers.csv
databricks fs cp data/orders.csv     dbfs:/Volumes/workspace/ecommerce_medallion/raw_data/orders.csv
databricks fs cp data/products.csv   dbfs:/Volumes/workspace/ecommerce_medallion/raw_data/products.csv
```

Expected files after upload:
```
/Volumes/workspace/ecommerce_medallion/raw_data/customers.csv   (~1.1 MB, 10,000 rows)
/Volumes/workspace/ecommerce_medallion/raw_data/orders.csv      (~8-9 MB, 100,000 rows)
/Volumes/workspace/ecommerce_medallion/raw_data/products.csv    (~30 KB, 500 rows)
```

---

## Step 4: Run the DDL Script

Execute `database/schema.sql` in a SQL Warehouse to create all Bronze, Silver, and
Gold tables. The DDL uses `CREATE TABLE IF NOT EXISTS` throughout, so it is safe to
re-run.

```sql
-- Paste contents of database/schema.sql into a SQL Warehouse query editor, or
-- use the Databricks CLI:
-- databricks sql execute --warehouse-id <id> --file database/schema.sql
```

---

## Step 5: Verify Setup

Run these checks in a notebook or SQL Warehouse to confirm the environment is ready:

```sql
-- Confirm schema and volume exist
SHOW SCHEMAS IN workspace;
SHOW VOLUMES IN workspace.ecommerce_medallion;

-- Confirm CSV files are readable
SELECT COUNT(*) FROM read_files(
  '/Volumes/workspace/ecommerce_medallion/raw_data/customers.csv',
  format => 'csv', header => true
);
-- Expected: 10000

SELECT COUNT(*) FROM read_files(
  '/Volumes/workspace/ecommerce_medallion/raw_data/orders.csv',
  format => 'csv', header => true
);
-- Expected: 100000

SELECT COUNT(*) FROM read_files(
  '/Volumes/workspace/ecommerce_medallion/raw_data/products.csv',
  format => 'csv', header => true
);
-- Expected: 500
```

---

## Step 6: Run the Pipeline

Execute notebooks in order:

| Order | Notebook                              | Layer  | Entry point?      |
|-------|---------------------------------------|--------|-------------------|
| 1     | `src/bronze/ingest_all.py`            | Bronze | Yes — runs 01-03  |
| 2     | `src/silver/create_silver_tables.py`  | Silver | Yes — runs 01-05  |
| 3     | `src/gold/create_gold_tables.py`      | Gold   | Yes — runs 01-04  |
| 4     | `src/dashboard/dashboard_queries.sql` | Dash.  | Run in SQL Editor |

Each entry-point notebook calls its sub-notebooks via `%run` and displays a
completion summary.
