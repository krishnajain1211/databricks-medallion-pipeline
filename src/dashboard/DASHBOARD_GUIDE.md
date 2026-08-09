# Dashboard Guide — E-Commerce Medallion Pipeline

Step-by-step instructions for building the Databricks SQL Dashboard from the
five queries in `src/dashboard/dashboard_queries.sql`.

---

## Prerequisites

Before opening the dashboard builder:

1. **Gold layer complete** — `create_gold_tables.py` has been run and all four
   Gold tables exist with data:
   - `workspace.ecommerce_medallion.gold_sales_by_product`
   - `workspace.ecommerce_medallion.gold_revenue_by_customer`
   - `workspace.ecommerce_medallion.gold_daily_weekly_trends`
   - `workspace.ecommerce_medallion.gold_customer_segmentation`
   - `workspace.ecommerce_medallion.silver_quality_metrics` (from Phase 3)

2. **SQL Warehouse running** — In Databricks Free Edition a Serverless SQL
   Warehouse is automatically available.  Confirm it is running:
   - Left sidebar → **SQL** → **SQL Warehouses**
   - If the warehouse shows "Stopped", click **Start** and wait ~1 minute.

---

## Step 1 — Create the Dashboard

1. In the left sidebar, click **Dashboards** (under the SQL section, or search
   "Dashboards" in the top search bar).
2. Click **Create dashboard** (top-right button).
3. Name the dashboard: `E-Commerce Medallion Pipeline — Overview`.
4. You are now in the Dashboard editor.  You will see a blank canvas and a
   **Datasets** panel on the left.

---

## Step 2 — Add Datasets (one per query)

Each tile needs its own Dataset.  Repeat the steps below **five times**, once
per query block in `dashboard_queries.sql`.

For each dataset:

1. In the **Datasets** panel (left side of the editor), click **+ Add dataset**
   (or the `+` icon).
2. A SQL editor tab opens.  Paste the query from `dashboard_queries.sql`.
3. Click **Run** to verify the query returns data.
4. Name the dataset as indicated in the table below, then click **Save**.

| Dataset name | Query in `dashboard_queries.sql` | Expected rows |
|---|---|---|
| `top_10_products` | TILE 1 — Top 10 Products by Revenue | 10 |
| `customer_revenue_dist` | TILE 2 — Customer Revenue Distribution | ~9,980 |
| `customer_segmentation` | TILE 3 — Customer Segmentation Breakdown | 4 |
| `quality_pass_rates` | TILE 4 — Data Quality Pass Rate | 10 |
| `daily_revenue_trend` | TILE 5 — Daily Revenue Trend | ~365 |

---

## Step 3 — Add Tiles (one per visualization)

After all five datasets are saved, add tiles to the canvas.

In the dashboard canvas, click **+ Add visualization** (or drag from the
Visualizations panel on the right).

---

### Tile 1 — Top 10 Products by Revenue (Bar Chart) — FR-28

1. Click **+ Add visualization** → choose **Bar chart**.
2. **Dataset**: select `top_10_products`.
3. Configure:
   - **X column**: `product_name`
   - **Y columns**: `total_revenue`
   - **Group by / Color**: `category`  *(gives each category a distinct colour)*
   - **Sort**: Descending by `total_revenue` (already ordered in the query)
   - **Label**: `Top 10 Products by Revenue`
4. In **Tooltip** settings, add `total_orders` and `avg_order_value`.
5. Click **Save**.  Resize the tile to span the full width of the canvas row.

---

### Tile 2 — Customer Revenue Distribution (Histogram) — FR-29

1. Click **+ Add visualization** → choose **Histogram**.
2. **Dataset**: select `customer_revenue_dist`.
3. Configure:
   - **X column**: `total_revenue`
   - **Bin size**: `500`  *(each bar = $500 revenue range)*
   - **Label**: `Customer Revenue Distribution`
4. Optional — add `customer_segment` as a **Colour** column to see how segments
   map onto the distribution.
5. Click **Save**.

> **Note:** Inactive customers (`total_revenue = 0`) are excluded from this
> query by design so the histogram is not skewed by a spike at zero.  Remove
> the `WHERE total_revenue > 0` clause in the dataset query if you want to
> include them.

---

### Tile 3 — Customer Segmentation Breakdown (Pie Chart) — FR-30

1. Click **+ Add visualization** → choose **Pie chart**.
2. **Dataset**: select `customer_segmentation`.
3. Configure:
   - **Label column**: `segment_type`
   - **Value column**: `customer_count`
   - **Label**: `Customer Segments`
4. In **Tooltip** settings, add `avg_revenue`, `total_revenue`,
   `pct_of_customers`, `pct_of_revenue`.
5. Click **Save**.

---

### Tile 4 — Data Quality Pass Rate (Bar Chart) — P-04 bonus

1. Click **+ Add visualization** → choose **Bar chart**.
2. **Dataset**: select `quality_pass_rates`.
3. Configure:
   - **X column**: `check_label`
   - **Y columns**: `pass_rate_pct`
   - **Group by / Color**: `entity`  *(customers vs. orders side-by-side)*
   - **Y-axis range**: 0 – 100  *(set manually to make percentage clear)*
   - **Label**: `Silver Layer Quality Pass Rates`
4. Add a **Reference line** at `y = 100` (labelled "Perfect pass") to show the
   100 % target.
5. In **Tooltip** settings, add `total_rows`, `rows_passed`, `rows_failed`.
6. Click **Save**.

> **Note:** Pass rates below 100 % are expected — they reflect the seeded
> defects in the synthetic data.  The completeness and uniqueness checks will
> show the lowest rates.

---

### Tile 5 — Daily Revenue Trend (Line Chart) — bonus

1. Click **+ Add visualization** → choose **Line chart**.
2. **Dataset**: select `daily_revenue_trend`.
3. Configure:
   - **X column**: `order_date`  *(set axis type to Date/Time)*
   - **Y columns**: `total_revenue`
   - **Secondary Y column** (optional): `total_orders`
   - **Label**: `Daily Revenue Trend`
4. Click **Save**.

---

## Step 4 — Arrange the Canvas

Recommended layout (drag tiles to resize and position):

```
┌──────────────────────────────────────────────────────────────────┐
│  Tile 1: Top 10 Products by Revenue          (full width, tall)  │
├───────────────────────────────┬──────────────────────────────────┤
│  Tile 3: Customer Segments    │  Tile 4: Quality Pass Rates      │
│  (half width, pie chart)      │  (half width, bar chart)         │
├───────────────────────────────┴──────────────────────────────────┤
│  Tile 5: Daily Revenue Trend                 (full width)        │
├──────────────────────────────────────────────────────────────────┤
│  Tile 2: Customer Revenue Distribution       (full width)        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Step 5 — Publish and Share

1. Click **Publish** (top-right) to save the final layout.
2. To share with reviewers: click the **Share** icon → add their email address
   or set to **"Anyone with the link can view"**.
3. Copy the dashboard URL and include it in `candidate-info.md` under the
   "Dashboard URL" field.

---

## Refreshing the Dashboard

The dashboard reads directly from the Gold Delta tables.  To reflect a fresh
pipeline run:

1. Re-run `create_silver_tables.py` → `create_gold_tables.py` in Databricks.
2. Return to the dashboard and click **Refresh** (the circular-arrow icon in the
   top-right of the dashboard viewer).  All tiles will re-query the updated tables.

There is no scheduled refresh configured by default in Databricks Free Edition.
If you want automatic refresh, open each dataset in the editor and set a
**Refresh schedule** (e.g., daily at 08:00).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Query fails with "Table not found" | Gold tables not yet created | Re-run `create_gold_tables.py` |
| Histogram shows only one bar | Bin size too large | Set bin size to 500 in chart config |
| Pie chart shows no data | `customer_segmentation` dataset not saved | Re-add dataset from TILE 3 query |
| SQL Warehouse "Stopped" error | Warehouse auto-stopped after idle period | Go to SQL Warehouses → Start |
| Pass-rate tile shows no reference line | Reference lines not available in current Databricks tier | Skip the reference line; note the 100% target in the tile title |
