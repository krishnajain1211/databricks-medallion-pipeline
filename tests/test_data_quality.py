"""
Purpose : Tier 1 data quality unit tests (FR-34).
          Runs locally via pytest — no Databricks connection required.
          Reimplements each of the five Silver quality-check rules in pandas,
          loads the committed CSVs from data/, and asserts that every check
          detects exactly the expected number of seeded failures documented in
          DATA_GENERATION_NOTES.md (SEED=42, deterministic output).

          Assertion strength: uses == (exact count) rather than the >= lower-bound
          required by FR-34.  The deterministic seed means an exact match is
          achievable and is stronger evidence than a lower bound.

Inputs  : data/customers.csv  (10,000 rows, 120 seeded defects)
          data/orders.csv     (100,000 rows, 580 seeded defects)
          data/products.csv   (500 rows, 0 defects — clean reference)
Outputs : pytest pass/fail results printed per test function
Phase   : Phase 6 — Testing (Tier 1)
Run     : pytest tests/test_data_quality.py -v
          (from the repo root; requires: pip install pytest pandas)
"""

import re
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

# ── Data paths ────────────────────────────────────────────────────────────────

_DATA_DIR = Path(__file__).parents[1] / "data"


def _load_customers() -> pd.DataFrame:
    """Load customers.csv with appropriate dtypes."""
    return pd.read_csv(
        _DATA_DIR / "customers.csv",
        dtype={
            "customer_id":      "Int64",   # nullable int — handles any missing IDs
            "customer_name":    str,
            "email":            str,       # NaN preserved for NULL detection
            "country":          str,
            "customer_segment": str,
            "lifetime_value":   float,
        },
        parse_dates=["signup_date"],
    )


def _load_orders() -> pd.DataFrame:
    """Load orders.csv with appropriate dtypes.

    customer_id and product_id are nullable (O-01, O-02 seeded NULLs).
    quantity is nullable Int64 for safety; unit_price and total_amount are float.
    """
    return pd.read_csv(
        _DATA_DIR / "orders.csv",
        dtype={
            "order_id":      "Int64",
            "customer_id":   "Int64",    # NULL in O-01 rows
            "product_id":    "Int64",    # NULL in O-02 rows
            "quantity":      "Int64",    # negative in O-06 rows
            "unit_price":    float,      # negative in O-07 rows
            "total_amount":  float,
            "order_status":  str,
        },
        parse_dates=["order_date", "payment_date"],
    )


def _load_products() -> pd.DataFrame:
    """Load products.csv (clean reference — no seeded defects)."""
    return pd.read_csv(
        _DATA_DIR / "products.csv",
        dtype={
            "product_id":   "Int64",
            "product_name": str,
            "category":     str,
            "price":        float,   # actual column name in products.csv is 'price'
            "cost":         float,
        },
    )


# ── Module-level fixtures (loaded once per test session) ──────────────────────

@pytest.fixture(scope="module")
def customers():
    """Shared customers DataFrame for all tests in this module."""
    return _load_customers()


@pytest.fixture(scope="module")
def orders():
    """Shared orders DataFrame for all tests in this module."""
    return _load_orders()


@pytest.fixture(scope="module")
def products():
    """Shared products DataFrame for all tests in this module."""
    return _load_products()


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 1 — Completeness (mirrors 01_quality_completeness.py)
# Seeded: C-01 (50 NULL email), O-01 (100 NULL customer_id), O-02 (200 NULL product_id)
# ══════════════════════════════════════════════════════════════════════════════

def test_completeness_null_email(customers):
    """C-01: 50 customers must have a NULL email value."""
    null_count = customers["email"].isna().sum()
    assert null_count == 50, (
        f"Completeness / NULL email (C-01): expected 50 rows, found {null_count}"
    )


def test_completeness_null_customer_id(orders):
    """O-01: 100 orders must have a NULL customer_id."""
    null_count = orders["customer_id"].isna().sum()
    assert null_count == 100, (
        f"Completeness / NULL customer_id (O-01): expected 100 rows, found {null_count}"
    )


def test_completeness_null_product_id(orders):
    """O-02: 200 orders must have a NULL product_id."""
    null_count = orders["product_id"].isna().sum()
    assert null_count == 200, (
        f"Completeness / NULL product_id (O-02): expected 200 rows, found {null_count}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 2 — Uniqueness (mirrors 02_quality_uniqueness.py)
# A-09: ALL copies of a duplicated key are flagged, not just the second occurrence.
# Seeded: C-04 (5 pairs = 10 customer rows), O-05 (10 pairs = 20 order rows)
# ══════════════════════════════════════════════════════════════════════════════

def test_uniqueness_duplicate_customer_id(customers):
    """C-04: 10 customer rows share 5 duplicated customer_ids (all copies flagged, A-09)."""
    dup_rows = customers[customers.duplicated("customer_id", keep=False)]
    assert len(dup_rows) == 10, (
        f"Uniqueness / duplicate customer_id (C-04): expected 10 rows, found {len(dup_rows)}"
    )


def test_uniqueness_duplicate_order_id(orders):
    """O-05: 20 order rows share 10 duplicated order_ids (all copies flagged, A-09)."""
    dup_rows = orders[orders.duplicated("order_id", keep=False)]
    assert len(dup_rows) == 20, (
        f"Uniqueness / duplicate order_id (O-05): expected 20 rows, found {len(dup_rows)}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 3 — Type Validation (mirrors 03_quality_type_validation.py)
# Seeded: C-02 (40 malformed email), C-03 (20 future signup_date),
#         O-06 (60 zero/negative quantity), O-07 (50 negative unit_price)
# ══════════════════════════════════════════════════════════════════════════════

# Regex must match the Silver script exactly (03_quality_type_validation.py)
_EMAIL_REGEX = r"^[^@]+@[^@]+\.[^@]+$"


def test_type_validation_malformed_email(customers):
    """C-02: 40 customers have a non-NULL email that fails the basic email regex."""
    non_null = customers[customers["email"].notna()]
    malformed = non_null[~non_null["email"].str.match(_EMAIL_REGEX)]
    assert len(malformed) == 40, (
        f"Type Validation / malformed email (C-02): expected 40 rows, found {len(malformed)}"
    )


def test_type_validation_future_signup_date(customers):
    """C-03: 20 customers have a signup_date strictly after today (generation date)."""
    today = pd.Timestamp(date.today())
    future_rows = customers[customers["signup_date"] > today]
    assert len(future_rows) == 20, (
        f"Type Validation / future signup_date (C-03): expected 20 rows, found {len(future_rows)}"
    )


def test_type_validation_zero_or_negative_quantity(orders):
    """O-06: 60 orders have quantity <= 0 (zero or negative values seeded)."""
    bad_qty = orders[orders["quantity"] <= 0]
    assert len(bad_qty) == 60, (
        f"Type Validation / zero/negative quantity (O-06): expected 60 rows, found {len(bad_qty)}"
    )


def test_type_validation_negative_unit_price(orders):
    """O-07: 50 orders have unit_price < 0."""
    neg_price = orders[orders["unit_price"] < 0]
    assert len(neg_price) == 50, (
        f"Type Validation / negative unit_price (O-07): expected 50 rows, found {len(neg_price)}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 4 — Referential Integrity (mirrors 04_quality_referential_integrity.py)
# A-11: orphan check only runs on non-NULL FKs (NULL FK is a separate completeness failure).
# Seeded: O-03 (50 orphan customer_id, IDs 10001–10050), O-04 (30 orphan product_id, IDs 501–530)
# ══════════════════════════════════════════════════════════════════════════════

def test_referential_integrity_orphan_customer_id(customers, orders):
    """O-03: 50 orders have a non-NULL customer_id absent from customers.csv."""
    valid_cust_ids = set(customers["customer_id"].dropna())
    non_null_orders = orders[orders["customer_id"].notna()]
    orphans = non_null_orders[~non_null_orders["customer_id"].isin(valid_cust_ids)]
    assert len(orphans) == 50, (
        f"Referential Integrity / orphan customer_id (O-03): expected 50 rows, found {len(orphans)}"
    )


def test_referential_integrity_orphan_product_id(orders, products):
    """O-04: 30 orders have a non-NULL product_id absent from products.csv."""
    valid_prod_ids = set(products["product_id"].dropna())
    non_null_orders = orders[orders["product_id"].notna()]
    orphans = non_null_orders[~non_null_orders["product_id"].isin(valid_prod_ids)]
    assert len(orphans) == 30, (
        f"Referential Integrity / orphan product_id (O-04): expected 30 rows, found {len(orphans)}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 5 — Business Logic (mirrors 05_quality_business_logic.py)
# BL-1: payment_date < order_date (non-NULL payment_date only — A-18)
# BL-2: order_status='Completed' AND payment_date IS NULL (defensive guard, 0 seeded)
# BL-3: total_amount mismatch — only checked when qty > 0 AND price > 0 (A-13)
#        Excludes O-06/O-07 rows which are counted under type validation, not here.
# Seeded: O-08 (40 total_amount mismatch), O-09 (30 payment_date < order_date)
# ══════════════════════════════════════════════════════════════════════════════

_AMT_TOLERANCE = 0.01   # matches the Silver script constant


def test_business_logic_total_amount_mismatch(orders):
    """O-08: 40 orders have abs(total_amount - qty*price) > 0.01 with valid qty and price.

    Rows where quantity <= 0 or unit_price < 0 are deliberately excluded from
    this check (they are flagged under type validation per O-06/O-07, not here).
    """
    valid_math_rows = orders[
        (orders["quantity"] > 0) & (orders["unit_price"] > 0)
    ]
    mismatch = valid_math_rows[
        (
            valid_math_rows["total_amount"]
            - valid_math_rows["quantity"] * valid_math_rows["unit_price"]
        ).abs() > _AMT_TOLERANCE
    ]
    assert len(mismatch) == 40, (
        f"Business Logic / total_amount mismatch (O-08): expected 40 rows, found {len(mismatch)}"
    )


def test_business_logic_payment_date_before_order_date(orders):
    """O-09: 30 orders have payment_date < order_date (all have order_status='Completed')."""
    has_payment = orders[orders["payment_date"].notna()]
    early_payment = has_payment[has_payment["payment_date"] < has_payment["order_date"]]
    assert len(early_payment) == 30, (
        f"Business Logic / payment_date before order_date (O-09): "
        f"expected 30 rows, found {len(early_payment)}"
    )


def test_business_logic_completed_no_payment_date(orders):
    """BL-2 defensive guard: no seeded rows with order_status='Completed' AND NULL payment_date.

    This check is in the Silver script as a defensive guard (A-18 case a).
    Verifying it returns 0 confirms the check does not produce false positives
    in our generated data.
    """
    completed_no_payment = orders[
        (orders["order_status"] == "Completed") & orders["payment_date"].isna()
    ]
    assert len(completed_no_payment) == 0, (
        f"Business Logic / BL-2 guard (defensive): expected 0 rows, "
        f"found {len(completed_no_payment)}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# SANITY CHECKS — Row counts and defect grand total
# ══════════════════════════════════════════════════════════════════════════════

def test_row_counts(customers, orders, products):
    """Verify that all three CSVs have the expected total row counts."""
    assert len(customers) == 10_000, f"customers.csv: expected 10,000 rows, found {len(customers)}"
    assert len(orders)    == 100_000, f"orders.csv: expected 100,000 rows, found {len(orders)}"
    assert len(products)  == 500,     f"products.csv: expected 500 rows, found {len(products)}"


def test_products_are_defect_free(products):
    """products.csv is intentionally clean — verify zero defects across all columns."""
    assert products["product_id"].isna().sum()   == 0, "Unexpected NULL product_id in products"
    assert products["product_name"].isna().sum() == 0, "Unexpected NULL product_name in products"
    assert products["category"].isna().sum()     == 0, "Unexpected NULL category in products"
    assert (products["price"] < 0).sum()         == 0, "Unexpected negative price in products"
    assert (products["cost"] < 0).sum()          == 0, "Unexpected negative cost in products"
