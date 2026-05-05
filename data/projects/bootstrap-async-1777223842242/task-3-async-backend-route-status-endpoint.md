Now I have all the context needed. Let me generate the guide.

# Task 3: Async Backend — Route + Status Endpoint

---

## 1. Context

This task converts the synchronous `POST /api/ai/text/bootstrap-project` handler — which holds an HTTP connection open for up to 25 minutes while running a three-step AI chain — into a 202 fire-and-forget that returns a `job_id` in milliseconds. A new `GET /api/ai/text/bootstrap-project/status/<job_id>` endpoint surfaces `WorkflowExecution` state so the Angular polling client can retrieve the six generated files once the chain completes. The structural failure mode (infrastructure-terminated connections on long-lived requests) is eliminated entirely: there is no held connection to kill. This is the third and final step that enables the New Project flow to function end-to-end without timeout failures.

**Trade-offs considered:**
- **Use `WorkflowRuntime` + `AICall` steps (as spec_gen does)** — rejected because `AICall._invoke` stores `ChainResult` objects in `context.outputs`, and `str.format_map` at the next step renders the dataclass repr rather than the `.text` content; this is a silent correctness defect in multi-step chained prompts.
- **SSE progress streaming** — deferred to `braindump-streaming-task-gen.md`; this task ships polling first, streaming can layer over it later.
- **task_gen pattern (WorkflowExecution + direct chain calls in thread body)** — chosen because it is the proven in-codebase async pattern, reuses existing prompt functions without new template constants, avoids the `ChainResult` interpolation issue, and fits within the "no new modules" budget.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/spec-doc/api

git status                                        # Flag any unrelated M/?? entries
git diff HEAD -- modules/ai/routes.py openapi.yaml dtos/models.py tests/test_ai_bootstrap.py
make test 2>&1 | tail -5                          # Record baseline; expect 192 passing
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: 192/192 passing.

---

## 3. Files

### To Create (new)
- None — all changes are contained in existing files.

### To Modify (cite CODEBASE CONTEXT)
- `spec-doc/api/openapi.yaml` — add `GET /api/ai/text/bootstrap-project/status/{job_id}` path; change POST response from 200 → 202; add `BootstrapJobStartResponse` and `BootstrapJobStatus` schemas (lines 426–453 and 882–893 are the bootstrap section; new schemas follow `GenerateTaskStatusResponse` at line 940)
- `spec-doc/api/dtos/models.py` — auto-generated; regenerate via `make generate-dtos` after openapi change; commit with `git add -f`
- `spec-doc/api/modules/ai/routes.py` — current: synchronous `bootstrap_project` handler (lines 169–228); target: 202 async handler + status handler + thread function + module-scope `_BOOTSTRAP_JOBS` dict; add `threading`, `uuid`, `WorkflowExecution`, `ExecutionStatus` imports; remove `BootstrapProjectResponse` from DTO import list
- `spec-doc/api/tests/test_ai_bootstrap.py` — current: 11 tests for sync 200/502 shape; target: updated assertions for 202/polling shape + 5 new status endpoint tests

### To Leave Alone
- `spec-doc/api/modules/workflows/execution.py` — `WorkflowExecution` and `ExecutionStatus` are imported and used as-is; no changes to the state machine
- `spec-doc/api/modules/ai/prompts/__init__.py` — existing `bootstrap_*_prompt` functions are called directly from the thread body; no new template constants needed
- `spec-doc/api/modules/spec_gen/routes.py` — imports `BootstrapProjectResponse` for its own use; untouched
- `spec-doc/api/modules/task_gen/service.py` — reference pattern only; not modified

---

## 4. Implementation Steps

### Step 1: Update `openapi.yaml` — new schemas and paths

**Action**: Add `BootstrapJobStartResponse` and `BootstrapJobStatus` schemas; change the POST response to 202; add the GET status path.

**File**: `spec-doc/api/openapi.yaml`

**Pattern — schema additions** (insert after `GenerateTaskStatusResponse` block, before `responses:` at line 966):

```yaml
    BootstrapJobStartResponse:
      type: object
      required: [job_id]
      properties:
        job_id:
          type: string
          description: Opaque UUID identifying the background bootstrap job.

    BootstrapJobStatus:
      type: object
      required: [running, done]
      properties:
        running:
          type: boolean
          description: True while the background thread is IN_PROGRESS.
        done:
          type: boolean
          description: True once the thread has reached a terminal state.
        files:
          type: array
          items:
            $ref: '#/components/schemas/BootstrapFile'
          description: Present and populated only when done is true and no error occurred.
        error:
          type: string
          description: Error message captured from the background thread. Present only on failure.
        latencyMs:
          type: integer
          minimum: 0
          description: Wall-clock milliseconds from job start to completion. Present only when done.
```

**Pattern — POST response change** (line 439–445 in the existing `bootstrap-project` POST block):

```yaml
      responses:
        '202':
          description: Job accepted; poll /status/{job_id} for progress
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BootstrapJobStartResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
```

**Pattern — new GET path** (insert after the POST `bootstrap-project` block, before `/api/spec-gen/generate:` at line 455):

```yaml
  /api/ai/text/bootstrap-project/status/{job_id}:
    get:
      summary: Poll the status of a bootstrap job
      operationId: getBootstrapProjectStatus
      tags: [ai]
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Job status — running, done with files, or done with error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BootstrapJobStatus'
        '404':
          description: Job not found or already evicted after first terminal read
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

**Verify**: `python -c "import yaml; yaml.safe_load(open('openapi.yaml'))"` — no parse error; exit 0.

---

### Step 2: Regenerate DTOs

**Action**: Run the codegen make target so `dtos/models.py` gains `BootstrapJobStartResponse` and `BootstrapJobStatus`; commit the generated file.

**File**: `spec-doc/api/dtos/models.py` (auto-generated — never hand-edit)

**Pattern** (expected additions at bottom of generated models, matching schema names):

```python
class BootstrapJobStartResponse(BaseModel):
    job_id: str

class BootstrapJobStatus(BaseModel):
    running: bool
    done: bool
    files: Optional[List[BootstrapFile]] = None
    error: Optional[str] = None
    latencyMs: Optional[conint(ge=0)] = None
```

**Verify**:
```bash
make generate-dtos          # regenerates dtos/models.py
make check-dtos             # must exit 0 — confirms yaml and generated file are in sync
python -c "from dtos.models import BootstrapJobStartResponse, BootstrapJobStatus; print('ok')"
```

---

### Step 3: Update `modules/ai/routes.py` — imports, module-scope dict, thread function, handlers

**Action**: Add four items at the top: `import threading`, `import uuid`, `WorkflowExecution` import, `ExecutionStatus` import. Remove `BootstrapProjectResponse` from the `dtos.models` import list (it is no longer used in this module). Add `_BOOTSTRAP_JOBS` at module scope. Add `_run_bootstrap_thread`. Replace the synchronous `bootstrap_project` handler. Add `bootstrap_status` handler.

**File**: `spec-doc/api/modules/ai/routes.py`

**Pattern — new imports** (add to existing top-of-file imports block; port from `modules/task_gen/service.py` lines 29–38):

```python
import threading
import uuid

from modules.workflows.execution import WorkflowExecution, ExecutionStatus
```

**Pattern — updated DTO import** (remove `BootstrapProjectResponse`; keep `BootstrapFile`):

```python
from dtos.models import (
    ...
    BootstrapProjectRequest,
    BootstrapFile,
    # BootstrapProjectResponse removed — spec_gen still imports it from dtos directly
)
```

**Pattern — module-scope dict** (after `ai_bp = Blueprint(...)`, before first route handler; mirrors `task_gen/service.py` line 52):

```python
_BOOTSTRAP_JOBS: dict[str, WorkflowExecution] = {}
```

**Pattern — thread function** (insert before `bootstrap_project` handler; ports task_gen `run_generation` structure, `service.py` lines 229–341):

```python
def _run_bootstrap_thread(execution: WorkflowExecution) -> None:
    """Background thread body. Drives the three-step chain; state machine via WorkflowExecution."""
    t0 = time.monotonic()
    inputs = execution.inputs
    try:
        system, prompt = bootstrap_analysis_prompt(
            inputs["braindump"], inputs["project_name"], inputs["builder"]
        )
        analysis = chain_adapter.generate(system, prompt).text

        system, prompt = bootstrap_epic_prompt(
            inputs["braindump"], inputs["project_name"], analysis,
            inputs["builder"], inputs["principles"],
        )
        epic = chain_adapter.generate(system, prompt).text

        system, prompt = bootstrap_architecture_prompt(
            inputs["braindump"], inputs["project_name"], epic,
            inputs["builder"], inputs["principles"],
            inputs["codebase"], inputs["references"],
        )
        architecture = chain_adapter.generate(system, prompt, max_tokens=16384).text

        execution.outputs.update({
            "analysis": analysis,
            "epic": epic,
            "architecture": architecture,
            "latency_ms": int((time.monotonic() - t0) * 1000),
        })
        execution.complete()
    except Exception as exc:
        execution.outputs["latency_ms"] = int((time.monotonic() - t0) * 1000)
        if not execution.is_terminal:
            execution.fail(str(exc))
```

**Pattern — async POST handler** (replace lines 169–228 entirely):

```python
@ai_bp.post("/bootstrap-project")
def bootstrap_project():
    req = BootstrapProjectRequest.model_validate(
        request.get_json(force=True, silent=False) or {}
    )
    project_name = req.project_name.strip()
    braindump = req.braindump.strip()
    if not project_name or not braindump:
        return jsonify({"error": "project_name and braindump are required"}), 400

    job_id = str(uuid.uuid4())
    inputs = {
        "braindump": braindump,
        "project_name": project_name,
        "builder": req.builder or read_context("builder"),
        "principles": req.principles or read_context("principles"),
        "codebase": req.codebase or read_context("codebase"),
        "references": req.references or read_context("references"),
    }
    execution = WorkflowExecution(workflow_ref="ai/bootstrap-project", inputs=inputs)
    execution.start()                        # NEW → IN_PROGRESS before thread dispatch
    _BOOTSTRAP_JOBS[job_id] = execution
    threading.Thread(
        target=_run_bootstrap_thread,
        args=(execution,),
        name=f"bootstrap[{job_id[:8]}]",
        daemon=True,
    ).start()
    return jsonify({"job_id": job_id}), 202
```

**Pattern — status handler** (add immediately after `bootstrap_project`; projects `WorkflowExecution` state to wire shape; evicts on first terminal read — architecture doc §Status Endpoint):

```python
@ai_bp.get("/bootstrap-project/status/<job_id>")
def bootstrap_status(job_id: str):
    execution = _BOOTSTRAP_JOBS.get(job_id)
    if execution is None:
        return jsonify({"error": "job not found"}), 404

    done = execution.is_terminal
    body: dict = {"running": execution.is_running, "done": done}

    if done:
        _BOOTSTRAP_JOBS.pop(job_id, None)          # evict on first terminal read
        if execution.status is ExecutionStatus.COMPLETED:
            outputs = execution.outputs
            epic = outputs.get("epic", "")
            tasks = bootstrap_extract_tasks(epic)
            pn = execution.inputs["project_name"]
            files = [
                BootstrapFile(filename="analysis.md",   content=outputs.get("analysis", "")),
                BootstrapFile(filename="epic.md",       content=epic),
                BootstrapFile(filename="architecture.md", content=outputs.get("architecture", "")),
                BootstrapFile(filename="spec-index.md", content=generate_spec_index(pn)),
                BootstrapFile(filename="timeline.md",   content=generate_timeline(pn, tasks)),
                BootstrapFile(filename="README.md",     content=generate_readme(pn)),
            ]
            body["files"] = [f.model_dump() for f in files]
            body["latencyMs"] = outputs.get("latency_ms", 0)
        elif execution.error:
            body["error"] = execution.error

    return jsonify(body)
```

**Verify**:
```bash
python -c "from modules.ai.routes import ai_bp, _BOOTSTRAP_JOBS, bootstrap_status; print('ok')"
python -m pytest tests/test_ai_bootstrap.py -x -q 2>&1 | head -30   # expect failures in existing tests before step 4
```

---

### Step 4: Update `tests/test_ai_bootstrap.py` — async assertions + status tests

**Action**: Add `waitForDone` helper and `reset_bootstrap_jobs` autouse fixture. Update assertions in 11 existing test methods for the new 202/polling shape. Add 5 new test functions for the status endpoint contract.

**File**: `spec-doc/api/tests/test_ai_bootstrap.py`

**Pattern — new helpers and fixture** (insert after existing imports; port from `task_gen/tests/test_routes.py` lines 76–99):

```python
import time
import modules.ai.routes as _routes_mod

def _post_bootstrap(client, body=None):
    return client.post(
        "/api/ai/text/bootstrap-project",
        json=body or makeBootstrap(),
    )

def waitForDone(client, job_id, timeout_s=5.0):
    """Poll status until done=True. Raises AssertionError on timeout."""
    deadline = time.monotonic() + timeout_s
    last_body = {}
    while time.monotonic() < deadline:
        r = client.get(f"/api/ai/text/bootstrap-project/status/{job_id}")
        if r.status_code == 404:
            raise AssertionError(f"Job {job_id} evicted before done; last body={last_body}")
        last_body = r.get_json()
        if last_body.get("done"):
            return last_body
        time.sleep(0.05)
    raise AssertionError(f"Thread did not finish within {timeout_s}s; last body={last_body}")
```

```python
@pytest.fixture(autouse=True)
def reset_bootstrap_jobs():
    """Wipe in-process job registry between tests to prevent cross-test leak."""
    _routes_mod._BOOTSTRAP_JOBS.clear()
    yield
    _routes_mod._BOOTSTRAP_JOBS.clear()
```

**Pattern — updated existing test assertions** (show before → after for representative cases):

```python
# BEFORE (TestBootstrapValidation):
def test_validRequest_returns200WithFilesEnvelope(self, client):
    r = client.post("/api/ai/text/bootstrap-project", ...)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "files" in body

# AFTER:
def test_validRequest_returns202AndJobId(self, client):
    r = _post_bootstrap(client)
    assert r.status_code == 202
    body = r.get_json()
    assert "job_id" in body
    assert isinstance(body["job_id"], str) and len(body["job_id"]) == 36  # UUID

# BEFORE (TestBootstrapErrorHandling):
def test_providerError_onFirstStep_returns502(self, client, monkeypatch):
    ...monkeypatch.setattr(chain_adapter, "generate", raise_provider_error)
    r = client.post(...)
    assert r.status_code == 502

# AFTER:
def test_providerError_onFirstStep_surfacesErrorInStatus(self, client, monkeypatch):
    from modules.chain import adapter as chain_adapter
    from modules.chain.errors import ProviderError
    def raise_provider_error(system, prompt, **kwargs):
        raise ProviderError("Rate limited", status_code=503)
    monkeypatch.setattr(chain_adapter, "generate", raise_provider_error)
    r = _post_bootstrap(client)
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]
    body = waitForDone(client, job_id)
    assert body["done"] is True
    assert body.get("error") is not None
    assert "Rate limited" in body["error"]
```

**Verify**: `python -m pytest tests/test_ai_bootstrap.py -x -q` — all 11 updated tests pass.

---

## 5. Tests

Complete assertion bodies. Framework: pytest + Flask test client, matching `modules/task_gen/tests/test_routes.py` and `tests/test_ai_bootstrap.py` patterns.

```python
# tests/test_ai_bootstrap.py  (5 new functions appended after existing classes)

import time
import modules.ai.routes as _routes_mod

# ── Helper ──────────────────────────────────────────────────────────────────

def waitForDone(client, job_id, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    last_body = {}
    while time.monotonic() < deadline:
        r = client.get(f"/api/ai/text/bootstrap-project/status/{job_id}")
        if r.status_code == 404:
            raise AssertionError(f"Job {job_id} evicted before done; last={last_body}")
        last_body = r.get_json()
        if last_body.get("done"):
            return last_body
        time.sleep(0.05)
    raise AssertionError(f"Thread did not finish within {timeout_s}s; last={last_body}")


# ── New test functions ───────────────────────────────────────────────────────

@pytest.mark.unit
def test_status_unknownJobId_returns404(client):
    r = client.get("/api/ai/text/bootstrap-project/status/does-not-exist")
    assert r.status_code == 404, r.get_data(as_text=True)
    body = r.get_json()
    assert "error" in body


@pytest.mark.unit
def test_completedJob_returnsAllSixFilenames(client):
    r = client.post(
        "/api/ai/text/bootstrap-project",
        data=json.dumps(makeBootstrap(project_name="Six Files Test")),
        content_type="application/json",
    )
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]
    body = waitForDone(client, job_id)

    assert body["done"] is True
    assert body["running"] is False
    assert "files" in body
    assert "error" not in body

    filenames = {f["filename"] for f in body["files"]}
    assert filenames == {
        "analysis.md",
        "epic.md",
        "architecture.md",
        "spec-index.md",
        "timeline.md",
        "README.md",
    }, f"unexpected filenames: {filenames}"


@pytest.mark.unit
def test_completedJob_hasLatencyMs(client):
    r = client.post(
        "/api/ai/text/bootstrap-project",
        data=json.dumps(makeBootstrap()),
        content_type="application/json",
    )
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]
    body = waitForDone(client, job_id)

    assert "latencyMs" in body, "latencyMs must be present on COMPLETED status"
    assert isinstance(body["latencyMs"], int)
    assert body["latencyMs"] >= 0


@pytest.mark.unit
def test_completedJob_evictsOnFirstTerminalRead(client):
    r = client.post(
        "/api/ai/text/bootstrap-project",
        data=json.dumps(makeBootstrap()),
        content_type="application/json",
    )
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]

    first = waitForDone(client, job_id)
    assert first["done"] is True, "first read must see done=True"

    # Second read must be 404 — eviction on first terminal read
    r2 = client.get(f"/api/ai/text/bootstrap-project/status/{job_id}")
    assert r2.status_code == 404, (
        f"second terminal read must return 404 after eviction; got {r2.status_code}"
    )


@pytest.mark.unit
def test_threadError_surfacedInStatus_notIn202(client, monkeypatch):
    from modules.chain import adapter as chain_adapter

    call_count = {"n": 0}

    def _fail_on_third(system, prompt, **kwargs):
        call_count["n"] += 1
        if call_count["n"] >= 3:
            raise RuntimeError("architecture step exploded")
        from modules.chain.types import ChainResult
        return ChainResult(text="mock output", latency_ms=5)

    monkeypatch.setattr(chain_adapter, "generate", _fail_on_third)

    r = client.post(
        "/api/ai/text/bootstrap-project",
        data=json.dumps(makeBootstrap()),
        content_type="application/json",
    )
    assert r.status_code == 202, "POST must always return 202; errors surface via status"

    job_id = r.get_json()["job_id"]
    body = waitForDone(client, job_id)

    assert body["done"] is True
    assert body["running"] is False
    assert "files" not in body, "files must not appear when thread errored"
    assert "architecture step exploded" in body.get("error", ""), (
        f"error message not found in status body: {body}"
    )
```

---

## 6. Commit Plan

**Executor instruction**: run each commit immediately after completing the corresponding step — not in a batch at the end.

1. `feat(openapi): add bootstrap async contract — 202 POST + status GET path` — after Step 1 — `openapi.yaml`: new GET path, POST 202 response, `BootstrapJobStartResponse` and `BootstrapJobStatus` schemas.

2. `chore(dtos): regenerate models from openapi — add BootstrapJobStartResponse + BootstrapJobStatus` — after Step 2 — `dtos/models.py`: auto-generated; use `git add -f dtos/models.py`.

3. `feat(ai/routes): replace sync bootstrap_project with 202 async handler + status endpoint` — after Step 3 — `modules/ai/routes.py`: `_BOOTSTRAP_JOBS`, `_run_bootstrap_thread`, new `bootstrap_project`, new `bootstrap_status`.

   Commit body must include:
   ```
   Deviations: Uses WorkflowExecution directly (task_gen pattern) rather than
   WorkflowRuntime + BOOTSTRAP_WORKFLOW. WorkflowRuntime's AICall stores ChainResult
   in context.outputs; format_map renders the dataclass repr, not .text, in chained
   multi-step prompts. task_gen is the proven async pattern for this codebase.
   ```

4. `test(ai/bootstrap): update assertions for 202 async shape + add 5 status endpoint tests` — after Step 4, once all 16 tests pass — `tests/test_ai_bootstrap.py`.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api
make test
```

**Expected delta**: 192 → 197 passing (+5 new status endpoint tests). Zero pre-existing tests broken.

Spot-check the specific test file:
```bash
python -m pytest tests/test_ai_bootstrap.py -v 2>&1 | grep -E "PASSED|FAILED|ERROR"
```
All 16 tests (11 updated + 5 new) must show `PASSED`.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - Step 1 revert: `git revert <sha-step1>` — removes openapi changes; run `make generate-dtos` again.
  - Step 2 revert: `git revert <sha-step2>` — restores prior `dtos/models.py`.
  - Step 3 revert: `git revert <sha-step3>` — restores synchronous `bootstrap_project` handler; 200 response resumes.
  - Step 4 revert: `git revert <sha-step4>` — restores old test assertions; revert Step 3 first for consistency.

- **Per-branch**: `git reset --hard <pre-task-sha>` to discard all four commits, or delete the feature branch. Pre-task SHA: capture with `git rev-parse HEAD` before Step 1.

---

## 9. Deviations Allowed

- **`WorkflowRuntime` not used** — the epic task description says "dispatches a daemon thread through `WorkflowRuntime`." This guide deviates by design (see Context §Trade-offs). The executor must document this in the Step 3 commit body under `Deviations:`. Do not silently omit it.
- **Prescribed path doesn't exist** → verify against CODEBASE CONTEXT; if still missing, stop and flag — do not invent.
- **`make generate-dtos` unavailable** → manually add the two new DTO classes to `dtos/models.py` matching the shapes in Step 2's Pattern section. Verify `make check-dtos` passes afterward (if available), or verify manually that field names match openapi.yaml schemas.
- **Test framework mismatch** → match the file's existing `pytest` + class-based style; translate silently but note in commit body.
- **Step 3 unlocks an obvious simplification for Step 4** → take it; log in commit body.
- **Side-effect required** (push, schema migration, publish) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task delivers the minimum backend contract needed for the Angular polling client in Task 4: a 202 POST and a status GET that evicts on first terminal read. It does not touch the Angular layer, the SSE streaming path, or persistent job storage. An eager executor might notice several natural extensions — all are explicitly deferred:

- **Angular polling client** (`startBootstrapProject`, `getBootstrapStatus`, start-then-poll loop in `new-project.component.ts`) — deferred to Task 4; this task ships the contract the client needs, not the client itself.
- **SSE progress streaming for bootstrap** — deferred to the `braindump-streaming-task-gen` epic; the `partial` field arrives there once that epic lands.
- **Persistent job storage** (`WorkflowExecutionStore` adapter) — deferred until multi-user deployment is scoped; in-process dict is the honest implementation for a single-user dev tool.
- **Cancellation surface** — `WorkflowExecution.request_cancel()` exists but runtime does not check between steps; requires a user-facing abort UX before it enters scope.
- **`chain.adapter` promotion to first-class infrastructure** — three consumers is the named trigger; it is a follow-on epic.
- **`max_tokens` default raise for all routes** — covered by `braindump-raise-max-tokens.md`; only the architecture step is bumped to 16384 here.
- **Job TTL / background eviction** — the purge-on-first-read strategy keeps the registry bounded without a TTL process; revisit only if multi-user or long-lived server scenarios emerge.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for the 202 + polling contract
- [Epic](./epic.md) — Task scope and dependencies
- [Timeline](./timeline.md) — Status tracking (update to "Done" after verification passes)