# Databricks notebook source

# COMMAND ----------

"""
Purpose : Silver Layer — Check 3: Type Validation.
          Flags rows where field values violate declared type constraints,
          value ranges, or enumeration membership.

Checks — customers:
  - email is non-NULL but fails basic format regex (no @ or no dot-domain)
  - signup_date is in the future (> today)
  - customer_segment not in {Premium, Standard, Basic}

Checks — orders:
  - quantity <= 0          (A-12)
  - unit_price < 0         (A-12)
  - order_status not in {Pending, Completed, Cancelled}  (A-17)

Note: NULL email is a Completeness failure, not Type Validation.
      Zero/negative-quantity rows also have an inconsistent total_amount,
      but they are counted once here (type validation), not additionally
      under business logic — see FR-05a.

Inputs  : workspace.ecommerce_medallion.bronze_customers  (Delta)
          workspace.ecommerce_medallion.bronze_orders     (Delta)
Outputs : type_val_fail_customers  — DataFrame[customer_id]
          type_val_fail_orders     — DataFrame[order_id]
          type_val_n_cust_failed   — int
          type_val_n_ord_failed    — int
Seeded  : C-02: 40 malformed email | C-03: 20 future signup_date
          O-06: 60 zero/neg quantity | O-07: 50 neg unit_price
Phase   : Phase 3 — Silver Layer
Run     : Standalone notebook, or %run from create_silver_tables.py
"""

# COMMAND ----------

CATALOG     = "workspace"
SCHEMA_NAME = "ecommerce_medallion"

_VALID_SEGMENTS  = ["Premium", "Standard", "Basic"]
_VALID_STATUSES  = ["Pending", "Completed", "Cancelled"]

# Email must have non-empty local part, @, domain with at least one dot.
# Same pattern used in generate_sample_data.py for seeding and verification.
_EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# ── Check 3a: Customers ───────────────────────────────────────────────────────

bronze_customers = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_customers")

type_val_fail_customers = (
    bronze_customers
    .filter(
        # Malformed email: non-NULL but invalid format (FR-04a)
        (F.col("email").isNotNull() & ~F.col("email").rlike(_EMAIL_REGEX))
        # Future signup_date: valid date string but semantically impossible (FR-04b)
        | (F.col("signup_date").isNotNull() & (F.col("signup_date") > F.current_date()))
        # Invalid customer_segment enum value (A-17)
        | (~F.col("customer_segment").isin(_VALID_SEGMENTS))
    )
    .select("customer_id")
    .distinct()
)

type_val_n_cust_failed = type_val_fail_customers.count()

# COMMAND ----------

# ── Check 3b: Orders ──────────────────────────────────────────────────────────

bronze_orders = spark.table(f"{CATALOG}.{SCHEMA_NAME}.bronze_orders")

type_val_fail_orders = (
    bronze_orders
    .filter(
        # Zero or negative quantity (FR-05a, A-12)
        (F.col("quantity").isNotNull() & (F.col("quantity") <= 0))
        # Negative unit_price (FR-05b, A-12)
        | (F.col("unit_price").isNotNull() & (F.col("unit_price") < 0))
        # Invalid order_status enum value (A-17)
        | (~F.col("order_status").isin(_VALID_STATUSES))
    )
    .select("order_id")
    .distinct()
)

type_val_n_ord_failed = type_val_fail_orders.count()

# COMMAND ----------

# ── Standalone summary ────────────────────────────────────────────────────────

_n_cust = bronze_customers.count()
_n_ord  = bronze_orders.count()

print("=== Check 3: Type Validation ===")
print(f"  customers : {type_val_n_cust_failed:>6,} rows failed"
      f"  ({type_val_n_cust_failed / _n_cust * 100:.2f}% of {_n_cust:,})")
print(f"  orders    : {type_val_n_ord_failed:>6,} rows failed"
      f"  ({type_val_n_ord_failed / _n_ord  * 100:.2f}% of {_n_ord:,})")
