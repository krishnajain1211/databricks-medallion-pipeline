# Databricks notebook source

# COMMAND ----------

"""
Purpose : Orchestrate Bronze layer ingestion for all three source tables.
          Runs each individual ingest notebook in dependency order
          (products first — it is the lighter reference table; customers
          second; orders last as the largest file), then displays a
          consolidated ingestion summary from bronze_ingestion_log.
Inputs  : /Volumes/workspace/ecommerce_medallion/raw_data/  (all three CSVs)
Outputs : workspace.ecommerce_medallion.bronze_customers      (Delta, overwrite)
          workspace.ecommerce_medallion.bronze_orders         (Delta, overwrite)
          workspace.ecommerce_medallion.bronze_products       (Delta, overwrite)
          workspace.ecommerce_medallion.bronze_ingestion_log  (3 rows appended)
Phase   : Phase 2 — Bronze Layer
Run     : Execute as a Databricks notebook (top-level Bronze entry point)
"""

# COMMAND ----------

from datetime import datetime, timedelta

run_start = datetime.now()
print(f"Bronze ingestion started at {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
print("─" * 60)

# COMMAND ----------

# ── Step 1: Products (reference table — smallest file) ───────────────────────
# Cell above is a label comment; %run must be the FIRST line of its own cell.

# COMMAND ----------

# MAGIC %run ./03_ingest_products

# COMMAND ----------

# ── Step 2: Customers ─────────────────────────────────────────────────────────

# COMMAND ----------

# MAGIC %run ./01_ingest_customers

# COMMAND ----------

# ── Step 3: Orders (largest file — run last) ──────────────────────────────────

# COMMAND ----------

# MAGIC %run ./02_ingest_orders

# COMMAND ----------

# ── Summary: query bronze_ingestion_log for this run's entries ────────────────
# Shows the three rows appended during this run, ordered by ingestion time.
# A 10-second buffer is subtracted from run_start to guard against serverless
# cold-start clock skew — the cluster's wall clock can lag the driver's
# datetime.now() by a few seconds at startup.

run_end = datetime.now()
elapsed = (run_end - run_start).seconds

print(f"\n{'─' * 60}")
print(f"Bronze ingestion complete  ({elapsed}s)")
print(f"{'─' * 60}\n")

_filter_from = (run_start - timedelta(seconds=10)).strftime('%Y-%m-%d %H:%M:%S')

summary_df = spark.sql(f"""
    SELECT
        table_name,
        row_count,
        source_path,
        DATE_FORMAT(ingestion_timestamp, 'yyyy-MM-dd HH:mm:ss') AS ingested_at
    FROM workspace.ecommerce_medallion.bronze_ingestion_log
    WHERE ingestion_timestamp >= '{_filter_from}'
    ORDER BY ingested_at
""")

display(summary_df)
