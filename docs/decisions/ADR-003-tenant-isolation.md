# ADR-003: Require explicit tenant context for business data access

**Status:** Accepted — 2026-09-19

## Context

Nearly every product record belongs to one organization. Relying on controllers to remember an organization filter would make accidental cross-tenant reads likely and difficult to review.

## Decision

All business entities inherit a common `TenantEntity` with a required indexed `organization_id`. Repositories require an immutable `TenantContext`, add its organization predicate to every read, and reject mutations whose entity organization differs. Services receive the same context and may not construct an unscoped repository.

The context will be derived from authenticated server-side identity claims. Client-provided resource IDs never change the active organization.

## Consequences

Tenant scope is explicit in constructors, queries, tests, logs, and code review. Cross-entity write services must resolve referenced IDs through the same tenant-scoped repositories. Platform administration that legitimately spans organizations will use a separate, narrowly authorized interface rather than bypassing tenant repositories.
