# spec-doc-api — Retry + Recovery for Failed and Truncated Tasks

> **MERGED** into `braindump-saas-reliability.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.

---

> **Priority**: P3 — quality + UX (user can recover from failures without engineer help).
> **Effort**: ~1 day (regenerate route + delete-file helper + Angular button + truncation flag).
> **Blocks**: nothing.
> **Depends on**: WorkflowRuntime + WorkflowExecution (already shipped — used to re-run failed executions),
>                `braindump-raise-max-tokens.md` (truncation heuristic moves there as the canonical home;
>                this brain dump consumes it).
> **Siblings**: `braindump-raise-max-tokens.md` (truncation detection),
>               `braindump-streaming-task-gen.md` (partial buffer state — early failure visibility),
>               `braindump-bootstrap-async.md` (re-run flow for failed bootstrap steps).
> **Port from**: nothing — net-new orchestration; uses Workflows epic primitives.

## What

A regenerate flow that handles three failure modes that real users hit:

1. **Explicit error** — `WorkflowExecution.status == ERROR`, `execution.error` set. Thread caught an exception.
2. **Empty file** — execution claims `COMPLETED` but the written file is 0 bytes (Claude returned nothing).
3. **Truncated file** — output cut mid-sentence (covered by truncation heuristic in `braindump-raise-max-tokens.md`).

For all three, Angular surfaces a "Regenerate" button on the affected file. One click → POST to a regenerate endpoint → re-runs the same workflow with the same inputs → new file overwrites the bad one. No engineer intervention required.

Currently a failed task requires SSH-ing in, deleting the bad file, editing the project's manifest, and triggering generation again. Two failure modes happened in the last work session. They will happen again.

### 1. Truncation detection — already in `raise-max-tokens` brain dump

The heuristic lives in `task_gen/service.py` per the max-tokens brain dump. After the workflow completes, before marking the execution done:

```python
warnings = []
if _looks_truncated(execution.outputs.get(filename_step_name, "").text):
    warnings.append("output may be truncated — regenerate recommended")
execution.warnings = warnings   # NEW field on WorkflowExecution; surfaced via status
```

`WorkflowExecution.warnings: list[str] = []` ships in the existing execution dataclass; null-default keeps backward compat.

### 2. POST `/api/projects/<id>/regenerate-task` — single-task case

```python
# modules/task_gen/routes.py
@task_gen_bp.post("/<project_id>/regenerate-task")
@require_auth
@check_usage_limit("task_gen")             # counts as a regular generation for metering
def regenerate_task(project_id: str):
    body = request.get_json(force=True, silent=True) or {}
    task_num = body.get("task_num")
    if not task_num:
        return jsonify({"error": "task_num required"}), 400

    project = current_app.project_repository.get_by_slug(g.current_user.id, project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404

    # Find the existing task file via git_store; delete from working tree (commit handles it)
    matches = [f for f in git_store.list_files(project.id) if re.match(rf"^task-{re.escape(task_num)}-.+\.md$", f)]
    for filename in matches:
        git_store.delete_file(project.id, filename, message=f"chore: regenerate task {task_num} (delete prior)")

    # Reuse the existing task_gen workflow + start mechanism
    started = service.start(project.id, task_num=task_num)
    if not started:
        return jsonify({"started": False, "alreadyRunning": True}), 409
    return jsonify({"started": True}), 202
```

`git_store.delete_file()` is a new op alongside `write_file` (commits a deletion; history retains the previous version). The project's "find next missing task" logic re-selects this slot because the file no longer exists at HEAD.

### 3. POST `/api/ai/text/bootstrap-project/<job_id>/retry` — failed bootstrap step

For bootstrap failures (architecture step errored after analysis + epic completed), retry only the failed step using the existing analysis + epic outputs. No need to regenerate the whole chain.

```python
@ai_bp.post("/bootstrap-project/<job_id>/retry")
@require_auth
@check_usage_limit("bootstrap")
def retry_bootstrap(job_id: str):
    body = request.get_json(force=True, silent=True) or {}
    step_name = body.get("step")     # "analysis" | "epic" | "architecture"
    if step_name not in ("analysis", "epic", "architecture"):
        return jsonify({"error": "step must be one of analysis|epic|architecture"}), 400

    prior_execution = _BOOTSTRAP_JOBS.get(job_id)
    if prior_execution is None or prior_execution.user_id != g.current_user.id:
        return jsonify({"error": "job not found"}), 404

    # Build a new execution that includes the prior steps' outputs as inputs
    repo = current_app.workflow_repository
    workflow = repo.get(f"spec_gen/bootstrap-{step_name}-only")    # one-step workflow per name
    new_inputs = {
        **prior_execution.inputs,
        "analysis": prior_execution.outputs.get("analysis", ChainResult(text="")).text,
        "epic":     prior_execution.outputs.get("epic",     ChainResult(text="")).text,
    }
    new_job_id = str(uuid.uuid4())
    new_execution = WorkflowExecution(workflow_ref=f"spec_gen/bootstrap-{step_name}-only", inputs=new_inputs)
    _BOOTSTRAP_JOBS[new_job_id] = new_execution
    threading.Thread(target=_run_bootstrap, args=(new_job_id, new_execution, workflow), daemon=True).start()
    return jsonify({"job_id": new_job_id}), 202
```

Three small workflows ship alongside the main `bootstrap-project`: `bootstrap-analysis-only`, `bootstrap-epic-only`, `bootstrap-architecture-only`. Each is a one-`AICall`-step workflow that takes the appropriate inputs (architecture-only takes `epic` as an input rather than running the prior step). The user pays for one call instead of three on retry.

### 4. Angular — regenerate button on every spec file

```typescript
// spec-file.component.ts
@Component({...})
export class SpecFileComponent {
  file = input.required<SpecFile>();
  status = input<TaskStatus>();

  get isRegenerable(): boolean {
    return this.file().size === 0
        || this.status()?.warnings?.length > 0
        || this.status()?.error != null;
  }

  regenerate() {
    const taskNum = this.file().filename.match(/^task-(\d+(?:\.\d+)?)-/)?.[1];
    this.taskGenService.regenerate(this.projectId, taskNum)
      .subscribe(() => this.pollUntilDone());
  }
}
```

Three states show the button:
- **Empty file** (`size === 0`) — red badge, "Generation failed"
- **Warning** (`warnings.length > 0`) — yellow badge, "Truncation detected"
- **Error** (`error != null`) — red badge, error message

Disabled while a regeneration is already running for that project.

### 5. Status response — surface `warnings` + `error`

```python
# task_gen/routes.py — extend the existing snapshot
return jsonify({
    "running":   execution.status == ExecutionStatus.IN_PROGRESS,
    "done":      execution.status in (ExecutionStatus.COMPLETED, ExecutionStatus.ERROR),
    "filename":  execution.outputs.get("filename"),
    "warnings":  execution.warnings,                         # NEW
    "error":     execution.error,                            # already there
    # ... existing fields ...
})
```

Bootstrap-async's status endpoint surfaces the same fields with the same shape. Angular reads `warnings` to show yellow badge, `error` to show red badge.

### 6. `git_store.delete_file()` — new op

```python
# modules/git_store/service.py
def delete_file(project_id: int, filename: str, message: str | None = None) -> str:
    """Remove filename from the working tree; commit; return new SHA."""
    repo = _open(project_id)
    file_path = Path(repo.workdir) / filename
    if file_path.exists():
        file_path.unlink()
    repo.index.remove(filename)
    repo.index.write()
    tree = repo.index.write_tree()
    sha = repo.create_commit("HEAD", _AUTHOR, _AUTHOR,
        message or f"chore({filename}): delete",
        tree, [repo.head.target])
    return str(sha)
```

History retains the previous version forever (`git log` shows the file existed; `git show <sha>:filename` recovers it). The user gets free undo: even after regenerate, the prior content is one git command away.

## Why now

A 0-byte `architecture.md` (the `workflows-1777207716306` project earlier this week) currently requires a developer to fix manually. The regenerate endpoint makes this a one-click operation for any user. The truncation heuristic from the max-tokens brain dump prevents the silent quality degradation that hides the failure today.

The Workflows epic shipped `WorkflowExecution` with the state machine + `error` field already in place. `warnings` is one new field. Reusing the workflow infrastructure means this brain dump is ~150 LOC of orchestration and one new git op — not a parallel system.

Both failure modes happened in the last session. They will happen again.

## What's missing

Two decisions:

1. **Auto-retry on transient failures?** Options:
   - (a) No auto-retry (proposed) — every retry is user-initiated; preserves audit trail and avoids retry storms
   - (b) Auto-retry once on `RateLimitError` only — defensible; the SDK's built-in retries already cover transient network blips
   - (c) Auto-retry on any error up to N times — risky; can hide real prompt bugs

   (a) is right for v1. The SDK provider's `max_retries=2` already handles transient network errors at the HTTP layer; layer-above retries should be explicit.

2. **Bootstrap retry granularity** — should `/retry` accept a step name (proposed) or only re-run the whole chain?
   - (a) Per-step retry (proposed) — saves 60% of cost on architecture-only retries; needs three small "X-only" workflows
   - (b) Full re-run only — simpler; uses the existing `bootstrap-project` workflow; ~3x cost on the failure case

   (a) is right when the SDK provider is the default (cost matters). If sticking with CLI provider for dev only, (b) is fine since cost is zero locally.

## Explicitly out of scope

- **Automatic retry without user action** — explicit user click only; never silently overwrite a file
- **Max retry count enforcement** — if a task keeps failing, the user should inspect the prompt or open a support ticket
- **Partial continuation** ("continue from where you left off") — unreliable with current LLMs; defer indefinitely
- **Diff view between original and regenerated** — `git diff` between the two SHAs is one endpoint away (already in `braindump-saas-git-storage-layer.md`); UI surface deferred
- **Cancellation of an in-flight regeneration** — `WorkflowExecution.request_cancel()` exists but the runtime hook is not wired up; covered by the cancellation hook in `braindump-saas-observability.md`'s open-questions list (cap #48)
- **Cross-project retry** — single-project scope; multi-project bulk operations are admin-tools territory (cap #75, deferred)
