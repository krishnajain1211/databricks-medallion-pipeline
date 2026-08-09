# Task Breakdown — Tasks as Defined to Cursor

> Documents how each build phase was broken into specific tasks sent to Cursor,
> and what was expected from each. Updated as phases complete.

---

## Phase 0 — Foundation & Scaffolding

**Task sent to Cursor:**
> "Scaffold the complete repository structure exactly as specified in Section 4 of
> requirements-analysis.md. All root-level .md files as stubs with a heading and
> placeholder. src/ tree as empty placeholder .py/.sql files with header comments
> from the FR items. tool-specific/cursor-workflow/ files with real, specific content
> based on our actual project setup (catalog=workspace, schema=ecommerce_medallion,
> volume=raw_data). Do not write any pipeline logic yet — structure only."

**Expected output:** Every file in the Section 4 repo tree created; tool-specific
files with real content; no implementation code anywhere.

**Result:** Complete. All 47 files and folders in the Section 4 scaffold created.
Tool-specific files (`project-context.md`, `spec.md`, `task-breakdown.md`,
`cursor-rules-or-instructions.md`) filled with real project-specific content.
Root-level `.md` files scaffolded as stubs. Catalog-name inconsistency ("main" vs
"workspace") caught and corrected in `requirements-analysis.md` and `data-model.md`
as part of this phase.

**Task to be sent to Cursor:**
> "Implement `src/data_generation/generate_sample_data.py`. Requirements: [paste
> FR-01 through FR-06 and FR-04a, FR-04b, FR-05a through FR-05d from
> requirements-analysis.md]. Use pandas + faker. Seed exactly 700 defects across
> 13 categories with no cross-category row overlap. After generating, run a
> verification pass that prints the count for each of the 13 defect categories —
> all must match the expected values in the Phase 1 verification table."

**Expected output:** Working `generate_sample_data.py`; three CSVs committed to `data/`;
verification output confirming all 13 defect counts; `DATA_GENERATION_NOTES.md` filled in.

**Result:** Complete. `generate_sample_data.py` implemented (~490 lines, SEED=42).
All 700 seeded defects across 13 categories verified by automated verification table
(actual == expected for every category). `DATA_GENERATION_NOTES.md` written with
13 sections. One bug fixed during run: `UnicodeEncodeError` on Windows cp1252 console
— fixed by replacing Unicode characters with ASCII equivalents.

**Task to be sent to Cursor:**
> "Implement the three Bronze ingest scripts and `ingest_all.py`. Requirements: [paste
> FR-07 through FR-12]. Use Unity Catalog Volume path `/Volumes/workspace/ecommerce_medallion/raw_data/`
> as `BASE_VOLUME_PATH` constant. Explicit schema (no inference). Write to
> `workspace.ecommerce_medallion.bronze_*` tables. Log row count, source path, and
> timestamp to `bronze_ingestion_log`. Assert exact row counts (10000, 100000, 500)."

**Expected output:** Four working scripts; Bronze Delta tables in Databricks; ingestion log
populated; `database/schema.sql` Bronze section complete.

**Result:** Complete. Four Bronze scripts implemented and running.
Bronze Delta tables populated (10,000 / 100,000 / 500 rows). Ingestion log table
populated per run. One critical bug discovered and fixed: `%run` silent failure
(label comment before `# MAGIC` in same cell silently disabled magic execution).
Fix: split label comments and `%run` directives into separate cells.
`database/schema.sql` Bronze DDL complete. `database/setup-notes.md` filled in
with 6-step setup guide.

**Task to be sent to Cursor:**
> "Implement all five Silver quality check scripts and `create_silver_tables.py`.
> Requirements: [paste FR-13 through FR-20 and Silver check specifications from spec.md].
> Never delete rows — stamp `quality_check_result` only. Multi-failure rows get
> comma-delimited codes. Add schema contract validation step before checks run.
> Produce quality metrics report as a Delta table showing % passed per check."

**Expected output:** Five check scripts + orchestrator; Silver Delta tables in Databricks
with `quality_check_result` populated; quality metrics Delta table; `data-quality-strategy.md`
filled in; quality report showing numbers traceable to the 700 seeded defects.

**Result:** Complete. Five quality check scripts + orchestrator implemented.
Silver Delta tables populated: 10,000 customers, 100,000 orders — no rows deleted.
`quality_check_result` stamped on every row. Quality metrics report produced.
Per-check failure counts confirmed against the 700-defect spec. `%run` bug fix from
Phase 2 applied proactively to `create_silver_tables.py` — no recurrence.
`data-quality-strategy.md` filled in with confirmed metrics.

**Task to be sent to Cursor:**
> "Implement all four Gold SQL scripts and `create_gold_tables.py`. Requirements:
> [paste FR-21 through FR-26 and Gold table specs from spec.md]. Source only rows
> where `quality_check_result = 'PASSED'`. For customer segmentation, define thresholds
> based on the actual data distribution (query silver_orders first to see revenue
> percentiles before writing the segmentation logic)."

**Expected output:** Four Gold Delta tables; spot-check of at least one product's
`total_revenue` against Silver source rows confirms math is correct.

**Result:** Complete. Four Gold Delta tables produced. FR-26 revenue cross-check
revealed a $635,295.88 revenue shortfall in `gold_revenue_by_customer` (G-08:
`WHERE quality_check_result = 'PASSED'` on the customer dimension wrongly excluded
~120 customers' orders). Fixed with `ROW_NUMBER()` CTE deduplication. After fix:
both cross-checks passed within $5.00 tolerance. `gold_daily_weekly_trends`: 1,923
rows (1,682 daily + 241 weekly). `gold_customer_segmentation`: 4 rows.

**Task to be sent to Cursor:**
> "Write `dashboard_queries.sql` with 4 queries: top-10 products bar chart,
> customer revenue histogram, customer segmentation pie chart, and quality metrics
> pass-rate bar chart (P-04). Each query must be standalone (not dependent on
> previous result sets). Write `DASHBOARD_GUIDE.md` with step-by-step instructions
> to recreate the dashboard in Databricks SQL."

**Expected output:** `dashboard_queries.sql` with 4 working queries; `DASHBOARD_GUIDE.md`
with enough detail that someone else can recreate the dashboard.

**Result:** Complete. Five tiles live in Databricks SQL Dashboard (3 required + 2 bonus).
Live URL confirmed. Three manual configuration bugs resolved during tile setup:
(1) Tile 5 dataset SQL mismatch causing wrong X-axis grain; (2) histogram axes
reversed — `total_revenue` on Y instead of X; (3) global `YEARLY(order_date)` filter
chip unexpectedly applied to all tiles. All resolved via dashboard editor configuration.
`DASHBOARD_GUIDE.md` updated with explicit axis configuration notes.

**Task to be sent to Cursor:**
> "Implement `tests/test_data_quality.py` and `tests/test_transformations.py` as
> described in the placeholder docstrings already in those files. Each test function
> must print: check name, expected count, found count, PASS/FAIL. All 13 seeded
> defect categories must have a corresponding test assertion."

**Expected output:** `pytest tests/ -v` runs clean locally with all tests passing and
explicit expected-vs-found output per check.

**Result:** Complete. 21/21 pytest tests pass locally (0.95s). Databricks integration
notebook: ALL PASSED after two test-code bug fixes — (1) `_check()` helper crashed
on `decimal.Decimal` from Spark; (2) `gold_daily_weekly_trends` expected range was
300–800 (estimated), corrected to exact 1,923. Pipeline data was correct throughout;
both bugs were in the test code, not the pipeline.

**Task to be sent to Cursor:**
> "Help draft `tool-workflow.md`, `reflection.md`, and `final-ai-usage-summary.md`
> based on the actual work done across Phases 0–6. For each, provide a draft that
> I will review and edit. Do not fabricate experiences — base all content on the
> actual exchanges logged in ai-prompts/*.md."

**Expected output:** Draft versions of all three artifacts for review and personalisation.

**Result:** Complete. `debugging-notes.md` (9 entries), `reflection.md` (all 7 sections),
`final-ai-usage-summary.md` (all sections), and `tool-workflow.md` (all 12 sections)
filled in with specific, sourced content. Pre-submission audit identified and resolved
8 remaining placeholder items across 6 files.
