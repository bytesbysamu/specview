# 📅 Timeline: SaaS Phase 3: Reliability + Observability

**Last Updated**: 2026-05-13

> Status tracking for this capability. This is the ONLY place for status.
> Epic and Architecture docs contain Priority, not Status.

---

## Done

| # | Task | Completed | Effort | Notes |
|---|------|-----------|--------|-------|
| — | Sentry projects created (api + web), API DSN configured | 2026-05-13 | — | Backend errors flowing. Frontend DSN saved but not wired. |
| — | Stripe keys configured in .env | 2026-05-13 | — | Enables Stripe health probe |

---

## In Progress

| # | Task | Started | Effort | Notes |
|---|------|---------|--------|-------|
| — | — | — | — | — |

---

## Backlog

| # | Task | Due | Effort | Notes |
|---|------|-----|--------|-------|
| 1 | **Complete health probes + Docker healthcheck** | TBD | 0.25 days | Neon + Stripe probes need real checks. Docker healthcheck interval: 300s for CLI. |
| 2 | **Activate Sentry user scoping + release tagging** | TBD | 0.25 days | Update `set_sentry_user` to accept email, wire into `@require_auth`, set `APP_RELEASE` |
| 3 | **Per-step retry — complete wiring** | TBD | 0.3 days | Routes exist. Missing: `@check_usage_limit("bootstrap")` on retry route. |
| 4 | **Cooperative cancellation — complete wiring** | TBD | 0.3 days | Route + `request_cancel()` exist. Missing: cancellation checks in `_run_bootstrap_thread`. |
| 5 | **Retry + cancel UI controls** | TBD | 0.25 days | Retry button exists but doesn't call API. Cancel button during generation doesn't exist. |

---

## Epic Progress

| Metric | Count |
|--------|-------|
| Done | 0 (prep work done: Sentry DSNs, Stripe keys) |
| In Progress | 0 |
| Backlog | 5 |
| **Total** | **5** |

---

## Related Documents

- [Epic](./epic.md) – Task definitions and scope
- [Solution Architecture](./architecture.md) – Design decisions
- [Spec Index](./spec-index.md) – Document overview
