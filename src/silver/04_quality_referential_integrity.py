"""
Purpose : Silver layer Check 4 — Referential Integrity.
          Flags orders rows where a non-NULL foreign key has no matching
          primary key in the parent table. NULL FK values are a Completeness
          failure (checked separately) and are excluded from this check.
          Does not delete any rows; stamps FAILED_REFERENTIAL_INTEGRITY.
Inputs  : workspace.ecommerce_medallion.bronze_customers (Delta table)
          workspace.ecommerce_medallion.bronze_orders    (Delta table)
          workspace.ecommerce_medallion.bronze_products  (Delta table)
Outputs : Adds/updates quality_check_result column on failing rows.
          Returns quality metrics dict: {check: 'referential_integrity', passed: N, failed: N}
Seeded  : 50 orphan customer_id + 30 orphan product_id (orders, non-NULL only)
Phase   : Phase 3 — Silver Layer
"""

# ── Implementation will be added in Phase 3 ─────────────────────────────────
#
# Planned checks:
#   orders (WHERE customer_id IS NOT NULL):
#     customer_id NOT IN (SELECT customer_id FROM bronze_customers)
#     → FAILED_REFERENTIAL_INTEGRITY
#   orders (WHERE product_id IS NOT NULL):
#     product_id NOT IN (SELECT product_id FROM bronze_products)
#     → FAILED_REFERENTIAL_INTEGRITY
#
# Note: Using LEFT ANTI JOIN pattern for performance on 100k rows.
