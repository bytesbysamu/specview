# Task 2: Scaffold 4-Package Directory Structure

## 1. Context

Task 2 is purely additive: it creates the 11 new Python package directories (with `__init__.py` stubs) that the subsequent file-move step (Task 3) will populate. Without these packages on disk first, Task 3's moves would land in unregistered directories that Python cannot import. By separating scaffold from move, there is a clean checkpoint between them — `make test` must pass before and after this task, with all 10 existing flat modules untouched. This task is the lowest-risk step in the restructure epic; it changes no imports, no logic, and no routes.

**Trade-offs considered:**
- **Create directories inside Task 3 (combined scaffold + move)** — rejected because it collapses the only safe pause point; a mid-move interrupt leaves imports broken with no clean revert.
- **Generate all `__init__.py` files with a shell one-liner** — rejected because a single commit per logical package group makes per-step revert surgical; a one-shot shell script is harder to audit in the diff.
- **Pure scaffold + docstring stubs, no tests this task** — superseded: a one-function structural assertion added to the existing `test_structural.py` provides a green-light signal before Task 3 begins and costs zero setup (same pytest run, same fixture pattern).

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/spec-doc/api

git status                               # flag unrelated M/?? entries
git diff HEAD -- modules/ tests/         # confirm target areas are clean
python -m pytest --tb=short -q          # record baseline; expect 624 passed, 1 skipped
```

**If the working tree is dirty on `modules/` or `tests/`**: stash or commit those changes separately before continuing.

**Baseline recorded**: 624 / 624 passing (1 skipped).

---

## 3. Files

### To Create (new)

- `api/modules/runtime/__init__.py` — top-level `runtime/` package marker; no exports until Task 3
- `api/modules/runtime/chain/__init__.py` — sub-package placeholder for `chain/` contents arriving in Task 3
- `api/modules/runtime/workflows/__init__.py` — sub-package placeholder for `workflows/` contents arriving in Task 3
- `api/modules/data/__init__.py` — top-level `data/` package marker
- `api/modules/data/projects/__init__.py` — sub-package placeholder for `projects/` contents
- `api/modules/data/context/__init__.py` — sub-package placeholder for `context/` contents
- `api/modules/data/templates/__init__.py` — sub-package placeholder for `templates/` contents
- `api/modules/ai/routes/__init__.py` — sub-package placeholder for `ai/routes.py` breakout
- `api/modules/ai/services/__init__.py` — sub-package placeholder for extracted service layer
- `api/modules/ai/workflows/__init__.py` — sub-package placeholder for AI-domain workflow definitions
- `api/modules/ai/workflows/spec_gen/__init__.py` — nested placeholder for `generate_spec.py` arriving in Task 3

### To Modify (cite CODEBASE CONTEXT)

- `api/tests/test_structural.py` — currently 6 structural assertions (~161 lines); add one new function `newPackages_areScaffolded` that imports all 11 new packages and asserts each is reachable.

### To Leave Alone

- `api/modules/ai/__init__.py` — existing package root; sub-packages are additive, parent untouched
- `api/modules/ai/prompts/__init__.py` — already exists; `ai/prompts/` is already scaffolded (confirmed by codebase inspection)
- `api/modules/chain/` — flat module stays in place until Task 3
- `api/modules/context/` — flat module stays in place until Task 3
- `api/modules/projects/` — flat module stays in place until Task 3
- `api/modules/templates/` — flat module stays in place until Task 3
- `api/modules/workflows/` — flat module stays in place until Task 3 (already has `steps/` and `repository/` sub-packages)
- `api/modules/quality/` — already a top-level peer module; zero changes this task or any task in this epic
- `api/modules/spec_gen/` — flat module stays in place until Task 3
- `api/modules/task_gen/` — flat module stays in place until Task 3
- `api/modules/implementation_guide/` — flat module stays in place until Task 3
- `api/openapi.yaml`, `api/dtos/models.py`, `api/create_app.py` — contract and factory; not touched this task

---

## 4. Implementation Steps

### Step 1: Create `runtime/` package tree

**Action**: Create three `__init__.py` stubs that establish `modules.runtime`, `modules.runtime.chain`, and `modules.runtime.workflows` as importable Python packages.

**Files**: `api/modules/runtime/__init__.py`, `api/modules/runtime/chain/__init__.py`, `api/modules/runtime/workflows/__init__.py` (all new)

**Pattern**:
```python
# api/modules/runtime/__init__.py
"""runtime — execution infrastructure (chain adapter + workflow engine).

Populated in Task 3 (file moves from modules/chain/ and modules/workflows/).
"""
```

```python
# api/modules/runtime/chain/__init__.py
"""runtime.chain — AI provider adapter boundary.

Populated in Task 3 (file moves from modules/chain/).
"""
```

```python
# api/modules/runtime/workflows/__init__.py
"""runtime.workflows — WorkflowRuntime execution engine.

Populated in Task 3 (file moves from modules/workflows/).
"""
```

**Verify**:
```bash
cd {WORKSPACE}/spec-doc/api
python -c "import modules.runtime; import modules.runtime.chain; import modules.runtime.workflows; print('runtime OK')"
```
Expect: `runtime OK` with no `ModuleNotFoundError`.

---

### Step 2: Create `data/` package tree

**Action**: Create four `__init__.py` stubs that establish `modules.data` and its three sub-packages as importable Python packages.

**Files**: `api/modules/data/__init__.py`, `api/modules/data/projects/__init__.py`, `api/modules/data/context/__init__.py`, `api/modules/data/templates/__init__.py` (all new)

**Pattern**:
```python
# api/modules/data/__init__.py
"""data — filesystem-backed storage and content retrieval.

Populated in Task 3 (file moves from modules/projects/, modules/context/, modules/templates/).
"""
```

```python
# api/modules/data/projects/__init__.py
"""data.projects — project CRUD and file read/write.

Populated in Task 3 (file moves from modules/projects/).
"""
```

```python
# api/modules/data/context/__init__.py
"""data.context — builder context file read/write (builder.md, principles.md, etc.).

Populated in Task 3 (file moves from modules/context/).
"""
```

```python
# api/modules/data/templates/__init__.py
"""data.templates — deterministic template generators (spec-index, timeline, README).

Populated in Task 3 (file moves from modules/templates/).
"""
```

**Verify**:
```bash
python -c "import modules.data; import modules.data.projects; import modules.data.context; import modules.data.templates; print('data OK')"
```
Expect: `data OK` with no errors.

---

### Step 3: Create `ai/` sub-packages

**Action**: Create four `__init__.py` stubs that add `routes/`, `services/`, `workflows/`, and `workflows/spec_gen/` as sub-packages of the existing `modules.ai` package. Note that `modules/ai/prompts/` already exists — do not create it.

**Files**: `api/modules/ai/routes/__init__.py`, `api/modules/ai/services/__init__.py`, `api/modules/ai/workflows/__init__.py`, `api/modules/ai/workflows/spec_gen/__init__.py` (all new)

**Pattern**:
```python
# api/modules/ai/routes/__init__.py
"""ai.routes — HTTP route handlers for all AI generation endpoints.

Populated in Task 3 (split from modules/ai/routes.py, modules/spec_gen/routes.py, modules/task_gen/routes.py).
"""
```

```python
# api/modules/ai/services/__init__.py
"""ai.services — pure business logic for AI generation (no Flask imports).

Populated in Task 3 (split from modules/spec_gen/service.py, modules/task_gen/service.py).
"""
```

```python
# api/modules/ai/workflows/__init__.py
"""ai.workflows — AI-domain Workflow definitions (consumes runtime.workflows engine).

Populated in Task 3 (moves from modules/spec_gen/workflows/).
"""
```

```python
# api/modules/ai/workflows/spec_gen/__init__.py
"""ai.workflows.spec_gen — Workflow definition for spec generation pipeline.

Populated in Task 3 (file moves from modules/spec_gen/workflows/).
"""
```

**Verify**:
```bash
python -c "
import modules.ai.routes
import modules.ai.services
import modules.ai.workflows
import modules.ai.workflows.spec_gen
print('ai sub-packages OK')
"
```
Expect: `ai sub-packages OK` with no errors.

---

### Step 4: Add scaffold verification test

**Action**: Append one new test function to `api/tests/test_structural.py` that asserts all 11 new packages are importable. Match the file's existing snake-case function naming convention (no class wrapper, plain `assert` statements).

**File**: `api/tests/test_structural.py` (cited from CODEBASE CONTEXT — `tests/` directory)

**Pattern**:
```python
def newPackages_areScaffolded():
    """Task 2 scaffold: all destination packages exist before any files move."""
    import importlib

    new_packages = [
        "modules.runtime",
        "modules.runtime.chain",
        "modules.runtime.workflows",
        "modules.data",
        "modules.data.projects",
        "modules.data.context",
        "modules.data.templates",
        "modules.ai.routes",
        "modules.ai.services",
        "modules.ai.workflows",
        "modules.ai.workflows.spec_gen",
    ]
    for pkg in new_packages:
        mod = importlib.import_module(pkg)
        assert mod is not None, f"Package '{pkg}' could not be imported — __init__.py missing"
```

**Verify**:
```bash
python -m pytest tests/test_structural.py -v
```
Expect: all prior structural tests pass **plus** `newPackages_areScaffolded` appears as PASSED. Count goes from 6 to 7 functions in that file.

---

## 5. Tests

Add the following to `api/tests/test_structural.py`. Framework: plain pytest (no class, no fixtures — matches existing file convention confirmed by inspection).

```python
def newPackages_areScaffolded():
    """Task 2 scaffold: all destination packages exist before any files move.

    Each assertion verifies that the corresponding __init__.py was created and
    Python can resolve the package via normal import machinery. This test is
    intentionally forward-looking: the packages are empty stubs until Task 3
    (file moves) populates them. Task 5 supersedes this check with the full
    hierarchy assertion.
    """
    import importlib

    new_packages = [
        "modules.runtime",
        "modules.runtime.chain",
        "modules.runtime.workflows",
        "modules.data",
        "modules.data.projects",
        "modules.data.context",
        "modules.data.templates",
        "modules.ai.routes",
        "modules.ai.services",
        "modules.ai.workflows",
        "modules.ai.workflows.spec_gen",
    ]
    for pkg in new_packages:
        try:
            mod = importlib.import_module(pkg)
        except ModuleNotFoundError as exc:
            raise AssertionError(
                f"Package '{pkg}' not importable — __init__.py missing or misplaced. "
                f"Original error: {exc}"
            )
        assert mod is not None, f"importlib returned None for '{pkg}' — unexpected"
```

---

## 6. Commit Plan

**Executor instruction**: run each commit immediately after its corresponding step completes — not batched at the end.

1. `chore(scaffold): add runtime/ package tree` — after **Step 1** — files: `api/modules/runtime/__init__.py`, `api/modules/runtime/chain/__init__.py`, `api/modules/runtime/workflows/__init__.py`

2. `chore(scaffold): add data/ package tree` — after **Step 2** — files: `api/modules/data/__init__.py`, `api/modules/data/projects/__init__.py`, `api/modules/data/context/__init__.py`, `api/modules/data/templates/__init__.py`

3. `chore(scaffold): add ai/ sub-packages (routes, services, workflows)` — after **Step 3** — files: `api/modules/ai/routes/__init__.py`, `api/modules/ai/services/__init__.py`, `api/modules/ai/workflows/__init__.py`, `api/modules/ai/workflows/spec_gen/__init__.py`

4. `test(scaffold): assert all 11 new packages are importable` — after **Step 4** (tests passing) — files: `api/tests/test_structural.py`

**Deviation logging**: if any step deviates from this guide, prefix that commit's body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api
make test
```

**Expected delta**: 624 → 625 passing (1 new `newPackages_areScaffolded` function; 0 pre-existing tests broken; 1 skipped count unchanged).

Run `make check-dtos` as a secondary confirmation that the DTO layer was not disturbed:
```bash
make check-dtos
```
Expect: exit code 0 (no diff).

---

## 8. Rollback

- **Per-step**: each of the 4 commits is independently revertible with `git revert <sha>`. Reverting commit 1 (runtime tree) does not affect commits 2–4. Reverting commit 4 (test) removes the assertion without touching any package files.
- **Per-branch**: if verification fails catastrophically (e.g., a stray file was introduced that breaks an existing import), reset to the pre-task SHA:
  ```bash
  git reset --hard <sha-before-step-1>  # destroys all 4 commits; working tree clean
  ```
  Because this task is purely additive, `git reset --hard` here loses only new `__init__.py` stubs and the new test function — no existing file is modified.

---

## 9. Deviations Allowed

- **`api/modules/ai/prompts/` listed in the epic but already exists** → confirmed by codebase inspection; skip creation silently, note `ai/prompts already present` in commit 3 body.
- **`test_structural.py` uses a class-based structure in reality** → translate `newPackages_areScaffolded` to a method inside the existing class; keep the assertion body verbatim; note in commit 4 body.
- **Python cannot import `modules.*` from `api/` without path setup** → if the verify commands in Steps 1–3 fail with `ModuleNotFoundError: No module named 'modules'`, run them as `PYTHONPATH=. python -c "..."` from inside `api/`; the `conftest.py` adds the parent dir to `sys.path` automatically during pytest, so Step 4's verify command is unaffected.
- **Side-effect required** (push to remote) → [REQUIRES APPROVAL] — stop and ask before running `git push`.

---

## 10. Out of Scope

This task creates empty package containers only. It does not move, rename, or rewrite any existing source file, and it does not change any import path, Blueprint registration, or route URL. Any change beyond `__init__.py` creation and the one structural test function is out of scope and must be deferred to the task listed below.

- **File moves** (`modules/chain/` → `modules/runtime/chain/`, etc.) — deferred to Task 3; moves before scaffold is complete leave imports broken with no safe checkpoint.
- **Import-path rewrites** (`from modules.chain` → `from modules.runtime.chain`) — deferred to Task 4; rewriting before files are moved produces `ModuleNotFoundError` throughout the test suite.
- **`ENABLED_MODULES` update in `create_app.py`** — deferred to Task 4; Blueprint registrations must not be touched while the source files still live at their original paths.
- **`packages_areInExpectedHierarchy` structural test** — deferred to Task 5; that test encodes the `saas_optional` allowlist decision which is resolved in Task 1 and encoded only after the full restructure is complete.
- **`runtime/chain/providers/__init__.py`** — not in the epic's Task 2 scope; `providers/` already exists under the current flat `modules/chain/`; its destination scaffold is created as part of the Task 3 file-move operation for that subtree.
- **`quality/` scaffold** — already exists at `modules/quality/` (confirmed by codebase inspection); no action required in any task of this epic.

**Rule for the executor**: if a change appears helpful but is listed here, stop and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for the 4-package hierarchy
- [Epic](./epic.md) — Full task scope and port budget
- [Timeline](./timeline.md) — Update status to `done` after `make test` passes