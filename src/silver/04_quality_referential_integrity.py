# Databricks notebook source

# COMMAND ----------

"""
Purpose : Silver Layer — Check 4: Referential Integrity.
          Flags orders rows whose foreign-key values do not exist in their
          referenced dimension tables.  Only non-NULL FK values are checked
          (A-11): NULL customer_id and NULL product_id are Completeness
          failures already caught by 01_quality_completeness.py.

Checks — orders only:
  - customer_id IS NOT NULL AND customer_id not in bronze_customers.customer_id
  - product_id  IS NOT NULL AND product_id  not in bronze_products.product_id

No referential integrity check is defined for customers (they are a root
dimension with no FK dependency in this schema).

Inputs  : workspace.ecommerce_medallion.bronze_customers  (Delta — lookup)
          workspace.ecommerce_medallion.bronze_products   (Delta — lookup)
          workspace.ecommerce_medallion.bronze_orders     (Delta — fact)
Outputs : ref_integ_fail_orders   — DataFrame[order_id]
          ref_integ_n_ord_failed  — int
Seeded  : O-03: 50 orphan customer_id (IDs 10001-10050)
          O-04: 30 orphan product_id  (IDs 501-530)
Phase   : Phase 3 — Silver Layer
Run     : Standalone notebook, or %run from create_silver_tables.py
"""

# COMMAND ----------

CATALOG     = "workspace"
SCHEMA_NAME = "ecommerce_medallion"

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# ── Build valid-ID lookup sets from dimension tables ──────────────────────────

valid_customer_ids = (
    spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_customers")
    .select("customer_id")
    .distinct()
)

valid_product_ids = (
    spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_products")
    .select("product_id")
    .distinct()
)

# COMMAND ----------

# ── Check 4: Referential Integrity — orders ───────────────────────────────────
# left_anti join: keeps only rows from orders that have NO matching key in
# the dimension table.  Pre-filter with isNotNull() so NULL FK rows are
# excluded (they are already handled by the completeness check).

bronze_orders = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_orders")

# Orphan customer_id
orphan_by_customer = (
    bronze_orders
    .filter(F.col("customer_id").isNotNull())
    .join(valid_customer_ids, "customer_id", "left_anti")
    .select("order_id")
)

# Orphan product_id
orphan_by_product = (
    bronze_orders
    .filter(F.col("product_id").isNotNull())
    .join(valid_product_ids, "product_id", "left_anti")
    .select("order_id")
)

# Union: a row is flagged if it fails either FK check
ref_integ_fail_orders = (
    orphan_by_customer
    .union(orphan_by_product)
    .distinct()
)

ref_integ_n_ord_failed = ref_integ_fail_orders.count()

# COMMAND ----------

# ── Standalone summary ────────────────────────────────────────────────────────

_n_ord = bronze_orders.count()

print("=== Check 4: Referential Integrity ===")
print(f"  orders    : {ref_integ_n_ord_failed:>6,} rows failed"
      f"  ({ref_integ_n_ord_failed / _n_ord * 100:.2f}% of {_n_ord:,})")
print(f"  [orphan customer_id: {orphan_by_customer.count():,}"
      f"  |  orphan product_id: {orphan_by_product.count():,}]")
