# AI Prompts — Gold Layer

> Prompt history for all exchanges related to Gold layer aggregation scripts
> (`01_sales_by_product.sql` through `04_customer_segmentation.sql`,
> `create_gold_tables.py`). Entries are added after each significant exchange.
> Format: see Section 5 of `requirements-analysis.md` for the standard entry template.

---

## Prompt 1: Implement all four Gold layer SQL scripts + create_gold_tables.py

**Date:** 2026-08-09
**Phase:** 4 — Gold Layer
**User prompt (summary):** Phase 3 (Silver) verified — all failure counts matched
the 700-defect spec, row counts confirmed nothing deleted. Proceed to Phase 4:
read requirements-analysis.md FR-21 through FR-26 and A-02; implement all four
`gold/*.sql` scripts + `create_gold_tables.py` orchestrator using correct `%run`
format (per Bronze/Silver lessons already logged); source only
`quality_check_result = 'PASSED'` rows from silver tables; write to
`workspace.ecommerce_medallion.gold_*`; ask if anything is ambiguous.

**AI response summary:**

### Files written
| File | Purpose |
|------|---------|
| `src/gold/01_sales_by_product.sql` | Gold A — product-level order volume + revenue |
| `src/gold/02_revenue_by_customer.sql` | Gold B — per-customer revenue + lifetime value |
| `src/gold/03_daily_weekly_trends.sql` | Gold C — daily & weekly revenue trends |
| `src/gold/04_customer_segmentation.sql` | Gold D — four-tier customer segments |
| `src/gold/create_gold_tables.py` | Orchestrator: %run each SQL, smoke checks, FR-26 cross-check |
| `database/schema.sql` | Added Gold DDL (four `CREATE TABLE IF NOT EXISTS` blocks) |

### Key design decisions

**SQL file format:** All four `.sql` files are Databricks SQL notebook format
(`-- Databricks notebook source` header, `-- COMMAND ----------` cell separators).
This means they can be run standalone in the SQL editor AND `%run` from the
Python orchestrator — SQL lives in exactly one place.

**`lifetime_value_actual` (FR-22):** Interpreted as the stored `lifetime_value`
field from `silver_customers` (the declared/estimated customer attribute from
source data), while `total_revenue` = computed `SUM(total_amount)` from PASSED
orders. Keeping both columns lets analysts compare declared vs. earned revenue.
This interpretation was documented explicitly since FR-22 did not define it.

**High-Value segmentation threshold (FR-24):** Used `total_revenue > 5000`.
Rationale: average customer revenue ≈ 10 orders × ~$550 avg ≈ $5,500, so $5,000
captures roughly the above-median customers. Threshold is documented as a
tunable design choice in the SQL comment — adjust after reviewing the
`gold_revenue_by_customer` distribution.

**Daily/weekly trends table structure (FR-23):** Single table with a `period_type`
column (`'daily'` | `'weekly'`) and a `period_start` DATE column, using UNION ALL
of two GROUP BYs. This avoids two separate tables and lets dashboard queries
filter by granularity with a simple WHERE.

**0-order customers in segmentation:** Used LEFT JOIN (with `quality_check_result`
filter in the ON clause, not WHERE) so customers with no PASSED orders appear
with `total_orders = 0` and are classified as `Inactive`. This is consistent with
the spec's Inactive definition.

**Revenue cross-check (FR-26):** Orchestrator computes `SUM(total_amount)` from
Silver PASSED orders and compares against `SUM(total_revenue)` from both
`gold_sales_by_product` and `gold_revenue_by_customer`. Tolerance set to $5.00
to accommodate cumulative ROUND(…,2) drift across up to 500 product rows or
10,000 customer rows (worst-case ±$0.005/row × 500 = $2.50).

**%run lesson applied:** Every `%run` cell in `create_gold_tables.py` is in its
own isolated cell, immediately after a separate label-comment cell — exactly the
two-cell pattern established during Bronze debugging (see `ai-prompts/bronze-layer.md`).

### Aggregation math spot-check (FR-26)
| Check | Formula | Expected |
|-------|---------|---------|
| Product total rows | distinct products in PASSED orders | ≤ 500 |
| Customer total rows | PASSED customer count | ≈ 9,850–9,900 (excl. duplicate/NULL) |
| Daily trends rows | distinct order_dates in PASSED orders | ≈ 365 |
| Weekly trends rows | distinct ISO weeks in PASSED orders | ≈ 52 |
| Revenue conservation | gold_sales_by_product SUM ≈ Silver PASSED SUM | within $5.00 |
| Revenue conservation | gold_revenue_by_customer SUM ≈ Silver PASSED SUM | within $5.00 |

**Evaluation:** Accepted — pending Databricks run verification.
