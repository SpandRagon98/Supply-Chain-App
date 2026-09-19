# Deployment

The `Build and deploy` GitHub Actions workflow in `.github/workflows/deploy.yml` derives lowercase GitHub Container Registry paths, publishes immutable SHA-tagged backend and frontend images on `main`, and can deploy those exact images to a protected Docker Compose host. No credential is stored in the repository.

## One-time host setup

1. Install Docker Engine with the Compose plugin.
2. Create the directory referenced by the `DEPLOY_PATH` GitHub secret.
3. Copy `.env.production.example` to `.env.production` in that directory.
4. Replace every placeholder. URL-encode the database password inside `DATABASE_URL`.
5. Use a random server-only `INTERNAL_API_TOKEN` of at least 32 characters.
6. Set `DEFAULT_ORGANIZATION_ID` and `DEFAULT_USER_ID` to an active tenant and user. The backend loads that user's persisted roles on every request. The token is injected only by the Next.js server and is never a `NEXT_PUBLIC_` variable.

The production Compose stack includes PostgreSQL 16 with a durable volume, Redis 7 with append-only persistence, a one-shot Alembic migration service, the API, Celery worker, and Next.js frontend. API and worker startup is gated on a successful migration; frontend startup is gated on API health.

## GitHub production environment

Create a protected GitHub environment named `production` and add:

- `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, and `DEPLOY_PATH` for SSH deployment.
- `GHCR_USERNAME` and a least-privilege `GHCR_TOKEN` with `read:packages` for private image pulls on the host.

Run **Build and deploy** manually and enable **Deploy images to the configured Docker Compose host**. The workflow copies the manifest, authenticates the host to GHCR, pulls the immutable commit images, runs migrations, and reconciles the stack with `--remove-orphans`.

## First tenant and demo data

For a demonstration environment, temporarily set `DEMO_MODE=true`, deploy, then seed after migrations:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml run --rm api python -m app.seed
```

Copy the seeded Nova organization and desired user UUIDs into `.env.production`, restore `DEMO_MODE=false`, and redeploy. Production requests require the internal token plus both IDs; plain organization headers are never accepted as authentication.

## Verification and rollback

```bash
docker compose --env-file .env.production -f docker-compose.production.yml ps
curl --fail http://localhost:8000/api/v1/health/ready
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=200 migrate api worker frontend
```

To roll back application code, set `BACKEND_IMAGE` and `FRONTEND_IMAGE` to an earlier `sha-...` pair and run `docker compose up -d`. Database downgrades are intentionally manual: review the Alembic revision and backup PostgreSQL before downgrading.
