# Databricks notebook source

# COMMAND ----------

"""
Purpose : Silver Layer — Check 2: Uniqueness.
          Identifies rows whose primary-key value appears more than once.
          ALL copies of a duplicated key are flagged (A-09 — conservative choice;
          downstream Gold tables filter to PASSED rows, so no duplicate survives).

Checks:
  customers : duplicate customer_id → FAILED_UNIQUENESS  (5 pairs = 10 rows)
  orders    : duplicate order_id    → FAILED_UNIQUENESS  (10 pairs = 20 rows)

Inputs  : workspace.ecommerce_medallion.bronze_customers  (Delta)
          workspace.ecommerce_medallion.bronze_orders     (Delta)
Outputs : uniqueness_fail_customers  — DataFrame[customer_id]  (5 distinct IDs)
          uniqueness_fail_orders     — DataFrame[order_id]     (10 distinct IDs)
          uniqueness_n_cust_failed   — int  (affected rows: 10)
          uniqueness_n_ord_failed    — int  (affected rows: 20)
Seeded  : C-04: 5 duplicate customer_id pairs | O-05: 10 duplicate order_id pairs
Phase   : Phase 3 — Silver Layer
Run     : Standalone notebook, or %run from create_silver_tables.py
"""

# COMMAND ----------

CATALOG     = "workspace"
SCHEMA_NAME = "ecommerce_medallion"

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# ── Check 2a: Customers — duplicate customer_id ───────────────────────────────
# Aggregate to find customer_ids with count > 1.  The resulting DataFrame holds
# only the *distinct* duplicated IDs; the orchestrator's left-join maps both
# copies of each ID back to bronze_customers, flagging all of them (A-09).

bronze_customers = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_customers")

uniqueness_fail_customers = (
    bronze_customers
    .groupBy("customer_id")
    .count()
    .filter(F.col("count") > 1)
    .select("customer_id")
)

# Affected row count = rows in bronze that share one of the duplicated IDs
uniqueness_n_cust_failed = (
    bronze_customers
    .join(uniqueness_fail_customers, "customer_id", "inner")
    .count()
)

# COMMAND ----------

# ── Check 2b: Orders — duplicate order_id ────────────────────────────────────

bronze_orders = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_orders")

uniqueness_fail_orders = (
    bronze_orders
    .groupBy("order_id")
    .count()
    .filter(F.col("count") > 1)
    .select("order_id")
)

uniqueness_n_ord_failed = (
    bronze_orders
    .join(uniqueness_fail_orders, "order_id", "inner")
    .count()
)

# COMMAND ----------

# ── Standalone summary ────────────────────────────────────────────────────────

_n_cust = bronze_customers.count()
_n_ord  = bronze_orders.count()

print("=== Check 2: Uniqueness ===")
print(f"  customers : {uniqueness_n_cust_failed:>6,} rows failed"
      f"  ({uniqueness_n_cust_failed / _n_cust * 100:.2f}% of {_n_cust:,})"
      f"  [{uniqueness_fail_customers.count()} distinct duplicate IDs]")
print(f"  orders    : {uniqueness_n_ord_failed:>6,} rows failed"
      f"  ({uniqueness_n_ord_failed / _n_ord  * 100:.2f}% of {_n_ord:,})"
      f"  [{uniqueness_fail_orders.count()} distinct duplicate IDs]")
