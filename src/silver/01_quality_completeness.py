# Databricks notebook source

# COMMAND ----------

"""
Purpose : Silver Layer — Check 1: Completeness.
          Identifies rows with NULL values in critical fields. Does not write
          any tables; exposes fail-ID DataFrames consumed by create_silver_tables.py.

Checks:
  customers : email IS NULL                              → FAILED_COMPLETENESS
  orders    : customer_id IS NULL  OR  product_id IS NULL → FAILED_COMPLETENESS

Note: payment_date IS NULL is NOT flagged here — it is nullable by design (A-18).
Note: The fail DataFrames contain only the PK of each failing row so the
      orchestrator can left-join them back to Bronze and add a boolean flag.

Inputs  : workspace.ecommerce_medallion.bronze_customers  (Delta)
          workspace.ecommerce_medallion.bronze_orders     (Delta)
Outputs : completeness_fail_customers  — DataFrame[customer_id]  (50 rows expected)
          completeness_fail_orders     — DataFrame[order_id]     (300 rows expected)
          completeness_n_cust_failed   — int
          completeness_n_ord_failed    — int
Seeded  : C-01: 50 NULL email | O-01: 100 NULL customer_id | O-02: 200 NULL product_id
Phase   : Phase 3 — Silver Layer
Run     : Standalone notebook, or %run from create_silver_tables.py
"""

# COMMAND ----------

CATALOG     = "workspace"
SCHEMA_NAME = "ecommerce_medallion"

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# ── Check 1a: Customers — email IS NULL ───────────────────────────────────────

bronze_customers = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_customers")

completeness_fail_customers = (
    bronze_customers
    .filter(F.col("email").isNull())
    .select("customer_id")
    .distinct()
)

completeness_n_cust_failed = completeness_fail_customers.count()

# COMMAND ----------

# ── Check 1b: Orders — customer_id IS NULL or product_id IS NULL ──────────────
# Checked independently so NULL customer_id and NULL product_id are each
# counted as completeness failures (A-11: referential integrity check only
# runs on non-NULL values; completeness check covers the NULL case).

bronze_orders = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_orders")

completeness_fail_orders = (
    bronze_orders
    .filter(F.col("customer_id").isNull() | F.col("product_id").isNull())
    .select("order_id")
    .distinct()
)

completeness_n_ord_failed = completeness_fail_orders.count()

# COMMAND ----------

# ── Standalone summary ────────────────────────────────────────────────────────

_n_cust = bronze_customers.count()
_n_ord  = bronze_orders.count()

print("=== Check 1: Completeness ===")
print(f"  customers : {completeness_n_cust_failed:>6,} rows failed"
      f"  ({completeness_n_cust_failed / _n_cust * 100:.2f}% of {_n_cust:,})")
print(f"  orders    : {completeness_n_ord_failed:>6,} rows failed"
      f"  ({completeness_n_ord_failed / _n_ord  * 100:.2f}% of {_n_ord:,})")
