# Task 2: Raise Call-Site Ceilings to 16 384

**Purpose**: Raise the `max_tokens` ceiling from 4 096 to 16 384 at the two call sites — the `architecture` step in the bootstrap workflow and the implementation-guide `chain_adapter.generate` call in `task_gen/service.py` — whose output regularly exceeds the current default, enabling longer documents once the CLI provider fix (Task 1) is live.

**Effort**: 0.5 days

**Dependencies**: Task 1 (CLI provider `--max-tokens` flag forwarding) must be **deployed** before this change has any practical effect. The code change itself can be authored and merged beforehand; the ceiling will simply be a silent no-op until the provider honours it.

**Parallel With**: —

**Blocks**: Task 3 (truncation heuristic — the heuristic only fires on long output, which requires this ceiling to be live)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The `AICall` step model and the `chain/adapter.py` surface already accept and forward `max_tokens` end-to-end — from `AICall.max_tokens` through `adapter.generate(max_tokens=...)` to the provider. The gap is that two call sites never deviate from the 4 096 default: the `architecture` AICall in `modules/spec_gen/workflows/generate_spec.py` (which produces the system's longest workflow document) and the direct `chain_adapter.generate(system, user)` call in `modules/task_gen/service.py` at line 328 (which generates implementation guides, the source of the observed truncation). This task sets `max_tokens=16_384` at precisely those two sites — nothing else changes.

**Trade-offs considered**:
- **Global ceiling raise (change the default in `adapter.py` or `AICall`)** — rejected because it silently inflates token consumption for every call in the system, including analysis and epic prompts that comfortably fit in 4 096 tokens; cost and latency increase with no quality benefit for those paths.
- **Runtime configuration via environment variable** — rejected because the two target sites are structurally distinct (long-form documents by design) and do not need operator-level tuning; a hardcoded constant is simpler, auditable, and avoids an undocumented runtime knob.
- **Explicit per-site constants at the two call sites** — preferred because it is surgical (no unintended scope creep), immediately auditable (grep for `16_384` finds every raised ceiling in the repo), and consistent with the principle that only demonstrably long-output sites receive the raise.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1 — confirm working tree is clean on target files
git status
git diff HEAD -- \
  spec-doc/api/modules/spec_gen/workflows/generate_spec.py \
  spec-doc/api/modules/task_gen/service.py

# 2 — verify AICall plumbing: max_tokens field declared AND forwarded to adapter
grep -n "max_tokens" spec-doc/api/modules/workflows/steps/ai_call.py
# Expected: field declaration (~line 57) AND usage in chain_adapter.generate call (~line 70)

# 3 — verify adapter plumbing: max_tokens threaded through generate()
grep -n "max_tokens" spec-doc/api/modules/chain/adapter.py
# Expected: parameter in generate() signature AND forwarded to provider.create_message()

# 4 — baseline test suite
cd spec-doc/api && make test
# Record passing count before any edits
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Plumbing prerequisite**: If step 2 or 3 above does NOT show `max_tokens` flowing all the way to `provider.create_message(...)`, the plumbing must be added before the ceiling values matter — stop and resolve that gap first (it belongs to Task 1 scope). Based on the current codebase, the plumbing is already complete: `AICall.max_tokens` (line 57, `ai_call.py`) passes through `chain_adapter.generate(max_tokens=self.max_tokens)` (line 70, `ai_call.py`) and through `adapter.generate(max_tokens=max_tokens)` (adapter line ~30) to `provider.create_message(max_tokens=max_tokens)`.

**Baseline recorded**: 192 / 192 passing (per CLAUDE.md).

---

## 3. Files

### To Create (new)
- `spec-doc/api/modules/spec_gen/tests/test_workflow_steps.py` — unit tests asserting per-step `max_tokens` values on the `generate-spec` workflow; depends on `_build_workflow()` from `generate_spec.py` and `AICall` from `modules/workflows/steps/ai_call.py`
- `spec-doc/api/modules/task_gen/tests/test_service_ceiling.py` — unit test asserting that `run_generation` calls `chain_adapter.generate` with `max_tokens=16_384`; depends on `run_generation` from `service.py` and monkeypatching all I/O

### To Modify (cite CODEBASE CONTEXT)
- `spec-doc/api/modules/spec_gen/workflows/generate_spec.py` — current: `architecture` AICall has no explicit `max_tokens` (inherits default 4 096); target: `max_tokens=16_384` added to that AICall only
- `spec-doc/api/modules/task_gen/service.py` — current: `chain_adapter.generate(system, user)` at line 328 passes no `max_tokens` (inherits adapter default 4 096); target: `chain_adapter.generate(system, user, max_tokens=16_384)`

### To Leave Alone
- `spec-doc/api/modules/chain/adapter.py` — the adapter already threads `max_tokens` correctly; no change required
- `spec-doc/api/modules/chain/providers/cli.py` — provider-layer fix is Task 1 scope; do not touch
- `spec-doc/api/modules/workflows/steps/ai_call.py` — the `AICall` model already has the `max_tokens` field and forwards it; no change required
- `spec-doc/api/openapi.yaml` — `warnings` schema addition is Task 4 scope; do not touch
- `spec-doc/api/dtos/models.py` — generated from `openapi.yaml`; untouched here

---

## 4. Implementation Steps

### Step 1: Raise the `architecture` AICall ceiling in `generate_spec.py`

**Action**: Add `max_tokens=16_384` to the `architecture` AICall constructor in `_build_workflow()`. The `analysis` and `epic` AICall instances must remain unchanged at their default 4 096 ceiling.

**File**: `spec-doc/api/modules/spec_gen/workflows/generate_spec.py` (existing — see `_build_workflow` function, `architecture` step, currently lines ~53–67)

**Pattern**:
```python
        .step(
            # See note above: "epic" comes from context.outputs, not inputs.
            AICall(
                name="architecture",
                system=ARCHITECTURE_SYSTEM,
                prompt_template=ARCHITECTURE_USER,
                input_keys=(
                    "braindump",
                    "project_name",
                    "builder",
                    "principles",
                    "codebase",
                    "references",
                ),
                max_tokens=16_384,          # raised: architecture output exceeds 4096
            )
        )
```

**Verify**:
```bash
grep -n "max_tokens" spec-doc/api/modules/spec_gen/workflows/generate_spec.py
# Expected: exactly one match, on the architecture AICall, value 16_384
# analysis and epic AICall blocks must NOT appear in this output
```

---

### Step 2: Raise the `chain_adapter.generate` ceiling in `task_gen/service.py`

**Action**: Append `max_tokens=16_384` to the `chain_adapter.generate(system, user)` call at line 328 in `run_generation`. No other lines in this file change.

**File**: `spec-doc/api/modules/task_gen/service.py` (existing — Step 9 comment block, line 327–328)

**Pattern**:
```python
        # Step 9: call chain adapter (the only AI call)
        result = chain_adapter.generate(system, user, max_tokens=16_384)
```

**Verify**:
```bash
grep -n "max_tokens" spec-doc/api/modules/task_gen/service.py
# Expected: exactly one match at the generate() call, value 16_384
```

---

### Step 3: Write tests for the architecture step ceiling

**Action**: Create `test_workflow_steps.py` in `modules/spec_gen/tests/`. Tests call `_build_workflow()` directly and assert per-step `max_tokens` values. Three tests: architecture raised, analysis unchanged, epic unchanged.

**File**: `spec-doc/api/modules/spec_gen/tests/test_workflow_steps.py` (new)

**Pattern**: see §5 Tests below.

**Verify**:
```bash
cd spec-doc/api && python -m pytest modules/spec_gen/tests/test_workflow_steps.py -v
# Expected: 3 passed
```

---

### Step 4: Write test for the impl-guide call-site ceiling

**Action**: Create `test_service_ceiling.py` in `modules/task_gen/tests/`. Monkeypatches all I/O in `run_generation` and captures the `max_tokens` argument forwarded to `chain_adapter.generate`.

**File**: `spec-doc/api/modules/task_gen/tests/test_service_ceiling.py` (new)

**Pattern**: see §5 Tests below.

**Verify**:
```bash
cd spec-doc/api && python -m pytest modules/task_gen/tests/test_service_ceiling.py -v
# Expected: 1 passed
```

---

## 5. Tests

Framework: **pytest**, camelCase+underscore naming convention (matches `test_service_helpers.py` and `test_ai_call.py`; collected via `python_functions = ["test_*", "*_*"]` in `pyproject.toml`).

### `spec-doc/api/modules/spec_gen/tests/test_workflow_steps.py` (new)

```python
# modules/spec_gen/tests/test_workflow_steps.py
"""Unit tests — per-step max_tokens values in the generate-spec workflow.

Only the 'architecture' step is raised to 16 384.
'analysis' and 'epic' must keep the AICall default of 4 096.
"""
from __future__ import annotations

from modules.spec_gen.workflows.generate_spec import _build_workflow
from modules.workflows.steps.ai_call import AICall

_RAISED_CEILING = 16_384
_DEFAULT_CEILING = 4096


def _get_step(name: str) -> AICall:
    """Retrieve the named AICall from the workflow; fail fast if absent."""
    wf = _build_workflow()
    matches = [s for s in wf.steps if isinstance(s, AICall) and s.name == name]
    assert len(matches) == 1, (
        f"Expected exactly one AICall named {name!r} in generate-spec workflow; "
        f"found {len(matches)}"
    )
    return matches[0]


def architectureStep_maxTokens_is16384():
    """architecture AICall must declare max_tokens=16384."""
    step = _get_step("architecture")
    assert step.max_tokens == _RAISED_CEILING, (
        f"architecture step must have max_tokens={_RAISED_CEILING}; "
        f"got {step.max_tokens}"
    )


def analysisStep_maxTokens_isDefault4096():
    """analysis step must retain the default 4096 ceiling — only architecture is raised."""
    step = _get_step("analysis")
    assert step.max_tokens == _DEFAULT_CEILING, (
        f"analysis step must keep default ceiling {_DEFAULT_CEILING}; "
        f"got {step.max_tokens}"
    )


def epicStep_maxTokens_isDefault4096():
    """epic step must retain the default 4096 ceiling — only architecture is raised."""
    step = _get_step("epic")
    assert step.max_tokens == _DEFAULT_CEILING, (
        f"epic step must keep default ceiling {_DEFAULT_CEILING}; "
        f"got {step.max_tokens}"
    )
```

---

### `spec-doc/api/modules/task_gen/tests/test_service_ceiling.py` (new)

```python
# modules/task_gen/tests/test_service_ceiling.py
"""Unit test — run_generation must forward max_tokens=16_384 to chain_adapter.generate.

All I/O dependencies are monkeypatched so no real filesystem, network,
or AI call occurs. The captured kwargs on chain_adapter.generate are the
sole assertion target.
"""
from __future__ import annotations

import pytest

from modules.chain import adapter as chain_adapter
from modules.chain.types import ChainResult
from modules.task_gen import service as _svc

_EXPECTED_CEILING = 16_384

_FAKE_TASKS = [{"num": "1", "name": "Dummy Task", "effort": "0.5 days"}]

_FAKE_PROJECT = {
    "specs": [
        {
            "filename": "epic.md",
            "content": (
                "# Epic: Ceiling Test\n\n"
                "### Task 1: Dummy Task\n"
                "A placeholder task for ceiling verification.\n"
            ),
        },
        {"filename": "architecture.md", "content": "# Architecture\n"},
    ]
}


@pytest.fixture(autouse=True)
def reset_executions():
    """Prevent state from bleeding across tests."""
    _svc._EXECUTIONS.clear()
    yield
    _svc._EXECUTIONS.clear()


def runGeneration_forwardsMaxTokens_16384(tmp_path, monkeypatch):
    """run_generation must call chain_adapter.generate with max_tokens=16_384."""
    project_id = "ceiling-test-proj"

    # Patch all I/O so the test runs without filesystem, network, or AI calls
    monkeypatch.setattr("modules.task_gen.service.get_project", lambda *_: _FAKE_PROJECT)
    monkeypatch.setattr(
        "modules.task_gen.service.bootstrap_extract_tasks",
        lambda _: _FAKE_TASKS,
    )
    monkeypatch.setattr("modules.task_gen.service.read_context", lambda _key: "")
    monkeypatch.setattr(
        "modules.task_gen.service.build_implementation_guide_prompt",
        lambda **_: ("SYSTEM_PROMPT", "USER_PROMPT"),
    )
    monkeypatch.setattr("modules.task_gen.service.update_file", lambda *_: None)

    captured: list[dict] = []

    def fake_generate(system, prompt, *, max_tokens, **_):
        captured.append({"system": system, "prompt": prompt, "max_tokens": max_tokens})
        return ChainResult(text="generated content", latency_ms=1)

    monkeypatch.setattr(chain_adapter, "generate", fake_generate)

    # Run synchronously (execution=None creates a transient WorkflowExecution internally)
    _svc.run_generation(project_id, tmp_path, task_num="1", execution=None)

    assert len(captured) == 1, (
        f"chain_adapter.generate must be called exactly once; called {len(captured)} time(s)"
    )
    assert captured[0]["max_tokens"] == _EXPECTED_CEILING, (
        f"run_generation must pass max_tokens={_EXPECTED_CEILING} to chain_adapter.generate; "
        f"got {captured[0]['max_tokens']!r}"
    )
```

---

## 6. Commit Plan

**Executor instruction**: run `git commit` after EACH step below completes — not once at the end of the task.

1. **`feat(spec-gen): raise architecture step max_tokens to 16384`** — after Step 1 — `modules/spec_gen/workflows/generate_spec.py`: adds `max_tokens=16_384` to the architecture AICall only

2. **`feat(task-gen): raise impl-guide generate call max_tokens to 16384`** — after Step 2 — `modules/task_gen/service.py`: appends `max_tokens=16_384` to the `chain_adapter.generate` call at step 9

3. **`test(spec-gen): assert architecture step ceiling is 16384, analysis and epic unchanged`** — after Step 3 passes — `modules/spec_gen/tests/test_workflow_steps.py`: new file, 3 tests

4. **`test(task-gen): assert run_generation forwards max_tokens=16384 to chain adapter`** — after Step 4 passes — `modules/task_gen/tests/test_service_ceiling.py`: new file, 1 test

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd spec-doc/api && make test
```

**Expected delta**: 192 → 196 passing (4 new tests: 3 in `test_workflow_steps.py`, 1 in `test_service_ceiling.py`). Zero pre-existing tests broken.

**Spot-check audit** (run after `make test` passes):

```bash
# Confirm exactly one raised ceiling per target file
grep -rn "16_384\|16384" spec-doc/api/modules/
# Expected: two matches — generate_spec.py (architecture AICall) + service.py (generate call)
# If more than two appear, a call site was accidentally changed

# Confirm analysis and epic steps are untouched
grep -A2 'name="analysis"' spec-doc/api/modules/spec_gen/workflows/generate_spec.py
grep -A2 'name="epic"' spec-doc/api/modules/spec_gen/workflows/generate_spec.py
# Neither block should contain max_tokens
```

---

## 8. Rollback

- **Per-step**: every step has its own commit. Any step is independently revertible with `git revert <sha>`. Revert in reverse order if multiple steps must be unwound (revert 4 → 3 → 2 → 1).
- **Per-branch**: if verification fails and multiple reverts are impractical, `git reset --hard <pre-task-sha>` on the feature branch, or delete and re-cut the branch. The only files affected are the four listed in §3 (two modified, two new); no schema changes, no generated files.

---

## 9. Deviations Allowed

- **`_build_workflow` is not importable** → If `_build_workflow` is refactored to a non-importable position between the architecture doc and execution, access the step list via the registered workflow from the app's `workflow_repository` instead. Adjust the test fixture accordingly and log as a deviation.
- **`workflow.steps` attribute name differs** → Inspect `modules/workflows/workflow.py` for the actual field name (it is `steps: tuple[Any, ...]` in the current codebase); adapt the test helper `_get_step` silently and note in commit body.
- **Test framework mismatch** → If `pyproject.toml` `python_functions` changes, rename test functions with `test_` prefix; translate silently but note in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Step N simplifies Step N+1** → take it, log deviation in that step's commit body.

---

## 10. Out of Scope

This task changes exactly two values in two files and verifies them with four tests. It does not grow into any surrounding infrastructure, regardless of how tempting adjacent improvements may appear.

- **CLI provider `--max-tokens` flag forwarding** (`modules/chain/providers/cli.py`) — Task 1 scope. Do not touch. The ceiling raise in this task is a silent no-op until the provider fix is deployed; that is the intended sequential dependency.
- **Truncation heuristic and `_looks_truncated` function** — Task 3 scope. Even if truncation is observed during manual verification, do not add any detection logic here.
- **`warnings` field in `openapi.yaml` and `dtos/models.py`** — Task 4 scope. The schema change is a separate deliverable that depends on the heuristic (Task 3) existing first.
- **`analysis` and `epic` ceiling raises** — explicitly out of scope. Both prompts fit comfortably within 4 096 tokens today. Raising them would increase cost with no quality benefit.
- **`task_gen/service.py` `run_generation` refactoring** — the function has eleven sequential steps and is already well-structured. Do not restructure it as part of this task.
- **Timeout configuration** — the architecture explicitly excludes timeout work until a concrete inventory exists; do not add or adjust any timeout values here.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)