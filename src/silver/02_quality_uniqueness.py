"""
Purpose : Silver layer Check 2 — Uniqueness.
          Flags ALL copies of duplicate primary key rows (not just the second
          occurrence). Does not delete any rows; stamps FAILED_UNIQUENESS.
Inputs  : workspace.ecommerce_medallion.bronze_customers (Delta table)
          workspace.ecommerce_medallion.bronze_orders    (Delta table)
Outputs : Adds/updates quality_check_result column on failing rows.
          Returns quality metrics dict: {check: 'uniqueness', passed: N, failed: N}
Seeded  : 10 duplicate customer_id (customers); 20 duplicate order_id (orders)
Phase   : Phase 3 — Silver Layer
"""

# ── Implementation will be added in Phase 3 ─────────────────────────────────
#
# Planned checks:
#   customers: customer_id appears more than once → all copies FAILED_UNIQUENESS
#   orders:    order_id appears more than once    → all copies FAILED_UNIQUENESS
#
# Note: Flag ALL copies (conservative/auditable). Downstream Gold tables filter
#       to quality_check_result = 'PASSED', so no duplicate survives into Gold.
