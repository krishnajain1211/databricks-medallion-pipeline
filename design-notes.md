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

---

## Production Orchestration Design

This section describes how the pipeline would run as a scheduled production job using
Databricks Jobs/Workflows rather than being triggered manually.

### Job DAG structure

A single Databricks Job would contain four tasks with explicit `depends_on` edges:

```
[1. Bronze ingest]
        │ on success
        ▼
[2. Silver quality checks]
        │ on success
        ▼
[3. Gold aggregations + FR-26 cross-check]
        │ on success
        ▼
[4. Dashboard refresh (SQL Warehouse query cache invalidation)]
```

Silver never starts unless Bronze exits successfully; Gold never starts unless Silver
exits successfully. Databricks Jobs enforces this natively via task dependencies — no
custom orchestration logic is needed. The FR-26 `AssertionError` in
`create_gold_tables.py` already causes Task 3 to fail loudly if revenue conservation
breaks, which blocks Task 4 automatically. Wrong dashboard numbers are never silently
published.

### Schedule

A daily cron schedule attached to the Job — e.g., `0 3 * * *` (03:00 UTC) — gives the
pipeline a nightly run after the previous day's orders have closed. The schedule is
configured on the Job, not on any individual notebook, so a single toggle pauses the
entire pipeline.

### Failure handling

- **Task retries:** Each task configured with 1–2 automatic retries and an exponential
  backoff (e.g., 5 min, then 15 min). Handles transient serverless cold-start failures
  or momentary Volume unavailability without paging anyone.
- **Alerting:** Job-level email/webhook alert fires on any task failure after retries
  are exhausted. The alert goes to the data engineering team, not just the job owner.
- **`bronze_ingestion_log` as the first failure signal:** The Bronze task writes a row to
  `bronze_ingestion_log` with row count and timestamp before exiting. A downstream
  monitoring query can detect a missing log entry (Bronze didn't run) or a row-count
  anomaly (source data truncated) independently of whether the task itself raised an
  error — this matters for partial-write failures that don't throw an exception.
- **FR-26 as the Gold-layer gate:** The revenue cross-check `AssertionError` in
  `create_gold_tables.py` is not just an assessment artifact — it is exactly what a
  scheduled job's Task 3 relies on to decide whether that day's Gold tables are trusted.
  If the cross-check fails, Task 3 fails, Task 4 (dashboard refresh) never runs, and the
  alert fires. Analysts see yesterday's numbers rather than corrupted ones. This is the
  correct failure mode.

### What would need to change from the current design

**Bronze: overwrite → append/merge keyed on ingestion date.**
The current `overwrite + overwriteSchema` mode is correct for a one-time seed load but
wrong for incremental production data. In production, new daily order files would be
merged into Bronze using `MERGE INTO ... ON (order_id)` for fact tables, or
`INSERT INTO` with a date partition for append-only patterns. The explicit StructType
schema in each ingest script already makes this change low-risk — the schema is locked,
not inferred.

**Data source: static Volume files → event-driven or scheduled delivery.**
Rather than manually uploaded CSVs, production would receive daily files from an upstream
system (e.g., an S3 prefix with a `YYYY-MM-DD` date partition, or a Kafka topic consumed
via Auto Loader). The `BASE_VOLUME_PATH` constant in each Bronze script is the single
change point — the rest of the ingest logic stays identical.

**Idempotency for safe retries.**
Silver and Gold already write with `overwrite` mode, so re-running them after a partial
failure produces the same output — they are idempotent by design. Bronze needs the
append/merge change above to become idempotent (i.e., re-ingesting the same date's file
must not duplicate rows). With a `MERGE ON order_id` pattern, re-running Bronze is safe.

### Tests as production gates

The two-tier test suite built for this assessment maps directly onto production job tasks:

- **Tier 1 (pandas/pytest):** Runs in CI on every pull request that changes Silver logic
  or Gold SQL. No Databricks connection required — fast feedback before any code lands.
- **Tier 2 (`integration_test_silver_gold.py`):** Promoted to a Job task that runs after
  Gold completes each night, writing pass/fail results to a `pipeline_run_log` Delta
  table. A monitoring dashboard reads this table and flags any day where the integration
  test did not produce `ALL PASSED`.

The FR-26 revenue cross-check and the Silver row-count conservation assertion are the
canonical checks a data team would trust to gate whether a daily pipeline run is valid.
They were built into the orchestrators from the start — not bolted on after the fact.
