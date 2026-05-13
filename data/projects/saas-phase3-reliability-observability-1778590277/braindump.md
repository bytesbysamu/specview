# SaaS Phase 3: Reliability + Observability

> **Priority**: P2 — quality floor for real users. Not a launch gate, but must ship within the first week.
> **Effort**: ~2 days.
> **Blocks**: nothing — all additive.
> **Depends on**: Phase 1 (auth interceptor for per-user Sentry scoping), Phase 2a (project isolation for per-user job scoping).

## The problem

Specview has observability infrastructure that's built but not activated, health probes that return "skipped", and zero reliability features for the 10-25 minute AI generation pipeline. A real user who hits a failure at minute 20 loses everything and must restart from scratch. There's no way to cancel a hung generation, no way to retry a single failed step, and no visibility into what's happening during the long wait.

---

## Current state (fact-checked 2026-05-13)

**Sentry — partially activated (2026-05-13):**
- Two Sentry projects created: `specview-api` (Python/Flask) and `specview-web` (JavaScript/Angular)
- API DSN set in `api/.env` → `SENTRY_DSN=https://acd82d9009a74adeafbcfe5ce982c720@o4511382072197120.ingest.de.sentry.io/4511382101360720`
- Web DSN saved in root `.env` → `SENTRY_DSN_WEB=https://c2995d9090468dcfe2b1158afaa3d738@o4511382072197120.ingest.de.sentry.io/4511382096511056`
- **Backend Sentry is receiving errors** — Python exceptions visible in Sentry dashboard. `init_sentry(app)` is wired in `create_app.py` and reads `SENTRY_DSN`.
- **Frontend Sentry is NOT wired yet** — the Angular app has no Sentry SDK integration. The DSN is saved but no code initializes it. No frontend errors flow to Sentry. Zero visibility into client-side crashes, Angular rendering errors, or HTTP failures from the user's browser.
- **`set_sentry_user()` not wired** — after `@require_auth` sets `g.current_user`, Sentry should call `sentry_sdk.set_user({"id": user.id, "email": user.email})` so every error has user context. This call doesn't exist yet — backend errors in Sentry show the stack trace but not which user was affected.
- **No `APP_RELEASE` tag** — Sentry errors aren't tied to a deploy/commit. Can't tell which release introduced a bug.
- Sentry free tier: 5K errors/month, 1 user — sufficient for launch.

**Built and working:**
- `api/modules/observability/logging.py` — structlog with JSON output, contextvars, request_id propagation. `init_logging()` is wired in `create_app.py`. Working.
- `api/modules/observability/sentry.py` — `init_sentry(app)` reads `SENTRY_DSN`, active when DSN is set. `set_sentry_user()` stub ready for auth middleware integration.
- `api/modules/observability/errors.py` — JSON error handlers for HTTPException, ValidationError, unhandled exceptions. Registered in `create_app.py`. Working.
- `api/modules/observability/health.py` — `GET /api/health/anthropic` validates Claude auth via `count_tokens` (5s timeout). Returns `ok`, `degraded`, or `skipped`.
- Chain adapter: `adapter.py` has in-process usage accumulator (`_USAGE` dict) with per-model cost tracking. `GET /api/ai/stats` returns cumulative totals.

**Stubbed health probes:**
- `GET /api/health/neon` — returns `{"status": "skipped"}` always. Should probe database connectivity.
- `GET /api/health/stripe` — returns `{"status": "skipped"}` always. Should validate Stripe API key. (Stripe keys are now configured in `.env` — this probe just needs to call `stripe.Balance.retrieve()`)
- Docker healthcheck uses `/api/health` (process liveness) not `/api/health/anthropic` (auth validity). The P0 project identified this gap but fix hasn't landed.

**Missing reliability features:**
- No per-step retry — if architecture step fails at minute 20, user must re-run entire 25-minute pipeline from scratch. Wastes time and Claude Max quota.
- No cancel mechanism — `WorkflowExecution.request_cancel()` may exist but is not wired into the bootstrap pipeline loop.
- No streaming partials — user stares at a spinner for 10-25 minutes with zero feedback on progress.
- Bootstrap runs in background threads via `_BOOTSTRAP_JOBS` dict. Frontend polls `GET /api/ai/text/bootstrap-project/status/<job_id>` every 3 seconds.

---

## Learnings from other projects

**Springular:**
Has a comprehensive health check architecture with separate probes for each external dependency (database, Stripe, Redis). Each probe has a timeout and returns a normalized status object. The key insight: health probes should be cheap (no writes, short timeout) and independent (one failing probe doesn't block others). Springular's Docker healthcheck hits a composite endpoint that aggregates all probes — container goes unhealthy if any critical dependency is down.

**Trendfy (Flask, closest stack):**
Built in 4 days so reliability is minimal, but the order processing pipeline has a useful pattern: each step writes its output to the database before proceeding to the next. If step 3 fails, steps 1 and 2 outputs are preserved in the orders table. This is the exact pattern specview needs — the bootstrap pipeline should persist each step's output so retry only replays the failed step.

**Bubls:**
Has Sentry with per-user scoping — after auth middleware sets the user, `sentry_sdk.set_user({"id": user.id, "email": user.email})` is called. Every error in Sentry shows which user was affected. Also has per-request structured logging with user_id in every log line via structlog contextvars. Both patterns are ready to wire in specview — the code exists, just needs the `SENTRY_DSN` env var and a one-line call in the auth decorator.

---

## Architecture direction

**Sentry activation is config + one line of code.** Create a Sentry project, set `SENTRY_DSN` in env, wire `set_sentry_user()` into the `@require_auth` decorator right after `g.current_user` is set. Set `APP_RELEASE` to git SHA for release tracking.

**Complete the health probes.** Neon probe: `SELECT 1` with 5s timeout. Stripe probe: `stripe.Balance.retrieve()` (zero cost, validates API key). Switch Docker healthcheck to `/api/health/anthropic` with longer interval (60s) since it makes a real API call.

**Per-step retry via sub-workflows.** Register three single-step workflows alongside the main bootstrap: `bootstrap-analysis-only`, `bootstrap-epic-only`, `bootstrap-architecture-only`. The retry endpoint takes a `job_id` and `step` name, creates a new execution using the successful outputs from prior steps as inputs. User pays for one step, not three, on an architecture-only retry. Angular surfaces a "Regenerate" button on any spec file where the step errored.

**Cooperative cancellation.** Wire `WorkflowExecution.request_cancel()` into the runtime loop — one `if` check between steps. Cancellation latency = at most one full step. Partial output is preserved. Angular shows a "Cancel" button next to the spinner during active generation.

**Streaming partials (stretch).** Add a `_partial_callback` to the pipeline context. Each chain call accumulates chunks and calls the callback with the last 500 characters. The polling endpoint includes `partial` in its response. Angular renders it in a collapsible `<pre>` block. No SSE needed — the existing 3-second polling loop picks up partials naturally. Nice UX improvement but not a launch gate.

---

## Testing baseline to maintain

Phase 3 established 146 tests across 9 spec files (39% statement coverage, 21% branch coverage). New code must maintain or improve this:

- **Health probes:** Need pytest cases for each probe — ok path, degraded path (dependency down), skipped path (env var missing). Mock the external calls (DB session, Stripe SDK).
- **Retry endpoint:** Needs test coverage for: valid retry (returns 202), job not found (404), step validation. Mock the workflow execution and thread spawning.
- **Cancel endpoint:** Needs test for: valid cancel (returns 202, status flips to CANCELLING), job not found (404), already completed (no-op or 409).
- **Frontend:** If retry/cancel buttons are added to the generation UI, add component test cases in `app.component.spec.ts` for button visibility in error state, button click triggers API call.
- **E2E:** Existing `bootstrap-pipeline.feature` covers the happy path. Consider adding a scenario for the retry flow if the mock provider supports it.
- **Structural:** New health probe endpoints should follow the existing blueprint pattern. New retry/cancel endpoints go in `ai/routes/text.py` following existing route conventions.

---

## Files involved

- `.env` — `SENTRY_DSN`, `APP_RELEASE`
- `api/modules/observability/health.py` — complete neon + stripe probes
- `api/modules/auth/decorators.py` — wire `sentry_sdk.set_user()` after auth
- `docker-compose.yml` — switch healthcheck to `/api/health/anthropic`, increase interval
- `api/modules/ai/routes/text.py` — retry + cancel endpoints
- `api/modules/runtime/workflows/` — per-step sub-workflow registration
- `web-ng/src/app/app.component.ts` — retry/cancel buttons in generation UI

## Success criteria

- Sentry captures unhandled exceptions with user context (id + email)
- `/api/health/neon` returns `ok` when DB is reachable, `degraded` on failure
- `/api/health/stripe` returns `ok` when Stripe API key is valid, `skipped` when unset
- Docker container goes `unhealthy` when Claude auth credentials are invalid
- Failed bootstrap step can be retried individually without re-running the full pipeline
- In-flight generation can be cancelled; partial output from completed steps is preserved
- Existing test suites pass without regression
