# Final AI Usage Summary

> Executive summary of how AI (Cursor) was used across the full lifecycle of this project.
> Written for an assessor reviewing the AI capability deliverable.

---

## Tool Used

**Cursor** with persistent project rules (`.cursor/rules/00-project-context.mdc`).
All exchanges took place in a single long-running Cursor session with conversation
history summarised and maintained across phases.

---

## Scale of AI Involvement

| Layer / Artifact | Lines of code / content | AI-generated | Human-authored |
|---|---|---|---|
| `generate_sample_data.py` | ~490 lines | 100% | 0% |
| Bronze layer (4 scripts) | ~480 lines | 100% | 0% |
| Silver layer (6 scripts) | ~580 lines | 100% | 0% |
| Gold layer (5 scripts) | ~480 lines | 100% | 0% |
| `dashboard_queries.sql` | 118 lines | 100% | 0% |
| `tests/test_data_quality.py` | ~240 lines | 100% | 0% |
| `tests/test_transformations.py` | ~160 lines | 100% | 0% |
| `tests/integration_test_silver_gold.py` | ~280 lines | 100% | 0% |
| Planning documents (`requirements-analysis.md`, gap log) | ~554 lines | 70% | 30% |
| `ai-prompts/*.md` files | ~800 lines | 80% | 20% |
| Schema DDL, setup notes, data model | ~400 lines | 100% | 0% |
| `DASHBOARD_GUIDE.md`, `DATA_GENERATION_NOTES.md` | ~200 lines | 100% | 0% |
| `debugging-notes.md`, `reflection.md`, `final-ai-usage-summary.md` | ~600 lines | 90% | 10% |

Approximately **95% of the codebase** was AI-generated. Human input was primarily
directional (requirements, corrections, acceptance decisions) rather than textual.

---

## Most Effective Prompts

**1. The planning prompt (Phase 0):**
> "Produce a comprehensive plan covering understanding check, functional/non-functional
> requirements, acceptance criteria, gap analysis, assumptions, repository scaffold,
> prompt history logging plan, phased build plan, evaluation-parameter mapping, and
> small polish opportunities."

This single prompt produced the full `requirements-analysis.md` with 35 FRs, 18
assumptions, 8 gaps, and a phased build checklist. All subsequent phases referenced it
as ground truth. High-quality initial planning multiplied the value of every later phase.

**2. The Silver phase prompt (Phase 3):**
> "Also check `ai-prompts/bronze-layer.md` before writing `create_silver_tables.py` —
> don't repeat the `%run` bug from Bronze."

Explicitly directing AI to read a previous debugging entry before writing new code
caused the Bronze `%run` lesson to propagate correctly into Silver's orchestrator.
Silver ran correctly the first time. This demonstrates how maintaining a prompt log
is operationally useful — not just a documentation afterthought.

**3. The Gold cross-check prompt (Phase 4):**
> "Implement all four gold/*.sql scripts + create_gold_tables.py orchestrator.
> Source only rows where quality_check_result = 'PASSED'."

AI interpreted FR-26 as a live `AssertionError`-raising cross-check in the orchestrator
rather than a passive post-hoc query. That choice caused Bug 4 ($635K revenue gap) to
surface on the first Gold run rather than potentially going unnoticed.

---

## Where AI Output Needed the Most Correction

**1. Gold customer scoping (Bug 4 / G-08).**
AI applied `WHERE c.quality_check_result = 'PASSED'` to the customer dimension, correctly
filtering dimension records but incorrectly excluding legitimate order revenue. The error
was semantically subtle — the same pattern that is correct for fact tables is wrong for
dimension tables in a flagging-not-deleting Silver design. Required an explicit correction
with explanation before AI understood the distinction.

**2. Integration test expected values (Bug 9).**
The test for `gold_daily_weekly_trends` row count used an estimate (`300–800`) rather than
the verified count from Phase 4. AI authored the test without checking the adjacent
`ai-prompts/gold-layer.md` entry that contained the real number. Required a user prompt
pointing to the source to get the correct assertion.

**3. Dashboard description accuracy.**
The initial `ai-prompts/dashboard.md` summary of the live dashboard tiles contained four
specific inaccuracies: wrong product category names, wrong histogram bin count, wrong tile
title, and a vague explanation for the 2026 revenue dip. Required line-by-line correction
against a screenshot before the log reflected what was actually built.

---

## Validation Approach

Every AI-generated output was validated before being accepted:

| Phase | Validation method |
|---|---|
| Data generation | Automated defect verification table: 13 categories × expected count = actual count |
| Bronze | `SHOW TABLES` smoke check + `COUNT(*)` assertion at end of each ingest script |
| Silver | Row count conservation check + per-check failure counts matched 13-defect spec |
| Gold | FR-26 revenue cross-check built into orchestrator; `AssertionError` on mismatch |
| Dashboard | Live Databricks dashboard tiles reviewed visually against screenshot |
| Tests | `pytest tests/ -v` locally (21/21) + Databricks integration notebook (ALL PASSED) |

No layer was accepted on code review alone. Every layer was run and its output verified
against a stated expectation from `requirements-analysis.md`.

---

## Prompt Pattern That Worked Consistently

```
1. State the phase and layer.
2. Name the specific files in requirements-analysis.md to read first.
3. Specify any prior debugging entries to check before writing code.
4. List what to implement, not how.
5. End with: "Ask if anything's ambiguous."
```

This pattern produced correctly-scoped responses that cited FRs and assumptions
rather than inventing design decisions, and that asked clarifying questions rather
than silently assuming.

---

## Prompt Pattern That Failed

Prompts that stated only the high-level goal without referencing the requirements
document produced correct-looking but subtly wrong code (Gold customer filter being
the clearest example). AI's default behaviour is to apply general best practices;
explicit references to project-specific constraints (flagging-not-deleting Silver,
A-09 "all copies of duplicates flagged", FR-11 "all columns nullable") were required
to override those defaults.

---

## Lessons for Real Production Pipelines

**AI is most effective as a fast, consistent implementer — not as a requirements analyst.**
The best outcomes in this project came from prompts that provided fully-formed, specific
requirements and asked AI to implement them. Prompts that left design decisions open
("how should I handle duplicates?") required more back-and-forth than prompts that had
already decided the answer ("use ROW_NUMBER() to deduplicate before the join").

**Prompt history is an operational asset, not just documentation.**
Logging debugging entries in `ai-prompts/*.md` and then referencing them in later
phase prompts ("also check bronze-layer.md before writing this orchestrator") produced
measurable improvement in first-run correctness. In a real team setting, a shared
prompt log would allow engineers to reuse effective prompts and avoid relearning the
same platform-specific bugs.

**Cross-checks in code beat review in comments.**
The single most valuable design choice in this project was implementing FR-26 as a
live assertion in `create_gold_tables.py` rather than a note in a review checklist.
It cost ~15 lines and caught a $635K bug. Any pipeline with a meaningful invariant
(revenue conservation, row count conservation, referential completeness) should
express that invariant as executable code.

**Two-tier testing catches different things.**
The local pandas tests verified transformation logic in isolation. The Databricks
integration tests verified that the actual Delta tables on actual infrastructure
contained the expected data. Neither tier produced false confidence on its own —
the integration tests were the ones that caught the two test-authoring bugs, precisely
because they ran against reality rather than a controlled in-memory fixture.
