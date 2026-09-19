# Backend

FastAPI modular-monolith foundation for Supply Chain Disruption Autopilot.

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
