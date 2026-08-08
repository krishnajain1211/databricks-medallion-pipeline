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

**Result:** _[To be filled in after Phase 0 completes.]_

---

## Phase 1 — Data Generation

**Task to be sent to Cursor:**
> "Implement `src/data_generation/generate_sample_data.py`. Requirements: [paste
> FR-01 through FR-06 and FR-04a, FR-04b, FR-05a through FR-05d from
> requirements-analysis.md]. Use pandas + faker. Seed exactly 700 defects across
> 13 categories with no cross-category row overlap. After generating, run a
> verification pass that prints the count for each of the 13 defect categories —
> all must match the expected values in the Phase 1 verification table."

**Expected output:** Working `generate_sample_data.py`; three CSVs committed to `data/`;
verification output confirming all 13 defect counts; `DATA_GENERATION_NOTES.md` filled in.

**Result:** _[To be filled in after Phase 1 completes.]_

---

## Phase 2 — Bronze Layer

**Task to be sent to Cursor:**
> "Implement the three Bronze ingest scripts and `ingest_all.py`. Requirements: [paste
> FR-07 through FR-12]. Use Unity Catalog Volume path `/Volumes/workspace/ecommerce_medallion/raw_data/`
> as `BASE_VOLUME_PATH` constant. Explicit schema (no inference). Write to
> `workspace.ecommerce_medallion.bronze_*` tables. Log row count, source path, and
> timestamp to `bronze_ingestion_log`. Assert exact row counts (10000, 100000, 500)."

**Expected output:** Four working scripts; Bronze Delta tables in Databricks; ingestion log
populated; `database/schema.sql` Bronze section complete.

**Result:** _[To be filled in after Phase 2 completes.]_

---

## Phase 3 — Silver Layer

**Task to be sent to Cursor:**
> "Implement all five Silver quality check scripts and `create_silver_tables.py`.
> Requirements: [paste FR-13 through FR-20 and Silver check specifications from spec.md].
> Never delete rows — stamp `quality_check_result` only. Multi-failure rows get
> comma-delimited codes. Add schema contract validation step before checks run.
> Produce quality metrics report as a Delta table showing % passed per check."

**Expected output:** Five check scripts + orchestrator; Silver Delta tables in Databricks
with `quality_check_result` populated; quality metrics Delta table; `data-quality-strategy.md`
filled in; quality report showing numbers traceable to the 700 seeded defects.

**Result:** _[To be filled in after Phase 3 completes.]_

---

## Phase 4 — Gold Layer

**Task to be sent to Cursor:**
> "Implement all four Gold SQL scripts and `create_gold_tables.py`. Requirements:
> [paste FR-21 through FR-26 and Gold table specs from spec.md]. Source only rows
> where `quality_check_result = 'PASSED'`. For customer segmentation, define thresholds
> based on the actual data distribution (query silver_orders first to see revenue
> percentiles before writing the segmentation logic)."

**Expected output:** Four Gold Delta tables; spot-check of at least one product's
`total_revenue` against Silver source rows confirms math is correct.

**Result:** _[To be filled in after Phase 4 completes.]_

---

## Phase 5 — Dashboard

**Task to be sent to Cursor:**
> "Write `dashboard_queries.sql` with 4 queries: top-10 products bar chart,
> customer revenue histogram, customer segmentation pie chart, and quality metrics
> pass-rate bar chart (P-04). Each query must be standalone (not dependent on
> previous result sets). Write `DASHBOARD_GUIDE.md` with step-by-step instructions
> to recreate the dashboard in Databricks SQL."

**Expected output:** `dashboard_queries.sql` with 4 working queries; `DASHBOARD_GUIDE.md`
with enough detail that someone else can recreate the dashboard.

**Result:** _[To be filled in after Phase 5 completes.]_

---

## Phase 6 — Testing

**Task to be sent to Cursor:**
> "Implement `tests/test_data_quality.py` and `tests/test_transformations.py` as
> described in the placeholder docstrings already in those files. Each test function
> must print: check name, expected count, found count, PASS/FAIL. All 13 seeded
> defect categories must have a corresponding test assertion."

**Expected output:** `pytest tests/ -v` runs clean locally with all tests passing and
explicit expected-vs-found output per check.

**Result:** _[To be filled in after Phase 6 completes.]_

---

## Phase 7 — Lifecycle Artifacts

**Task to be sent to Cursor:**
> "Help draft `tool-workflow.md`, `reflection.md`, and `final-ai-usage-summary.md`
> based on the actual work done across Phases 0–6. For each, provide a draft that
> I will review and edit. Do not fabricate experiences — base all content on the
> actual exchanges logged in ai-prompts/*.md."

**Expected output:** Draft versions of all three artifacts for review and personalisation.

**Result:** _[To be filled in after Phase 7 completes.]_
