# ADR-001: Start with a modular monolith

**Status:** Accepted — 2026-09-19

## Context

The product requires tightly coordinated workflow execution, supply-network traversal, deterministic calculations, approvals, auditability, and integration adapters. Premature service decomposition would add operational complexity before the boundaries are validated.

## Decision

Build one FastAPI deployable with explicit domain and infrastructure modules. Use internal interfaces for workflow stages, connectors, and AI providers. Run long-running work through Celery and Redis.

## Consequences

Modules may evolve into independently deployed services only when ownership, scale, reliability, or data boundaries demonstrate a concrete need. No controller should become the business-engine boundary.
