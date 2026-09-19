# Supply Chain Disruption Autopilot

An enterprise decisioning platform that detects supply-chain disruptions, maps them to an organization's network, calculates deterministic business impact, recommends mitigations, routes approvals, executes integration actions, and verifies outcomes.

The application is being delivered in deliberate phases. Phase 0 establishes the portable monorepo and local dependency environment; application services and UI begin in later phases.

## Repository layout

```text
backend/          FastAPI modular-monolith service (Phase 1)
frontend/         Next.js application (Phase 14)
docs/             Architecture, operating docs, and ADRs
infrastructure/   Deployment-neutral infrastructure definitions
scripts/          Repeatable developer and verification commands
.github/workflows CI foundations
```

## Local startup

1. Copy `.env.example` to `.env` and replace the local database password.
2. Start platform dependencies:

   ```powershell
   docker compose up -d postgres redis
   ```

3. Confirm their health:

   ```powershell
   docker compose ps
   ```

The API, worker, migrations, and frontend are intentionally not present until their scheduled implementation phases. See [implementation status](docs/implementation-status.md) for the current scope and [architecture](docs/architecture.md) for target boundaries.

## Planned developer commands

| Purpose | Command |
| --- | --- |
| Validate Phase 0 structure and Compose configuration | `powershell -ExecutionPolicy Bypass -File scripts/verify-phase0.ps1` |
| Start dependencies | `docker compose up -d postgres redis` |
| Stop dependencies | `docker compose down` |
| Run API | Added in Phase 1 |
| Run worker | Added in Phase 1 |
| Run migrations / seed data | Added in Phases 2–3 |
| Run frontend | Added in Phase 14 |

## Design guardrails

- Deterministic services own numerical business facts, graph traversal, risk scoring, feasibility, and optimization.
- AI providers may classify, extract, summarize, and explain only after structured data and calculations exist.
- The initial backend is a modular monolith, not a collection of microservices.
- All tenant-scoped domain data will use organization isolation and RBAC.
- Workflow definitions and their published versions will be persisted and immutable after publication.

## License

This project is released under the [MIT License](LICENSE).
