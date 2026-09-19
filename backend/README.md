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
uvicorn app.main:app --reload
```

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
