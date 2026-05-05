# spec-doc — SaaS Reliability (async lifecycle, streaming, retry, cancellation)

> **Priority**: P3 — quality + UX. Real users will hit every one of these.
> **Effort**: ~2 days (4 features sharing the polling/runtime substrate).
> **Blocks**: nothing — all additive over the existing WorkflowRuntime.
> **Depends on**: WorkflowRuntime + WorkflowExecution (Workflows epic — already shipped); Anthropic SDK provider for streaming.
> **Siblings**: persistence (executions reference projects), monetisation (cancellations don't refund — see §4).
> **Consolidates**: former `braindump-bootstrap-async.md` + `braindump-streaming-task-gen.md` + `braindump-retry-recovery.md` + `braindump-runtime-cancellation.md`.
> **Port from**: humanize-me's Flask `Response(generator())` for the SSE half. Rest is net-new orchestration on Workflows epic primitives.

## What

Four operational capabilities for long-running AI generations, all sharing the same `WorkflowRuntime` + `WorkflowExecution` + polling substrate. Each is small individually; bundling them prevents inventing parallel state machines per feature.

1. **Async via WorkflowRuntime** — bootstrap migrates from inline 25-min HTTP call to 202 + polling, reusing the proven `task_gen` pattern.
2. **Streaming partial buffer** — runtime accumulates streamed chunks; polling endpoint surfaces them; user sees a live console instead of a spinner.
3. **Retry / regenerate** — failed or truncated tasks get a one-click rerun; bootstrap retries individual failed steps (~33% cost vs full chain).
4. **Cooperative cancellation** — `WorkflowExecution.request_cancel()` shipped but unread; this wires it into the runtime loop.

### 1. Bootstrap async (kills the timeout class)

```python
# modules/spec_gen/workflows/bootstrap.py
def register_workflows(repo) -> None:
    repo.save(
        Workflow.builder("bootstrap-project")
        .inputs("braindump", "project_name", "builder", "principles", "codebase", "references")
        .outputs("files")
        .step(AICall(name="analysis",     system=BOOTSTRAP_ANALYSIS_SYSTEM, prompt_template=ANALYSIS_USER,
                     input_keys=("braindump", "project_name", "builder"),                                   max_tokens=4096))
        .step(AICall(name="epic",         system=BOOTSTRAP_EPIC_SYSTEM,     prompt_template=EPIC_USER,
                     input_keys=("braindump", "project_name", "builder", "principles"),                      max_tokens=8192))
        .step(AICall(name="architecture", system=BOOTSTRAP_ARCH_SYSTEM,     prompt_template=ARCH_USER,
                     input_keys=("braindump", "project_name", "builder", "principles", "codebase", "references"), max_tokens=16384))
        .step(Compute(name="files", fn_name="bootstrap.marshal_files"))
        .build()
    )
```

```python
# modules/ai/routes.py
_BOOTSTRAP_JOBS: dict[str, WorkflowExecution] = {}    # in-process; purge on first done-read

@ai_bp.post("/bootstrap-project")
@require_auth
@check_usage_limit("bootstrap")
def bootstrap_project():
    inputs = {**request.get_json(force=True), "builder": ...read_context...}
    workflow = current_app.workflow_repository.get("spec_gen/bootstrap-project")
    job_id = str(uuid.uuid4())
    execution = WorkflowExecution(workflow_ref="spec_gen/bootstrap-project", inputs=inputs)
    _BOOTSTRAP_JOBS[job_id] = execution
    threading.Thread(target=_run, args=(job_id, execution, workflow), daemon=True).start()
    return jsonify({"job_id": job_id}), 202

@ai_bp.get("/bootstrap-project/status/<job_id>")
def bootstrap_status(job_id):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if not execution: return jsonify({"error": "not found"}), 404
    response = {
        "running": execution.status == ExecutionStatus.IN_PROGRESS,
        "done":    execution.status in (ExecutionStatus.COMPLETED, ExecutionStatus.ERROR),
        "current_step": execution.current_step_name,
        "partial":      execution.outputs.get("_partials", {}).get(execution.current_step_name, ""),
        "warnings":     execution.warnings,
        "error":        execution.error,
    }
    if response["done"]:
        if execution.status == ExecutionStatus.COMPLETED:
            response["files"] = execution.outputs.get("files", [])
        _BOOTSTRAP_JOBS.pop(job_id, None)        # purge on first done-read
    return jsonify(response)
```

Same pattern for `task_gen` and `spec_gen` — already async, gets streaming + retry + cancel for free below.

### 2. Streaming partial buffer

```python
# modules/workflows/steps/ai_call.py — opt-in streaming flag
class AICall(AbstractStep):
    ...
    stream: bool = False

    def _invoke(self, context):
        merged = {**context.outputs, **context.inputs}
        prompt = self.prompt_template.format_map(merged)
        if not self.stream:
            return chain_adapter.generate(self.system, prompt, model=self.model, max_tokens=self.max_tokens)
        chunks = []
        for delta in chain_adapter.stream_generate(self.system, prompt, model=self.model, max_tokens=self.max_tokens):
            chunks.append(delta)
            if cb := context.inputs.get("_partial_callback"):
                cb(self.name, "".join(chunks)[-500:])    # rolling tail
        return ChainResult(text="".join(chunks), latency_ms=0)
```

Long-form steps (architecture, impl-guide) opt in via `AICall(..., stream=True)`. Rolling 500-char tail surfaced as `partial` in the polling response. Angular renders it in `<pre>`. **No SSE client needed** — the existing 3-second polling loop sees the live preview.

Optional Phase 2: `GET /api/.../stream` returns `text/event-stream` for sub-second updates. Same backend, different transport.

### 3. Retry + recovery

Truncation heuristic (lives in `raise-max-tokens` brain dump) sets `execution.warnings` after a step completes but looks malformed (unclosed code fence, suspiciously short). Failed executions set `execution.error`.

```python
# modules/task_gen/routes.py
@task_gen_bp.post("/<project_id>/regenerate-task")
@require_auth
@check_usage_limit("task_gen")
def regenerate_task(project_id):
    task_num = request.get_json()["task_num"]
    project = current_app.project_repository.get_by_slug(g.current_user.id, project_id)
    for filename in [f for f in git_store.list_files(project.id) if re.match(rf"^task-{re.escape(task_num)}-", f)]:
        git_store.delete_file(project.id, filename, message=f"chore: regenerate task {task_num}")
    started = service.start(project.id, task_num=task_num)
    return jsonify({"started": started}), 202 if started else 409
```

Bootstrap retry uses **per-step sub-workflows** so the user pays for one call, not three, on architecture-only retries:

```python
# modules/ai/routes.py
@ai_bp.post("/bootstrap-project/<job_id>/retry")
@require_auth
@check_usage_limit("bootstrap")
def retry_bootstrap(job_id):
    step = request.get_json()["step"]                # "analysis" | "epic" | "architecture"
    prior = _BOOTSTRAP_JOBS.get(job_id)
    workflow = current_app.workflow_repository.get(f"spec_gen/bootstrap-{step}-only")
    new_inputs = {**prior.inputs,
                  "analysis": prior.outputs.get("analysis", ChainResult(text="")).text,
                  "epic":     prior.outputs.get("epic",     ChainResult(text="")).text}
    new_id = str(uuid.uuid4())
    new_exec = WorkflowExecution(workflow_ref=f"spec_gen/bootstrap-{step}-only", inputs=new_inputs)
    _BOOTSTRAP_JOBS[new_id] = new_exec
    threading.Thread(target=_run, args=(new_id, new_exec, workflow), daemon=True).start()
    return jsonify({"job_id": new_id}), 202
```

Three small sub-workflows ship alongside the main `bootstrap-project`. Angular surfaces a "Regenerate" button on any spec file with `size === 0`, `warnings.length > 0`, or `error != null`.

### 4. Cooperative cancellation

`WorkflowExecution.request_cancel()` already exists (Task 3 of the Workflows epic). The runtime never reads it — this wires it in:

```python
# modules/workflows/runtime.py
def run(self, execution, workflow):
    execution.start()
    context = StepContext(run_id=execution.execution_id, inputs={**execution.inputs, "_partial_callback": ...})
    try:
        for step in workflow.steps:
            if execution.status == ExecutionStatus.CANCELLING:
                execution.cancel()                   # CANCELLING → CANCELLED
                return
            yield from step.execute(context)
        execution.complete()
    except Exception as exc:
        execution.fail(str(exc))
        raise
```

One `if` per step. Cooperative (between-steps), not preemptive — the in-flight `chain_adapter.generate()` call still completes. Cancellation latency = at most one full step.

```python
# Per consumer feature — bootstrap shown
@ai_bp.post("/bootstrap-project/<job_id>/cancel")
@require_auth
def cancel_bootstrap(job_id):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if not execution: return jsonify({"error": "not found"}), 404
    if execution.status not in (ExecutionStatus.NEW, ExecutionStatus.IN_PROGRESS):
        return jsonify({"error": "cannot cancel", "status": execution.status.value}), 409
    execution.request_cancel()
    return jsonify({"status": execution.status.value}), 202
```

Angular shows a red "Cancel" button next to the spinner; replaces with "Cancelling…" until status flips to `CANCELLED`. Partial output is kept on cancel (user decides cleanup via the regenerate flow).

## Why now

The current 3600s gunicorn timeout is the third escalation in this band-aid sequence — proxies, load balancers, OS connection-tracking will kill long-held connections regardless. Async is the only structural fix. **All four features in this brain dump share the same backend substrate** (WorkflowRuntime + WorkflowExecution + polling endpoint); doing them in one round amortises the testing + Angular wiring.

Five real consumer cases queue up the moment the SDK provider (paid API spend) lands:
- Bootstrap timeout: lose 25 min + spend; can't retry partial work
- Spec-gen timeout: lose 6-9 min + spend
- No mid-flight feedback: users assume "stuck"
- Truncation silently ships broken docs
- No way to abort a runaway generation

## What's missing

Two decisions:

1. **Job TTL** — proposed: purge from `_BOOTSTRAP_JOBS` on first done-read. Alternatives: cap-50 LRU, or 1-hour TTL. Purge-on-read is simplest and fits the consumer pattern (Angular reads once, navigates).
2. **Cancellation refund** — proposed: cancellation counts as a usage call (no refund). The metering decorator only charges on `< 400` responses; cancel returns 202 then sees CANCELLED on next poll, but the original POST already counted. Pro-rate later if needed.

## Explicitly out of scope

- **Persistent job storage (DB-backed executions)** — single-user dev pattern; in-process is sufficient for v1.
- **Mid-step cancellation** (interrupting an in-flight `generate()` call) — would require subprocess kill / SDK abort; race-y; defer.
- **WebSocket transport** — SSE is one-way push, sufficient.
- **CLI provider streaming** — CLI is dev-only after SDK lands; no need.
- **Auto-retry on transient failures** — explicit user click only; SDK's `max_retries=2` covers HTTP transients at the right layer.
- **Cancellation propagation to sub-workflows** (Composite step kind) — Phase 2.
- **Cancellation deadline / orphan-cleanup TTL** — defer; the cost case is user-initiated.
- **Per-token cost tracking during streaming** — token counts arrive end-of-stream; mid-stream is a different surface.
- **Diff view between original and regenerated** — `git diff` between the two SHAs is one endpoint away (persistence brain dump owns it).
