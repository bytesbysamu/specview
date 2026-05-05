# Task 4: WorkflowRepository (FS Adapter)

## 1. Context

This task delivers Layer E of the five-layer workflow architecture: the `WorkflowRepository` port and its `WorkflowRepositoryFs` filesystem adapter. Feature routes and the `WorkflowRuntime` from Tasks 1–3 need to load named `Workflow` objects without knowing where they live or how they are stored; the port supplies that abstraction boundary. The FS adapter satisfies it by walking `modules/<feature>/workflows/*.py` at app startup, importing each file, and calling its `register_workflows(repo)` function — adding workflows under qualified names like `spec_gen/generate-spec`. This keeps per-feature ownership intact (each feature's definitions live inside its own subdirectory) while giving the runtime a single-call entry point: `repo.get("spec_gen/generate-spec")`. The Bounded Context constraint — no feature routes may traverse `workflows/` directories directly — is sealed with a structural test that mirrors the existing `featureModules_mustNotImportProvidersDirectly` guardrail in `test_structural.py`.

**Trade-offs considered:**
- **Module-level import side effects (auto-registration on import)** — rejected because it couples the registration lifecycle to Python's module import order, making the walk implicit and the startup sequence untestable in isolation.
- **Central `WORKFLOWS` registry dict in `create_app.py`** — rejected because it violates the per-feature ownership Bounded Context; a central dict requires a central edit whenever a new feature adds a workflow.
- **`register_workflows(repo)` convention per workflow file** — preferred because the startup walk is explicit (scannable, testable, grep-able), the registration call is the only interface contract a feature workflow file must satisfy, and the FS adapter can be replaced by `WorkflowRepositoryDb` without changing any feature workflow file.

---

## 2. Pre-flight

All commands run from `{WORKSPACE}/spec-doc/api/`.

```bash
# 1. Confirm clean working tree (flag any unrelated M/?? before starting)
git status

# 2. Confirm target files are untouched
git diff HEAD -- modules/workflows/ create_app.py tests/test_structural.py

# 3. Verify Tasks 1–3 shipped the workflows package (prerequisite)
#    If this command returns nothing, STOP — Tasks 1–3 must complete first.
ls modules/workflows/__init__.py 2>/dev/null && echo "OK" || echo "MISSING — Tasks 1-3 required"

# 4. Record baseline test count (substitute actual N into Verification section)
python -m pytest --co -q 2>/dev/null | tail -1
```

**If working tree is dirty on target files**: stash or commit unrelated changes before continuing.

**If `modules/workflows/__init__.py` is missing**: see Step 1 — the guide creates a minimal package marker as a permitted side effect of Task 4. Record this as a deviation in the commit body.

**Baseline recorded**: [N] collected before this task starts.

---

## 3. Files

### To Create (new)

- `modules/workflows/__init__.py` — package marker; required if Tasks 1–3 have not yet run; safe to create even if the file already exists (idempotent empty init)
- `modules/workflows/repository/__init__.py` — `WorkflowRepository` ABC port + `WorkflowNotFound` error; the only legal import path for consumers
- `modules/workflows/repository/fs_adapter.py` — `WorkflowRepositoryFs` concrete adapter + `_PrefixedRepo` internal wrapper; imports `importlib.util`, `pathlib.Path`
- `modules/workflows/tests/__init__.py` — test sub-package marker; required if Tasks 1–3 have not created `modules/workflows/tests/`
- `modules/workflows/tests/test_repository.py` — complete pytest suite for the port, adapter, and `_PrefixedRepo`

### To Modify (cite CODEBASE CONTEXT)

- `create_app.py` (lines 41–45, after blueprint registration loop) — add four-line repository init block; attaches `app.workflow_repository` before error handlers; confirmed clean at `{WORKSPACE}/spec-doc/api/create_app.py`
- `tests/test_structural.py` (append after line 46, after `gunicorn_inProdRequirements`) — add `featureModules_mustNotLoadWorkflowsDirectly` bare function; same grep-plus-assert pattern as existing tests; confirmed at `{WORKSPACE}/spec-doc/api/tests/test_structural.py`

### To Leave Alone

- `modules/workflows/workflow.py` (if present from Tasks 1–3) — Workflow aggregate; Task 4 imports it only via `TYPE_CHECKING`; do not edit
- `modules/workflows/step.py`, `execution.py`, `runtime.py`, `events.py` (if present from Tasks 1–3) — domain layer delivered by prior tasks; no changes
- `modules/chain/adapter.py` — the chain adapter boundary; not touched here; cited only as the reference pattern Task 4's structural test mirrors
- `openapi.yaml`, `dtos/models.py` — no new endpoints in this task; do not touch
- `modules/*/routes.py`, `modules/*/service.py` (all existing feature modules) — no route changes until Task 5 (spec_gen migration)

---

## 4. Implementation Steps

### Step 1: Create the `modules/workflows` package marker

**Action**: Create `modules/workflows/__init__.py` if it does not already exist. If Tasks 1–3 have run and the file exists, skip this step and log no deviation.

**File**: `modules/workflows/__init__.py` (new or already present)

**Pattern**:
```python
"""Workflows domain layer.

Layer boundaries (see docs/architecture.md):
  A – chain.adapter  (I/O)
  B – step           (Value Objects)
  C – workflow       (Aggregate)
  D – execution      (Runtime)
  E – repository     (Discovery) ← this package
"""
```

**Verify**: `python -c "import modules.workflows; print('ok')"` — expect `ok` with no import error.

---

### Step 2: Create the `WorkflowRepository` port

**Action**: Create `modules/workflows/repository/__init__.py` with the abstract port class and `WorkflowNotFound` error. Uses `from __future__ import annotations` so `TYPE_CHECKING`-gated imports remain zero-cost at runtime.

**File**: `modules/workflows/repository/__init__.py` (new)

**Pattern**:
```python
"""WorkflowRepository port — ELA hexagonal boundary (Layer E).

INVARIANT: All consumers import from this module only.
           Never import from fs_adapter directly outside the app factory.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Workflow is from Tasks 1–3; not imported at runtime to avoid
    # circular-import risk before that task is complete.
    from modules.workflows.workflow import Workflow


class WorkflowNotFound(Exception):
    """Raised by WorkflowRepository.get() when name has no registered workflow."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Workflow not found: {name!r}")
        self.name = name


class WorkflowRepository(ABC):
    """Port: the only legal access path to workflow definitions.

    Implementors: WorkflowRepositoryFs (Phase 1), WorkflowRepositoryDb (Phase 3+).
    """

    @abstractmethod
    def get(self, name: str) -> "Workflow":
        """Return the Workflow registered under *name*.

        Raises WorkflowNotFound if no workflow is registered under that name.
        Qualified names use the form ``feature/workflow-name``
        (e.g. ``spec_gen/generate-spec``).
        """

    @abstractmethod
    def list(self) -> list[str]:
        """Return a sorted list of all registered qualified workflow names."""

    @abstractmethod
    def save(self, workflow: "Workflow") -> None:
        """Register *workflow* under its name.

        Overwrites any existing registration for the same name.
        Phase 1 callers: _PrefixedRepo (internal to fs_adapter) and tests.
        """
```

**Verify**: `python -c "from modules.workflows.repository import WorkflowRepository, WorkflowNotFound; print('ok')"` — expect `ok`.

---

### Step 3: Create the `WorkflowRepositoryFs` adapter

**Action**: Create `modules/workflows/repository/fs_adapter.py` with `WorkflowRepositoryFs`, the internal `_PrefixedRepo` wrapper, and the `_import_and_register` loader. The startup walk pattern mirrors `chain/providers/` discovery in spirit: scan `modules/*/workflows/[!_]*.py`, import each file, call `register_workflows(prefixed_repo)` if present.

**File**: `modules/workflows/repository/fs_adapter.py` (new)

**Pattern**:
```python
"""WorkflowRepositoryFs — filesystem adapter for WorkflowRepository port.

Startup walk (called once from create_app):
  for each modules/<feature>/workflows/[!_]*.py:
      import file → call register_workflows(_PrefixedRepo(repo, feature))

_PrefixedRepo transparently qualifies workflow names as "feature/workflow.name"
so workflow definition files use plain names (e.g. "generate-spec") and the
repository stores qualified names (e.g. "spec_gen/generate-spec").
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from modules.workflows.repository import WorkflowNotFound, WorkflowRepository


class WorkflowRepositoryFs(WorkflowRepository):
    """In-process, dict-backed workflow registry. Populated at startup by from_modules_dir()."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    # ── Port implementation ────────────────────────────────────────────────

    def get(self, name: str) -> object:
        if name not in self._store:
            raise WorkflowNotFound(name)
        return self._store[name]

    def list(self) -> list[str]:
        return sorted(self._store)

    def save(self, workflow: object) -> None:
        self._store[workflow.name] = workflow  # type: ignore[attr-defined]

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def from_modules_dir(cls, modules_dir: Path) -> WorkflowRepositoryFs:
        """Walk modules_dir/*/workflows/[!_]*.py and register all workflows.

        Skips files whose name begins with '_' (e.g. __init__.py).
        Skips feature subdirectories that have no workflows/ directory.
        Skips Python files that define no register_workflows() function.
        """
        repo = cls()
        for workflows_dir in sorted(modules_dir.glob("*/workflows")):
            if not workflows_dir.is_dir():
                continue
            feature = workflows_dir.parent.name
            prefixed = _PrefixedRepo(repo, feature)
            for py_file in sorted(workflows_dir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                _import_and_register(py_file, feature, prefixed)
        return repo


# ── Internal helpers ───────────────────────────────────────────────────────

def _import_and_register(
    py_file: Path,
    feature: str,
    repo: WorkflowRepository,
) -> None:
    """Import py_file and call register_workflows(repo) if the function exists."""
    module_name = f"_workflow_def_{feature}_{py_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, py_file)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load workflow definition file {py_file}: {exc}"
        ) from exc
    if callable(getattr(mod, "register_workflows", None)):
        mod.register_workflows(repo)


class _PrefixedRepo(WorkflowRepository):
    """Internal adapter that qualifies workflow names with a feature prefix.

    Workflow files call repo.save(workflow) using plain names like "generate-spec";
    _PrefixedRepo stores and retrieves them under "feature/generate-spec".
    """

    def __init__(self, delegate: WorkflowRepositoryFs, feature: str) -> None:
        self._delegate = delegate
        self._feature = feature

    def get(self, name: str) -> object:
        return self._delegate.get(f"{self._feature}/{name}")

    def list(self) -> list[str]:
        prefix = f"{self._feature}/"
        return [n[len(prefix):] for n in self._delegate.list() if n.startswith(prefix)]

    def save(self, workflow: object) -> None:
        qualified = f"{self._feature}/{workflow.name}"  # type: ignore[attr-defined]
        self._delegate._store[qualified] = workflow
```

**Verify**:
```bash
python -c "
from pathlib import Path
from modules.workflows.repository.fs_adapter import WorkflowRepositoryFs
repo = WorkflowRepositoryFs()
print('list:', repo.list())          # []
print('ok')
"
```
Expect `list: []` then `ok`.

---

### Step 4: Wire `WorkflowRepositoryFs` into the app factory

**Action**: Add four lines to `create_app.py` immediately after the blueprint registration loop (after line 44 `app.register_blueprint(bp)`) and before the `@app.get('/health')` decorator. This attaches `app.workflow_repository` to the Flask app instance at startup.

**File**: `create_app.py` (modify — confirmed at lines 41–46)

**Pattern** (exact edit — replace the gap between the `for` loop and `@app.get('/health')`):
```python
    for module_path, blueprint_attr in ENABLED_MODULES:
        module = importlib.import_module(module_path)
        bp = getattr(module, blueprint_attr)
        app.register_blueprint(bp)

    from pathlib import Path
    from modules.workflows.repository.fs_adapter import WorkflowRepositoryFs
    app.workflow_repository = WorkflowRepositoryFs.from_modules_dir(
        Path(__file__).parent / "modules"
    )

    @app.get('/health')
```

**Verify**:
```bash
python -c "
from create_app import create_app
app = create_app({'TESTING': True})
from modules.workflows.repository import WorkflowRepository
assert isinstance(app.workflow_repository, WorkflowRepository), 'wrong type'
print('ok — workflow_repository attached:', type(app.workflow_repository).__name__)
"
```
Expect `ok — workflow_repository attached: WorkflowRepositoryFs`.

---

### Step 5: Add structural test

**Action**: Append `featureModules_mustNotLoadWorkflowsDirectly` to `tests/test_structural.py`. Same shape as existing tests: one bare function (collected by pytest via `python_functions = ["*_*"]`), one grep pass over `modules/`, one assertion, failure message names the rule and fix.

**File**: `tests/test_structural.py` (append after line 46)

**Pattern**:
```python
def featureModules_mustNotLoadWorkflowsDirectly():
    """Only WorkflowRepositoryFs may glob workflow directories or importlib-load
    workflow definition files. Feature code must call WorkflowRepository.get()
    or .list() instead.

    Rule: the two specific patterns below are only legal inside
          modules/workflows/repository/fs_adapter.py.
    Fix:  Remove direct filesystem access to */workflows/ paths; inject or
          look up a WorkflowRepository instance instead.
    """
    import re

    adapter_path = "modules/workflows/repository/fs_adapter.py"
    violations = []
    for py_file in sorted((_REPO_ROOT / "modules").rglob("*.py")):
        rel = str(py_file.relative_to(_REPO_ROOT))
        if rel == adapter_path:
            continue
        text = py_file.read_text(encoding="utf-8")
        # Pattern A: .glob("*/workflows") — the startup directory walk
        if re.search(r'\.glob\s*\(\s*["\'][^"\']*\*/workflows', text):
            violations.append(f"{rel}: glob on */workflows pattern")
            continue
        # Pattern B: spec_from_file_location in a file that also mentions workflows
        if re.search(r'\bspec_from_file_location\b', text) and "workflows" in text:
            violations.append(f"{rel}: importlib load of workflow file")

    assert not violations, (
        "featureModules_mustNotLoadWorkflowsDirectly violated.\n"
        "Only fs_adapter.py may discover or importlib-load workflow definition files.\n"
        "Feature code must use WorkflowRepository.get() or .list():\n"
        + "\n".join(f"  {v}" for v in violations)
    )
```

**Verify**: `python -m pytest tests/test_structural.py -v` — all three structural tests pass, including the new one.

---

### Step 6: Create the test sub-package and test suite

**Action**: Create `modules/workflows/tests/__init__.py` (empty, package marker) if it does not already exist from Tasks 1–3. Then create `modules/workflows/tests/test_repository.py` with the complete test suite. Tests use a `_StubWorkflow` dataclass so they are independent of the Task 1–3 `Workflow` implementation.

**File**: `modules/workflows/tests/__init__.py` (new or already present — idempotent empty init)

**File**: `modules/workflows/tests/test_repository.py` (new — see Section 5 for full content)

**Verify**: `python -m pytest modules/workflows/tests/test_repository.py -v` — all new tests pass, zero failures.

---

## 5. Tests

**Framework**: pytest with `python_functions = ["test_*", "*_*"]`; `testpaths = ["tests", "modules"]`; `pythonpath = ["."]`. All test methods use `test_` prefix inside classes (consistent with `test_project.py`). The `app` fixture and `spec_doc_dir` autouse fixture from `tests/conftest.py` are available.

**File**: `modules/workflows/tests/test_repository.py`

```python
"""Tests for WorkflowRepository port and WorkflowRepositoryFs adapter.

Uses _StubWorkflow (a plain dataclass) so these tests are independent of the
Workflow aggregate from Tasks 1–3.
"""
import pytest
from dataclasses import dataclass
from pathlib import Path

from modules.workflows.repository import WorkflowNotFound, WorkflowRepository
from modules.workflows.repository.fs_adapter import WorkflowRepositoryFs, _PrefixedRepo


# ── Minimal stub — no dependency on Task 1–3 Workflow implementation ──────────

@dataclass
class _StubWorkflow:
    """Stand-in for the Workflow aggregate: satisfies workflow.name contract."""
    name: str


# ── WorkflowNotFound ──────────────────────────────────────────────────────────

class TestWorkflowNotFound:
    def test_carries_name_attribute(self):
        exc = WorkflowNotFound("spec_gen/generate-spec")
        assert exc.name == "spec_gen/generate-spec", (
            "WorkflowNotFound.name must equal the argument passed to __init__"
        )

    def test_message_includes_name(self):
        exc = WorkflowNotFound("spec_gen/generate-spec")
        assert "spec_gen/generate-spec" in str(exc), (
            "WorkflowNotFound.__str__ must contain the missing workflow name"
        )


# ── Port is abstract ──────────────────────────────────────────────────────────

class TestWorkflowRepository_isAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            WorkflowRepository()  # type: ignore[abstract]


# ── WorkflowRepositoryFs.save ─────────────────────────────────────────────────

class TestWorkflowRepositoryFs_save:
    def test_storePersists_underWorkflowName(self):
        repo = WorkflowRepositoryFs()
        wf = _StubWorkflow(name="alpha")
        repo.save(wf)
        assert repo.get("alpha") is wf, (
            "save() must make the workflow retrievable by its .name"
        )

    def test_secondSave_overwritesFirst(self):
        repo = WorkflowRepositoryFs()
        wf1 = _StubWorkflow(name="alpha")
        wf2 = _StubWorkflow(name="alpha")
        repo.save(wf1)
        repo.save(wf2)
        assert repo.get("alpha") is wf2, (
            "second save() with the same name must overwrite the first"
        )


# ── WorkflowRepositoryFs.get ──────────────────────────────────────────────────

class TestWorkflowRepositoryFs_get:
    def test_knownName_returnsSavedInstance(self):
        repo = WorkflowRepositoryFs()
        wf = _StubWorkflow(name="bravo")
        repo.save(wf)
        result = repo.get("bravo")
        assert result is wf, "get() must return the exact instance passed to save()"

    def test_unknownName_raisesWorkflowNotFound(self):
        repo = WorkflowRepositoryFs()
        with pytest.raises(WorkflowNotFound) as exc_info:
            repo.get("does-not-exist")
        assert exc_info.value.name == "does-not-exist", (
            "WorkflowNotFound raised by get() must carry the missing name"
        )


# ── WorkflowRepositoryFs.list ─────────────────────────────────────────────────

class TestWorkflowRepositoryFs_list:
    def test_empty_whenNothingSaved(self):
        repo = WorkflowRepositoryFs()
        assert repo.list() == [], "list() on an empty repo must return []"

    def test_returnsSorted_afterMultipleSaves(self):
        repo = WorkflowRepositoryFs()
        for name in ["gamma", "alpha", "beta"]:
            repo.save(_StubWorkflow(name=name))
        assert repo.list() == ["alpha", "beta", "gamma"], (
            "list() must return workflow names in ascending lexicographic order"
        )

    def test_returnsCopy_mutationDoesNotAffectStore(self):
        repo = WorkflowRepositoryFs()
        repo.save(_StubWorkflow(name="x"))
        names = repo.list()
        names.append("injected")
        assert "injected" not in repo.list(), (
            "list() must return a copy; mutating the returned list must not "
            "alter the repository's internal state"
        )


# ── WorkflowRepositoryFs.from_modules_dir ────────────────────────────────────

class TestWorkflowRepositoryFs_fromModulesDir:
    """Each test uses tmp_path so no real modules/ directory is touched."""

    def _write_feature_workflow(self, tmp_path: Path, feature: str, py_name: str, wf_name: str) -> None:
        """Helper: write a minimal workflow definition file under tmp_path/<feature>/workflows/."""
        d = tmp_path / feature / "workflows"
        d.mkdir(parents=True, exist_ok=True)
        (d / py_name).write_text(
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class _W:\n"
            "    name: str\n"
            "def register_workflows(repo):\n"
            f"    repo.save(_W(name={wf_name!r}))\n",
            encoding="utf-8",
        )

    def test_registersWorkflow_fromPythonFile(self, tmp_path: Path):
        self._write_feature_workflow(tmp_path, "my_feature", "gen.py", "generate-spec")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        result = repo.get("my_feature/generate-spec")
        assert result.name == "generate-spec", (
            "from_modules_dir must load the workflow defined in the .py file"
        )

    def test_qualifiesName_withFeaturePrefix(self, tmp_path: Path):
        self._write_feature_workflow(tmp_path, "feat_x", "w.py", "my-wf")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert "feat_x/my-wf" in repo.list(), (
            "from_modules_dir must register workflows under 'feature/workflow-name'"
        )

    def test_skipsDunderFiles(self, tmp_path: Path):
        d = tmp_path / "feat" / "workflows"
        d.mkdir(parents=True)
        (d / "__init__.py").write_text(
            "def register_workflows(repo):\n"
            "    raise RuntimeError('dunder file must not be loaded')\n",
            encoding="utf-8",
        )
        # Must not raise; dunder file must be silently skipped
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert repo.list() == [], "files beginning with '_' must be skipped"

    def test_noop_whenNoWorkflowsDir(self, tmp_path: Path):
        (tmp_path / "no_workflows_here").mkdir()
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert repo.list() == [], (
            "a feature module without a workflows/ directory must be silently skipped"
        )

    def test_noop_whenNoRegisterFunction(self, tmp_path: Path):
        d = tmp_path / "feat" / "workflows"
        d.mkdir(parents=True)
        (d / "constants.py").write_text("ANSWER = 42\n", encoding="utf-8")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert repo.list() == [], (
            "a workflow file without register_workflows() must be silently skipped"
        )

    def test_registersWorkflows_acrossMultipleFeatures(self, tmp_path: Path):
        self._write_feature_workflow(tmp_path, "feat_a", "w.py", "wf-a")
        self._write_feature_workflow(tmp_path, "feat_b", "w.py", "wf-b")
        repo = WorkflowRepositoryFs.from_modules_dir(tmp_path)
        assert "feat_a/wf-a" in repo.list(), "feat_a workflow must be registered"
        assert "feat_b/wf-b" in repo.list(), "feat_b workflow must be registered"
        assert len(repo.list()) == 2, "only the two registered workflows must be present"


# ── _PrefixedRepo ─────────────────────────────────────────────────────────────

class TestPrefixedRepo:
    def test_save_addsFeaturePrefix(self):
        base = WorkflowRepositoryFs()
        prefixed = _PrefixedRepo(base, "my_feature")
        wf = _StubWorkflow(name="wf-1")
        prefixed.save(wf)
        # The base store must hold the qualified name
        retrieved = base.get("my_feature/wf-1")
        assert retrieved is wf, (
            "_PrefixedRepo.save() must store under 'feature/workflow.name' "
            "in the delegate repository"
        )

    def test_get_resolvesWithFeaturePrefix(self):
        base = WorkflowRepositoryFs()
        prefixed = _PrefixedRepo(base, "my_feature")
        wf = _StubWorkflow(name="wf-1")
        prefixed.save(wf)
        result = prefixed.get("wf-1")
        assert result is wf, (
            "_PrefixedRepo.get('wf-1') must resolve to 'my_feature/wf-1' "
            "in the delegate and return the correct instance"
        )

    def test_list_stripsFeaturePrefix(self):
        base = WorkflowRepositoryFs()
        prefixed = _PrefixedRepo(base, "feat")
        prefixed.save(_StubWorkflow(name="alpha"))
        prefixed.save(_StubWorkflow(name="beta"))
        names = prefixed.list()
        assert names == ["alpha", "beta"], (
            "_PrefixedRepo.list() must return plain names without the feature prefix, "
            "sorted ascending; got: " + repr(names)
        )


# ── App factory wiring ────────────────────────────────────────────────────────

def test_createApp_attaches_workflowRepository(app):
    """create_app() must attach a WorkflowRepository instance to app.workflow_repository."""
    from modules.workflows.repository import WorkflowRepository
    assert hasattr(app, "workflow_repository"), (
        "app must have a workflow_repository attribute after create_app()"
    )
    assert isinstance(app.workflow_repository, WorkflowRepository), (
        "app.workflow_repository must be a WorkflowRepository instance; "
        f"got {type(app.workflow_repository)}"
    )
```

---

## 6. Commit Plan

**Executor instruction**: run `git commit` after completing each numbered step above — not at the end. Each commit below corresponds directly to one step.

1. `feat(workflows): create workflows package marker` — after Step 1 — `modules/workflows/__init__.py`: empty package init enabling sub-package imports
2. `feat(workflows/repository): add WorkflowRepository port and WorkflowNotFound` — after Step 2 — `modules/workflows/repository/__init__.py`: ABC port + typed error
3. `feat(workflows/repository): add WorkflowRepositoryFs FS adapter` — after Step 3 — `modules/workflows/repository/fs_adapter.py`: concrete adapter + `_PrefixedRepo` + `_import_and_register`
4. `feat(create_app): register WorkflowRepositoryFs at startup` — after Step 4 — `create_app.py`: four-line block attaches `app.workflow_repository`
5. `test(structural): featureModules_mustNotLoadWorkflowsDirectly` — after Step 5 — `tests/test_structural.py`: new bare function guarding the repository boundary
6. `test(workflows/repository): add complete repository test suite` — after tests pass in Step 6 — `modules/workflows/tests/__init__.py`, `modules/workflows/tests/test_repository.py`: 20 test methods covering port, adapter, prefixed wrapper, and app factory wiring

**Deviation logging**: if any step diverges from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Run from {WORKSPACE}/spec-doc/api/
python -m pytest -v
```

**Expected delta**: N → N+20 passing. Zero pre-existing tests broken.

The 20 new tests break down as:
- `TestWorkflowNotFound`: 2
- `TestWorkflowRepository_isAbstract`: 1
- `TestWorkflowRepositoryFs_save`: 2
- `TestWorkflowRepositoryFs_get`: 2
- `TestWorkflowRepositoryFs_list`: 3
- `TestWorkflowRepositoryFs_fromModulesDir`: 6
- `TestPrefixedRepo`: 3
- `test_createApp_attaches_workflowRepository`: 1
- `featureModules_mustNotLoadWorkflowsDirectly` (structural): 1

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` — Step 4's `create_app.py` change is the only one with runtime impact; reverting it stops the repository from being attached at startup without breaking anything else.
- **Per-branch**: if verification fails catastrophically, record the pre-task SHA from pre-flight (`git log -1 --format=%H`), then `git reset --hard <pre-task-sha>`. If working on a feature branch, `git branch -D <branch-name>` is the cleanest reset.

---

## 9. Deviations Allowed

- **`modules/workflows/` already has a different `__init__.py` from Tasks 1–3** → do not overwrite; skip Step 1, log deviation in commit 1's body; the package already exists and is importable.
- **`modules/workflows/tests/` already exists from Tasks 1–3** → skip creating `__init__.py`; proceed directly to creating `test_repository.py`.
- **`Workflow` class location differs from `modules.workflows.workflow`** → the `TYPE_CHECKING` import in the port is for type checking only; it does not affect runtime. If mypy complains, update the import path to match the actual module — this is a one-line change, not a structural deviation.
- **Step 4's import of `WorkflowRepositoryFs` in `create_app.py` fails** → most likely cause is `modules/workflows/` not yet existing (Tasks 1–3 incomplete); halt and flag [REQUIRES PRIOR TASK COMPLETION] rather than continuing.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log the deviation in the commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL], and ask before proceeding.

---

## 10. Out of Scope

This task installs the port interface, the filesystem adapter, and the startup registration walk — nothing more. It does not validate or exercise the full workflow execution path, and it does not add any HTTP-visible surface. The structural test guards the boundary but does not cover every conceivable bypass; as the codebase grows, the test's pattern set can be widened.

- **`WorkflowRepositoryDb`** — explicitly deferred in the architecture until a multi-user persistence requirement is named; the port makes the swap a binding change, not a rewrite; do not stub it here
- **JSON workflow loader** — Phase 3 work; the `from_modules_dir` walk today only handles `.py` files; JSON file support requires a Pydantic schema driven by the GUI consumer, which is not yet defined
- **HTTP endpoints for repository (`GET /api/workflows`, `GET /api/workflows/<name>`)** — Phase 3; the GUI palette requires `list()` and `get()` over HTTP, but no GUI consumer exists in Phase 1; adding endpoints now would require openapi.yaml and DTO changes outside this task's blast radius
- **`spec_gen` workflow definition file** — Task 5 (spec_gen migration) owns the first real `modules/spec_gen/workflows/*.py` file; this task only delivers the infrastructure that Task 5 will register against
- **Registry for `StepKind` constructors and `Provider` implementations** — mentioned in architecture Layer E; Phase 3 trigger is the JSON loader dispatching on `kind` names; Phase 1 Python workflows use direct type construction and need no registry

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a proposed deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Layer E design and hexagonal boundary rationale
- [Epic](./epic.md) – Task scope, success criteria, and Phase delivery boundaries
- [Timeline](./timeline.md) – Status tracking (mark Task 4 complete after Verification passes)