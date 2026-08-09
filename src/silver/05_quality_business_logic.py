# Databricks notebook source

# COMMAND ----------

"""
Purpose : Silver Layer — Check 5: Business Logic (additive extension, A-01/A-13).
          Flags orders rows that are structurally valid but violate cross-field
          business rules.  This check is in addition to the four named quality
          checks; it does not affect acceptance-criteria count.

Checks — orders only (A-18, A-13):
  Case BL-1 : payment_date < order_date
               — payment recorded before the order existed (seeded: 30 rows, O-09)
  Case BL-2 : order_status = 'Completed' AND payment_date IS NULL
               — completed order with no payment record (defensive guard; 0 seeded)
  Case BL-3 : quantity > 0 AND unit_price > 0
               AND |total_amount − quantity × unit_price| > 0.01
               — arithmetic mismatch with float tolerance (seeded: 40 rows, O-08)
               — Rows with quantity <= 0 or unit_price < 0 are excluded here;
                 they are counted once under type validation (FR-05a, FR-05b).

No business-logic check is defined for customers or products in this schema.

Inputs  : workspace.ecommerce_medallion.bronze_orders  (Delta)
Outputs : business_logic_fail_orders   — DataFrame[order_id]
          business_logic_n_ord_failed  — int
Seeded  : O-08: 40 total_amount mismatch | O-09: 30 payment_date < order_date
Phase   : Phase 3 — Silver Layer
Run     : Standalone notebook, or %run from create_silver_tables.py
"""

# COMMAND ----------

CATALOG     = "workspace"
SCHEMA_NAME = "ecommerce_medallion"

# Floating-point tolerance for the total_amount cross-check (A-13)
_AMT_TOLERANCE = 0.01

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# ── Check 5: Business Logic — orders ─────────────────────────────────────────

bronze_orders = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_orders")

business_logic_fail_orders = (
    bronze_orders
    .filter(
        # BL-1: payment before order date (A-18 case b)
        (F.col("payment_date").isNotNull() & (F.col("payment_date") < F.col("order_date")))

        # BL-2: Completed order has no payment date (A-18 case a — defensive guard)
        | ((F.col("order_status") == "Completed") & F.col("payment_date").isNull())

        # BL-3: total_amount arithmetic mismatch (A-13)
        # Only checked when qty and price are positive (type-valid rows).
        # Zero/negative qty or price rows are flagged under type validation, not here.
        | (
            (F.col("quantity") > 0)
            & (F.col("unit_price") > 0)
            & (
                F.abs(
                    F.col("total_amount") - (F.col("quantity") * F.col("unit_price"))
                ) > _AMT_TOLERANCE
            )
        )
    )
    .select("order_id")
    .distinct()
)

business_logic_n_ord_failed = business_logic_fail_orders.count()

# COMMAND ----------

# ── Standalone summary ────────────────────────────────────────────────────────

_n_ord = bronze_orders.count()

print("=== Check 5: Business Logic ===")
print(f"  orders    : {business_logic_n_ord_failed:>6,} rows failed"
      f"  ({business_logic_n_ord_failed / _n_ord * 100:.2f}% of {_n_ord:,})")
print(f"  Expected breakdown: ~40 (BL-3 amount mismatch) + ~30 (BL-1 payment date)")
