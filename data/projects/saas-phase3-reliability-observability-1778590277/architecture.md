# 🏗️ Solution Architecture: SaaS Phase 3 — Reliability + Observability

## Architecture Overview

Phase 3 converts specview's backend from "errors vanish into logs" to "failures are attributed, recoverable, and cancellable." The core insight is that the bootstrap pipeline already writes each step's output to disk as a markdown file before proceeding to the next step. This means the infrastructure for per-step retry already exists in the data layer — a retry only needs to re-execute a single step function, reading prior successful outputs from the project folder as input context. No new workflow abstraction is required; the retry endpoint reuses the same step functions the bootstrap pipeline already calls.

The observability side is almost entirely activation of existing code. Sentry is receiving backend errors today but without user identity or release tags, making triage impossible. The `set_sentry_user()` helper exists in the observability module; it just needs a single call site in the auth decorator. Health probes follow the same pattern — the probe infrastructure and route blueprint exist, but two probes return hardcoded "skipped" instead of checking their dependencies. Completing them is a matter of wiring real checks into the existing probe shape.

Cancellation and retry share a design constraint: both interact with the in-process job state dict (`_BOOTSTRAP_JOBS`) that the bootstrap pipeline already uses for polling. Cancellation adds a flag to this dict that the pipeline loop checks between steps. Retry creates a new job entry that runs a single step instead of the full sequence. Both patterns stay within the existing 202-and-poll contract — no new transport mechanism, no new state store, no Redis.

## Design Principles

| Principle | Application in Phase 3 |
|-----------|------------------------|
| P1 — Adapter Boundary | Health probes for Neon and Stripe call through their respective adapter surfaces, not raw SDK imports. The Anthropic probe already follows this pattern via the chain adapter's `count_tokens` method |
| P2 — Thin HTTP Layer | Retry and cancel endpoints validate input (job exists, step name is valid, job is in a retryable/cancellable state), then delegate to service functions. No business logic in route handlers |
| P3 — Async 202 + Polling | Retry returns 202 with a new job ID and reuses the existing polling endpoint. Cancel returns 202 immediately; the next poll reflects the cancelled state. No new transport patterns introduced |
| P4 — No Speculative Abstractions | The implementation uses a `_RETRY_WORKFLOW_REFS` dict + `WorkflowRepositoryFs` to map step names to sub-workflows registered in `bootstrap.py`. This is the existing pattern, not a new abstraction. Each sub-workflow is a single-step `Workflow` that runs via `WorkflowRuntime`. |
| P7 — File Size & Structure | Retry and cancel endpoints add to existing `text.py` routes. Health probe completion stays within the existing `health.py` file. No new modules created for fewer than 50 lines of new logic |

## Component Design

### Health Probe Completion

**Purpose:** Replace hardcoded "skipped" responses in Neon and Stripe probes with real dependency validation, and fix the Docker healthcheck to detect dead Claude credentials.

The existing health blueprint in `api/modules/observability/health.py` already defines the probe shape — each probe returns a status object with `status` (ok, degraded, skipped) and optional metadata. The Anthropic probe demonstrates the pattern: call a cheap, read-only API method with a short timeout, catch failures, return a normalized status.

The Neon probe executes a trivial read query with a 5-second timeout. If the connection fails or times out, the probe returns "degraded" rather than crashing the health endpoint. If no database URL is configured, it returns "skipped" — preserving the ability to run specview without a database during local development.

The Stripe probe calls the balance retrieval endpoint, which is free, requires no parameters, and validates that the API key is authentic. Same timeout-and-degrade pattern. When no Stripe key is configured (pre-monetization), the probe returns "skipped" — this is correct behavior, not a gap.

The Docker healthcheck switches from `/api/health` (process liveness only) to `/api/health/anthropic` (Claude credential validation). The interval increases to 300 seconds (5 minutes) because the Anthropic probe under CLI provider makes a real generation call, not just a `count_tokens` check. The `health.py` code comment confirms 300s for CLI provider. The `start_period` must accommodate container boot time so the first few probe failures during startup don't trigger an unhealthy state.

### Sentry User Scoping and Release Tracking

**Purpose:** Make every backend exception in Sentry actionable by attaching user identity and deploy version.

The `set_sentry_user()` function exists in `api/modules/observability/sentry.py` but currently only accepts `user_id: str` — it must be updated to also accept `email` so Sentry errors show both identity fields. It needs exactly one call site: inside the `@require_auth` decorator in `api/modules/auth/decorators.py`, immediately after `g.current_user` is populated from the JWT, passing both `g.current_user.id` and `g.current_user.email`. This placement guarantees that every authenticated request — and therefore every error raised during an authenticated request — carries the user's ID and email in Sentry's scope.

Unauthenticated errors (health probes, login failures) intentionally have no user context. This is correct — there is no user to attribute them to.

Release tracking uses an `APP_RELEASE` environment variable set to the git SHA at deploy time. The Sentry SDK reads this via its `release` parameter during initialization. This connects Sentry errors to specific deploys, enabling "introduced in release X" filtering. The value is set once in the Docker build or Coolify deploy config; the application reads it from the environment at startup.

### Per-Step Retry for Bootstrap Pipeline

**Purpose:** Allow a user to retry a single failed pipeline step without replaying the entire 10–25 minute sequence.

The bootstrap pipeline writes each step's output to the project folder as it completes: `analysis.md`, then `epic.md`, then `architecture.md`, then `timeline.md`, then `implementation-guide.md`. When step 3 (architecture) fails, the project folder contains valid `analysis.md` and `epic.md` from the successful steps. These files persist on disk regardless of whether the overall job succeeds or fails.

The retry endpoint accepts a project ID and a step name. It validates that the project exists, that the step name is valid, and that the prerequisite outputs exist on disk. It then creates a new background job — using the same `_BOOTSTRAP_JOBS` dict and the same 202-and-poll contract as the original bootstrap — that runs only the requested step function. The step function reads its input context from the prior step files already on disk, exactly as it would during a normal pipeline run.

This design has a critical trade-off: **retry replays a step using the current versions of prior outputs, not the versions that existed when the original pipeline ran.** If a user manually edits `analysis.md` between the original run and the retry, the retried step sees the edited version. This is acceptable — and arguably desirable — because the user may have edited the analysis precisely to fix the issue that caused the downstream step to fail. The alternative (snapshotting prior outputs at pipeline start) adds complexity for a scenario that helps the user.

The retry creates a new job ID, not reusing the failed one. This avoids state machine complexity around resetting a failed job's status. The frontend polls the new job ID with the same polling logic it already uses. From the frontend's perspective, a retry is indistinguishable from a fresh generation — it just completes faster because only one step runs.

**What this does not support:** Retrying a step that succeeded. The UI only surfaces the retry control on failure states. Regenerating a successful step is a separate feature (full regeneration) that this phase does not address.

### Cooperative Cancellation

**Purpose:** Let a user cancel an in-flight generation between steps, preserving output from completed steps.

Cancellation is cooperative, not preemptive. **Current gap:** the original `_run_bootstrap_thread` has NO cancellation check between its 3 sequential `chain_adapter.generate()` calls — the cancel endpoint sets the flag but the thread runs to completion. Only retry jobs via `_run_bootstrap_via_runtime` honour the flag because they delegate to `WorkflowRuntime.run()`. The fix: add `if execution.is_cancelling: execution.cancel(); return` checks between steps in `_run_bootstrap_thread`. After this fix, the bootstrap pipeline loop checks a cancellation flag between steps. If the flag is set, the loop exits cleanly, marks the job as cancelled, and preserves whatever step outputs have already been written to disk. The maximum cancellation latency is one full step — if the user cancels during the architecture step, that step runs to completion (or failure) before the loop exits.

The cancel endpoint sets the flag and returns 202 immediately. The next poll response reflects the transition to a cancelling state, then to cancelled once the loop has exited. The job's step outputs remain on disk and are accessible through the normal project file endpoints.

The design deliberately avoids mid-step cancellation (killing the Claude subprocess or aborting the API call). Mid-step cancellation would require subprocess signal handling for the CLI provider and request cancellation for the SDK provider — two different mechanisms behind the adapter boundary. The complexity is not justified: cancellation latency of one step (3–8 minutes) is acceptable when the alternative is waiting for the remaining steps (potentially 15+ minutes). Users who are unhappy with one-step latency can close their browser; the daemon thread will complete the current step and then check the flag.

**State transitions for a cancelled job:** `running` → `cancelling` (flag set, current step still executing) → `cancelled` (loop exited, partial output preserved). The `cancelling` state is visible to the frontend via the poll endpoint so the UI can show "Cancelling after current step completes…" rather than implying instant cancellation.

### Retry and Cancel UI Controls

**Purpose:** Surface retry and cancel actions in the generation view so users can act on failures and hung jobs without developer tools.

The generation view in `web-ng/src/app/` already polls the bootstrap status endpoint every 3 seconds and renders the current job state. The UI changes are additive — new controls conditional on job state, wired to new API endpoints.

During active generation (`running` state), a cancel button appears alongside the existing progress indicator. Clicking it calls the cancel endpoint and transitions the button to a disabled "Cancelling…" state until the next poll confirms cancellation.

On step failure (`error` state with a `failed_step` field in the poll response), a retry button appears that identifies the failed step by name. Clicking it calls the retry endpoint, receives a new job ID, and the polling loop switches to the new job — reusing the existing polling mechanism entirely.

The controls are intentionally minimal: one button for cancel, one button for retry. No confirmation dialogs — cancel is safe (output is preserved) and retry is cheap (one step, not four). The cost of an accidental click is low; the cost of a confirmation dialog on every interaction with a frustrated user is high.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Health probes | Flask blueprint (existing) | Probes already follow the blueprint pattern in `health.py`; completion adds real checks, not new infrastructure |
| Error tracking | Sentry Python SDK (existing) | Already initialized and receiving errors; activation is configuration, not integration |
| Background jobs | `threading.Thread` + module-level dict (existing) | Retry jobs use the same 202-and-poll pattern as bootstrap; no new job infrastructure |
| Cancellation | Boolean flag in job state dict | Cooperative check between steps; no subprocess signals, no external coordination |
| Frontend | Angular signals (existing) | Retry/cancel controls are conditional rendering based on poll state already tracked in the component |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Reuse step functions directly instead of registering sub-workflows | P4 — no speculative abstraction. The bootstrap has four steps today and will not have forty. Calling step functions directly avoids a workflow registry that serves one consumer | If step count grows significantly, this becomes repetitive. Acceptable: refactor when the third similar retry path appears, not before |
| Cooperative cancellation between steps, not mid-step | Mid-step cancel requires two different abort mechanisms (subprocess kill for CLI, request abort for SDK) behind the adapter boundary. One-step latency (3–8 min) is acceptable vs. 15+ min remaining pipeline time | User waits up to one full step after pressing cancel. Acceptable because partial output is preserved and the alternative complexity is high |
| New job ID for retry instead of resetting failed job state | Avoids state machine complexity (failed → retrying → running → done). The frontend already handles switching to a new job ID during fresh generation | Retry history is implicit (multiple job IDs for the same project). Acceptable: there is no retry analytics requirement today |
| Docker healthcheck targets `/api/health/anthropic` with 60s interval | A container with invalid Claude credentials is functionally dead for its primary purpose. Process-level liveness is insufficient — the container must validate its ability to call the AI provider | Health probe makes a real API call with (minimal) token cost. 60s interval bounds this to ~1440 calls/day. Acceptable given the probe uses `count_tokens`, not a generation call |
| No streaming partials in this phase | Requires new polling payload shape, frontend rendering of partial markdown, and callback plumbing through the chain adapter. The existing 3-second poll with step-level progress is adequate for launch | Users see a spinner for 3–8 minutes per step with no content preview. Acceptable: the poll already reports which step is active, providing coarse progress. Revisit if user feedback indicates blind waiting is a churn factor |
| Frontend Sentry SDK deferred to a follow-up phase | Independent of backend reliability features; requires Angular SDK setup, source map upload, and a separate error budget evaluation. Mixing it into this phase dilutes focus | Zero visibility into client-side errors persists. Acceptable: backend errors are the higher-severity gap because they affect the AI pipeline; frontend errors are typically rendering issues with lower blast radius |
| Retry reads current disk state, not snapshotted inputs | Snapshotting prior step outputs at pipeline start adds storage complexity for a scenario (user edits between failure and retry) that is actually beneficial — the user may have fixed the input that caused the failure | If a user accidentally corrupts a prior output between failure and retry, the retried step receives corrupted input. Mitigated: the original pipeline wrote the file, and manual editing is an intentional act |
| Cancel preserves partial output as accessible project files | Completed step outputs are already written to the project folder during normal pipeline execution. Cancellation simply stops writing new files — no cleanup, no rollback | A cancelled project has incomplete specs (e.g., analysis and epic but no architecture). The project view must handle this gracefully — showing available files without implying completeness. This is already the case during active generation |

## Integration Points

### Auth Decorator → Sentry Scope

The `@require_auth` decorator in `api/modules/auth/decorators.py` is the single point where user identity is established for a request. Adding the Sentry user scope call here guarantees coverage across all authenticated endpoints without requiring each route to remember to set context. This follows the same pattern proven in the Bubls project.

### Bootstrap Pipeline → Cancellation Check

The bootstrap loop in `api/modules/ai/workflows/spec_gen/bootstrap.py` iterates through steps sequentially. The cancellation check inserts between iterations — after one step completes and before the next begins. This is the natural seam; no restructuring of the loop is required.

### Poll Endpoint → Retry/Cancel State

The existing poll endpoint at `GET /api/ai/text/bootstrap-project/status/<job_id>` returns the job state dict. Retry and cancel add new fields to this dict: `failed_step` (which step failed, enabling targeted retry) and `cancelling` (flag has been set, current step still running). The frontend reads these fields to determine which controls to render. No new endpoints are needed for state queries — the existing poll contract expands naturally.

### Retry Endpoint → Step Functions

The retry endpoint in `api/modules/ai/routes/text.py` validates the request, then calls the specific step function from the bootstrap module. It passes the project path so the step function reads its input context from prior output files on disk — the same file paths the function uses during a normal pipeline run. The step function does not know it is being called as a retry; it simply generates output for its step given the available context.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Retry requested for a step whose prerequisites do not exist on disk | 409 Conflict — the prior steps must succeed before this step can be retried. The response body names the missing prerequisite |
| Retry requested for a job that is still running | 409 Conflict — cannot retry while generation is active. User must cancel first or wait for completion |
| Cancel requested for a job that has already completed or failed | No-op — return 200 with current job state. Cancelling a finished job is not an error; it is simply unnecessary |
| Cancel requested for a job that is already cancelling | Idempotent — return 202. Setting the flag twice has no side effects |
| Health probe dependency is unreachable | Probe returns `degraded` with error metadata. Other probes are unaffected. The composite health endpoint aggregates individual probe results |
| Sentry DSN is not configured | `init_sentry()` no-ops silently. `set_sentry_user()` no-ops silently. No crashes, no log spam. This is the expected state in local development |

## Related Documents

- [Analysis](./analysis.md) — Problems and observability gaps driving this phase
- [Epic](./epic.md) — Scope, task breakdown, and success criteria
- [Timeline](./timeline.md) — Delivery schedule and task sequencing
- [Implementation Guide](./guides/phase-3-reliability.md) — Step-by-step build instructions for all five tasks