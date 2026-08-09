# AI Prompts — Dashboard

> Prompt history for all exchanges related to `dashboard_queries.sql`
> and `DASHBOARD_GUIDE.md`. Entries are added after each significant exchange.
> Format: see Section 5 of `requirements-analysis.md` for the standard entry template.

---

## Prompt 1: Implement dashboard_queries.sql and DASHBOARD_GUIDE.md

**Date:** 2026-08-09
**Phase:** 5 — Dashboard
**User prompt (summary):** Phase 4 Gold verified (FR-26 PASS on both tables, correct
row counts confirmed in Databricks). Proceed to Phase 5: read FR-27 through FR-32;
write `src/dashboard/dashboard_queries.sql` (3+ queries sourced from Gold tables)
and `src/dashboard/DASHBOARD_GUIDE.md` (step-by-step Databricks SQL Dashboard setup);
ask if anything's ambiguous; log to `ai-prompts/dashboard.md`.

**AI response summary:**

### Files written
| File | Description |
|------|------------|
| `src/dashboard/dashboard_queries.sql` | Five labelled query blocks with chart config comments |
| `src/dashboard/DASHBOARD_GUIDE.md` | End-to-end dashboard setup guide (prerequisites → publish) |

### Queries implemented

| Tile | FR / Polish | Chart type | Source table | Key design choice |
|------|------------|------------|-------------|-------------------|
| 1 — Top 10 Products | FR-28 | Bar chart | `gold_sales_by_product` | `LIMIT 10 ORDER BY total_revenue DESC`; colour series on `category` |
| 2 — Revenue Distribution | FR-29 | Histogram | `gold_revenue_by_customer` | Returns raw `total_revenue` per customer; Databricks bins automatically. `WHERE total_revenue > 0` excludes Inactive spike at zero (removable) |
| 3 — Segmentation | FR-30 | Pie chart | `gold_customer_segmentation` | Added `pct_of_customers` and `pct_of_revenue` window columns for tooltip |
| 4 — Quality Pass Rate | P-04 | Bar chart | `silver_quality_metrics` | `CONCAT(check_name, ' (', entity, ')')` as `check_label`; grouped by `entity` |
| 5 — Daily Trend | bonus | Line chart | `gold_daily_weekly_trends` | `WHERE period_type = 'daily'` to use the existing UNION ALL table at daily grain |

### DASHBOARD_GUIDE.md structure
- **Prerequisites**: Gold tables populated, SQL Warehouse running
- **Step 1**: Create dashboard with name
- **Step 2**: Add 5 datasets (one per query) with expected row counts
- **Step 3**: Add tiles — full chart-type config settings for each tile
- **Step 4**: Recommended canvas layout (ASCII art diagram)
- **Step 5**: Publish and share, including where to put the dashboard URL
- **Refresh**: How to re-run pipeline and refresh tiles
- **Troubleshooting**: 5 common issues with fixes

### Unambiguous design choices (not asked, documented here)
- **Histogram raw vs. pre-bucketed**: chose raw values; Databricks histogram
  visualization handles binning, giving reviewers the flexibility to set bin size
  in the UI rather than fixing it in SQL.
- **Inactive customers excluded from histogram**: `WHERE total_revenue > 0`
  prevents a zero-revenue spike that would compress the meaningful distribution.
  The filter is noted as removable in both the SQL comment and the guide.
- **5th bonus tile**: `gold_daily_weekly_trends` exists with daily+weekly data
  but had no FR-assigned visualization. Added as a line chart bonus tile since
  the data is there and the guide explains it clearly.

**Evaluation:** Accepted — pending Databricks dashboard creation.
