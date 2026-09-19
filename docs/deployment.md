# Deployment

The `Build and deploy` GitHub Actions workflow (`.github/workflows/deploy.yml`) derives lowercase GitHub Container Registry image names from the repository owner, then publishes immutable SHA-tagged backend and frontend images on `main`, plus `latest` tags for convenience. GHCR requires lowercase repository names.

For a remote Docker Compose deployment, configure the protected GitHub `production` environment with `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, and `DEPLOY_PATH`. The server must contain an `.env.production` with `DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS`, and any port overrides. Run the workflow manually and select **Deploy images to the configured Docker Compose host**. The workflow transfers only the production Compose manifest; secrets stay in GitHub and the server environment file.

The deployment uses `docker-compose.production.yml`, runs the API, worker, and frontend as pinned images, and performs an API health check through Compose before the frontend starts. The frontend server receives the private `API_URL=http://api:8000/api/v1` Compose address; this avoids baking a public backend URL into the image.
