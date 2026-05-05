
# 🎯 Epic: Dev Experience, CI/CD, and Deployment

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

spec-doc-api currently runs only on one machine, in one way, with no automated gate before code reaches production. Every new contributor must reverse-engineer the environment from memory and tribal knowledge. Every push to `master` is a manual, unverified deployment. This is acceptable for a prototype; it is a liability for a tool that generates AI-assisted engineering specs against a live product backlog.

Containerization and a CI/CD pipeline convert the backend from a local dev artifact into a reproducible, deployable service. The GitHub Actions pipeline enforces the existing DTO-drift rule and pytest suite on every PR — removing the current dependency on developer discipline. The Coolify deployment path reduces a production push to a single `git push`, eliminating manual server operations. These are not aspirational improvements; they are the minimum bar for a backend that will handle AI provider calls running up to 15 minutes per request without silent timeouts killing them.

Doing this now, before Phase 2 AI text endpoints are built, costs roughly half a day. Doing it after — while debugging a container that also needs to run new Claude SDK calls — costs significantly more, and the Dockerfile will be blamed for AI bugs that are actually application bugs.

**Value Proposition**: Make spec-doc-api reproducible to run, impossible to deploy with a broken test suite, and deployable to production with a single push.

---

## Scope

### What This Epic Covers

- **Health route** — minimal `GET /health` endpoint required before any container smoke test can pass
- **Dockerfile** — non-root, slim base image with Gunicorn at a timeout that accommodates 15-minute AI provider calls
- **docker-compose.yml** — local dev and CI target with the `spec-doc/` data volume mounted read-only
- **docker-compose.coolify.yml** — production target with Traefik labels; resolves the data volume contract before ad-hoc bind-mount hacks accumulate
- **GitHub Actions pipeline** — three sequential jobs: test (every push + PR), docker-build + smoke (main only), deploy via Coolify webhook (main only)
- **.env.example** — documents every env var the app reads; no secrets committed
- **Dependabot** — weekly pip dependency updates, added at the same time as the pipeline
- **Makefile additions** — `docker-build`, `docker-up`, `docker-down`, `docker-logs`, `docker-smoke` targets

### What This Epic Does NOT Cover

- ❌ Nginx reverse proxy — Coolify's Traefik handles routing and SSL for a single-subdomain backend; no nginx service needed
- ❌ Staging environment — production and local only; no second-environment trigger exists in this project
- ❌ Docker registry (GHCR) — Coolify builds from source; no pre-built image push required
- ❌ Redis or task queue — background AI jobs use `threading.Thread` with polling; no queue needed at current concurrency
- ❌ Gevent worker class — no concurrent AI use demonstrated; `gthread` ships first
- ❌ Path filters (dorny/paths-filter) — deferred until this repo has more than one module consuming the pipeline
- ❌ `spec-doc-live` worktree removal — side effect of containerization, not DevOps scaffolding; deferred until the container is proven stable in production
- ❌ Monitoring, Sentry, alerting — no named consumer

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel With | Effort | Priority |
|---|------|--------------|---------------|--------|----------|
| 1 | **Health Route + Gunicorn Prerequisite** | None | — | 0.25 days | High |
| 2 | **Dockerfile + docker-compose.yml** | Task 1 | — | 0.5 days | High |
| 3 | **.env.example + Dependabot** | None | Task 2 | 0.25 days | High |
| 4 | **GitHub Actions Pipeline** | Task 2 | Task 5 | 0.5 days | High |
| 5 | **docker-compose.coolify.yml + Makefile Additions** | Task 2 | Task 4 | 0.25 days | High |

---

### Task 1: Health Route + Gunicorn Prerequisite

Before any container can run a smoke test, the Flask app must expose a `/health` endpoint and Gunicorn must be present in `requirements.txt` at build time. This task establishes both prerequisites so that Task 2 (the Dockerfile) is not blocked by a missing route or a missing dependency at the exact moment it is first built. Gunicorn moving from dev to prod deps is a deliberate position: the Dockerfile depends on it, so it belongs in the dependency set that production runs.

**Scope**: One route added to `create_app.py`; one line moved in `requirements.txt`. No other application code changes.

---

### Task 2: Dockerfile + docker-compose.yml

The Dockerfile defines the single reproducible build artifact for spec-doc-api: a non-root, slim-base image running Gunicorn with a timeout calibrated to the longest AI provider call this backend makes. The `docker-compose.yml` targets local development and CI, mounting the `spec-doc/` sibling repo as a read-only data volume — the same data relationship the app has today, expressed as a container contract.

**Scope**: `Dockerfile` and `docker-compose.yml` only. The production Coolify compose is a separate task. The critical constraint is the Gunicorn timeout: it must accommodate AI calls running up to 15 minutes; the default of 120 seconds silently kills them.

---

### Task 3: .env.example + Dependabot

`.env.example` documents every environment variable the application reads — Flask flags, data paths, CORS origins, AI provider selection, and API keys — with safe defaults for local development. No secrets are committed. Dependabot is added at the same time as the pipeline, not after, because shipping CI/CD without automated dependency updates creates a false sense of maintenance coverage.

**Scope**: `.env.example` at repo root; `.github/dependabot.yml` for pip weekly updates. No application code changes.

---

### Task 4: GitHub Actions Pipeline

Three sequential jobs gate every push and pull request against the same quality bar: the existing pytest suite, the DTO-drift check that is already a required repo rule, and a docker-build smoke test that proves the container starts and serves its two primary endpoints. The deploy job fires only on `main` and only after the build smoke passes, reducing production push to a webhook call.

**Scope**: `.github/workflows/deploy.yml` with test, docker-build, and deploy jobs. Secrets `COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` must be provisioned in GitHub before the deploy job succeeds — the pipeline ships without them, but the deploy job will fail until they exist. The open question of whether a `mock` AI provider exists must be resolved before this task begins; CI overrides `AI_PROVIDER=mock` for the docker-build smoke job.

---

### Task 5: docker-compose.coolify.yml + Makefile Additions

The Coolify compose file defines the production container: Traefik labels for subdomain routing, SSL via Let's Encrypt, and the named volume that establishes the data contract between the API and its project files in production. The production domain placeholder must be resolved before this file is committed — options are documented in the Analysis. Makefile additions wrap the compose commands behind the same `make` interface the rest of the project uses.

**Scope**: `docker-compose.coolify.yml` and five new `Makefile` targets. The domain resolution decision (placeholder vs. real subdomain vs. env substitution) is a prerequisite to merging this task.

---

## Success Criteria

- ✅ `docker compose build && docker compose up -d` succeeds from a clean checkout with only `.env` filled in
- ✅ `GET /health` returns `{"status": "ok"}` from the running container
- ✅ `GET /api/projects` returns a JSON array from the running container
- ✅ Every PR against `main` runs `make lint`, `make test`, and `make check-dtos` before merge is possible
- ✅ A push to `main` with passing tests triggers a Coolify deploy without manual intervention
- ✅ `.env.example` covers every env var the app reads; `README` or equivalent references it
- ✅ Dependabot opens its first pip update PR within one week of the pipeline merging
- ✅ No AI provider call is silently killed by a Gunicorn timeout in the containerized service

---

## Non-Goals

- ❌ Staging environment — explicitly excluded; no second-environment trigger exists
- ❌ Gevent worker class — gthread ships; gevent is added only when concurrent AI use becomes a demonstrated problem
- ❌ `spec-doc-live` worktree cleanup — deferred until the container runs stably in production; this epic does not remove existing infrastructure
- ❌ Docker image publishing to GHCR — Coolify builds from source; a registry adds complexity with no consumer
- ❌ Monitoring or error tracking — no named consumer at this stage

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
