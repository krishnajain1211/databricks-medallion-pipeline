# Design Notes

> Architecture overview, layer-by-layer design decisions, and debugging approach.
> Sections are filled in incrementally as each phase completes.

## Architecture Overview

_[High-level design of Bronze → Silver → Gold → Dashboard — Mermaid diagram (P-03) to be added in Phase 0.]_

## Data Model & Schema

_[Descriptions of customers, orders, products tables — see data-model.md for full data dictionary.]_

## Bronze Layer Design

_[Raw ingestion from Unity Catalog Volumes, schema inference, metadata logging — to be documented in Phase 2.]_

## Silver Layer Design

_[Four quality checks (Completeness, Uniqueness, Type Validation, Referential Integrity) + Business Logic bonus,
quality_check_result column, quality metrics report — to be documented in Phase 3.]_

## Gold Layer Design

_[Four aggregation tables sourced from Silver PASSED rows — to be documented in Phase 4.]_

## Data Quality Validation Strategy

_[See data-quality-strategy.md for full strategy. Summary to be added here in Phase 3.]_

## Debugging Approach

_[See debugging-notes.md for the debugging log. Methodology summary to be added here in Phase 7.]_
