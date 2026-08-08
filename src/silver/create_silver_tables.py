"""
Purpose : Orchestrate all Silver layer quality checks and produce the final
          silver_customers and silver_orders Delta tables with quality_check_result
          column populated. Also runs the schema contract validation step (P-01)
          before any checks execute, and produces the quality metrics report.
Inputs  : workspace.ecommerce_medallion.bronze_customers (Delta table)
          workspace.ecommerce_medallion.bronze_orders    (Delta table)
          workspace.ecommerce_medallion.bronze_products  (Delta table)
Outputs : workspace.ecommerce_medallion.silver_customers       (Delta table)
          workspace.ecommerce_medallion.silver_orders          (Delta table)
          workspace.ecommerce_medallion.silver_quality_metrics (Delta table)
          Printed quality metrics report (% passed per check)
Phase   : Phase 3 — Silver Layer
Run     : Execute as a Databricks notebook (top-level entry point for Silver)
"""

# ── Implementation will be added in Phase 3 ─────────────────────────────────
#
# Planned execution order:
#   0. Schema contract validation (P-01): assert Bronze table schemas match
#      declared expected schemas — fail fast if columns are missing or types drifted
#   1. %run ./01_quality_completeness
#   2. %run ./02_quality_uniqueness
#   3. %run ./03_quality_type_validation
#   4. %run ./04_quality_referential_integrity
#   5. %run ./05_quality_business_logic   (additive)
#   6. Write silver_customers and silver_orders with quality_check_result populated
#   7. Compute and write quality metrics report (% passed per check)
#   8. Print summary table to notebook output
