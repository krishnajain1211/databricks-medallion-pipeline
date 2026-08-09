# Databricks notebook source

# COMMAND ----------

"""
Purpose  : Tier 2 integration tests (FR-35) — runs directly against the live Delta
           tables in the Databricks workspace, not against local CSVs.
           This is the authoritative proof that the pipeline produces correct output
           on real infrastructure.

           Assertions are a focused subset of the full pandas test suite
           (tests/test_data_quality.py), covering the most important layer-level
           invariants:

             1. Row count conservation  — Silver row counts = Bronze row counts
                                          (nothing was deleted; Silver flags, never drops)
             2. quality_check_result distributions — FAILED_COMPLETENESS,
                FAILED_UNIQUENESS, FAILED_REFERENTIAL_INTEGRITY counts match the
                exact seeded defect counts from DATA_GENERATION_NOTES.md
             3. PASSED row counts — confirms total PASSED = total − failures
             4. Gold row count sanity — four Gold tables within expected ranges
             5. FR-26 revenue cross-check — gold_sales_by_product SUM and
                gold_revenue_by_customer SUM both within $5.00 of Silver PASSED total

           Pattern: all assertions are accumulated into a `_failures` list so every
           check runs even if earlier ones fail.  A final cell raises AssertionError
           only if any check failed, printing a consolidated report.

Inputs   : workspace.ecommerce_medallion.silver_customers  (Delta)
           workspace.ecommerce_medallion.silver_orders     (Delta)
           workspace.ecommerce_medallion.bronze_customers  (Delta — for row count baseline)
           workspace.ecommerce_medallion.bronze_orders     (Delta — for row count baseline)
           workspace.ecommerce_medallion.gold_sales_by_product     (Delta)
           workspace.ecommerce_medallion.gold_revenue_by_customer  (Delta)
           workspace.ecommerce_medallion.gold_customer_segmentation (Delta)
           workspace.ecommerce_medallion.gold_daily_weekly_trends   (Delta)
Outputs  : Console report — PASS / FAIL per assertion, summary at the end
Phase    : Phase 6 — Testing (Tier 2)
Run      : Open in Databricks as a notebook, attach to a running SQL Warehouse or
           cluster, then Run All.  All Gold and Silver tables must exist first.
"""

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA  = "ecommerce_medallion"

def _tbl(name: str):
    """Return a cached Spark DataFrame for the named table."""
    return spark.table(f"{CATALOG}.{SCHEMA}.{name}")

# Accumulator for assertion failures — all checks run even if earlier ones fail.
_failures = []

def _check(label: str, actual, expected, tolerance: float = 0):
    """Assert actual == expected (within tolerance) and log the result.

    Uses float() conversion for diff so that decimal.Decimal values returned
    by Spark aggregate collect() are handled correctly alongside int and float.
    Without the cast, isinstance(Decimal, (int, float)) is False → diff=None
    → the :.2f format spec crashes with TypeError (caught 2026-08-09, testing.md).
    """
    try:
        diff = abs(float(actual) - float(expected))
    except (TypeError, ValueError):
        diff = None

    ok     = (diff <= tolerance) if (diff is not None) else (actual == expected)
    status = "PASS" if ok else "FAIL"

    if tolerance > 0 and diff is not None:
        detail = (
            f"expected {expected:,} ± {tolerance:,.2f}, got {actual:,}, diff={diff:,.2f}"
        )
    else:
        detail = f"expected {expected:,}, got {actual:,}"

    print(f"  [{status}]  {label}  —  {detail}")
    if not ok:
        _failures.append(f"{label}: {detail}")

print("=== Tier 2 Integration Tests — starting ===\n")

# COMMAND ----------

# ── 1. Row count conservation ─────────────────────────────────────────────────
# Silver must have the same number of rows as Bronze (flag only, never delete).

print("── Section 1: Row count conservation (Silver == Bronze)")

bronze_cust_count   = _tbl("bronze_customers").count()
bronze_order_count  = _tbl("bronze_orders").count()
silver_cust_count   = _tbl("silver_customers").count()
silver_order_count  = _tbl("silver_orders").count()

_check("silver_customers row count == bronze_customers",  silver_cust_count,  bronze_cust_count)
_check("silver_orders row count == bronze_orders",        silver_order_count, bronze_order_count)

# Also assert the absolute expected values from DATA_GENERATION_NOTES.md
_check("bronze_customers absolute count",  bronze_cust_count,  10_000)
_check("bronze_orders absolute count",     bronze_order_count, 100_000)

# COMMAND ----------

# ── 2. quality_check_result distributions — Completeness ─────────────────────
# Asserted counts are derived from DATA_GENERATION_NOTES.md with non-overlap guarantee.
#
# customers FAILED_COMPLETENESS = C-01 (50 NULL email only)
# orders    FAILED_COMPLETENESS = O-01 (100 NULL customer_id) + O-02 (200 NULL product_id)
#           = 300 (non-overlapping seeding ranges ensure no double-counting)

print("\n── Section 2: Completeness failures (FAILED_COMPLETENESS counts)")

silver_customers = _tbl("silver_customers")
silver_orders    = _tbl("silver_orders")

comp_fail_cust = silver_customers.filter(
    F.col("quality_check_result").contains("FAILED_COMPLETENESS")
).count()

comp_fail_ord = silver_orders.filter(
    F.col("quality_check_result").contains("FAILED_COMPLETENESS")
).count()

_check("FAILED_COMPLETENESS rows in silver_customers  (C-01: NULL email)",        comp_fail_cust, 50)
_check("FAILED_COMPLETENESS rows in silver_orders  (O-01: 100 + O-02: 200)",      comp_fail_ord, 300)

# COMMAND ----------

# ── 3. quality_check_result distributions — Uniqueness ───────────────────────
# customers FAILED_UNIQUENESS = C-04 (5 pairs × 2 = 10 rows — all copies flagged, A-09)
# orders    FAILED_UNIQUENESS = O-05 (10 pairs × 2 = 20 rows — all copies flagged)

print("\n── Section 3: Uniqueness failures (FAILED_UNIQUENESS counts)")

uniq_fail_cust = silver_customers.filter(
    F.col("quality_check_result").contains("FAILED_UNIQUENESS")
).count()

uniq_fail_ord = silver_orders.filter(
    F.col("quality_check_result").contains("FAILED_UNIQUENESS")
).count()

_check("FAILED_UNIQUENESS rows in silver_customers  (C-04: 5 pairs × 2)", uniq_fail_cust, 10)
_check("FAILED_UNIQUENESS rows in silver_orders     (O-05: 10 pairs × 2)", uniq_fail_ord, 20)

# COMMAND ----------

# ── 4. quality_check_result distributions — Referential Integrity ─────────────
# orders FAILED_REFERENTIAL_INTEGRITY = O-03 (50 orphan customer_id)
#                                     + O-04 (30 orphan product_id)
#                                     = 80  (non-overlapping seeding ranges)
# No referential integrity check is defined for customers in this pipeline.

print("\n── Section 4: Referential integrity failures (FAILED_REFERENTIAL_INTEGRITY counts)")

ri_fail_ord = silver_orders.filter(
    F.col("quality_check_result").contains("FAILED_REFERENTIAL_INTEGRITY")
).count()

_check("FAILED_REFERENTIAL_INTEGRITY rows in silver_orders  (O-03: 50 + O-04: 30)", ri_fail_ord, 80)

# COMMAND ----------

# ── 5. PASSED row counts ──────────────────────────────────────────────────────
# PASSED = total − all failing rows.
# Since defects are seeded in non-overlapping ranges, each row fails at most one check.
#   customers PASSED = 10,000 − 120 (C-01:50 + C-04:10 + C-02:40 + C-03:20) = 9,880
#   orders    PASSED = 100,000 − 580 (all 9 order defect categories)          = 99,420

print("\n── Section 5: PASSED row counts")

passed_cust  = silver_customers.filter(F.col("quality_check_result") == "PASSED").count()
passed_ord   = silver_orders.filter(F.col("quality_check_result") == "PASSED").count()

_check("silver_customers PASSED count  (10,000 − 120 failures)",  passed_cust, 9_880)
_check("silver_orders    PASSED count  (100,000 − 580 failures)", passed_ord,  99_420)

# COMMAND ----------

# ── 6. Gold table row count sanity ────────────────────────────────────────────
# gold_sales_by_product     : ≤ 500  (at most one row per product)
# gold_revenue_by_customer  : ≈ 9,980+ (all unique non-NULL customer_ids in silver_customers)
# gold_daily_weekly_trends  : exactly 1,923 — verified against real Databricks data
#                             (1,682 daily rows + 241 weekly rows, SEED=42 is deterministic)
# gold_customer_segmentation: exactly 4 rows (one per segment_type, always)

print("\n── Section 6: Gold table row count sanity")

n_product = _tbl("gold_sales_by_product").count()
n_cust    = _tbl("gold_revenue_by_customer").count()
n_trends  = _tbl("gold_daily_weekly_trends").count()
n_seg     = _tbl("gold_customer_segmentation").count()

# Range bounds for tables whose exact size varies by data distribution at runtime.
if not (1 <= n_product <= 500):
    _failures.append(f"gold_sales_by_product row count out of range: expected 1–500, got {n_product}")
    print(f"  [FAIL]  gold_sales_by_product row count  —  expected 1–500, got {n_product:,}")
else:
    print(f"  [PASS]  gold_sales_by_product row count  —  {n_product:,} (within 1–500)")

if not (9_000 <= n_cust <= 10_000):
    _failures.append(f"gold_revenue_by_customer row count out of range: expected 9,000–10,000, got {n_cust}")
    print(f"  [FAIL]  gold_revenue_by_customer row count  —  expected 9,000–10,000, got {n_cust:,}")
else:
    print(f"  [PASS]  gold_revenue_by_customer row count  —  {n_cust:,} (within 9,000–10,000)")

# Exact assertions for tables whose row count is fully determined by SEED=42.
_check("gold_customer_segmentation row count (exactly 4 segment types)", n_seg, 4)
_check(
    "gold_daily_weekly_trends row count  (1,682 daily + 241 weekly = 1,923, SEED=42)",
    n_trends, 1_923,
)

# COMMAND ----------

# ── 7. FR-26 Revenue cross-check ─────────────────────────────────────────────
# Both Gold product and customer revenue totals must sum to the Silver PASSED total,
# within the rounding tolerance documented in create_gold_tables.py ($5.00).

print("\n── Section 7: FR-26 Revenue cross-check")

silver_total = (
    silver_orders
    .filter(F.col("quality_check_result") == "PASSED")
    .agg(F.sum("total_amount").alias("total"))
    .collect()[0]["total"]
)

gold_product_total = (
    _tbl("gold_sales_by_product")
    .agg(F.sum("total_revenue").alias("total"))
    .collect()[0]["total"]
)

gold_customer_total = (
    _tbl("gold_revenue_by_customer")
    .agg(F.sum("total_revenue").alias("total"))
    .collect()[0]["total"]
)

print(f"  Silver PASSED total_amount SUM    : ${silver_total:>16,.2f}")
print(f"  gold_sales_by_product SUM         : ${gold_product_total:>16,.2f}")
print(f"  gold_revenue_by_customer SUM      : ${gold_customer_total:>16,.2f}")

# Tolerance = $5.00 — accounts for ROUND(…,2) applied per row in the Gold SQL.
# Max drift = (rows) × $0.005/row: 500 products × $0.005 = $2.50 worst case.
_REVENUE_TOLERANCE = 5.00
_check("gold_sales_by_product SUM ≈ Silver PASSED SUM  (FR-26)",
       gold_product_total,  silver_total, tolerance=_REVENUE_TOLERANCE)
_check("gold_revenue_by_customer SUM ≈ Silver PASSED SUM  (FR-26)",
       gold_customer_total, silver_total, tolerance=_REVENUE_TOLERANCE)

# COMMAND ----------

# ── Final report ──────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
if _failures:
    print(f"INTEGRATION TEST RESULT: FAILED — {len(_failures)} assertion(s) failed")
    print("-" * 65)
    for i, msg in enumerate(_failures, 1):
        print(f"  {i}. {msg}")
    print("=" * 65)
    raise AssertionError(
        f"{len(_failures)} integration assertion(s) failed — see output above."
    )
else:
    print("INTEGRATION TEST RESULT: ALL PASSED")
    print("  All layer-level invariants confirmed against live Delta tables.")
    print("=" * 65)
