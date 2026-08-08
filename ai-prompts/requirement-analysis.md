# AI Prompts — Requirement Analysis & Planning

This file logs all AI-assisted exchanges related to requirement analysis,
planning, and architectural decisions for this project. Entries are numbered
sequentially and append-only — earlier entries are never edited after logging.

---

## Prompt 1: Initial comprehensive requirement analysis and planning

**PROMPT SENT:**
"ROLE & CONTEXT — You are acting as a senior data engineer and AI pairing partner
on a formal, AI-first capability assessment [...] DO NOT WRITE OR GENERATE ANY CODE
YET. This first step is planning only. SOURCE OF TRUTH — Read
docs/assessment-requirements.md in full [...] WHAT I NEED YOU TO PRODUCE (as a
plan): 1. Understanding check [...] 2. Full requirement extraction [...] 3.
Assumptions & edge cases [...] 4. Full repository scaffold [...] 5. Prompt history
logging plan [...] 6. Phased, step-wise build plan [...] 7. Evaluation-parameter
mapping [...] 8. Small polish opportunities [...] 9. Open questions [...]"
(Full prompt was ~700 words covering 9 structured deliverables and hard
constraints; the above is a faithful condensed summary.)

**AI RESPONSE SUMMARY:**
Cursor read `docs/assessment-requirements.md` (537 lines) and `.cursor/rules/`
in full before producing a nine-section planning document covering:
- Understanding check restating the e-commerce Bronze→Silver→Gold→Dashboard
  pipeline in plain language
- Full functional requirements (FR-01 to FR-38), non-functional requirements
  (NFR-01 to NFR-10), and verbatim acceptance criteria with gap annotations
- Seven documented gaps (G-01 to G-07) — each with a reasoned resolution and a
  locked assumption (A-01 to A-06), notably: Silver check count "4 vs. 5 files"
  resolved to four named checks; Gold aggregation count "3 vs. 4 tables" resolved
  to four; "~700 problematic rows" identified as 460 with existing categories
  (later revised — see Prompt 4); missing `tests/` and `tool-specific/` folders
  added to scaffold
- Eighteen assumptions and edge cases (A-07 to A-18) covering currency, timezone,
  duplicate resolution strategy, multi-failure stamping, referential integrity
  scope, negative values, payment_date nullability, DBFS paths (later revised),
  etc.
- Complete proposed repository scaffold (31 files across 12 folders)
- Prompt history logging plan with file-to-activity mapping and standardised entry
  format
- Eight-phase checkpoint build plan (Phase 0 Foundation through Phase 7
  Artifacts), each with "done looks like" and acceptance criteria mapping
- Evaluation-parameter mapping across all 11 rubric areas, flagging Data
  Contracts/Schema Thinking as the weakest
- Four polish opportunities (P-01 schema contract validation, P-02 lineage row
  counts, P-03 Mermaid diagram, P-04 quality metrics dashboard tile)
- Six open questions (OQ-01 through OQ-06) flagged for resolution before Phase 2

**YOUR EVALUATION:**
✓ Accepted:
- All seven gap identifications and their resolutions — found real contradictions
  in the document (Gold count, Silver count, missing `tests/` folder) that would
  have caused problems if not caught at planning time
- The phased build plan structure and "done looks like" framing — gives a clear
  self-verification mechanism against the rubric
- The evaluation-parameter mapping, especially the flag that Data
  Contracts/Schema Thinking is weak (polish opportunity P-01 directly addresses it)
- The four polish opportunities — all are genuinely small and high-value
- The prompt history logging format and file mapping
- The eighteen assumptions, particularly A-09 (flag ALL duplicate copies, not
  just second), A-10 (comma-delimited multi-failure codes), A-11 (referential
  integrity only checks non-NULL rows), A-18 (payment_date nullability)

✗ Changed:
- G-03 / A-03 ("~700 problematic rows" resolution): initially resolved as a
  documentation error with 460 being the authoritative count. This was later
  revised in Prompt 3 (math correction) and fundamentally reconsidered in Prompt 4
  (see separate entries)
- OQ-01 through OQ-06 were open questions at this stage — all resolved in Prompt 3

✗ Rejected:
- Nothing in the plan structure was rejected outright at this stage

**FINAL DECISION:** Plan accepted in full and saved to `requirements-analysis.md`
as the primary planning artifact. Six open questions deferred for resolution.

---

## Prompt 2: Save plan to file

**PROMPT SENT:**
"save this plan in a file"

**AI RESPONSE SUMMARY:**
Read the Cursor internal plan file and wrote its content to
`requirements-analysis.md` in the project root. Chose the root location (over
`docs/` or `ai-prompts/`) because `requirements-analysis.md` is a first-class
submission artifact named in the assessment's repo tree and the content — all
nine planning sections — maps directly to it. Stripped the internal YAML
frontmatter (plan metadata) before writing.

**YOUR EVALUATION:**
✓ Accepted:
- File location (`requirements-analysis.md` at repo root) — correct per the
  required repo structure
- Content written in full, including all nine sections and the introductory note
  identifying this as a pre-code collaborative planning exercise

✗ Changed:
- None

✗ Rejected:
- None

**FINAL DECISION:** `requirements-analysis.md` written to the repo root with
the complete nine-section planning document.

---

## Prompt 3: Six corrections before locking the plan

**PROMPT SENT:**
"A few corrections before we lock this in:
1. Fix the G-03 percentage math: it should be ~0.42% across all rows
   (460/110,500), or exactly 0.40% within orders specifically (400/100,000) [...]
2. Resolve OQ-01: Databricks Community Edition was retired Jan 1, 2026 and
   replaced by Free Edition. Use Free Edition everywhere [...]
3. Revise A-14 (and resolve OQ-02): use Unity Catalog Volumes
   (/Volumes/<catalog>/<schema>/raw_data/...) as the canonical data path [...]
4. Resolve OQ-05: Unity Catalog three-level namespace is a constraint, not a
   choice, given Free Edition. Use it directly.
5. Resolve OQ-04: document a two-tier testing approach explicitly — pandas-based
   unit tests locally for the quality-check logic, plus a Databricks notebook
   that validates against the real Silver Delta tables as integration verification.
6. Resolve OQ-06: yes to per-phase commits, and additionally tag each phase
   completion (e.g. git tag phase-1-data-generation)."

**AI RESPONSE SUMMARY:**
Applied all six corrections as targeted `StrReplace` edits to
`requirements-analysis.md`:
- G-03 math: corrected to ~0.42% (460/110,500) and exactly 0.40% (400/100,000)
- NFR-10: removed "(Community)" parenthetical; added explicit note that Community
  Edition was retired January 1, 2026
- FR-07: updated from "S3/DBFS" to the concrete Unity Catalog Volume path
  `/Volumes/main/ecommerce_medallion/raw_data/`
- A-14: completely rewritten to describe Unity Catalog Volumes as the canonical
  path; introduced `BASE_VOLUME_PATH` constant pattern; removed all DBFS references
- A-15: updated to say files are uploaded to the Volume path, not DBFS
- FR-33/34/35: rewritten to describe the two-tier testing approach explicitly
  (Tier 1: pandas pytest locally; Tier 2: Databricks integration notebook)
- Phase 2 description: updated DBFS upload to Unity Catalog Volumes upload
- Phase 6 description and "Done looks like": expanded to describe both tiers
- Section 7 testing row: upgraded from Medium to Strong coverage
- Section 9: all six OQs closed as resolved decisions, with Unity Catalog naming
  convention locked in (`main.ecommerce_medallion.<table>`, Volume path confirmed)
  and git tag naming scheme defined (`phase-N-<name>` with `feat(phase-N):` commit
  message pattern)

**YOUR EVALUATION:**
✓ Accepted:
- All six corrections applied as specified
- Unity Catalog naming convention: `main` catalog, `ecommerce_medallion` schema,
  layer-prefixed table names (e.g., `bronze_customers`, `silver_orders`)
- Two-tier testing split: Tier 1 pandas (no Databricks needed, always runnable by
  reviewer) + Tier 2 Databricks notebook (authoritative proof on real infra)
- Git tag naming: `phase-0-foundation` through `phase-7-artifacts` with
  `feat(phase-N):` commit message convention

✗ Changed:
- None — all six corrections were applied exactly as specified

✗ Rejected:
- None

**FINAL DECISION:** All six corrections applied; `requirements-analysis.md`
updated in-place. All open questions OQ-01 through OQ-06 are now resolved.

---

## Prompt 4: Extend seeded defects to exactly 700 rows across 13 categories

**PROMPT SENT:**
"One more revision to the planning document: I want the total seeded defect count
to be exactly 700 rows [...] Rather than scaling the existing categories
arbitrarily, extend into new defect types that seed real test cases for the Type
Validation and Business Logic checks we're already implementing [...]:

customers.csv — 120 issues total:
- 50 NULL email (completeness) — unchanged
- 10 duplicate customer_id (uniqueness) — unchanged
- 40 malformed email format [...] (type validation) — new
- 20 future-dated signup_date [...] (type validation) — new

orders.csv — 580 issues total:
- 100 NULL customer_id — unchanged
- 200 NULL product_id — unchanged
- 50 orphan customer_id — unchanged
- 30 orphan product_id — unchanged
- 20 duplicate order_id — unchanged
- 60 zero or negative quantity (type validation) — new
- 50 negative unit_price (type validation) — new
- 40 rows where total_amount != quantity * unit_price (business logic) — new
- 30 rows where payment_date is before order_date (business logic) — new

[...] Update the document accordingly: revise FR-04/FR-05, add new FR items,
revise G-03 and A-03, update A-12 and A-13, update Phase 1 'done looks like',
update DATA_GENERATION_NOTES.md proposed structure."

**AI RESPONSE SUMMARY:**
Applied all requested changes to `requirements-analysis.md` across six sections:

- **FR-04** expanded into a categorised bullet list (4 customer issue types, total
  120 rows); added FR-04a (malformed email must be syntactically invalid for regex
  detection) and FR-04b (future dates must be ≥ 1 day beyond generation date)
- **FR-05** expanded into a 9-bullet categorised list (580 orders rows); added
  FR-05a through FR-05d specifying exact generation constraints for each new
  category (zero/negative quantity, negative price, arithmetic mismatch with
  >0.01 tolerance, payment_date rows must have `order_status = 'Completed'`)
- **Grand total** stamped inline: 120 + 580 + 0 = 700 distinct affected rows, no
  intentional overlap
- **G-03** reframed: "~700" was never a miscalculation — it was an incomplete
  enumeration that assumed type-validation and business-logic seeds which the
  document implicitly required. Corrected defect rates: ~0.63% across all rows
  (700/110,500), 0.58% within orders (580/100,000)
- **A-03** resolution updated: 700 is now the locked authoritative figure
- **A-08** updated: future-dated signup_date is now explicitly seeded (20 rows,
  FR-04b), not an optional defensive check
- **A-12** flipped from "not seeded, defensive-only" to "explicitly seeded":
  60 zero/negative-quantity rows and 50 negative-price rows are real test cases;
  tolerance rule `abs(total_amount − quantity × unit_price) > 0.01` locked in
- **A-13** flipped: 40 intentional arithmetic mismatch rows are the primary test
  cases for `05_quality_business_logic.py`
- **A-18** expanded: now documents both business logic cases (completed order with
  NULL payment, and payment before order); 30 seeded rows (FR-05d) are the true
  positives for case (b)
- **Phase 1 "Done looks like"** replaced with a 13-row verification table mapping
  every issue category to its expected count and the Silver check it seeds
- **DATA_GENERATION_NOTES.md proposed structure** in section 4 updated to describe
  thirteen sections (one per category), in the order the generator introduces them
- **FR-06** updated to reference thirteen sections (corrected from an inadvertent
  "nine sections" in an intermediate draft)

**YOUR EVALUATION:**
✓ Accepted:
- The full 700-row breakdown as specified — all 13 categories, all counts, no
  overlap constraint
- The reframing of G-03: the 460 was incomplete, not wrong; the ~700 figure in the
  assessment document is now internally consistent with the full check scope
- FR-04a and FR-04b constraints (regex-detectable malformed emails; minimum 1-day
  future offset for signup_date)
- FR-05a through FR-05d generation constraints, especially FR-05d's requirement
  that payment_date-before-order_date rows have `order_status = 'Completed'`
- The Phase 1 verification table as the literal definition of done for that phase
- The thirteen-section DATA_GENERATION_NOTES.md structure

✗ Changed:
- None — all changes were applied exactly as specified

✗ Rejected:
- None

**FINAL DECISION:** `requirements-analysis.md` updated with the 700-row defect
target locked across 13 categories; G-03 reframed as a resolved gap; A-08, A-12,
A-13, A-18 updated to reflect explicitly seeded test cases; Phase 1 "done looks
like" upgraded to a full verification table.

---

## Prompt 5: Establish real-time AI prompt history logging workflow

**PROMPT SENT:**
"From this point forward in our work on this project, I need you to actively
maintain the AI prompt history deliverable as we go [...] Every time we complete a
significant exchange [...] do the following automatically, without me having to ask:
1. Determine which file the exchange belongs in [per defined mapping]
2. Append a new entry using exactly [the specified format]
3. Number entries sequentially within each file
4. If I haven't explicitly told you what was accepted/changed/rejected after you
   propose something, ask me directly — do not guess or fabricate my evaluation
5. If I accept something fully with no changes, still log it
6. Before we move from one task to the next, proactively remind me: 'Should I log
   this exchange to ai-prompts/[file].md before we continue?'
7. Do not silently skip logging because something seems minor
[...] Confirm you understand this workflow, then apply it starting with our most
recent exchange (the 700-row defect count revision) — log that one now [...] and
all from the first prompt."

**AI RESPONSE SUMMARY:**
Confirmed the logging workflow in full. Created `ai-prompts/requirement-analysis.md`
with five sequential entries covering all exchanges in this session:
- Prompt 1: Initial nine-section planning request and full plan output
- Prompt 2: Save plan to requirements-analysis.md
- Prompt 3: Six corrections (Free Edition, Unity Catalog Volumes, two-tier testing,
  git tags, percentage math fix, OQ resolutions)
- Prompt 4: 700-row defect target extension across 13 categories
- Prompt 5: This entry — establishing the ongoing logging workflow

**YOUR EVALUATION:**
_Pending your review of this log file. Please confirm: (a) the format is correct,
(b) the evaluation sections for Prompts 1–4 accurately reflect your actual
judgments, and (c) anything that should be corrected before we proceed to Phase 0
scaffolding._

**FINAL DECISION:** Logging workflow established and active from this point forward.
`ai-prompts/requirement-analysis.md` initialised with all five planning-phase
entries.
