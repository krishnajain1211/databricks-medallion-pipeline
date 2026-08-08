"""
Purpose : Ingest customers.csv from Unity Catalog Volumes into the
          bronze_customers Delta table. Raw data only — no transformations
          or quality checks. Logs row count, source path, and timestamp.
Inputs  : /Volumes/workspace/ecommerce_medallion/raw_data/customers.csv
Outputs : workspace.ecommerce_medallion.bronze_customers (Delta table)
          workspace.ecommerce_medallion.bronze_ingestion_log (row appended)
Phase   : Phase 2 — Bronze Layer
Run     : Execute as a Databricks notebook or %run from ingest_all.py
"""

# ── Implementation will be added in Phase 2 ─────────────────────────────────
#
# Planned steps:
#   1. Define BASE_VOLUME_PATH constant (swappable without touching logic)
#   2. Read customers.csv with explicit schema (no schema inference drift)
#   3. Write to bronze_customers as Delta table (overwrite mode)
#   4. Log: row_count, source_path, ingestion_timestamp to bronze_ingestion_log
#   5. Assert row_count == 10000 as a basic smoke check
