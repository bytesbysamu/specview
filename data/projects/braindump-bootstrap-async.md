# spec-doc-api — Bootstrap Async via WorkflowRuntime

> **MERGED** into `braindump-saas-reliability.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P3 — kills the timeout class on bootstrap; precondition for reliable cloud deploy.
> **Effort**: ~0.5 day (BOOTSTRAP_WORKFLOW + 2 routes + Angular polling).
> **Blocks**: nothing.
> **Depends on**: WorkflowRuntime + WorkflowExecution (already shipped).
> **Siblings**: `braindump-streaming-task-gen.md` (partial buffer for the polling response),
>               `braindump-retry-recovery.md` (per-step retry consumes BOOTSTRAP_WORKFLOW),
>               `braindump-raise-max-tokens.md` (per-step max_tokens tuning depends on CLI fix).
> **Status**: spec-doc folder generated; implementation in flight.

## What

Migrate `POST /api/ai/text/bootstrap-project` from its current inline three-call pattern to async (HTTP 202 + polling), reusing the `WorkflowRuntime` + `WorkflowExecution` infrastructure shipped by the Workflows-as-a-Domain-Layer epic. The POST returns a job ID immediately; a background thread runs the chain through `WorkflowRuntime.run()`; Angular polls a status endpoint until done.

The current blocking call holds an HTTP connection open for 10–25 minutes. Proxies, load balancers, and OS connection-tracking will kill that connection regardless of what Flask, gunicorn, or Angular's `timeout()` is set to. The 3600s gunicorn timeout in the Dockerfile is a band-aid that *will* fail again on infrastructure we don't control. The async pattern has no HTTP connection to keep alive — it is the only structural fix.

This brain dump explicitly **does not invent a new dict-backed job store**. `WorkflowExecution` (`api/modules/workflows/execution.py`) already does this, with a state machine and proper status transitions. Bootstrap becomes the third consumer (after `task_gen` and `spec_gen`) of the same pattern.

### 1. Define `BOOTSTRAP_WORKFLOW` — `api/modules/spec_gen/workflows/bootstrap.py`

The four prompt functions already live in `modules/ai/prompts/__init__.py`. Wrap each as an `AICall` step. Total: a 4-step workflow (analysis → epic → architecture → file-marshalling).

```python
# modules/spec_gen/workflows/bootstrap.py
from modules.workflows.workflow import Workflow
from modules.workflows.steps.ai_call import AICall
from modules.workflows.steps.compute import Compute
from modules.workflows.steps.registry import register_compute
from modules.spec_gen.prompts import (
    BOOTSTRAP_ANALYSIS_SYSTEM, BOOTSTRAP_ANALYSIS_USER,
    BOOTSTRAP_EPIC_SYSTEM,     BOOTSTRAP_EPIC_USER,
    BOOTSTRAP_ARCH_SYSTEM,     BOOTSTRAP_ARCH_USER,
)

@register_compute("bootstrap.marshal_files")
def marshal_files(context):
    """Convert {analysis, epic, architecture} step outputs into the BootstrapFile list."""
    return [
        {"filename": "analysis.md",     "content": context.outputs["analysis"].text},
        {"filename": "epic.md",         "content": context.outputs["epic"].text},
        {"filename": "architecture.md", "content": context.outputs["architecture"].text},
    ]


def register_workflows(repo) -> None:
    repo.save(
        Workflow.builder("bootstrap-project")
        .inputs("braindump", "project_name", "builder", "principles", "codebase", "references")
        .outputs("files")
        .step(AICall(
            name="analysis",
            system=BOOTSTRAP_ANALYSIS_SYSTEM,
            prompt_template=BOOTSTRAP_ANALYSIS_USER,
            input_keys=("braindump", "project_name", "builder"),
            max_tokens=4096,
        ))
        .step(AICall(
            name="epic",
            system=BOOTSTRAP_EPIC_SYSTEM,
            prompt_template=BOOTSTRAP_EPIC_USER,
            input_keys=("braindump", "project_name", "builder", "principles"),
            max_tokens=8192,
        ))
        .step(AICall(
            name="architecture",
            system=BOOTSTRAP_ARCH_SYSTEM,
            prompt_template=BOOTSTRAP_ARCH_USER,
            input_keys=("braindump", "project_name", "builder", "principles", "codebase", "references"),
            max_tokens=16384,
        ))
        .step(Compute(name="files", fn_name="bootstrap.marshal_files"))
        .build()
    )
```

The architecture step gets `max_tokens=16384` because that's where truncation happens today (see `braindump-raise-max-tokens.md`).

### 2. Replace `bootstrap_project` route — async dispatch

```python
# modules/ai/routes.py
import threading
import uuid
from flask import current_app

# In-process registry of running bootstrap executions, keyed by job_id.
# WorkflowExecution carries its own status state machine; this dict only owns the lifetime.
_BOOTSTRAP_JOBS: dict[str, WorkflowExecution] = {}


@ai_bp.post("/bootstrap-project")
def bootstrap_project():
    req = BootstrapProjectRequest.model_validate(request.get_json(force=True, silent=False) or {})
    inputs = {
        "braindump":     req.braindump.strip(),
        "project_name":  req.project_name.strip(),
        "builder":       req.builder or read_context("builder"),
        "principles":    req.principles or read_context("principles"),
        "codebase":      req.codebase or read_context("codebase"),
        "references":    req.references or read_context("references"),
    }

    repo = current_app.workflow_repository
    workflow = repo.get("spec_gen/bootstrap-project")

    job_id = str(uuid.uuid4())
    execution = WorkflowExecution(workflow_ref="spec_gen/bootstrap-project", inputs=inputs)
    _BOOTSTRAP_JOBS[job_id] = execution

    threading.Thread(target=_run_bootstrap, args=(job_id, execution, workflow), daemon=True).start()
    return jsonify({"job_id": job_id}), 202


def _run_bootstrap(job_id: str, execution: WorkflowExecution, workflow) -> None:
    runtime = WorkflowRuntime()
    try:
        for _event in runtime.run(execution, workflow):
            pass  # event observers (logging, cost tracking) subscribe at the runtime level
    except Exception as exc:
        execution.fail(str(exc))   # state-machine transition; status field updated atomically
```

The route handler is ~25 lines. No try/except around the chain — `WorkflowRuntime` already handles step failures and emits `StepFailed` events; `execution.fail()` is called from outside only when something *outside* the chain breaks (e.g., a context-loading I/O error).

### 3. Status endpoint — read from WorkflowExecution

```python
@ai_bp.get("/bootstrap-project/status/<job_id>")
def bootstrap_status(job_id: str):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if execution is None:
        return jsonify({"error": "job not found"}), 404

    response = {
        "running": execution.status == ExecutionStatus.IN_PROGRESS,
        "done":    execution.status in (ExecutionStatus.COMPLETED, ExecutionStatus.ERROR),
    }
    if execution.status == ExecutionStatus.COMPLETED:
        response["files"] = execution.outputs.get("files", [])
        response["latencyMs"] = int((execution.completed_at - execution.started_at) * 1000) if execution.completed_at else None
    if execution.status == ExecutionStatus.ERROR:
        response["error"] = execution.error

    # Purge on first read after done — the consumer reads exactly once
    if response["done"]:
        _BOOTSTRAP_JOBS.pop(job_id, None)
    return jsonify(response)
```

`status` field reads come straight from `WorkflowExecution`'s state machine (no parallel status dict). The TTL question from the original brain dump is settled: **purge on first read after done**. Angular reads the result once, navigates to the project, the job is gone.

### 4. Angular — start + poll

```typescript
// new-project.component.ts
async bootstrapProject(params: BootstrapParams) {
  const { job_id } = await firstValueFrom(this.aiService.startBootstrapProject(params));
  while (true) {
    await new Promise(r => setTimeout(r, 3000));
    const status = await firstValueFrom(this.aiService.getBootstrapStatus(job_id));
    if (status.done) {
      if (status.error) throw new Error(status.error);
      return status;
    }
  }
}
```

```typescript
// ai.service.ts
startBootstrapProject(params): Observable<{job_id: string}> {
  return this.http.post<{job_id: string}>(`${this.baseUrl}/bootstrap-project`, params);
  // No timeout — POST returns in ms
}

getBootstrapStatus(jobId: string): Observable<BootstrapStatus> {
  return this.http.get<BootstrapStatus>(`${this.baseUrl}/bootstrap-project/status/${jobId}`)
    .pipe(timeout(10_000));
}
```

### 5. openapi.yaml changes

- `POST /api/ai/text/bootstrap-project` response shape changes: `{job_id: string}` (was `{files, latencyMs}`).
- New `GET /api/ai/text/bootstrap-project/status/{job_id}`.
- New `BootstrapJobStatus` schema mirrors `task_gen`'s status shape: `{running, done, files?, error?, latencyMs?}`.

The Angular `BootstrapProject` DTO type changes; the `new-project.component.ts` flow above subsumes that.

## Why now

The current 3600s gunicorn timeout is a band-aid that has already escalated twice (600s → 1200s → 3600s). The next escalation is "rebuild the whole thing async" because there is no further timeout to raise — proxies and connection-tracking will kill long-held connections regardless. Doing the migration now is cheaper than doing it after the next infrastructure outage.

The pattern is proven. `task_gen` (POST → 202 → polling GET) has zero timeout failures since T3's refactor. `WorkflowExecution` carries the state machine; `WorkflowRuntime` runs the chain; reusing both means bootstrap inherits all of T3's test coverage rather than reinventing the dict.

This also makes bootstrap the **third consumer of WorkflowRuntime** (after task_gen and spec_gen). Three consumers is the trigger the v3 brain dump named for promoting `chain.adapter` and the runtime to first-class infrastructure rather than a single-feature scaffold.

## What's missing

One decision: **do we keep `bootstrap_project` returning the old shape behind a feature flag for one release?** Options:
- (a) Hard cutover (proposed) — the old shape was already broken on long requests; preserving it preserves the broken behaviour. Angular ships the new flow on the same merge.
- (b) Feature flag — Angular reads `ENABLE_ASYNC_BOOTSTRAP` and chooses path. More test surface, less risk.

Pick (a). The old shape's failure mode is not "works but slow" — it's "kills the connection at minute 25 with no error." There's nothing to preserve.

## Explicitly out of scope

- **SSE streaming for bootstrap progress** — `braindump-streaming-task-gen.md` covers the partial-buffer-in-polling pattern that fits both task gen and bootstrap. Land that brain dump separately; bootstrap inherits the partial field for free once it's there.
- **Persistent job storage** — single-user dev tool; in-process is sufficient. The repository port + a future `WorkflowExecutionStore` adapter is the migration path when multi-user persistence is named.
- **Cancellation surface** — `WorkflowExecution.request_cancel()` exists (T3 shipped it) but the runtime doesn't yet check between steps. Wire that in once a real "user wants to abort a long bootstrap" UX appears.
- **Migrating spec_gen to use this BOOTSTRAP_WORKFLOW** — `spec_gen/generate-spec` already has its own workflow. Share prompt constants, not workflows.
- **Replacing chain.adapter.generate's max_tokens default** — handled by `braindump-raise-max-tokens.md`.
