"""
Purpose : Orchestrate ingestion of all three Bronze layer sources in order:
          customers → products → orders. Runs each individual ingest script
          and prints a summary of row counts on completion.
Inputs  : /Volumes/workspace/ecommerce_medallion/raw_data/ (all three CSVs)
Outputs : workspace.ecommerce_medallion.bronze_customers (Delta table)
          workspace.ecommerce_medallion.bronze_orders    (Delta table)
          workspace.ecommerce_medallion.bronze_products  (Delta table)
          workspace.ecommerce_medallion.bronze_ingestion_log (3 rows appended)
Phase   : Phase 2 — Bronze Layer
Run     : Execute as a Databricks notebook (top-level entry point for Bronze)
"""

# ── Implementation will be added in Phase 2 ─────────────────────────────────
#
# Planned steps:
#   1. %run ./01_ingest_customers
#   2. %run ./03_ingest_products   (products before orders — FK reference table first)
#   3. %run ./02_ingest_orders
#   4. Print summary: table name, row count, ingestion timestamp for all three
