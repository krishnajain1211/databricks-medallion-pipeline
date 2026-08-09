"""
Purpose : Tier 1 transformation unit tests (FR-35 Tier 1 component).
          Tests the correctness of Gold layer aggregation logic using small,
          hand-constructed in-memory pandas DataFrames.  No Databricks connection
          or real CSV loading required — all inputs are defined inline per test.

          Each helper function mirrors the SQL logic of one Gold script:
            compute_sales_by_product()    → 01_sales_by_product.sql
            compute_revenue_by_customer() → 02_revenue_by_customer.sql
            assign_segment()              → 04_customer_segmentation.sql CASE logic

          Tests verify: correct GROUP BY aggregation, LEFT JOIN 0-order customers,
          boundary conditions of the segmentation CASE logic, and that FAILED rows
          are excluded from all aggregations.

Inputs  : Small in-memory pandas DataFrames constructed per test (no file I/O)
Outputs : pytest pass/fail results printed per test function
Phase   : Phase 6 — Testing (Tier 1)
Run     : pytest tests/test_transformations.py -v
          (from the repo root; requires: pip install pytest pandas)
"""

import pandas as pd
import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions — pandas implementations of Gold SQL logic
# ══════════════════════════════════════════════════════════════════════════════

def compute_sales_by_product(
    orders: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """Mirror the GROUP BY aggregation of 01_sales_by_product.sql.

    Filters orders to quality_check_result == 'PASSED', INNER JOINs to products
    on product_id, then aggregates total_orders (COUNT DISTINCT order_id),
    total_revenue (SUM total_amount), and avg_order_value (AVG total_amount)
    per product.

    Args:
        orders:   DataFrame with columns [order_id, product_id, total_amount,
                  quality_check_result]
        products: DataFrame with columns [product_id, product_name, category]

    Returns:
        DataFrame with one row per product, sorted descending by total_revenue.
    """
    passed = orders[orders["quality_check_result"] == "PASSED"]
    merged = passed.merge(
        products[["product_id", "product_name", "category"]],
        on="product_id",
        how="inner",
    )
    result = (
        merged
        .groupby(["product_id", "product_name", "category"], sort=False)
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("total_amount", "sum"),
            avg_order_value=("total_amount", "mean"),
        )
        .reset_index()
    )
    result["total_revenue"]   = result["total_revenue"].round(2)
    result["avg_order_value"] = result["avg_order_value"].round(2)
    return result.sort_values("total_revenue", ascending=False).reset_index(drop=True)


def compute_revenue_by_customer(
    customers: pd.DataFrame,
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """Mirror the LEFT JOIN + GROUP BY logic of 02_revenue_by_customer.sql.

    Includes ALL customers regardless of their quality_check_result (G-08 fix).
    Filters orders to quality_check_result == 'PASSED' in the JOIN condition so
    customers with 0 PASSED orders appear with total_orders=0 and total_revenue=0.

    Args:
        customers: DataFrame with columns [customer_id, customer_name,
                   customer_segment, lifetime_value]
        orders:    DataFrame with columns [order_id, customer_id, total_amount,
                   quality_check_result]

    Returns:
        DataFrame with one row per customer, sorted descending by total_revenue.
    """
    passed_orders = orders[orders["quality_check_result"] == "PASSED"][
        ["order_id", "customer_id", "total_amount"]
    ]
    merged = customers.merge(passed_orders, on="customer_id", how="left")
    result = (
        merged
        .groupby(
            ["customer_id", "customer_name", "customer_segment", "lifetime_value"],
            sort=False,
        )
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("total_amount", "sum"),
            avg_order_value=("total_amount", "mean"),
        )
        .reset_index()
    )
    result["total_orders"]    = result["total_orders"].fillna(0).astype(int)
    result["total_revenue"]   = result["total_revenue"].fillna(0).round(2)
    result["avg_order_value"] = result["avg_order_value"].fillna(0).round(2)
    return result.sort_values("total_revenue", ascending=False).reset_index(drop=True)


def assign_segment(total_revenue: float, total_orders: int) -> str:
    """Mirror the CASE segmentation logic of 04_customer_segmentation.sql.

    Segmentation rules (mutually exclusive, priority order):
      High-Value : total_revenue > 5000
      Repeat     : total_orders >= 2 AND total_revenue <= 5000
      One-Time   : total_orders == 1
      Inactive   : total_orders == 0 (no PASSED orders)

    Args:
        total_revenue: computed SUM(total_amount) from PASSED orders
        total_orders:  COUNT DISTINCT order_id from PASSED orders

    Returns:
        Segment label string.
    """
    if total_revenue > 5000:
        return "High-Value"
    elif total_orders >= 2 and total_revenue <= 5000:
        return "Repeat"
    elif total_orders == 1:
        return "One-Time"
    else:
        return "Inactive"


# ══════════════════════════════════════════════════════════════════════════════
# Test 1 — compute_sales_by_product: correct aggregation over PASSED orders
# ══════════════════════════════════════════════════════════════════════════════

def test_sales_by_product_aggregation():
    """Verify total_orders, total_revenue, avg_order_value per product are correct.

    Mini dataset: 5 orders, 2 products.
      Product 10 (Widget): 2 PASSED orders at $100 and $200 → total $300, avg $150
      Product 20 (Gadget): 3 PASSED orders at $50, $75, $25  → total $150, avg $50
    Output must be sorted descending by total_revenue (Widget first).
    """
    orders = pd.DataFrame({
        "order_id":             [1, 2, 3, 4, 5],
        "product_id":           [10, 10, 20, 20, 20],
        "total_amount":         [100.0, 200.0, 50.0, 75.0, 25.0],
        "quality_check_result": ["PASSED"] * 5,
    })
    products = pd.DataFrame({
        "product_id":   [10, 20],
        "product_name": ["Widget", "Gadget"],
        "category":     ["Electronics", "Accessories"],
    })

    result = compute_sales_by_product(orders, products)

    assert len(result) == 2, f"Expected 2 product rows, got {len(result)}"

    widget = result[result["product_id"] == 10].iloc[0]
    gadget = result[result["product_id"] == 20].iloc[0]

    assert widget["total_orders"]    == 2
    assert widget["total_revenue"]   == pytest.approx(300.0, abs=0.01)
    assert widget["avg_order_value"] == pytest.approx(150.0, abs=0.01)

    assert gadget["total_orders"]    == 3
    assert gadget["total_revenue"]   == pytest.approx(150.0, abs=0.01)
    assert gadget["avg_order_value"] == pytest.approx(50.0, abs=0.01)

    # Widget (total_revenue=300) must appear before Gadget (150) in sort order
    assert result.iloc[0]["product_id"] == 10, "Result must be sorted desc by total_revenue"


# ══════════════════════════════════════════════════════════════════════════════
# Test 2 — compute_revenue_by_customer: LEFT JOIN preserves 0-order customers
# ══════════════════════════════════════════════════════════════════════════════

def test_revenue_by_customer_aggregation():
    """Verify totals per customer and that customers with 0 PASSED orders appear.

    Mini dataset:
      Alice (ID 1): 2 PASSED orders — $200 + $300 = $500 total, avg $250
      Bob   (ID 2): 1 PASSED order  — $150, avg $150
      Carol (ID 3): no orders — must appear with total_orders=0, total_revenue=0
    """
    customers = pd.DataFrame({
        "customer_id":      [1, 2, 3],
        "customer_name":    ["Alice", "Bob", "Carol"],
        "customer_segment": ["Premium", "Standard", "Basic"],
        "lifetime_value":   [5000.0, 3000.0, 1000.0],
    })
    orders = pd.DataFrame({
        "order_id":             [101, 102, 103],
        "customer_id":          [1, 1, 2],
        "total_amount":         [200.0, 300.0, 150.0],
        "quality_check_result": ["PASSED", "PASSED", "PASSED"],
    })

    result = compute_revenue_by_customer(customers, orders)

    assert len(result) == 3, f"Expected 3 customer rows, got {len(result)}"

    alice = result[result["customer_id"] == 1].iloc[0]
    bob   = result[result["customer_id"] == 2].iloc[0]
    carol = result[result["customer_id"] == 3].iloc[0]

    assert alice["total_orders"]    == 2
    assert alice["total_revenue"]   == pytest.approx(500.0, abs=0.01)
    assert alice["avg_order_value"] == pytest.approx(250.0, abs=0.01)

    assert bob["total_orders"]      == 1
    assert bob["total_revenue"]     == pytest.approx(150.0, abs=0.01)
    assert bob["avg_order_value"]   == pytest.approx(150.0, abs=0.01)

    # Carol has no orders — LEFT JOIN must preserve her with zero values
    assert carol["total_orders"]    == 0
    assert carol["total_revenue"]   == pytest.approx(0.0, abs=0.01)
    assert carol["avg_order_value"] == pytest.approx(0.0, abs=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# Test 3 — assign_segment: all four tiers + boundary conditions
# ══════════════════════════════════════════════════════════════════════════════

def test_customer_segmentation_logic():
    """Verify the CASE segmentation rules for all four tiers and key boundary values.

    Boundary cases explicitly tested:
      total_revenue = 5001, total_orders = 1  → High-Value (revenue wins over order count)
      total_revenue = 5000, total_orders = 2  → Repeat (exactly at the threshold, not above)
      total_revenue = 5000, total_orders = 0  → Inactive (no orders, despite revenue=5000)
    """
    # Core tier assignments
    assert assign_segment(total_revenue=8000, total_orders=5)  == "High-Value"
    assert assign_segment(total_revenue=3000, total_orders=4)  == "Repeat"
    assert assign_segment(total_revenue=200,  total_orders=1)  == "One-Time"
    assert assign_segment(total_revenue=0,    total_orders=0)  == "Inactive"

    # Boundary: revenue > 5000 overrides order count — still High-Value with 1 order
    assert assign_segment(total_revenue=5001, total_orders=1)  == "High-Value"

    # Boundary: exactly at threshold (5000) is NOT High-Value
    assert assign_segment(total_revenue=5000, total_orders=2)  == "Repeat"

    # Boundary: 0 orders is always Inactive, even if total_revenue somehow > 0
    # (edge case — shouldn't occur with real data, but tests rule priority)
    assert assign_segment(total_revenue=5000, total_orders=0)  == "Inactive"

    # Boundary: exactly 2 orders at low revenue → Repeat (not One-Time)
    assert assign_segment(total_revenue=100,  total_orders=2)  == "Repeat"


# ══════════════════════════════════════════════════════════════════════════════
# Test 4 — quality_check_result filter: FAILED rows excluded from aggregations
# ══════════════════════════════════════════════════════════════════════════════

def test_quality_check_result_filter_excluded_from_product_agg():
    """Verify that FAILED_* rows do not contribute to Gold aggregations.

    4-order dataset for one product: 2 PASSED, 1 FAILED_COMPLETENESS, 1 FAILED_UNIQUENESS.
    Only the 2 PASSED orders (total_amount=$100+$200=$300) should appear in the output.
    The FAILED orders (total_amount=$999 + $888) must be completely excluded.
    """
    orders = pd.DataFrame({
        "order_id":             [1, 2, 3, 4],
        "product_id":           [10, 10, 10, 10],
        "total_amount":         [100.0, 200.0, 999.0, 888.0],
        "quality_check_result": [
            "PASSED",
            "PASSED",
            "FAILED_COMPLETENESS",
            "FAILED_UNIQUENESS",
        ],
    })
    products = pd.DataFrame({
        "product_id":   [10],
        "product_name": ["Widget"],
        "category":     ["Electronics"],
    })

    result = compute_sales_by_product(orders, products)

    assert len(result) == 1, f"Expected 1 product row, got {len(result)}"
    widget = result.iloc[0]

    # Only the 2 PASSED orders should be aggregated
    assert widget["total_orders"]  == 2
    assert widget["total_revenue"] == pytest.approx(300.0, abs=0.01)

    # Confirm the FAILED amounts were not included (would give 300+999+888=2187)
    assert widget["total_revenue"] != pytest.approx(2187.0, abs=0.01), (
        "FAILED rows appear to have been included in the aggregation"
    )


def test_quality_check_result_filter_excluded_from_customer_agg():
    """Verify FAILED orders are excluded from customer revenue aggregations.

    Alice has 1 PASSED order ($200) and 1 FAILED order ($500).
    Her gold_revenue_by_customer entry should show total_revenue=$200, not $700.
    """
    customers = pd.DataFrame({
        "customer_id":      [1],
        "customer_name":    ["Alice"],
        "customer_segment": ["Premium"],
        "lifetime_value":   [5000.0],
    })
    orders = pd.DataFrame({
        "order_id":             [101, 102],
        "customer_id":          [1, 1],
        "total_amount":         [200.0, 500.0],
        "quality_check_result": ["PASSED", "FAILED_BUSINESS_LOGIC"],
    })

    result = compute_revenue_by_customer(customers, orders)

    assert len(result) == 1
    alice = result.iloc[0]

    assert alice["total_orders"]  == 1, "Only 1 PASSED order should be counted"
    assert alice["total_revenue"] == pytest.approx(200.0, abs=0.01), (
        "FAILED_BUSINESS_LOGIC order must not contribute to total_revenue"
    )
