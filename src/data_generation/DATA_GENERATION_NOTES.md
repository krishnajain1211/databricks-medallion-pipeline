# Data Generation Notes

> Documents every seeded data quality issue across all three CSV files.
> One section per defect category — thirteen in total.
> Purpose: ensure reviewers can trace exactly which rows test which Silver layer check.
>
> Source of truth for defect counts: `requirements-analysis.md` FR-04, FR-05.
> Script: `src/data_generation/generate_sample_data.py` (SEED=42, deterministic).

---

## Summary Table

| ID   | Category                    | File             | Count | Silver Check Triggered         |
|------|-----------------------------|------------------|------:|--------------------------------|
| C-01 | NULL email                  | customers.csv    |    50 | Completeness                   |
| C-02 | Malformed email             | customers.csv    |    40 | Type Validation                |
| C-03 | Future signup_date          | customers.csv    |    20 | Type Validation                |
| C-04 | Duplicate customer_id       | customers.csv    |    10 | Uniqueness                     |
| O-01 | NULL customer_id            | orders.csv       |   100 | Completeness                   |
| O-02 | NULL product_id             | orders.csv       |   200 | Completeness                   |
| O-03 | Orphan customer_id          | orders.csv       |    50 | Referential Integrity          |
| O-04 | Orphan product_id           | orders.csv       |    30 | Referential Integrity          |
| O-05 | Duplicate order_id          | orders.csv       |    20 | Uniqueness                     |
| O-06 | Zero/negative quantity      | orders.csv       |    60 | Type Validation                |
| O-07 | Negative unit_price         | orders.csv       |    50 | Type Validation                |
| O-08 | total_amount mismatch       | orders.csv       |    40 | Business Logic (05)            |
| O-09 | payment_date < order_date   | orders.csv       |    30 | Business Logic (05)            |
| —    | **Grand total**             | —                | **700** | —                            |

Row counts: customers.csv = 10,000; orders.csv = 100,000; products.csv = 500.
products.csv is intentionally defect-free (clean reference table).

---

## C-01 — NULL email (customers.csv, 50 rows)

**What was seeded:** 50 rows where the `email` column is an empty cell (NULL).

**How:** Positions 0–49 in the pre-shuffle array have `email` set to `None`. Python's
`pandas.to_csv` writes `None` as an empty field, which Spark reads as NULL with
a StringType schema.

**No overlap with:** C-02 (malformed email rows have a non-NULL bad string).

**Silver check triggered:** `01_quality_completeness.py` — flags any row with
`email IS NULL` as `FAILED_COMPLETENESS`.

---

## C-02 — Malformed email (customers.csv, 40 rows)

**What was seeded:** 40 rows with a non-NULL email string that violates basic
email syntax. Five patterns cycling in round-robin (8 rows each):

| Pattern              | Example                    | Violation              |
|----------------------|----------------------------|------------------------|
| `noatsign{n}example.com` | `noatsign000example.com` | Missing `@`           |
| `user{n}@`           | `user001@`                 | No domain after `@`    |
| `@nodomain{n}`       | `@nodomain002`             | No local-part before @ |
| `user{n}@nodotdomain`| `user003@nodotdomain`      | No `.` in domain       |
| `justtext{n}`        | `justtext004`              | No `@` or `.`          |

**Silver check triggered:** `03_quality_type_validation.py` — uses regex
`^[^@]+@[^@]+\.[^@]+$`; any non-NULL email that does not match is flagged
`FAILED_TYPE_VALIDATION`.

---

## C-03 — Future signup_date (customers.csv, 20 rows)

**What was seeded:** 20 rows where `signup_date` is a valid ISO-format date
(**YYYY-MM-DD**) but falls between 1 and 365 days after the generation date
(per FR-04b: "at least one day beyond the generation date").

**How:** `rng.integers(1, 366, 20)` offsets are added to `date.today()`. All
resulting dates are formatted as strings in the CSV — they parse correctly in
Spark as DateType but fail the temporal boundary check.

**Silver check triggered:** `03_quality_type_validation.py` — flags any row
where `signup_date > current_date()` as `FAILED_TYPE_VALIDATION`.

---

## C-04 — Duplicate customer_id (customers.csv, 10 rows)

**What was seeded:** 5 pairs of rows sharing the same `customer_id` (= 10 rows
total with a duplicate ID; all 10 are flagged by A-09's "flag all copies" rule).

**How:** Pre-shuffle positions 110–114 are the originals (customer_ids 111–115).
Positions 115–119 are overwritten to the same IDs (111–115). After shuffling the
5 "copy" rows are distributed throughout the file.

**Important design note (A-09):** The Silver uniqueness check flags ALL copies of
a duplicated ID, not just the second occurrence. This means all 10 rows (5 pairs)
receive `FAILED_UNIQUENESS`, and none of the 5 duplicated IDs survives into Gold.

**Silver check triggered:** `02_quality_uniqueness.py`.

---

## O-01 — NULL customer_id (orders.csv, 100 rows)

**What was seeded:** 100 rows with no `customer_id` value (NULL / empty cell).

**Non-overlap guarantee (A-11):** These rows are completely separate from O-03
(orphan customer_id). A NULL `customer_id` is a completeness failure; a non-NULL
customer_id that doesn't match any customer is a referential integrity failure.
The two checks must not be conflated.

**Silver check triggered:** `01_quality_completeness.py` — flags rows where
`customer_id IS NULL` as `FAILED_COMPLETENESS`.

---

## O-02 — NULL product_id (orders.csv, 200 rows)

**What was seeded:** 200 rows with no `product_id` value.

**Same non-overlap guarantee as O-01 vs O-03:** NULL product_id rows (O-02) are
a different defect group from orphan product_id rows (O-04).

**Silver check triggered:** `01_quality_completeness.py` — flags rows where
`product_id IS NULL` as `FAILED_COMPLETENESS`.

---

## O-03 — Orphan customer_id (orders.csv, 50 rows)

**What was seeded:** 50 rows with a non-NULL `customer_id` value that does not
appear in `customers.csv`. IDs used: **10001–10050** (one above N_CUSTOMERS=10,000).

**Why this range:** Any integer > 10,000 is guaranteed to be absent from the 9,995
unique customer_ids in customers.csv, making the referential integrity check
unambiguous.

**Silver check triggered:** `04_quality_referential_integrity.py` — joins orders
to customers on `customer_id`; non-NULL orders.customer_id with no matching
customers row → `FAILED_REFERENTIAL_INTEGRITY`.

---

## O-04 — Orphan product_id (orders.csv, 30 rows)

**What was seeded:** 30 rows with a non-NULL `product_id` value that does not
appear in `products.csv`. IDs used: **501–530** (one above N_PRODUCTS=500).

**Silver check triggered:** `04_quality_referential_integrity.py` — same join
logic as O-03 but for the products dimension.

---

## O-05 — Duplicate order_id (orders.csv, 20 rows)

**What was seeded:** 10 pairs of rows sharing an `order_id` (= 20 rows total
flagged by the uniqueness check).

**How:** Pre-shuffle positions 380–389 are the originals (order_ids 381–390).
Positions 390–399 are overwritten with the same IDs. After shuffling the 10 copy
rows are distributed throughout.

**A-09 applies:** Both copies of each duplicate ID receive `FAILED_UNIQUENESS`.
Neither survives into Gold.

**Silver check triggered:** `02_quality_uniqueness.py`.

---

## O-06 — Zero/negative quantity (orders.csv, 60 rows)

**What was seeded:** 60 rows with `quantity ≤ 0`. Values cycle through:
`[0, -1, -2, -3, -5, -10]` (10 rows of each value).

**FR-05a — paired total_amount:** For these rows `total_amount` is set to a
random positive value (not `quantity × unit_price`), making it also inconsistent.
However, these rows are counted **only once** in the 580 total — they are
classified as type validation failures, not separately as business logic failures.
The O-08 mismatch check filters them out by requiring `quantity > 0`.

**Silver check triggered:** `03_quality_type_validation.py` — flags any row
where `quantity <= 0` as `FAILED_TYPE_VALIDATION`.

---

## O-07 — Negative unit_price (orders.csv, 50 rows)

**What was seeded:** 50 rows with `unit_price < 0` (range: −0.01 to −100.00).
These rows have valid positive `quantity` (1–10).

**FR-05b — total_amount:** Set to `quantity × unit_price` (which is negative
since price < 0). This makes `total_amount` consistently negative — not an
*additional* mismatch, just the natural product of the negative price.

**Counted once only:** Similar to O-06, these rows are counted as type validation
failures. The O-08 mismatch check excludes them via `unit_price > 0` filter.

**Silver check triggered:** `03_quality_type_validation.py` — flags any row
where `unit_price < 0` as `FAILED_TYPE_VALIDATION`.

---

## O-08 — total_amount mismatch (orders.csv, 40 rows)

**What was seeded:** 40 rows with **valid positive** `quantity` and `unit_price`
but a deliberately wrong `total_amount`. The delta cycles through
`[+10, −10, +20, −20, +50]` (8 rows of each), added on top of the correct
`quantity × unit_price` value.

**FR-05c — why these rows are distinct:** They have valid qty and price (so they
don't overlap O-06/O-07). The only fault is the arithmetic inconsistency in
`total_amount`.

**Tolerance:** The Silver check uses `abs(total_amount − quantity × unit_price) > 0.01`
to allow for floating-point rounding (A-13). All seeded deltas are ≥10.00, so
all 40 rows are caught unambiguously.

**Silver check triggered:** `05_quality_business_logic.py` → `FAILED_BUSINESS_LOGIC`.

---

## O-09 — payment_date before order_date (orders.csv, 30 rows)

**What was seeded:** 30 rows where `payment_date < order_date`. The offset
(payment is `1–30 days before` the order date) is random. All 30 rows have
`order_status = 'Completed'` (per FR-05d) — a completed order with a temporally
impossible payment record.

**A-18 context:** `payment_date` is nullable by design (Pending/Cancelled orders
have no payment date). NULL payment_date is NOT flagged. Only a non-NULL
`payment_date` that precedes `order_date` is flagged here.

**Silver check triggered:** `05_quality_business_logic.py` → `FAILED_BUSINESS_LOGIC`.

---

*Last updated: Phase 1 — Data Generation*
