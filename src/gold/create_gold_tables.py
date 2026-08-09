# Databricks notebook source

# COMMAND ----------

"""
Purpose  : Orchestrate all four Gold layer aggregation tables in dependency order.
           Sources only Silver rows with quality_check_result = 'PASSED'.
           Each sub-notebook is run via %run so the SQL lives in exactly one place.
Inputs   : workspace.ecommerce_medallion.silver_customers (quality_check_result = 'PASSED')
           workspace.ecommerce_medallion.silver_orders    (quality_check_result = 'PASSED')
           workspace.ecommerce_medallion.bronze_products  (product metadata, all rows)
Outputs  : workspace.ecommerce_medallion.gold_sales_by_product      (Delta table)
           workspace.ecommerce_medallion.gold_revenue_by_customer    (Delta table)
           workspace.ecommerce_medallion.gold_daily_weekly_trends    (Delta table)
           workspace.ecommerce_medallion.gold_customer_segmentation  (Delta table)
Phase    : Phase 4 — Gold Layer
Run      : Top-level entry point for Gold.  Execute this notebook to rebuild all
           four Gold tables from scratch (CREATE OR REPLACE).
%run note: Each SQL notebook gets its own two-cell block — a label comment cell
           followed immediately by a bare %run cell — to avoid the silent-failure
           bug where Databricks ignores a magic command that is not the first
           content line of its cell (lesson from Bronze debugging, 2026-08).
"""

import datetime

run_start = datetime.datetime.now()
print(f"Gold layer build started at {run_start.strftime('%Y-%m-%d %H:%M:%S')}")

# COMMAND ----------

# ── Step 1: gold_sales_by_product ────────────────────────────────────────────

# COMMAND ----------

# MAGIC %run ./01_sales_by_product

# COMMAND ----------

# ── Step 2: gold_revenue_by_customer ─────────────────────────────────────────

# COMMAND ----------

# MAGIC %run ./02_revenue_by_customer

# COMMAND ----------

# ── Step 3: gold_daily_weekly_trends ─────────────────────────────────────────

# COMMAND ----------

# MAGIC %run ./03_daily_weekly_trends

# COMMAND ----------

# ── Step 4: gold_customer_segmentation ───────────────────────────────────────

# COMMAND ----------

# MAGIC %run ./04_customer_segmentation

# COMMAND ----------

# ── Smoke checks: row counts for all four Gold tables ────────────────────────

gold_tables = [
    "gold_sales_by_product",
    "gold_revenue_by_customer",
    "gold_daily_weekly_trends",
    "gold_customer_segmentation",
]

print("\n=== Gold Layer Build Complete ===")
print(f"{'Table':<35} {'Row Count':>10}")
print("-" * 47)

for table in gold_tables:
    full_name = f"workspace.ecommerce_medallion.{table}"
    count = spark.table(full_name).count()
    print(f"{table:<35} {count:>10,}")

run_end = datetime.datetime.now()
elapsed = (run_end - run_start).total_seconds()
print(f"\nCompleted in {elapsed:.1f}s at {run_end.strftime('%Y-%m-%d %H:%M:%S')}")

# COMMAND ----------

# ── Aggregation spot-checks (FR-26) ──────────────────────────────────────────
# Verify that the total revenue in gold matches what the Silver PASSED rows show.
# Both values should be equal (within floating-point rounding).

silver_total = (
    spark.table("workspace.ecommerce_medallion.silver_orders")
    .filter("quality_check_result = 'PASSED'")
    .agg({"total_amount": "sum"})
    .collect()[0][0]
)

gold_product_total = (
    spark.table("workspace.ecommerce_medallion.gold_sales_by_product")
    .agg({"total_revenue": "sum"})
    .collect()[0][0]
)

gold_customer_total = (
    spark.table("workspace.ecommerce_medallion.gold_revenue_by_customer")
    .agg({"total_revenue": "sum"})
    .collect()[0][0]
)

print("\n=== Revenue Cross-Check (FR-26) ===")
print(f"Silver PASSED total_amount SUM : ${silver_total:>15,.2f}")
print(f"gold_sales_by_product SUM      : ${gold_product_total:>15,.2f}")
print(f"gold_revenue_by_customer SUM   : ${gold_customer_total:>15,.2f}")


# Gold SQL applies ROUND(..., 2) to each product/customer row before summing.
# Each ROUND() can introduce ±$0.005; with up to 500 products or 10 000 customers
# the worst-case cumulative drift is ~$50.  We tolerate up to $5 here (well within
# the expected range for our 500-product, 10 000-customer dataset).
tolerance = 5.00

product_ok  = abs(silver_total - gold_product_total)  <= tolerance
customer_ok = abs(silver_total - gold_customer_total) <= tolerance

print(f"\ngold_sales_by_product match     : {'PASS' if product_ok  else 'FAIL'}"
      f"  (diff = ${abs(silver_total - gold_product_total):.2f})")
print(f"gold_revenue_by_customer match  : {'PASS' if customer_ok else 'FAIL'}"
      f"  (diff = ${abs(silver_total - gold_customer_total):.2f})")

if not (product_ok and customer_ok):
    raise AssertionError(
        "Gold revenue totals deviate from Silver source by more than the rounding "
        f"tolerance (${tolerance:.2f}).  Investigate for missing or duplicate rows."
    )
