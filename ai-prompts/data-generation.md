# AI Prompts — Data Generation

> Prompt history for all exchanges related to `generate_sample_data.py`
> and `DATA_GENERATION_NOTES.md`. Entries are added after each significant exchange.
> Format: see Section 5 of `requirements-analysis.md` for the standard entry template.

---

## Prompt 1: Implement and run generate_sample_data.py; write DATA_GENERATION_NOTES.md

**PROMPT SENT:**
"Before we continue Bronze, I realized Phase 1 (data generation) was never
actually executed — data/ only has a .gitkeep, no real CSVs exist yet.

Implement and then RUN src/data_generation/generate_sample_data.py per
requirements-analysis.md sections 2.1 (FR-01 through FR-06) and 3
(A-07, A-08, A-12, A-13) — the exact schemas, 10,000/100,000/500 row counts,
and all 13 seeded defect categories totaling 700 rows.

After running it, show me the verification table with actual counts per defect
category so I can confirm it matches the 700-row target before we move forward.
Write src/data_generation/DATA_GENERATION_NOTES.md as well.
Log this to ai-prompts/data-generation.md."

**AI RESPONSE SUMMARY:**
1. Read requirements-analysis.md FR-01 through FR-06 and A-07, A-08, A-12,
   A-13, A-14, A-15 before writing a line of code.
2. Checked Python version (3.12) and installed packages — none of pandas,
   numpy, faker were present. Ran `pip install pandas numpy faker`.
3. Implemented generate_sample_data.py from scratch (~490 lines):
   - Fixed SEED=42 on Faker, numpy RNG, and random for full reproducibility.
   - Non-overlapping index-slice layout: each defect group occupies a specific
     row range BEFORE shuffle, ensuring no accidental overlap between categories.
   - All 13 defect categories implemented across 4 functions:
     `generate_products()`, `generate_customers()`, `generate_orders()`,
     `verify_defects()`.
   - Key implementation decisions:
     - C-04 (dup customer_id): 5 pairs × 2 = 10 rows; positions 115-119 copy
       IDs from 110-114.
     - O-05 (dup order_id): 10 pairs × 2 = 20 rows; positions 390-399 copy
       IDs from 380-389.
     - O-06 (neg qty): total_amount set to random positive value (FR-05a).
     - O-07 (neg price): total_amount = qty × negative_price (FR-05b, consistently
       negative; excluded from O-08 mismatch check by `unit_price > 0` filter).
     - O-08 (mismatch): valid positive qty/price; delta cycled from
       [+10, -10, +20, -20, +50] on top of correct total.
     - O-09 (payment before order): forced order_status='Completed' per FR-05d.
   - pd.Int64Dtype() used for nullable integer columns (customer_id, product_id
     in orders) to avoid float "100.0" values in CSV output.
   - Rows shuffled (random_state=SEED) before return so defects are distributed.
   - verify_defects() uses pd.to_datetime() for reliable date comparisons; mismatch
     count filtered to qty>0 AND price>0 to exclude O-06/O-07 rows.
4. First run failed with UnicodeEncodeError on Windows cp1252 console (✓ → symbol).
   Fixed by replacing Unicode characters with ASCII equivalents.
5. Second run succeeded. All 13 defect categories matched expected counts exactly.

**DEFECT VERIFICATION TABLE (actual output):**
```
   id                  category          file  expected  actual  match
 C-01                NULL email customers.csv        50      50   True
 C-02           Malformed email customers.csv        40      40   True
 C-03        Future signup_date customers.csv        20      20   True
 C-04     Duplicate customer_id customers.csv        10      10   True
 O-01          NULL customer_id    orders.csv       100     100   True
 O-02           NULL product_id    orders.csv       200     200   True
 O-03        Orphan customer_id    orders.csv        50      50   True
 O-04         Orphan product_id    orders.csv        30      30   True
 O-05        Duplicate order_id    orders.csv        20      20   True
 O-06    Zero/negative quantity    orders.csv        60      60   True
 O-07       Negative unit_price    orders.csv        50      50   True
 O-08     total_amount mismatch    orders.csv        40      40   True
 O-09 payment_date < order_date    orders.csv        30      30   True
TOTAL        All seeded defects             —       700     700   True
```
Grand total: 700/700. Run time: ~4 seconds.

6. Wrote DATA_GENERATION_NOTES.md — 13 sections (one per defect category),
   summary table, non-overlap guarantees documented for all check boundaries.

**YOUR EVALUATION:** _Pending your confirmation. Please review the verification
table above and confirm counts are acceptable before we commit._

**FINAL DECISION:** _Pending._
