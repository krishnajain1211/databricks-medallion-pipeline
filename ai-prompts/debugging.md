# AI Prompts — Debugging Index

> Debugging entries were logged in the prompt file for the layer where the bug occurred,
> not collected here. This file serves as a navigational index.
> Format of each entry: see Section 5 of `requirements-analysis.md`.

---

## Where Debugging Entries Live

| Phase | Bug | Location |
|---|---|---|
| Phase 1 — Data generation | `UnicodeEncodeError` on Windows cp1252 console (✓ symbol) | `ai-prompts/data-generation.md` Prompt 1, AI Response step 4 |
| Phase 2 — Bronze | `%run` silent failure: label comment before `# MAGIC` disabled magic execution in `ingest_all.py` | `ai-prompts/bronze-layer.md` Debugging Entry 1 |
| Phase 4 — Gold | G-08: `gold_revenue_by_customer` $635K short — `WHERE quality_check_result = 'PASSED'` on customer dimension incorrectly excluded legitimate orders | `ai-prompts/gold-layer.md` Debugging Entry 1 |
| Phase 5 — Dashboard | Three tile configuration bugs: SQL/dataset mismatch (Tile 5), histogram axes reversed (Tile 2), global `YEARLY(order_date)` filter chip applied to all tiles | `ai-prompts/dashboard.md` Debugging Entries 1–3 |
| Phase 6 — Testing | `_check()` helper crashed with `TypeError` on `decimal.Decimal` from Spark aggregation | `ai-prompts/testing.md` Debugging Entry 1 |
| Phase 6 — Testing | `gold_daily_weekly_trends` expected range `300–800` was an estimate; corrected to exact `1,923` | `ai-prompts/testing.md` Debugging Entry 2 |

---

> Note: The merge conflict encountered when applying the Bronze `%run` fix is documented
> in `debugging-notes.md` (Bug 3) rather than in `ai-prompts/` because it was a git-level
> event, not an AI prompt exchange.
