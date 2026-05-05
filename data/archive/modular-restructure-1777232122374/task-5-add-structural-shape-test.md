# Task 5: Add Structural Shape Test — Implementation Guide

---

## 1. Context

This task adds `packages_areInExpectedHierarchy` to `api/tests/test_structural.py` — a single assertion function that pins the four-package layout produced by the Apr-2026 modular-restructure epic and prevents silent re-sprawl. Without it, a future engineer could drop a new module directly under `modules/` and no CI job would object; the flat-list anti-pattern would quietly re-emerge. The test encodes two things: the exhaustive set of four core packages (`ai`, `runtime`, `data`, `quality`) that Tasks 1–4 produce, and the `saas_optional` decision from Task 1 — an explicit allowlist of the four planned SaaS peer packages (`auth`, `billing`, `usage`, `observability`). Every future SaaS module requires a visible PR edit to this allowlist, which is the intent.

**Trade-offs considered:**

- **Naming-convention check (`name.startswith("saas_")`)** — rejected because it is open-ended; any misspelled or miscategorised module passes silently, defeating the purpose of the gate.
- **Test-only grep (no directory walk)** — rejected because checking `__init__.py` presence is more precise than grepping source files; it catches scaffolded-but-empty packages that haven't written any source yet.
- **Exhaustive allowlist (chosen)** — preferred because the four SaaS modules are the complete planned set; the list is short, auditable, and fails loudly for any unexpected name. Adding a fifth SaaS module is one intentional PR line.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# 1. Confirm working tree is clean
git status

# 2. Confirm target file is unmodified
git diff HEAD -- api/tests/test_structural.py

# 3. Verify Tasks 1–4 are complete — new hierarchy must exist
ls api/modules/ai/__init__.py \
   api/modules/runtime/__init__.py \
   api/modules/data/__init__.py \
   api/modules/quality/__init__.py

# 4. Confirm flat packages are gone (none of these should exist)
ls api/modules/chain api/modules/spec_gen api/modules/task_gen \
   api/modules/context api/modules/projects api/modules/templates \
   api/modules/workflows api/modules/implementation_guide 2>&1 | grep "No such"

# 5. Record baseline — make test must pass before Task 5 touches anything
cd api && python -m pytest --tb=short -q 2>&1 | tail -5
```

**If working tree is dirty on `api/tests/test_structural.py`**: stash or commit the unrelated change first.

**If steps 3–4 fail** (new packages missing or old packages still present): Tasks 1–4 are incomplete. Do not proceed — this task's test will fail on the current shape.

**Baseline recorded**: 624 / 624 passing (1 skipped).

---

## 3. Files

### To Create (new)
_(none — all changes are additions to an existing file)_

### To Modify
- `api/tests/test_structural.py` — append one function `packages_areInExpectedHierarchy` after the existing six; no existing function is touched

### To Leave Alone
- `api/tests/conftest.py` — fixture wiring is unchanged; the new function needs no fixtures
- `api/pyproject.toml` — `python_functions = ["test_*", "*_*"]` already collects the new function; do not modify
- `api/modules/*/` — no source files are touched in this task
- `api/openapi.yaml` — contract is unrelated to package layout
- `api/dtos/models.py` — generated artifact; do not touch

---

## 4. Implementation Steps

### Step 1: Append `packages_areInExpectedHierarchy` to `test_structural.py`

**Action**: Open `api/tests/test_structural.py` and append the function below after `coherenceModule_doesNotImportFlaskOrChain`. Do not alter any existing function or the module-level constants (`_REPO_ROOT`).

**File**: `api/tests/test_structural.py` (from CODEBASE CONTEXT — `tests/`)

**Pattern**:

```python
def packages_areInExpectedHierarchy():
    """Top-level packages under modules/ must belong to the four-package core
    set or the approved SaaS peer allowlist.

    Rule: modules/ has exactly four named core packages (ai, runtime, data,
          quality) produced by the Apr-2026 modular-restructure epic. SaaS
          capabilities (auth, billing, usage, observability) may appear as
          peer packages at the modules/ root; they are enumerated explicitly
          in SAAS_OPTIONAL below. Any other top-level package means an
          engineer silently re-sprawled the flat structure this epic ended.

    saas_optional decision (Task 1, modular-restructure epic, Apr 2026):
          Exhaustive allowlist chosen over naming-convention check.
          Rationale: the four named SaaS modules are the complete planned set;
          an explicit set fails loudly for unexpected names and makes each
          future SaaS capability a visible, intentional PR edit rather than a
          silent addition. To add a fifth SaaS module: (1) add its name to
          SAAS_OPTIONAL, (2) add a one-line rationale comment beside it.

    Fix:  If your package is a SaaS capability, extend SAAS_OPTIONAL below.
          If it belongs under a core package, move it there. Do not grow the
          core set without an architecture review.
    """
    # Core four-package hierarchy — output of the Apr-2026 restructure epic.
    # All four must be present; absence indicates an incomplete Task 3/4 run.
    CORE_PACKAGES = {"ai", "runtime", "data", "quality"}

    # Approved SaaS peer packages. Exhaustive by design — see docstring above.
    # To add a fifth SaaS module: add its name here with a rationale comment.
    SAAS_OPTIONAL = {
        "auth",           # planned: Neon auth wrapper
        "billing",        # planned: Stripe / RevenueCat adapter
        "usage",          # planned: per-user quota + rate-limit service
        "observability",  # planned: structured logging + health aggregation
    }

    modules_root = _REPO_ROOT / "modules"
    actual = {
        d.name
        for d in modules_root.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and (d / "__init__.py").exists()
    }

    # Guard: all four core packages must be present.
    missing_core = CORE_PACKAGES - actual
    assert not missing_core, (
        "packages_areInExpectedHierarchy: core packages missing from modules/:\n"
        + "\n".join(f"  modules/{p}/" for p in sorted(missing_core))
        + "\nExpected core set: " + ", ".join(sorted(CORE_PACKAGES))
        + "\nThis indicates Tasks 1-4 of the modular-restructure epic are incomplete."
        + "\nDo not add this test until all four core packages exist with __init__.py."
    )

    # Guard: no unexpected packages outside core + saas_optional.
    unexpected = actual - CORE_PACKAGES - SAAS_OPTIONAL
    assert not unexpected, (
        "packages_areInExpectedHierarchy: unexpected top-level packages under modules/:\n"
        + "\n".join(f"  modules/{p}/" for p in sorted(unexpected))
        + "\nAllowed core:         " + ", ".join(sorted(CORE_PACKAGES))
        + "\nAllowed saas_optional: " + ", ".join(sorted(SAAS_OPTIONAL))
        + "\nTo register a new SaaS module: add its name to SAAS_OPTIONAL in"
        + "\n  api/tests/test_structural.py with a one-line rationale comment."
        + "\nTo add a core package: requires an architecture review PR."
    )
```

**Verify**:
```bash
cd api && python -m pytest tests/test_structural.py -v -k packages_areInExpectedHierarchy
```
Expect: `PASSED` — 1 passed, 0 failed.

---

## 5. Tests

Framework: **pytest** with `python_functions = ["test_*", "*_*"]` (see `api/pyproject.toml`). Every function whose name contains `_` is collected. No class wrappers needed.

The complete assertion body for the new function is given in Step 1 above. For completeness, below is the full function as it should appear verbatim in the file — no stubs, no omissions.

```python
def packages_areInExpectedHierarchy():
    """Top-level packages under modules/ must belong to the four-package core
    set or the approved SaaS peer allowlist.

    Rule: modules/ has exactly four named core packages (ai, runtime, data,
          quality) produced by the Apr-2026 modular-restructure epic. SaaS
          capabilities (auth, billing, usage, observability) may appear as
          peer packages at the modules/ root; they are enumerated explicitly
          in SAAS_OPTIONAL below. Any other top-level package means an
          engineer silently re-sprawled the flat structure this epic ended.

    saas_optional decision (Task 1, modular-restructure epic, Apr 2026):
          Exhaustive allowlist chosen over naming-convention check.
          Rationale: the four named SaaS modules are the complete planned set;
          an explicit set fails loudly for unexpected names and makes each
          future SaaS capability a visible, intentional PR edit rather than a
          silent addition. To add a fifth SaaS module: (1) add its name to
          SAAS_OPTIONAL, (2) add a one-line rationale comment beside it.

    Fix:  If your package is a SaaS capability, extend SAAS_OPTIONAL below.
          If it belongs under a core package, move it there. Do not grow the
          core set without an architecture review.
    """
    # Core four-package hierarchy — output of the Apr-2026 restructure epic.
    # All four must be present; absence indicates an incomplete Task 3/4 run.
    CORE_PACKAGES = {"ai", "runtime", "data", "quality"}

    # Approved SaaS peer packages. Exhaustive by design — see docstring above.
    # To add a fifth SaaS module: add its name here with a rationale comment.
    SAAS_OPTIONAL = {
        "auth",           # planned: Neon auth wrapper
        "billing",        # planned: Stripe / RevenueCat adapter
        "usage",          # planned: per-user quota + rate-limit service
        "observability",  # planned: structured logging + health aggregation
    }

    modules_root = _REPO_ROOT / "modules"
    actual = {
        d.name
        for d in modules_root.iterdir()
        if d.is_dir()
        and not d.name.startswith("_")
        and (d / "__init__.py").exists()
    }

    # Guard: all four core packages must be present.
    missing_core = CORE_PACKAGES - actual
    assert not missing_core, (
        "packages_areInExpectedHierarchy: core packages missing from modules/:\n"
        + "\n".join(f"  modules/{p}/" for p in sorted(missing_core))
        + "\nExpected core set: " + ", ".join(sorted(CORE_PACKAGES))
        + "\nThis indicates Tasks 1-4 of the modular-restructure epic are incomplete."
        + "\nDo not add this test until all four core packages exist with __init__.py."
    )

    # Guard: no unexpected packages outside core + saas_optional.
    unexpected = actual - CORE_PACKAGES - SAAS_OPTIONAL
    assert not unexpected, (
        "packages_areInExpectedHierarchy: unexpected top-level packages under modules/:\n"
        + "\n".join(f"  modules/{p}/" for p in sorted(unexpected))
        + "\nAllowed core:         " + ", ".join(sorted(CORE_PACKAGES))
        + "\nAllowed saas_optional: " + ", ".join(sorted(SAAS_OPTIONAL))
        + "\nTo register a new SaaS module: add its name to SAAS_OPTIONAL in"
        + "\n  api/tests/test_structural.py with a one-line rationale comment."
        + "\nTo add a core package: requires an architecture review PR."
    )
```

The function exercises two distinct failure modes:

| Scenario | Which assert fires | Expected message prefix |
|---|---|---|
| Core package missing (e.g. `modules/runtime/` deleted) | `missing_core` assert | `core packages missing from modules/` |
| Unexpected flat package present (e.g. `modules/chain/` re-added) | `unexpected` assert | `unexpected top-level packages under modules/` |

---

## 6. Commit Plan

**Executor instruction**: commit after **each step** completes — not at the end of the task. There is one step in this task, so one commit.

1. `test(structural): add packages_areInExpectedHierarchy shape gate` — after Step 1 — `api/tests/test_structural.py`: adds exhaustive allowlist structural test pinning the four-package hierarchy and saas_optional decision from Task 1

Run:
```bash
cd {WORKSPACE} && git add api/tests/test_structural.py
git commit -m "$(cat <<'EOF'
test(structural): add packages_areInExpectedHierarchy shape gate

Pins the four-package modules/ hierarchy produced by the Apr-2026
modular-restructure epic. Any top-level package outside core
{ai, runtime, data, quality} or the approved saas_optional
{auth, billing, usage, observability} set fails CI.

saas_optional decision: exhaustive allowlist (see inline rationale).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

**Deviation logging**: if anything about the implementation differs from the guide (e.g., Task 1 chose naming-convention over allowlist), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → **625** passing. Zero pre-existing tests broken.

Confirm the new function is collected and passes:
```bash
cd api && python -m pytest tests/test_structural.py -v
```
Expected output — seven functions listed, all `PASSED`:
```
tests/test_structural.py::noPromptStrings_inRouteHandlers PASSED
tests/test_structural.py::gunicorn_inProdRequirements PASSED
tests/test_structural.py::abstractStep_execute_isConcreteTemplateMethod PASSED
tests/test_structural.py::workflowsModule_doesNotImportChainProvidersDirectly PASSED
tests/test_structural.py::featureModules_mustNotLoadWorkflowsDirectly PASSED
tests/test_structural.py::coherenceModule_doesNotImportFlaskOrChain PASSED
tests/test_structural.py::packages_areInExpectedHierarchy PASSED
```

---

## 8. Rollback

- **Per-step**: the single commit is independently revertible.
  ```bash
  git revert <sha>   # creates a new revert commit; safe on a PR branch
  ```
- **Per-branch**: if verification fails catastrophically (e.g., a Task 4 import path was wrong and multiple tests break):
  ```bash
  git reset --hard <pre-task-5-sha>   # [REQUIRES APPROVAL] — destructive
  ```
  Prefer `git revert` for shared branches; use `reset --hard` only on a private feature branch.

---

## 9. Deviations Allowed

- **`saas_optional` decision differs from guide**: if Task 1's commit message or output chose naming-convention (`name.startswith("saas_")`) over exhaustive allowlist, replace the `SAAS_OPTIONAL` set with a convention check and update the inline rationale accordingly. Log the deviation in the commit body.
- **Four core packages not yet present**: if `ls api/modules/runtime/__init__.py` fails, stop. Do not add a failing test. Flag the incomplete Task 4 state and resolve it before proceeding.
- **`test_structural.py` already has a draft `packages_areInExpectedHierarchy`**: if a skeleton or stub already exists, compare it against the full body in Step 1; fill it in completely rather than duplicating. Log the deviation.
- **Test count baseline differs from 624**: if `make test` shows a different count after Tasks 1–4, record the actual baseline and adjust the expected post-Task-5 delta accordingly (+1 either way). The delta, not the absolute number, is the invariant.
- **Step 1 unlocks an obvious simplification** → take it, log deviation in commit body.
- **Side-effect required** (push, schema change) → STOP, mark **[REQUIRES APPROVAL]** and ask.

---

## 10. Out of Scope

This task has a strict one-function port budget. The structural test function encodes the boundary; it does not modify any existing behaviour, build new infrastructure, or expand into adjacent concerns. Any of the following that an eager executor might attempt is explicitly out of scope:

- **Updating existing structural test path references** (e.g., `workflowsModule_doesNotImportChainProvidersDirectly` references `_REPO_ROOT / "modules" / "workflows"` — after the restructure this path is `modules/runtime/workflows/`). That update belongs to Task 4's import-rewrite commit, not Task 5. If these functions are broken, stop and fix Task 4 first.
- **Adding `__init__.py` stubs or creating new directories** — that is Task 2's scope.
- **Moving source files** — that is Task 3's scope.
- **SaaS module implementation** (auth, billing, usage, observability) — the allowlist reserves the names; no code is written here. Each is its own future epic.
- **Renaming `quality/` to `pipeline/`** — explicitly excluded from the restructure epic per the Architecture doc; requires a separate PR.
- **Splitting `chain/` into sub-packages** — ELA #5 prohibits this until a second non-AI consumer exists.
- **Adding per-package `CLAUDE.md` files** — `api/CLAUDE.md` remains the single source of truth; no sub-docs are created in this epic.

**Rule for the executor**: if a change appears helpful but is listed above, **STOP**, flag it as a deviation, and do not expand this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – `packages_areInExpectedHierarchy` design rationale (§ Structural Shape Test)
- [Epic](./epic.md) – Task 5 scope and port budget
- [Timeline](./timeline.md) – Update status to ✅ after verification passes