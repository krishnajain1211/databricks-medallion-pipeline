# Data Quality Strategy

> Four named quality checks implemented in the Silver layer, plus one optional
> Business Logic check. All checks stamp a `quality_check_result` column —
> bad rows are never deleted. Strategy is refined as Phase 3 progresses.

## Quality Checks Overview

### 1. Completeness Check (`01_quality_completeness.py`)
- **What:** No NULLs in critical fields
- **Fields checked:** `email` (customers); `customer_id`, `product_id` (orders)
- **Seeded issues:** 50 NULL email (customers); 100 NULL customer_id + 200 NULL product_id (orders)
- **Threshold:** >99% complete expected
- **Result:** `FAILED_COMPLETENESS` stamped on failing rows

### 2. Uniqueness Check (`02_quality_uniqueness.py`)
- **What:** No duplicate primary key rows
- **Fields checked:** `customer_id` (customers); `order_id` (orders)
- **Seeded issues:** 10 duplicate customer_id; 20 duplicate order_id
- **Threshold:** 100% unique expected
- **Result:** `FAILED_UNIQUENESS` stamped on ALL copies of a duplicate (not just second occurrence)

### 3. Type Validation Check (`03_quality_type_validation.py`)
- **What:** Field values match declared types and valid enumeration sets; dates are not future-dated where invalid; numeric fields are in valid ranges
- **Fields checked:** `email` format (regex), `signup_date` (not future), `quantity` (> 0), `unit_price` (≥ 0), `customer_segment` (enum), `order_status` (enum)
- **Seeded issues:** 40 malformed email + 20 future signup_date (customers); 60 zero/negative quantity + 50 negative unit_price (orders)
- **Result:** `FAILED_TYPE_VALIDATION` stamped on failing rows

### 4. Referential Integrity Check (`04_quality_referential_integrity.py`)
- **What:** Foreign keys exist in their parent tables (non-NULL values only)
- **Fields checked:** `customer_id` in orders → must exist in customers; `product_id` in orders → must exist in products
- **Seeded issues:** 50 orphan customer_id + 30 orphan product_id (orders)
- **Note:** NULL FK values are a Completeness failure, not a Referential Integrity failure — checked independently
- **Result:** `FAILED_REFERENTIAL_INTEGRITY` stamped on failing rows

### 5. Business Logic Check (`05_quality_business_logic.py`) — additive, not counted in the "4 checks"
- **What:** Cross-field consistency rules
- **Rules:** (a) `total_amount ≈ quantity × unit_price` (tolerance 0.01); (b) `payment_date` ≥ `order_date` where both are non-NULL; (c) `order_status = 'Completed'` must have non-NULL `payment_date`
- **Seeded issues:** 40 total_amount mismatch + 30 payment_date before order_date (orders)
- **Result:** `FAILED_BUSINESS_LOGIC` stamped on failing rows

## Multi-Failure Handling

A row that fails more than one check receives a comma-delimited result, e.g.:
`FAILED_COMPLETENESS,FAILED_REFERENTIAL_INTEGRITY`

Rows passing all checks receive: `PASSED`

## Quality Metrics Report

Produced by `create_silver_tables.py` as a Spark DataFrame, displayed inline via
`display()` in the Databricks notebook, and written to
`workspace.ecommerce_medallion.silver_quality_metrics` for downstream querying.
Dashboard Tile 4 ("Data Quality Checks — Rows Failed by Type") sources from this table.

Counts below are combined across all entities per check type. Referential Integrity and
Business Logic apply to orders only; all others apply to both customers and orders.

| Check | Total rows checked | Passed | Failed | Pass rate |
|---|---|---|---|---|
| Completeness | 110,000 | 109,650 | 350 (50 customers + 300 orders) | 99.68% |
| Uniqueness | 110,000 | 109,970 | 30 (10 customers + 20 orders) | 99.97% |
| Type Validation | 110,000 | 109,830 | 170 (60 customers + 110 orders) | 99.85% |
| Referential Integrity | 100,000 | 99,920 | 80 (orders only) | 99.92% |
| Business Logic | 100,000 | 99,930 | 70 (orders only) | 99.93% |
