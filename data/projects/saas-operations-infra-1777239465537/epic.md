# 🎯 Epic: SaaS Operations & Infra

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Production systems fail silently without observability. When the Anthropic SDK provider and user auth land in Phase 1, real 500s will surface through user complaints rather than dashboards unless structured logging, error tracking, and health checks are already in place. The four observability pieces share a `request_id` context model and are cheaper to ship together than to wire incrementally — each piece without the others leaves a gap in the debug chain. The port cost from Bubls is low; the configuration cost (Sentry project, log-destination decision) is one-time admin work that pays for itself on the first production incident.

A broken `ng build` shipping silently is the Angular analogue of the same problem. Backend CI gates are solid, but the frontend has none. A four-job pipeline and a multi-stage Dockerfile make the deployed artifact identical to what CI tested — closing the gap before any external user lands.

Both concerns share the same theme — production maturity before growth — and each is too small to warrant a separate epic. Shipping them together avoids two separate planning and review cycles while keeping the scope contained.

**Value Proposition**: Observability and CI hardening ship as a unit before Phase 1 so every subsequent epic is debuggable and every deploy is verified.

---

## Scope

### What This Epic Covers

- **Structured logging** — JSON log output with `request_id` propagation across all modules
- **Sentry error tracking** — opt-in via environment variable; per-user scoping stubbed until auth middleware exists
- **JSON error handlers** — consistent error shape for HTTP exceptions, validation errors, and unhandled exceptions
- **Health check blueprint** — `/api/health/anthropic` as a live check; `/api/health/neon` and `/api/health/stripe` as stubs returning `{"status": "skipped"}` until those dependencies are wired
- **Angular CI gate** — `build-frontend` job that blocks deploy on a broken `ng build`
- **Multi-stage Dockerfile** — bundles Angular `dist/` into the Flask image; Flask catch-all serves Angular client-side routing in production

### What This Epic Does NOT Cover

- ❌ **nginx + Let's Encrypt SSL** — Coolify Traefik is the SSL layer; standalone certbot is relevant only if Coolify is replaced
- ❌ **Structural cleanup** (`docs/` lift, `projects/` rename) — file-path churn with no user-facing value; scope after a major release
- ❌ **Sentry Replay, OpenTelemetry, APM** — single service, single developer; re-scope at first compliance trigger or second service boundary
- ❌ **Per-tenant log isolation, PII scrubbing** — `user_id` in every log line is sufficient; re-scope at first compliance trigger
- ❌ **Per-PR preview deploys, Kubernetes/Helm** — re-scope when team size exceeds one
- ❌ **Neon + Stripe live health checks** — neither is a spec-doc dependency today; stubs satisfy the stable endpoint contract without the operational overhead

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Structured Logging** | None | — | 0.5 days | High |
| 2 | **Sentry + Error Handlers** | Task 1 | Yes (with 3) | 0.5 days | High |
| 3 | **Health Check Blueprint** | Task 1 | Yes (with 2) | 0.5 days | High |
| 4 | **Angular CI + Multi-stage Docker** | Task 3 | No | 1 day | Low |

### Task 1: Structured Logging

Establish JSON-structured logging with `request_id` propagation in a new `modules/observability/` module, and migrate every existing module from the stdlib logger to the structured equivalent so that correlated log lines are available from the first day of Phase 1. This is the load-bearing foundation: Sentry needs structured context, and the error handlers need a functioning logger — both are blocked until this is in place.

**Port budget**: ~30 LOC for the logging module; the per-module logger migration is mechanical. Per-user context injection is deferred to Phase 1 auth middleware.

---

### Task 2: Sentry + Error Handlers

Add opt-in Sentry integration and register JSON error handlers for HTTP exceptions, validation errors, and unhandled exceptions into `create_app()` directly after logging initialization. Every unhandled exception must produce both a Sentry event and a correlated log line with the same `request_id`. Per-user Sentry scoping is a stub in this task — it is populated by auth middleware in Phase 1.

**Port budget**: ~45 LOC across the Sentry and error-handler modules. The stub for per-user scope is two lines; activating it in Phase 1 requires no changes to this module.

---

### Task 3: Health Check Blueprint

Register a `/api/health` blueprint with a live check for the Anthropic dependency and stable `{"status": "skipped"}` stubs for Neon and Stripe. A consistent, versioned endpoint contract here is required before Task 4 can define its smoke-test assertions — the CI pipeline targets this endpoint, so the shape must not change when Neon and Stripe live checks are activated later.

**Port budget**: ~40 LOC for the health blueprint. Neon and Stripe live-check bodies are deferred; the endpoint routes and response schema are stable from day one.

---

### Task 4: Angular CI + Multi-stage Docker

Extend the GitHub Actions pipeline with a `build-frontend` job and a `docker-build` job that assembles the multi-stage image and smoke-tests it before the deploy job runs. A failed `ng build` must block the deploy. The multi-stage Dockerfile is the production container shape — a single image serving both the Flask API and the bundled Angular app — replacing the current backend-only image.

**Port budget**: ~90 lines across two new CI job definitions, the Dockerfile build stages, and a Flask catch-all route. No changes to the existing `test-backend` or `deploy` jobs.

---

## Success Criteria

- ✅ An unhandled exception returns `{"error": "internal_server_error", "code": 500}`, emits a structured log line containing `request_id`, and creates a Sentry event when the DSN is configured
- ✅ Every log line produced during a request lifecycle shares the same `request_id` value, enabling full-request correlation in any log viewer
- ✅ `GET /api/health/anthropic` returns `{"status": "ok"}` against a valid API key and `{"status": "degraded"}` with a `503` on provider failure
- ✅ `/api/health/neon` and `/api/health/stripe` return `{"status": "skipped"}` with `200` — stable shape, no live dependency
- ✅ A broken `ng build` produces a failed CI workflow that prevents the deploy job from running
- ✅ The Docker image built in CI serves `200 OK` from both the API base path and the Angular root in the smoke-test step

---

## Non-Goals

- ❌ **Coolify replacement with standalone nginx** — Traefik handles SSL and routing; certbot is redundant until the deploy target changes
- ❌ **Log aggregation beyond stdout** — Coolify captures stdout at launch; upgrade to an aggregator when search volume justifies the cost
- ❌ **Sentry Replay** — activate at the first hard-to-reproduce user bug, not at launch
- ❌ **OpenTelemetry / full APM** — Sentry plus structured logs cover the single-service, single-developer case; re-scope at the second-service boundary
- ❌ **Structural file moves** — `projects/` rename and `docs/` lift are cosmetic; defer to a quiet week after a major release

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview