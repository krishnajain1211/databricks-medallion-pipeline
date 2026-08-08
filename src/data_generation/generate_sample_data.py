"""
Purpose : Generate synthetic CSV seed data for the e-commerce medallion pipeline.
          Introduces exactly 700 intentional quality issues across 13 categories,
          seeding test cases for all four Silver layer quality checks and the
          Business Logic check.
Inputs  : None — all parameters configured via constants defined at top of file.
Outputs : data/customers.csv  — 10,000 rows, 120 quality issues
          data/orders.csv     — 100,000 rows, 580 quality issues
          data/products.csv   — 500 rows, 0 quality issues
Phase   : Phase 1 — Data Generation
Run     : python src/data_generation/generate_sample_data.py
          (runs locally; requires pandas and faker — no Databricks connection needed)
"""

# ── Implementation will be added in Phase 1 ─────────────────────────────────
#
# Planned issue categories (no overlap between rows within each category):
#
# customers.csv (120 issues):
#   - 50  NULL email                           → seeds Completeness check
#   - 10  duplicate customer_id                → seeds Uniqueness check
#   - 40  malformed email (no @ or bad domain) → seeds Type Validation check
#   - 20  future-dated signup_date (> today)   → seeds Type Validation check
#
# orders.csv (580 issues):
#   - 100 NULL customer_id                     → seeds Completeness check
#   - 200 NULL product_id                      → seeds Completeness check
#   - 50  orphan customer_id (not in customers)→ seeds Referential Integrity check
#   - 30  orphan product_id (not in products)  → seeds Referential Integrity check
#   - 20  duplicate order_id                   → seeds Uniqueness check
#   - 60  zero or negative quantity            → seeds Type Validation check
#   - 50  negative unit_price                  → seeds Type Validation check
#   - 40  total_amount != quantity * unit_price → seeds Business Logic check
#   - 30  payment_date < order_date            → seeds Business Logic check
#
# products.csv (0 issues): clean reference data only
