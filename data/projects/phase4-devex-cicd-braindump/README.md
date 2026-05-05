# spec-doc-api — Dev Experience, CI/CD, and Deployment

## What

Add the DevOps scaffolding spec-doc-api is missing: Dockerfile, docker-compose, GitHub Actions pipeline, Coolify deployment config, and `.env.example`. None of this changes the Flask application code. All of it makes the backend reproducible to run locally, testable in CI, and deployable to production with a single push to main.

The reference pattern is constellation-api (single Flask service, GitHub Actions, Coolify webhook) — not wardrobai's full multi-service nginx stack, which is overkill for a single-service backend with no frontend co-deployment.

### 1. Dockerfile

Non-root user, slim base, Gunicorn. Same pattern as wardrobai `server/Dockerfile` and constellation-api `backend/Dockerfile`.

```
FROM python:3.11-slim
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 3101
CMD gunicorn --bind 0.0.0.0:${PORT:-3101} --workers 2 --worker-class gthread --threads 4 --timeout 900 --preload app:app
```

`gunicorn` is a prod dependency — moves to `requirements.txt`. `debug=True` in `app.py` is gated by `FLASK_DEBUG != 1`. (`FLASK_ENV` is deprecated since Flask 2.3 — use `FLASK_DEBUG=0` in production, `FLASK_DEBUG=1` in dev.)

Timeout must be 900s minimum — the CLI AI provider runs Claude for up to 15 minutes per task generation call. 120s will silently kill long AI requests. `--preload` loads the app once before forking workers, which is faster and avoids duplicate initialization of the AI provider.

Consumer: CI docker-build job, Coolify, any developer running the containerized backend.

### 2. docker-compose.yml (local dev + CI)

Single service. Mounts `spec-doc/` as read-only data volume — the backend reads projects and context files from the sibling repo, same as today.

```yaml
services:
  api:
    build: .
    ports:
      - "${PORT:-3101}:3101"
    environment:
      - FLASK_DEBUG=${FLASK_DEBUG:-1}
      - SPEC_DOC_DIR=/data/spec-doc
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:4201}
      - AI_PROVIDER=${AI_PROVIDER:-cli}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
    volumes:
      - ../spec-doc:/data/spec-doc:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3101/health"]
      interval: 30s
      retries: 3
```

Consumer: `make docker-up` local dev, CI docker-build + smoke job.

### 3. docker-compose.coolify.yml (production)

Traefik labels for subdomain routing — Coolify manages SSL and DNS. No nginx needed. Pattern from wardrobai `docker-compose.coolify.yml`.

```yaml
services:
  api:
    build: .
    expose:
      - "3101"
    environment:
      - FLASK_DEBUG=0
      - SPEC_DOC_DIR=/data/spec-doc
      - CORS_ORIGINS=https://spec-doc.yourdomain.com
      - AI_PROVIDER=claude
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - spec-doc-data:/data/spec-doc
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.spec-doc-api.rule=Host(`api.spec-doc.yourdomain.com`)"
      - "traefik.http.routers.spec-doc-api.tls.certresolver=letsencrypt"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3101/health"]
      interval: 30s
      retries: 3

volumes:
  spec-doc-data:
```

Consumer: Coolify reads this file on deploy. The `spec-doc-data` volume is where the Angular frontend's project files live in production — separate from the API repo.

### 4. GitHub Actions pipeline

Three jobs, sequential, same structure as constellation-api `deploy.yml`:

**test** — runs on every push and PR
- Python 3.11
- `actions/cache` on `~/.cache/pip` keyed to `requirements*.txt` hash (saves 30-60s per run)
- `pip install -r requirements-dev.txt`
- `make lint` (flake8)
- `make test` (pytest -v)
- `make check-dtos` (DTO drift detection)

**docker-build** — runs after test passes, main push only
- Override `AI_PROVIDER=mock` so the container starts without an API key
- `docker compose build`
- `docker compose up -d`
- Wait for healthcheck (30s polling)
- `curl -f http://localhost:3101/health`
- `curl -f http://localhost:3101/api/projects` (smoke: must return JSON array)
- `docker compose down`

Note: `/health` must be implemented in the Flask app (`create_app.py`) before this job runs — it does not exist yet. Add a one-liner route that returns `{"status": "ok"}` before writing the pipeline.

**deploy** — runs after docker-build passes, main push only
- Coolify webhook: `curl -X POST -H "Authorization: Bearer $COOLIFY_TOKEN" $COOLIFY_WEBHOOK`

Secrets required: `COOLIFY_WEBHOOK`, `COOLIFY_TOKEN`.

Path filters (dorny/paths-filter from wardrobai) are worth adding when this repo grows more modules — not needed yet.

Consumer: every push to main, every PR opened against main.

### 5. .env.example

Documents every env var the app reads. No secrets committed. Developer copies to `.env`, fills in values.

```
# Flask
FLASK_DEBUG=1
PORT=3101

# Data
SPEC_DOC_DIR=../spec-doc

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:4201,http://localhost:4202

# AI provider: claude | cli | mock
AI_PROVIDER=cli
ANTHROPIC_API_KEY=sk-ant-...

# Coolify (CI only — GitHub Secrets, never in .env)
# COOLIFY_WEBHOOK=https://coolify.yourdomain.com/api/v1/deploy/webhook?uuid=...
# COOLIFY_TOKEN=...
```

Consumer: every new developer, executor container setup, Coolify environment UI.

### 6. Makefile additions

New targets on top of the existing Makefile (from Phase 3):

```makefile
docker-build:   docker compose build
docker-up:      docker compose up -d
docker-down:    docker compose down
docker-logs:    docker compose logs -f api
docker-smoke:   curl -f http://localhost:3101/health && curl -f http://localhost:3101/api/projects
```

Consumer: developer running the container locally, CI job scripts.

## Why now

Phase 2 (AI text endpoints) is about to be built. When it's done, the backend will cover the full Angular contract. That's the right moment to containerize — before Phase 2 so the Dockerfile and CI are proven before AI calls are added, not after when debugging a failing container is harder.

Constellation-api took 2 hours to add this scaffolding and it's been the most painless deployment in the portfolio. WardrobAI's nginx + 6-service stack took a full day. Spec-doc-api is a single Flask service with no database and no auth — this is the easiest possible deployment surface. Do it now, before the codebase grows.

The `spec-doc-data` volume strategy in production matters: the backend reads project files from a volume that the Angular frontend writes to. Defining that volume contract now prevents ad-hoc bind-mount hacks when production deployment starts.

## What's missing

Two decisions before writing the first file (data volume is resolved — see below):

- **Single repo or two repos in Coolify**: Spec-doc (Angular) and spec-doc-api (Flask) are separate repos. Coolify can deploy them separately with separate webhooks, or from a single compose file that references both. Separate webhooks is simpler — Angular and Flask deploy independently. Decision: separate webhooks.

- **gunicorn workers for AI calls**: AI text endpoints (Phase 2) will call Claude SDK or CLI — calls run 30s–15min. With 2 workers × 4 gthread threads, concurrent AI calls will queue. For a single-user tool this is acceptable. For multi-user, switch to gevent worker class or add a task queue. Decision: ship `gthread`, add gevent when concurrent AI use becomes a real problem.

### Data volume — resolved

Option B is the answer. `PUT /api/projects/:id/files/:filename` already exists and is used by the Angular frontend today. In production: mount one named volume in the API container only. The Angular frontend writes project files through the API — no shared volume, no frontend container needed. The `docker-compose.coolify.yml` above reflects this. Decision closed.

## Also add

- **Dependabot** — add `.github/dependabot.yml` for pip weekly updates at the same time as the pipeline. This is the right moment; don't add CI/CD without automated dependency updates.
- **`/health` route** — implement in `create_app.py` before any of the CI/CD is wired up. Single route, returns `{"status": "ok"}`, no auth.

## Explicitly out of scope

- Nginx reverse proxy — Coolify's Traefik handles routing and SSL; no nginx service needed for a single-subdomain backend
- Redis or task queue — background AI jobs already use `threading.Thread` with polling; no queue needed yet
- Monitoring / Sentry / alerting — no named consumer
- Multi-environment (staging) — production and local only for now
- iOS build pipeline — not a mobile product
- Docker registry (GHCR) — Coolify builds from source; no pre-built image push needed

## Side effect

Containerizing the backend with gunicorn eliminates the need for the `spec-doc-live` git worktree. That worktree exists only because Flask debug auto-reload wipes in-memory state when the executor commits code changes. Gunicorn in a container does not auto-reload. Once this phase ships, the live server can run as a container and the worktree can be removed.
