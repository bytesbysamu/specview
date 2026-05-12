# SaaS Phase 3: Reliability + Observability

> **Priority**: P2 — quality floor for real users. Not a launch gate, but must ship within the first week.
> **Effort**: ~2 days.
> **Blocks**: nothing — all additive.
> **Depends on**: Phase 1 (auth interceptor for per-user Sentry scoping), Phase 2 (billing status for Stripe health probe).

## What this is

Activate the observability stack that's already built but not configured, complete the stubbed health probes, and add reliability features (retry, cancel, streaming) that real users will need the first time a generation fails or hangs.

---

## Current State (fact-checked 2026-05-12)

**What exists and works:**
- `api/modules/observability/logging.py` — structlog with JSON output, contextvars, request_id propagation. `init_logging()` is wired in `create_app.py`.
- `api/modules/observability/sentry.py` — `init_sentry(app)` reads `SENTRY_DSN`, silent no-op if unset. `set_sentry_user()` stub ready for auth middleware integration.
- `api/modules/observability/errors.py` — JSON error handlers for HTTPException, ValidationError, and unhandled exceptions. Registered in `create_app.py`.
- `api/modules/observability/health.py` — `GET /api/health/anthropic` validates Claude auth via `count_tokens` (5s timeout). Returns `ok`, `degraded`, or `skipped`.
- Chain adapter: `adapter.py` has in-process usage accumulator (`_USAGE` dict) with per-model cost tracking. `GET /api/ai/stats` returns cumulative totals.
- Bootstrap pipeline: runs in background threads via `_BOOTSTRAP_JOBS` dict. Frontend polls `GET /api/ai/text/bootstrap-project/status/<job_id>` every 3 seconds.

**What's stubbed or missing:**
- `GET /api/health/neon` — returns `{"status": "skipped"}` (not probing the database)
- `GET /api/health/stripe` — returns `{"status": "skipped"}` (not checking Stripe API)
- `SENTRY_DSN` not set — Sentry is completely silent
- No retry mechanism — if a bootstrap step fails, the entire pipeline must be re-run from scratch
- No cancel mechanism — `WorkflowExecution.request_cancel()` may exist but is not wired into the bootstrap pipeline
- No streaming partials — user sees a spinner for 10-25 minutes with no feedback
- Docker healthcheck uses `/api/health` (process liveness) not `/api/health/anthropic` (auth validity). P0 project identified this but fix hasn't landed yet.

---

## Task 1 — Activate Sentry + Complete Health Probes

> **Effort**: 0.5 days

### Sentry activation

1. Create Sentry project for Specview
2. Set `SENTRY_DSN` in `.env` and Coolify env vars
3. Wire `set_sentry_user()` into `@require_auth` decorator — after `g.current_user` is set, call `sentry_sdk.set_user({"id": user.id, "email": user.email})`
4. Set `APP_RELEASE` to git SHA: `APP_RELEASE=specview@$(git rev-parse --short HEAD)`

### Neon health probe

```python
@health_bp.get("/neon")
def neon_health():
    """Probe database connectivity via a lightweight query."""
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        return jsonify({"status": "degraded", "error": str(exc)[:100]}), 503
```

### Stripe health probe

```python
@health_bp.get("/stripe")
def stripe_health():
    """Validate Stripe API key via a balance retrieval (zero cost)."""
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        return jsonify({"status": "skipped"}), 200
    try:
        import stripe
        stripe.api_key = key
        stripe.Balance.retrieve(timeout=5)
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        return jsonify({"status": "degraded", "error": str(exc)[:100]}), 503
```

### Docker healthcheck fix (from P0)

Switch Docker healthcheck to validate Claude auth, not just process liveness:

```yaml
# docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-sf", "http://127.0.0.1:3101/api/health/anthropic"]
  interval: 60s
  timeout: 10s
  retries: 3
  start_period: 120s
```

**Note from P0 review:** The `/api/health/anthropic` endpoint returns `"skipped"` when `ANTHROPIC_API_KEY` is not set (which is the case under CLI provider with Claude Max). This endpoint needs to be updated to do a lightweight CLI validation when `CHAIN_PROVIDER=cli`. This is flagged in the P0 epic Task 4.

---

## Task 2 — Bootstrap Per-Step Retry

> **Effort**: 1 day
> **Port from**: `braindump-saas-reliability.md` retry + recovery section.

The bootstrap pipeline has 3 sequential steps (analysis → epic → architecture). If architecture fails, the user currently loses the successful analysis and epic results and must re-run the entire pipeline. This wastes time and Claude Max quota.

### Per-step sub-workflows

Register three single-step workflows alongside the main bootstrap:

```python
# modules/ai/workflows/spec_gen/bootstrap.py
# Main pipeline (existing)
register_workflow("bootstrap-project", steps=[analysis, epic, architecture])

# Per-step retry workflows (new)
register_workflow("bootstrap-analysis-only", steps=[analysis])
register_workflow("bootstrap-epic-only", steps=[epic])
register_workflow("bootstrap-architecture-only", steps=[architecture])
```

### Retry endpoint

```python
@ai_bp.post("/bootstrap-project/<job_id>/retry")
@require_auth
@check_usage_limit("bootstrap")
def retry_bootstrap(job_id):
    step = request.get_json()["step"]  # "analysis" | "epic" | "architecture"
    prior = _BOOTSTRAP_JOBS.get(job_id)
    if not prior:
        return jsonify({"error": "job not found"}), 404

    workflow = workflow_repository.get(f"bootstrap-{step}-only")
    new_inputs = {
        **prior.inputs,
        "analysis": prior.outputs.get("analysis", ""),
        "epic": prior.outputs.get("epic", ""),
    }
    new_id = str(uuid.uuid4())
    new_exec = WorkflowExecution(workflow_ref=f"bootstrap-{step}-only", inputs=new_inputs)
    _BOOTSTRAP_JOBS[new_id] = new_exec
    threading.Thread(target=_run, args=(new_id, new_exec, workflow), daemon=True).start()
    return jsonify({"job_id": new_id}), 202
```

### Angular

Surface a "Regenerate" button on any spec file where `error != null` or `warnings.length > 0`. The button calls the retry endpoint for the specific failed step.

---

## Task 3 — Cancel In-Flight Generation

> **Effort**: 0.5 days

### Backend

Add cancel endpoint:

```python
@ai_bp.post("/bootstrap-project/<job_id>/cancel")
@require_auth
def cancel_bootstrap(job_id):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if not execution:
        return jsonify({"error": "not found"}), 404
    execution.request_cancel()  # sets status to CANCELLING
    return jsonify({"status": "cancelling"}), 202
```

Wire cancellation check into the pipeline loop — between steps, check if cancellation was requested:

```python
for step in workflow.steps:
    if execution.status == "cancelling":
        execution.cancel()  # CANCELLING → CANCELLED
        return
    # ... run step
```

Cooperative cancellation (between-steps, not preemptive). Cancellation latency = at most one full step. Partial output is preserved.

### Angular

Red "Cancel" button next to the spinner during generation. Replaces with "Cancelling..." until status flips.

---

## Task 4 — Streaming Partial Preview (Optional)

> **Effort**: 1 day
> **Verdict**: nice UX improvement but not a launch gate. Defer if time is tight.

The user currently stares at a spinner for 10-25 minutes. Streaming partials would show a rolling tail of the in-progress generation in a `<pre>` block.

**Backend:** Add `_partial_callback` to the pipeline context. Each chain call accumulates chunks and calls the callback with the last 500 characters. The polling endpoint includes `partial` in its response.

**Frontend:** If `response.partial` is non-empty, display it in a collapsible live preview below the status bar. Auto-scroll to bottom.

**No SSE needed.** The existing 3-second polling loop picks up partials naturally.

---

## Files to Change

| File | Change |
|------|--------|
| `.env` | Add `SENTRY_DSN`, `APP_RELEASE` |
| `api/modules/observability/health.py` | Complete neon + stripe probes |
| `api/modules/auth/decorators.py` | Wire `sentry_sdk.set_user()` after auth |
| `docker-compose.yml` | Switch healthcheck to `/api/health/anthropic` |
| `api/modules/ai/routes/text.py` | Add retry + cancel endpoints |
| `web-ng/src/app/app.component.ts` | Add retry/cancel buttons to generation UI |

## Success Criteria

- [ ] Sentry captures unhandled exceptions with user context (id + email)
- [ ] `/api/health/neon` returns `ok` when DB is reachable, `degraded` otherwise
- [ ] `/api/health/stripe` returns `ok` when Stripe API key is valid
- [ ] `docker ps` shows `unhealthy` when Claude auth credentials are invalid
- [ ] Failed bootstrap step can be retried individually without re-running the full pipeline
- [ ] In-flight generation can be cancelled; partial output is preserved
