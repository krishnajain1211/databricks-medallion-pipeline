# Data Generation Notes

> Thirteen-section documentation of every seeded quality issue in the synthetic
> CSV data. Each section covers: row count, target field(s), generation method,
> which Silver check it seeds, and any edge-case constraints.
> To be completed in Phase 1 alongside `generate_sample_data.py`.

---

## 1. NULL email — 50 rows (customers.csv)
_[Generation method, field, Silver check seeded — to be documented in Phase 1.]_

## 2. Duplicate customer_id — 10 rows (customers.csv)
_[To be documented in Phase 1.]_

## 3. Malformed email format — 40 rows (customers.csv)
_[Syntactically invalid: missing `@`, or domain without `.` suffix (e.g., `userexample.com`, `user@`, `@domain`). Must be detectable by regex — not just unusual formatting. To be documented in Phase 1.]_

## 4. Future-dated signup_date — 20 rows (customers.csv)
_[signup_date > generation date by at least 1 day. To be documented in Phase 1.]_

## 5. NULL customer_id — 100 rows (orders.csv)
_[To be documented in Phase 1.]_

## 6. NULL product_id — 200 rows (orders.csv)
_[To be documented in Phase 1.]_

## 7. Orphan customer_id — 50 rows (orders.csv)
_[customer_id values that do not appear in customers.csv. Must be non-NULL. To be documented in Phase 1.]_

## 8. Orphan product_id — 30 rows (orders.csv)
_[product_id values that do not appear in products.csv. Must be non-NULL. To be documented in Phase 1.]_

## 9. Duplicate order_id — 20 rows (orders.csv)
_[To be documented in Phase 1.]_

## 10. Zero or negative quantity — 60 rows (orders.csv)
_[quantity <= 0. Paired total_amount is also set inconsistently. To be documented in Phase 1.]_

## 11. Negative unit_price — 50 rows (orders.csv)
_[unit_price < 0. total_amount similarly negative. To be documented in Phase 1.]_

## 12. total_amount mismatch — 40 rows (orders.csv)
_[Valid positive quantity and unit_price, but total_amount deliberately set to quantity × unit_price ± non-zero delta (e.g., off by 10). Check tolerance: abs(total_amount − quantity × unit_price) > 0.01. To be documented in Phase 1.]_

## 13. payment_date before order_date — 30 rows (orders.csv)
_[Both dates non-NULL; order_status = 'Completed'. payment_date < order_date. To be documented in Phase 1.]_

---

## Summary

| # | File | Issue category | Count | Silver check seeded |
|---|---|---|---|---|
| 1 | customers.csv | NULL email | 50 | Completeness |
| 2 | customers.csv | Duplicate customer_id | 10 | Uniqueness |
| 3 | customers.csv | Malformed email format | 40 | Type Validation |
| 4 | customers.csv | Future-dated signup_date | 20 | Type Validation |
| 5 | orders.csv | NULL customer_id | 100 | Completeness |
| 6 | orders.csv | NULL product_id | 200 | Completeness |
| 7 | orders.csv | Orphan customer_id | 50 | Referential Integrity |
| 8 | orders.csv | Orphan product_id | 30 | Referential Integrity |
| 9 | orders.csv | Duplicate order_id | 20 | Uniqueness |
| 10 | orders.csv | Zero/negative quantity | 60 | Type Validation |
| 11 | orders.csv | Negative unit_price | 50 | Type Validation |
| 12 | orders.csv | total_amount mismatch | 40 | Business Logic |
| 13 | orders.csv | payment_date before order_date | 30 | Business Logic |
| | **Total** | | **700** | |
