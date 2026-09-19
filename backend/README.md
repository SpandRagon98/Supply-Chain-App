# Backend

FastAPI modular-monolith foundation for Supply Chain Disruption Autopilot.

The Phase 2 schema contains 53 canonical tables across identity, supply network, operations, disruption intelligence, workflow execution, integrations, AI telemetry, notifications, and immutable audit history. All business tables are organization-scoped.

## Run locally

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

`python -m app.seed` inserts or refreshes the deterministic 902-record Nova Electronics dataset in one transaction. Stable identities make repeated runs safe.

Run the worker in a second shell:

```powershell
celery -A app.worker.celery_app worker --loglevel=INFO
```

## Quality checks

```powershell
ruff check .
ruff format --check .
mypy app
pytest
```

The readiness endpoint checks PostgreSQL and Redis. Liveness deliberately does not, so orchestrators can distinguish a failed process from an unavailable dependency.

Repository and service code must receive an explicit `TenantContext`. Use `TenantRepository` or a domain-specific subclass for business data access; direct unscoped reads are not an accepted application pattern.

Workflow code is split across `app.workflows` (contracts, registry, validation, execution), `app.services.workflows` (draft/publish/clone lifecycle), and `app.repositories.workflows` (tenant-scoped persistence). Published workflow versions cannot be changed in place.

Connector code is split across `app.connectors` (adapter contracts, mock sources, registry), `app.services.connectors` (checkpointed execution and lineage), and `app.repositories.connectors` (tenant-scoped configurations and run telemetry).

Signal intelligence is implemented in `app.intelligence` with orchestration in `app.services.signal_intelligence`. Raw connector values remain preserved while normalization, matching, confidence review, deduplication, and incident transitions remain deterministic.
