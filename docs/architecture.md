# Architecture

## Target architecture

The product starts as a Python modular monolith with a separately deployed Next.js client. PostgreSQL is the system of record; Redis supports asynchronous work and Celery task dispatch. Connectors and AI providers are replaceable adapters behind explicit interfaces.

```mermaid
flowchart LR
  UI[Next.js operations console] --> API[FastAPI modular monolith]
  API --> DB[(PostgreSQL)]
  API --> Queue[(Redis)]
  Queue --> Worker[Celery workers]
  Worker --> DB
  Worker --> Connectors[ERP, weather, news, shipment adapters]
  Worker --> AI[Optional AI provider]
```

## Decision boundary

```mermaid
flowchart LR
  Signals --> Deterministic[Normalization, entity resolution, graph analysis,
  inventory, impact, risk, scenario feasibility, optimization]
  Deterministic --> Decisions[Recommendations and approval requests]
  Decisions --> AI[Optional explanation and narrative]
  Decisions --> Execution[Idempotent integration actions]
```

Numerical business claims originate only from structured records and deterministic calculations. AI outputs are never authoritative for inventory, revenue, risk, feasibility, or optimization values.

## Initial service boundaries

- `api`: HTTP, authentication boundary, RBAC, response envelopes, and orchestration entry points.
- `domain`: supply-chain entities, calculation services, workflow engine, policies, and audit events.
- `infrastructure`: database repositories, connectors, Celery tasks, AI adapters, and observability.
- `frontend`: operational UI consuming aggregation and resource APIs.

This layout stays within one backend deployable until real operational needs justify extracting a service.
