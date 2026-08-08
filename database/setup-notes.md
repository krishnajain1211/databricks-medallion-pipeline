# Environment Setup Notes

> Step-by-step instructions for initialising the Databricks Free Edition workspace
> before running any pipeline scripts. To be completed and verified in Phase 2.

## Prerequisites

- Databricks Free Edition workspace (serverless)
- Unity Catalog enabled (default in Free Edition)
- Python 3.x with `pandas` and `faker` installed locally (for data generation)

## Step 1: Create the Unity Catalog Schema

Run in a Databricks SQL Warehouse or notebook:

```sql
CREATE SCHEMA IF NOT EXISTS workspace.ecommerce_medallion
COMMENT 'E-commerce medallion pipeline — Bronze, Silver, and Gold tables';
```

## Step 2: Create the Unity Catalog Volume

```sql
CREATE VOLUME IF NOT EXISTS workspace.ecommerce_medallion.raw_data
COMMENT 'Raw CSV source files for Bronze ingestion';
```

Volume path after creation: `/Volumes/workspace/ecommerce_medallion/raw_data/`

## Step 3: Upload CSV Files to the Volume

_[Upload instructions (Databricks UI or CLI) — to be documented in Phase 2.]_

Upload:
- `data/customers.csv` → `/Volumes/workspace/ecommerce_medallion/raw_data/customers.csv`
- `data/orders.csv`    → `/Volumes/workspace/ecommerce_medallion/raw_data/orders.csv`
- `data/products.csv`  → `/Volumes/workspace/ecommerce_medallion/raw_data/products.csv`

## Step 4: Run the DDL Script

```sql
-- Run database/schema.sql in a SQL Warehouse
```

## Step 5: Verify Setup

_[Verification queries — to be documented in Phase 2.]_
