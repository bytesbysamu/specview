# Task 3: Add Truncation Heuristic + Warnings State

**Purpose**: After the chain call returns in `task_gen/service.py`, a lightweight pure function inspects the raw output text for three truncation signals — short length, unbalanced code fences, missing terminal punctuation — and appends a human-readable entry to a `warnings` list stored on the task execution. The `warnings` list is surfaced through the polling endpoint and declared as a first-class field in the OpenAPI contract.

**Effort**: 1 day

**Dependencies**: Task 2 (ceiling raise in `task_gen/service.py`) should be merged first so that the heuristic exercises real output length when running against the live system. Development and testing can proceed on a branch in parallel since the mock provider exercises the path correctly.

**Parallel With**: Task 4 (Angular warning badge) can be developed against the OpenAPI contract defined here without waiting for this task to deploy.

**Blocks**: Task 4 (Angular warning badge) — the badge needs the `warnings` field on the polling response.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task adds a post-call quality gate to `modules/task_gen/service.py`. Today the `run_generation` function calls the chain adapter and writes output unconditionally — if the model truncated its response, the file is silently incomplete and the caller sees no signal. The fix introduces `_looks_truncated`, a pure function that inspects three deterministic text properties (character length below a floor, an odd count of triple-backtick fence markers indicating a mid-block stop, and a last non-empty line that ends without sentence- or structure-terminal punctuation). If any signal fires, a human-readable string is appended to a `warnings` list which is stored in `execution.outputs` before `_finish_with_success` is called. The `snapshot()` function is updated to always include the `warnings` key in its returned dict, even when the list is empty and even when no execution exists yet (idle state). The `GenerateTaskStatusResponse` schema in `openapi.yaml` gains a required `warnings` array; `dtos/models.py` is regenerated to reflect it. No changes touch the chain layer, the file-writing logic, or any module outside `task_gen/service.py`, `openapi.yaml`, and `dtos/models.py`.

**Trade-offs considered**:
- **Blocking write on detected truncation** — rejected because partial output is immediately useful and inspectable; a hard failure forces a manual retry loop on every truncation event, which is the same user experience as today with no diagnostic information added.
- **Boolean `truncated` field instead of a string list** — rejected because a boolean encodes only presence or absence; a list allows independent future heuristics (e.g., a provider-layer context-window-exceeded signal) to append entries without a schema version bump. The overhead of an empty list serializing as `[]` vs. `false` is negligible.
- **Write-then-warn with an always-present `warnings` list** — chosen because it is additive, fully backwards-compatible, and gives any consumer (including the deferred Angular badge) a stable contract to depend on from day one.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
cd {WORKSPACE}/spec-doc/api

git status                                          # flag any unrelated M/?? entries
git diff HEAD -- modules/task_gen/service.py \
               openapi.yaml \
               dtos/models.py                       # confirm all three targets are clean

make test                                           # record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes in a separate commit, before starting this task.

**Baseline recorded**: record the passing test count printed by `make test`. Expected: 192 passing (per CLAUDE.md). Any pre-existing failures must be understood before proceeding.

---

## 3. Files

### To Create (new)
*(none — all work is additive edits to existing files)*

### To Modify (cite CODEBASE CONTEXT)
- `spec-doc/api/modules/task_gen/service.py` — add `_MIN_GUIDE_LENGTH`, `_TERMINAL_CHARS`, `_looks_truncated` pure function; update `run_generation` to compute and store `warnings`; update `snapshot()` to always include the `warnings` key
- `spec-doc/api/openapi.yaml` — add `warnings` to `required` list and `properties` of `GenerateTaskStatusResponse` (lines 940–964)
- `spec-doc/api/dtos/models.py` — **never hand-edited**; regenerated via `make generate-dtos` after the `openapi.yaml` change
- `spec-doc/api/modules/task_gen/tests/test_service_helpers.py` — add `_looks_truncated` unit tests
- `spec-doc/api/modules/task_gen/tests/test_routes.py` — update idle-state exact-equality assertion; add `warnings` integration tests

### To Leave Alone
- `spec-doc/api/modules/chain/adapter.py` — the adapter boundary is unchanged; this task adds no new AI calls and changes no provider behaviour
- `spec-doc/api/modules/chain/providers/` — no provider changes in this task (that is Task 1)
- `spec-doc/api/modules/spec_gen/` — no call-site changes here (Task 2's ceiling raise)
- `spec-doc/api/modules/workflows/execution.py` — `WorkflowExecution.outputs` is a plain `dict`; no schema change needed there; the warnings list is stored under the key `"warnings"` by `run_generation`

---

## 4. Implementation Steps

### Step 1: Add `_looks_truncated` pure function to `service.py`

**Action**: Insert a new `# Truncation heuristic` section after the `# Filename derivation` section (after line 222, before line 224 — the blank line preceding `# Background thread body`). Define two module-level constants and the pure function. Do not modify any other line in the file.

**File**: `spec-doc/api/modules/task_gen/service.py`

**Pattern** (insert between line 222 and line 224):
```python
# ---------------------------------------------------------------------------
# Truncation heuristic
# ---------------------------------------------------------------------------

_MIN_GUIDE_LENGTH = 500  # characters; guides shorter than this are suspicious

_TERMINAL_CHARS = frozenset([
    '.', '!', '?', ':', ',', ';',
    '|', ')', ']', '}', '`', '>',
    '"', "'", '-', '*', '_',
])


def _looks_truncated(text: str) -> bool:
    """Return True if *text* shows heuristic signs of truncation.

    Three signals are checked; any one is sufficient to return True:
    1. Length below _MIN_GUIDE_LENGTH — suspiciously short output.
    2. Unbalanced ``` fences — an odd count means the model stopped mid-block.
    3. Last non-empty line lacks a sentence- or structure-terminal character.

    Designed to prefer false positives over false negatives: a spurious
    warning is dismissible; a silently broken document is not.
    """
    if not text:
        return True

    # Signal 1: too short
    if len(text) < _MIN_GUIDE_LENGTH:
        return True

    # Signal 2: unbalanced code fences
    if text.count("```") % 2 != 0:
        return True

    # Signal 3: last non-empty line lacks terminal punctuation
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if lines and lines[-1] and lines[-1][-1] not in _TERMINAL_CHARS:
        return True

    return False
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api
python -c "from modules.task_gen.service import _looks_truncated; \
           assert _looks_truncated('') is True; \
           assert _looks_truncated('A' * 499) is True; \
           assert _looks_truncated('A' * 500 + '\nDone.') is False; \
           print('Step 1 OK')"
```
Expect: `Step 1 OK`

---

### Step 2: Annotate `run_generation` with truncation warnings

**Action**: In `run_generation` (line 327–338), insert a "Step 9a" block between the chain call (`result = chain_adapter.generate(...)`, line 328) and the file-write step. Store the warnings list on `execution.outputs` in Step 11 alongside the existing filename/taskNum/taskName outputs.

**File**: `spec-doc/api/modules/task_gen/service.py`

**Pattern** — replace lines 327–338 verbatim with:
```python
        # Step 9: call chain adapter (the only AI call)
        result = chain_adapter.generate(system, user)

        # Step 9a: heuristic truncation check (write-then-warn)
        warnings: list[str] = []
        if _looks_truncated(result.text):
            warnings.append(
                "Output may be truncated — verify the file is complete before using."
            )

        # Step 10: write output file (always, regardless of truncation)
        filename = derive_task_filename(task["num"], task["name"])
        update_file(projects_dir, project_id, filename, result.text)

        # Step 11: mark done
        execution.outputs["filename"] = filename
        execution.outputs["taskNum"] = task["num"]
        execution.outputs["taskName"] = task["name"]
        execution.outputs["warnings"] = warnings
        _finish_with_success(execution)
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api
python -c "
import ast, sys
src = open('modules/task_gen/service.py').read()
tree = ast.parse(src)
print('Step 2 parses OK')
"
python -m pytest modules/task_gen/tests/test_routes.py -v -k 'afterCompletion' --tb=short
```
Expect: the `status_afterCompletion_includesFilenameAndTaskMeta` test still passes.

---

### Step 3: Update `snapshot()` to always include `warnings`

**Action**: In `snapshot()` (lines 74–101), make two changes: (a) add `"warnings": []` to the idle-state return dict, and (b) add `out["warnings"] = exc.outputs.get("warnings", [])` immediately before the final `return out`.

**File**: `spec-doc/api/modules/task_gen/service.py`

**Pattern** — change (a), line 85:
```python
    # Before:
    if not slots:
        return {"running": False, "done": False}

    # After:
    if not slots:
        return {"running": False, "done": False, "warnings": []}
```

**Pattern** — change (b), lines 99–101:
```python
    # Before:
    if exc.error is not None:
        out["error"] = exc.error
    return out

    # After:
    if exc.error is not None:
        out["error"] = exc.error
    out["warnings"] = exc.outputs.get("warnings", [])
    return out
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api
python -c "
from modules.task_gen import service as svc
svc._EXECUTIONS.clear()
snap = svc.snapshot('no-such-project')
assert snap == {'running': False, 'done': False, 'warnings': []}, snap
print('Step 3 idle-state OK')
"
```
Expect: `Step 3 idle-state OK`

---

### Step 4: Add `warnings` to `GenerateTaskStatusResponse` in `openapi.yaml`

**Action**: In `openapi.yaml`, locate the `GenerateTaskStatusResponse` schema (lines 940–964). Add `warnings` to the `required` array and insert the property definition between `done` and `allDone`.

**File**: `spec-doc/api/openapi.yaml`

**Pattern** — change the `required` line (line 942):
```yaml
    # Before:
      required: [running, done]

    # After:
      required: [running, done, warnings]
```

**Pattern** — insert after the `done` property block (after line 949, before the `allDone` property):
```yaml
        warnings:
          type: array
          items:
            type: string
          description: >-
            Heuristic truncation signals detected after generation. Empty list
            when no signals are present; one or more strings when the output
            shows signs of truncation. Always present in the response.
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api
python -c "
import yaml
with open('openapi.yaml') as f:
    spec = yaml.safe_load(f)
schema = spec['components']['schemas']['GenerateTaskStatusResponse']
assert 'warnings' in schema['required'], 'warnings not in required'
assert 'warnings' in schema['properties'], 'warnings not in properties'
assert schema['properties']['warnings']['type'] == 'array', 'wrong type'
print('Step 4 OK')
"
```
Expect: `Step 4 OK`

---

### Step 5: Regenerate `dtos/models.py`

**Action**: Run `make generate-dtos` to regenerate `dtos/models.py` from the updated `openapi.yaml`. Then verify the new field appears in the generated file. Stage with `git add -f` per project conventions.

**File**: `spec-doc/api/dtos/models.py` (generated — never hand-edited)

**Pattern**:
```bash
cd {WORKSPACE}/spec-doc/api
make generate-dtos
```

After generation, `GenerateTaskStatusResponse` in `dtos/models.py` must contain a `warnings` field. Exact shape depends on the codegen tool version; either of these is acceptable:
```python
# Required field variant (expected when warnings is in `required`):
warnings: List[str] = Field(..., description='Heuristic truncation signals ...')

# Default-factory variant (also acceptable):
warnings: List[str] = Field(default_factory=list, description='...')
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api
python -c "
from dtos.models import GenerateTaskStatusResponse
import inspect
sig = inspect.signature(GenerateTaskStatusResponse)
assert 'warnings' in sig.parameters, 'warnings field missing from DTO'
print('Step 5 DTO OK')
"
make check-dtos   # must exit 0 — fails if models.py is out of sync with openapi.yaml
```
Expect: `Step 5 DTO OK` and `make check-dtos` exits `0`.

**Note**: Per CLAUDE.md — `dtos/models.py` is committed; use `git add -f dtos/models.py`.

---

## 5. Tests

Match the existing framework: pytest, direct `assert` statements, function names in `subject_condition_outcome` camelCase, picked up by `python_functions = ["test_*", "*_*"]` in `pyproject.toml`. No `test_` prefix needed.

### Unit tests — add to `spec-doc/api/modules/task_gen/tests/test_service_helpers.py`

Append after line 141 (end of file):

```python
looksTruncated = _svc._looks_truncated


# ---------------------------------------------------------------------------
# _looks_truncated — heuristic truncation detection
# ---------------------------------------------------------------------------

def looksTruncated_emptyString_returnsTrue():
    assert looksTruncated("") is True


def looksTruncated_belowMinLength_returnsTrue():
    # 499 chars — one below the 500-char floor
    assert looksTruncated("x" * 499) is True


def looksTruncated_exactlyMinLength_lengthSignalClear():
    # 500 chars, no fences, last char is period — all three signals clear
    body = "A" * 498 + "x."
    assert looksTruncated(body) is False


def looksTruncated_oddFenceCount_returnsTrue():
    # Long enough, terminal punct present, but fence count is 1 (odd)
    body = "A" * 500 + "\n```python\ncode here\n" + "end."
    assert looksTruncated(body) is True


def looksTruncated_evenFenceCount_fenceSignalClear():
    # Two balanced fences — fence signal does not fire
    body = "A" * 500 + "\n```python\ncode\n```\nfinal sentence."
    assert looksTruncated(body) is False


def looksTruncated_lastLineNoTerminalPunct_returnsTrue():
    # Last non-empty line ends with a plain word — terminal signal fires
    body = "A" * 500 + "\nThis line ends with a word"
    assert looksTruncated(body) is True


def looksTruncated_lastLineWithPeriod_returnsFalse():
    body = "A" * 500 + "\nThis document is complete."
    assert looksTruncated(body) is False


def looksTruncated_lastLineWithPipe_returnsFalse():
    # Table rows end with `|` — structure-terminal
    body = "A" * 500 + "\n| value | other |"
    assert looksTruncated(body) is False


def looksTruncated_lastLineWithClosingParen_returnsFalse():
    # Markdown link ending with `)` — structure-terminal
    body = "A" * 500 + "\n[Timeline](./timeline.md) — Status tracking (update after done)"
    assert looksTruncated(body) is False


def looksTruncated_trailingBlankLines_inspectsPriorNonEmptyLine():
    # Trailing blank lines are ignored; the non-empty line above ends with `.`
    body = "A" * 499 + ".\n\n\n"
    assert looksTruncated(body) is False


def looksTruncated_zeroByteFenceCount_signalClear():
    # No fences at all — count is 0 (even); should not trigger fence signal
    body = "A" * 500 + "\nDone."
    assert looksTruncated(body) is False
```

### Integration tests — `spec-doc/api/modules/task_gen/tests/test_routes.py`

#### Update the existing idle-state test (line 143)

```python
# Replace:
#   assert body == {"running": False, "done": False}
# With:
def status_noJobEverStarted_returnsRunningFalseDoneFalse(client, project_id):
    r = client.get(f"/api/projects/{project_id}/generate-task/status")
    assert r.status_code == 200
    body = r.get_json()
    assert body == {"running": False, "done": False, "warnings": []}
```

#### New tests — append to `test_routes.py`

```python
def status_afterCompletion_warningsKeyAlwaysPresent(client, project_id, seeded_project):
    """warnings is always present in the terminal status response as a list."""
    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202
    body = waitForDone(client, project_id)
    assert body["done"] is True
    assert "warnings" in body, "warnings key must always be present in terminal response"
    assert isinstance(body["warnings"], list)


def status_mockOutputShort_triggersLengthHeuristic(client, project_id, seeded_project):
    """Mock provider output is shorter than _MIN_GUIDE_LENGTH; length heuristic fires."""
    # The mock provider produces a short MOCK[...] string — well below 500 chars.
    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202
    body = waitForDone(client, project_id)
    assert body["done"] is True
    assert body["warnings"], "expected non-empty warnings for short mock output"
    assert any("truncat" in w.lower() for w in body["warnings"])


def status_longWellFormedOutput_warningsEmpty(client, project_id, seeded_project, monkeypatch):
    """Long, well-formed output with balanced fences and terminal punctuation produces no warnings."""
    from modules.chain import adapter as chain_adapter
    from modules.chain.types import ChainResult

    long_complete = (
        "# Implementation Guide\n\n"
        + "This is a complete and thorough section.\n\n" * 20
        + "## Out of Scope\n\n"
        + "Nothing is out of scope here.\n"
    )

    def _long_output(system, prompt, **kwargs):
        return ChainResult(text=long_complete, latency_ms=10)

    monkeypatch.setattr(chain_adapter, "generate", _long_output)

    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202
    body = waitForDone(client, project_id)
    assert body["done"] is True
    assert body["warnings"] == [], f"expected empty warnings, got: {body['warnings']}"


def status_unbalancedFences_triggersHeuristic(client, project_id, seeded_project, monkeypatch):
    """Output with an odd number of ``` fences triggers the fence-balance heuristic."""
    from modules.chain import adapter as chain_adapter
    from modules.chain.types import ChainResult

    odd_fences = (
        "# Guide\n\n"
        + "Detailed content here.\n\n" * 15
        + "```python\ncode_start()\n"
        # deliberately no closing fence
    )

    def _odd_fence_output(system, prompt, **kwargs):
        return ChainResult(text=odd_fences, latency_ms=10)

    monkeypatch.setattr(chain_adapter, "generate", _odd_fence_output)

    r = client.post(f"/api/projects/{project_id}/generate-task")
    assert r.status_code == 202
    body = waitForDone(client, project_id)
    assert body["done"] is True
    assert body["warnings"], "expected warning for unbalanced fences"
    assert any("truncat" in w.lower() for w in body["warnings"])
```

---

## 6. Commit Plan

**Executor instruction**: run each commit command immediately after completing the corresponding step — not at the end of the task. If a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

1. `feat(task_gen): add _looks_truncated pure heuristic` — **after Step 1** — `modules/task_gen/service.py`: new `_MIN_GUIDE_LENGTH`, `_TERMINAL_CHARS`, `_looks_truncated`

   ```bash
   git add spec-doc/api/modules/task_gen/service.py
   git commit -m "$(cat <<'EOF'
   feat(task_gen): add _looks_truncated pure heuristic

   Adds three-signal truncation detector: length floor, unbalanced code
   fences, missing terminal punctuation on the last non-empty line.
   Pure function with no I/O or side effects.

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

2. `feat(task_gen): annotate execution with truncation warnings` — **after Step 2 + Step 3** — `modules/task_gen/service.py`: `run_generation` warnings block, `snapshot()` idle-state and terminal-state changes

   ```bash
   git add spec-doc/api/modules/task_gen/service.py
   git commit -m "$(cat <<'EOF'
   feat(task_gen): annotate execution with truncation warnings

   run_generation: calls _looks_truncated after chain call; stores
   warnings list in execution.outputs before marking done. File is
   written regardless (write-then-warn).
   snapshot(): always includes warnings key — empty list for idle
   state and for executions that produced no truncation signal.

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

3. `feat(openapi): add warnings field to GenerateTaskStatusResponse` — **after Step 4** — `openapi.yaml`

   ```bash
   git add spec-doc/api/openapi.yaml
   git commit -m "$(cat <<'EOF'
   feat(openapi): add warnings field to GenerateTaskStatusResponse

   Declares warnings as a required array<string> on the task-status
   response. Always present; empty list when no truncation signals
   detected. Backwards-compatible addition — no existing field removed.

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

4. `chore(dtos): regenerate models.py with warnings field` — **after Step 5** — `dtos/models.py`

   ```bash
   git add -f spec-doc/api/dtos/models.py
   git commit -m "$(cat <<'EOF'
   chore(dtos): regenerate models.py with warnings field

   Auto-generated by make generate-dtos after openapi.yaml change.
   GenerateTaskStatusResponse now includes warnings: List[str].

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

5. `test(task_gen): add heuristic unit tests and warnings integration tests` — **after all tests pass** — test files

   ```bash
   git add spec-doc/api/modules/task_gen/tests/test_service_helpers.py \
           spec-doc/api/modules/task_gen/tests/test_routes.py
   git commit -m "$(cat <<'EOF'
   test(task_gen): add heuristic unit tests and warnings integration tests

   Unit: 11 tests for _looks_truncated (empty, length floor, fence
   balance, terminal punctuation, trailing blank lines).
   Integration: idle-state exact-equality updated for warnings key;
   4 new route tests covering always-present contract, mock short
   output, long well-formed output, and unbalanced fences.

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api
make test
```

**Expected delta**: baseline → baseline + 15 passing (11 unit tests for `_looks_truncated` + 4 new integration tests). Zero pre-existing tests broken. The one updated test (`status_noJobEverStarted_returnsRunningFalseDoneFalse`) still passes under its new assertion.

**Spot-check the specific suites**:
```bash
# Unit tests for heuristic
python -m pytest modules/task_gen/tests/test_service_helpers.py -v -k 'looksTruncated' --tb=short

# Integration tests including new warnings tests
python -m pytest modules/task_gen/tests/test_routes.py -v --tb=short

# DTO sync gate
make check-dtos
```

---

## 8. Rollback

- **Per-step**: every commit in the Commit Plan is independently revertible. `git revert <sha>` for the relevant commit, then re-run `make test` to confirm the baseline is restored.
- **Per-branch**: if verification fails catastrophically (e.g., the DTO regeneration produces an incompatible shape that breaks `make check-dtos`), reset the feature branch: `git reset --hard <pre-task-sha>`. Do **not** force-push to `master`; open a follow-up PR with the diagnosis instead.
- **DTO-specific**: if `make generate-dtos` produces an unexpected shape, revert the `openapi.yaml` commit first (`git revert <step-4-sha>`), revert the DTO commit, run `make check-dtos` to confirm the baseline is restored, then diagnose the codegen tool version before re-attempting.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify against the file listing in this guide; if a path is genuinely absent, stop and flag rather than invent an alternative location.
- **Test framework mismatch** → the repo uses pytest with camelCase function names (no `test_` prefix, picked up by `python_functions = ["*_*"]`). If the discovered convention differs, match what is already in the file and note the deviation in the commit body.
- **`make generate-dtos` produces `Optional[List[str]]` instead of `List[str]`** for the `warnings` field (if the codegen tool does not treat the array as a bare required field): this is acceptable. The `snapshot()` function always returns a list, so the `Optional` wrapper is never `None` in practice. Do not attempt to hand-edit `dtos/models.py` to remove the `Optional`; the contract is enforced by the implementation, not the DTO annotation.
- **Side-effect required** (push, schema migration, publish) → **STOP**, mark `[REQUIRES APPROVAL]`, and ask before proceeding.
- **Step N unlocks a simplification for Step N+1** → take it, log in the commit body.

---

## 10. Out of Scope

This task adds the truncation heuristic, stores warnings on the task state, and declares the `warnings` field in the OpenAPI contract. It does not touch the chain layer, the CLI provider, the call-site ceilings, or any Angular component. The following items were considered and explicitly deferred:

- **Angular warning badge** — the frontend consumer of the `warnings` field. The API contract this task ships is the stable surface the badge depends on; the badge rendering is a separate deliverable scoped to a later task in the epic.
- **Auto-retry on truncation** — the write-then-warn decision is architecturally closed for this epic. Auto-retry carries restart-loop risk that requires a dedicated design session before entering scope.
- **Timeout increases** — no inventory of specific timeout values or their code locations exists; scoping that work without an inventory produces changes in the wrong places. Deferred until an inventory is available.
- **Provider-layer truncation signal** — the CLI binary does not expose a machine-readable flag; all three heuristic signals are text-based. If the binary gains a structured output field in a future version, a provider-layer signal could replace or supplement the heuristic. That is a separate task against the chain layer.
- **Raising `max_tokens` at the call site in `task_gen/service.py`** — this is Task 2's responsibility. This task does not change the `chain_adapter.generate(system, user)` call signature; that change ships in Task 2 and should be visible on the branch this task is cut from.
- **Warning message internationalisation or categorisation** — the single string `"Output may be truncated — verify the file is complete before using."` is sufficient for the current consumer (a developer-facing badge). Structured warning codes (e.g., `TRUNCATED_LENGTH`, `TRUNCATED_FENCE`) are a follow-up if multiple consumers need to branch on warning type.

**Rule for the executor**: if a change appears helpful but is listed here, stop and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale and component design for the heuristic
- [Epic](./epic.md) – Full task scope and sequencing
- [Timeline](./timeline.md) – Status tracking (update to ✅ after `make test` confirms the delta)