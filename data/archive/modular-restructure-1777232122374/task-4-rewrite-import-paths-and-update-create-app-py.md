Now I have the real data I need. Let me write the guide.

# Implementation Guide — Task 4: Rewrite Import Paths & Update `create_app.py`

## 1. Context

Task 3 physically relocated 16 source files from the flat `modules/` layout into four named packages (`ai/`, `runtime/`, `data/`, `quality/`). Every cross-module `from modules.X import Y` that crossed a package boundary is now a broken import, and `ENABLED_MODULES` in `create_app.py` still points at the six old dotted paths. This task performs the purely mechanical repair: rewrite all ~50 broken import statements across routes, services, workflow definitions, and test files; update ENABLED_MODULES to the six new paths; and rename the two test files (`spec_gen/tests/test_routes.py`, `task_gen/tests/test_routes.py`) that would collide once both land inside `modules/ai/routes/tests/`. `make test` must return to 624 passing with zero semantic change to any assertion.

**Trade-offs considered:**

- **Automated `sed -i` global replacement** — rejected; a single regex can't distinguish `from modules.chain import X` inside a comment vs live code, and the audit shows multiple distinct prefix patterns that overlap (e.g., `modules.chain` vs `modules.chain.errors` vs `modules.chain.types`); per-file edits are safer and produce a reviewable diff.
- **Single mega-commit for all rewrites** — rejected; a per-category commit boundary (`ENABLED_MODULES` → `chain` → `workflows` → `data` → `ai-internal` → `tests`) makes each failure independently bisectable and matches the commit-per-step rule.
- **Rewrite internal workflow imports as relative imports** — preferred for files entirely within `modules/runtime/workflows/`, as it removes future path-fragility; all other cross-package references remain absolute for explicitness.

---

## 2. Pre-flight

Run from `{WORKSPACE}/api` BEFORE editing any file:

```bash
# Confirm clean branch state
git status
git diff HEAD -- create_app.py

# Capture exact ENABLED_MODULES strings (source of truth)
grep -n "modules\." create_app.py

# Audit: every cross-module absolute import that will be broken after Task 3
grep -rn "^from modules\." modules/ tests/ create_app.py | sort > /tmp/task4_audit.txt
cat /tmp/task4_audit.txt

# Check for test file collisions in merged ai/routes/tests/
ls modules/ai/routes/tests/ 2>/dev/null || echo "dir absent — check Task 3 output"

# Baseline — expect ImportError failures (Task 3 broke these)
make test 2>&1 | tail -30
# Record: which ImportErrors appear so you can confirm each is resolved
```

**If working tree is dirty on target files**: stash unrelated changes before starting.

**Baseline recorded**: Make test is expected to FAIL after Task 3. Record the exact `ImportError` lines printed — each one is a checkbox item for this task.

---

## 3. Files

### To Create (new)

- `api/tests/test_runtime_imports.py` — four smoke-import assertions confirming the new package roots are importable; permanent structural guard

### To Modify (cite CODEBASE CONTEXT — all paths are post-Task 3 locations)

- `api/create_app.py` — ENABLED_MODULES list (6 entries, all need new paths) + line 48 `from modules.workflows.repository.fs_adapter import WorkflowRepositoryFs`
- `api/modules/ai/routes/text.py` — was `modules/ai/routes.py`; imports `modules.chain` and `modules.context.service` and `modules.templates.generators` and `modules.workflows.execution`
- `api/modules/ai/routes/spec_gen.py` — was `modules/spec_gen/routes.py`; imports `modules.context.service` and multiple `modules.workflows.*`
- `api/modules/ai/routes/task_gen.py` — was `modules/task_gen/routes.py`; imports `modules.projects.errors` and `modules.projects.service`
- `api/modules/ai/services/task_gen.py` — was `modules/task_gen/service.py`; imports `modules.chain`, `modules.context.service`, `modules.implementation_guide.prompts`, `modules.projects.service`, `modules.workflows.execution`
- `api/modules/ai/workflows/spec_gen/generate_spec.py` — was `modules/spec_gen/workflows/generate_spec.py`; imports `modules.spec_gen.prompts` and `modules.workflows.steps.*` and `modules.workflows.workflow`
- `api/modules/ai/workflows/spec_gen/bootstrap.py` — was `modules/spec_gen/workflows/bootstrap.py`; imports multiple `modules.workflows.*`
- `api/modules/runtime/workflows/steps/ai_call.py` — was `modules/workflows/steps/ai_call.py`; imports `modules.chain`
- `api/modules/runtime/workflows/runtime.py` — was `modules/workflows/runtime.py`; absolute imports of sibling modules → convert to relative
- `api/modules/runtime/workflows/repository/fs_adapter.py` — was `modules/workflows/repository/fs_adapter.py`; absolute import of sibling → convert to relative
- `api/modules/runtime/workflows/repository/__init__.py` — was `modules/workflows/repository/__init__.py`; absolute import of sibling → convert to relative
- `api/modules/data/projects/service.py` — was `modules/projects/service.py`; imports `modules.templates.generators`
- `api/modules/data/projects/routes.py` — was `modules/projects/routes.py`; imports `modules.quality.coherence` (quality stays flat — verify no-op)
- All test files under `api/modules/*/tests/` that contain `from modules.` references — update to new paths
- `api/modules/ai/routes/tests/test_routes.py` (collision origin) — **rename** to `test_spec_gen_routes.py` or `test_task_gen_routes.py` per Step 6

### To Leave Alone

- `api/openapi.yaml` — contract is path-independent; zero changes
- `api/dtos/models.py` — generated artifact; untouched
- `api/modules/quality/` — already at its final location; imports into quality are `modules.quality.*` and do not change
- Any `__init__.py` stubs scaffolded in Task 2 — already at correct paths; do not re-edit unless they contain broken absolute imports (verify in pre-flight grep output)
- `api/tests/test_structural.py` — Task 5 owns this file; do not add the hierarchy test here

---

## 4. Implementation Steps

### Step 1: Update ENABLED_MODULES and the top-level workflow import in `create_app.py`

**Action**: Replace all six string entries in ENABLED_MODULES and the single `from modules.workflows` import at line 48 with their new paths.

**File**: `api/create_app.py` (CODEBASE CONTEXT — App factory)

**Pattern**:

```python
# BEFORE
ENABLED_MODULES = [
    'modules.projects.routes',   # → projects_bp
    'modules.context.routes',    # → context_bp
    'modules.ai.routes',         # → ai_bp
    'modules.templates.routes',  # → templates_bp
    'modules.task_gen.routes',   # → task_gen_bp
    'modules.spec_gen.routes',   # → spec_gen_bp
]
# line 48
from modules.workflows.repository.fs_adapter import WorkflowRepositoryFs

# AFTER
ENABLED_MODULES = [
    'modules.data.projects.routes',   # → projects_bp
    'modules.data.context.routes',    # → context_bp
    'modules.ai.routes.text',         # → ai_bp
    'modules.data.templates.routes',  # → templates_bp
    'modules.ai.routes.task_gen',     # → task_gen_bp
    'modules.ai.routes.spec_gen',     # → spec_gen_bp
]
# line 48
from modules.runtime.workflows.repository.fs_adapter import WorkflowRepositoryFs
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "
from create_app import create_app
app = create_app()
rules = [str(r) for r in app.url_map.iter_rules()]
print('routes:', len(rules))
assert len(rules) > 5, 'blueprints failed to register'
print('PASS')
"
```
Expect: `routes: N` (N ≥ 20) and `PASS`.

---

### Step 2: Rewrite `modules.chain` → `modules.runtime.chain` imports

**Action**: In every file that imports from `modules.chain`, replace the prefix. Three files are affected; update all in this step.

**Files**:
- `api/modules/ai/routes/text.py`
- `api/modules/ai/services/task_gen.py`
- `api/modules/runtime/workflows/steps/ai_call.py`

**Pattern** (same substitution in all three files):

```python
# BEFORE
from modules.chain import adapter as chain_adapter
from modules.chain.errors import ProviderError
from modules.chain.types import ChainResult

# AFTER
from modules.runtime.chain import adapter as chain_adapter
from modules.runtime.chain.errors import ProviderError
from modules.runtime.chain.types import ChainResult
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "from modules.runtime.chain import adapter as a; print('adapter:', a); print('PASS')"
python -c "from modules.runtime.workflows.steps.ai_call import AICall; print('AICall:', AICall); print('PASS')"
# Confirm no remaining old-path references
grep -rn "from modules\.chain" modules/ tests/ create_app.py && echo "STALE REFERENCES REMAIN" || echo "clean"
```
Expect: both `PASS` lines print; grep reports `clean`.

---

### Step 3: Rewrite `modules.workflows` → `modules.runtime.workflows` imports (cross-package references)

**Action**: Update all absolute cross-package `modules.workflows.*` references. Internal imports *within* `modules/runtime/workflows/` are converted to relative imports to avoid future path-fragility.

**Files** (and which imports change in each):

**`api/modules/ai/routes/text.py`**:
```python
# BEFORE
from modules.workflows.execution import ExecutionStatus, WorkflowExecution
# AFTER
from modules.runtime.workflows.execution import ExecutionStatus, WorkflowExecution
```

**`api/modules/ai/routes/spec_gen.py`**:
```python
# BEFORE
from modules.workflows.execution import WorkflowExecution
from modules.workflows.repository import WorkflowNotFound
from modules.workflows.steps import StepCompleted, StepFailed
# AFTER
from modules.runtime.workflows.execution import WorkflowExecution
from modules.runtime.workflows.repository import WorkflowNotFound
from modules.runtime.workflows.steps import StepCompleted, StepFailed
```

**`api/modules/ai/services/task_gen.py`**:
```python
# BEFORE
from modules.workflows.execution import WorkflowExecution
# AFTER
from modules.runtime.workflows.execution import WorkflowExecution
```

**`api/modules/ai/workflows/spec_gen/generate_spec.py`**:
```python
# BEFORE
from modules.workflows.steps.ai_call import AICall
from modules.workflows.workflow import Workflow
# AFTER
from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.workflow import Workflow
```

**`api/modules/ai/workflows/spec_gen/bootstrap.py`**:
```python
# BEFORE
from modules.workflows.steps import registry as _registry
from modules.workflows.steps.ai_call import AICall
from modules.workflows.steps.base import StepContext
from modules.workflows.steps.compute import Compute
from modules.workflows.workflow import Workflow
# AFTER
from modules.runtime.workflows.steps import registry as _registry
from modules.runtime.workflows.steps.ai_call import AICall
from modules.runtime.workflows.steps.base import StepContext
from modules.runtime.workflows.steps.compute import Compute
from modules.runtime.workflows.workflow import Workflow
```

**`api/modules/runtime/workflows/runtime.py`** — convert to relative:
```python
# BEFORE (absolute)
from modules.workflows.execution import WorkflowExecution
from modules.workflows.steps import StepContext, StepEvent
from modules.workflows.workflow import Workflow
# AFTER (relative — no future path exposure)
from .execution import WorkflowExecution
from .steps import StepContext, StepEvent
from .workflow import Workflow
```

**`api/modules/runtime/workflows/repository/fs_adapter.py`** — convert to relative:
```python
# BEFORE
from modules.workflows.repository import WorkflowNotFound, WorkflowRepository
# AFTER
from . import WorkflowNotFound, WorkflowRepository
```

**`api/modules/runtime/workflows/repository/__init__.py`** — convert to relative:
```python
# BEFORE
from modules.workflows.workflow import Workflow
# AFTER
from ..workflow import Workflow
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "from modules.runtime.workflows import WorkflowRuntime; print('WorkflowRuntime OK')"
python -c "from modules.runtime.workflows.repository.fs_adapter import WorkflowRepositoryFs; print('RepositoryFs OK')"
grep -rn "from modules\.workflows" modules/ tests/ create_app.py && echo "STALE REFERENCES REMAIN" || echo "clean"
```
Expect: both OK lines; grep reports `clean`.

---

### Step 4: Rewrite data-layer imports (`modules.context`, `modules.projects`, `modules.templates`)

**Action**: Replace the three old flat data-module prefixes wherever they appear. Quality is unaffected (stays at `modules.quality`).

**Complete substitution table for this step**:

| Old prefix | New prefix |
|---|---|
| `modules.context.service` | `modules.data.context.service` |
| `modules.projects.service` | `modules.data.projects.service` |
| `modules.projects.errors` | `modules.data.projects.errors` |
| `modules.templates.generators` | `modules.data.templates.generators` |

**Files and changes**:

**`api/modules/ai/routes/text.py`**:
```python
# BEFORE
from modules.context.service import read_context
from modules.templates.generators import generate_spec_index, generate_timeline, generate_readme
# AFTER
from modules.data.context.service import read_context
from modules.data.templates.generators import generate_spec_index, generate_timeline, generate_readme
```

**`api/modules/ai/routes/spec_gen.py`**:
```python
# BEFORE
from modules.context.service import read_context
# AFTER
from modules.data.context.service import read_context
```

**`api/modules/ai/routes/task_gen.py`**:
```python
# BEFORE
from modules.projects.errors import ProjectNotFoundError
from modules.projects.service import get_project
# AFTER
from modules.data.projects.errors import ProjectNotFoundError
from modules.data.projects.service import get_project
```

**`api/modules/ai/services/task_gen.py`**:
```python
# BEFORE
from modules.context.service import read_context
from modules.projects.service import get_project, update_file
# AFTER
from modules.data.context.service import read_context
from modules.data.projects.service import get_project, update_file
```

**`api/modules/data/projects/service.py`** (was `modules/projects/service.py`):
```python
# BEFORE
from modules.templates.generators import generate_spec_index, generate_timeline, generate_readme
# AFTER
from modules.data.templates.generators import generate_spec_index, generate_timeline, generate_readme
```

**`api/modules/data/projects/routes.py`** (was `modules/projects/routes.py`) — verify only, likely no change needed:
```python
# This file imports modules.quality.coherence — quality stays at modules.quality
# Confirm the line reads:
from modules.quality.coherence import lint_capability   # unchanged
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "from modules.data.context.service import read_context; print('context OK')"
python -c "from modules.data.projects.service import get_project; print('projects OK')"
python -c "from modules.data.templates.generators import generate_spec_index; print('templates OK')"
grep -rn "from modules\.\(context\|projects\|templates\)\." modules/ tests/ create_app.py \
  && echo "STALE REFERENCES REMAIN" || echo "clean"
```
Expect: three OK lines; grep reports `clean`.

---

### Step 5: Rewrite AI-internal cross-module imports (`implementation_guide`, `spec_gen.prompts`)

**Action**: Fix two remaining broken import origins that reference old module names that no longer exist as top-level packages.

**Sub-step 5a** — `implementation_guide.prompts` → locate the moved file first:
```bash
# Find where implementation_guide/prompts.py landed after Task 3
find {WORKSPACE}/api/modules/ai -name "*.py" | xargs grep -l "build_implementation_guide_prompt" 2>/dev/null
# Expected: modules/ai/prompts/implementation_guide.py (or similar)
```

**`api/modules/ai/services/task_gen.py`**:
```python
# BEFORE
from modules.implementation_guide.prompts import build_implementation_guide_prompt
# AFTER — use the path confirmed by the find command above
from modules.ai.prompts.implementation_guide import build_implementation_guide_prompt
```

**Sub-step 5b** — `spec_gen.prompts` → locate the moved file:
```bash
# Find where spec_gen/prompts.py landed after Task 3
find {WORKSPACE}/api/modules/ai -name "*.py" | xargs grep -l "def.*spec" 2>/dev/null | grep prompts
```

**`api/modules/ai/workflows/spec_gen/generate_spec.py`**:
```python
# BEFORE
from modules.spec_gen.prompts import build_spec_prompt, build_epic_prompt  # (exact names per file)
# AFTER — use path confirmed above; likely:
from modules.ai.prompts.spec_gen import build_spec_prompt, build_epic_prompt
```

> **Deviation rule**: If the find commands reveal a different path than shown above, use the actual path and log it in the commit body under `Deviations:`. Do NOT invent a path — read what Task 3 produced.

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "
from modules.ai.prompts.implementation_guide import build_implementation_guide_prompt
print('impl_guide prompt OK')
"
python -c "
import importlib, sys
mod = importlib.import_module('modules.ai.workflows.spec_gen.generate_spec')
print('generate_spec workflow OK')
"
grep -rn "from modules\.\(implementation_guide\|spec_gen\)\." modules/ tests/ create_app.py \
  && echo "STALE REFERENCES REMAIN" || echo "clean"
```
Expect: both OK lines; grep reports `clean`.

---

### Step 6: Rewrite test file imports and rename colliding test files

**Action** (part A — detect collisions): Check if two `test_routes.py` files now share `modules/ai/routes/tests/`:
```bash
ls {WORKSPACE}/api/modules/ai/routes/tests/
```
If two files named `test_routes.py` cannot coexist (the second overwrote the first in Task 3), Task 3 may have left one behind. Identify which test subjects are in each file:
```bash
grep -n "^class\|^def test_" {WORKSPACE}/api/modules/ai/routes/tests/test_routes.py
```

**Action** (part B — rename): Rename `test_routes.py` files with descriptive names:
```bash
# If spec_gen route tests are in the colliding file:
git mv {WORKSPACE}/api/modules/ai/routes/tests/test_routes.py \
       {WORKSPACE}/api/modules/ai/routes/tests/test_spec_gen_routes.py

# If task_gen route tests are in a separate surviving file:
git mv {WORKSPACE}/api/modules/ai/routes/tests/test_task_gen_routes.py \
       {WORKSPACE}/api/modules/ai/routes/tests/test_task_gen_routes.py   # already named correctly

# Original ai text routes (if separately preserved):
git mv {WORKSPACE}/api/modules/ai/routes/tests/test_text_routes.py \
       {WORKSPACE}/api/modules/ai/routes/tests/test_text_routes.py       # keep as-is
```

> **Deviation rule**: The exact collision state depends on what Task 3 produced. Read `ls` output; rename only actual duplicates. If no collision exists, skip the rename; log it in the commit body.

**Action** (part C — update imports in all test files): Run the audit grep against `modules/*/tests/` and apply the same category A–E substitutions from Steps 1–5.
```bash
# Find all test files with stale imports
grep -rln "from modules\.\(chain\|workflows\|projects\|context\|templates\|spec_gen\|task_gen\|implementation_guide\)\." \
  {WORKSPACE}/api/modules/ {WORKSPACE}/api/tests/
```
For every file listed, apply the same substitution table used in Steps 2–5. The test assertions themselves do not change — only import lines change.

**Verify**:
```bash
cd {WORKSPACE}/api
# Full import validation across all test files
python -m pytest --collect-only -q 2>&1 | grep "ERROR\|ImportError" | head -20
# Expect: zero ERROR lines (all test files importable)
```

---

## 5. Tests

Add `api/tests/test_runtime_imports.py` (new). These four assertions confirm the four new package roots are importable and their public interfaces are intact — a permanent structural guard that survives future refactors.

```python
"""Smoke tests: verify new package roots are importable after Task 4 import rewrites."""
import importlib

import pytest


@pytest.mark.parametrize("module_path,expected_attr", [
    ("modules.runtime.chain.adapter", "generate"),
    ("modules.runtime.workflows", "WorkflowRuntime"),
    ("modules.data.projects.service", "get_project"),
    ("modules.data.context.service", "read_context"),
])
def test_newPackageRoot_isImportable(module_path, expected_attr):
    """Each new package root resolves and exposes its documented public name."""
    mod = importlib.import_module(module_path)
    assert hasattr(mod, expected_attr), (
        f"{module_path} is missing '{expected_attr}'. "
        "Either the import path is wrong or the public symbol was renamed."
    )


def test_adapterBoundary_noDirectProviderImports():
    """No file outside adapter.py and providers/ imports from runtime.chain.providers directly.

    This is ELA Pattern #1. Grep the source tree; fail if any violation exists.
    """
    import subprocess
    result = subprocess.run(
        [
            "grep", "-rn",
            "--include=*.py",
            "--exclude-dir=providers",
            "from modules.runtime.chain.providers",
            "modules/",
        ],
        capture_output=True,
        text=True,
        cwd=str(__import__("pathlib").Path(__file__).parent.parent),
    )
    violations = [
        line for line in result.stdout.splitlines()
        if "adapter.py" not in line and "/providers/" not in line and "/tests/" not in line
    ]
    assert violations == [], (
        "ELA #1 violation — direct provider import outside adapter boundary:\n"
        + "\n".join(violations)
    )
```

---

## 6. Commit Plan

**Executor instruction**: run `git add` and `git commit` after EACH step completes — not at the end of the task. Each boundary below is a git commit.

1. **`fix(create_app): update ENABLED_MODULES and workflow repo import to new package paths`** — after Step 1 — files: `create_app.py`

2. **`fix(runtime): rewrite modules.chain → modules.runtime.chain in routes, services, ai_call`** — after Step 2 — files: `modules/ai/routes/text.py`, `modules/ai/services/task_gen.py`, `modules/runtime/workflows/steps/ai_call.py`

3. **`fix(runtime): rewrite modules.workflows → modules.runtime.workflows; convert internal imports to relative`** — after Step 3 — files: `modules/ai/routes/text.py`, `modules/ai/routes/spec_gen.py`, `modules/ai/services/task_gen.py`, `modules/ai/workflows/spec_gen/generate_spec.py`, `modules/ai/workflows/spec_gen/bootstrap.py`, `modules/runtime/workflows/runtime.py`, `modules/runtime/workflows/repository/fs_adapter.py`, `modules/runtime/workflows/repository/__init__.py`

4. **`fix(data): rewrite modules.{context,projects,templates} → modules.data.* across all consumers`** — after Step 4 — files: `modules/ai/routes/text.py`, `modules/ai/routes/spec_gen.py`, `modules/ai/routes/task_gen.py`, `modules/ai/services/task_gen.py`, `modules/data/projects/service.py`

5. **`fix(ai): rewrite implementation_guide and spec_gen.prompts imports to ai.prompts.*`** — after Step 5 — files: `modules/ai/services/task_gen.py`, `modules/ai/workflows/spec_gen/generate_spec.py`

6. **`fix(tests): rewrite cross-module imports in test files; rename colliding test_routes.py`** — after Step 6 — files: all `modules/*/tests/*.py` with stale imports; any renamed test files

7. **`test(runtime): add smoke import tests for new package roots and adapter boundary`** — after tests pass — files: `tests/test_runtime_imports.py`

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation (e.g., `Deviations: step 5b — spec_gen.prompts located at modules.ai.prompts.generation, not modules.ai.prompts.spec_gen`).

---

## 7. Verification

```bash
cd {WORKSPACE}/api
make test
```

**Expected delta**: failures after Task 3 → **628 passing** (624 pre-epic baseline + 4 parametrized smoke cases + 1 adapter-boundary test from `test_runtime_imports.py`). Zero pre-existing tests broken. Zero assertion body changes in any moved test file.

**Additional spot checks**:
```bash
# Confirm no stale absolute imports of any old flat prefix remain
grep -rn "from modules\.\(chain\|workflows\|projects\|context\|templates\|spec_gen\|task_gen\|implementation_guide\)\." \
  {WORKSPACE}/api/modules/ {WORKSPACE}/api/tests/ {WORKSPACE}/api/create_app.py
# Expect: zero output

# Confirm blueprint registration still works end-to-end
cd {WORKSPACE}/api && python -c "
from create_app import create_app
app = create_app()
bp_names = [bp for bp in app.blueprints]
print('registered blueprints:', bp_names)
assert 'ai_bp' in bp_names, 'ai_bp missing'
assert 'task_gen_bp' in bp_names, 'task_gen_bp missing'
assert 'spec_gen_bp' in bp_names, 'spec_gen_bp missing'
assert 'context_bp' in bp_names, 'context_bp missing'
assert 'projects_bp' in bp_names, 'projects_bp missing'
assert 'templates_bp' in bp_names, 'templates_bp missing'
print('PASS — all 6 blueprints registered')
"
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>`. Because the steps are ordered (ENABLED_MODULES → chain → workflows → data → ai-internal → tests), reverting step N requires first reverting steps N+1…7 in reverse order.
- **Per-branch**: if verification fails catastrophically after all steps, `git reset --hard <pre-task-4-sha>` restores the Task 3 end-state (imports broken but files in correct locations). Retrieve the sha with `git log --oneline | grep "Task 3"` before starting.

---

## 9. Deviations Allowed

- **`find` command in Step 5 returns a path different from `modules.ai.prompts.implementation_guide`** → use the actual path; log in commit 5 body as `Deviations: implementation_guide prompt at <actual path>`.
- **No test collision exists in `modules/ai/routes/tests/`** (Task 3 already renamed) → skip the `git mv` commands in Step 6; log `Deviations: no collision — Task 3 already renamed test_routes files`.
- **A moved `__init__.py` stub contains a stale absolute import** not caught in the pre-flight grep → fix it within whichever step covers that module's prefix; add the file to that step's commit.
- **Step N unlocks a relative-import simplification for Step N+1** → take it and log in the commit body; do not expand scope beyond import-path changes.
- **Side-effect required** (e.g., migration, schema change, push) → STOP, mark `[REQUIRES APPROVAL]`, and ask before proceeding.

---

## 10. Out of Scope

This task is the last step before `make test` returns to green. The executor must resist any temptation to clean up import ordering, collapse redundant imports, rename symbols, adjust Blueprint names, or add route handlers — the constraint is absolute: zero semantic change. The following items are explicitly deferred.

- **Structural hierarchy test** (`packages_areInExpectedHierarchy` in `tests/test_structural.py`) — owned by Task 5; the `saas_optional` allowlist decision from Task 1 must be encoded there, not here.
- **`anthropic_sdk.py` provider completion** — the provider file moved to `modules/runtime/chain/providers/`; its import path is now correct but its implementation may still be a stub. Completing the SDK provider is a separate epic item.
- **`quality/` Blueprint registration** — if `quality/` exposes a Blueprint that is not in ENABLED_MODULES, that is a pre-existing omission; do not add it here without a separate PR.
- **Per-package `CLAUDE.md` files** — the architecture explicitly deferred these; `api/CLAUDE.md` remains the single source of truth.
- **Renaming `quality/` to `pipeline/`** — the architecture flagged this as a separate concern, separate PR.
- **Splitting `runtime/chain/` into sub-packages** — ELA #5 prohibits speculative splits; `ai/` is the only consumer today.
- **Import ordering / isort cleanup** — any import-order violations introduced by the rewrites are cosmetic; address in a dedicated lint PR after `make test` is green.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for the four-package hierarchy
- [Epic](./epic.md) — Full task scope and file-move mapping confirmed in Task 1
- [Timeline](./timeline.md) — Status tracking (mark Task 4 done after `make test` reaches 628 passing)