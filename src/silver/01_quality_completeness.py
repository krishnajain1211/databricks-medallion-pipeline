"""
Purpose : Silver layer Check 1 — Completeness.
          Flags rows with NULL values in critical fields. Does not delete
          any rows; stamps quality_check_result with FAILED_COMPLETENESS.
Inputs  : workspace.ecommerce_medallion.bronze_customers (Delta table)
          workspace.ecommerce_medallion.bronze_orders    (Delta table)
Outputs : Adds/updates quality_check_result column on failing rows.
          Returns quality metrics dict: {check: 'completeness', passed: N, failed: N}
Seeded  : 50 NULL email (customers); 100 NULL customer_id + 200 NULL product_id (orders)
Phase   : Phase 3 — Silver Layer
"""

# ── Implementation will be added in Phase 3 ─────────────────────────────────
#
# Planned checks:
#   customers: email IS NULL  → FAILED_COMPLETENESS
#   orders:    customer_id IS NULL OR product_id IS NULL → FAILED_COMPLETENESS
#
# Note: payment_date IS NULL is NOT a completeness failure (nullable by design).
# Note: Results are OR-merged with any existing quality_check_result value
#       so multi-failure rows accumulate all codes (see assumption A-10).
