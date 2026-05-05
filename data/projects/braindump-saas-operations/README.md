# spec-doc — SaaS Operations & Infra (observability + CI + deploy + cleanup)

> **Priority**: mixed — observability is P3 (ship around Phase 1 so everything else is debuggable);
>                       Angular CI is P4; structural cleanup + nginx stack are P5.
> **Effort**: ~1.5 days observability; ~1 day Angular CI; rest is backlog.
> **Blocks**: nothing structurally; observability **enables** debugging every other bucket.
> **Depends on**: nothing — pure additive infrastructure.
> **Siblings**: every other bucket (observability is the lens for everything; CI gates everything).
> **Consolidates**: former `braindump-saas-observability.md` + `braindump-frontend-backend-cicd.md` + `braindump-monorepo-refactor.md` + `braindump-docker-compose-production.md`.
> **Port from**: bubls (Sentry + structlog + health checks + multi-stage Dockerfile + nginx stack — all near-verbatim).

## What

Four operational concerns bundled into one bucket because they share the same theme (production maturity) and each is too small to be its own dump. Ordered by what unblocks the most:

1. **Observability** (P3 — ship first) — Sentry + structlog + per-dep health checks + JSON error handler. Without this everything below is harder to debug.
2. **Angular CI + multi-stage Docker** (P4) — current CI tests backend only; bad `ng build` ships silently.
3. **Structural cleanup** (P5) — `projects/` → `api/resources/`, lift `docs/` to root. Cosmetic.
4. **nginx + Let's Encrypt SSL stack** (P5) — partly redundant with Coolify Traefik shipped in Epic 6; relevant only if you outgrow Coolify.

### 1. Observability — `modules/observability/` (the load-bearing piece)

Four small things that share a debug-context model:

```
modules/observability/
├── sentry.py        # init_sentry(app) — Flask integration, per-user scoping after auth
├── logging.py       # init_logging() — structlog with JSON output + request_id propagation
├── health.py        # health_bp blueprint — /api/health/{anthropic,neon,stripe}
└── errors.py        # register_error_handlers(app) — JSON responses for every exception
```

```python
# modules/observability/sentry.py
def init_sentry(app):
    if dsn := os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=dsn, integrations=[FlaskIntegration()],
                        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                        environment=os.environ.get("APP_ENV", "production"),
                        release=os.environ.get("APP_RELEASE", "dev"))
```

Per-user scoping happens in the auth middleware: after `g.current_user` is set, `sentry_sdk.set_user({"id": ..., "email": ...})`.

```python
# modules/observability/logging.py
def init_logging():
    structlog.configure(processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level, structlog.stdlib.add_logger_name,
        _add_request_context,                    # injects request_id, user_id
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ], wrapper_class=structlog.stdlib.BoundLogger, cache_logger_on_first_use=True)
```

Every module switches `import logging` → `import structlog; logger = structlog.get_logger(__name__)`. Existing `logger.info("msg")` calls still work; new structured form is `logger.info("event", key=value)`.

```python
# modules/observability/health.py
@health_bp.get("/anthropic")
def anthropic_health():
    if not os.environ.get("ANTHROPIC_API_KEY"): return jsonify({"status": "skipped"}), 200
    try:
        Anthropic(timeout=5.0).messages.count_tokens(model="claude-haiku-4-5",
                                                     messages=[{"role": "user", "content": "ping"}])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "degraded", "error": str(e)[:100]}), 503
# Same shape for /neon and /stripe
```

```python
# modules/observability/errors.py
def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def _http(exc): return jsonify({"error": exc.description, "code": exc.code}), exc.code

    @app.errorhandler(ValidationError)
    def _validation(exc): return jsonify({"error": "validation_failed", "details": exc.errors()}), 422

    @app.errorhandler(Exception)
    def _unexpected(exc):
        logger.exception("unhandled_exception", path=request.path)
        return jsonify({"error": "internal_server_error", "code": 500}), 500
```

All four wired in `create_app()` in order: structlog → sentry → error handlers → health blueprint. **Order matters** (structlog first so subsequent inits log structured).

`.env`:
```
SENTRY_DSN=https://...@sentry.io/...
APP_ENV=production
APP_RELEASE=spec-doc@$(git rev-parse --short HEAD)
LOG_LEVEL=INFO
```

### 2. Angular CI + multi-stage Docker (Phase 4 — when ready)

Current CI: `make test` + `make check-dtos` + `make lint` (backend only). Bad `ng build` ships silently to production. Fix: 4-job pipeline.

```yaml
# .github/workflows/deploy.yml (extending Epic 6)
jobs:
  test-backend:    # existing — pytest + check-dtos + lint
  build-frontend:  # NEW — ng build, upload dist as artifact
  docker-build:    # NEW — multi-stage Dockerfile bundling Flask + dist; smoke test /api + /
  deploy:          # existing Coolify webhook — main branch only
```

Multi-stage Dockerfile bundles `web/dist/spec-doc/browser/` into the Flask image. Flask catch-all route serves `index.html` for non-API paths so Angular routing works:

```python
# create_app.py
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_angular(path):
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    if not os.path.exists(web_dir): return "", 404    # dev: served by Angular dev server on :4201
    target = os.path.join(web_dir, path)
    return send_from_directory(web_dir, path if os.path.exists(target) else "index.html")
```

CI smoke step asserts both `/api/projects` and `/` return 200 from the built container.

### 3. Structural cleanup (P5 — defer)

Two file moves discussed and deferred:
- Lift `docs/` to repo root (was `api/docs/`)
- Move `projects/` into `api/resources/projects/`

High churn on file paths; defer until a quiet week. Best done after a major release rather than mid-sprint.

### 4. nginx + SSL (P5 — defer; Coolify covers this)

Production `docker-compose.coolify.yml` shipped in Epic 6 with Traefik labels. Coolify's Traefik handles SSL via Let's Encrypt + subdomain routing. The standalone nginx + certbot stack from `braindump-docker-compose-production.md` is **only relevant if you outgrow Coolify** — not the launch case.

## Why now

The Anthropic SDK provider (paid API spend) + auth (real users) land in Phase 1. The day a real user hits a 500, the team reads about it from the user instead of the logs unless **observability is in place first**. Sentry without structlog is half-blind; structlog without Sentry doesn't alert; health checks without either gives a green light to a degraded system. **All four observability pieces ship together** because they share `request_id` flow.

Bubls ships every one of these in production. The port is genuinely cheap (~10–30 LOC per piece); the cost is project setup (Sentry account, log destination if any) which is one-time admin work.

Angular CI + the rest are nice-to-haves that don't block launch but should follow before the team is bigger than 1.

## What's missing

Two decisions:

1. **Where do JSON logs go in production?** Coolify captures stdout (proposed; zero infra; not searchable across time) vs ship to BetterStack/Logtail/Loki (searchable + alertable; costs money). Start with Coolify; upgrade when volume justifies.
2. **Sentry traces sample rate** — 0.1 (10%) proposed; matches bubls launch.

## Explicitly out of scope

- **APM (Datadog, New Relic)** — Sentry covers errors + basic perf; full APM is enterprise-tier infra.
- **Custom metrics dashboard** — `/api/stats` (cost dashboard; lives in SDK provider brain dump) covers product metrics; ops metrics belong in Sentry/Coolify.
- **OpenTelemetry tracing** — overkill for a single-service backend.
- **Per-tenant log isolation** — `user_id` is in every log line; aggregator filtering is the access control.
- **PII scrubbing in logs** — defer until a compliance trigger fires.
- **Frontend session replay (Sentry Replay)** — payload size; turn on when first hard-to-repro user bug appears.
- **Audit log of admin actions** — separate; brain dump when admin tools (capability #75) are scoped.
- **Container registry (GHCR push)** — Coolify builds from source; no push step needed.
- **Per-PR preview deploys** — not needed at current team size.
- **Kubernetes / Helm** — Docker Compose on a single VPS is the deployment target.
- **Per-IP rate limiting** — cloud LB or Cloudflare; out of bucket scope.
- **SSL via certbot when Coolify Traefik is the deploy target** — redundant.
