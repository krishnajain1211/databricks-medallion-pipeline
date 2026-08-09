# Debugging Notes

> Chronological log of every meaningful bug encountered and resolved during development.
> One entry per issue. Format: date, phase, symptom, root cause, fix, lesson.
> Source: ai-prompts/*.md debugging entries + manual debugging sessions during Phases 1–6.

---

## Bug 1 — Phase 1 skipped, caught before Bronze ran on empty data

**Date:** 2026-08-09
**Phase:** Transition between Phase 1 (Data Generation) and Phase 2 (Bronze)

**Symptom:**
Phase 2 Bronze ingestion scripts were fully implemented and ready to run. On inspection,
`data/` contained only `.gitkeep` — no `customers.csv`, `orders.csv`, or `products.csv`
existed. The Bronze scripts would have read from a Unity Catalog Volume that contained
no files and silently produced empty Delta tables.

**Root cause:**
Phase 1 (data generation) was planned but never explicitly triggered during the build
sequence. The repository scaffold created `data/` as an empty directory with `.gitkeep`,
and no one prompted the `generate_sample_data.py` run before moving to Bronze. Because
the Bronze ingest scripts read from Unity Catalog Volumes (not directly from `data/`),
the missing CSVs would not have caused an obvious error — the scripts would simply have
returned 0 rows with no exception raised.

**Fix applied:**
Caught during a pre-run checklist review (FR-01 through FR-06 cross-check before Phase 2
started). Implemented and ran `generate_sample_data.py`, verified all 13 defect categories
× 700 total seeded rows against the spec, committed the three CSVs, then uploaded them to
the Unity Catalog Volume before any Bronze script touched the workspace.

**Lesson:**
Phase ordering in a build plan is not self-enforcing. A checklist or explicit
"outputs of previous phase must exist" guard before each phase starts would have
caught this at planning time. For Bronze specifically: the ingest scripts doing a
`COUNT(*)` smoke check at the end provides a safety net, but the count being 0 is
not the same as raising an error — always verify the source files exist first.

---

## Bug 2 — Bronze orchestrator: silent %run failure in ingest_all.py

**Date:** 2026-08-09
**Phase:** Phase 2 — Bronze Layer

**Symptom:**
`ingest_all.py` completed without raising any exceptions. `SHOW TABLES` in the
`ecommerce_medallion` schema returned empty — no Bronze Delta tables were created.
The orchestrator appeared to succeed but had done nothing.

**Root cause:**
In Databricks source-format `.py` notebooks, a cell is treated as a **magic cell**
(`%run`, `%sql`, etc.) only when the `# MAGIC` prefix is the **first content line**
after the `# COMMAND ----------` separator. The original `ingest_all.py` had label
comments before the `# MAGIC %run` directive inside the same cell:

```
# COMMAND ----------
# ── Step 1: Products ─────────────────
# MAGIC %run ./03_ingest_products   ← treated as a plain Python comment
```

Databricks fell back to plain IPython `%run`, which runs a `.py` file as a script
rather than executing a notebook. In that mode `spark` is not available, no Delta
writes occur, and no exception is raised — the failure is completely silent.

**Fix applied:**
Split each label comment and its `%run` into two separate cells, inserting an
additional `# COMMAND ----------` between them so that `# MAGIC %run` is guaranteed
to be the first content line of its own dedicated cell. The same two-cell pattern
was applied proactively to `create_silver_tables.py`, `create_gold_tables.py`, and
the integration test notebook to prevent recurrence.

**Lesson:**
Databricks magic cell recognition is positional — any content before `# MAGIC` in
the same cell, including blank lines and comments, silently disables it. Always verify
that tables actually exist after an orchestrator run, not just that the run produced
no error. `SHOW TABLES` or a `spark.catalog.tableExists()` check costs nothing and
catches this class of failure immediately.

---

## Bug 3 — Merge conflict when applying the Bronze %run fix

**Date:** 2026-08-09
**Phase:** Phase 2 — Bronze Layer (post-fix)

**Symptom:**
After splitting the Bronze `ingest_all.py` cells to fix Bug 2, a git merge conflict
appeared in `ingest_all.py` when the fix branch was rebased against the main working
branch. The conflict markers appeared inside the cell separator block, making the
notebook unparseable by Databricks until resolved.

**Root cause:**
Two edits had touched `ingest_all.py` in overlapping line regions: the original Phase 2
commit (which added the label comments + `%run` in a single cell) and the debugging
fix commit (which split them). Git's three-way merge could not automatically reconcile
the restructured cell layout because the added `# COMMAND ----------` lines caused the
line-number alignment to shift.

**Fix applied:**
Resolved manually by accepting the debug-fix version of the cell structure (two cells
per `%run`) and discarding the original single-cell layout. Verified the resolved file
rendered correctly in Databricks before recommitting.

**Lesson:**
Databricks notebook cell structure (specifically the `# COMMAND ----------` separators)
is semantically significant but looks like a comment to git's diff algorithm.
Refactoring cell boundaries will always produce conflicts when the same file has
parallel edits. Prefer smaller, focused commits that touch only the cells being
changed, and resolve cell-structure conflicts by reviewing Databricks semantics
rather than relying on automatic merge.

---

## Bug 4 — Gold: customer revenue $635,295.88 short of Silver PASSED total (G-08)

**Date:** 2026-08-09
**Phase:** Phase 4 — Gold Layer

**Symptom:**
FR-26 revenue cross-check in `create_gold_tables.py` failed:
`gold_revenue_by_customer` was **$635,295.88 short** of the Silver PASSED total,
while `gold_sales_by_product` matched exactly. The asymmetry pointed directly at
the customer join logic, not the data.

**Root cause:**
`02_revenue_by_customer.sql` filtered `WHERE c.quality_check_result = 'PASSED'` on
the customer dimension before joining to PASSED orders. This excluded approximately
120 customers whose *customer records* carried defect flags (NULL email, malformed
email, duplicate customer_id) — even though those customers' *orders* had passed all
order-level quality checks and were fully legitimate transactions. The missing revenue
was the total_amount of all PASSED orders belonging to those 120 customers.

`gold_sales_by_product` was unaffected because it aggregates by product and never
touches the customer table at all, which is why it matched exactly while the customer
aggregation did not. This diagnostic asymmetry made the root cause unambiguous.

Additionally, a naive fix of simply removing the WHERE clause would have caused
double-counted revenue for the 20 duplicate customer_id rows (C-02) — both copies
of each duplicate pair would have joined against the same orders.

**Fix applied:**
Replaced `WHERE c.quality_check_result = 'PASSED'` with a `ROW_NUMBER() OVER
(PARTITION BY customer_id ORDER BY customer_id)` CTE in both
`02_revenue_by_customer.sql` and `04_customer_segmentation.sql`:
- Includes all unique customer_ids regardless of their record-level quality flag.
- Collapses the 20 duplicate-ID rows (C-02) to one canonical row per `customer_id`.
- The order side of the join remains filtered to `quality_check_result = 'PASSED'`.

After the fix, both revenue cross-checks passed with diff < $0.01.

**Lesson:**
In a flagging-not-deleting Silver layer, `quality_check_result` on a dimension
record describes data quality issues with *that record* — it does not mean the
customer never existed or that their transactions are invalid. Filtering Gold
dimension tables by `quality_check_result = 'PASSED'` is the wrong predicate;
the correct predicate is to deduplicate on the business key (`customer_id`) and
include all unique entities. The built-in FR-26 revenue cross-check was what
caught this bug — without it, the revenue shortfall would have gone undetected.

---

## Bug 5 — Dashboard: Tile 5 dataset SQL didn't match repo + wrong X-axis grain

**Date:** 2026-08-09
**Phase:** Phase 5 — Dashboard

**Symptom:**
Tile 5 (Daily Revenue Trend line chart) rendered but the X-axis was bucketed by
month instead of day, and `period_type` was not available as a selectable field
in the chart configuration panel.

**Root cause:**
Two related issues, both on Tile 5 (not Tile 4):
1. The dataset SQL pasted into the Databricks dashboard editor did not match the
   version in `dashboard_queries.sql`. Specifically, the `WHERE period_type = 'daily'`
   filter had been applied server-side in the pasted variant, which meant `period_type`
   was never a column in the dataset output and could not be selected in the chart config.
2. With the dataset as pasted, the X-axis was auto-configured as `MONTHLY(order_date)`
   rather than plain `order_date`, producing monthly buckets instead of a daily trend line.

**Fix applied:**
Re-pasted the exact query from `dashboard_queries.sql` into the dataset editor (ensuring
`period_type` appeared as a column and `WHERE period_type = 'daily'` was present). Then
set the chart X-axis to plain `order_date` (not the auto-detected date truncation). Line
chart then rendered the correct daily granularity.

**Lesson:**
Always paste dataset SQL directly from the repo file — do not retype or paraphrase it
in the dashboard editor, as even small deviations (a missing filter, a renamed column)
can make chart fields unavailable and cause misleading auto-configuration. The
DASHBOARD_GUIDE.md step should say "copy verbatim from `dashboard_queries.sql`."

---

## Bug 6 — Dashboard: Histogram axis fields configured in wrong order

**Date:** 2026-08-09
**Phase:** Phase 5 — Dashboard

**Symptom:**
Tile 2 (Customer Revenue Distribution) rendered as streaky horizontal bands rather
than a proper histogram with vertical bars.

**Root cause:**
`total_revenue` was placed in the Y-axis field instead of the X-axis field. With a
continuous numeric column on Y and nothing meaningful on X, Databricks rendered each
row as a horizontal streak rather than bucketing values into bins. This also left the
Y-axis with no aggregation field after the X/Y swap, so a second issue emerged immediately
after the field was moved.

**Fix applied (two steps):**
1. Moved `total_revenue` from Y-axis to X-axis and set binning to `BIN(2500)` — this
   produced the bin boundaries used in the final histogram (1.33k, 4.86k, 3.07k, 678
   customers across visible bins).
2. With `total_revenue` now on X, the Y-axis had no field at all. Added `Count` (record
   count) to the Y-axis. Histogram then rendered correctly showing customer count per bin.

**Lesson:**
For Databricks histogram charts, the numeric column being distributed goes on the X-axis
(as the bin source), and Count goes on the Y-axis. The streaky-band symptom is the
diagnostic for a continuous field on the wrong axis. The DASHBOARD_GUIDE.md should
specify axis assignment explicitly: "X-axis: total_revenue, BIN(2500); Y-axis: Count."

---

## Bug 7 — Dashboard: Yearly order_date global filter chip affected all tiles

**Date:** 2026-08-09
**Phase:** Phase 5 — Dashboard

**Symptom:**
A `YEARLY(order_date)` filter chip appeared at the top of the dashboard and, when
active, restricted all tiles to the selected year — causing incomplete data across
every tile simultaneously rather than a single-tile issue.

**Root cause:**
Databricks AI/BI Dashboard automatically surfaced a global filter chip for
`order_date` based on the date column present in one of the tile datasets. When
the grain was set to YEARLY in the filter chip configuration, the filter applied
dashboard-wide (not scoped to one tile), which was not the intended behaviour.

**Fix applied:**
Used "Reset all to default" on the filter chip panel, which cleared the active
year selection and restored all tiles to their full unfiltered data range. No tile
configuration changes were needed — the fix was entirely at the dashboard filter
level.

**Lesson:**
Databricks AI/BI Dashboards can auto-generate global filter chips from date columns
in any dataset. These chips apply across all tiles by default and are easy to
accidentally activate. Always verify the "Reset all to default" option is available
and clearly documented for dashboard consumers, since a stale year filter on a
published dashboard would silently show incomplete data to every viewer.

---

## Bug 8 — Integration test: _check() crashed with TypeError on decimal.Decimal (Section 7)

**Date:** 2026-08-09
**Phase:** Phase 6 — Testing (Tier 2)

**Symptom:**
`integration_test_silver_gold.py` crashed at Section 7 (FR-26 revenue cross-check):
```
TypeError: unsupported format string passed to NoneType.__format__
```
The three revenue totals printed immediately before the crash were all identical
($54,940,228.41) — the pipeline data was entirely correct.

**Root cause:**
The `_check()` helper determined whether to compute a numeric diff with:
```python
diff = abs(actual - expected) if isinstance(expected, (int, float)) else None
```
Spark's `F.sum()` on a `DECIMAL(14,2)` column returns `decimal.Decimal` in Python
when collected — not `float` or `int`. So `isinstance(expected, (int, float))` was
`False`, `diff` was set to `None`, and the format string `f"diff={diff:,.2f}"` in
the `tolerance > 0` branch crashed trying to apply `:,.2f` to `None`.

**Fix applied:**
Replaced the `isinstance` guard with a `float()` conversion in a `try/except`:
```python
try:
    diff = abs(float(actual) - float(expected))
except (TypeError, ValueError):
    diff = None
```
Also guarded the format string so `diff:,.2f` is only attempted when `diff is not None`.
`float(decimal.Decimal(...))` is always safe and preserves the value correctly.

**Lesson:**
Python's `decimal.Decimal` is not a subclass of `float` — `isinstance(Decimal, float)`
is always `False`. Any helper that uses `isinstance(x, (int, float))` to decide whether
to perform numeric operations will silently skip `Decimal` values. In Spark test code,
use `float()` conversion rather than `isinstance` checks for numeric type guards.
This bug was caught only because the notebook was actually run, not just reviewed —
the code looked correct on inspection.

---

## Bug 9 — Integration test: gold_daily_weekly_trends expected range was wrong (Section 6)

**Date:** 2026-08-09
**Phase:** Phase 6 — Testing (Tier 2)

**Symptom:**
Section 6 of the integration test used the range `300–800` as the expected row count
for `gold_daily_weekly_trends`. This range was wrong — the actual verified count from
the Phase 4 Databricks run was 1,923 rows (1,682 daily + 241 weekly). The test would
have passed with the wrong expectation during the test run, masking the discrepancy.

**Root cause:**
The range `300–800` was estimated from first principles during test authoring ("~365
daily dates for one year of data") without consulting the Phase 4 verification data
already recorded in `ai-prompts/gold-layer.md`. The estimate was wrong for two reasons:
1. The synthetic order dates span multiple calendar years (2022–2026), not just one year.
2. The weekly rows were not counted at all in the estimate.

This was an error in the *test's expected value*, not in the pipeline or the data.

**Fix applied:**
Replaced the `if not (300 <= n_trends <= 800)` range check with an exact `_check()`
assertion using the verified count of 1,923. The count is deterministic because SEED=42
produces the same order dates every run, yielding the same set of distinct calendar days
and ISO weeks.

**Lesson:**
Test expected values should be sourced from verified artifacts — specifically, the
Phase 4 run outputs already recorded in `ai-prompts/gold-layer.md` — not reconstructed
from intuition. A wrong expected value in an assertion that passes is arguably worse
than a test failure: it gives false confidence. When real data is already available,
always use it as ground truth for test expectations.
