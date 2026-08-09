# Candidate Information

**Name:** Krishna Jain
**Role:** SE
**Primary Technology Stack:** Python / PySpark, SQL, Databricks
**Primary AI Tool Used:** Cursor
**Project Option Selected:** Data Pipeline (Medallion Architecture)
**Assessment Start Date:** 07/08/2026
**Submission Date:** 21/08/2026

## Tools & Environment

- Databricks: Free Edition (serverless) — Community Edition was retired January 1, 2026
- Unity Catalog: catalog `workspace`, schema `ecommerce_medallion`
- Volume path: `/Volumes/workspace/ecommerce_medallion/raw_data/`
- Languages: Python, PySpark, SQL
- Libraries: PySpark, Delta Lake, pandas, faker
- AI Tool: Cursor (with `.cursor/rules/` persistent project context)

## Dashboard

**Live Dashboard URL:**
https://dbc-dee8a4d8-a132.cloud.databricks.com/dashboardsv3/01f193f3b5b01aa793411e6f3897ebd2/published?o=7474645374027427

**Dashboard name:** Ecommerce Medallion Pipeline — Sales & Data Quality Dashboard
**Tiles:** Top 10 Products by Revenue · Customer Revenue Distribution ·
Customer Segmentation · Data Quality Pass Rates · Yearly Revenue Trend
**Verified:** 2026-08-09 — all 5 tiles rendering against live Gold/Silver Delta tables

## Setup Summary

Run order: `generate_sample_data.py` → upload CSVs to Unity Catalog Volume →
`ingest_all.py` (Bronze) → `create_silver_tables.py` (Silver) →
`create_gold_tables.py` (Gold) → attach `dashboard_queries.sql` to Databricks SQL Dashboard.
Full step-by-step instructions in `README.md` and `database/setup-notes.md`.
