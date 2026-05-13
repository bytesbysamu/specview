# Implementation Guide: SaaS Phase 3 — Reliability + Observability

## Overview
This epic hardens specview from a fragile, unobservable prototype into a production-grade service that fails gracefully and attributes errors to affected users. The work sequences in two lanes: Tasks 1 and 2 (health probes, Sentry scoping) are independent and can be done in parallel, followed by Tasks 3 and 4 (retry, cancellation) which depend on the observability foundation, and finally Task 5 (frontend UI) which requires the backend endpoints from Tasks 3 and 4 to be complete.

## Shared Pre-flight
- Confirm Phase 1 auth interceptor is merged: verify that `modules/auth/decorators.py` contains a working `require_auth` decorator that populates `g.current_user`
- Confirm Phase 2a project isolation is merged: verify that `@require_project_ownership` is on all project routes (job dict `_BOOTSTRAP_JOBS` is global — isolation is enforced at the route layer, not the dict)
- Run the existing backend test suite to establish a green baseline (819 backend / 155 frontend): `pytest --tb=short -q`
- Verify Sentry DSN is configured in the staging environment so that scoping changes can be validated against a live Sentry project
- Verify `DATABASE_URL` is set and points to a reachable Neon Postgres instance in the staging environment
- Verify `STRIPE_SECRET_KEY` is set in staging (or intentionally absent if pre-monetization) — note: the env var is `STRIPE_SECRET_KEY`, not `STRIPE_SECRET_KEY`
- Confirm the `WorkflowExecution.request_cancel()` method exists in `modules/runtime/workflows/execution.py` (it does, at line 113)
- Decide the `APP_RELEASE` injection strategy: set it as a Docker build arg baked to the git SHA at image build time

---

## Task 1: Complete health probes + Docker healthcheck  [Effort: 0.25 days]

### What
Replace the hardcoded "skipped" stubs in the Neon and Stripe health probes with real dependency checks, and update the Dockerfile healthcheck to target the Anthropic probe so Docker orchestration can detect containers with dead Claude credentials.

### Files
- **Modify**: `modules/observability/health.py` — replace the `neon_health` stub (line 137) with a real database connectivity check using SQLAlchemy, and replace the `stripe_health` stub (line 143) with a Stripe balance retrieval call
- **Modify**: `docker-compose.yml` — update existing API healthcheck to target `/api/health/anthropic` with a 300-second interval
- **Modify**: `modules/observability/tests/test_health.py` — add test cases for the Neon and Stripe probe success, degraded, and skipped paths

### Steps
1. In `modules/observability/health.py`, replace the `neon_health` function body. Import `get_engine` from `modules/data/db/engine`. When `DATABASE_URL` is not configured, return status "skipped" with a 200. When configured, execute a trivial SQL query (such as `SELECT 1`) using `sqlalchemy.text` with a 5-second connection timeout. On success return status "ok"; on any exception return status "degraded" with the error message truncated to `_MAX_ERROR_CHARS`, and a 503 status code.
2. In the same file, replace the `stripe_health` function body. Lazily import the `stripe` module inside the handler to avoid cold-start cost. When `STRIPE_SECRET_KEY` is not set in the environment, return status "skipped" with a 200. When set, call `stripe.Balance.retrieve()` with a 5-second timeout. On success return status "ok"; on any exception return status "degraded" with the truncated error and a 503.
3. In `docker-compose.yml`, update the existing API healthcheck to target `/api/health/anthropic` instead of `/api/health`. Set the interval to 300 seconds (CLI provider makes a real API call), timeout to 30 seconds, start period to 120 seconds, and retries to 2.
4. Add tests in `modules/observability/tests/test_health.py` for both new probes. For Neon: test the "ok" path by mocking `get_engine` to return an engine whose `connect` context manager succeeds; test the "degraded" path by making the connection raise an exception; test the "skipped" path by unsetting `DATABASE_URL`. For Stripe: test "ok" by mocking `stripe.Balance.retrieve`; test "degraded" by making it raise; test "skipped" by unsetting `STRIPE_SECRET_KEY`.
5. Run the health test suite and confirm all new and existing Anthropic probe tests pass.

### Verify
- `pytest modules/observability/tests/test_health.py -v` passes with new Neon and Stripe test cases
- `curl http://localhost:3101/api/health/neon` returns `{"status": "ok"}` when DATABASE_URL points to a reachable Postgres and `{"status": "skipped"}` when unset
- `curl http://localhost:3101/api/health/stripe` returns `{"status": "ok"}` when STRIPE_SECRET_KEY is valid and `{"status": "skipped"}` when unset
- `docker compose config` shows the API healthcheck targeting `/api/health/anthropic` with 300s interval

---

## Task 2: Activate Sentry user scoping + release tagging  [Effort: 0.25 days]

### What
Update `set_sentry_user` to accept an email parameter alongside user_id, wire it into the `require_auth` decorator so every authenticated request carries user identity in Sentry scope, and confirm release tagging via `APP_RELEASE` is active in `init_sentry`.

### Files
- **Modify**: `modules/observability/sentry.py` — update the `set_sentry_user` function signature to accept an optional `email` parameter and pass it to `sentry_sdk.set_user`
- **Modify**: `modules/auth/decorators.py` — add a call to `set_sentry_user` inside the `require_auth` decorator after `g.current_user` is populated
- **Modify**: `Dockerfile` — add an `ARG APP_RELEASE` build arg and set `ENV APP_RELEASE` so the Sentry SDK picks up the deploy commit SHA at runtime

### Steps
1. In `modules/observability/sentry.py`, change the `set_sentry_user` function signature from `set_sentry_user(user_id: str)` to `set_sentry_user(user_id: str, email: str | None = None)`. Update the `sentry_sdk.set_user` call to pass a dict containing both `id` and `email` fields, omitting `email` from the dict if it is None. Remove the TODO comment on lines 46-49 since auth integration is being completed.
2. In `modules/auth/decorators.py`, add an import for `set_sentry_user` from `modules.observability.sentry`. Inside the `wrapper` function of `require_auth`, immediately after line 45 where `g.current_user = user` is set, call `set_sentry_user(str(user.id), getattr(user, 'email', None))`. This placement ensures every authenticated request — and every error raised during that request — has user context in Sentry.
3. In `Dockerfile`, add `ARG APP_RELEASE=dev` before the USER directive and add `ENV APP_RELEASE=${APP_RELEASE}` so the value propagates to the container environment. The `init_sentry` function in `sentry.py` already reads `APP_RELEASE` from `os.environ` at line 40 and passes it as the `release` parameter to `sentry_sdk.init`.
4. Verify that `init_sentry` in `sentry.py` already reads `APP_RELEASE` from the environment and passes it to `sentry_sdk.init` as the `release` parameter — confirm this is the case at line 40. No code change is needed for release tagging; it is already wired.

### Verify
- `pytest modules/auth/ -v` passes without regression
- Trigger a test error on an authenticated endpoint in staging and confirm the Sentry event shows both `user.id` and `user.email` fields
- Confirm the Sentry event in staging shows a `release` tag matching the deployed git SHA (not the default "dev")
- `grep -n "set_sentry_user" modules/auth/decorators.py` shows the call site inside `require_auth`

---

## Task 3: Per-step retry — complete wiring  [Effort: 0.3 days]

### What
The retry endpoint and sub-workflows already exist but the retry route is missing the `@check_usage_limit("bootstrap")` decorator, allowing free-tier users to retry without quota enforcement. This task adds the missing decorator so retries count against the daily usage cap.

### Files
- **Modify**: `modules/ai/routes/text.py` — add the `@check_usage_limit("bootstrap")` decorator to the `bootstrap_retry` function
- **Modify**: `modules/ai/routes/tests/test_text_bootstrap.py` — add test cases for the retry endpoint covering success, not-found, and usage-limit-hit paths

### Steps
1. In `modules/ai/routes/text.py`, add the `@check_usage_limit("bootstrap")` decorator to the `bootstrap_retry` function at line 435. Stack it between `@require_auth` (outer) and the function definition (inner), matching the same stacking order used on `bootstrap_project` at lines 267-268. The import for `check_usage_limit` is already present at line 23.
2. In `modules/ai/routes/tests/test_text_bootstrap.py`, add a test that verifies the retry endpoint returns 429 when a free-tier user has exhausted their daily bootstrap quota. Mock `get_remaining` from `modules.usage.service` to return 0, issue a POST to the retry endpoint with a valid job_id and step, and assert the response is 429 with the `free_tier_limit_reached` error code.
3. Add a test that verifies the retry endpoint returns 404 when the job_id does not exist in `_BOOTSTRAP_JOBS`.
4. Add a test that verifies the retry endpoint returns 202 with a new `job_id` in the response body when a valid job with prior outputs is retried. Seed `_BOOTSTRAP_JOBS` with a completed execution that has analysis output, request a retry of the "epic" step, and confirm the response contains a fresh job_id distinct from the original.

### Verify
- `pytest modules/ai/routes/tests/test_text_bootstrap.py -v` passes with the new retry test cases
- The `bootstrap_retry` function in `text.py` has both `@require_auth` and `@check_usage_limit("bootstrap")` decorators
- `pytest --tb=short -q` full suite shows no regressions
- Manual test: call the retry endpoint with a valid job and confirm the `X-Usage-Remaining` header appears in the 202 response

---

## Task 4: Cooperative cancellation — complete wiring  [Effort: 0.3 days]

### What
The cancel endpoint sets the cancellation flag via `execution.request_cancel()`, but the original `_run_bootstrap_thread` function has no cancellation checks between its three sequential `chain_adapter.generate()` calls — the thread ignores the flag and runs all steps to completion. This task inserts cancellation checks between steps so the thread exits cleanly when the flag is set, preserving completed step outputs.

### Files
- **Modify**: `modules/ai/routes/text.py` — add cancellation checks between steps in `_run_bootstrap_thread`, and add `failed_step` and status fields to the poll response in `bootstrap_status`
- **Modify**: `modules/ai/routes/tests/test_text_bootstrap.py` — add test cases for cancellation during the bootstrap thread

### Steps
1. In `modules/ai/routes/text.py`, inside `_run_bootstrap_thread` (starting at line 228), add a cancellation check after each `chain_adapter.generate()` call completes and before the next step begins. After the analysis step output is stored in `execution.outputs["analysis"]` (line 238), check `if execution.status is ExecutionStatus.CANCELLING`. If true, call `execution.cancel()`, record the latency, and return from the function. Add the same check after the epic step output is stored (line 245) and before the architecture prompt is built.
2. In the `bootstrap_status` function (line 315), enhance the response body to include a `failed_step` field when the execution status is ERROR. Set `body["failed_step"]` to `execution.current_step_name` so the frontend knows which step failed and can offer a targeted retry. Also include `body["status"]` set to `execution.status.value` for all responses so the frontend can distinguish between "cancelling" and "cancelled" states.
3. In `modules/ai/routes/tests/test_text_bootstrap.py`, add a test that verifies cooperative cancellation. Create a `WorkflowExecution`, start it, set its status to CANCELLING via `request_cancel()`, seed it into `_BOOTSTRAP_JOBS`, then verify that the status endpoint returns the "cancelling" status. Add another test verifying that after the execution transitions to CANCELLED, the status endpoint returns "cancelled" with `done: true`.
4. Add a test verifying that the cancel endpoint returns 409 when the job has already completed (status is COMPLETED).

### Verify
- `pytest modules/ai/routes/tests/test_text_bootstrap.py -v` passes including the new cancellation tests
- Reading `_run_bootstrap_thread` in `text.py` shows cancellation checks between each of the three step boundaries
- The poll response includes `failed_step` when a job is in ERROR status and `status` reflecting the execution state
- `pytest --tb=short -q` full suite shows no regressions

---

## Task 5: Retry + cancel UI controls in generation view  [Effort: 0.25 days]

### What
Surface a cancel button during active generation and a retry button on step failure in the Angular frontend generation view, wired to the backend cancel and retry endpoints. The Angular frontend lives in the `web-ng/` directory (separate from the backend in `/app`). This task adds conditional UI controls based on the poll response state already tracked by the component.

### Files
- **Modify**: `web-ng/src/app/services/projects.service.ts` — add `cancelBootstrap(jobId: string)` and `retryBootstrapStep(jobId: string, step: string)` methods returning `Promise<T>` via `firstValueFrom()`
- **Modify**: `web-ng/src/app/app.component.ts` — add signal-based state for cancel/retry visibility, wire click handlers that call the new service methods, and handle the job_id swap on retry (generation UI lives in the root component, not a separate generation component)
- **Modify**: `web-ng/src/app/app.component.html` — add a cancel button visible during `running` state and a retry button visible during `error` state with the `failed_step` label

### Steps
1. In `web-ng/src/app/services/projects.service.ts`, add a `cancelBootstrap` method that sends a POST to `/api/ai/text/bootstrap-project/{jobId}/cancel` via `firstValueFrom()` returning `Promise<{status: string}>`. Add a `retryBootstrapStep` method that sends a POST to `/api/ai/text/bootstrap-project/{jobId}/retry` with a JSON body containing the step name, returning `Promise<{job_id: string}>`.
2. In the root component (`app.component`) TypeScript file, add a `cancelling` signal initialized to `false`. Add an `onCancel` method that calls `cancelBootstrap` with the current job ID, sets `cancelling` to `true`, and on success lets the existing poll loop pick up the state transition. Add an `onRetry` method that calls `retryBootstrapStep` with the current job ID and the `failed_step` from the poll response, then on success updates the tracked job ID to the new one returned in the response and resets the component state so the existing poll loop begins polling the new job.
3. In the root component (`app.component`) template, add a cancel button inside the active-generation progress area. Conditionally render it when the poll state is `running` and not already `cancelling`. Bind its click to `onCancel()`. When `cancelling` is true, show a disabled button with "Cancelling..." text instead.
4. In the same template, add a retry button that renders when the poll state indicates `error` and a `failed_step` is present. Display the failed step name on the button label (e.g., "Retry architecture"). Bind its click to `onRetry()`. After the user clicks retry, replace the retry button with the standard progress indicator as the new job begins polling.
5. Update the poll response interface or type in the component to include the `failed_step` and `status` fields returned by the enhanced backend poll endpoint from Task 4.

### Verify
- `ng build --configuration production` in the `web-ng/` directory completes without errors
- During active generation in the browser, a cancel button appears alongside the progress indicator and transitions to "Cancelling..." on click
- On a step failure, the retry button appears with the failed step name and clicking it starts a new poll cycle with the fresh job ID
- The existing generation happy path (all steps succeed) renders identically with no visual regressions