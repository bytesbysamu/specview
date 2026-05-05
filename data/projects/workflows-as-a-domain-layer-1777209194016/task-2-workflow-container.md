# Task 2: Workflow Container — Implementation Guide

## 1. Context

Task 2 introduces the `Workflow` Aggregate Root (ELA Pattern #20) and its fluent `WorkflowBuilder` (ELA Pattern #1) as the Layer C domain object that route handlers will eventually invoke in place of inline orchestration. A `Workflow` is a named, immutable, ordered container of Steps whose construction is controlled entirely by the builder — guaranteeing that declared inputs, outputs, and a non-empty step list are always satisfied before a `Workflow` object exists. `WorkflowRef` is the lightweight identifier external callers hold rather than the full aggregate. This task ships the pure-Python container with no runtime, no repository, and no JSON schema; subsequent tasks (Layer D and E) consume it.

**Trade-offs considered**:
- **Using `AbstractBaseClass` with a `__new__` guard** to prevent direct instantiation — rejected because it adds metaclass complexity and `frozen=True` dataclasses already raise `FrozenInstanceError` on mutation; convention + a structural test covers the construction path cheaply.
- **Making `Workflow` a plain `class` with `__slots__`** rather than a frozen dataclass — rejected because the frozen dataclass gives `__eq__`, `__hash__`, and immutability for free with less ceremony, consistent with the existing `ChainResult` and `ReviewResult` shapes in `modules/chain/types.py`.
- **Frozen dataclass for `Workflow` + `WorkflowBuilder` as a standalone class** — preferred because it separates mutable construction state from the immutable aggregate, matches the repo's existing value-object pattern, and gives the JSON loader in Phase 3 a clean `build()` call site without new construction logic.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# From the spec-doc-api root
cd {WORKSPACE}   # i.e., spec-doc/api/

git status                                           # Flag any unrelated M/?? entries
git diff HEAD -- modules/ tests/                     # Confirm target files are clean
ls modules/ | grep workflows                         # Must print nothing — package must not exist yet
make test 2>&1 | tail -5                             # Record baseline; note passing count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: `___` / `___` passing (fill in from `make test` output before Step 1).

---

## 3. Files

### To Create (new)
- `modules/workflows/__init__.py` — package entry point; exports `Workflow` and `WorkflowRef`
- `modules/workflows/workflow.py` — `WorkflowRef` frozen dataclass, `Workflow` frozen aggregate, `WorkflowBuilder` fluent class
- `modules/workflows/tests/__init__.py` — empty; makes pytest discover the test module
- `modules/workflows/tests/test_workflow.py` — full test suite (30 tests); imports `AbstractStep` from Task 1.1 and defines a tiny `NoopStep(AbstractStep)` subclass for use as test fixtures (no inspection of step internals — the assertions only care about Step identity and ordering).

### To Modify
*(none — Task 2 adds a new package and does not touch any existing file)*

### To Leave Alone
- `modules/chain/adapter.py` — Layer A adapter; Task 2 has no AI call boundary; do not widen its signature here
- `modules/chain/types.py` — existing frozen value objects (`ChainResult`, `ReviewResult`); serve as the pattern reference only
- `create_app.py` — `ENABLED_MODULES` list; `modules.workflows` has no blueprint and must not be registered here
- `tests/test_structural.py` and `modules/chain/tests/test_structural.py` — existing structural tests; do not edit them
- `dtos/models.py` — auto-generated; never hand-edit

---

## 4. Implementation Steps

### Step 1: Scaffold the `workflows` package

**Action**: Create the three empty anchor files that establish the package on disk.

**File**: `modules/workflows/__init__.py` (new)

```python
# placeholder — replaced in Step 4
```

**File**: `modules/workflows/workflow.py` (new)

```python
# placeholder — replaced in Steps 2–4
```

**File**: `modules/workflows/tests/__init__.py` (new)

```python
# empty — pytest discovery anchor
```

**Verify**:
```bash
python -c "import modules.workflows"   # Must exit 0 with no output
```

---

**Commit after Step 1** (see Section 6, commit 1).

---

### Step 2: Implement `WorkflowRef`

**Action**: Replace `modules/workflows/workflow.py` content with the `WorkflowRef` frozen dataclass. Validate that `name` is non-empty. Implement `__str__` and `__repr__`. The frozen dataclass gives `__eq__` and `__hash__` for free, making it safe to use as a dict key or set member.

**File**: `modules/workflows/workflow.py` (new — replace placeholder)

**Pattern** (porting from `modules/chain/types.py` frozen-dataclass shape):

```python
"""Workflow aggregate — Layer C.
ELA Patterns: #1 (Builder), #8 (Facade), #20 (Aggregate Root).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowRef:
    """Stable identifier for a named Workflow.

    External callers (route handlers, WorkflowExecution) hold WorkflowRef,
    not the Workflow object itself.

    name: qualified identifier — ``"<feature>/<workflow-name>"``,
          e.g. ``"spec_gen/generate-spec"``.
    """
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError(
                "WorkflowRef.name must be a non-empty, non-blank string"
            )

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"WorkflowRef({self.name!r})"
```

**Verify**:
```bash
python -c "
from modules.workflows.workflow import WorkflowRef
r = WorkflowRef('spec_gen/generate-spec')
assert str(r) == 'spec_gen/generate-spec'
assert r == WorkflowRef('spec_gen/generate-spec')
print('WorkflowRef OK')
"
```

---

**Commit after Step 2** (see Section 6, commit 2).

---

### Step 3: Implement `WorkflowBuilder`

**Action**: Append `WorkflowBuilder` to `modules/workflows/workflow.py` immediately after `WorkflowRef`. The builder holds mutable state (`set`, `list`) during construction, then freezes it into the `Workflow` aggregate on `build()`. All fluent setters return `self`. `build()` collects all failing invariants before raising so callers see the full error in one shot.

**File**: `modules/workflows/workflow.py` (extend — append after `WorkflowRef`)

**Pattern**:

```python
class WorkflowBuilder:
    """Fluent Builder (ELA Pattern #1). Only legal construction path for Workflow.

    Usage::

        wf = (
            Workflow.builder("spec_gen/generate-spec")
            .inputs("braindump", "project_name")
            .outputs("spec_markdown")
            .step(step_a)
            .step(step_b)
            .build()
        )
    """

    def __init__(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Workflow name must not be empty or blank")
        self._name: str = name
        self._inputs: set[str] = set()
        self._outputs: set[str] = set()
        self._steps: list[Any] = []

    # ── Fluent setters ──────────────────────────────────────────────────────

    def inputs(self, *names: str) -> "WorkflowBuilder":
        """Declare one or more input names. Chainable."""
        self._inputs.update(names)
        return self

    def outputs(self, *names: str) -> "WorkflowBuilder":
        """Declare one or more output names. Chainable."""
        self._outputs.update(names)
        return self

    def step(self, s: Any) -> "WorkflowBuilder":
        """Append one Step to the ordered step list. Chainable."""
        self._steps.append(s)
        return self

    # ── Terminal ────────────────────────────────────────────────────────────

    def build(self) -> "Workflow":
        """Validate all invariants and return a frozen Workflow.

        Raises ValueError listing every unmet invariant (not just the first).
        """
        errors: list[str] = []
        if not self._inputs:
            errors.append("at least one input must be declared (.inputs(...))")
        if not self._outputs:
            errors.append("at least one output must be declared (.outputs(...))")
        if not self._steps:
            errors.append("at least one step must be appended (.step(...))")
        if errors:
            raise ValueError(
                f"Cannot build Workflow {self._name!r}: " + "; ".join(errors)
            )
        return Workflow(
            ref=WorkflowRef(self._name),
            inputs=frozenset(self._inputs),
            outputs=frozenset(self._outputs),
            steps=tuple(self._steps),
        )

    # ── Internal ────────────────────────────────────────────────────────────

    @classmethod
    def _from_workflow(cls, w: "Workflow") -> "WorkflowBuilder":
        """Reconstruct a mutable builder from a frozen Workflow (for to_builder())."""
        b = cls(w.ref.name)
        b._inputs = set(w.inputs)
        b._outputs = set(w.outputs)
        b._steps = list(w.steps)
        return b
```

**Verify**:
```bash
python -c "
from modules.workflows.workflow import WorkflowBuilder
from dataclasses import dataclass

@dataclass(frozen=True)
class _S:
    n: str

b = WorkflowBuilder('a/wf')
assert b.inputs('x') is b
assert b.outputs('y') is b
assert b.step(_S('s1')) is b
print('Builder fluent API OK')
"
```

---

### Step 4: Implement the `Workflow` aggregate and wire `__init__.py`

**Action**: Append the `Workflow` frozen dataclass to `modules/workflows/workflow.py` after `WorkflowBuilder`. Then replace `modules/workflows/__init__.py` with the public exports.

**File**: `modules/workflows/workflow.py` (extend — append after `WorkflowBuilder`)

**Pattern** (follows `ChainResult` frozen-dataclass shape in `modules/chain/types.py`; adds static factory and instance variation method per architecture Layer C):

```python
@dataclass(frozen=True)
class Workflow:
    """Aggregate Root (ELA Pattern #20). Named, immutable, ordered Step container.

    Construct exclusively via ``Workflow.builder(name)``.
    Direct instantiation bypasses all builder-enforced invariants.

    steps: ordered tuple of AbstractStep instances.
           Authorised consumer: WorkflowRuntime (Layer D) only.
           Route handlers must not enumerate or reference individual steps.
    """
    ref: WorkflowRef
    inputs: frozenset[str]
    outputs: frozenset[str]
    steps: tuple[Any, ...]

    # ── Read-only derived ──────────────────────────────────────────────────

    @property
    def step_count(self) -> int:
        """Number of steps in this workflow."""
        return len(self.steps)

    # ── Construction ───────────────────────────────────────────────────────

    @staticmethod
    def builder(name: str) -> WorkflowBuilder:
        """Fluent Builder entry point. The sole legal construction path."""
        return WorkflowBuilder(name)

    def to_builder(self) -> WorkflowBuilder:
        """Return a Builder pre-populated from this Workflow for creating variations.

        The returned builder is independent; calling build() produces a new
        Workflow and leaves this one unchanged (frozen).
        """
        return WorkflowBuilder._from_workflow(self)
```

**File**: `modules/workflows/__init__.py` (replace placeholder)

```python
"""Workflow domain layer — Layer C.

Public API
----------
Workflow      Aggregate Root; construct via Workflow.builder(name)
WorkflowRef   Stable identifier; external callers hold this, not Workflow
"""
from .workflow import Workflow, WorkflowRef

__all__ = ["Workflow", "WorkflowRef"]
```

**Verify**:
```bash
python -c "
from modules.workflows import Workflow, WorkflowRef
from dataclasses import dataclass

@dataclass(frozen=True)
class _S:
    n: str

wf = (
    Workflow.builder('spec_gen/generate-spec')
    .inputs('braindump', 'project_name')
    .outputs('spec_markdown')
    .step(_S('draft'))
    .step(_S('review'))
    .build()
)
assert wf.ref == WorkflowRef('spec_gen/generate-spec')
assert wf.step_count == 2
assert isinstance(wf.inputs, frozenset)
assert isinstance(wf.steps, tuple)
try:
    wf.ref = WorkflowRef('other')
    raise AssertionError('should be frozen')
except (AttributeError, TypeError):
    pass
print('Workflow aggregate OK')
"
```

---

**Commit after Steps 3 + 4 together** (see Section 6, commit 3).

---

### Step 5: Write and run the test suite

**Action**: Create `modules/workflows/tests/test_workflow.py` with the full 30-test suite below (see Section 5). Run it and confirm all pass with zero regressions in pre-existing tests.

**File**: `modules/workflows/tests/test_workflow.py` (new)

**Verify**:
```bash
python -m pytest modules/workflows/tests/ -v          # All 30 new tests pass
make test                                             # Full suite; baseline + 30 passing, 0 broken
```

---

**Commit after Step 5** (see Section 6, commit 4).

---

## 5. Tests

Framework: **pytest** with `python_functions = ["test_*", "*_*"]` (from `pyproject.toml`). Naming convention: `subject_verbObject` with camelCase interior, matching `healthEndpoint_returns200` and `mockProvider_generateReturnsChainResult` patterns in the repo.

**File**: `modules/workflows/tests/test_workflow.py`

```python
"""Workflow aggregate and builder tests — Layer C.

Uses a minimal `NoopStep(AbstractStep)` subclass as the test fixture. Tests
do not inspect step internals — they assert on Step identity and ordering only.
"""
from __future__ import annotations

import pytest

from modules.workflows import Workflow, WorkflowRef
from modules.workflows.steps import AbstractStep


# ── Test step fixture ─────────────────────────────────────────────────────────
# Minimal AbstractStep subclass; no provider, no I/O. Suitable as a placeholder
# in workflow-container tests that don't exercise step execution.

class NoopStep(AbstractStep):
    def _invoke(self, context):  # noqa: D401
        return None


_STEP_A = NoopStep(name="step-a")
_STEP_B = NoopStep(name="step-b")
_STEP_C = NoopStep(name="step-c")


# ── WorkflowRef ───────────────────────────────────────────────────────────────

def workflowRef_storesName():
    ref = WorkflowRef("spec_gen/generate-spec")
    assert ref.name == "spec_gen/generate-spec", (
        f"expected 'spec_gen/generate-spec', got {ref.name!r}"
    )


def workflowRef_strReturnsName():
    ref = WorkflowRef("spec_gen/generate-spec")
    assert str(ref) == "spec_gen/generate-spec", (
        f"__str__ returned {str(ref)!r}"
    )


def workflowRef_reprContainsName():
    ref = WorkflowRef("my/wf")
    assert "my/wf" in repr(ref), (
        f"__repr__ did not contain 'my/wf': {repr(ref)!r}"
    )


def workflowRef_isFrozen():
    ref = WorkflowRef("spec_gen/generate-spec")
    with pytest.raises((AttributeError, TypeError)):
        ref.name = "mutated"  # type: ignore[misc]


def workflowRef_equalByValue():
    assert WorkflowRef("a/b") == WorkflowRef("a/b"), (
        "Two WorkflowRefs with the same name must be equal"
    )


def workflowRef_differentNames_notEqual():
    assert WorkflowRef("a/b") != WorkflowRef("a/c"), (
        "WorkflowRefs with different names must not be equal"
    )


def workflowRef_hashableAndUsableInSet():
    refs = {WorkflowRef("a/b"), WorkflowRef("a/b"), WorkflowRef("c/d")}
    assert len(refs) == 2, (
        f"Expected 2 unique refs in set, got {len(refs)}"
    )


def workflowRef_emptyName_raisesValueError():
    with pytest.raises(ValueError):
        WorkflowRef("")


def workflowRef_blankName_raisesValueError():
    with pytest.raises(ValueError):
        WorkflowRef("   ")


# ── WorkflowBuilder — fluent API ──────────────────────────────────────────────

def builder_inputsReturnsSelf():
    b = Workflow.builder("a/wf")
    result = b.inputs("x")
    assert result is b, "inputs() must return the builder for chaining"


def builder_outputsReturnsSelf():
    b = Workflow.builder("a/wf")
    result = b.outputs("y")
    assert result is b, "outputs() must return the builder for chaining"


def builder_stepReturnsSelf():
    b = Workflow.builder("a/wf")
    result = b.step(_STEP_A)
    assert result is b, "step() must return the builder for chaining"


def builder_fullyChained_buildsSuccessfully():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf, Workflow), (
        f"build() must return a Workflow, got {type(wf)}"
    )


def builder_multipleInputs_allStored():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x", "y", "z")
        .outputs("out")
        .step(_STEP_A)
        .build()
    )
    assert wf.inputs == frozenset({"x", "y", "z"}), (
        f"expected inputs {{'x','y','z'}}, got {wf.inputs}"
    )


def builder_multipleOutputs_allStored():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("p", "q")
        .step(_STEP_A)
        .build()
    )
    assert wf.outputs == frozenset({"p", "q"}), (
        f"expected outputs {{'p','q'}}, got {wf.outputs}"
    )


def builder_multipleSteps_orderPreserved():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .step(_STEP_B)
        .step(_STEP_C)
        .build()
    )
    assert wf.steps == (_STEP_A, _STEP_B, _STEP_C), (
        f"Step order not preserved: {wf.steps}"
    )


def builder_stepCount_matchesStepsAdded():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .step(_STEP_B)
        .build()
    )
    assert wf.step_count == 2, (
        f"expected step_count=2, got {wf.step_count}"
    )


# ── WorkflowBuilder — validation ──────────────────────────────────────────────

def builder_noSteps_buildRaisesValueError():
    with pytest.raises(ValueError, match="step"):
        Workflow.builder("a/wf").inputs("x").outputs("y").build()


def builder_noInputs_buildRaisesValueError():
    with pytest.raises(ValueError, match="input"):
        Workflow.builder("a/wf").outputs("y").step(_STEP_A).build()


def builder_noOutputs_buildRaisesValueError():
    with pytest.raises(ValueError, match="output"):
        Workflow.builder("a/wf").inputs("x").step(_STEP_A).build()


def builder_allInvariantsUnmet_errorMessageListsAll():
    with pytest.raises(ValueError) as exc:
        Workflow.builder("a/wf").build()
    msg = str(exc.value)
    assert "input" in msg, f"error message missing 'input': {msg}"
    assert "output" in msg, f"error message missing 'output': {msg}"
    assert "step" in msg, f"error message missing 'step': {msg}"


def builder_emptyName_raisesValueError():
    with pytest.raises(ValueError):
        Workflow.builder("")


def builder_blankName_raisesValueError():
    with pytest.raises(ValueError):
        Workflow.builder("   ")


# ── Workflow aggregate ────────────────────────────────────────────────────────

def workflow_refMatchesBuilderName():
    wf = (
        Workflow.builder("spec_gen/generate-spec")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    assert wf.ref == WorkflowRef("spec_gen/generate-spec"), (
        f"ref mismatch: {wf.ref!r}"
    )


def workflow_isFrozen_refMutationRaises():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    with pytest.raises((AttributeError, TypeError)):
        wf.ref = WorkflowRef("other")  # type: ignore[misc]


def workflow_stepsIsTuple():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf.steps, tuple), (
        f"steps must be a tuple for immutability; got {type(wf.steps)}"
    )


def workflow_inputsIsFrozenset():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x", "y")
        .outputs("z")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf.inputs, frozenset), (
        f"inputs must be a frozenset; got {type(wf.inputs)}"
    )


def workflow_outputsIsFrozenset():
    wf = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("z", "w")
        .step(_STEP_A)
        .build()
    )
    assert isinstance(wf.outputs, frozenset), (
        f"outputs must be a frozenset; got {type(wf.outputs)}"
    )


# ── to_builder / variations ───────────────────────────────────────────────────

def toBuilder_producesEquivalentWorkflow():
    original = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    copy = original.to_builder().build()
    assert copy.ref == original.ref, f"ref mismatch: {copy.ref!r}"
    assert copy.inputs == original.inputs, f"inputs mismatch: {copy.inputs}"
    assert copy.outputs == original.outputs, f"outputs mismatch: {copy.outputs}"
    assert copy.steps == original.steps, f"steps mismatch: {copy.steps}"


def toBuilder_addingStep_doesNotMutateOriginal():
    original = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    variant = original.to_builder().step(_STEP_B).build()
    assert original.step_count == 1, (
        f"original.step_count mutated: expected 1, got {original.step_count}"
    )
    assert variant.step_count == 2, (
        f"variant.step_count wrong: expected 2, got {variant.step_count}"
    )


def toBuilder_addingInput_doesNotMutateOriginal():
    original = (
        Workflow.builder("a/wf")
        .inputs("x")
        .outputs("y")
        .step(_STEP_A)
        .build()
    )
    variant = original.to_builder().inputs("extra").build()
    assert "extra" not in original.inputs, (
        f"original.inputs was mutated: {original.inputs}"
    )
    assert "extra" in variant.inputs, (
        f"'extra' missing from variant.inputs: {variant.inputs}"
    )
    assert "x" in variant.inputs, (
        f"original input 'x' missing from variant.inputs: {variant.inputs}"
    )


# ── Structural ────────────────────────────────────────────────────────────────

def workflowModule_exportsWorkflowAndWorkflowRef():
    import modules.workflows as wf_mod
    assert hasattr(wf_mod, "Workflow"), (
        "modules.workflows must export Workflow"
    )
    assert hasattr(wf_mod, "WorkflowRef"), (
        "modules.workflows must export WorkflowRef"
    )
    assert wf_mod.Workflow is Workflow
    assert wf_mod.WorkflowRef is WorkflowRef


def workflowModule_allListsExactly():
    import modules.workflows as wf_mod
    assert set(wf_mod.__all__) == {"Workflow", "WorkflowRef"}, (
        f"__all__ must list exactly Workflow and WorkflowRef; got {wf_mod.__all__}"
    )
```

---

## 6. Commit Plan

**Executor instruction**: run each commit command as soon as the corresponding step completes. Do not batch commits at the end.

**1. `feat(workflows): scaffold workflows package`** — after Step 1 — files: `modules/workflows/__init__.py`, `modules/workflows/workflow.py` (placeholder), `modules/workflows/tests/__init__.py`

```bash
git add modules/workflows/__init__.py \
        modules/workflows/workflow.py \
        modules/workflows/tests/__init__.py
git commit -m "$(cat <<'EOF'
feat(workflows): scaffold workflows package

Adds modules/workflows/ package skeleton and empty test anchor.
Layer C of the Workflow domain layer (architecture.md §Layer C).
EOF
)"
```

**2. `feat(workflows): add WorkflowRef identifier type`** — after Step 2 — file: `modules/workflows/workflow.py` (WorkflowRef only)

```bash
git add modules/workflows/workflow.py
git commit -m "$(cat <<'EOF'
feat(workflows): add WorkflowRef identifier type

WorkflowRef is a frozen dataclass identifier that external callers
(route handlers, WorkflowExecution) hold in place of the full aggregate.
Validates non-empty name; provides __str__ and __repr__.
EOF
)"
```

**3. `feat(workflows): add Workflow aggregate and fluent builder`** — after Steps 3 + 4 — files: `modules/workflows/workflow.py` (complete), `modules/workflows/__init__.py` (wired)

```bash
git add modules/workflows/workflow.py \
        modules/workflows/__init__.py
git commit -m "$(cat <<'EOF'
feat(workflows): add Workflow aggregate and fluent builder

WorkflowBuilder (ELA Pattern #1) is the sole construction path.
Workflow (ELA Pattern #20) is a frozen aggregate with ref, inputs,
outputs, and an ordered steps tuple. to_builder() enables variation
without mutation. build() fails fast with a message listing all
unmet invariants.

Port budget: Workflow, WorkflowBuilder, WorkflowRef only.
JSON schema and WorkflowRuntime are deferred (Phase 3 / Task 4).
EOF
)"
```

**4. `test(workflows): add Workflow and WorkflowRef test suite`** — after Step 5 — file: `modules/workflows/tests/test_workflow.py`

```bash
git add modules/workflows/tests/test_workflow.py
git commit -m "$(cat <<'EOF'
test(workflows): add Workflow and WorkflowRef test suite

30 tests covering: WorkflowRef immutability and equality,
builder fluent API and chaining, build() invariant validation,
Workflow frozen aggregate properties, to_builder() variation
isolation, and public __all__ export shape.

Uses a NoopStep(AbstractStep) test fixture from Task 1.1 — no step internals are inspected.
EOF
)"
```

**Deviation logging**: if any step deviates, prefix the commit body with `Deviations:` and one line per deviation before the `Co-Authored-By` line.

---

## 7. Verification

```bash
# From {WORKSPACE}
python -m pytest modules/workflows/tests/ -v          # 30 new tests; all green
make test                                              # Full suite; 0 pre-existing tests broken
```

**Expected delta**: `<baseline>` → `<baseline + 30>` passing. The delta is exactly 30 — the new test file introduces no parametrize multipliers, no class-based groupings, and no conftest additions.

---

## 8. Rollback

**Per-step**: each of the four commits is independently revertible:
```bash
git revert <sha>   # generates a new revert commit; safe on any branch
```

**Per-branch**: if verification fails catastrophically after all four commits:
```bash
git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destroys uncommitted work
# or delete the feature branch entirely if working on one:
git checkout main
git branch -D feature/task-2-workflow-container   # [REQUIRES APPROVAL]
```

Identify `<pre-task-sha>` from `git log --oneline` before starting: it is the commit immediately before commit 1 above.

---

## 9. Deviations Allowed

- **Prescribed path `modules/workflows/` already exists**: stop, inspect contents, reconcile with what was already merged before continuing. Do not overwrite silently.
- **`frozen=True` dataclass incompatibility with Python version**: if `__post_init__` cannot validate on a frozen dataclass due to interpreter version, switch to `__init_subclass__` guard or a `@classmethod` factory — log in commit body.
- **Test framework mismatch** (e.g., `python_functions` config differs): match whatever convention the repo's `pyproject.toml` declares at the time; translate function-naming style silently and note in commit body.
- **Step 3 + Step 4 ordering conflict** (builder references `Workflow` before it is defined): Python forward references in type hints are handled by `from __future__ import annotations`; if that import is already present and still fails, use string literals for the return type annotation — `-> "Workflow"`.
- **Side-effect required** (push, publish, schema migration): STOP, mark `[REQUIRES APPROVAL]`, and do not proceed.
- **Step N unlocks a simplification for Step N+1**: take it, log as a deviation in the commit body.

---

## 10. Out of Scope

This task delivers exactly the three objects named in the epic's port budget — `Workflow`, `WorkflowBuilder`, and `WorkflowRef` — and nothing else. Eager executors will notice that the `Workflow.steps` tuple is accessible and may be tempted to add iteration helpers, a `get_step()` method, or a validation hook. None of those belong here. The workflow layer is not wired into any route handler, registered with any blueprint, or serialised to any format in this task.

- **`AbstractStep`** — Task 1.1; this task imports it for the `NoopStep` test fixture
- **`AICall`, `Compute`** — Task 1.2; not consumed here, only produced for downstream tasks
- **`WorkflowRuntime`** — Layer D (Task 4); the authorised consumer of `Workflow.steps`; not in scope here
- **`WorkflowRepository` and `WorkflowRepositoryFs`** — Layer E (Task 5); filesystem loading and the bounded-context per-feature `workflows/` subdirectory structure belong to Task 5
- **JSON workflow schema and JSON loader** — Phase 3; explicitly excluded by the architecture; do not add a `to_dict()`, `from_dict()`, or Pydantic model here
- **`WorkflowExecution` command and status state machine** — Layer D (Task 4); `WorkflowRef` is used by `WorkflowExecution` but `WorkflowExecution` itself is Task 4's output
- **Registration in `create_app.py` `ENABLED_MODULES`** — `modules.workflows` has no blueprint and must not appear there
- **Decorator step wrappers** (`RetryStep`, `LoggedStep`) — Phase 2; the Step foundation must be stable first

**Rule for the executor**: if a change appears helpful but appears in the list above, STOP and flag it as a deviation rather than absorbing it into this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Layer C design rationale, Aggregate Root and Builder pattern decisions
- [Epic](./epic.md) – Full task scope, success criteria, and explicit non-goals
- [Timeline](./timeline.md) – Status tracking (mark Task 2 complete after `make test` passes)