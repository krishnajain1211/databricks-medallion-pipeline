# Databricks notebook source

# COMMAND ----------

"""
Purpose : Orchestrate all five Silver quality checks, build silver_customers and
          silver_orders Delta tables with a quality_check_result column on every
          row, and write a silver_quality_metrics summary table.

Execution order:
  1. %run each check notebook (01-05) — each reads Bronze, exposes fail-ID DataFrames
  2. Read Bronze tables once in this notebook
  3. Left-join each fail-ID DataFrame back to Bronze on PK → boolean flag columns
  4. Build quality_check_result via concat_ws + when (A-10: all failures accumulated)
  5. Write silver_customers and silver_orders (overwrite)
  6. Compute pass-rate metrics per check per entity → write silver_quality_metrics

quality_check_result values (FR-18):
  "PASSED"
  "FAILED_COMPLETENESS"
  "FAILED_UNIQUENESS"
  "FAILED_TYPE_VALIDATION"
  "FAILED_REFERENTIAL_INTEGRITY"
  "FAILED_BUSINESS_LOGIC"
  Comma-delimited combinations when a row fails more than one check (A-10).

Inputs  : workspace.ecommerce_medallion.bronze_customers  (Delta)
          workspace.ecommerce_medallion.bronze_orders     (Delta)
          workspace.ecommerce_medallion.bronze_products   (Delta — for ref-int lookup)
Outputs : workspace.ecommerce_medallion.silver_customers      (Delta, overwrite)
          workspace.ecommerce_medallion.silver_orders         (Delta, overwrite)
          workspace.ecommerce_medallion.silver_quality_metrics (Delta, overwrite)
Phase   : Phase 3 — Silver Layer
Run     : Execute as a Databricks notebook (top-level Silver entry point)
"""

# COMMAND ----------

from datetime import datetime
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType, LongType, StringType, StructField, StructType, TimestampType,
)

CATALOG     = "workspace"
SCHEMA_NAME = "ecommerce_medallion"

run_start = datetime.now()
print(f"Silver pipeline started at {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
print("-" * 60)

# COMMAND ----------

# ── Step 1: Run all five quality checks ───────────────────────────────────────
# IMPORTANT: each %run must be the FIRST content line of its own cell.
# A comment or blank line before # MAGIC demotes the cell to plain Python
# and the %run is silently ignored (see ai-prompts/bronze-layer.md Debug 1).

# COMMAND ----------

# Step 1a — Completeness

# COMMAND ----------

# MAGIC %run ./01_quality_completeness

# COMMAND ----------

# Step 1b — Uniqueness

# COMMAND ----------

# MAGIC %run ./02_quality_uniqueness

# COMMAND ----------

# Step 1c — Type Validation

# COMMAND ----------

# MAGIC %run ./03_quality_type_validation

# COMMAND ----------

# Step 1d — Referential Integrity

# COMMAND ----------

# MAGIC %run ./04_quality_referential_integrity

# COMMAND ----------

# Step 1e — Business Logic

# COMMAND ----------

# MAGIC %run ./05_quality_business_logic

# COMMAND ----------

# ── Step 2: Read Bronze tables once in orchestrator scope ─────────────────────
# The check scripts also read Bronze internally (for standalone usability), but
# we read them again here to build clean Silver DataFrames without side-effects.

bronze_customers = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_customers")
bronze_orders    = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_orders")

print("Bronze tables loaded.")

# COMMAND ----------

# ── Step 3 & 4: Build silver_customers ────────────────────────────────────────
# Three checks apply to customers: Completeness, Uniqueness, Type Validation.
#
# Join strategy: each fail-ID DataFrame holds the DISTINCT PK values of
# failing rows. A left-join on PK propagates True to all matching Bronze rows
# (including BOTH copies of a duplicated ID — A-09). Non-matching rows get
# null, filled to False.

silver_customers = (
    bronze_customers
    # Completeness flag
    .join(
        completeness_fail_customers.withColumn("_fc", F.lit(True)),
        "customer_id", "left",
    )
    # Uniqueness flag
    .join(
        uniqueness_fail_customers.withColumn("_fu", F.lit(True)),
        "customer_id", "left",
    )
    # Type Validation flag
    .join(
        type_val_fail_customers.withColumn("_ftv", F.lit(True)),
        "customer_id", "left",
    )
    .fillna({"_fc": False, "_fu": False, "_ftv": False})
    .withColumn(
        "quality_check_result",
        F.when(
            ~F.col("_fc") & ~F.col("_fu") & ~F.col("_ftv"),
            F.lit("PASSED"),
        ).otherwise(
            F.concat_ws(
                ",",
                F.when(F.col("_fc"),  F.lit("FAILED_COMPLETENESS")),
                F.when(F.col("_fu"),  F.lit("FAILED_UNIQUENESS")),
                F.when(F.col("_ftv"), F.lit("FAILED_TYPE_VALIDATION")),
            )
        ),
    )
    .drop("_fc", "_fu", "_ftv")
)

# COMMAND ----------

# ── Step 3 & 4: Build silver_orders ──────────────────────────────────────────
# Five checks apply to orders: Completeness, Uniqueness, Type Validation,
# Referential Integrity, Business Logic.

silver_orders = (
    bronze_orders
    # Completeness flag
    .join(
        completeness_fail_orders.withColumn("_fc",  F.lit(True)),
        "order_id", "left",
    )
    # Uniqueness flag
    .join(
        uniqueness_fail_orders.withColumn("_fu", F.lit(True)),
        "order_id", "left",
    )
    # Type Validation flag
    .join(
        type_val_fail_orders.withColumn("_ftv", F.lit(True)),
        "order_id", "left",
    )
    # Referential Integrity flag
    .join(
        ref_integ_fail_orders.withColumn("_fri", F.lit(True)),
        "order_id", "left",
    )
    # Business Logic flag
    .join(
        business_logic_fail_orders.withColumn("_fbl", F.lit(True)),
        "order_id", "left",
    )
    .fillna({"_fc": False, "_fu": False, "_ftv": False, "_fri": False, "_fbl": False})
    .withColumn(
        "quality_check_result",
        F.when(
            ~F.col("_fc") & ~F.col("_fu") & ~F.col("_ftv")
            & ~F.col("_fri") & ~F.col("_fbl"),
            F.lit("PASSED"),
        ).otherwise(
            F.concat_ws(
                ",",
                F.when(F.col("_fc"),  F.lit("FAILED_COMPLETENESS")),
                F.when(F.col("_fu"),  F.lit("FAILED_UNIQUENESS")),
                F.when(F.col("_ftv"), F.lit("FAILED_TYPE_VALIDATION")),
                F.when(F.col("_fri"), F.lit("FAILED_REFERENTIAL_INTEGRITY")),
                F.when(F.col("_fbl"), F.lit("FAILED_BUSINESS_LOGIC")),
            )
        ),
    )
    .drop("_fc", "_fu", "_ftv", "_fri", "_fbl")
)

# COMMAND ----------

# ── Step 5: Write Silver tables ───────────────────────────────────────────────

(
    silver_customers.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA_NAME}.silver_customers")
)
print(f"Written: {CATALOG}.{SCHEMA_NAME}.silver_customers")

(
    silver_orders.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA_NAME}.silver_orders")
)
print(f"Written: {CATALOG}.{SCHEMA_NAME}.silver_orders")

# COMMAND ----------

# ── Step 6: Compute quality metrics (FR-19) ───────────────────────────────────
# Per-check, per-entity pass rates — written to silver_quality_metrics and
# displayed as a table in the notebook output.

def _metrics_rows(entity: str, table_name: str, total: int) -> list:
    """
    Build one metrics row per quality check for the given entity.
    Reads quality_check_result from the written Silver table to count failures.
    """
    df = spark.table(table_name)
    checks = {
        "completeness":           "FAILED_COMPLETENESS",
        "uniqueness":             "FAILED_UNIQUENESS",
        "type_validation":        "FAILED_TYPE_VALIDATION",
        "referential_integrity":  "FAILED_REFERENTIAL_INTEGRITY",
        "business_logic":         "FAILED_BUSINESS_LOGIC",
    }
    rows = []
    for check_name, code in checks.items():
        failed = df.filter(F.col("quality_check_result").contains(code)).count()
        passed = total - failed
        rows.append((
            check_name,
            entity,
            total,
            passed,
            failed,
            round(passed / total * 100, 2),
            run_start,
        ))
    return rows

_n_cust = silver_customers.count()
_n_ord  = silver_orders.count()

_metrics_schema = StructType([
    StructField("check_name",    StringType(),    False),
    StructField("entity",        StringType(),    False),
    StructField("total_rows",    LongType(),      False),
    StructField("rows_passed",   LongType(),      False),
    StructField("rows_failed",   LongType(),      False),
    StructField("pass_rate_pct", DoubleType(),    False),
    StructField("run_timestamp", TimestampType(), False),
])

metrics_rows = (
    _metrics_rows("customers", f"{CATALOG}.{SCHEMA_NAME}.silver_customers", _n_cust) +
    _metrics_rows("orders",    f"{CATALOG}.{SCHEMA_NAME}.silver_orders",    _n_ord)
)

quality_metrics_df = spark.createDataFrame(metrics_rows, schema=_metrics_schema)

(
    quality_metrics_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA_NAME}.silver_quality_metrics")
)
print(f"Written: {CATALOG}.{SCHEMA_NAME}.silver_quality_metrics")

# COMMAND ----------

# ── Step 7: Display quality metrics report ────────────────────────────────────

run_end = datetime.now()
elapsed = (run_end - run_start).seconds

print(f"\n{'=' * 60}")
print(f"  QUALITY METRICS REPORT  ({elapsed}s total)")
print(f"{'=' * 60}")

display(
    spark.table(f"{CATALOG}.{SCHEMA_NAME}.silver_quality_metrics")
    .select("entity", "check_name", "total_rows", "rows_failed", "rows_passed", "pass_rate_pct")
    .orderBy("entity", "check_name")
)

print("\nRow count summary:")
print(f"  silver_customers : {_n_cust:,} rows")
print(f"  silver_orders    : {_n_ord:,}  rows")
print(f"\n  silver_customers PASSED : "
      f"{silver_customers.filter(F.col('quality_check_result') == 'PASSED').count():,}")
print(f"  silver_orders    PASSED : "
      f"{silver_orders.filter(F.col('quality_check_result') == 'PASSED').count():,}")
