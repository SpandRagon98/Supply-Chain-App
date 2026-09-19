# Supply Chain Disruption Autopilot

An enterprise decisioning platform that detects supply-chain disruptions, maps them to an organization's network, calculates deterministic business impact, recommends mitigations, routes approvals, executes integration actions, and verifies outcomes.

The application is being delivered in deliberate phases. The backend foundation now provides the API process, worker, database migration framework, structured logging, and operational health checks. Domain capabilities arrive in subsequent backend phases before frontend implementation begins.

## Repository layout

```text
backend/          FastAPI modular-monolith service
frontend/         Next.js application (Phase 14)
docs/             Architecture, operating docs, and ADRs
infrastructure/   Deployment-neutral infrastructure definitions
scripts/          Repeatable developer and verification commands
.github/workflows CI foundations
```

## Local startup

1. Copy `.env.example` to `.env` and replace the local database password.
2. Build and start the backend stack:

   ```powershell
   docker compose up --build -d
   ```

3. Apply database migrations:

   ```powershell
   docker compose run --rm api alembic upgrade head
   ```

4. Confirm service health:

   ```powershell
   docker compose ps
   Invoke-RestMethod http://localhost:8000/api/v1/health/ready
   ```

Interactive API documentation is available at `http://localhost:8000/docs` outside production. The frontend remains intentionally deferred until complete backend validation. See [implementation status](docs/implementation-status.md) for current scope and [backend documentation](docs/backend.md) for service details.

## Planned developer commands

| Purpose | Command |
| --- | --- |
| Validate Phase 0 structure and Compose configuration | `powershell -ExecutionPolicy Bypass -File scripts/verify-phase0.ps1` |
| Start complete backend stack | `docker compose up --build -d` |
| Stop dependencies | `docker compose down` |
| Run API locally | `cd backend; uvicorn app.main:app --reload` |
| Run worker locally | `cd backend; celery -A app.worker.celery_app worker --loglevel=INFO` |
| Run backend checks | `cd backend; ruff check .; mypy app; pytest` |
| Run migrations | `docker compose run --rm api alembic upgrade head` |
| Seed data | Added in Phase 3 |
| Run frontend | Added in Phase 14 |

## Design guardrails

- Deterministic services own numerical business facts, graph traversal, risk scoring, feasibility, and optimization.
- AI providers may classify, extract, summarize, and explain only after structured data and calculations exist.
- The initial backend is a modular monolith, not a collection of microservices.
- All tenant-scoped domain data will use organization isolation and RBAC.
- Workflow definitions and their published versions will be persisted and immutable after publication.

## License

This project is released under the [MIT License](LICENSE).
