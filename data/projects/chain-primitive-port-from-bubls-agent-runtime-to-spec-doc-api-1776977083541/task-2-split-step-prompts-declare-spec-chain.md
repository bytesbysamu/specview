# Task 2: Split Step Prompts + Declare SPEC_CHAIN

## 1. Context

Task 2 decomposes the monolithic `generate_spec_prompt()` function in `flask/modules/ai/prompts/__init__.py` into four pure, single-responsibility functions — one per pipeline step — and wires them into a `SPEC_CHAIN` declaration in the new `flask/modules/ai/chains.py`. This matters because the runner from Task 1 owns output framing and sequencing; individual step prompts must not embed `===FILE:` marker instructions or assume how their output will be used. The chain declaration is what routes.py (Task 3) will reference to drive the SSE streaming endpoint.

**Trade-offs considered:**
- **Keep `generate_spec_prompt()` alongside new step functions during a soak** — rejected because no route calls it yet; there is no existing batch endpoint in `routes.py` to protect (confirmed by `routes.py:31`), so the old function is dead code the moment the step functions exist.
- **Put `SPEC_CHAIN` inside `prompts/__init__.py`** — rejected because `chains.py` declares orchestration shape while `prompts/__init__.py` declares individual step text; mixing them makes both harder to test in isolation and inverts the dependency direction (prompts should not know about chain structure).
- **Four separate prompt files, one per step** — rejected; the step prompts are short (~6 lines each) and contextually related; a single `prompts/__init__.py` file keeps them navigable without inventing module hierarchy for 24 lines of code.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Must be run from flask/ directory
cd {WORKSPACE}/flask

# Verify Task 1 shipped — both files are required
ls modules/chain/runner.py               # STOP if missing — Task 1 is not done
python -c "from modules.chain.runner import ChainDefinition, ChainStep, ChainEvent, run_chain; print('Task 1 OK')"

# Inspect ChainStep interface — record fields so chains.py uses the right attribute names
python -c "from modules.chain.runner import ChainStep; import dataclasses; print(dataclasses.fields(ChainStep))"

# Confirm generate_spec_prompt is not called from any route handler
grep -r "generate_spec_prompt" . --include="*.py"  # expect: prompts/__init__.py + test_prompts.py only

# Baseline test count
python -m pytest --co -q 2>/dev/null | tail -5
```

**If Task 1 runner is missing**: STOP. This task cannot proceed without `modules/chain/runner.py` exporting `ChainDefinition`, `ChainStep`, `ChainEvent`, `run_chain`.

**If `generate_spec_prompt` appears in any route file**: STOP and flag — that route must be identified before the function is removed.

**Baseline recorded**: [N]/[N] passing.

---

## 3. Files

### To Create (new)
- `flask/modules/ai/chains.py` — (new) declares `SPEC_CHAIN` as a `ChainDefinition` with four `ChainStep` entries; imports `ChainDefinition`/`ChainStep` from `modules.chain.runner` and the four step prompt functions from `modules.ai.prompts`
- `flask/modules/ai/tests/test_chains.py` — (new) shape + import tests for `SPEC_CHAIN`

### To Modify (cite CODEBASE CONTEXT)
- `flask/modules/ai/prompts/__init__.py` — remove `_GENERATE_SPEC_BASE` constant and `generate_spec_prompt()` (lines 49–72); add four step prompt functions: `spec_analysis_prompt`, `spec_epic_prompt`, `spec_architecture_prompt`, `spec_doc_spec_prompt`
- `flask/modules/ai/tests/test_prompts.py` — remove two stale tests (`generateSpecPrompt_containsFileMarkerInstruction`, `generateSpecPrompt_embedsPrinciples`); add import alias for four new step functions; add 8 new step-function tests

### To Leave Alone
- `flask/modules/chain/adapter.py` — adapter boundary is unchanged; `chains.py` imports only from `modules.chain.runner`, not from `adapter`
- `flask/modules/ai/routes.py` — route handlers for generate-spec are Task 3 scope
- `flask/modules/chain/tests/test_structural.py` — structural test already passes; `chains.py` imports from `modules.chain.runner`, not from `providers.*`; no change needed

---

## 4. Implementation Steps

### Step 1: Remove `generate_spec_prompt()` and add four step prompt functions

**Action**: In `flask/modules/ai/prompts/__init__.py`, delete the `_GENERATE_SPEC_BASE` block and `generate_spec_prompt()` (lines 49–72). Add four step prompt functions after the existing `# ── iterate` block and before `# ── review`.

**File**: `flask/modules/ai/prompts/__init__.py` (CODEBASE CONTEXT: `flask/modules/ai/prompts/__init__.py`)

**Pattern** (replace the deleted block with):
```python
# ── generate-spec steps ───────────────────────────────────────────────────────
# Each function is a pure callable: receives only the inputs its step needs,
# returns (system_prompt, user_prompt). No ===FILE: framing — the runner owns that.

_ANALYSIS_SYSTEM = (
    "You are a spec readiness analyst. Given a product brain dump, produce a concise "
    "analysis document: problem statement (2-3 sentences), hard constraints, open "
    "questions, dependencies, and explicitly out of scope. Under 40 lines total. "
    "Return markdown only — no preamble, no commentary."
)


def spec_analysis_prompt(input_text: str, builder: str, principles: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    return _ANALYSIS_SYSTEM + ctx, input_text


_EPIC_SYSTEM = (
    "You are a product manager writing an epic document. Given a brain dump and a "
    "prior analysis, produce an epic covering: business value, scope (in/out), "
    "task list, and success criteria. Return markdown only — no preamble."
)


def spec_epic_prompt(input_text: str, analysis: str, builder: str, principles: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    return _EPIC_SYSTEM + ctx, f"## Brain dump\n{input_text}\n\n## Analysis\n{analysis}"


_ARCHITECTURE_SYSTEM = (
    "You are a software architect. Given a brain dump and a prior epic, produce an "
    "architecture document: tech stack decisions, key patterns, component "
    "responsibilities, and trade-offs. Return markdown only — no preamble."
)


def spec_architecture_prompt(input_text: str, epic: str, builder: str, principles: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    return _ARCHITECTURE_SYSTEM + ctx, f"## Brain dump\n{input_text}\n\n## Epic\n{epic}"


_SPEC_DOC_SPEC_SYSTEM = (
    "You are a product spec writer. Given a brain dump and a prior architecture, "
    "produce the product thesis document: what this is, who it's for, why it wins, "
    "core principles, and open questions. Return markdown only — no preamble."
)


def spec_doc_spec_prompt(input_text: str, architecture: str, builder: str, principles: str) -> tuple[str, str]:
    ctx = (f"\n\n## Builder Profile\n{builder}" if builder else "")
    ctx += (f"\n\n## Principles\n{principles}" if principles else "")
    return _SPEC_DOC_SPEC_SYSTEM + ctx, f"## Brain dump\n{input_text}\n\n## Architecture\n{architecture}"
```

**Verify**:
```bash
cd {WORKSPACE}/flask
python -c "from modules.ai.prompts import spec_analysis_prompt, spec_epic_prompt, spec_architecture_prompt, spec_doc_spec_prompt; print('imports OK')"
python -c "from modules.ai.prompts import generate_spec_prompt" 2>&1 | grep -q "ImportError\|cannot import" && echo 'old function removed OK'
```

---

### Step 2: Create `chains.py` with `SPEC_CHAIN`

**Action**: Create `flask/modules/ai/chains.py`. Import `ChainDefinition` and `ChainStep` from `modules.chain.runner`. Import the four step functions from `modules.ai.prompts`. Declare `SPEC_CHAIN`.

Before writing, verify the exact field names Task 1 shipped:
```bash
python -c "from modules.chain.runner import ChainStep; import dataclasses; [print(f.name) for f in dataclasses.fields(ChainStep)]"
```
The guide assumes fields: `name` (str), `prompt_fn` (callable), `input_keys` (dict[str, str]). If Task 1 used different field names, adapt and log a deviation in the commit body.

**File**: `flask/modules/ai/chains.py` (new)

**Pattern**:
```python
"""SPEC_CHAIN — four-step spec generation pipeline.

Each ChainStep is a pure declaration: name, prompt function, and input-key
resolution map. run_chain() in modules.chain.runner owns sequencing, $-key
resolution, and ChainEvent emission. This file has no I/O, no adapter calls.
"""
from __future__ import annotations

from modules.chain.runner import ChainDefinition, ChainStep
from modules.ai.prompts import (
    spec_analysis_prompt,
    spec_epic_prompt,
    spec_architecture_prompt,
    spec_doc_spec_prompt,
)

SPEC_CHAIN = ChainDefinition(
    name="generate-spec",
    steps=(
        ChainStep(
            name="analysis",
            prompt_fn=spec_analysis_prompt,
            input_keys={
                "input_text": "$input_text",
                "builder": "$builder",
                "principles": "$principles",
            },
        ),
        ChainStep(
            name="epic",
            prompt_fn=spec_epic_prompt,
            input_keys={
                "input_text": "$input_text",
                "analysis": "$analysis",
                "builder": "$builder",
                "principles": "$principles",
            },
        ),
        ChainStep(
            name="architecture",
            prompt_fn=spec_architecture_prompt,
            input_keys={
                "input_text": "$input_text",
                "epic": "$epic",
                "builder": "$builder",
                "principles": "$principles",
            },
        ),
        ChainStep(
            name="spec_doc_spec",
            prompt_fn=spec_doc_spec_prompt,
            input_keys={
                "input_text": "$input_text",
                "architecture": "$architecture",
                "builder": "$builder",
                "principles": "$principles",
            },
        ),
    ),
)
```

**Verify**:
```bash
cd {WORKSPACE}/flask
python -c "from modules.ai.chains import SPEC_CHAIN; print(len(SPEC_CHAIN.steps), 'steps')"
# expect: 4 steps
python -c "from modules.ai.chains import SPEC_CHAIN; print([s.name for s in SPEC_CHAIN.steps])"
# expect: ['analysis', 'epic', 'architecture', 'spec_doc_spec']
```

---

### Step 3: Update `test_prompts.py` and create `test_chains.py`

**Action**: In `flask/modules/ai/tests/test_prompts.py`:
1. Remove the alias `generateSpecPrompt = _prompts.generate_spec_prompt` (line 6)
2. Add four import aliases for the new step functions
3. Delete `generateSpecPrompt_containsFileMarkerInstruction` and `generateSpecPrompt_embedsPrinciples` (lines 56–64)
4. Add 8 new step-function tests

Then create `flask/modules/ai/tests/test_chains.py` with SPEC_CHAIN shape tests.

**File**: `flask/modules/ai/tests/test_prompts.py` (CODEBASE CONTEXT: `flask/modules/ai/tests/test_prompts.py`)

Add after line 10 (existing aliases block):
```python
specAnalysisPrompt = _prompts.spec_analysis_prompt
specEpicPrompt = _prompts.spec_epic_prompt
specArchitecturePrompt = _prompts.spec_architecture_prompt
specDocSpecPrompt = _prompts.spec_doc_spec_prompt
```

Remove lines 56–64 entirely (the two `generateSpecPrompt_*` tests).

Add at end of file:
```python
def specAnalysisPrompt_embedsInputText():
    _, prompt = specAnalysisPrompt("my product idea", "", "")
    assert "my product idea" in prompt

def specAnalysisPrompt_embedsBuilderInSystem():
    system, _ = specAnalysisPrompt("idea", "I am a solo founder", "")
    assert "I am a solo founder" in system

def specEpicPrompt_embedsAnalysisInPrompt():
    _, prompt = specEpicPrompt("idea", "analysis content here", "", "")
    assert "analysis content here" in prompt

def specEpicPrompt_omitsBuilderSectionWhenEmpty():
    system, _ = specEpicPrompt("idea", "analysis", "", "")
    assert "Builder Profile" not in system

def specArchitecturePrompt_embedsEpicInPrompt():
    _, prompt = specArchitecturePrompt("idea", "epic content here", "", "")
    assert "epic content here" in prompt

def specArchitecturePrompt_embedsPrinciplesInSystem():
    system, _ = specArchitecturePrompt("idea", "epic", "", "ship fast")
    assert "ship fast" in system

def specDocSpecPrompt_embedsArchitectureInPrompt():
    _, prompt = specDocSpecPrompt("idea", "architecture content here", "", "")
    assert "architecture content here" in prompt

def specDocSpecPrompt_embedsBuilderInSystem():
    system, _ = specDocSpecPrompt("idea", "arch", "I am a solo founder", "")
    assert "I am a solo founder" in system
```

**File**: `flask/modules/ai/tests/test_chains.py` (new)

```python
# flask/modules/ai/tests/test_chains.py
from modules.ai.chains import SPEC_CHAIN


def specChain_hasExactlyFourSteps():
    assert len(SPEC_CHAIN.steps) == 4, f"expected 4 steps, got {len(SPEC_CHAIN.steps)}"


def specChain_stepNamesAreInOrder():
    names = [s.name for s in SPEC_CHAIN.steps]
    assert names == ["analysis", "epic", "architecture", "spec_doc_spec"], (
        f"step names or order wrong: {names}"
    )


def specChain_allStepsHaveCallablePromptFn():
    for step in SPEC_CHAIN.steps:
        assert callable(step.prompt_fn), f"step {step.name!r}: prompt_fn is not callable"


def specChain_epicStepResolvesAnalysisFromPriorStep():
    epic_step = next(s for s in SPEC_CHAIN.steps if s.name == "epic")
    assert "$analysis" in epic_step.input_keys.values(), (
        "epic step must resolve $analysis from the prior analysis step output"
    )


def specChain_architectureStepResolvesEpicFromPriorStep():
    arch_step = next(s for s in SPEC_CHAIN.steps if s.name == "architecture")
    assert "$epic" in arch_step.input_keys.values(), (
        "architecture step must resolve $epic from the prior epic step output"
    )


def specChain_specDocSpecStepResolvesArchitectureFromPriorStep():
    spec_step = next(s for s in SPEC_CHAIN.steps if s.name == "spec_doc_spec")
    assert "$architecture" in spec_step.input_keys.values(), (
        "spec_doc_spec step must resolve $architecture from the prior architecture step output"
    )
```

**Verify**:
```bash
cd {WORKSPACE}/flask
python -m pytest modules/ai/tests/test_prompts.py modules/ai/tests/test_chains.py -v
# All new tests pass; no generateSpecPrompt_* tests appear in output
```

---

## 5. Tests

All tests in `flask/modules/ai/tests/test_prompts.py` and `flask/modules/ai/tests/test_chains.py`. Complete assertion bodies shown in Step 3 above. Framework: pytest with `python_functions = ["test_*", "*_*"]` (from `flask/pyproject.toml`).

Summary of assertion logic:

| Test | Assertion |
|------|-----------|
| `specAnalysisPrompt_embedsInputText` | `"my product idea" in prompt` |
| `specAnalysisPrompt_embedsBuilderInSystem` | `"I am a solo founder" in system` |
| `specEpicPrompt_embedsAnalysisInPrompt` | `"analysis content here" in prompt` |
| `specEpicPrompt_omitsBuilderSectionWhenEmpty` | `"Builder Profile" not in system` |
| `specArchitecturePrompt_embedsEpicInPrompt` | `"epic content here" in prompt` |
| `specArchitecturePrompt_embedsPrinciplesInSystem` | `"ship fast" in system` |
| `specDocSpecPrompt_embedsArchitectureInPrompt` | `"architecture content here" in prompt` |
| `specDocSpecPrompt_embedsBuilderInSystem` | `"I am a solo founder" in system` |
| `specChain_hasExactlyFourSteps` | `len(SPEC_CHAIN.steps) == 4` |
| `specChain_stepNamesAreInOrder` | `names == ["analysis", "epic", "architecture", "spec_doc_spec"]` |
| `specChain_allStepsHaveCallablePromptFn` | `callable(step.prompt_fn)` for each step |
| `specChain_epicStepResolvesAnalysisFromPriorStep` | `"$analysis" in epic_step.input_keys.values()` |
| `specChain_architectureStepResolvesEpicFromPriorStep` | `"$epic" in arch_step.input_keys.values()` |
| `specChain_specDocSpecStepResolvesArchitectureFromPriorStep` | `"$architecture" in spec_step.input_keys.values()` |

---

## 6. Commit Plan

1. `refactor(ai/prompts): split generate_spec_prompt into four step functions` — `flask/modules/ai/prompts/__init__.py`: remove `_GENERATE_SPEC_BASE` + `generate_spec_prompt()`; add `_ANALYSIS_SYSTEM`, `spec_analysis_prompt`, `_EPIC_SYSTEM`, `spec_epic_prompt`, `_ARCHITECTURE_SYSTEM`, `spec_architecture_prompt`, `_SPEC_DOC_SPEC_SYSTEM`, `spec_doc_spec_prompt`

2. `feat(ai/chains): declare SPEC_CHAIN with four ChainStep entries` — `flask/modules/ai/chains.py` (new): `SPEC_CHAIN` wiring all four step functions with `$`-prefixed input resolution

3. `test(ai/prompts): replace generateSpecPrompt tests with step-function tests` — `flask/modules/ai/tests/test_prompts.py`: remove 2 stale tests, add 8 step-function tests; `flask/modules/ai/tests/test_chains.py` (new): 6 SPEC_CHAIN shape tests

**Deviation logging**: prefix the commit body with `Deviations:` and one line per deviation if `ChainStep` fields differ from `name`/`prompt_fn`/`input_keys` assumed in this guide.

---

## 7. Verification

```bash
cd {WORKSPACE}/flask
python -m pytest -v
```

**Expected delta**: baseline N → N+12 passing (remove 2 stale `generateSpecPrompt_*` tests, add 8 step-function tests + 6 SPEC_CHAIN tests = net +12). Zero pre-existing tests broken.

Spot-check the structural test still passes:
```bash
python -m pytest modules/chain/tests/test_structural.py -v
# featureModules_mustNotImportProvidersDirectly must pass — chains.py imports from runner, not providers
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. Commits are ordered so reverting commit 3 alone restores old tests; reverting commit 2 removes `chains.py`; reverting commit 1 restores `generate_spec_prompt()`.
- **Per-branch**: `git reset --hard <pre-task-sha>` returns the branch to the post-Task-1 state. No DB migrations, no external state, no side effects to undo.

---

## 9. Deviations Allowed

- **`ChainStep` fields differ from assumed shape** (`name`/`prompt_fn`/`input_keys`) → inspect Task 1's `runner.py`, adapt `chains.py` field names to match, and log the deviation in commit 2's body. Do not invent a shim; use what Task 1 shipped.
- **`ChainDefinition.steps` is a `list` not a `tuple`** → use `[...]` instead of `(...)` in `SPEC_CHAIN`; log deviation.
- **`input_keys` uses a different resolution marker than `$`** → use whatever marker Task 1 uses; the semantics (prior-step output by name, initial input by name) are the invariant, not the character.
- **Step N test reveals the system constant needs a wording tweak** → adjust the constant, log deviation in the commit body. System prompt content is not load-bearing for the chain shape tests.
- **Side-effect required** (schema change, push, publish) → STOP, mark [REQUIRES APPROVAL], ask.

---

## 10. Out of Scope

This task ends at pure function declarations and the chain shape. It does not touch routes, the adapter, or tests that require HTTP. The runner from Task 1 is treated as a black box whose interface is inspected but not modified. The following are explicitly deferred and must not be absorbed by an eager executor:

- **SSE streaming endpoint** (`POST /api/ai/text/generate-spec/stream`) — Task 3 scope; routes.py comment at line 31 already marks this boundary
- **OpenAPI declaration for `ChainEvent`** — Task 4 scope; no `openapi.yaml` changes in this task
- **DTO regeneration (`make dto`)** — no new request/response DTOs are introduced; `ChainEvent` is declared in Task 1's runner
- **Structural test `test_pipelinedFeatures_useRunChain`** — greps route files for adapter call sites; meaningless until the route exists (Task 3)
- **Removal of the batch `generate-spec` endpoint** — confirmed non-existent in `routes.py`; no deprecation action needed in this task
- **`context_loader` integration** — route handler (Task 3) reads context and passes `builder`/`principles` as plain strings; `chains.py` and `prompts/__init__.py` receive them as parameters and must not import `context_loader`

**Rule for the executor**: if a change touches `routes.py`, `openapi.yaml`, `context_loader.py`, or any test that starts a Flask app, STOP and flag it as out-of-scope before proceeding.

---

## Related Documents

- [Solution Architecture](./projects/chain-primitive-port-from-bubls-agent-runtime-to-spec-doc-api-1776977083541/architecture.md) — Design rationale; `ChainEvent` type decision; context-stays-in-route decision
- [Epic](./projects/chain-primitive-port-from-bubls-agent-runtime-to-spec-doc-api-1776977083541/epic.md) — Full task list and scope
- [Timeline](./projects/chain-primitive-port-from-bubls-agent-runtime-to-spec-doc-api-1776977083541/timeline.md) — Status tracking (update after done)