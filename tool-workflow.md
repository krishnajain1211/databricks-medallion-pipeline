# AI Workflow Foundation (Part A)

> How Cursor was used across the full data engineering lifecycle for this project.

---

## Primary AI Tool Used

**Cursor** (AI-enabled IDE), using the Composer/Agent mode with the Sonnet model.

Cursor was the only AI tool used. No separate Claude, ChatGPT, or Copilot sessions were
run alongside it. All prompt exchanges happened inside a single long-running Cursor
conversation, with a conversation summary maintained across context resets.

Project rules were loaded automatically from `.cursor/rules/00-project-context.mdc` at
the start of every session, ensuring Cursor never forgot the hard constraints (flagging
not deleting, no PII, snake_case naming, docstrings on every function) without needing
to restate them in each prompt.

---

## How I Provide Project Context

Context was provided in three layers:

**1. Persistent rules file (`.cursor/rules/00-project-context.mdc`)**
Contains the non-negotiable hard rules: Silver never deletes rows, all synthetic data,
snake_case identifiers, every non-trivial decision must be explainable. These are loaded
into every Cursor session automatically, so they apply even after a context reset.

**2. `requirements-analysis.md` as ground truth**
Every phase prompt began with "Read requirements-analysis.md FR-XX through FR-YY and
A-XX before starting." This forced Cursor to read the locked requirements rather than
invent assumptions. The assumptions list (A-01 through A-18) was the single place where
design decisions were recorded — not in code comments, not in the AI's context window.

**3. `ai-prompts/*.md` for cross-phase memory**
When starting Phase 3 (Silver), the prompt explicitly said "check `ai-prompts/bronze-layer.md`
before writing `create_silver_tables.py` — don't repeat the `%run` bug from Bronze."
This caused Cursor to read the Bronze debugging entry and apply the fix proactively to
Silver. Without this cross-referencing, the same silent failure would have recurred.

---

## How I Use AI for Requirement Analysis

Cursor produced the initial `requirements-analysis.md` from a single detailed planning
prompt that specified: understanding check, functional requirements, non-functional
requirements, acceptance criteria, gap analysis, assumptions, scaffold, prompt history
plan, phased build plan, evaluation mapping, and polish opportunities.

The output was reviewed, corrected in three rounds (defect count from 460 to 700;
environment from Community Edition to Free Edition; catalog from "main" to "workspace"),
and then locked. Subsequent phases treated `requirements-analysis.md` as read-only.

When new gaps emerged during implementation (G-08: Gold customer filter bug), they were
added to the gap log in `requirements-analysis.md` rather than resolved silently in code.
This kept the requirements document accurate as a historical record, not just a plan.

---

## How I Use AI for Pipeline Design (Bronze/Silver/Gold)

Design decisions were made in the planning phase and encoded as assumptions (A-01
through A-18) before any code was written. Cursor was given the decisions, not asked to
make them. For example:

- **Bronze:** "Write mode is overwrite + overwriteSchema; ingest metadata to a log table."
  Cursor implemented those choices; it did not choose them.
- **Silver:** "Flag bad rows via `quality_check_result` column — never delete." The
  fail-ID DataFrame pattern (each check script exposes a DataFrame of failing PKs; the
  orchestrator left-joins them all) was proposed by Cursor and accepted after review.
- **Gold:** "Source only `quality_check_result = 'PASSED'` rows; include FR-26 revenue
  cross-check." The CTE deduplication pattern for customer dimension (ROW_NUMBER) was
  proposed by Cursor after the G-08 bug was explained; the decision to use it was human.

The key discipline: Cursor was asked "implement this design" rather than "design this
for me." When Cursor was given an open-ended design question, the quality of the output
dropped (the Gold customer filter bug is the clearest example).

---

## How I Use AI for Code Generation (Python/PySpark/SQL)

All pipeline code was AI-generated (~95% of the codebase). The prompt pattern that
worked consistently:

```
1. Name the phase and files to implement.
2. Cite the specific FRs and assumptions to read first.
3. Cite any prior debugging entries to check before writing.
4. State the constraint on format (Databricks notebook source format, snake_case, docstrings).
5. End with: "Ask if anything's ambiguous."
```

This produced correctly-scoped responses that cited requirements rather than inventing
decisions. Vague prompts ("write the Silver quality checks") produced code that looked
right but missed subtle spec constraints (e.g., A-11: NULL FK rows excluded from
referential integrity check before the anti-join).

Specific format constraints were critical for Databricks notebooks: the `# Databricks
notebook source` header, `# COMMAND ----------` cell separators, and the rule that
`# MAGIC %run` must be the first content line of its cell — all stated explicitly in
the prompt or in the rules file.

---

## How I Validate AI-Generated Code and Logic

No layer was accepted on code review alone. Each phase had a specific validation gate:

| Phase | Validation method |
|---|---|
| Data generation | Automated defect verification table: 13 categories, actual count = expected count (700/700) |
| Bronze | `SHOW TABLES` after first orchestrator run; `COUNT(*)` assertion at end of each ingest script |
| Silver | Row count conservation (10,000 customers, 100,000 orders — nothing deleted); per-check failure counts matched the 13-defect spec |
| Gold | FR-26 revenue cross-check built into the orchestrator as an `AssertionError`-raising cell |
| Dashboard | Live Databricks dashboard tiles reviewed visually; screenshot used to catch inaccurate tile descriptions in the prompt log |
| Tests | `pytest tests/ -v` locally (21/21 passed); Databricks integration notebook run to ALL PASSED |

The FR-26 cross-check is the most valuable example: it was implemented as executable
code that raises an error on failure, not as a post-hoc review note. That choice caught
a $635K revenue gap on the first Gold run.

---

## How I Use AI for Testing and Validation

Two test tiers, both AI-generated:

**Tier 1 — Local pandas tests (`tests/test_data_quality.py`, `tests/test_transformations.py`)**
21 pytest tests, runnable with no cloud dependency. Each Silver check has one test that
loads the real CSVs, applies the check logic in pandas, and asserts the exact expected
defect count from `requirements-analysis.md`. Gold transformation logic is unit-tested
against small in-memory DataFrames. Run in under 1 second; suitable for CI.

**Tier 2 — Databricks integration notebook (`tests/integration_test_silver_gold.py`)**
7 sections of assertions against live Delta tables, including row count conservation,
per-check Silver failure counts, PASSED row counts, Gold row count sanity, and the FR-26
revenue cross-check. Uses an accumulator pattern so all failures print before raising.

The test authoring prompts included the expected counts from the verified Phase 4 output
in `ai-prompts/gold-layer.md`. Where this was not done (the `gold_daily_weekly_trends`
range was estimated rather than sourced), the expected value was wrong — and was caught
and corrected on the first run.

---

## How I Use AI for Debugging

For every bug that required more than one attempt to fix, the debugging session was
logged in the relevant `ai-prompts/*.md` file with: symptom, root cause, fix, lesson.
The log entry was then referenced in the next phase's prompt to prevent recurrence.

**Example of the workflow in practice:**
1. Bronze `%run` silent failure discovered via `SHOW TABLES` returning empty.
2. Root cause identified: label comment before `# MAGIC` in same cell.
3. Fix applied: split into two cells, `# MAGIC %run` first line of its own cell.
4. Entry written in `ai-prompts/bronze-layer.md`.
5. Silver prompt included: "check `ai-prompts/bronze-layer.md` before writing the
   orchestrator." Silver's `create_silver_tables.py` got the fix on the first write.

Prompts used during debugging were specific about the symptom and what had already been
ruled out: "The three SUMs are all correct ($54,940,228.41) — so the data is fine. The
crash is in the `_check()` helper's format string when `diff` is None." This level of
specificity produced a correct root-cause analysis and fix without a back-and-forth round.

---

## How I Use AI for Data Quality Checks

The five Silver quality checks (completeness, uniqueness, type validation, referential
integrity, business logic) were each implemented as a separate Databricks notebook
following the fail-ID DataFrame pattern:

1. Read Bronze table(s).
2. Identify which primary key values fail this specific check.
3. Expose a DataFrame of failing IDs and an integer count.

The orchestrator (`create_silver_tables.py`) left-joins all five fail-ID DataFrames back
to Bronze, builds boolean flag columns, then derives `quality_check_result` as a
comma-delimited list of failure codes or "PASSED". This design was chosen so that a row
with multiple failures gets all failure codes recorded (Assumption A-10), not just the
first one caught.

The 13 seeded defect categories in `generate_sample_data.py` were designed to map
one-to-one to the Silver checks — ensuring each check has at least one real case to
catch, with non-overlapping row ranges so no row accidentally triggers two checks
intended to test different things. Cursor implemented the non-overlap layout as
index slices before shuffle.

---

## What Information I Avoid Sharing with AI Tools

**No real customer data.** All data is synthetic, generated by `generate_sample_data.py`
with SEED=42. The CSVs contain fictional names (Faker library), randomly generated emails,
and no real transaction records. At no point were real customer names, emails, order IDs,
or any other PII provided to Cursor.

**No secrets or credentials.** The Databricks workspace URL, personal access token, and
cluster IDs never appeared in any prompt or file committed to the repository. Connection
details in `database/setup-notes.md` describe the setup process (catalog name, schema
name, volume name) but contain no authentication material.

**No proprietary business logic.** The e-commerce domain is generic; there is no
company-specific pricing logic, customer segmentation criteria from a real business,
or internal system architecture that could be sensitive if reconstructed from the
conversation history.

---

## How I Would Reuse This Workflow in a Real Production Pipeline

The core pattern transfers directly, with three additions for production:

**What transfers as-is:**
- Persistent rules file (`.cursor/rules/`) with the team's hard constraints — naming,
  security, approved libraries, flagging vs. deleting policy.
- `requirements-analysis.md` as a locked spec before any code phase starts, with a
  gap log updated as implementation reveals ambiguities.
- Phase-structured prompts that cite specific FR numbers and assumption IDs — these keep
  AI output aligned with the spec rather than general best practice.
- Built-in cross-checks in orchestrators (revenue conservation, row count conservation).
- Two-tier tests: fast pandas/unit tests in CI, integration notebook on schedule.

**What would be added for production:**
- Prompt templates stored in version control, shared across the team. Every engineer
  uses the same "Phase N" prompt structure rather than each writing their own.
- Schema evolution guards before Bronze write: compare CSV headers to the expected
  StructType and fail early rather than silently writing malformed data.
- Scheduled Databricks job running the integration notebook after each pipeline run,
  with results written to a monitoring table.
- The AI prompt history (`ai-prompts/*.md`) retained as a living document updated
  after each pipeline change — not just for the initial build, but for every schema
  change, bugfix, and threshold adjustment thereafter.

---

## Lessons Learned

**What worked:**

- **Grounding prompts in a requirements document** prevented scope drift and produced
  code that cited specific FRs rather than general patterns. Every prompt that included
  "read FR-XX through FR-YY first" produced better-scoped output than those that did not.

- **Logging debugging entries and cross-referencing them in the next phase** caused
  lessons to propagate automatically. The `%run` fix applied to Bronze appeared correctly
  in Silver on first write because the Silver prompt pointed Cursor to the Bronze debug log.

- **Building invariant checks into orchestrators** (FR-26 revenue cross-check) caught a
  real bug that would otherwise have required manual investigation of aggregated totals.
  The check cost ~15 lines; the bug it caught was a $635K revenue discrepancy.

- **Running code before accepting it** found bugs that code review missed: the `%run`
  silent failure, the Decimal type error in `_check()`, and the wrong expected range in
  the integration test — none of these were visible on inspection.

**What did not work:**

- **Open-ended design prompts** ("how should I handle duplicates in Gold?") produced
  plausible but subtly wrong decisions (the customer filter bug). Specific design prompts
  with the decision already made ("use ROW_NUMBER() to deduplicate, include all unique
  customers regardless of quality_check_result") produced correct implementations.

- **Estimating test expected values** instead of sourcing them from verified artifacts.
  The `gold_daily_weekly_trends` range was wrong because it was calculated from
  intuition rather than the Phase 4 output already in the prompt log.

- **Trusting AI descriptions of visual output.** The dashboard tile descriptions in
  `ai-prompts/dashboard.md` contained four specific inaccuracies after the initial
  write (wrong category names, wrong histogram bin count, wrong tile title, imprecise
  2026 explanation). AI cannot see the live dashboard — any description of visual
  output must be human-verified against the actual screenshot before it is logged.
