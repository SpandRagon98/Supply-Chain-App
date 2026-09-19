# Implementation status

## Current phase

| Phase | Status | Date | Evidence |
| --- | --- | --- | --- |
| 0 — Repository Foundation | COMPLETE | 2026-09-19 | Monorepo, Compose dependencies, environment template, CI foundation, and verification script |
| 1 — Backend Foundation | COMPLETE | 2026-09-19 | FastAPI, settings, SQLAlchemy, Alembic, Redis, Celery, logging, errors, health API, and tests validated |
| 2 — Domain Model | COMPLETE | 2026-09-19 | 53 canonical tables, frozen migration, tenant repository/service structure, and isolation tests |
| 3 — Synthetic Demo Data | COMPLETE | 2026-09-19 | Deterministic 892-record Nova Electronics network, idempotent seed command, scenario contracts, and PostgreSQL integration test |
| 4 — Workflow Engine | COMPLETE | 2026-09-19 | Version lifecycle, immutable publication, deep cloning, DAG validation, stage registry/contracts, durable execution, retries, and failure policies |
| 5 — Connector Framework | COMPLETE | 2026-09-19 | Versioned adapters, ERP/weather/news/shipment/supplier mocks, checkpointed runs, canonical sink boundary, and source lineage |
| 6 — Signal + Incident Intelligence | COMPLETE | 2026-09-19 | Raw-preserving normalization, deterministic detection, entity resolution, confidence review, incident deduplication, and guarded lifecycle |
| 7 — Supply network + impact | COMPLETE | 2026-09-19 | Deterministic NetworkX BOM traversal, inventory coverage, stockout, customer and revenue exposure |
| 8 — Risk engine | COMPLETE | 2026-09-19 | Configurable explainable factors and durable risk assessments |
| 9 — Scenario + optimization | COMPLETE | 2026-09-19 | Feasible mitigation scenarios and OR-Tools CBC objective selection |
| 10 — AI layer | COMPLETE | 2026-09-19 | Optional structured providers, prompt versioning, and run telemetry |
| 11 — Recommendation + approval | COMPLETE | 2026-09-19 | Explainable recommendation, approval policy routing, and decision history |
| 12 — Execution + verification | COMPLETE | 2026-09-19 | Idempotent mock actions, execution results, and outcome resolution logic |
| 13 — Complete backend validation | COMPLETE | 2026-09-19 | Offline Taiwan Typhoon chain test from signal through verification |
| 14 — Frontend foundation | COMPLETE | 2026-09-19 | Next.js / TypeScript foundation, theme tokens, responsive layout primitives, container build |
| 15 — App shell | COMPLETE | 2026-09-19 | Responsive sidebar, top bar, navigation, search affordance, and workspace shell |
| 16 — Command center dashboard | COMPLETE | 2026-09-19 | API-health-aware command center with non-fabricated KPI states |
| 17 — Operational screens | COMPLETE | 2026-09-19 | Disruptions, network, suppliers, inventory, shipments, and incident-detail screens |
| 18–25 — Decision screens, workflow UX, simulation, deployment, quality | NOT STARTED | — | — |

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

## Phase 5 record

- **Date:** 2026-09-19
- **Major files:** `backend/app/connectors`, `backend/app/services/connectors.py`, `backend/app/repositories/connectors.py`, `backend/tests/test_connectors.py`, and `docs/connectors.md`.
- **Major decisions:** adapters only fetch immutable raw records; versioned registry references avoid provider branches in services; canonical mapping occurs behind a sink protocol; only successful runs advance checkpoints; telemetry stores hashes/source references rather than secrets or duplicate payloads.
- **Mock coverage:** ERP inventory/POs, Taiwan weather, Singapore port news, shipment delays, supplier shutdown/capacity, and a deliberately low-confidence rumor. Five mock connector configurations extend the Nova dataset from 892 to 897 records.
- **Tests executed:** deterministic payload hashing, record/batch validation, adapter registry behavior, all five mock feeds, checkpoint advancement, lineage content, durable failures, unavailable configuration, tenant enforcement, Nova seed contracts, PostgreSQL connector-run persistence, Ruff, strict mypy, and the complete backend suite.
- **Remaining technical debt:** production HTTP clients, credential resolution, scheduling, rate limits, provider pagination, and canonical signal sinks arrive with real integration work. Phase 6 implements normalization and signal/incident persistence using this sink boundary.

## Phase 6 record

- **Date:** 2026-09-19
- **Major files:** `backend/app/intelligence`, `backend/app/services/signal_intelligence.py`, `backend/app/repositories/signals.py`, `backend/tests/test_signal_intelligence.py`, and `docs/signal-intelligence.md`.
- **Major decisions:** preserve raw and normalized payloads separately; keep detection and matching deterministic; configure thresholds per signal source; group signals using category/location/relevant-entity identities; never auto-clear a review gate merely because later corroboration raises confidence.
- **Demo behavior:** the five mock feeds yield 10 canonical signals grouped into 5 incidents; two Taiwan weather records group together, four Singapore port records group together, and the low-confidence Kyoto rumor is review-gated. Five seeded signal sources extend Nova from 897 to 902 records.
- **Tests executed:** country/unit/identifier normalization, threshold validation, detection/filtering, exact/fuzzy/multi-match resolution, low-confidence review, idempotent replay, weather and port deduplication, lifecycle guards, tenant enforcement, PostgreSQL full mock ingestion, Ruff, strict mypy, and the complete backend suite.
- **Remaining technical debt:** review assignment APIs, manual entity-match correction, location master data/ports, richer currency and unit conversion, and provider-specific normalization rules remain future work. Phase 7 consumes resolved incidents for graph traversal and impact calculations.

## Phases 7–13 record

- **Date:** 2026-09-19
- **Major files:** `backend/app/impact`, `backend/app/risk`, `backend/app/optimization`, `backend/app/ai`, `backend/app/recommendations`, `backend/app/execution`, their application services, phase-specific tests, and the corresponding architecture notes in `docs/`.
- **Major decisions:** business calculations, risk, scenario comparison, recommendation selection, approval routing, and verification remain deterministic and independent from the optional AI provider; each numerical output retains structured source data or calculation lineage; mock execution produces a stable external reference for a given idempotency key.
- **Taiwan Typhoon validation:** a mock Taiwan weather signal resolves to Formosa's supplier site, traces its material dependencies through the Nova BOM, calculates exposure, scores risk, selects an alternative source with OR-Tools, produces a recommendation, routes approval, executes a mock action, and verifies the predicted protected revenue.
- **Tests executed:** phase-focused unit tests, strict Ruff and mypy checks, and the complete backend suite. PostgreSQL persistence integration remains exercised in CI where `TEST_DATABASE_URL` is available.
- **Remaining technical debt:** full authenticated, paginated operational APIs and workflow-stage bindings are the next backend expansion; external production adapters, job scheduling, and a live outcome monitor remain intentionally out of scope before the frontend phases.

## Phases 14–17 record

- **Date:** 2026-09-19
- **Major files:** `frontend/app`, `frontend/components`, `frontend/lib`, `frontend/Dockerfile`, `frontend/package.json`, `docker-compose.production.yml`, `.github/workflows/deploy.yml`, and `docs/deployment.md`.
- **Major decisions:** original light enterprise design tokens are defined once in global CSS; dashboard, supplier, inventory, shipment, and incident screens consume tenant-scoped read APIs; screens retain explicit unavailable states when an API or tenant data is unreachable, rather than fabricating business values.
- **Deployment:** CI runs frontend type checking and production builds. `deploy.yml` publishes immutable backend and frontend images to GHCR and supports a protected, manually triggered Docker Compose deployment using GitHub environment secrets.
- **Tests executed:** TypeScript no-emit type check, production Next build, dependency audit with no reported vulnerabilities, and full backend quality suite. Local Docker Compose runtime validation is blocked because Docker is not installed on this host; CI retains Compose validation.
