# spec-doc — Deployment Stack Rewrite

> **Supersedes**: `projects/aligning-spec-doc-deployment-1777307253079/` (in-flight epic, do not generate from) and `projects/braindump-deployment-config-fragmentation.md` (interim notes, archived).
>
> **Priority**: P1 — production deploy surface is fragmented across three compose files with conflicting ingress strategies, a healthcheck that fails silently, and three dead workflow files. Any future deploy change is currently a guess about which file matters.
>
> **Effort**: ~1–1.5 days end-to-end.
>
> **Blocks**: nothing on the product roadmap. Unblocks confident deploys and any future SaaS features that need consistent env var plumbing (Stripe, Sentry, Neon).
>
> **Depends on**: nothing in the codebase. Externally: confirming Coolify's current `Compose Path` and which env vars it actually has set.
>
> **Status**: Authored 2026-04-28 after a full audit of `.github/workflows/`, `Dockerfile`, `docker-compose*.yml`, `Makefile`s, and `.dockerignore`.

---

## What's in the tree right now (verified)

**Workflows (4 files, 1 actually runs)**
- `.github/workflows/deploy.yml` — root, canonical, targets `master`. Jobs: `test` ∥ `build-frontend` → `docker-build` → `deploy`. Soft-fails on the SPA smoke test (lines 128–143 only `WARN`).
- `api/.github/workflows/deploy.yml` — git-tracked, **dead** (GitHub only reads `.github/workflows/` at repo root). Targets `main`, references `make docker-up`.
- `web/.github/workflows/test-frontend.yml` and `web/.github/workflows/ci.yml` — git-tracked, **dead**. Karma + Playwright setup checks that never execute.

**Docker (1 Dockerfile, 1 .dockerignore, 3 compose files)**
- `api/Dockerfile` — multi-stage. Stage 1 `node:20-alpine` builds Angular; stage 2 `python:3.11-slim` runs Flask serving the baked-in dist via `web_serve_bp`. Build context = repo root.
- `api/.dockerignore` — **dead since context moved to repo root**. Docker honours `.dockerignore` only at the build context root. There is no root `.dockerignore`. Result: `web/node_modules/` and `web/.angular/cache/` get sent to the daemon on every build.
- `docker-compose.yml` (root) — `api` service, `ports: 3101:3101`, full env (Stripe, Auth, DB, Sentry — all using `STRIPE_PRICE_ID_PRO`), curl healthcheck, named `spec-doc-data` volume. Added in commit `416e317 feat(deploy): add root-level docker-compose.yml for Coolify`.
- `api/docker-compose.yml` — local dev. Bind mount `../spec-doc:ro`, python urllib healthcheck, minimal env.
- `api/docker-compose.coolify.yml` — Traefik labels (`Host(\`api.spec-doc.${DOMAIN}\`)`), no `ports:`, **missing Stripe / Auth / DB / Sentry env entirely**, curl healthcheck.

**Angular**
- `web/src/environments/environment.ts` — only one env file. `apiUrl: 'http://localhost:3101'` (no `/api` suffix; service code presumably appends paths).
- `web/.gitignore`, `web/.editorconfig`, etc. — looks like an embedded sub-project but lives in the monorepo.

**Makefiles**
- Root: `dev-all`, `dev-api`, `dev-web`, `install`, `test` (delegates).
- `api/`: `lint`, `test`, `check-dtos`, `docker-build/up/down/logs/smoke`. All `docker-*` targets run bare `docker compose` (no `-f`), so they hit `api/docker-compose.yml` if invoked from `api/`.

---

## Bugs, in priority order

1. **`curl` healthcheck against `python:3.11-slim` will fail.** Both root and coolify compose use `["CMD", "curl", "-f", "http://localhost:3101/health"]`. `python:3.11-slim` ships no curl. Container becomes unhealthy on every interval; `depends_on: condition: service_healthy` (whether already used or proposed) never resolves.
2. **Three compose files, no canonical.** Pick one. Today it's a coin flip whether root or coolify is what Coolify reads — the env var coverage mismatch means production silently lacks Stripe/Auth/DB/Sentry depending on which.
3. **Build context = repo root, but `.dockerignore` is in `api/`.** Builds ship `web/node_modules` (~hundreds of MB) on every push. Slow CI, big build context, no actual exclusion happening.
4. **Three tracked-but-dead workflow files.** Confuses every PR review and every future CI audit.
5. **Soft-fail SPA smoke test.** Comment in `.github/workflows/deploy.yml:130-133` admits this is a temporary seam. It's been temporary for a while.
6. **`api/Dockerfile` bakes Angular dist into the Flask image.** Every CSS tweak rebuilds the Python layer. Diverges from humanize-me / speedback which both run an nginx frontend container talking to an internal Flask backend.

---

## What

Replace the current monolithic-image + three-compose-files setup with a clean two-container stack and one canonical compose file. Match the proven shape from humanize-me and speedback so the operational pattern is one project's worth of muscle memory, not three.

### End state

```
┌──────────────────────────────────────────────────────────┐
│ Coolify  →  Traefik  →  frontend:80  (nginx:alpine)      │
│                            │                              │
│                            ├─→ static SPA (Angular dist)  │
│                            │                              │
│                            └─→ /api/* → backend:3101      │
│                                          (Flask, gthread, │
│                                           --timeout 900)  │
└──────────────────────────────────────────────────────────┘
```

- **One** `docker-compose.yml` at repo root. Two services. `expose:` only — Coolify/Traefik handles TLS and domain.
- **One** Dockerfile per service: `web/Dockerfile` (node builder → nginx:alpine), `api/Dockerfile` (Flask only, single stage).
- **One** `.dockerignore` at repo root.
- **One** workflow file: `.github/workflows/deploy.yml`. Four jobs: `frontend-ci` ∥ `backend-ci` → `docker-integration` → `deploy`.
- Angular `environment.ts` uses relative `/api` so dev (proxy.conf.json) and prod (nginx) share the same path.
- `web_serve_bp` deleted from Flask; nginx owns static serving.

### Concrete shape

**Root `docker-compose.yml`** (replaces all three current compose files; the api/ ones get deleted):

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: api/Dockerfile
    expose: ["3101"]
    environment:
      SPEC_DOC_DIR: /data/spec-doc
      CHAIN_PROVIDER: ${CHAIN_PROVIDER:-claude}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:4201}
      APP_ENV: ${APP_ENV:-production}
      AUTH_SECRET: ${AUTH_SECRET}
      NEON_AUTH_JWKS_URI: ${NEON_AUTH_JWKS_URI}
      DATABASE_URL: ${DATABASE_URL}
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
      STRIPE_PRICE_ID_PRO: ${STRIPE_PRICE_ID_PRO}
      SENTRY_DSN: ${SENTRY_DSN}
    volumes:
      - spec-doc-data:/data/spec-doc
    healthcheck:
      test:
        - "CMD-SHELL"
        - >
          python -c "import urllib.request;
          urllib.request.urlopen('http://localhost:3101/health')"
          || exit 1
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks: [spec-doc-net]

  frontend:
    build:
      context: .
      dockerfile: web/Dockerfile
    expose: ["80"]
    depends_on:
      backend: { condition: service_healthy }
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost/api/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 45s
    networks: [spec-doc-net]

volumes:
  spec-doc-data:

networks:
  spec-doc-net:
    driver: bridge
```

Two non-obvious choices in there:

- **`STRIPE_PRICE_ID_PRO`** matches what's already in `docker-compose.yml:20` and the billing module — do not invent `STRIPE_PRO_PRICE_ID`.
- **Healthcheck via `python -c urllib.request`** because `curl` is not in `python:3.11-slim`. Frontend uses `wget` because nginx:alpine includes BusyBox wget.

**Routing decision (subtle but critical)**

Flask's existing health route is `/health`, not `/api/health` (`api/create_app.py:90`). So nginx must either (a) proxy `/api/*` and Flask gains an `/api/health` route, or (b) nginx healthcheck hits the backend container directly via the service network. Pick **(a)**: register all Flask routes under `/api/`, including `/health`. Cleaner contract; Coolify entry point is unambiguous; `nginx.conf` becomes one location block.

**Frontend `web/Dockerfile`** (new, pattern from humanize-me):

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /workspace
COPY web/package.json web/package-lock.json ./
RUN npm ci --prefer-offline --no-audit --progress=false
COPY web/ ./
RUN npx ng build --configuration production

FROM nginx:alpine
COPY --from=builder /workspace/dist/spec-doc/browser /usr/share/nginx/html
COPY web/nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Build context = repo root (matches backend), so `web/Dockerfile` and `api/Dockerfile` are symmetric. One root `.dockerignore` covers both.

**`web/nginx/nginx.conf`** key directives:
- `resolver 127.0.0.11 valid=30s; set $backend http://backend:3101;` — defers DNS so nginx starts before backend is healthy.
- `location ^~ /api/ { proxy_pass $backend; proxy_buffering off; proxy_read_timeout 900s; … }` — SSE-safe, matches gunicorn `--timeout 900`.
- `location / { try_files $uri $uri/ /index.html; }` — SPA fallback.
- Static assets (`*.js|css|woff2|…`) get `Cache-Control: immutable`.

**Workflow rewrite** (`.github/workflows/deploy.yml`):

```yaml
jobs:
  frontend-ci:    # web/, ng build prod
  backend-ci:     # api/, make lint test check-dtos
  docker-integration:        # docker compose up; smoke / and /api/health; tear down
    needs: [frontend-ci, backend-ci]
    if: github.ref == 'refs/heads/master'
  deploy:                     # Coolify webhook
    needs: [docker-integration]
    if: github.ref == 'refs/heads/master'
```

Smoke test uses `docker compose exec -T frontend wget -qO- http://localhost/api/health` — exercises the actual nginx→Flask path without needing host port-mapping. Hard-fails (no `WARN`).

**Root `.dockerignore`** (new):

```
.git
.github
.claude
.vscode
projects/
**/node_modules/
**/.angular/
**/__pycache__/
**/.pytest_cache/
**/.mypy_cache/
**/.venv
**/venv
.env
.env.*
!.env.example
*.md
docs/
api/tests/
api/.coverage
api/htmlcov
web/dist/
docker-compose*.yml
```

---

## Execution order

Five tasks, each independently revertible:

1. **Workflow + dead-file cleanup.** `git rm api/.github/workflows/deploy.yml web/.github/workflows/test-frontend.yml web/.github/workflows/ci.yml api/.dockerignore api/docker-compose.coolify.yml`. Add root `.dockerignore`. Side-effect free.
2. **Add `web/Dockerfile` + `web/nginx/nginx.conf`.** Pure additions; nothing references them yet.
3. **Move all Flask routes under `/api/` prefix** (including `/health`). Update Angular `environment.ts` to `apiUrl: '/api'` and `proxy.conf.json` accordingly. Remove `web_serve_bp`. This is the biggest single diff but it's mostly mechanical.
4. **Replace `docker-compose.yml` with the two-service version above. Simplify `api/Dockerfile` to single-stage Flask-only.** Delete `api/docker-compose.yml` (or keep purely for `make dev` if that's preferred, but I'd kill it).
5. **Rewrite `.github/workflows/deploy.yml` to four-job parallel structure.**

Each step ships its own commit set + tests. Steps 1, 2, 5 can run in any order; step 3 must precede step 4 (otherwise Flask routes don't match nginx upstream).

---

## Why now

The deployment surface has been accumulating files faster than it's been shedding them: an api/-scoped compose, a Coolify-specific compose, a root compose, three `.github/workflows/` directories. Three of those four workflow files don't run. The healthcheck command doesn't work in the runtime image. The `.dockerignore` doesn't apply to the build context. None of these are bugs that fail loudly — they fail by being silently irrelevant or silently broken, which is the worst kind of CI/deploy state.

The existing `aligning-spec-doc-deployment` epic identified the right *direction* (nginx + Flask split, parallel CI) but anchored on the wrong baseline assumptions (edits api/ compose, healthcheck path mismatch, Stripe var name mismatch, ignores three dead files). Discard and restart from accurate ground truth.

The siblings (humanize-me, speedback) already run this exact shape in production. Porting their pattern is lower-risk than inventing a spec-doc-specific one.

---

## What's missing — open questions before this becomes an epic

1. **Coolify's actual `Compose Path` setting.** Need to know whether Coolify currently points at root `docker-compose.yml`, `api/docker-compose.coolify.yml`, or something else. Affects which file we keep during the transition (briefly we need both to work). User to check Coolify dashboard.
2. **`environment.prod.ts`** — does not currently exist. Decide: do we add one for production-only config, or keep a single `environment.ts` and rely on `--configuration production` doing nothing useful? Lean toward keeping single file; nothing currently varies between dev and prod that isn't a runtime env var.
3. **Flask route prefix change to `/api/*`** — verify no external consumers of `/health` (uptime monitors, Coolify's own healthcheck UI, etc.) break. If something depends on `/health` at root, keep it as a duplicate route while migrating.
4. **`api/docker-compose.yml` retention** — kill it, or keep as a documented dev-only file? Lean toward kill; `make dev-api` doesn't even use compose, it runs `python3 app.py` directly. Compose for dev is over-engineering.
5. **Spec-doc data volume** — root compose uses named volume `spec-doc-data`; api/ uses bind mount `../spec-doc:ro`. Coolify production should keep the named volume; local dev never used compose anyway. No conflict, just delete the bind-mount path.

---

## Out of scope

- **Migrating off Coolify** (Kamal, Dokku, self-hosted). Coolify works.
- **Adding Redis / Postgres as compose services.** spec-doc is in-process state; SQLite is the database; no message broker needed.
- **TLS in nginx config.** Coolify/Traefik terminates TLS; frontend container stays HTTP-only on port 80.
- **Separate nginx reverse-proxy tier** (wardrobai pattern). spec-doc has one SPA and one backend; the frontend container *is* the entry point. No second consumer to justify a third container.
- **`docker-compose.test.yml`** for CI. The main compose file handles the smoke test in `docker-integration`. A parallel test-only compose doubles maintenance with no benefit.
- **Build artifact upload for the Angular dist.** Each service builds inside its own Docker stage; no downstream consumer of a standalone dist artifact.
- **CLAUDE.md or docs update.** Track separately if the deploy runbook needs rewriting; not part of the code change.
