# Design Notes

> Architecture overview, layer-by-layer design decisions, and debugging approach.
> Decisions below are locked — see `requirements-analysis.md` for the full gap log
> and assumption list that produced them.

---

## Architecture Overview

```
Unity Catalog Volume
/Volumes/workspace/ecommerce_medallion/raw_data/
        │  customers.csv · orders.csv · products.csv
        │
        ▼  Bronze (raw ingest)
workspace.ecommerce_medallion.bronze_*
        │  Faithful copy — zero transformation
        │  Every source row preserved exactly as received
        │
        ▼  Silver (quality gate)
workspace.ecommerce_medallion.silver_*
        │  All rows kept — bad rows flagged, never deleted
        │  quality_check_result column stamped on every row
        │  silver_quality_metrics: pass rate per check
        │
        ▼  Gold (business aggregations)
workspace.ecommerce_medallion.gold_*
        │  Sourced from PASSED rows only (+ customer deduplication)
        │  Four analyst-facing tables
        │
        ▼  Databricks SQL Dashboard
        Five tiles sourced from Gold and Silver metrics tables
```

**Catalog / schema / volume:** All objects live in `workspace.ecommerce_medallion`.
Raw data is stored in the Unity Catalog Volume `raw_data` rather than DBFS, which is
the recommended pattern for Databricks Free Edition (serverless).

---

## Data Model & Schema

Three source tables with intentional FK relationships:

- `customers` (10,000 rows) — dimension table; `customer_id` PK
- `orders` (100,000 rows) — fact table; `order_id` PK, `customer_id` FK, `product_id` FK
- `products` (500 rows) — dimension table; `product_id` PK

Full field-level data dictionary and Unity Catalog naming table in `data-model.md`.
Full CREATE TABLE DDL for all Bronze, Silver, and Gold tables in `database/schema.sql`.

---

## Bronze Layer Design

**Design goal:** Faithful raw ingestion — no filtering, no transformation, no judgment.

**Key decisions:**

- **Explicit StructType schemas** (not inferred) — prevents schema drift if a CSV
  header changes silently. All columns declared nullable to preserve seeded defects
  exactly as they arrive.
- **Write mode: overwrite + overwriteSchema** — each Bronze run is a full reload.
  Appropriate for a batch pipeline where source CSVs are replaced, not appended.
- **Ingestion metadata log (`bronze_ingestion_log`)** — each run appends a row with
  source path, row count, and timestamp. Enables per-run auditability without touching
  the Bronze tables themselves.
- **`total_amount` uses `DecimalType(12, 2)`** (wider than the `DecimalType(10, 2)` used
  for `unit_price`) — computed totals from quantity × price can exceed 9,999.99; the
  wider type is a defensive margin, documented as an intentional choice.
- **Unity Catalog Volume path as a constant** (`BASE_VOLUME_PATH`) at the top of each
  ingest script — one place to update if the environment changes.
- **Run order in orchestrator:** products first (smallest, reference table), then
  customers, then orders (largest; FK-dependent on the other two).

**Databricks notebook format:** All Bronze scripts use `# Databricks notebook source`
format, enabling them to run as notebooks in Databricks and be reviewed as Python files
in git. Critical rule: `# MAGIC %run` must be the **first content line** of its cell —
any preceding comment or blank line silently disables magic execution (see Bug 2 in
`debugging-notes.md`).

---

## Silver Layer Design

**Design goal:** Trust and governance — flag every quality issue without losing any data.

**Core rule (FR-18, Assumption A-10):** Bad rows are **never deleted**. Every row in
`silver_customers` and `silver_orders` receives a `quality_check_result` column:
- `PASSED` — passed all applicable checks
- `FAILED_<CHECK_NAME>` — failed one check
- `FAILED_X,FAILED_Y` — comma-delimited when a row fails multiple checks

**Fail-ID DataFrame pattern:**
Each of the five check scripts (`01_` through `05_`) reads Bronze tables, identifies
which primary key values fail its specific check, and exposes:
- `{check}_fail_customers` — DataFrame[customer_id] of failing IDs
- `{check}_fail_orders` — DataFrame[order_id] of failing IDs
- `{check}_n_*_failed` — integer count

The orchestrator (`create_silver_tables.py`) left-joins all five fail-ID DataFrames back
to Bronze on PK, builds boolean flag columns, then derives `quality_check_result` using
`concat_ws` + `when`. This means a row with two failures gets both codes recorded.

**Check scope and edge cases:**
- **Completeness:** Flags NULL in `email` (customers) and NULL `customer_id`/`product_id`
  (orders). NULL `payment_date` is deliberately excluded — it is valid for Pending/Cancelled
  orders (Assumption A-18).
- **Uniqueness:** Flags ALL copies of a duplicate key, not just the second occurrence
  (Assumption A-09). Both rows of a duplicate pair receive `FAILED_UNIQUENESS`.
- **Type Validation:** Flags malformed email (regex), future `signup_date`, zero/negative
  `quantity`, negative `unit_price`.
- **Referential Integrity:** Pre-filters `isNotNull()` before the anti-join so NULL FKs
  are not double-counted (they are a Completeness failure, not a Referential Integrity
  failure — Assumption A-11).
- **Business Logic:** Checks `total_amount ≈ quantity × unit_price` (tolerance 0.01)
  only when `qty > 0 AND price > 0`, excluding rows already flagged for invalid
  numerics (Assumption A-13). Also checks `payment_date < order_date`.

**Quality metrics report:** Produced by the orchestrator and written to
`workspace.ecommerce_medallion.silver_quality_metrics`. Dashboard Tile 4 sources from it.

---

## Gold Layer Design

**Design goal:** Business-ready aggregations for analysts and dashboards.

**Source filter:** All four Gold tables source from `quality_check_result = 'PASSED'` rows
in Silver — with one deliberate exception (see G-08 below).

**Four aggregation tables:**

| Table | Grain | Key design choice |
|---|---|---|
| `gold_sales_by_product` | One row per product | INNER JOIN to `bronze_products` for product metadata; revenue and order count aggregated from PASSED orders |
| `gold_revenue_by_customer` | One row per unique customer | Customer dimension deduplicated by `ROW_NUMBER()` CTE (G-08 fix); includes ALL unique customers; orders filtered to PASSED |
| `gold_daily_weekly_trends` | One row per day or ISO week | Single table with `period_type` column (`'daily'`/`'weekly'`) using UNION ALL — avoids two separate tables |
| `gold_customer_segmentation` | One row per segment (4 rows total) | High-Value threshold: `total_revenue > 5,000`; Inactive = 0 PASSED orders via LEFT JOIN |

**G-08 — Customer dimension filter bug and fix:**
The initial implementation filtered `WHERE silver_customers.quality_check_result = 'PASSED'`
before joining to orders. This excluded ~120 customers whose *records* had defects (bad
email, duplicate ID) even though their *orders* were fully valid PASSED transactions —
producing a $635,295.88 revenue shortfall in `gold_revenue_by_customer`. Fix: replaced
the WHERE clause with a `ROW_NUMBER() OVER (PARTITION BY customer_id)` CTE that
deduplicates on `customer_id` and includes all unique customers regardless of their
record-level quality result. Full details in `requirements-analysis.md` Gap G-08 and
`ai-prompts/gold-layer.md` Debugging Entry 1.

**FR-26 revenue cross-check:** Built into `create_gold_tables.py` as an
`AssertionError`-raising cell. Compares `SUM(total_amount)` from Silver PASSED orders
against `SUM(total_revenue)` from both `gold_sales_by_product` and
`gold_revenue_by_customer`. Tolerance: $5.00 (accommodates cumulative ROUND(…,2) drift).
This cross-check caught the G-08 bug on the first Gold run.

---

## Data Quality Validation Strategy

See `data-quality-strategy.md` for the full strategy with verified metrics.

**Summary:** Five checks implemented in the Silver layer; four are required by the spec
(Completeness, Uniqueness, Type Validation, Referential Integrity); one is additive
(Business Logic). Combined pass rates exceed 99.6% for all checks against the 700-row
seeded defect set. Defect categories were designed with non-overlapping row index ranges
so each check has clean, unambiguous true-positive test cases.

---

## Debugging Approach

See `debugging-notes.md` for the full chronological bug log (9 entries).

**Methodology:**
1. Run the pipeline (or test) on real infrastructure before accepting any implementation.
2. When a failure occurs, document: symptom first, then root cause, then fix, then lesson.
3. Log the lesson in the relevant `ai-prompts/*.md` file immediately.
4. Reference that log entry at the start of the next phase's prompt ("check
   `ai-prompts/bronze-layer.md` before writing this orchestrator").

This produced measurable results: the Bronze `%run` silent failure was logged in Phase 2
and the lesson propagated to Silver, Gold, and the integration test notebook on first
write — none of those files required a `%run` debugging round.
