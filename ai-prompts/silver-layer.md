# AI Prompts — Silver Layer

> Prompt history for all exchanges related to Silver layer quality check scripts
> (`01_quality_completeness.py` through `05_quality_business_logic.py`),
> `create_silver_tables.py`, `data-quality-strategy.md`, and the quality metrics report.
> Entries are added after each significant exchange.
> Format: see Section 5 of `requirements-analysis.md` for the standard entry template.

---

## Prompt 1: Implement all 5 quality check scripts + create_silver_tables.py orchestrator

**PROMPT SENT:**
"Phase 3, Silver layer. Read requirements-analysis.md's Silver section and
A-09/A-10/A-11/A-16/A-18 first. Also check ai-prompts/bronze-layer.md before
writing create_silver_tables.py — don't repeat the %run bug from Bronze.
Implement all 5 quality check scripts + create_silver_tables.py orchestrator.
Ask if anything's ambiguous. Log to ai-prompts/silver-layer.md."

**AI RESPONSE SUMMARY:**
Read all required sections and the Bronze debug entry before writing code.
Stated architecture upfront. No ambiguities found — all design questions resolved
from assumptions (A-09, A-10, A-11, A-16, A-18).

**Architecture chosen (fail-ID DataFrame pattern):**
Each check script (01-05) reads Bronze tables, identifies which PK values
fail its specific check, and exposes:
- `{check}_fail_customers` — DataFrame[customer_id] of failing IDs
- `{check}_fail_orders`    — DataFrame[order_id] of failing IDs
- `{check}_n_*_failed`     — int count of affected rows

The orchestrator left-joins each fail-ID DataFrame back to Bronze on PK,
adding boolean flag columns (`_fc`, `_fu`, `_ftv`, `_fri`, `_fbl`), then
builds `quality_check_result` using `concat_ws` + `when`:
- If all flags False → "PASSED"
- Otherwise → comma-delimited list of failure codes (A-10: all failures recorded)

**Key design decisions documented:**

- A-09 (all copies flagged): `uniqueness_fail_customers` holds 5 distinct
  duplicate customer_ids; when left-joined to bronze_customers, BOTH rows of
  each pair receive `_fu = True`. Same for orders.

- A-11 (ref integrity scope): `04_quality_referential_integrity.py` pre-filters
  `isNotNull()` before the anti-join so NULL FK rows are excluded (handled by
  completeness check).

- A-18 (payment_date cases): 05_quality_business_logic.py implements both:
  BL-1 (payment_date < order_date, seeded in 30 rows) and
  BL-2 (Completed + payment_date IS NULL, defensive — 0 seeded rows).

- A-13 (total_amount tolerance): BL-3 only fires when qty > 0 AND price > 0,
  explicitly excluding O-06/O-07 rows which are counted under type validation.

- Bronze %run bug applied: in create_silver_tables.py, every label comment
  and its %run are split into two separate cells with an intermediate
  `# COMMAND ----------`, ensuring # MAGIC is the first content line.

**Files written:**
- `src/silver/01_quality_completeness.py`      (~65 lines)
- `src/silver/02_quality_uniqueness.py`        (~70 lines)
- `src/silver/03_quality_type_validation.py`   (~90 lines)
- `src/silver/04_quality_referential_integrity.py` (~80 lines)
- `src/silver/05_quality_business_logic.py`    (~75 lines)
- `src/silver/create_silver_tables.py`         (~180 lines)
- `database/schema.sql` — Silver section filled in (3 CREATE TABLE statements)

**Expected check outcomes against seeded data:**
| Check              | Entity    | Rows Expected Failed |
|--------------------|-----------|---------------------|
| Completeness       | customers |  50 (NULL email)    |
| Completeness       | orders    | 300 (100+200 NULL)  |
| Uniqueness         | customers |  10 (5 pairs × 2)   |
| Uniqueness         | orders    |  20 (10 pairs × 2)  |
| Type Validation    | customers |  60 (40+20)         |
| Type Validation    | orders    | 110 (60+50)         |
| Ref Integrity      | orders    |  80 (50+30)         |
| Business Logic     | orders    |  70 (40+30)         |

**YOUR EVALUATION:** _Pending Databricks run. Please verify the quality metrics
table matches the expected counts above, and that silver_customers and
silver_orders have the correct row counts (10,000 and 100,000 respectively
with quality_check_result on every row)._

**FINAL DECISION:** _Pending._
