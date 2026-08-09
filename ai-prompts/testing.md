# AI Prompts — Testing

> Prompt history for all exchanges related to `tests/test_data_quality.py`
> and `tests/test_transformations.py`. Entries are added after each significant exchange.
> Format: see Section 5 of `requirements-analysis.md` for the standard entry template.

---

## Prompt 1: Implement test_data_quality.py and test_transformations.py

**Date:** 2026-08-09
**Phase:** 6 — Testing
**User prompt (summary):** Phase 5 (Dashboard) complete and verified. Proceed to
Phase 6: read FR-33 through FR-35 and the two-tier testing approach (pandas unit
tests locally, Databricks integration notebook for real verification). Implement
`tests/test_data_quality.py` (assert each of the 5 Silver checks catches its actual
seeded defect count) and `tests/test_transformations.py` (unit test at least one Gold
aggregation function). Ask if anything's ambiguous. Log to `ai-prompts/testing.md`.

**AI response summary:**

### Files written
| File | Content |
|------|---------|
| `tests/test_data_quality.py` | 16 tests covering all 5 Silver checks + sanity checks |
| `tests/test_transformations.py` | 5 tests covering 3 Gold aggregation functions |

### No ambiguities — implementation proceeded directly

All defect counts were read directly from `DATA_GENERATION_NOTES.md` (deterministic
SEED=42). Silver check logic was verified against `05_quality_business_logic.py` to
ensure exact parity. No design decisions required asking.

### test_data_quality.py: 16 tests across 5 checks

| Test function | Seeded defect | Asserted count |
|---|---|---|
| `test_completeness_null_email` | C-01 | == 50 |
| `test_completeness_null_customer_id` | O-01 | == 100 |
| `test_completeness_null_product_id` | O-02 | == 200 |
| `test_uniqueness_duplicate_customer_id` | C-04 | == 10 rows (5 pairs, A-09: all copies) |
| `test_uniqueness_duplicate_order_id` | O-05 | == 20 rows (10 pairs) |
| `test_type_validation_malformed_email` | C-02 | == 40 |
| `test_type_validation_future_signup_date` | C-03 | == 20 |
| `test_type_validation_zero_or_negative_quantity` | O-06 | == 60 |
| `test_type_validation_negative_unit_price` | O-07 | == 50 |
| `test_referential_integrity_orphan_customer_id` | O-03 | == 50 |
| `test_referential_integrity_orphan_product_id` | O-04 | == 30 |
| `test_business_logic_total_amount_mismatch` | O-08 | == 40 (qty>0 AND price>0 filter applied) |
| `test_business_logic_payment_date_before_order_date` | O-09 | == 30 |
| `test_business_logic_completed_no_payment_date` | BL-2 (defensive) | == 0 (verifies no false positives) |
| `test_row_counts` | sanity | customers=10k, orders=100k, products=500 |
| `test_products_are_defect_free` | sanity | 0 NULLs/negatives in products.csv |

Assertion strength: `==` (exact count, stronger than `>=` required by FR-34) — justified
by the deterministic SEED=42 ensuring identical output every run.

### test_transformations.py: 5 tests covering 3 helper functions

Helper functions mirror Gold SQL logic in pandas:
- `compute_sales_by_product()` — mirrors `01_sales_by_product.sql`
- `compute_revenue_by_customer()` — mirrors `02_revenue_by_customer.sql` (including G-08 fix: no customer quality_check_result filter)
- `assign_segment()` — mirrors `04_customer_segmentation.sql` CASE logic

| Test function | What it verifies |
|---|---|
| `test_sales_by_product_aggregation` | Correct GROUP BY totals for 2 products; desc sort by revenue |
| `test_revenue_by_customer_aggregation` | Correct totals + LEFT JOIN preserves Carol (0 orders) with zeros |
| `test_customer_segmentation_logic` | All 4 segment labels + 4 boundary conditions (threshold edge cases) |
| `test_quality_check_result_filter_excluded_from_product_agg` | FAILED rows excluded from product revenue |
| `test_quality_check_result_filter_excluded_from_customer_agg` | FAILED orders excluded from customer revenue |

### Debugging — one test required a fix

`test_products_are_defect_free` initially referenced column `unit_price` but
the actual column in `products.csv` is `price` (schema has
`product_id, product_name, category, price, cost, stock_quantity, reorder_level`).
The `_load_products()` dtype mapping was also corrected.
Fix was applied immediately after the first run failure; no test logic changed.

### Final run result

```
21 passed in 0.95s
```

All 21 tests pass against the real CSVs on Python 3.12 / pytest 9.1.1.

**Evaluation:** Accepted and verified — 21/21 PASSED locally (2026-08-09).

---

## Prompt 2: Implement integration_test_silver_gold.py (Tier 2)

**Date:** 2026-08-09
**Phase:** 6 — Testing (Tier 2)
**User prompt (summary):** Implement a Databricks notebook-format `.py` integration
test that runs a focused subset of the Tier 1 assertions directly against the live
Delta tables (silver_customers, silver_orders, gold_* tables). Correct %run format.
Log to ai-prompts/testing.md.

**AI response summary:**

### File written
`tests/integration_test_silver_gold.py` — Databricks notebook format
(`# Databricks notebook source`, `# COMMAND ----------` cells).

### Assertions implemented (7 sections)

| Section | What it checks | Expected values |
|---|---|---|
| 1. Row count conservation | Silver rows == Bronze rows | customers=10,000, orders=100,000 (nothing deleted) |
| 2. Completeness failures | FAILED_COMPLETENESS count per table | customers=50 (C-01), orders=300 (O-01+O-02) |
| 3. Uniqueness failures | FAILED_UNIQUENESS count per table | customers=10 (C-04), orders=20 (O-05) |
| 4. Referential integrity | FAILED_REFERENTIAL_INTEGRITY in orders | 80 (O-03:50 + O-04:30) |
| 5. PASSED counts | PASSED rows in each Silver table | customers=9,880, orders=99,420 |
| 6. Gold row counts | Row count ranges for all 4 Gold tables | product≤500, customer 9k–10k, seg=4, trends 300–800 |
| 7. FR-26 revenue | Gold revenue SUM ≈ Silver PASSED SUM | Within $5.00 tolerance |

### Design decisions

**Accumulator pattern (not early-exit):** All assertions accumulate into `_failures`.
Every check runs regardless of prior failures. Final cell prints consolidated pass/fail
report and raises `AssertionError` only if anything failed. This lets a reviewer see
all results in one notebook run rather than stopping at the first failure.

**No %run in this notebook:** This IS the top-level integration notebook — there is
nothing to `%run`. The Bronze/Silver/Gold lessons about %run placement apply only to
orchestrator notebooks that call sub-notebooks.

**Range bounds for Gold row counts (not exact):** Gold table sizes depend on
runtime data distribution (e.g., whether all 500 products appear in PASSED orders).
Ranges are used: `1–500` for products, `9,000–10,000` for customers,
`300–800` for daily+weekly trends combined. Only `gold_customer_segmentation`
is asserted exactly (always 4 rows, one per segment type).

**Expected counts derived from DATA_GENERATION_NOTES.md + non-overlap guarantee:**
Since all 13 defect categories are seeded in non-overlapping index ranges (per A-10
intent), each row has exactly one failure code. This means Silver failure counts
add cleanly without double-counting.

**Evaluation:** Accepted with one bug fixed — see Debugging Entry 1 below.

---

## Debugging Entry 1: _check() crashed on Decimal type in Section 7 (FR-26)

**Date:** 2026-08-09
**Phase:** 6 — Testing (Tier 2)
**Trigger:** Running `integration_test_silver_gold.py` in Databricks.

**Symptom reported:**
> TypeError: unsupported format string passed to NoneType.__format__
> crashed on Section 7 (FR-26 revenue cross-check). The three printed SUMs
> right before the crash were all identical ($54,940,228.41) — so the actual
> revenue data is correct.

**Root cause:**

`_check()` line 59 computed `diff` conditionally:
```python
diff = abs(actual - expected) if isinstance(expected, (int, float)) else None
```
Spark's `F.sum()` on a `DECIMAL(14,2)` column returns `decimal.Decimal` in Python
when collected — **not** `float` or `int`. So `isinstance(expected, (int, float))`
evaluated to `False` → `diff = None`.

Line 63 then tried to format `diff` with `:.2f` inside the `tolerance > 0` branch:
```python
f"... diff={diff:,.2f}"  # ← crashes: NoneType has no :.2f formatting
```
Python's `format()` protocol raises `TypeError` when `:,.2f` is applied to `None`.

The data itself was entirely correct (all three revenue totals matched exactly).
This was purely a type-handling bug in the test helper, not a pipeline bug.
It was caught because the notebook was actually run, not just code-reviewed.

**Fix applied:**

Two changes to `_check()` in `tests/integration_test_silver_gold.py`:

1. Replace `isinstance` guard with `float()` conversion in a `try/except`:
```python
try:
    diff = abs(float(actual) - float(expected))
except (TypeError, ValueError):
    diff = None
```
`float(decimal.Decimal("54940228.41"))` works correctly. The try/except handles
any edge case (NaN, None inputs) without crashing.

2. Guard the format string so `diff:,.2f` is never reached when `diff is None`:
```python
if tolerance > 0 and diff is not None:
    detail = f"expected {expected:,} ± {tolerance:,.2f}, got {actual:,}, diff={diff:,.2f}"
else:
    detail = f"expected {expected:,}, got {actual:,}"
```

**Lesson:** `decimal.Decimal` is not a subclass of `float` or `int` in Python,
even though it behaves like one for arithmetic. Any helper that checks
`isinstance(x, (int, float))` to decide whether to compute a numeric diff will
silently fall through for Spark-collected DECIMAL aggregates. Always use
`float()` conversion or `numbers.Number` for numeric type guards in Spark test code.

**Evaluation:** Fixed — ALL PASSED confirmed on re-run.

---

## Debugging Entry 2: gold_daily_weekly_trends expected range was wrong (test bug, not pipeline bug)

**Date:** 2026-08-09
**Phase:** 6 — Testing (Tier 2)
**Trigger:** User review of integration test Section 6 output against verified Phase 4 data.

**Symptom reported:**
> Section 6 range for gold_daily_weekly_trends (expected 300–800) is wrong — it
> was an estimate, not based on real data.  Verified back in Phase 4 that the real
> count is 1,923 (1,682 daily rows + 241 weekly rows).

**Root cause:**

The range `300–800` in Section 6 was written from first principles ("~365 daily
dates") without consulting the actual Phase 4 verification data that had already
been recorded in `ai-prompts/gold-layer.md`. The estimate was off by 2–6× because:
- The "daily" estimate ignored that order_dates span multiple calendar years
  (synthetic data goes 2022–2026), not just one year (~365 days)
- The weekly rows were not accounted for at all in the initial estimate

The pipeline itself was always correct — this was an error in the *test's expected
value*, not in the data or the pipeline logic.

**Fix applied:**

Replaced the `if not (300 <= n_trends <= 800)` range check with an exact assertion
using `_check()`:
```python
_check(
    "gold_daily_weekly_trends row count  (1,682 daily + 241 weekly = 1,923, SEED=42)",
    n_trends, 1_923,
)
```
The exact count (1,923) is deterministic — SEED=42 produces the same order dates
every run, which produces the same set of distinct calendar days and ISO weeks.

Also updated the Section 6 header comment to document the verified counts.

**Lesson:** Writing an assertion range from an estimate, rather than from real
observed data, defeats the purpose of the test.  When the pipeline has already been
run and verified (Phase 4 confirmed the row counts in Databricks), those real values
should be used as the test's expected values — not reconstructed from memory.
Checking `ai-prompts/gold-layer.md` before writing Section 6 would have prevented
this.  Test expected values should be sourced from verified artifacts, not intuition.

**Evaluation:** Fixed — re-run pending (ALL PASSED expected).
