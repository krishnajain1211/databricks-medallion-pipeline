# Reflection

> Honest assessment of the AI-assisted data engineering workflow used in this project.

---

## What I Built

A production-quality Bronze → Silver → Gold → Dashboard data pipeline for an
e-commerce sales use case, running on Databricks Free Edition with Unity Catalog.
Starting from three synthetic CSVs (10,000 customers, 100,000 orders, 500 products)
with 700 intentionally seeded data quality defects across 13 categories, the pipeline:

- **Bronze layer:** Raw ingestion into Delta tables via three ingest scripts plus an
  orchestrator, preserving all defects exactly as they arrived.
- **Silver layer:** Five quality checks stamping a `quality_check_result` column on
  every row — flagging bad rows, never deleting them — plus a quality metrics report
  and a Silver orchestrator that learned from a real Bronze bug before being written.
- **Gold layer:** Four aggregation tables (product revenue, customer revenue, daily/weekly
  trends, customer segmentation), built from PASSED rows only, with a built-in FR-26
  revenue cross-check that caught a real data scoping bug during development.
- **Dashboard:** Five Databricks SQL Dashboard tiles including three required
  visualisations plus a bonus quality pass-rate tile and a daily revenue trend chart.
- **Tests:** 21 local pandas unit tests (all passing in <1s) and a Databricks integration
  notebook covering 7 layer-level invariants against the live Delta tables.

---

## How I Used AI (Across the Lifecycle)

AI (Cursor) was used at every stage, but the role varied:

| Stage | AI role | Human role |
|---|---|---|
| Planning | Generated full requirements analysis, gap log, assumptions list | Reviewed, corrected gap math, added constraints, locked the plan |
| Scaffold | Created all empty files and folder structure | Approved structure, caught a catalog-name inconsistency in the scaffold |
| Data generation | Implemented `generate_sample_data.py` with all 13 defect categories | Verified output counts, caught the skipped-Phase-1 gap |
| Bronze | Implemented all four notebook files, schema DDL, setup notes | Confirmed run format, added 10s timestamp buffer, caught the silent %run failure |
| Silver | Implemented five quality check scripts + orchestrator | Verified against real Databricks output; all counts matched on first run |
| Gold | Implemented four SQL notebooks + Python orchestrator with FR-26 cross-check | Cross-check caught a real scoping bug ($635K revenue gap); instructed the fix |
| Dashboard | Wrote all five queries with chart config comments; wrote DASHBOARD_GUIDE.md | Created tiles in Databricks, hit three real UI bugs, confirmed final layout |
| Tests | Implemented 21 pandas tests + Databricks integration notebook | Caught two bugs in the integration test (wrong type handling, wrong expected range) |
| Artifacts | Writing debugging-notes.md, reflection.md, final-ai-usage-summary.md | Providing the real history including bugs not in the prompt log |

---

## What AI Helped With Most

**Boilerplate at scale without drift.** The pipeline has ~15 files across Bronze, Silver,
and Gold, each following a consistent pattern (Databricks notebook format, explicit
StructType schemas, `quality_check_result` stamping, docstring headers). Writing all of
these by hand would have introduced naming inconsistencies and structural drift. AI kept
the pattern consistent across every file without being explicitly reminded each time.

**Building in the right safety checks.** The FR-26 revenue cross-check in
`create_gold_tables.py` was suggested as part of the Gold implementation (it was in the
spec as FR-26 but the AI chose to implement it as an `AssertionError`-raising cell rather
than a passive print). That cross-check caught Bug 4 — the $635K revenue gap — within
minutes of the first Gold run. Without it, the gap would likely not have been noticed
until a reviewer questioned the customer revenue figures.

**Translating requirements to code correctly.** A-09 (all copies of duplicate keys
flagged, not just the second occurrence), A-11 (NULL FKs excluded from referential
integrity check), and A-13 (total_amount mismatch only checked when qty > 0 AND price > 0)
are subtle non-obvious constraints. The Silver layer implemented all three correctly
on the first run without needing a debugging round, because the AI read the assumptions
before writing the code.

---

## What AI Got Wrong

**The Gold customer filter (Bug 4, G-08).** The initial `02_revenue_by_customer.sql`
filtered `WHERE c.quality_check_result = 'PASSED'` on the customer dimension, which is
semantically wrong in a flagging-not-deleting pipeline. A customer with a bad email
address is still a real customer with real transactions. The AI applied a pattern that
makes sense for order tables (filter to PASSED rows before aggregating) but should not
have been applied to the dimension table. It required a real cross-check failure and
a prompt correcting the mental model before the fix was applied.

**The $5,000 High-Value segmentation threshold.** The initial threshold was chosen as
"above the approximate $5,500 average", expecting roughly half of customers to be
High-Value. When the actual dashboard pie chart ran, the distribution was more skewed
than expected — the High-Value slice dominated. The threshold works as a demonstration
but is not a defensible business rule. In a real project this would need to be calibrated
against actual percentile data from `gold_revenue_by_customer` before publishing.

**The integration test expected values (Bug 9).** The `gold_daily_weekly_trends` expected
range of `300–800` was estimated from "one year ≈ 365 days" without checking the real
Phase 4 output. The actual count is 1,923 (spanning 2022–2026 with both daily and weekly
rows). The AI wrote the test without consulting the verified artifact already in the
prompt log. This is a process failure: AI should have referenced `ai-prompts/gold-layer.md`
before writing Section 6 of the integration test.

**The `_check()` Decimal handling (Bug 8).** The integration test helper used
`isinstance(x, (int, float))` as a numeric guard, which silently fails for
`decimal.Decimal` values returned by Spark. This is a Python type system edge case that
the AI did not anticipate. It was caught immediately on the first test run.

---

## How I Validated AI Output

Every piece of AI-generated code was verified against real infrastructure or real data
before being accepted:

- **Data generation:** Defect verification table confirmed all 13 categories × exact
  count before Bronze was started.
- **Bronze:** `SHOW TABLES` after first run (which showed nothing — that's how Bug 2
  was discovered). Re-run after fix confirmed all three tables populated.
- **Silver:** Row counts (10,000 customers, 100,000 orders — no deletion), quality
  metrics table checked against expected per-check failure counts, spot-checks on
  raw Silver rows to confirm real NULL/orphan values on flagged rows.
- **Gold:** FR-26 revenue cross-check built into the orchestrator. Both totals matched
  after Bug 4 was fixed.
- **Dashboard:** Each tile manually verified by viewing the live Databricks dashboard,
  including checking category labels (caught the incorrect "Home" category in the
  initial tile description) and bin counts in the histogram.
- **Tests:** `pytest tests/ -v` run locally against real CSVs — 21/21 passed. Integration
  notebook run in Databricks — ALL PASSED after two fix iterations.

The discipline of running code and checking output before accepting AI output was the
single most effective quality gate across the project.

---

## What I Would Improve Next

**Define the High-Value threshold from data, not intuition.** Before finalising
`04_customer_segmentation.sql`, run a percentile query on `gold_revenue_by_customer`
to find p75 or p80 of `total_revenue`, and use that as the threshold. A data-derived
threshold is auditable; a round number is not.

**Add schema evolution guards.** The Bronze ingest scripts use `overwriteSchema=true`,
which means a column rename in a CSV header would silently propagate to Bronze and then
break the Silver quality checks downstream with no error. A schema comparison step
(expected columns vs. actual CSV headers) before writing to Bronze would prevent this.

**Automate the Tier 2 integration test as a scheduled job.** Currently the integration
notebook is run manually. Scheduling it as a Databricks job after each pipeline run
would catch regressions automatically and produce a timestamped pass/fail record.

**Consolidate the Gold cross-check and integration test into one notebook.** The FR-26
revenue check in `create_gold_tables.py` and the equivalent check in
`integration_test_silver_gold.py` are separate but redundant. Ideally the orchestrator's
smoke check would be the integration test's source of truth, not a parallel
reimplementation.

---

## Reusable Workflow

The pattern that worked well and is worth keeping for real production pipelines:

1. **Lock a requirements document before writing code.** `requirements-analysis.md` with
   gap analysis, assumptions, and an acceptance criteria checklist prevented scope drift
   at every phase. When a new ambiguity appeared (G-08), it was added to the gap log
   rather than silently resolved in code.

2. **Log AI prompt history as a first-class deliverable.** Maintaining `ai-prompts/*.md`
   entries throughout the project created an auditable record of every design decision,
   including the ones that were corrected. In a real review, this is more valuable than
   the code itself.

3. **Build cross-checks into orchestrators, not as afterthoughts.** The FR-26 revenue
   check was part of the Gold orchestrator's design. It caught a real bug on the first
   run. Any pipeline that moves data between layers should include an invariant check
   (row count conservation, revenue conservation, referential completeness) as a
   first-class output cell.

4. **Use the two-tier testing model.** Local pandas tests (fast, CI-friendly, no cloud
   dependency) for logic correctness; Databricks integration tests for infrastructure
   correctness. Neither tier replaces the other. The pandas tests caught zero runtime
   bugs (the code logic was correct) but provide a regression safety net for future
   changes. The integration tests caught two test-authoring bugs.

5. **Prefer notebook-format source files for Databricks pipelines.** Using
   `# Databricks notebook source` format throughout means every file is both a runnable
   Databricks notebook and a reviewable Python file in git. The tradeoff is the `%run`
   placement rule, but that rule is learnable and documentable.
