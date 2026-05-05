# SaaS Operations & Infra — Analysis

## The Problem
spec-doc ships with no error visibility, no structured logs, and no dependency health checks. When the Anthropic SDK provider and auth land in Phase 1, real-user 500s will surface only through user reports. All four observability pieces share a `request_id` context model and must ship as a unit before Phase 1.

## Hard Constraints
- Coolify Traefik is the SSL/routing layer — standalone nginx + certbot is redundant at the current deploy target
- Single-container Flask + static is the production shape — multi-stage Dockerfile must preserve this, not introduce a second service
- No external queue or persistent store — log output is stdout only; no sidecar log agent
- Neon and Stripe are not spec-doc dependencies today — health check endpoints for both are premature

## Open Questions
- **Log destination**: brain dump proposes Coolify stdout as the launch default — confirm this is a decision (stdout until volume justifies an aggregator), not a question the epic should re-open
- **Neon + Stripe health checks**: omit until the dependency is actually wired, or add stubs returning `{"status": "skipped"}` now so the endpoint contract is stable?

## Dependencies & Sequencing
- Observability init order is fixed: structlog → Sentry → error handlers → health blueprint; breaking this order loses structured context in Sentry
- Sentry per-user scoping requires Phase 1 auth middleware to exist first; the hook is a stub until then
- Angular CI and the multi-stage Dockerfile need a stable `/api/health` endpoint to smoke-test against — don't merge before observability lands

## Explicitly Out of Scope
- nginx + Let's Encrypt SSL — Coolify Traefik covers this; re-scope only if Coolify is replaced
- Structural cleanup (docs/ lift, projects/ rename) — file-path churn with no user-facing value; re-scope after a major release, not mid-sprint
- Sentry Replay, OpenTelemetry, APM, PII scrubbing, per-tenant log isolation — single service, single developer; re-scope at first compliance trigger or second service
- Per-PR preview deploys, Kubernetes/Helm — re-scope when team size > 1