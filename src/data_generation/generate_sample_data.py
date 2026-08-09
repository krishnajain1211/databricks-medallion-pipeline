"""
Purpose  : Generate synthetic e-commerce CSVs with intentionally seeded data quality
           issues for all 13 defect categories in requirements-analysis.md FR-04 and
           FR-05.  Total seeded: 120 (customers) + 580 (orders) + 0 (products) = 700.
Inputs   : None — fully synthetic; Faker + NumPy RNG with fixed SEED=42 for
           reproducible output across runs.
Outputs  : data/customers.csv  (10,000 rows, 120 defects)
           data/orders.csv     (100,000 rows, 580 defects)
           data/products.csv   (500 rows,    0 defects — clean reference data)
Phase    : Phase 1 — Data Generation
Run      : python src/data_generation/generate_sample_data.py
Requires : pip install pandas numpy faker   (no Spark — local script per A-15)
"""

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Set

import numpy as np
import pandas as pd
from faker import Faker

# ── Reproducibility ───────────────────────────────────────────────────────────
SEED = 42
Faker.seed(SEED)
rng  = np.random.default_rng(SEED)
fake = Faker()

# ── Output directory ──────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parents[2] / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Row counts ────────────────────────────────────────────────────────────────
N_CUSTOMERS = 10_000
N_ORDERS    = 100_000
N_PRODUCTS  = 500
TODAY       = date.today()

# ── Seeded defect counts (both sums are asserted at startup) ──────────────────

# customers.csv — 4 categories, must total 120
DC_NULL_EMAIL       = 50   # FR-04  : NULL email
DC_MALFORMED_EMAIL  = 40   # FR-04a : syntactically invalid email
DC_FUTURE_DATE      = 20   # FR-04b : signup_date > today
DC_DUP_CUST_ID      = 10   # FR-04  : duplicate customer_id (5 pairs × 2 rows)

# orders.csv — 9 categories, must total 580
DO_NULL_CUST_ID     = 100  # FR-05  : NULL customer_id
DO_NULL_PROD_ID     = 200  # FR-05  : NULL product_id
DO_ORPHAN_CUST      = 50   # FR-05  : customer_id not in customers table
DO_ORPHAN_PROD      = 30   # FR-05  : product_id not in products table
DO_DUP_ORDER_ID     = 20   # FR-05  : duplicate order_id (10 pairs × 2 rows)
DO_NEG_QTY          = 60   # FR-05a : quantity <= 0
DO_NEG_PRICE        = 50   # FR-05b : unit_price < 0
DO_AMT_MISMATCH     = 40   # FR-05c : total_amount != qty * price (valid qty/price)
DO_PAYMENT_BEFORE   = 30   # FR-05d : payment_date < order_date

assert (DC_NULL_EMAIL + DC_MALFORMED_EMAIL + DC_FUTURE_DATE + DC_DUP_CUST_ID) == 120, \
    "Customer defect counts must sum to 120"
assert (DO_NULL_CUST_ID + DO_NULL_PROD_ID + DO_ORPHAN_CUST + DO_ORPHAN_PROD +
        DO_DUP_ORDER_ID + DO_NEG_QTY + DO_NEG_PRICE + DO_AMT_MISMATCH +
        DO_PAYMENT_BEFORE) == 580, \
    "Order defect counts must sum to 580"

# ── Reference enumerations ────────────────────────────────────────────────────
CUSTOMER_SEGMENTS = ["Premium", "Standard", "Basic"]
ORDER_STATUSES    = ["Pending", "Completed", "Cancelled"]
CATEGORIES = [
    "Electronics", "Clothing", "Books", "Home & Garden", "Sports",
    "Toys", "Food & Beverage", "Health & Beauty", "Automotive", "Tools",
]
COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Australia", "Germany",
    "France", "Japan", "India", "Brazil", "Mexico", "Italy", "Spain",
    "Netherlands", "Sweden", "Singapore", "South Korea", "Switzerland",
    "New Zealand", "Norway", "Argentina",
]

# Orphan IDs — guaranteed outside valid ranges so they trigger referential checks
_ORPHAN_CUST_START = N_CUSTOMERS + 1   # 10001 … 10050
_ORPHAN_PROD_START = N_PRODUCTS  + 1   # 501 … 530

# Email regex shared with 03_quality_type_validation.py
_EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rand_dates(start: date, count: int, days_range: int) -> list:
    """
    Return `count` random date objects uniformly sampled from
    [start, start + days_range].
    """
    offsets = rng.integers(0, days_range + 1, count)
    return [start + timedelta(days=int(d)) for d in offsets]


# ── Generators ────────────────────────────────────────────────────────────────

def generate_products(n: int = N_PRODUCTS) -> pd.DataFrame:
    """
    Build clean products reference DataFrame — no defects seeded.

    Parameters
    ----------
    n : int
        Number of rows (default 500).

    Returns
    -------
    pd.DataFrame with columns: product_id, product_name, category, price,
    cost, stock_quantity, reorder_level.
    """
    prices = rng.uniform(5.0, 500.0, n).round(2)
    costs  = (prices * rng.uniform(0.3, 0.7, n)).round(2)
    return pd.DataFrame({
        "product_id":     range(1, n + 1),
        "product_name":   [f"{fake.word().title()} {fake.word().title()}" for _ in range(n)],
        "category":       rng.choice(CATEGORIES, n),
        "price":          prices,
        "cost":           costs,
        "stock_quantity": rng.integers(0, 1001, n),
        "reorder_level":  rng.integers(10, 201, n),
    })


def generate_customers(n: int = N_CUSTOMERS) -> pd.DataFrame:
    """
    Build customers DataFrame with 4 defect categories (120 affected rows).

    Index layout before shuffle (non-overlapping):
      [0   :  50] → NULL email             (C-01, 50 rows)
      [50  :  90] → malformed email        (C-02, 40 rows — 5 patterns × 8)
      [90  : 110] → future signup_date     (C-03, 20 rows)
      [110 : 115] → dup customer_id orig   (C-04, 5 rows)
      [115 : 120] → dup customer_id copy   (C-04, 5 rows — same IDs as 110-114)
      [120 :   n] → clean                  (9,880 rows)

    Parameters
    ----------
    n : int
        Total row count (default 10,000).

    Returns
    -------
    pd.DataFrame with columns: customer_id, customer_name, email, country,
    signup_date, customer_segment, lifetime_value.
    Rows shuffled with random_state=SEED before returning.
    """
    # Base arrays — all clean initially
    customer_ids    = list(range(1, n + 1))
    customer_names  = [fake.name()  for _ in range(n)]
    emails          = [fake.email() for _ in range(n)]
    countries       = list(rng.choice(COUNTRIES, n))
    signup_days     = (TODAY - date(2020, 1, 1)).days
    signup_dates    = _rand_dates(date(2020, 1, 1), n, signup_days)
    segments        = list(rng.choice(CUSTOMER_SEGMENTS, n))
    lifetime_values = list(rng.uniform(10.0, 50_000.0, n).round(2))

    # C-01: NULL email (positions 0-49)
    for i in range(DC_NULL_EMAIL):
        emails[i] = None

    # C-02: Malformed email (positions 50-89) — 5 patterns in round-robin
    _patterns = [
        lambda j: f"noatsign{j:03d}example.com",   # missing @
        lambda j: f"user{j:03d}@",                  # no domain
        lambda j: f"@nodomain{j:03d}",              # no local part
        lambda j: f"user{j:03d}@nodotdomain",       # missing TLD dot
        lambda j: f"justtext{j:03d}",               # no @ or dot
    ]
    for i in range(DC_MALFORMED_EMAIL):
        emails[DC_NULL_EMAIL + i] = _patterns[i % 5](i)

    # C-03: Future signup_date (positions 90-109) — FR-04b: at least 1 day ahead
    future_offsets = rng.integers(1, 366, DC_FUTURE_DATE)
    _c03_start = DC_NULL_EMAIL + DC_MALFORMED_EMAIL   # 90
    for i, offset in enumerate(future_offsets):
        signup_dates[_c03_start + i] = TODAY + timedelta(days=int(offset))

    # C-04: Duplicate customer_id (positions 110-119 = 5 pairs)
    # Positions 115-119 receive the same customer_ids as 110-114.
    _c04_start = _c03_start + DC_FUTURE_DATE   # 110
    _n_pairs   = DC_DUP_CUST_ID // 2           # 5
    for i in range(_n_pairs):
        customer_ids[_c04_start + _n_pairs + i] = customer_ids[_c04_start + i]

    df = pd.DataFrame({
        "customer_id":      customer_ids,
        "customer_name":    customer_names,
        "email":            emails,
        "country":          countries,
        "signup_date":      signup_dates,
        "customer_segment": segments,
        "lifetime_value":   lifetime_values,
    })
    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)


def generate_orders(
    n: int = N_ORDERS,
    valid_customer_ids: Set[int] = None,
    valid_product_ids:  Set[int] = None,
) -> pd.DataFrame:
    """
    Build orders DataFrame with 9 defect categories (580 affected rows).

    Index layout before shuffle (non-overlapping):
      [0   : 100] → NULL customer_id           (O-01)
      [100 : 300] → NULL product_id            (O-02)
      [300 : 350] → orphan customer_id         (O-03 — IDs 10001-10050)
      [350 : 380] → orphan product_id          (O-04 — IDs 501-530)
      [380 : 390] → dup order_id originals     (O-05 — 10 rows)
      [390 : 400] → dup order_id copies        (O-05 — 10 rows, same IDs as 380-389)
      [400 : 460] → zero/negative quantity     (O-06)
      [460 : 510] → negative unit_price        (O-07)
      [510 : 550] → total_amount mismatch      (O-08)
      [550 : 580] → payment_date < order_date  (O-09)
      [580 :   n] → clean                      (99,420 rows)

    Parameters
    ----------
    n                  : Total row count (default 100,000).
    valid_customer_ids : Set of customer_ids present in customers.csv.
    valid_product_ids  : Set of product_ids present in products.csv.

    Returns
    -------
    pd.DataFrame with columns: order_id, customer_id, order_date, product_id,
    quantity, unit_price, total_amount, order_status, payment_date.
    Rows shuffled with random_state=SEED before returning.
    """
    order_start  = date(2022, 1, 1)
    order_range  = (TODAY - order_start).days
    cust_list    = list(valid_customer_ids)
    prod_list    = list(valid_product_ids)

    # Base arrays — all valid
    order_ids    = list(range(1, n + 1))
    customer_ids = list(rng.choice(cust_list, n))
    product_ids  = list(rng.choice(prod_list, n))
    order_dates  = _rand_dates(order_start, n, order_range)
    quantities   = list(rng.integers(1, 11, n))
    unit_prices  = list(rng.uniform(1.0, 200.0, n).round(2))
    statuses     = list(rng.choice(ORDER_STATUSES, n, p=[0.2, 0.6, 0.2]))

    # payment_date: Completed → order_date + 0-7 days; Pending/Cancelled → None
    _pay_offsets = rng.integers(0, 8, n)
    payment_dates = [
        (order_dates[i] + timedelta(days=int(_pay_offsets[i])))
        if statuses[i] == "Completed" else None
        for i in range(n)
    ]

    # total_amount: correct for base (defects applied per-group below)
    total_amounts = [
        round(quantities[i] * unit_prices[i], 2) for i in range(n)
    ]

    # ── Apply defects ─────────────────────────────────────────────────────────

    # O-01: NULL customer_id (positions 0-99)
    for i in range(DO_NULL_CUST_ID):
        customer_ids[i] = None

    # O-02: NULL product_id (positions 100-299)
    for i in range(DO_NULL_PROD_ID):
        product_ids[100 + i] = None

    # O-03: Orphan customer_id — IDs above N_CUSTOMERS (positions 300-349)
    for i in range(DO_ORPHAN_CUST):
        customer_ids[300 + i] = _ORPHAN_CUST_START + i

    # O-04: Orphan product_id — IDs above N_PRODUCTS (positions 350-379)
    for i in range(DO_ORPHAN_PROD):
        product_ids[350 + i] = _ORPHAN_PROD_START + i

    # O-05: Duplicate order_ids — positions 390-399 copy IDs from 380-389
    for i in range(DO_DUP_ORDER_ID // 2):
        order_ids[390 + i] = order_ids[380 + i]

    # O-06: Zero/negative quantity (positions 400-459)
    # FR-05a: paired total_amount set to a positive inconsistent value
    _neg_qty_pool = [0, -1, -2, -3, -5, -10]
    _inconsistent = list(rng.uniform(10.0, 200.0, DO_NEG_QTY).round(2))
    for i in range(DO_NEG_QTY):
        idx = 400 + i
        quantities[idx]    = _neg_qty_pool[i % len(_neg_qty_pool)]
        total_amounts[idx] = _inconsistent[i]   # positive, wrong

    # O-07: Negative unit_price (positions 460-509)
    # FR-05b: total_amount = qty × (negative price) — consistently negative
    _neg_prices = list(-rng.uniform(0.01, 100.0, DO_NEG_PRICE).round(2))
    for i in range(DO_NEG_PRICE):
        idx = 460 + i
        unit_prices[idx]   = _neg_prices[i]
        total_amounts[idx] = round(quantities[idx] * unit_prices[idx], 2)

    # O-08: total_amount mismatch (positions 510-549)
    # FR-05c: valid positive qty and price; total_amount off by a fixed delta
    _deltas = [10.0, -10.0, 20.0, -20.0, 50.0]
    for i in range(DO_AMT_MISMATCH):
        idx = 510 + i
        total_amounts[idx] = round(total_amounts[idx] + _deltas[i % len(_deltas)], 2)

    # O-09: payment_date < order_date (positions 550-579)
    # FR-05d: order_status forced to 'Completed'
    _back_offsets = rng.integers(1, 31, DO_PAYMENT_BEFORE)
    for i in range(DO_PAYMENT_BEFORE):
        idx = 550 + i
        statuses[idx]      = "Completed"
        payment_dates[idx] = order_dates[idx] - timedelta(days=int(_back_offsets[i]))

    df = pd.DataFrame({
        "order_id":     order_ids,
        "customer_id":  pd.array(customer_ids, dtype=pd.Int64Dtype()),
        "order_date":   order_dates,
        "product_id":   pd.array(product_ids,  dtype=pd.Int64Dtype()),
        "quantity":     quantities,
        "unit_price":   unit_prices,
        "total_amount": total_amounts,
        "order_status": statuses,
        "payment_date": payment_dates,
    })
    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)


# ── Verification ──────────────────────────────────────────────────────────────

def verify_defects(
    customers_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    valid_customer_ids: Set[int],
    valid_product_ids: Set[int],
) -> pd.DataFrame:
    """
    Count seeded defects in generated DataFrames and compare to expected values.

    Parameters
    ----------
    customers_df       : Generated customers DataFrame.
    orders_df          : Generated orders DataFrame.
    valid_customer_ids : Set of customer_ids in customers.csv.
    valid_product_ids  : Set of product_ids in products.csv.

    Returns
    -------
    pd.DataFrame with columns: id, category, file, expected, actual, match.
    Raises AssertionError if any count differs from expected.
    """

    def _malformed_email_count(ser: pd.Series) -> int:
        """Non-null values that fail the email regex."""
        def _bad(x):
            return pd.notna(x) and not bool(_EMAIL_RE.match(str(x)))
        return int(ser.apply(_bad).sum())

    def _orphan_count(ser: pd.Series, valid: Set[int]) -> int:
        """Non-null values not present in the valid set."""
        return int((ser.notna() & ~ser.isin(valid)).sum())

    # Convert date columns to Timestamps for reliable pandas comparisons
    sig_dt  = pd.to_datetime(customers_df["signup_date"], errors="coerce")
    pay_dt  = pd.to_datetime(orders_df["payment_date"],   errors="coerce")
    ord_dt  = pd.to_datetime(orders_df["order_date"],     errors="coerce")
    today_ts = pd.Timestamp(TODAY)

    # Total_amount mismatch: only rows where qty > 0 AND price > 0 (excludes
    # O-06 and O-07 rows which are counted separately under type validation)
    _qty  = orders_df["quantity"].astype(float)
    _price = orders_df["unit_price"].astype(float)
    _amt   = orders_df["total_amount"].astype(float)
    _mismatch = int(
        ((_qty > 0) & (_price > 0) & ((_amt - _qty * _price).abs() > 0.01)).sum()
    )

    rows = [
        # ── Customers ──────────────────────────────────────────────────────
        ("C-01", "NULL email",               "customers.csv", DC_NULL_EMAIL,
         int(customers_df["email"].isna().sum())),

        ("C-02", "Malformed email",          "customers.csv", DC_MALFORMED_EMAIL,
         _malformed_email_count(customers_df["email"])),

        ("C-03", "Future signup_date",       "customers.csv", DC_FUTURE_DATE,
         int((sig_dt > today_ts).sum())),

        ("C-04", "Duplicate customer_id",    "customers.csv", DC_DUP_CUST_ID,
         int(customers_df.duplicated(subset=["customer_id"], keep=False).sum())),

        # ── Orders ─────────────────────────────────────────────────────────
        ("O-01", "NULL customer_id",         "orders.csv", DO_NULL_CUST_ID,
         int(orders_df["customer_id"].isna().sum())),

        ("O-02", "NULL product_id",          "orders.csv", DO_NULL_PROD_ID,
         int(orders_df["product_id"].isna().sum())),

        ("O-03", "Orphan customer_id",       "orders.csv", DO_ORPHAN_CUST,
         _orphan_count(orders_df["customer_id"], valid_customer_ids)),

        ("O-04", "Orphan product_id",        "orders.csv", DO_ORPHAN_PROD,
         _orphan_count(orders_df["product_id"],  valid_product_ids)),

        ("O-05", "Duplicate order_id",       "orders.csv", DO_DUP_ORDER_ID,
         int(orders_df.duplicated(subset=["order_id"], keep=False).sum())),

        ("O-06", "Zero/negative quantity",   "orders.csv", DO_NEG_QTY,
         int((_qty <= 0).sum())),

        ("O-07", "Negative unit_price",      "orders.csv", DO_NEG_PRICE,
         int((_price < 0).sum())),

        ("O-08", "total_amount mismatch",    "orders.csv", DO_AMT_MISMATCH,
         _mismatch),

        ("O-09", "payment_date < order_date","orders.csv", DO_PAYMENT_BEFORE,
         int((pay_dt.notna() & (pay_dt < ord_dt)).sum())),
    ]

    summary = pd.DataFrame(rows, columns=["id", "category", "file", "expected", "actual"])
    summary["match"] = (summary["expected"] == summary["actual"])

    total_actual = int(summary["actual"].sum())
    total_row = pd.DataFrame([{
        "id":       "TOTAL",
        "category": "All seeded defects",
        "file":     "—",
        "expected": 700,
        "actual":   total_actual,
        "match":    total_actual == 700,
    }])
    return pd.concat([summary, total_row], ignore_index=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    Generate all three CSVs, save to data/, and print a defect verification table.
    Exits with a non-zero status if any defect count does not match expectations.
    """
    print("=" * 68)
    print("  Databricks Medallion Pipeline — Data Generation  (SEED=42)")
    print("=" * 68)

    # 1. Products — generate first so valid product_ids are available for orders
    print("\n[1/3] Generating products.csv  (500 rows, no defects) ...")
    products_df = generate_products()
    products_df.to_csv(OUTPUT_DIR / "products.csv", index=False)
    valid_product_ids = set(products_df["product_id"])
    print(f"      OK  {len(products_df):,} rows  ->  {OUTPUT_DIR / 'products.csv'}")

    # 2. Customers
    print("\n[2/3] Generating customers.csv  (10,000 rows, 120 defects) ...")
    customers_df = generate_customers()
    customers_df.to_csv(
        OUTPUT_DIR / "customers.csv", index=False, date_format="%Y-%m-%d"
    )
    valid_customer_ids = set(customers_df["customer_id"])
    print(f"      OK  {len(customers_df):,} rows  ->  {OUTPUT_DIR / 'customers.csv'}")

    # 3. Orders — depends on both valid ID sets generated above
    print("\n[3/3] Generating orders.csv  (100,000 rows, 580 defects) ...")
    orders_df = generate_orders(
        valid_customer_ids=valid_customer_ids,
        valid_product_ids=valid_product_ids,
    )
    orders_df.to_csv(
        OUTPUT_DIR / "orders.csv", index=False, date_format="%Y-%m-%d"
    )
    print(f"      OK  {len(orders_df):,} rows  ->  {OUTPUT_DIR / 'orders.csv'}")

    # 4. Verify all 13 defect categories
    print("\n" + "=" * 68)
    print("  DEFECT VERIFICATION TABLE")
    print("=" * 68)
    summary = verify_defects(
        customers_df, orders_df, valid_customer_ids, valid_product_ids
    )

    pd.set_option("display.max_colwidth", 28)
    pd.set_option("display.width", 100)
    print(summary.to_string(index=False))

    mismatches = summary[~summary["match"]]
    if not mismatches.empty:
        raise AssertionError(
            f"\n\nDefect count mismatches:\n{mismatches.to_string(index=False)}"
        )

    print("\nPASS: All 13 defect categories match expected counts.")
    print(f"  Grand total : 700 seeded defects  "
          f"(120 customers + 580 orders + 0 products)")
    print(f"  Output dir  : {OUTPUT_DIR.resolve()}\n")


if __name__ == "__main__":
    main()
