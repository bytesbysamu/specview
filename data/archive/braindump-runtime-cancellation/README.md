# spec-doc-api — WorkflowRuntime Cancellation Hook (cooperative)

> **MERGED** into `braindump-saas-reliability.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P3 — quality + UX (user can stop a runaway 15-minute generation).
> **Effort**: ~half day (cancellation check between steps + 1 route + Angular abort button).
> **Blocks**: nothing.
> **Depends on**: WorkflowRuntime + WorkflowExecution (already shipped — `request_cancel()` exists, runtime never reads it).
> **Siblings**: `braindump-bootstrap-async.md` (long-running bootstrap is the primary consumer),
>               `braindump-streaming-task-gen.md` (cancel mid-stream),
>               `braindump-retry-recovery.md` (cancel-then-retry is a normal flow).
> **Port from**: nothing — net-new ~30-50 LOC; uses Workflows epic primitives left as a stub by Task 3.

## What

`WorkflowExecution.request_cancel()` shipped with Task 3 of the Workflows epic, transitioning the execution to `CANCELLING`. **The runtime never reads this status**, so the cancel call has no effect today — the workflow runs to completion regardless. This brain dump wires the cooperative-cancellation check into the runtime's step-iteration loop, plus the HTTP route + Angular button that exposes it.

The current UX gap: a user clicks "Bootstrap project", sees the spinner, realises they typed the wrong name, has no way to stop the generation. Their only options are wait 15 minutes or refresh the tab (the background thread keeps running — wasted Anthropic spend).

Cooperative cancellation = the runtime checks `execution.status == CANCELLING` between steps; if true, halts the loop, transitions to `CANCELLED`, and returns. Mid-step cancellation (interrupting an in-flight `chain_adapter.generate()` call) is **not** in scope — the SDK call is synchronous and would require a separate timeout/thread-kill mechanism. Between-steps is the sweet spot: deterministic, simple, covers the long-tail bootstrap case (3 sequential calls = 3 cancellation points).

### 1. Runtime — check between steps

```python
# modules/workflows/runtime.py
class WorkflowRuntime:
    def run(self, execution: WorkflowExecution, workflow: Workflow) -> Iterator[StepEvent]:
        execution.start()  # NEW → IN_PROGRESS
        context = StepContext(run_id=execution.execution_id, inputs=execution.inputs)
        try:
            for step in workflow.steps:
                # Cooperative cancellation check — runs before each step
                if execution.status == ExecutionStatus.CANCELLING:
                    execution.cancel()                      # CANCELLING → CANCELLED
                    return
                yield from step.execute(context)
            execution.complete()                            # IN_PROGRESS → COMPLETED
        except Exception as exc:
            execution.fail(str(exc))                        # IN_PROGRESS → ERROR
            raise
```

The check is one `if` per step. No threading, no signals, no SIGINT handlers. The background thread that runs this generator owns the cancellation cost — at most one full step's worth of latency between `request_cancel()` and the actual transition to `CANCELLED`.

### 2. Cancel route — `POST /api/workflows/<execution_id>/cancel`

For each consumer-feature (bootstrap, task_gen, spec_gen) the same pattern:

```python
# modules/ai/routes.py — bootstrap example
@ai_bp.post("/bootstrap-project/<job_id>/cancel")
@require_auth
def cancel_bootstrap(job_id: str):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if execution is None or execution.user_id != g.current_user.id:
        return jsonify({"error": "job not found"}), 404
    if execution.status not in (ExecutionStatus.NEW, ExecutionStatus.IN_PROGRESS):
        return jsonify({"error": "cannot cancel — not in progress",
                        "status": execution.status.value}), 409
    execution.request_cancel()                              # IN_PROGRESS → CANCELLING
    return jsonify({"status": execution.status.value}), 202
```

`task_gen` and `spec_gen` get the same shape route. Each polling endpoint already returns `status`; Angular sees `CANCELLING` then `CANCELLED` on subsequent polls.

### 3. Angular — abort button

```typescript
// new-project.component.ts
async bootstrap(params: BootstrapParams) {
  const { job_id } = await firstValueFrom(this.aiService.startBootstrap(params));
  this.activeJobId.set(job_id);

  while (true) {
    await new Promise(r => setTimeout(r, 3000));
    const status = await firstValueFrom(this.aiService.getBootstrapStatus(job_id));
    if (status.status === 'CANCELLED') return;
    if (status.done) { /* navigate to project */ return; }
  }
}

cancel() {
  const id = this.activeJobId();
  if (!id) return;
  this.aiService.cancelBootstrap(id).subscribe();
  // Polling loop above sees CANCELLED on next poll and exits
}
```

UI: red "Cancel" button next to the spinner; replaces with "Cancelling…" until status flips to `CANCELLED`. On `CANCELLED` the modal closes and any partially-written file is deleted (covered by `braindump-retry-recovery.md`'s delete pattern).

### 4. Partial-output cleanup on cancel

When a workflow cancels mid-chain, prior steps' outputs are already written to `context.outputs` and may have been persisted to git via `Persist` steps (or directly via the route handler). Two options:

- (a) **Keep partial output** (proposed) — the user can see what was generated before cancellation; manually delete or regenerate
- (b) **Auto-rollback** via `git_store.revert_to(initial_sha)` — clean slate but harder to debug

(a) is right for v1. Cleanup is the user's call; the regenerate flow already handles reset.

### 5. Tests

```python
def runtime_cancelsBetweenSteps(monkeypatch):
    """When request_cancel() lands during step 1, step 2 is not invoked."""
    invoked = []
    def step1_invoke(ctx): invoked.append("step1"); return None
    def step2_invoke(ctx): invoked.append("step2"); return None

    workflow = Workflow.builder("test").step(NoopStep(name="s1", _invoke=step1_invoke))\
                                       .step(NoopStep(name="s2", _invoke=step2_invoke)).build()
    execution = WorkflowExecution(workflow_ref="test", inputs={})
    execution.start()
    execution.request_cancel()                              # cancel BEFORE runtime runs
    list(WorkflowRuntime().run(execution, workflow))        # drain

    assert invoked == []                                    # neither step ran
    assert execution.status == ExecutionStatus.CANCELLED


def runtime_cancelsAfterFirstStep():
    """Cancel after step 1 completes; step 2 is skipped."""
    cancel_after_step1 = lambda ctx: execution.request_cancel()
    workflow = Workflow.builder("test").step(NoopStep(name="s1", _invoke=cancel_after_step1))\
                                       .step(NoopStep(name="s2", _invoke=lambda c: pytest.fail("should not run"))).build()
    execution = WorkflowExecution(workflow_ref="test", inputs={})
    execution.start()
    list(WorkflowRuntime().run(execution, workflow))
    assert execution.status == ExecutionStatus.CANCELLED


def cancelRoute_returns404_forUnknownJob(client):
    r = client.post("/api/ai/text/bootstrap-project/nonexistent/cancel")
    assert r.status_code == 404


def cancelRoute_returns409_whenAlreadyCompleted(client):
    # Set up a completed execution; assert cancel returns 409
    ...
```

## Why now

`request_cancel()` exists as dead code today — the user can call it but the runtime ignores it. The Workflows epic Task 3 author left this as an explicit open question for "Task 5 (spec_gen migration)" but Task 5 didn't pick it up either. It's been a stub on shipped code since the epic landed.

Three real consumers want it:
- **Bootstrap** runs 25 minutes; abandoning is currently a refresh-and-eat-the-cost
- **Task generation** runs 15 minutes; same UX
- **Spec generation** (`/api/spec-gen/generate`) runs ~3 calls = 6-9 minutes

All three throw away real Anthropic spend if the user can't cancel. The cost case alone justifies a half-day fix.

## What's missing

One decision: **what gets refunded if cancelled?**
- (a) Nothing — cancellation counts as a usage call (proposed) — simplest; users learn to commit before clicking Bootstrap
- (b) Refund the usage counter if cancelled before any AI call completes — fairer; needs to track which step finished
- (c) Pro-rate based on number of completed steps — fairest, most complex

(a) is right for v1. The metering brain dump's `@check_usage_limit` decorator already only charges on `< 400` responses; we keep that contract. Pro-rating is over-engineering until usage data shows users cancelling enough to matter.

## Explicitly out of scope

- **Mid-step cancellation** (interrupting an in-flight `chain_adapter.generate()`) — would require killing the subprocess (CLI provider) or aborting the SDK request. Both have race conditions; defer until users complain that 5-minute Opus calls can't be killed.
- **Cancellation propagation to sub-workflows** (Composite step kind) — Phase 2; not needed at v1.
- **Auto-cancellation on user logout / session expiry** — speculative; revisit if abandoned executions become a real cost item.
- **Cancellation deadline / TTL** (auto-cancel after N minutes of no client poll) — defer; the cost case for cancellation is user-initiated, not orphan-cleanup.
- **Differential cancellation pricing** — see What's Missing.
- **Webhook on cancellation** — no consumer named.
