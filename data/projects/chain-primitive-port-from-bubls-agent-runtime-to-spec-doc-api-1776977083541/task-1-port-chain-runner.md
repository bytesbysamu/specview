# Task 1: Port Chain Runner — Implementation Guide

## 1. Context

This task ports the sequential chain execution primitive into `flask/modules/chain/runner.py`, adding three types (`ChainStep`, `ChainDefinition`, `ChainEvent`) and the `run_chain()` generator. The runner sits between feature routes and the adapter: routes call `run_chain()`, the runner calls `chain_adapter.generate()`, and the adapter dispatches to providers. No consumer route lands in this task — the primitive ships first, unit-tested against the mock provider, so Tasks 3–4 have a tested foundation to wire into. The structural test (`pipelinedFeatures_useRunChain`) ships alongside the primitive because Task 1 is when the violation class (repeated adapter calls per handler) first becomes possible.

**Trade-offs considered:**
- **`ChainEvent` as frozen dataclass** — rejected because `model_dump_json()` is needed for SSE serialization in the route handler (Task 4); plain `dataclass` would require a manual serializer.
- **`run_chain()` accepting `stream=True` and yielding text deltas** — deferred; streaming SSE is Task 4's scope. This task's generator always uses `adapter.generate()` (batch) and yields `ChainEvent` objects only. Streaming adds complexity that has no consumer until the route lands.
- **Pydantic `BaseModel` for `ChainEvent` only; frozen dataclasses for `ChainStep`/`ChainDefinition`** — preferred because it aligns `ChainEvent` with the existing DTO layer while keeping the structural types immutable and cheap to construct.

---

## 2. Pre-flight

```bash
git status
# Flag any M entries on flask/modules/chain/ — stash or commit unrelated changes first.

git diff HEAD -- flask/modules/chain/runner.py flask/modules/chain/tests/test_runner.py flask/modules/chain/tests/test_structural.py
# All three paths should 404 (runner.py, test_runner.py do not exist yet).

python -m pytest flask/ -v --tb=short -q
# Record the passing count — this is your baseline.
```

**Baseline recorded**: ___ passing (fill in before editing).

---

## 3. Files

### To Create (new)
- `flask/modules/chain/runner.py` — `ChainStep`, `ChainDefinition`, `ChainEvent`, `_resolve_inputs()`, `run_chain()`. Imports `chain_adapter` via relative import from the same package.
- `flask/modules/chain/tests/test_runner.py` — 7 unit tests for the runner using `CHAIN_PROVIDER=mock`.

### To Modify
- `flask/modules/chain/tests/test_structural.py` — add `pipelinedFeatures_useRunChain()` structural test (AST-based; greps all `modules/*/routes.py` for repeated `chain_adapter.generate`/`stream` calls per handler). Current state: 1 test (`featureModules_mustNotImportProvidersDirectly`).

### To Leave Alone
- `flask/modules/chain/adapter.py` — runner calls `chain_adapter.generate()`; adapter requires no changes.
- `flask/modules/chain/types.py` — `ChainResult` is the return type from `adapter.generate()`; consumed read-only by the runner.
- `flask/modules/chain/providers/` — no changes; the existing provider implementations are correct.
- `flask/modules/ai/routes.py` — no consumer route this task; leave untouched.
- `flask/modules/ai/prompts/__init__.py` — prompt split is Task 2; leave the monolithic `generate_spec_prompt()` intact.

---

## 4. Implementation Steps

### Step 1: Create `flask/modules/chain/runner.py`

**Action**: Create the runner module with the three types and `run_chain()` generator. Port from the chain primitive shape described in `braindump-chain-primitive-port.md` (lines 27–47) and the reference adapter pattern in the architecture doc. `ChainEvent` uses Pydantic `BaseModel` (not dataclass) for `model_dump_json()` SSE support. `ChainStep` and `ChainDefinition` are frozen dataclasses. `run_chain()` uses `adapter.generate()` (no streaming in this task). Any exception inside a step is caught, emits an `error` event naming the step, then returns — the generator never truncates silently.

**File**: `flask/modules/chain/runner.py` (new)

**Pattern** — port and adapt from `braindump-chain-primitive-port.md:27-47`:
```python
"""Chain runner — port of bubls agent_runtime/runner.py.

Adaptations from source:
- No DB logging: steps log via logger.info(); chain_call table deferred
  (trigger: cost observability becomes a real requirement).
- No user object: context comes through the inputs dict as plain strings.
- ChainEvent is Pydantic BaseModel (not dataclass) for model_dump_json()
  SSE serialization in the route handler (Task 4).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Iterator, Literal

from pydantic import BaseModel, Field

from . import adapter as chain_adapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChainStep:
    """One step: a prompt builder and its input references."""
    name: str
    prompt_fn: Callable[..., tuple[str, str]]
    inputs: dict[str, str]  # param_name → "$prior_step_name" or "$input"


@dataclass(frozen=True)
class ChainDefinition:
    """Ordered pipeline of ChainSteps with a name."""
    name: str
    steps: list[ChainStep]


class ChainEvent(BaseModel):
    """SSE event payload. model_dump_json() used in streaming route (Task 4)."""
    type: Literal["step_started", "step_completed", "chain_completed", "error"]
    step: str | None = None
    data: dict = Field(default_factory=dict)


def _resolve_inputs(inputs: dict[str, str], outputs: dict[str, str]) -> dict[str, str]:
    """Resolve $-prefixed references to entries in outputs."""
    resolved: dict[str, str] = {}
    for param, ref in inputs.items():
        if ref.startswith("$"):
            key = ref[1:]
            if key not in outputs:
                raise KeyError(
                    f"input ${key!r} not found in chain outputs; "
                    f"available: {sorted(outputs)}"
                )
            resolved[param] = outputs[key]
        else:
            resolved[param] = ref
    return resolved


def run_chain(
    definition: ChainDefinition,
    inputs: dict[str, str],
) -> Iterator[ChainEvent]:
    """Execute steps sequentially, yielding ChainEvents.

    inputs: initial context — e.g. {"input": braindump_text, "builder": "...", ...}.
    $input in a step's inputs dict resolves to inputs["input"].
    $<step_name> resolves to that step's completed text output.
    Any exception in a step emits type="error" and halts — never silent truncation.
    """
    outputs: dict[str, str] = dict(inputs)

    for step in definition.steps:
        yield ChainEvent(type="step_started", step=step.name, data={})
        try:
            resolved = _resolve_inputs(step.inputs, outputs)
            system, prompt = step.prompt_fn(**resolved)
            result = chain_adapter.generate(system, prompt)
            outputs[step.name] = result.text
            yield ChainEvent(
                type="step_completed",
                step=step.name,
                data={"text": result.text, "latency_ms": result.latency_ms},
            )
            logger.info(
                "chain.step completed chain=%s step=%s latency_ms=%d",
                definition.name, step.name, result.latency_ms,
            )
        except Exception as exc:
            yield ChainEvent(type="error", step=step.name, data={"message": str(exc)})
            return

    yield ChainEvent(type="chain_completed", step=None, data={"chain": definition.name})
```

**Verify**: `python -c "from flask.modules.chain.runner import ChainDefinition, ChainStep, ChainEvent, run_chain; print('ok')"` from `{WORKSPACE}/spec-doc/` — expect `ok`.

---

### Step 2: Create `flask/modules/chain/tests/test_runner.py`

**Action**: Write 7 pytest functions covering the full event contract. Use `CHAIN_PROVIDER=mock` via `monkeypatch`. Define helper callables at module level with camelCase names (no underscores) so `python_functions = ["test_*", "*_*"]` does not collect them as tests.

**File**: `flask/modules/chain/tests/test_runner.py` (new)

**Pattern** — matches existing test conventions in `flask/modules/chain/tests/test_adapter.py`:
```python
"""Runner tests — condition_expectedOutcome naming, CHAIN_PROVIDER=mock."""
import json
import pytest
from modules.chain.runner import ChainDefinition, ChainStep, ChainEvent, run_chain


# Camelcase helpers — no underscores in name, so pytest won't collect them.
def echoPrompt(text: str) -> tuple[str, str]:
    return "system", f"echo: {text}"


def failingPrompt(text: str) -> tuple[str, str]:
    raise RuntimeError("deliberate step failure")


def singleStep_emitsStartedCompletedChainCompleted(monkeypatch):
    ...

def stepCompleted_dataContainsTextAndLatencyMs(monkeypatch):
    ...

# etc. — full bodies in Tests section below.
```

**Verify**: `python -m pytest flask/modules/chain/tests/test_runner.py -v` from `{WORKSPACE}/spec-doc/` — expect 7 passed.

---

### Step 3: Add `pipelinedFeatures_useRunChain` to `flask/modules/chain/tests/test_structural.py`

**Action**: Append one structural test to the existing file (do not modify `featureModules_mustNotImportProvidersDirectly`). The test uses Python's `ast` module to parse every `modules/*/routes.py` file and counts `chain_adapter.generate` and `chain_adapter.stream` attribute calls per function definition. More than one per function = chain-by-copy-paste violation. Architecture doc (§`test_pipelinedFeatures_useRunChain`) mandates this test ships alongside the primitive because Task 1 is when the violation class first becomes possible.

**File**: `flask/modules/chain/tests/test_structural.py` (modify — append after the existing test)

**Pattern**:
```python
def pipelinedFeatures_useRunChain():
    """Route handlers must not call chain_adapter.generate/stream more than once.

    More than one direct adapter call per handler = chain-by-copy-paste;
    use run_chain() for multi-step pipelines.
    Fix: extract repeated calls into a ChainDefinition and call run_chain().
    """
    import ast
    import pathlib
    from modules.chain import adapter as _adapter

    flask_root = pathlib.Path(_adapter.__file__).parents[2]  # chain/ → modules/ → flask/
    offenders = []

    for routes_py in flask_root.rglob("modules/*/routes.py"):
        tree = ast.parse(routes_py.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            adapter_calls = sum(
                1
                for child in ast.walk(node)
                if isinstance(child, ast.Attribute)
                and isinstance(child.value, ast.Name)
                and child.value.id == "chain_adapter"
                and child.attr in ("generate", "stream")
            )
            if adapter_calls > 1:
                offenders.append(
                    f"{routes_py.relative_to(flask_root)}::{node.name} "
                    f"({adapter_calls} chain_adapter calls)"
                )

    assert offenders == [], (
        f"chain-by-copy-paste detected: {offenders}. "
        "Use run_chain() for multi-step pipelines instead of repeated adapter calls."
    )
```

**Verify**: `python -m pytest flask/modules/chain/tests/test_structural.py -v` from `{WORKSPACE}/spec-doc/` — expect 2 passed (both structural tests).

---

## 5. Tests

Full assertion bodies. Framework: pytest, `python_functions = ["test_*", "*_*"]`, no classes, `condition_expectedOutcome` naming.

```python
# flask/modules/chain/tests/test_runner.py
"""Runner tests — CHAIN_PROVIDER=mock, no filesystem fixtures required."""
import json
import pytest
from modules.chain.runner import ChainDefinition, ChainStep, ChainEvent, run_chain


# Module-level helpers: camelCase (no underscores) so pytest skips collection.
def echoPrompt(text: str) -> tuple[str, str]:
    return "system", f"echo: {text}"


def failingPrompt(text: str) -> tuple[str, str]:
    raise RuntimeError("deliberate step failure")


def singleStep_emitsStartedCompletedChainCompleted(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    defn = ChainDefinition(
        name="test-chain",
        steps=[ChainStep(name="step1", prompt_fn=echoPrompt, inputs={"text": "$input"})],
    )
    events = list(run_chain(defn, {"input": "hello"}))
    types = [e.type for e in events]
    assert types == ["step_started", "step_completed", "chain_completed"], (
        f"unexpected event sequence for single-step chain: {types}"
    )


def stepCompleted_dataContainsTextAndLatencyMs(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    defn = ChainDefinition(
        name="test-chain",
        steps=[ChainStep(name="s", prompt_fn=echoPrompt, inputs={"text": "$input"})],
    )
    events = list(run_chain(defn, {"input": "hi"}))
    completed = next(e for e in events if e.type == "step_completed")
    assert "text" in completed.data, "step_completed.data must include 'text'"
    assert "latency_ms" in completed.data, "step_completed.data must include 'latency_ms'"
    assert isinstance(completed.data["latency_ms"], int), (
        f"latency_ms must be int, got {type(completed.data['latency_ms'])}"
    )


def twoSteps_emitsFiveEventSequence(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")

    def step2Prompt(prior: str) -> tuple[str, str]:
        return "system", f"step2: {prior}"

    defn = ChainDefinition(
        name="two-step",
        steps=[
            ChainStep(name="step1", prompt_fn=echoPrompt, inputs={"text": "$input"}),
            ChainStep(name="step2", prompt_fn=step2Prompt, inputs={"prior": "$step1"}),
        ],
    )
    events = list(run_chain(defn, {"input": "hello"}))
    types = [e.type for e in events]
    assert types == [
        "step_started", "step_completed",
        "step_started", "step_completed",
        "chain_completed",
    ], f"unexpected event sequence for 2-step chain: {types}"


def stepFailure_emitsErrorEventAndHalts(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    defn = ChainDefinition(
        name="fail-chain",
        steps=[
            ChainStep(name="bad", prompt_fn=failingPrompt, inputs={"text": "$input"}),
            ChainStep(name="unreachable", prompt_fn=echoPrompt, inputs={"text": "$input"}),
        ],
    )
    events = list(run_chain(defn, {"input": "trigger"}))
    types = [e.type for e in events]
    assert "error" in types, "step failure must emit error event"
    assert types.count("step_completed") == 0, (
        "no step should complete after a failure"
    )
    error_ev = next(e for e in events if e.type == "error")
    assert error_ev.step == "bad", (
        f"error.step must name the failing step; got: {error_ev.step!r}"
    )
    assert "message" in error_ev.data, "error.data must include 'message'"
    assert "deliberate" in error_ev.data["message"], (
        f"error.data.message should contain the original exception text; "
        f"got: {error_ev.data['message']!r}"
    )


def chainCompleted_dataContainsChainName(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    defn = ChainDefinition(
        name="named-chain",
        steps=[ChainStep(name="s", prompt_fn=echoPrompt, inputs={"text": "$input"})],
    )
    events = list(run_chain(defn, {"input": "x"}))
    finished = next((e for e in events if e.type == "chain_completed"), None)
    assert finished is not None, "chain_completed must be emitted on successful run"
    assert finished.data.get("chain") == "named-chain", (
        f"chain_completed.data['chain'] should be 'named-chain'; got: {finished.data}"
    )


def chainEvent_modelDumpJson_roundtripsToValidJson():
    event = ChainEvent(type="step_started", step="analysis", data={"foo": "bar"})
    serialized = event.model_dump_json()
    parsed = json.loads(serialized)
    assert parsed["type"] == "step_started", f"type mismatch: {parsed}"
    assert parsed["step"] == "analysis", f"step mismatch: {parsed}"
    assert parsed["data"] == {"foo": "bar"}, f"data mismatch: {parsed}"


def missingInputRef_emitsErrorEvent(monkeypatch):
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")

    def promptNeedsGhost(ghost: str) -> tuple[str, str]:
        return "system", ghost

    defn = ChainDefinition(
        name="bad-ref",
        steps=[
            ChainStep(
                name="s",
                prompt_fn=promptNeedsGhost,
                inputs={"ghost": "$nonexistent"},
            )
        ],
    )
    events = list(run_chain(defn, {"input": "hello"}))
    types = [e.type for e in events]
    assert "error" in types, (
        "missing $ref should emit error event, not raise uncaught"
    )
    assert "chain_completed" not in types, (
        "chain must not complete when an input reference is missing"
    )
```

---

## 6. Commit Plan

**Commit 1** — `feat(chain): add ChainDefinition, ChainStep, ChainEvent, run_chain primitive`
- Files: `flask/modules/chain/runner.py`
- What: The three types and the generator. No consumer, no route wiring.

**Commit 2** — `test(chain): runner unit tests + structural guard for pipelined features`
- Files: `flask/modules/chain/tests/test_runner.py`, `flask/modules/chain/tests/test_structural.py`
- What: 7 runner tests + `pipelinedFeatures_useRunChain` structural test appended to existing structural file.

**Deviation logging**: if either commit deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation (e.g., `Deviations: ChainEvent.data typed as dict[str, Any] instead of dict — Pydantic v2 requires explicit Any for mixed-value dicts`).

---

## 7. Verification

```bash
python -m pytest flask/ -v --tb=short
```

**Expected delta**: baseline → baseline + 8 passing. Zero pre-existing tests broken.

Breakdown: 7 new tests in `test_runner.py` + 1 new test in `test_structural.py`.

---

## 8. Rollback

- **Per-step (per-commit)**: each commit is independently revertible — `git revert <sha>`. Commit 2 (tests) can be reverted without affecting Commit 1 (implementation), and vice versa.
- **Per-branch**: if verification fails after both commits, `git reset --hard <pre-task-sha>` discards both. The pre-task sha is the one recorded during pre-flight (`git log --oneline -1`).

---

## 9. Deviations Allowed

- **`list[ChainStep]` in frozen dataclass triggers a Pydantic or mypy warning** → annotate with `field(default_factory=list)` if needed, or use `tuple[ChainStep, ...]` for true immutability. Log in commit body.
- **`ast.parse` fails on a routes.py with a syntax error** → the structural test will raise `SyntaxError` rather than asserting. Wrap the parse in a try/except and add the file to `offenders` with a `"[parse error]"` suffix. Log in commit body.
- **`parents[2]` resolves to the wrong directory** → verify with a `print(flask_root)` one-liner before committing the structural test; adjust the parent count to reach `flask/`.
- **Pydantic v2 rejects `dict` field without explicit type parameter** → use `dict[str, Any]` and add `from typing import Any`. Log in commit body.
- **Step requires side-effect** (push, db write, rm) → STOP, mark `[REQUIRES APPROVAL]`.

---

## 10. Out of Scope

Task 1 delivers the primitive only. Everything downstream is a separate task with its own guide. An eager executor might notice that `run_chain()` is nearly usable for `generate-spec` right now and be tempted to wire in the route — do not. The consumer route requires prompt-split work (Task 2) and chain declaration (Task 3) to be landed and reviewed first. Similarly, the structural test for `pipelinedFeatures_useRunChain` will pass trivially today (there are no chained calls yet) — that is expected and correct.

Explicitly deferred:
- **Prompt split** (`analysis_prompt`, `epic_prompt`, `architecture_prompt`, `spec_doc_spec_prompt`) — Task 2. `generate_spec_prompt()` in `flask/modules/ai/prompts/__init__.py` is untouched.
- **`SPEC_CHAIN` declaration** (`flask/modules/ai/chains.py`) — Task 3. No chain instance is created in this task.
- **SSE route** (`POST /api/ai/text/generate-spec/stream`) — Task 4. No route wiring.
- **OpenAPI + DTO regen** for `ChainEvent` — Task 5.
- **Retry/backoff per step** — deferred until first production rate-limit incident.
- **Streaming within `run_chain()`** (`adapter.stream()` per step) — deferred until Task 4; the route can yield SSE by wrapping the already-batch `run_chain()`.
- **DB logging of chain calls** — deferred until cost observability is a real requirement.

**Rule for the executor**: if a change appears helpful but is named here, STOP and flag it as a deviation rather than absorbing it into this task.

---

## Related Documents

- `braindump-chain-primitive-port.md` — full rationale and shape spec
- `flask/modules/chain/adapter.py` — the call target for `run_chain()`
- `flask/modules/chain/tests/test_structural.py` — file being extended in Step 3