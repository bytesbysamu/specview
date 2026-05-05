# 🏗️ Solution Architecture: Dev Experience, CI/CD, and Deployment

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

spec-doc-api is a single Flask service with no database, no auth layer, and a single sibling-repo data dependency. The containerization and pipeline architecture reflects that simplicity: one image, one compose file per target environment, one sequential pipeline. The reference pattern is constellation-api — not the wardrobai nginx stack, which exists to co-deploy a frontend and multiple backing services. Adding nginx or a registry here would be complexity with no consumer.

The central design tension is the AI provider's call duration. Claude SDK calls can run up to 15 minutes. Gunicorn's default worker timeout of 120 seconds silently kills those calls without an error visible to the caller. Every other architectural choice — worker class, thread count, healthcheck retry interval — is downstream of that constraint. The system is designed so that the timeout is visible, configurable, and never accidentally defaulted.

The data relationship between the API and the project files it reads deserves explicit treatment. Today that relationship is an undocumented filesystem assumption: the API reads from a sibling directory on the same machine. In the container architecture, that relationship becomes a named volume contract. Local and CI environments mount the sibling repo read-only; production exposes a named volume that the API writes to through its own file-mutation endpoints. The Angular frontend has no shared volume — it writes project files through the API. This resolves the data contract before ad-hoc bind-mount decisions accumulate.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| One image, two targets | The same `Dockerfile` builds both local/CI and production. Environment differences are expressed in compose files, not in the image. |
| Explicit over implicit | Every env var the app reads is documented in `.env.example` with a safe local default. Nothing is inferred at runtime. |
| Timeout is a first-class concern | Gunicorn timeout is set to 900 seconds — not the default, not a guess. It is sized to the longest known AI provider call this backend makes. |
| Existing quality gates, enforced by the pipeline | The DTO-drift check and pytest suite already exist. The pipeline enforces them on every PR rather than relying on developer discipline. |
| Ship gthread, add gevent when needed | Two workers × four gthread threads handles the current single-user load. Gevent is deferred until concurrent AI use is a demonstrated problem, not an anticipated one. |
| Data contract over filesystem assumption | The spec-doc data relationship is expressed as a volume mount in every compose target — not left as an implicit path on the host machine. |

---

## System Boundaries

### What This System Includes

- **`/health` route** — the prerequisite for any container smoke test; lives in `create_app.py` and has no auth requirement
- **Dockerfile** — single build artifact; non-root, slim base, Gunicorn with gthread workers and a 900-second timeout
- **`docker-compose.yml`** — local development and CI target; read-only bind-mount of the sibling `spec-doc/` directory as the data volume
- **`docker-compose.coolify.yml`** — production target; Traefik labels for subdomain routing and SSL; named volume as the data contract for project files
- **`.github/workflows/deploy.yml`** — three-job sequential pipeline: test (all pushes and PRs), docker-build smoke (main only), deploy via Coolify webhook (main only)
- **`.env.example`** — documents every env var the app reads; no secrets committed
- **`.github/dependabot.yml`** — weekly pip dependency updates; shipped at the same time as the pipeline, not after
- **Makefile additions** — `docker-build`, `docker-up`, `docker-down`, `docker-logs`, `docker-smoke` targets wrap compose commands behind the existing `make` interface

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Nginx reverse proxy | Coolify's Traefik handles subdomain routing and SSL termination for a single-service backend; nginx adds a network hop and a config file with no benefit |
| Docker registry (GHCR) | Coolify builds from source on deploy; a registry requires push steps and pull credentials with no named consumer at this stage |
| Staging environment | No second-environment trigger exists; production and local are the only targets |
| Redis / task queue | Background AI jobs use `threading.Thread` with polling; queue infrastructure requires a named consumer to justify its operational cost |
| Gevent worker class | Concurrent AI use is not a demonstrated problem; gthread ships first and gevent is added when the problem is real |
| Monitoring / Sentry / alerting | No named consumer |
| `spec-doc-live` worktree removal | Side effect of containerization, not DevOps scaffolding; deferred until the container is proven stable in production |

---

## Component Design

### Health Route

**Purpose**: Provides the liveness signal required by Docker healthchecks, the CI smoke test, and Coolify's deployment verification. Without it, no automated system can confirm the container started correctly.

**Key Parts**:
- One route registered in `create_app.py` — `GET /health` returning `{"status": "ok"}` with no authentication requirement

**Patterns**: Minimal liveness endpoint — no dependency checks, no database ping, no AI provider reachability. The endpoint confirms the process is alive; deeper checks belong in separate readiness probes if that need arises.

**Consumers**: Docker healthcheck in both compose files; CI docker-build smoke job; Coolify deployment health verification.

---

### Dockerfile

**Purpose**: Defines the single reproducible build artifact for spec-doc-api. Encodes the non-root security posture, the slim base image, and the Gunicorn configuration that accommodates long-running AI provider calls.

**Key Parts**:
- Non-root user (`appuser`) — defense against container escape; standard practice for any service exposed to network traffic
- `python:3.11-slim` base — matches the Python version in local dev; slim avoids pulling build tools that are not needed at runtime
- Gunicorn with `gthread` worker class and 900-second timeout — the timeout is the load-bearing constraint; 2 workers × 4 threads handles sequential AI requests from a single-user tool
- `--preload` flag — loads the app once before forking workers, avoiding duplicate initialization of the AI provider adapter

**Patterns**: Immutable artifact — the image is built once and run in multiple contexts via compose files. The 900-second timeout is not configurable at runtime; it is a fixed decision in the image to prevent accidental regression to the Gunicorn default.

**Consumers**: `make docker-up` local development; CI docker-build job; Coolify production deployment.

---

### docker-compose.yml (Local Dev + CI)

**Purpose**: Defines the local development and CI execution environment. Translates the existing filesystem assumption — that the API reads from the sibling `spec-doc/` directory — into an explicit, versioned volume contract.

**Key Parts**:
- Single `api` service — no sidecar services; the backend has no database or cache dependency
- Read-only bind-mount of `../spec-doc` at `/data/spec-doc` — enforces that the API cannot write to its data source in local and CI contexts; production is where writes are permitted
- `AI_PROVIDER` env var — CI overrides this to `mock` so the docker-build smoke job runs without a live API key

**Patterns**: Environment parameterization via env vars rather than per-environment Dockerfiles. The compose file is the environment definition; the image is environment-agnostic.

**Consumers**: `make docker-up` for local development; CI docker-build job for smoke testing.

---

### docker-compose.coolify.yml (Production)

**Purpose**: Defines the production deployment contract. Expresses the Traefik routing, SSL, and data volume configuration that Coolify needs to deploy the service without manual server operations.

**Key Parts**:
- Traefik labels — route `api.spec-doc.yourdomain.com` to port 3101; Let's Encrypt certresolver handles SSL; no nginx needed
- Named volume `spec-doc-data` — the production data contract; the API's file-mutation endpoints (`PUT /api/projects/:id/files/:filename`) write into this volume; the Angular frontend writes through the API, not to a shared volume
- `FLASK_DEBUG=0` — hardcoded in the production compose file, not left to an env var override that could be misconfigured

**Patterns**: Separate compose file per deployment target (local vs. production) rather than a single compose file with environment-specific overrides. This makes the production config auditable and diff-able without risk of accidentally running production settings locally.

**Consumers**: Coolify reads this file on deploy; no other consumer.

---

### GitHub Actions Pipeline

**Purpose**: Enforces the existing quality gates (pytest, DTO-drift) on every PR and push, and reduces a production deployment to a single push to `main`. Removes the dependency on developer discipline for checks that already exist.

**Key Parts**:
- **test job** — runs on every push and pull request; pip cache keyed to `requirements*.txt` hash; executes `make lint`, `make test`, `make check-dtos`
- **docker-build job** — runs after `test`, on `main` pushes only; overrides `AI_PROVIDER=mock`; builds and starts the container; polls `/health` for liveness; hits `/api/projects` to verify the data volume mount and route registration; tears down
- **deploy job** — runs after `docker-build`, on `main` pushes only; issues the Coolify webhook call; requires `COOLIFY_WEBHOOK` and `COOLIFY_TOKEN` secrets provisioned in GitHub

**Patterns**: Sequential jobs with hard dependencies — the deploy job cannot run unless the smoke test passed; the smoke test cannot run unless tests passed. This is a deliberate constraint: no partial success path exists.

**Consumers**: Every push to `main`; every PR opened against `main`.

---

### .env.example

**Purpose**: Makes the environment contract explicit and self-documenting. Eliminates the reverse-engineering burden for new contributors and documents the distinction between local defaults, CI overrides, and secrets that must never be committed.

**Key Parts**:
- All Flask, data path, CORS, and AI provider variables with safe local defaults
- `AI_PROVIDER` documented with its three valid values: `claude`, `cli`, `mock`
- Coolify secrets (`COOLIFY_WEBHOOK`, `COOLIFY_TOKEN`) commented out with an explicit note that they live in GitHub Secrets, never in `.env`

**Consumers**: Every new developer setting up a local environment; Coolify environment UI for production secrets; CI job documentation.

---

### Dependabot Configuration

**Purpose**: Automates pip dependency updates so that CI/CD is not shipped without a maintenance mechanism. The window between "CI ships" and "Dependabot ships" is the highest-risk period for dependency drift.

**Key Parts**:
- Weekly pip update schedule — not daily; weekly balances update frequency against PR noise
- Scoped to the spec-doc-api repo only

**Consumers**: GitHub PR queue; the CI pipeline that validates every Dependabot PR.

---

### Makefile Additions

**Purpose**: Wraps Docker Compose commands behind the same `make` interface the rest of the project uses. Developers who know `make dev` and `make test` should not need to remember compose syntax for the container workflow.

**Key Parts**:
- `docker-build`, `docker-up`, `docker-down`, `docker-logs`, `docker-smoke` — five targets that map directly to compose operations
- `docker-smoke` calls `/health` and `/api/projects` — same two endpoints the CI smoke job validates, so local smoke produces the same signal as CI

**Consumers**: Developers running the containerized backend locally; CI job scripts that call `make` targets.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Container runtime | Docker + Compose | No Kubernetes consumer exists; Compose is the right scope for a single-service backend |
| Base image | `python:3.11-slim` | Matches local Python version; slim avoids pulling build toolchain at runtime |
| WSGI server | Gunicorn with `gthread` | `gthread` handles I/O-bound AI calls without the complexity of gevent; `--preload` avoids duplicate AI provider initialization |
| CI/CD platform | GitHub Actions | Already the repo's CI platform; no additional tooling needed |
| Reverse proxy / SSL | Coolify's Traefik | Handles subdomain routing and Let's Encrypt for a single-service backend; no nginx config to maintain |
| Deployment platform | Coolify | Consistent with constellation-api; builds from source; webhook-triggered deploy eliminates manual server operations |
| Dependency updates | Dependabot (pip) | Native to GitHub; zero operational cost; the correct pairing for a GitHub Actions pipeline |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| 900-second Gunicorn timeout | The CLI AI provider runs Claude for up to 15 minutes per task generation call; 120 seconds (the default) silently kills those calls without surfacing an error | A 900-second timeout means a hung worker holds a slot for 15 minutes; acceptable at current single-user concurrency |
| `gthread` over `gevent` | Concurrent AI use is not a demonstrated problem; gthread handles sequential requests without the monkey-patching risks and dependency weight of gevent | If concurrent AI use becomes real, migrating to gevent requires a worker class change and dependency addition; that migration is straightforward |
| Separate webhooks for spec-doc (Angular) and spec-doc-api (Flask) | Independent deploys are simpler than a single compose file spanning two repos; Angular and Flask release independently | Coolify must be configured with two separate service definitions; coordination is manual if a release requires both |
| Named volume over shared volume for production data | The Angular frontend writes project files through the API's file-mutation endpoints, not to a shared volume; the API is the single writer | The named volume is only accessible from the API container; if direct volume inspection is needed in production, it requires a Docker exec or a separate container |
| Read-only bind-mount for local/CI data | Enforces that the local and CI environments cannot mutate the source data; mirrors the read-heavy workload that context loading represents | Developers cannot test file-write endpoints locally without adjusting the compose mount; write-endpoint testing is a known constraint |
| `--preload` in Gunicorn | The AI provider adapter initializes once before workers fork, not once per worker; avoids duplicate SDK initialization and reduces startup time | With `--preload`, a crash during app initialization kills all workers before any request is served; the failure is loud and fast, which is the correct behavior |
| `.env.example` with commented-out secrets | Makes the secret/non-secret boundary explicit in the file developers copy; prevents accidental `.env` commits from including webhook tokens | Commented-out lines require a discipline convention; enforced by `.gitignore` on `.env`, not by tooling |

---

## Execution Flow

```
Every push / PR
  test job ──→ (passes) ──→ docker-build job (main only)
                                    │
                                    └──→ (passes) ──→ deploy job (main only)
                                                            │
                                                            └──→ Coolify webhook

PR against main
  test job only ──→ (must pass before merge)
```

The `test` job is the gate for all merges. The `docker-build` and `deploy` jobs run only on `main` — they do not run on PRs, because building and deploying from a PR branch before merge is not a requirement this project has. The pipeline is linear and intentionally not parallelized: a passing smoke test on a broken test suite is not a meaningful signal.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview