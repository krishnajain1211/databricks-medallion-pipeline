# Databricks notebook source

# COMMAND ----------

"""
Purpose : Ingest products.csv from Unity Catalog Volumes into the
          bronze_products Delta table. Raw data only — no transformations
          or quality checks. Logs row count, source path, and ingestion
          timestamp to bronze_ingestion_log.
Inputs  : /Volumes/workspace/ecommerce_medallion/raw_data/products.csv
Outputs : workspace.ecommerce_medallion.bronze_products        (Delta, overwrite)
          workspace.ecommerce_medallion.bronze_ingestion_log   (Delta, append)
Phase   : Phase 2 — Bronze Layer
Run     : Execute as a Databricks notebook, or %run from ingest_all.py
"""

# COMMAND ----------

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_VOLUME_PATH = "/Volumes/workspace/ecommerce_medallion/raw_data"
CATALOG          = "workspace"
SCHEMA_NAME      = "ecommerce_medallion"
TARGET_TABLE     = f"{CATALOG}.{SCHEMA_NAME}.bronze_products"
LOG_TABLE        = f"{CATALOG}.{SCHEMA_NAME}.bronze_ingestion_log"
SOURCE_FILE      = "products.csv"
EXPECTED_ROWS    = 500

# COMMAND ----------

from datetime import datetime
from pyspark.sql.types import (
    DecimalType, IntegerType, LongType,
    StringType, StructField, StructType, TimestampType,
)

# COMMAND ----------

# ── Explicit source schema (FR-09) ────────────────────────────────────────────
# products.csv has no seeded quality issues — it is clean reference data.
# The explicit schema still guards against future data drift.

products_schema = StructType([
    StructField("product_id",     IntegerType(),      True),
    StructField("product_name",   StringType(),       True),
    StructField("category",       StringType(),       True),
    StructField("price",          DecimalType(10, 2), True),
    StructField("cost",           DecimalType(10, 2), True),
    StructField("stock_quantity", IntegerType(),      True),
    StructField("reorder_level",  IntegerType(),      True),
])

log_schema = StructType([
    StructField("table_name",          StringType(),    False),
    StructField("source_path",         StringType(),    False),
    StructField("row_count",           LongType(),      False),
    StructField("ingestion_timestamp", TimestampType(), False),
])

# COMMAND ----------

# ── Read CSV from Unity Catalog Volume (FR-07, FR-09, FR-11) ─────────────────
source_path = f"{BASE_VOLUME_PATH}/{SOURCE_FILE}"

df = (
    spark.read
    .format("csv")
    .option("header", "true")
    .schema(products_schema)
    .load(source_path)
)

print(f"Rows read from source : {df.count():,}")

# COMMAND ----------

# ── Write to Bronze Delta table — no transformations (FR-08, FR-11) ───────────
(
    df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TARGET_TABLE)
)

# COMMAND ----------

# ── Log ingestion metadata (FR-10) ────────────────────────────────────────────
row_count = spark.table(TARGET_TABLE).count()

log_entry = spark.createDataFrame(
    [(TARGET_TABLE, source_path, row_count, datetime.now())],
    schema=log_schema,
)
(
    log_entry.write
    .format("delta")
    .mode("append")
    .option("mergeSchema", "true")
    .saveAsTable(LOG_TABLE)
)

# COMMAND ----------

# ── Smoke check ───────────────────────────────────────────────────────────────
assert row_count == EXPECTED_ROWS, (
    f"Row count mismatch for {TARGET_TABLE}: "
    f"expected {EXPECTED_ROWS:,}, got {row_count:,}. "
    "Verify that products.csv was uploaded to the Volume before running."
)

print(f"✓ {TARGET_TABLE}")
print(f"  Rows ingested : {row_count:,}")
print(f"  Source        : {source_path}")
print(f"  Timestamp     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
