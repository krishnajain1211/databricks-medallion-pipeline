# Databricks Medallion Pipeline — Full Planning Document

> **Note:** This document was produced as a collaborative planning exercise with Cursor AI before any code was written. It serves as the `requirements-analysis.md` submission artifact and as the source material for `ai-prompts/requirement-analysis.md`. All gaps, locked assumptions, and open questions were identified through careful reading of `docs/assessment-requirements.md` and the project rules in `.cursor/rules/`.

---

## 1. Understanding Check

An e-commerce company generates daily sales data across three source systems: a customer database, an order management system, and a product catalog. That data lands as CSV files (on S3 or DBFS) and must be made reliable and analytics-ready through a three-layer pipeline built in Databricks.

- **Bronze** — faithful raw ingestion: CSVs land as Delta tables with zero transformation. Every source row is preserved exactly as received, plus ingestion metadata (timestamp, row count, source file name). Nothing is cleaned or judged here.
- **Silver** — trust and governance: four data quality checks run against the raw data. Rows that fail any check are **not removed**; instead, a `quality_check_result` column is stamped on every row (e.g., `PASSED`, `FAILED_COMPLETENESS`, `FAILED_UNIQUENESS`, etc.) so downstream consumers know exactly what to trust. A quality metrics report is produced showing the pass-rate for each check.
- **Gold** — business intelligence: Silver data (good rows only, filtered by `quality_check_result`) is aggregated into four analyst-facing tables: Sales by Product, Revenue by Customer, Daily/Weekly Trends, and Customer Segmentation. These tables feed directly into dashboards.
- **Dashboard** — three or more Databricks SQL visualizations (a bar chart of top-10 products by revenue, a revenue-distribution histogram, and a customer-segmentation pie chart) built on top of Gold tables.

The submission is simultaneously a working pipeline AND an evidence portfolio of how AI was used throughout — requirement analysis, design, code generation, testing, debugging, and reflection all documented with full prompt history.

---

## 2. Full Requirement Extraction

### 2.1 Functional Requirements

**Data Generation**
- FR-01: Generate `customers.csv` with 10,000 rows; schema: `customer_id` (INT PK), `customer_name` (STRING), `email` (STRING), `country` (STRING), `signup_date` (DATE), `customer_segment` (Premium/Standard/Basic), `lifetime_value` (DECIMAL).
- FR-02: Generate `orders.csv` with 100,000 rows; schema: `order_id` (INT PK), `customer_id` (INT FK), `order_date` (DATE), `product_id` (INT FK), `quantity` (INT), `unit_price` (DECIMAL), `total_amount` (DECIMAL), `order_status` (Pending/Completed/Cancelled), `payment_date` (DATE, nullable).
- FR-03: Generate `products.csv` with 500 rows; schema: `product_id` (INT PK), `product_name` (STRING), `category` (STRING), `price` (DECIMAL), `cost` (DECIMAL), `stock_quantity` (INT), `reorder_level` (INT).
- FR-04: Intentionally embed in `customers.csv` — **120 total affected rows**, no overlap between categories:
  - 50 rows with NULL `email` — seeds Completeness check (FR-14)
  - 10 rows with duplicate `customer_id` — seeds Uniqueness check (FR-15)
  - 40 rows with malformed `email` format (missing `@`, or domain without a `.` suffix) — seeds Type Validation check (FR-16)
  - 20 rows with `signup_date` > today (future-dated) — seeds Type Validation check (FR-16)
- FR-04a: The 40 malformed-email rows must be syntactically invalid (e.g., `userexample.com`, `user@`, `@domain`) so the Type Validation check can detect them with a regex rule, not just a NULL check.
- FR-04b: The 20 future-dated `signup_date` rows must use dates at least one day beyond the generation date so temporal boundary checks are unambiguous.
- FR-05: Intentionally embed in `orders.csv` — **580 total affected rows**, no overlap between categories:
  - 100 rows with NULL `customer_id` — seeds Completeness check (FR-14)
  - 200 rows with NULL `product_id` — seeds Completeness check (FR-14)
  - 50 rows with `customer_id` not in the customers table — seeds Referential Integrity check (FR-17)
  - 30 rows with `product_id` not in the products table — seeds Referential Integrity check (FR-17)
  - 20 duplicate `order_id` rows — seeds Uniqueness check (FR-15)
  - 60 rows with zero or negative `quantity` (e.g., 0, −1, −5) — seeds Type Validation check (FR-16)
  - 50 rows with negative `unit_price` (e.g., −9.99) — seeds Type Validation check (FR-16)
  - 40 rows where `total_amount ≠ quantity × unit_price` (intentional arithmetic mismatch) — seeds Business Logic check (`05_quality_business_logic.py`)
  - 30 rows where `payment_date` < `order_date` (payment before the order was placed) — seeds Business Logic check (`05_quality_business_logic.py`)
- FR-05a: The 60 zero/negative-quantity rows must have `quantity ≤ 0`; paired `total_amount` values are also set inconsistently to ensure they also trigger the business logic check — but these rows are counted only once in the 580 total (no double-counting in the row tally).
- FR-05b: The 50 negative-`unit_price` rows have `unit_price < 0`; `total_amount` is similarly set to a negative value.
- FR-05c: The 40 `total_amount` mismatch rows have valid positive `quantity` and `unit_price` but `total_amount` is deliberately set to `quantity × unit_price ± a non-zero delta` (e.g., off by 10).
- FR-05d: The 30 `payment_date < order_date` rows have both dates populated and `order_status = 'Completed'` so they also stress-test the A-18 payment-date nullability assumption.
- **Grand total: 120 (customers) + 580 (orders) + 0 (products) = 700 distinct affected rows**, matching the assessment document's stated figure exactly.
- FR-06: Document data generation decisions in `src/data_generation/DATA_GENERATION_NOTES.md`, with one section per issue category (thirteen sections total — see section 4 for proposed structure).

**Bronze Layer**
- FR-07: Read all three CSVs from Unity Catalog Volumes into Databricks (canonical path: `/Volumes/workspace/ecommerce_medallion/raw_data/`).
- FR-08: Create three Bronze Delta tables (`bronze_customers`, `bronze_orders`, `bronze_products`) with raw, unchanged data.
- FR-09: Handle schema inference and explicit data-type mapping.
- FR-10: Log ingestion metadata per run: row count, source file path, ingestion timestamp.
- FR-11: No transformations — pure ingest only.
- FR-12: Provide both individual ingest scripts (`01_ingest_customers.py`, `02_ingest_orders.py`, `03_ingest_products.py`) and an orchestrating `ingest_all.py`.

**Silver Layer**
- FR-13: Implement four data quality checks (see Gap G-01 for count resolution).
- FR-14: Check 1 — Completeness: flag rows with NULL in critical fields (`email` for customers; `customer_id`, `product_id` for orders).
- FR-15: Check 2 — Uniqueness: flag rows with duplicate `order_id` (orders) or duplicate `customer_id` (customers).
- FR-16: Check 3 — Type Validation: flag rows where field values cannot be coerced to their declared types (e.g., non-numeric in numeric fields, invalid date formats, out-of-enum categorical values).
- FR-17: Check 4 — Referential Integrity: flag orders rows where non-NULL `customer_id` has no match in customers, or non-NULL `product_id` has no match in products.
- FR-18: Never delete flagged rows; stamp `quality_check_result` column on every row.
- FR-19: Produce a quality metrics report showing % passed for each check.
- FR-20: `create_silver_tables.py` orchestrates all checks into final Silver Delta tables.

**Gold Layer**
- FR-21: Produce aggregation table A — `gold_sales_by_product`: `product_id`, `product_name`, `category`, `total_orders`, `total_revenue`, `avg_order_value`.
- FR-22: Produce aggregation table B — `gold_revenue_by_customer`: `customer_id`, `customer_name`, `customer_segment`, `total_orders`, `total_revenue`, `avg_order_value`, `lifetime_value_actual`.
- FR-23: Produce aggregation table C — `gold_daily_weekly_trends`: daily and weekly revenue trends (implied by `03_daily_weekly_trends.sql` in the repo tree).
- FR-24: Produce aggregation table D — `gold_customer_segmentation`: `segment_type` (High-Value/Repeat/One-Time/Inactive), `customer_count`, `avg_revenue`, `total_revenue`.
- FR-25: `create_gold_tables.py` orchestrates all four Gold tables.
- FR-26: Aggregation calculations must be correct (SUM, COUNT, AVG verified against source).

**Dashboard**
- FR-27: Minimum 3 Databricks SQL Dashboard tiles.
- FR-28: Visualization 1 — Top 10 products by revenue (bar chart), sourced from `gold_sales_by_product`.
- FR-29: Visualization 2 — Customer revenue distribution (histogram), sourced from `gold_revenue_by_customer`.
- FR-30: Visualization 3 — Customer segmentation breakdown (pie chart), sourced from `gold_customer_segmentation`.
- FR-31: Write all queries in `src/dashboard/dashboard_queries.sql`.
- FR-32: Produce `DASHBOARD_GUIDE.md` with setup instructions for the dashboard.

**Testing**
- FR-33: Two-tier automated testing approach (see OQ-04 resolution in section 9).
- FR-34: Tier 1 — pandas-based unit tests (run locally via pytest, no Databricks connection required): replicate the quality-check logic using pandas DataFrames loaded from the committed CSVs in `data/`. Each check asserts it detects at least the expected number of seeded failures (e.g., ≥50 NULL email rows caught by the completeness check). Fast, CI-friendly, and runnable by any reviewer.
- FR-35: Tier 2 — Databricks integration notebook: a notebook run against the live Silver Delta tables in the Free Edition workspace that validates `quality_check_result` distributions, row counts per layer, and spot-checks aggregation math in Gold. This is the authoritative proof that the pipeline produces correct output on real infrastructure.

**Database / Schema**
- FR-36: Provide `database/schema.sql` with CREATE TABLE statements for all Bronze/Silver/Gold tables.
- FR-37: `database/setup-notes.md` with instructions for initialising the Databricks environment.
- FR-38: `database/seed-data-notes.md` documenting the seed data approach.

### 2.2 Non-Functional Requirements

- NFR-01: Code must be clean, readable, and commented with docstrings/header comments on every function and script.
- NFR-02: Consistent `snake_case` naming for all Python identifiers, SQL objects, and file names.
- NFR-03: `README.md` setup instructions must work end-to-end (someone else must be able to clone and run).
- NFR-04: No real PII — all data is synthetic.
- NFR-05: Every non-trivial architectural decision must be documented (not silently made).
- NFR-06: Code must be production-quality, suitable for an internal design review.
- NFR-07: Prompt history (including rejections and revisions) is a mandatory deliverable, not optional.
- NFR-08: Full lifecycle artifacts required: requirement analysis, design notes, test strategy, debugging notes, reflection.
- NFR-09: Time constraint: core pipeline scoped for 20–25 focused hours; remaining time goes into artifacts.
- NFR-10: Environment: Databricks Free Edition (serverless), not Community Edition — Community Edition was retired January 1, 2026.

### 2.3 Acceptance Criteria (verbatim from document, with gap annotations)

- [ ] Sample data generated (3 CSVs with intentional issues)
- [ ] Bronze layer ingests all three sources successfully
- [ ] Silver layer implements all four quality checks *(see Gap G-01 below)*
- [ ] Quality report shows % passed for each check
- [ ] Gold layer produces all three aggregation tables *(see Gap G-02 below)*
- [ ] Aggregation calculations are correct (sum, count, avg, etc.)
- [ ] Dashboard displays all 3+ visualizations
- [ ] All code is readable, commented, documented
- [ ] README setup instructions work end-to-end
- [ ] Data quality tests pass (verify checks catch intentional issues)

### 2.4 Gaps, Inconsistencies, and Contradictions — with Resolutions

**Gap G-01: Silver layer check count — "4" vs. 5 repo files**

The Core Logic section says "Implement below quality checks" and lists Completeness, Uniqueness, Referential Integrity, and flagging (a mechanism, not a distinct check). Acceptance criteria say "all four quality checks." The common technical requirements also say "all 4 quality checks." But the repo tree shows five Silver files: `01_quality_completeness.py`, `02_quality_uniqueness.py`, `03_quality_type_validation.py`, `04_quality_referential_integrity.py`, `05_quality_business_logic.py`. The data-quality-strategy template only defines three checks (Completeness, Uniqueness, Referential Integrity).

**Resolution (locked assumption A-01):** We implement exactly four named quality checks — Completeness, Uniqueness, Type Validation, Referential Integrity — matching both the "4 checks" requirement and the four most meaningful files in the repo tree. `05_quality_business_logic.py` is kept in the structure but scoped as an optional extension (e.g., `total_amount == quantity × unit_price` cross-field check) that does not block acceptance criteria. The data-quality-strategy template will be updated to list all four checks.

---

**Gap G-02: Gold layer aggregation count — "4 aggregations" vs. "all three aggregation tables"**

The Common Technical Requirements bullet says "Gold layer aggregation code (all 4 aggregations)." The repo tree contains four SQL files (including `03_daily_weekly_trends.sql`). But the Core Logic section only describes three named aggregations (A, B, C), and the Acceptance Criteria say "all three Gold layer aggregations."

**Resolution (locked assumption A-02):** We implement all four aggregation tables, matching the repo structure and the "4 aggregations" language in Common Technical Requirements. The Acceptance Criteria use of "three" is a stale copy from an earlier draft. Daily/weekly trends (table C) is the fourth, and its absence would leave a gap in the dashboard story. All four are delivered; self-assessment will check off the "three aggregations" criterion after confirming three of the four are complete, then flag the fourth as implemented beyond minimum.

---

**Gap G-03: "~700 problematic rows" — apparent mismatch resolved by extending seed coverage**

The document states "Total issues: ~700 problematic rows out of ~100,000 (0.7% — realistic data quality)." The originally enumerated specific counts (completeness + uniqueness + referential integrity only) totalled: customers — 50 + 10 = 60; orders — 100 + 200 + 50 + 30 + 20 = 400; grand total = 460. This looked like a documentation error. However, the gap disappears once type-validation and business-logic seed rows are included — which the assessment document implicitly assumed because it specifies Silver layer checks for exactly those categories.

**Resolution (locked assumption A-03):** The "~700" figure is internally consistent with the full scope of quality checks required. The 460 count only covered completeness, uniqueness, and referential integrity; it was an incomplete enumeration, not a miscalculation. By extending seed data to also cover type-validation (malformed email, future signup_date, zero/negative quantity, negative unit_price) and business-logic (total_amount mismatch, payment_date before order_date) failures, the total reaches exactly 700 across distinct rows with no intentional overlap: 120 (customers) + 580 (orders) + 0 (products) = 700. The actual defect rate is ~0.63% across all source rows (700 / 110,500), or 0.58% within orders specifically (580 / 100,000) — both consistent with the document's "realistic data quality" framing. This resolution is locked.

---

**Gap G-04: `tool-specific/cursor-workflow/` folder absent from repo tree**

Section 10 (Tool-Specific Expectations for Cursor) requires submitting `tool-specific/cursor-workflow/` with four files. The repo tree in section 8 does not include this folder.

**Resolution (locked assumption A-04):** Add `tool-specific/cursor-workflow/` to the repo scaffold as a top-level folder, not nested under `src/` or `docs/`. The existing `cursor-rules-or-instructions.md` already lives there.

---

**Gap G-05: No submission templates for `README.md`, `data-model.md`, `debugging-notes.md`, `final-ai-usage-summary.md`**

These four files appear in the repo tree but have no template provided in section 9.

**Resolution (locked assumption A-05):** Propose a sensible structure for each (see section 4 below). They will be scaffolded before any code phase begins so that filling them in is a matter of incremental updates, not a last-minute dump.

---

**Gap G-06: No `tests/` directory in the repo tree, despite testing being an acceptance criterion**

The acceptance criteria require a "basic test suite" and "data quality tests that pass," but the repo tree has no `tests/` folder.

**Resolution (locked assumption A-06):** Add `tests/` as a top-level directory with `test_data_quality.py` and `test_transformations.py`. This is the standard Python convention and reviewers will expect it.

---

**Gap G-07: `data-quality-strategy.md` template defines only three checks**

The template in section 9 lists Completeness, Uniqueness, and Referential Integrity — not Type Validation.

**Resolution:** Consistent with A-01, the `data-quality-strategy.md` we create will document all four checks.

---

**Gap G-08: Gold customer tables excluded legitimate orders by filtering on customer-level quality_check_result**

*Discovered: 2026-08-09 during Phase 4 — caught by the FR-26 revenue cross-check built into `create_gold_tables.py`.*

The initial implementation of `02_revenue_by_customer.sql` and `04_customer_segmentation.sql` filtered `WHERE silver_customers.quality_check_result = 'PASSED'` before joining to PASSED orders. This silently dropped ~120 customers whose records had record-level defects (NULL email, malformed email, duplicate customer_id) even though those customers' individual orders had passed all order-level quality checks. The result was a $635,295.88 revenue shortfall in `gold_revenue_by_customer` vs. `gold_sales_by_product` — both should sum to the same Silver PASSED total. `gold_sales_by_product` matched exactly because it aggregates by product and never touches the customer table.

**Root cause:** The Silver layer's data quality philosophy (flag bad rows, never delete) means a customer record with a bad email is still a real customer. Their orders are processed and can be perfectly valid. Filtering the Gold *customer dimension* by the customer record's quality_check_result conflated record-level data quality with customer existence — a business logic error, not a data quality rule.

**Resolution:** Replace `WHERE c.quality_check_result = 'PASSED'` with a `ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY customer_id)` CTE that deduplicates `silver_customers` on `customer_id` (collapsing the 20 seeded C-02 duplicate rows to one canonical record) and includes ALL unique customers regardless of their record's quality result. The orders side of the join remains filtered to `quality_check_result = 'PASSED'`. Applied to both `02_revenue_by_customer.sql` and `04_customer_segmentation.sql`.

**Lesson:** Cross-checks like FR-26 should be built into orchestrators from the start — this bug would have gone undetected without the revenue conservation assertion in `create_gold_tables.py`.

---

## 3. Assumptions and Edge Cases

**A-01 through A-06** are locked assumptions from Gap analysis above.

**A-07 — Currency:** No currency field exists in any table. All monetary values (`price`, `cost`, `unit_price`, `total_amount`, `lifetime_value`) are assumed to be in a single currency (USD). No currency conversion logic is needed. This is noted in `data-model.md`.

**A-08 — Timezone handling:** `order_date`, `signup_date`, and `payment_date` are stored as DATE (not TIMESTAMP). No timezone conversion is required. All dates are treated as wall-clock dates in the local timezone of the generating system. Future-dated `signup_date` is now explicitly seeded (20 rows, FR-04b) and caught by the Type Validation check. Future-dated `order_date` is not seeded but the Type Validation check will defensively flag it if encountered.

**A-09 — Duplicate row resolution:** When the uniqueness check detects duplicate `order_id` rows (20 seeded), ALL copies of the duplicate are flagged with `FAILED_UNIQUENESS` — not just the second occurrence. Downstream Gold tables filter to `quality_check_result = 'PASSED'` rows, so no duplicate record survives into Gold. This is the conservative choice; the alternative (keep-first-drop-rest) would silently alter data. Flagging all copies is auditable.

**A-10 — Multiple issues on the same row:** A row can fail more than one check (e.g., an orders row with both NULL `customer_id` and a duplicate `order_id`). The `quality_check_result` column will store a comma-delimited list of all failed checks (e.g., `FAILED_COMPLETENESS,FAILED_UNIQUENESS`). Rows that pass all checks get `PASSED`. This is more informative than a single-failure flag.

**A-11 — Referential integrity check scope:** The orphan check (orders rows where `customer_id` is not in the customers table) must only test rows where `customer_id` is not NULL. A NULL `customer_id` is a separate completeness failure. The two issues are seeded independently and must be checked independently to avoid double-counting. Same logic applies to `product_id`.

**A-12 — Negative quantities and prices (now explicitly seeded):** `generate_sample_data.py` will seed 60 rows with `quantity ≤ 0` and 50 rows with `unit_price < 0` in `orders.csv` (FR-05a, FR-05b). These are real test cases for the Type Validation check (`03_quality_type_validation.py`), not just defensive guards. The check flags `FAILED_TYPE_VALIDATION` on any row where `quantity ≤ 0` or `unit_price < 0`. No negative-quantity or negative-price rows are seeded in `products.csv` or `customers.csv`.

**A-13 — `total_amount` consistency (now explicitly seeded):** `generate_sample_data.py` will seed 40 rows in `orders.csv` where `total_amount ≠ quantity × unit_price` by a deliberate non-zero delta (FR-05c). These rows are valid in all other respects (positive quantity, positive price) and are the primary test cases for `05_quality_business_logic.py`. The check flags `FAILED_BUSINESS_LOGIC` on any row where `abs(total_amount − quantity × unit_price) > 0.01` (a small tolerance for floating-point rounding). This check is in addition to the four named quality checks and does not affect the acceptance criteria count (A-01).

**A-14 — Data file paths (resolved OQ-02):** Databricks Free Edition uses Unity Catalog Volumes as the native, production-supported storage layer for unmanaged files. Legacy `dbfs:/FileStore/...` paths are not used. All CSV source files are staged at `/Volumes/workspace/ecommerce_medallion/raw_data/` (e.g., `/Volumes/workspace/ecommerce_medallion/raw_data/customers.csv`) before Bronze ingestion. A single `BASE_VOLUME_PATH` configuration constant at the top of each ingest script keeps the path swappable without touching transform logic. This is the current Free Edition-native pattern and reads correctly in a production design review.

**A-15 — `generate_sample_data.py` runtime:** This script runs locally (not on Databricks) and uses `pandas` + `faker` to generate the CSVs. It does not require PySpark. The generated files are committed to `data/` and uploaded to the Unity Catalog Volume path (`/Volumes/workspace/ecommerce_medallion/raw_data/`) before Bronze ingestion runs.

**A-16 — Null handling precedence:** When multiple checks could flag the same row (e.g., both completeness and referential integrity), the `quality_check_result` column lists all applicable failure codes (A-10). No precedence hierarchy — all failures are recorded.

**A-17 — `customer_segment` and `order_status` validation:** These are categorical fields with defined enumerations. Type validation will check that values fall within the allowed set. This is part of the Type Validation check (FR-16).

**A-18 — `payment_date` nullability and temporal validity:** `payment_date` is nullable by schema design (Pending orders have no payment date). NULL `payment_date` is NOT a completeness failure. Two business logic cases are checked: (a) `order_status = 'Completed'` and `payment_date IS NULL` — completed order with no payment record; (b) `payment_date < order_date` — payment recorded before the order existed. Case (b) is explicitly seeded in 30 rows (FR-05d), all with `order_status = 'Completed'`, making them true positive test cases for the business logic check. Both cases produce `FAILED_BUSINESS_LOGIC` in `quality_check_result`.

---

## 4. Full Repository Scaffold

```
databricks-medallion-pipeline/
├── README.md                               # expanded from stub
├── candidate-info.md                       # from template in doc s.9
├── tool-workflow.md                        # Part A — AI Workflow Foundation
├── requirements-analysis.md               # this file
├── design-notes.md                        # from template in doc s.9
├── data-model.md                          # proposed structure below
├── data-quality-strategy.md               # 4-check version
│
├── src/
│   ├── data_generation/
│   │   ├── generate_sample_data.py
│   │   └── DATA_GENERATION_NOTES.md
│   ├── bronze/
│   │   ├── 01_ingest_customers.py
│   │   ├── 02_ingest_orders.py
│   │   ├── 03_ingest_products.py
│   │   └── ingest_all.py
│   ├── silver/
│   │   ├── 01_quality_completeness.py
│   │   ├── 02_quality_uniqueness.py
│   │   ├── 03_quality_type_validation.py
│   │   ├── 04_quality_referential_integrity.py
│   │   ├── 05_quality_business_logic.py   # optional 5th, additive
│   │   └── create_silver_tables.py
│   ├── gold/
│   │   ├── 01_sales_by_product.sql
│   │   ├── 02_revenue_by_customer.sql
│   │   ├── 03_daily_weekly_trends.sql
│   │   ├── 04_customer_segmentation.sql
│   │   └── create_gold_tables.py
│   └── dashboard/
│       ├── dashboard_queries.sql
│       └── DASHBOARD_GUIDE.md
│
├── data/
│   ├── customers.csv
│   ├── orders.csv
│   └── products.csv
│
├── database/
│   ├── schema.sql
│   ├── seed-data-notes.md
│   └── setup-notes.md
│
├── tests/
│   ├── test_data_quality.py               # proves checks catch seeded issues
│   └── test_transformations.py            # unit tests on transformation logic
│
├── docs/
│   └── assessment-requirements.md         # already exists
│
├── debugging-notes.md
├── reflection.md
├── final-ai-usage-summary.md
│
├── ai-prompts/
│   ├── requirement-analysis.md            # prompt log for this conversation
│   ├── data-generation.md
│   ├── bronze-layer.md
│   ├── silver-layer.md
│   ├── gold-layer.md
│   ├── dashboard.md
│   ├── debugging.md
│   └── documentation.md
│
└── tool-specific/
    └── cursor-workflow/
        ├── project-context.md
        ├── spec.md
        ├── cursor-rules-or-instructions.md  # already exists
        └── task-breakdown.md
```

### Proposed structure for files without templates

**`README.md`** — `# Setup`, Environment prerequisites (Databricks Free Edition, Python 3.x, pandas, faker), Unity Catalog Volumes upload steps, run order (data_generation → bronze → silver → gold → dashboard), expected outputs per phase, known limitations.

**`data-model.md`** — ERD description (text-based, plus Mermaid diagram), field-level data dictionary for all three source tables, layer-by-layer row counts (Bronze = raw count, Silver = raw + quality_check_result column, Gold = aggregated counts), lineage notes (which Silver columns feed which Gold fields).

**`src/data_generation/DATA_GENERATION_NOTES.md`** — Thirteen sections, one per seeded issue category, each containing: count, target field(s), generation method (e.g., "randomly replaced with None using `df.sample(50).email = None`"), which Silver check is designed to catch it, and any edge-case notes (e.g., "malformed emails are syntactically invalid, not just unusual — confirmed with regex before committing"). Sections in order:
1. NULL email (50 rows) — Completeness
2. Duplicate customer_id (10 rows) — Uniqueness
3. Malformed email format (40 rows) — Type Validation
4. Future-dated signup_date (20 rows) — Type Validation
5. NULL customer_id in orders (100 rows) — Completeness
6. NULL product_id in orders (200 rows) — Completeness
7. Orphan customer_id in orders (50 rows) — Referential Integrity
8. Orphan product_id in orders (30 rows) — Referential Integrity
9. Duplicate order_id (20 rows) — Uniqueness
10. Zero/negative quantity (60 rows) — Type Validation
11. Negative unit_price (50 rows) — Type Validation
12. total_amount mismatch (40 rows) — Business Logic
13. payment_date before order_date (30 rows) — Business Logic

**`debugging-notes.md`** — Chronological log of issues encountered during development, structured as: date, symptom, root cause, fix applied, what I learned. One entry per meaningful debugging session.

**`final-ai-usage-summary.md`** — Executive summary of how AI was used end-to-end: tool used, percentage of code AI-generated vs. human-written, best prompts, worst prompts, what AI got wrong, what checks caught it, lessons for reuse in real production pipelines.

---

## 5. Prompt History Logging Plan

### File-to-activity mapping

| File | Captures |
|---|---|
| `ai-prompts/requirement-analysis.md` | This planning conversation and any follow-up requirement clarifications |
| `ai-prompts/data-generation.md` | All prompts related to `generate_sample_data.py` |
| `ai-prompts/bronze-layer.md` | Bronze ingest scripts, schema inference, metadata logging |
| `ai-prompts/silver-layer.md` | All five Silver quality check scripts, create_silver_tables.py |
| `ai-prompts/gold-layer.md` | All four Gold SQL scripts, create_gold_tables.py |
| `ai-prompts/dashboard.md` | Dashboard queries, DASHBOARD_GUIDE.md |
| `ai-prompts/debugging.md` | Any debugging session (wrong row counts, type errors, Databricks connectivity, test failures) |
| `ai-prompts/documentation.md` | tool-workflow.md, reflection.md, design-notes.md, any AI-assisted doc drafting |

### Entry format (consistent across all files)

```markdown
## Prompt N: [Short title]

**PROMPT SENT:**
[Full prompt text, or verbatim summary if very long]

**AI RESPONSE SUMMARY:**
[What Cursor generated — key decisions, code shape, any notable choices]

**YOUR EVALUATION:**
✓ Accepted:
- [Specific things that were correct and why]

✗ Changed:
- [What was wrong and how you fixed it, with reasoning]

✗ Rejected:
- [What was discarded and why it didn't fit the architecture]

**FINAL DECISION:** [One sentence: what was used, modified, or discarded]
```

### Reminder commitment

After every significant exchange (new script, new quality check, a debugging session, a design decision), I will proactively prompt you to log an entry in the appropriate `ai-prompts/*.md` file before we move on to the next task. I will not wait for you to ask. This applies even when the result is fully accepted — the absence of rejection evidence is itself useful for the evaluator.

---

## 6. Phased, Checkpoint-Based Build Plan

### Phase 0 — Foundation (2–3 hours)
**What:** Create the full repo scaffold (all folders and placeholder files), fill in `candidate-info.md`, expand `README.md` to a working skeleton, write `requirements-analysis.md` from this planning output, write `design-notes.md` and `data-model.md` (high-level sections, filled in incrementally), scaffold all `ai-prompts/*.md` files, fill in `tool-specific/cursor-workflow/` files (`project-context.md`, `spec.md`, `task-breakdown.md`), log this conversation in `ai-prompts/requirement-analysis.md`.

**Done looks like:** Running `git status` shows a clean, fully-structured repo with all placeholder files committed. No code yet.

**Acceptance criteria satisfied:** None yet (artifacts only). But the evaluator can see structured thinking from day one.

---

### Phase 1 — Data Generation (2–3 hours)
**What:** Write and run `src/data_generation/generate_sample_data.py`. Generate all three CSVs with correct row totals and all nine seeded issue categories. Commit CSVs to `data/`. Write `DATA_GENERATION_NOTES.md`. Log in `ai-prompts/data-generation.md`.

**Done looks like:** Three CSVs committed. A verification script (or manual pandas check) confirms all nine defect categories hit their exact counts with no cross-category overlap:

| File | Issue category | Expected count | Check it seeds |
|---|---|---|---|
| customers.csv | NULL email | 50 | Completeness |
| customers.csv | Duplicate customer_id | 10 | Uniqueness |
| customers.csv | Malformed email format | 40 | Type Validation |
| customers.csv | Future-dated signup_date | 20 | Type Validation |
| orders.csv | NULL customer_id | 100 | Completeness |
| orders.csv | NULL product_id | 200 | Completeness |
| orders.csv | Orphan customer_id | 50 | Referential Integrity |
| orders.csv | Orphan product_id | 30 | Referential Integrity |
| orders.csv | Duplicate order_id | 20 | Uniqueness |
| orders.csv | Zero/negative quantity | 60 | Type Validation |
| orders.csv | Negative unit_price | 50 | Type Validation |
| orders.csv | total_amount mismatch | 40 | Business Logic |
| orders.csv | payment_date before order_date | 30 | Business Logic |
| **Total** | | **700** | |

`DATA_GENERATION_NOTES.md` has one section per issue category documenting the count, how it was introduced, and which Silver check it is designed to trigger.

**Acceptance criteria satisfied:** "Sample data generated (3 CSVs with intentional issues)."

---

### Phase 2 — Bronze Layer (2–3 hours)
**What:** Write `01_ingest_customers.py`, `02_ingest_orders.py`, `03_ingest_products.py`, and `ingest_all.py`. Write `database/schema.sql` with Bronze CREATE TABLE statements using the three-level Unity Catalog namespace (`workspace.ecommerce_medallion.<table>`). Write `database/setup-notes.md`. Upload CSVs to `/Volumes/workspace/ecommerce_medallion/raw_data/`, run ingestion notebooks, verify row counts match source CSVs. Log in `ai-prompts/bronze-layer.md`.

**Done looks like:** Three Bronze Delta tables exist in Databricks. Row counts match the source CSVs exactly. Ingestion metadata table shows timestamp and file path. Schema SQL can reproduce the tables from scratch.

**Acceptance criteria satisfied:** "Bronze layer ingests all three sources successfully."

---

### Phase 3 — Silver Layer (4–5 hours)
**What:** Write all five Silver scripts (four required checks + business logic bonus). Write `create_silver_tables.py` orchestrator. Produce quality metrics report as a DataFrame or saved Delta table. Update `database/schema.sql` with Silver table definitions. Write `data-quality-strategy.md`. Log in `ai-prompts/silver-layer.md`.

**Done looks like:** Silver tables exist with `quality_check_result` column populated. A query `SELECT quality_check_result, COUNT(*) FROM silver_orders GROUP BY 1` returns distinct failure codes and a PASSED count. Quality report shows % passed for each of the four checks, and the numbers are traceable back to the seeded defect counts.

**Acceptance criteria satisfied:** "Silver layer implements all four quality checks," "Quality report shows % passed for each check."

---

### Phase 4 — Gold Layer (3–4 hours)
**What:** Write all four Gold SQL scripts. Write `create_gold_tables.py` orchestrator. Update `database/schema.sql` with Gold table definitions. Manually verify at least one aggregation (e.g., spot-check one product's `total_revenue` against Silver source rows). Log in `ai-prompts/gold-layer.md`.

**Done looks like:** Four Gold Delta tables exist. Spot-checks on 3–5 rows in each table confirm aggregation math is correct. `data-model.md` updated with lineage from Silver to Gold.

**Acceptance criteria satisfied:** "Gold layer produces all three [four] aggregation tables," "Aggregation calculations are correct."

---

### Phase 5 — Dashboard (2–3 hours)
**What:** Write `dashboard_queries.sql` with 3+ queries. Create the Databricks SQL Dashboard manually (UI-based). Write `DASHBOARD_GUIDE.md` with step-by-step setup. Log in `ai-prompts/dashboard.md`.

**Done looks like:** Dashboard opens in Databricks and renders all three visualizations from live Gold table data. `DASHBOARD_GUIDE.md` allows someone else to recreate it.

**Acceptance criteria satisfied:** "Dashboard displays all 3+ visualizations."

---

### Phase 6 — Testing (2–3 hours)
**What:** Write Tier 1 pandas unit tests — `tests/test_data_quality.py` loads the committed CSVs with pandas and asserts each quality-check function detects at least the expected number of seeded failures; `tests/test_transformations.py` unit tests at least one Gold aggregation function. Both run locally via `pytest` with no Databricks connection. Write the Tier 2 integration notebook (`tests/integration_validation.py` or `.ipynb`) that queries the live Silver and Gold Delta tables in Databricks and validates row counts, `quality_check_result` distributions, and aggregation spot-checks. Log all failures and fixes in `ai-prompts/debugging.md`.

**Done looks like:** `pytest tests/` passes locally with zero failures; output explicitly shows each check's expected vs. found count (e.g., "Completeness: expected ≥50 NULL email, found 50 — PASS"). Tier 2 notebook runs clean in Databricks, with each cell confirming expected row counts and quality distributions against the live Delta tables.

**Acceptance criteria satisfied:** "Data quality tests pass (verify checks catch intentional issues)," "At least one meaningful test tier."

---

### Phase 7 — Lifecycle Artifacts (3–4 hours)
**What:** Fill in `debugging-notes.md` with all issues encountered. Write `reflection.md`. Write `final-ai-usage-summary.md`. Finalise `tool-workflow.md` (Part A). Update all `ai-prompts/*.md` entries. Final README review. Log in `ai-prompts/documentation.md`.

**Done looks like:** Every file in the repo tree is non-empty. Running the repo from a fresh clone produces working Bronze, Silver, Gold tables, and the dashboard loads.

**Acceptance criteria satisfied:** "All code is readable, commented, documented," "README setup instructions work end-to-end," "Full prompt history with all AI interactions documented," all reflection/debugging/analysis artifacts present.

---

## 7. Evaluation-Parameter Mapping

| Evaluation area | Where demonstrated | Coverage strength |
|---|---|---|
| Requirement analysis | This document; gap analysis (G-01 to G-07) with reasoned resolutions | Strong |
| Prompting / context-setting | `ai-prompts/*.md` files showing full prompt → response → evaluation → decision cycle; `.cursor/rules/00-project-context.mdc` | Strong |
| Tool workflow | `tool-specific/cursor-workflow/` (all 4 files); `tool-workflow.md` (Part A) | Strong |
| Pipeline design | `design-notes.md`; `data-model.md`; phased build plan above | Medium-strong — richer once Mermaid diagram is added (P-03) |
| Code quality | Every `src/` script with docstrings, snake_case, header comments; `database/schema.sql` | Strong — enforced by Cursor rules |
| Data quality depth | `data-quality-strategy.md`; all 5 Silver scripts; quality metrics report; tests proving catches | Strong |
| Testing approach | Tier 1: pandas pytest (`tests/test_data_quality.py`, `tests/test_transformations.py`) — runs locally; Tier 2: Databricks integration notebook against live Silver/Gold Delta tables | Strong — two distinct tiers covering local logic and live infrastructure |
| Debugging methodology | `debugging-notes.md`; `ai-prompts/debugging.md`; Phase 6 failures documented | Medium — start logging early |
| Data contracts / schema thinking | `database/schema.sql`; `data-model.md` data dictionary; no explicit inter-layer schema validation yet | **Weak — address with P-01** |
| Documentation | All `.md` artifacts; `DASHBOARD_GUIDE.md`; `DATA_GENERATION_NOTES.md`; `README.md` | Strong |
| Responsible AI judgment | `tool-workflow.md` section on what info is avoided; `ai-prompts/*.md` rejection evidence; no PII | Medium-strong — needs explicit section in `tool-workflow.md` |

**Flag:** Data contracts / schema thinking is the weakest area. Address with polish opportunity P-01 below.

---

## 8. Small Polish Opportunities

**P-01 — Schema contract validation step between Bronze and Silver (HIGH VALUE, ~2 hours)**
Before Silver quality checks run, add a thin schema assertion function in `create_silver_tables.py` (or a standalone `00_schema_contract.py`) that compares the Bronze table schema against the declared expected schema from `database/schema.sql`. If a column is missing or a type has drifted, the run fails fast with a clear error rather than producing silent garbage in Silver. This directly demonstrates data contract / schema thinking — the weakest evaluation area currently — and is a real production pattern.

**P-02 — Data lineage row-count summary in `data-model.md` (~30 minutes)**
Add a table showing row counts at each layer: Bronze (raw), Silver PASSED, Silver FAILED by check type, Gold (aggregated). Update this after each phase. It makes the data quality story immediately readable to a reviewer without having to run the pipeline themselves.

**P-03 — Mermaid architecture diagram in `design-notes.md` (~30 minutes)**
A single Mermaid flowchart showing the Bronze → Silver → Gold → Dashboard flow with the key transformations labeled at each arrow (e.g., "4 quality checks + quality_check_result stamp," "filter PASSED + aggregate"). This is a concrete visual that makes the design review experience much stronger.

**P-04 — Quality metrics summary tile in the dashboard (~1 hour)**
A fourth dashboard tile showing a bar chart of "% rows passing each check" (from a quality metrics Delta table written in Phase 3). This ties the Silver quality work directly into the dashboard story, demonstrates end-to-end thinking, and is a natural data engineering pattern (quality SLA monitoring visible to stakeholders). It only requires one additional SQL query and one additional tile.

---

## 9. Open Questions — All Resolved

**OQ-01 — RESOLVED: Databricks environment edition**
Databricks Community Edition was retired January 1, 2026. The target environment is **Databricks Free Edition** (serverless). All code, documentation, and `candidate-info.md` will use "Free Edition" exclusively. Free Edition executes notebooks and SQL via serverless compute (no cluster management); this is the primary execution mode for all pipeline scripts.

---

**OQ-02 — RESOLVED: Data file paths**
DBFS `FileStore` paths are not used. The canonical data path is Unity Catalog Volumes: `/Volumes/workspace/ecommerce_medallion/raw_data/`. See A-14 for full details and rationale.

---

**OQ-03 — `generate_sample_data.py` runtime (confirmed)**
Runs locally with `pandas` + `faker`; no Databricks connection required. Output CSVs are committed to `data/` and uploaded to the Unity Catalog Volume before Phase 2. The script will not be adapted for Databricks notebooks — keeping it local avoids Databricks library dependencies in the data-generation step and makes it independently runnable by any reviewer.

---

**OQ-04 — RESOLVED: Two-tier testing approach**
- **Tier 1 (local, pytest):** Quality-check logic is reimplemented using pandas in `tests/test_data_quality.py`. Tests load CSVs from `data/`, run the logic, and assert expected failure counts. No Databricks connection. `tests/test_transformations.py` unit tests Gold aggregation functions the same way.
- **Tier 2 (Databricks, integration):** A notebook (`tests/integration_validation.py`) queries the live Silver and Gold Delta tables and validates row counts, `quality_check_result` distributions, and aggregation spot-checks. This is the authoritative end-to-end proof on real infrastructure.

The two-tier split means Tier 1 is always runnable by a reviewer with only Python installed, while Tier 2 demonstrates pipeline correctness in the actual target environment.

---

**OQ-05 — RESOLVED: Unity Catalog three-level namespace**
Unity Catalog's three-level namespace (`catalog.schema.table`) is a constraint of Free Edition, not a choice. Naming convention locked in:
- **Catalog:** `workspace` (the Free Edition default catalog confirmed in the Databricks workspace)
- **Schema:** `ecommerce_medallion` (single schema — layers are distinguished by table-name prefix)
- **Tables:** `bronze_customers`, `bronze_orders`, `bronze_products`, `silver_customers`, `silver_orders`, `gold_sales_by_product`, etc.
- **Full reference example:** `workspace.ecommerce_medallion.bronze_customers`
- **Volume path:** `/Volumes/workspace/ecommerce_medallion/raw_data/`

All scripts, SQL, and `database/schema.sql` will use this three-part naming throughout.

---

**OQ-06 — RESOLVED: Git commit strategy**
One commit per completed phase, plus a git tag at each phase boundary. Tag naming convention:

```
phase-0-foundation
phase-1-data-generation
phase-2-bronze
phase-3-silver
phase-4-gold
phase-5-dashboard
phase-6-testing
phase-7-artifacts
```

Commit messages follow the pattern: `feat(phase-N): <brief description of what was completed>`. This gives the evaluator a visible, navigable development history and directly demonstrates the iterative workflow called out in the Cursor rubric.
