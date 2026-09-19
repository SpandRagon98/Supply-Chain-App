# ADR-002: Keep decisioning deterministic

**Status:** Accepted — 2026-09-19

## Context

Supply-chain recommendations contain financially material values that must be repeatable, auditable, and explainable.

## Decision

Inventory coverage, stockout projections, BOM propagation, impact, risk, scenario costs and feasibility, and optimization are computed from structured data by deterministic services. AI adapters may only classify unstructured signals or produce narratives based on already calculated structured results.

## Consequences

Every material number can retain lineage to records and calculations. The application remains functional when no external AI key is configured.
