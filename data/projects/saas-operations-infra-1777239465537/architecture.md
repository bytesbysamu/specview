# 🏗️ Solution Architecture: SaaS Operations & Infra

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

This epic adds two independent but thematically unified concerns: an observability layer that makes every other epic debuggable, and a CI/Docker layer that makes every deploy trustworthy. Neither concern touches product logic, so both are purely additive — they wire into `create_app.py` and the GitHub Actions pipeline without reshaping existing modules.

The observability system is built on a shared `request_id` context model. That context, established at request entry by a Flask `before_request` hook, is the thread that connects a log line to a Sentry event to a health-check alarm. Without a shared context, the three pieces are three independent blind spots rather than a correlated debug chain. With it, a 500 in production maps immediately to a correlated log envelope, a Sentry event, and an identifiable code path — before a user has to report it.

The CI/Docker concern is the deployment-side equivalent: the current pipeline proves the backend works but ships the frontend unverified. A broken `ng build` produces a silent failure in the deployed container. A multi-stage Dockerfile eliminates the gap by making CI build the exact artifact that runs in production, and a smoke test asserts both surfaces serve before the deploy job fires.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| ELA #2 — Blueprint Module Structure | All observability pieces live in `modules/observability/`; `routes.py` / `service.py` / `tests/` per-file |
| ELA #5 — No Speculative Abstractions | `modules/observability/` has one consumer (`create_app.py`); no registry or plugin system |
| Adapter boundary respected | Health check for Anthropic calls the provider through `modules/chain/adapter.py`, not the Anthropic SDK directly |
| Initialization order as contract | structlog → Sentry → error handlers → health blueprint; this order is documented and tested |
| Opt-in external dependencies | Sentry activates only when `SENTRY_DSN` is present; absent DSN is a silent no-op, not an error |

---

## System Boundaries

### What This System Includes

- `modules/observability/logging.py` — structlog initialization with `request_id` propagation via context vars
- `modules/observability/sentry.py` — opt-in Sentry Flask integration; per-user scope stub for auth middleware
- `modules/observability/errors.py` — JSON error handlers for `HTTPException`, `ValidationError`, and unhandled exceptions
- `modules/observability/health.py` — `/api/health` blueprint with a live Anthropic check and `{"status": "skipped"}` stubs for Neon and Stripe
- Wiring in `create_app.py` — four ordered init calls; no existing modules modified beyond logger imports
- `build-frontend` CI job — `ng build` gate that blocks the deploy job on failure
- `docker-build` CI job — multi-stage image assembly and smoke test before deploy
- Flask catch-all route in `create_app.py` — serves Angular `index.html` for non-API paths; inactive in dev (no `web/` directory)

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Sentry Replay | Payload size cost; activate at first hard-to-reproduce user bug |
| OpenTelemetry / full APM | Single service, single developer; Sentry + structured logs cover the case |
| Per-tenant log isolation / PII scrubbing | `user_id` in every log line is sufficient; defer to first compliance trigger |
| Log aggregation beyond stdout | Coolify captures stdout at launch; upgrade when search volume justifies the cost |
| Neon + Stripe live health checks | Neither is a spec-doc dependency today; stubs satisfy the stable endpoint contract |
| nginx + certbot SSL | Coolify Traefik is the SSL layer; redundant until the deploy target changes |
| Per-PR preview deploys | Not needed at team size of one |
| Container registry push (GHCR) | Coolify builds from source; no push step required |
| Structural file moves (`projects/` rename, `docs/` lift) | High path churn, zero user-facing value; defer to a quiet week after a major release |

---

## Component Design

### Observability Module — `modules/observability/`

**Purpose**: Provide a shared `request_id` context model that connects log lines to Sentry events across the full request lifecycle.

**Key Parts**:

- `logging.py` — Calls `structlog.configure()` once at app startup. Uses `structlog.contextvars` so that a `request_id` bound at `before_request` is automatically present on every log line emitted during that request, regardless of which module emits it. Every existing module migrates from `import logging` to `structlog.get_logger(__name__)` — existing `.info("msg")` call sites remain valid; new call sites gain keyword arguments for structured fields. Consumer: every Flask module.

- `sentry.py` — Wraps `sentry_sdk.init()` behind an env-var guard. When `SENTRY_DSN` is absent, `init_sentry(app)` is a no-op; the rest of the system has no conditional Sentry branches. Per-user scoping (`sentry_sdk.set_user(...)`) is a two-line stub activated by auth middleware in Phase 1 — this module does not change when auth lands. Consumer: `create_app.py`.

- `errors.py` — Registers three error handlers on the Flask app: one for `werkzeug.exceptions.HTTPException` (preserves the HTTP status code), one for `pydantic.ValidationError` (returns 422 with field-level detail), and one for bare `Exception` (returns 500, logs `logger.exception("unhandled_exception")` which includes the `request_id` from context vars, and captures the Sentry event). Consistent error shape means Angular's HTTP interceptor can handle errors generically. Consumer: `create_app.py`, Angular HTTP interceptor.

- `health.py` — A Flask Blueprint registered at `/api/health`. The `/anthropic` route makes a minimal token-count probe against the Anthropic API (5-second timeout) and returns `{"status": "ok"}` or `{"status": "degraded"}` with 503. The `/neon` and `/stripe` routes return `{"status": "skipped"}` with 200 — the endpoint shape is stable now so CI smoke tests and future monitoring integrations can target it without a contract change when live checks are activated. Consumers: CI smoke test, `docker-build` job, future uptime monitoring.

**Patterns**: Blueprint Module Structure (ELA #2); opt-in external dependency; single initialization site.

---

### CI Pipeline Extension — `.github/workflows/deploy.yml`

**Purpose**: Gate the deploy job on a verified frontend build and a smoke-tested Docker image.

**Key Parts**:

- `build-frontend` job — Checks out the repo, runs `ng build`, and uploads the `dist/` directory as a workflow artifact. If `ng build` exits non-zero, the job fails and the downstream `docker-build` and `deploy` jobs do not run. This is the only gate needed: `ng build` catches type errors, missing imports, and broken templates that `ng test` would not surface in CI. Consumer: `docker-build` job (downloads the artifact).

- `docker-build` job — Downloads the `dist/` artifact, builds the multi-stage Docker image, starts a container, and asserts that both `/api/health/anthropic` and `/` return the expected status codes. Both assertions must pass before the `deploy` job is allowed to run. Consumer: `deploy` job.

**Patterns**: Fan-in dependency chain (build-frontend → docker-build → deploy); artifact-passing between jobs so the Dockerfile does not re-run `ng build`.

---

### Multi-stage Dockerfile + Flask Catch-all

**Purpose**: Produce a single image that serves both the Flask API and the Angular SPA, making the deployed artifact identical to what CI tested.

**Key Parts**:

- Build stage — Installs Node, runs `ng build`. Output is `dist/spec-doc/browser/`.
- Final stage — Python base, copies Flask source and the Angular `dist/` output into a `web/` subdirectory alongside the Flask app.
- Flask catch-all route in `create_app.py` — Serves static assets directly by path; falls back to `index.html` for all other paths so Angular's client-side router handles navigation. The route is activated only when the `web/` directory exists; in dev mode the directory is absent and requests fall through to Angular's dev server on `:4201`.

**Patterns**: Ported from `humanize-me` reference (references.md). Single-artifact deploy eliminates the "works in CI but not in production" class of failures.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Structured logging | `structlog` with `contextvars` | Context-var propagation makes `request_id` automatic across call stacks; JSON output is machine-parseable in Coolify's log viewer |
| Error tracking | Sentry Python SDK + `sentry-sdk[flask]` | Proven in Bubls; opt-in via DSN; per-user scoping plugs into Phase 1 auth without module changes |
| Health checks | Plain Flask Blueprint | No framework needed; endpoint shape is the only contract that matters |
| CI frontend gate | `ng build` exit code | Sufficient to catch broken builds; no Karma/Jest required in this job |
| Production image | Multi-stage Dockerfile | Single image, single deploy target; no nginx sidecar needed because Coolify Traefik handles SSL and routing |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| All four observability pieces ship together | They share the `request_id` context model; Sentry without structlog is half-blind; structlog without Sentry doesn't alert; shipping them separately leaves gaps | Slightly larger task scope; mitigated by the low LOC count of each piece |
| structlog over stdlib `logging` | Context-var propagation is not available in stdlib without manual threading; structlog's `merge_contextvars` processor makes `request_id` automatic | Adds a new dependency; existing `logger.info("msg")` call sites continue to work without change |
| Sentry opt-in via `SENTRY_DSN` env var | Local dev and CI run without a Sentry project; the code path is identical with or without DSN | If DSN is accidentally absent in production, errors are logged but not alerted — documented operational risk |
| `/api/health/neon` and `/api/health/stripe` return `{"status": "skipped"}` | Neither dependency is wired into spec-doc today; a live probe would fail with a misleading result | Monitoring tools that check for `"ok"` must be configured to also accept `"skipped"` — document this in the runbook |
| JSON logs to stdout only (Coolify captures) | Zero infra, zero cost, available immediately; upgrade path is BetterStack/Logtail when search volume justifies it | Not searchable across time periods; acceptable for a single-developer app at launch |
| Angular dist bundled into Flask image | Eliminates deploy-time drift between tested artifact and running container; mirrors the humanize-me reference | Image size increases by the Angular bundle (~2–5 MB gzipped); acceptable for this service size |

---

## Execution Flow

```
Task 1 (Structured Logging)
  └─► Task 2 (Sentry + Error Handlers)  ──┐
  └─► Task 3 (Health Check Blueprint)   ──┤
                                           ▼
                                        Task 4 (Angular CI + Multi-stage Docker)
```

Tasks 2 and 3 are parallel after Task 1 because both depend on the logger being initialized first (`structlog` first so subsequent inits log structured). Task 4 depends on Task 3 because the CI smoke test targets the health endpoint — its response contract must be stable before the assertion is written.

---

## Open Questions

- **Log destination in production** — Options: (A) stdout only, captured by Coolify (zero cost, not searchable across time); (B) BetterStack/Logtail (searchable + alertable, ~$25/mo at low volume); (C) self-hosted Loki (free, operational overhead). Decision trigger: first time a support incident requires searching logs beyond Coolify's retention window. Proposed default: A at launch, re-decide at first incident.

- **Sentry traces sample rate** — Options: 0.0 (error-only, no performance data), 0.1 (10%, matches Bubls launch default), 1.0 (full, expensive at scale). Re-decision trigger: Sentry quota warning or first performance complaint. Proposed default: 0.1.

- **Anthropic health check via adapter or SDK direct** — Options: (A) call through `modules/chain/adapter.py` to respect the adapter boundary; (B) call the Anthropic SDK directly in `health.py` because the health check is a probe, not a generation. ELA #1 says all AI provider calls go through the adapter. Implementation guide must resolve whether a token-count probe is an "AI provider call" or infrastructure plumbing. If B, the health module is an explicit documented exception to ELA #1.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview