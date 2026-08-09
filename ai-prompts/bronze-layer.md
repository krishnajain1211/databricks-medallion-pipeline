# AI Prompts — Bronze Layer

> Prompt history for all exchanges related to Bronze ingestion scripts
> (`01_ingest_customers.py`, `02_ingest_orders.py`, `03_ingest_products.py`,
> `ingest_all.py`), `database/schema.sql` (Bronze tables), and
> `database/setup-notes.md`. Entries are added after each significant exchange.
> Format: see Section 5 of `requirements-analysis.md` for the standard entry template.

---

## Prompt 1: Implement all four Bronze layer scripts and Bronze schema DDL

**PROMPT SENT:**
"Phase 2, Bronze layer. Read requirements-analysis.md FR-07 through FR-12 and
A-14 before starting. Implement src/bronze/01_ingest_customers.py,
02_ingest_orders.py, 03_ingest_products.py, and ingest_all.py per those FRs —
read from /Volumes/workspace/ecommerce_medallion/raw_data/, write to Bronze
Delta tables in workspace.ecommerce_medallion, log ingestion metadata (row count,
source path, timestamp). Ask if anything's ambiguous rather than assuming."

**AI RESPONSE SUMMARY:**
Before writing code, Cursor asked three design questions via structured UI prompt:
(1) Databricks notebook format vs plain Python; (2) write mode for bronze tables;
(3) ingestion log persistence. All three answered, then implemented:

- **01_ingest_customers.py, 02_ingest_orders.py, 03_ingest_products.py:**
  Databricks notebook format (`# Databricks notebook source`, `# COMMAND ----------`
  cell separators). Each file follows identical 6-cell structure:
  Config constants → Imports → Explicit StructType schema → Read CSV →
  Write Delta (overwrite + overwriteSchema) → Count from table → Append to log →
  Assert expected row count + print confirmation.
  Key choices: `BASE_VOLUME_PATH` constant at top of every file (A-14);
  all columns nullable to preserve seeded defects unchanged (FR-11);
  `payment_date` nullable by design with a comment explaining why (A-18);
  `total_amount` uses `DecimalType(12, 2)` vs `DecimalType(10, 2)` for others
  (larger potential values from quantity × price).

- **ingest_all.py:**
  Uses `# MAGIC %run ./03_ingest_products` pattern for each sub-notebook.
  Run order: products first (smallest, reference table), then customers, then orders.
  Captures `run_start` timestamp before first `%run`, queries `bronze_ingestion_log`
  filtered to `ingestion_timestamp >= run_start` for a clean per-run summary.
  Uses `display(summary_df)` for notebook table visualization.

- **database/schema.sql — Bronze section:**
  Added four `CREATE TABLE IF NOT EXISTS ... USING DELTA` statements with column
  comments (notably `payment_date -- nullable: Pending orders have no payment date`)
  and table-level `COMMENT` strings. Matches the exact StructType schemas in the
  ingest scripts.

**YOUR EVALUATION:**
All four open questions confirmed and resolved. See Prompt 2 for the applied changes.

**FINAL DECISION:** Accepted with four clarifications applied (see Prompt 2).

---

## Prompt 2: Apply four Bronze-layer clarifications

**PROMPT SENT:**
"Answers to the four open Bronze-layer questions:
1. %run format — Confirmed correct. No change needed.
2. Timestamp buffer — Yes, add it, but use a 10 second buffer (run_start - 10 seconds).
3. DecimalType(12,2) for total_amount — Keep it, but add a one-line inline comment
   explaining why it differs from the other price fields.
4. database/setup-notes.md — Fill it in now, including the actual CREATE SCHEMA /
   CREATE VOLUME commands we ran manually in the Databricks UI, plus a note that
   these were created via the UI with the equivalent SQL included for reproducibility."

**AI RESPONSE SUMMARY:**
Three targeted edits applied:

1. **`%run` format (no change):** Confirmed standard syntax. No edit made.

2. **`src/bronze/ingest_all.py` — 10-second buffer:**
   - Added `timedelta` to imports alongside `datetime`.
   - Introduced `_filter_from = (run_start - timedelta(seconds=10)).strftime(...)`.
   - Updated the summary query's WHERE clause to use `_filter_from`.
   - Added a comment explaining the rationale: serverless cold-start clock skew
     can cause the cluster's wall clock to lag the driver's `datetime.now()` by
     a few seconds at startup.

3. **`src/bronze/02_ingest_orders.py` — DecimalType(12,2) comment:**
   - Added inline comment: `# wider than other price fields: computed total (qty × price) can exceed 9,999.99`
   - Decision is now explicitly documented as intentional, not an inconsistency.

4. **`database/setup-notes.md` — fully filled in:**
   - Added note that Steps 1 (CREATE SCHEMA) and 2 (CREATE VOLUME) were executed
     via the Databricks UI, not SQL, during initial environment configuration.
   - Equivalent SQL included under each step for reproducibility.
   - Added Step 5 (verify setup with `read_files()` row-count checks).
   - Added Step 6 (pipeline run order table: Bronze → Silver → Gold → Dashboard).
   - Upload instructions provided for both UI and Databricks CLI (Option A/B).

**YOUR EVALUATION:** _Pending final review of applied changes._

**FINAL DECISION:** _Pending._
