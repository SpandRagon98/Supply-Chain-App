# Implementation status

## Current phase

| Phase | Status | Date | Evidence |
| --- | --- | --- | --- |
| 0 — Repository Foundation | COMPLETE | 2026-09-19 | Monorepo, Compose dependencies, environment template, CI foundation, and verification script |
| 1 — Backend Foundation | COMPLETE | 2026-09-19 | FastAPI, settings, SQLAlchemy, Alembic, Redis, Celery, logging, errors, health API, and tests validated |
| 2 — Domain Model | COMPLETE | 2026-09-19 | 53 canonical tables, frozen migration, tenant repository/service structure, and isolation tests |
| 3 — Synthetic Demo Data | COMPLETE | 2026-09-19 | Deterministic 892-record Nova Electronics network, idempotent seed command, scenario contracts, and PostgreSQL integration test |
| 4 — Workflow Engine | COMPLETE | 2026-09-19 | Version lifecycle, immutable publication, deep cloning, DAG validation, stage registry/contracts, durable execution, retries, and failure policies |
| 5–13 — Backend capability phases | NOT STARTED | — | — |
| 14–25 — Frontend, E2E, deployment, quality phases | NOT STARTED | — | — |

## Phase 0 decisions

- The target repository was empty; it was initialized as a monorepo.
- PostgreSQL and Redis are the only Compose services at this stage. They are developer dependencies, not application placeholders.
- Backend and frontend directories include scope markers only, preserving the required sequencing: backend is validated before UI implementation.
- CI currently validates the foundation; language-specific lint, tests, type checks, and builds are added with their respective applications.

## Verification

- `docker compose --env-file .env.example config`
- `scripts/verify-phase0.ps1`

## Phase 1 record

- **Date:** 2026-09-19
- **Major files:** `backend/app`, `backend/migrations`, `backend/tests`, `backend/pyproject.toml`, `backend/Dockerfile`, `docs/backend.md`, and the backend CI job.
- **Major decisions:** async SQLAlchemy and asyncpg; versioned API routing; distinct liveness/readiness probes; one shared image for API and workers; structured request IDs; stable success/error envelopes; no domain tables before Phase 2.
- **Tests executed:** Ruff lint and format check, strict mypy, 16 pytest tests with 90% coverage, Alembic head validation, Compose YAML parsing, a live Uvicorn liveness probe, and repository diff checks.
- **Result:** all executable checks passed.

## Technical debt / known limitations

- Docker daemon availability is environment-dependent; Compose syntax can be validated without it, while container health requires a local Docker engine.
- Domain entities and repository/service abstractions begin in Phase 2; the baseline migration intentionally contains no tables.
- The frontend remains deferred until complete backend validation.
- Docker is not installed on the current host, so Compose services could not be started here. Compose validation remains enforced in GitHub Actions.
- Local tests run on Python 3.14 and expose upstream deprecation warnings from the FastAPI/Starlette test client; CI uses the supported project baseline, Python 3.12.

## Phase 2 record

- **Date:** 2026-09-19
- **Major files:** domain model modules under `backend/app/domain/models`, tenant context, repository/service foundations, Alembic revision `46e6e8f4af02`, schema tests, `docs/data-model.md`, and ADR-003.
- **Major decisions:** 53-table canonical schema; one `Facility` table with typed specializations; product-to-product BOM components for multiple levels; JSONB for configurable structures and lineage; explicit tenant context on repositories and services.
- **Tests executed:** 29 pytest tests with 97% coverage, tenant-scope query compilation, complete table-scope contract, Ruff, strict mypy, Alembic head validation, and complete PostgreSQL upgrade SQL compilation.
- **Remaining technical debt:** live PostgreSQL migration execution is unavailable on this Docker-less local host; CI performs a PostgreSQL upgrade/schema-drift/downgrade/upgrade round trip on every push and pull request.

## Phase 3 record

- **Date:** 2026-09-19
- **Major files:** `backend/app/seed`, `backend/tests/test_demo_seed.py`, `scripts/seed-demo.ps1`, and `docs/demo-data.md`.
- **Major decisions:** one fictional Nova Electronics tenant; deterministic UUIDv5 identities and timestamps; one transactional, idempotent seed; realistic connected records rather than disconnected fixtures; multi-level BOMs and explicit scenario pressure points.
- **Dataset:** 892 records covering RBAC, 18 suppliers, 40 materials, 10 products, 10 BOMs, 8 facilities, 176 inventory snapshots, 30 purchase orders, 42 customer orders, 20 shipments, and supporting lines/events/history.
- **Tests executed:** exact dataset contract, stable identity and tenant-scope checks, supplier and BOM topology, operational pressure signals, repeat seeding against PostgreSQL in CI, Ruff, strict mypy, and the full backend suite.
- **Remaining technical debt:** synthetic data is intentionally static and represents one tenant; disruption incidents and derived impact/risk records begin in their dedicated capability phases.

## Phase 4 record

- **Date:** 2026-09-19
- **Major files:** `backend/app/workflows`, `backend/app/services/workflows.py`, `backend/app/repositories/workflows.py`, `backend/tests/test_workflow_engine.py`, and `docs/workflow-engine.md`.
- **Major decisions:** persisted configuration selects versioned registry handlers; NetworkX validates and orders the DAG; service methods are the workflow mutation boundary; published content is immutable and changes require a deep-cloned draft; runtime execution is deterministic and sequential before later Celery parallelization.
- **Tests executed:** topological ordering, cycle/self/disabled-dependency rejection, versioned handler registration, result-state constraints, draft validation, publication immutability, deep version cloning, retry recovery, durable run/stage-run persistence, PostgreSQL lifecycle integration, Ruff, strict mypy, and the complete backend suite.
- **Remaining technical debt:** queue dispatch, conditional-edge evaluation, approval resumption, replay APIs, and parallel branch execution are intentionally deferred until their dependent capability phases. Workflow management HTTP APIs arrive before the frontend management phase.
