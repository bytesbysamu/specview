# 🎯 Epic: SaaS Phase 3 — Reliability + Observability

## Business Value

A 10–25 minute AI pipeline with no recovery path is a churn machine. When a user's architecture step fails at minute 20, they lose everything and must restart from scratch — burning their time and Claude Max quota. Every unrecoverable failure is a support ticket for a solo founder who can't afford to triage them, or worse, a silent churn event with no signal at all. Retry and cancel are table-stakes expectations for any long-running workflow; shipping without them invites the kind of early-user frustration that poisons word-of-mouth before the product finds its audience.

Observability has the same economics. Backend Sentry is receiving errors today, but without user context there's no way to correlate a stack trace to the person it affected. Health probes return hardcoded "skipped," so Docker orchestration can't distinguish a healthy container from one with dead database credentials. These gaps are invisible during solo testing and catastrophic under real load. Fixing them now — before paying users arrive — is an order of magnitude cheaper than diagnosing blind production incidents later.

This phase converts specview from "works on my machine" to "fails gracefully and tells me who was affected." That's the minimum quality floor required to charge money for a product that asks users to wait 25 minutes for output.

## Scope

### What This Epic Covers

- **Health probe completion** — Replace stubbed Neon and Stripe probes with real dependency checks; fix Docker healthcheck to validate Claude auth credentials
- **Sentry user scoping + release tracking** — Update `set_sentry_user()` signature to accept email (currently only takes `user_id: str`), wire into `@require_auth` after `g.current_user` is set, tag errors with `APP_RELEASE`
- **Per-step retry** — Allow a user to retry a single failed pipeline step using preserved outputs from prior successful steps, avoiding full pipeline replay
- **Cooperative cancellation** — Let a user cancel an in-flight generation between steps, preserving partial output from already-completed steps
- **Frontend retry/cancel UI** — Surface regenerate and cancel controls in the generation view so users can act on failures and hung jobs

### What This Epic Does NOT Cover

- ❌ **Streaming partials** — Tagged as stretch, requires new polling payload shape and frontend rendering. The existing 3-second polling UX is adequate for launch. Re-scope if user complaints about blind waiting appear post-launch
- ❌ **Frontend Sentry SDK integration** — Angular SDK initialization, client-side error capture, and source maps. Valuable but independent of the reliability features here; defer to a follow-up
- ❌ **Alerting rules / PagerDuty** — Zero paying users doesn't justify alert routing infrastructure. Re-scope when paying users exist
- ❌ **E2E retry test scenario** — Unit and integration coverage is sufficient; mock provider may not support the step-failure flow needed for an E2E retry case

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Complete health probes + Docker healthcheck** | None | — | 0.25 days | High |
| 2 | **Activate Sentry user scoping + release tagging** | Phase 1 auth interceptor | With T1 | 0.25 days | High |
| 3 | **Per-step retry — complete wiring** | Phase 2a project isolation | After T1–T2 | 0.3 days | High |
| 4 | **Cooperative cancellation — complete wiring** | T3 | With T3 | 0.3 days | High |
| 5 | **Retry + cancel UI controls in generation view** | T3, T4 | After T3–T4 | 0.25 days | High |

**Status note (2026-05-13):** Tasks 3-4 are partially implemented. Backend routes exist (`bootstrap_cancel`, `bootstrap_retry` in `text.py`), sub-workflows registered in `bootstrap.py`, `request_cancel()` exists in `WorkflowExecution`. Remaining work:
- **Retry:** Missing `@check_usage_limit("bootstrap")` decorator. Route works but free users can retry unlimited.
- **Cancel:** `_run_bootstrap_thread` (original bootstrap) has NO cancellation check between steps — the cancel endpoint sets the flag but the thread ignores it and runs all 3 steps. Only retry jobs via `_run_bootstrap_via_runtime` honour the flag. Must add cancellation checks to the original thread.
- **Frontend:** Retry button exists but `retryLastOp()` just resets status to idle — it does NOT call the retry API. Cancel button during active generation doesn't exist.

## Success Criteria

- ✅ `/api/health/neon` returns `ok` when database is reachable, `degraded` on connection failure
- ✅ `/api/health/stripe` returns `ok` when Stripe API key is valid, `skipped` when unconfigured
- ✅ Docker container reports `unhealthy` when Claude auth credentials are invalid
- ✅ Every unhandled backend exception in Sentry includes `user.id` and `user.email`
- ✅ Sentry errors are tagged with `APP_RELEASE` matching the deployed commit
- ✅ A failed bootstrap step (e.g., architecture) can be retried individually; only the failed step's Claude cost is incurred
- ✅ An in-flight generation can be cancelled; completed step outputs are preserved and accessible
- ✅ Generation UI shows a cancel control during active generation and a regenerate control on step failure
- ✅ All pre-existing test suites pass without regression (819 backend / 155 frontend); new endpoints have test coverage for success, not-found, and conflict paths

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design for retry, cancel, and health probes
- [Implementation Guide](./guides/phase-3-reliability.md) — Step-by-step build instructions
- [Timeline](./timeline.md) — Status tracking and delivery schedule