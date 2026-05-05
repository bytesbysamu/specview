`movedFiles_absentFromOldPaths` assertions` — after Step 7 tests pass — file: `tests/test_structural.py`

**Deviation logging**: if a step deviates, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

Run the two new structural tests first — these are the only tests expected to pass:

```bash
cd {WORKSPACE}/api
python -m pytest tests/test_structural.py::movedFiles_existAtNewPaths \
                 tests/test_structural.py::movedFiles_absentFromOldPaths -v
```

Then run the full suite and confirm failures are exclusively import-related:

```bash
python -m pytest --tb=line -q 2>&1 | grep -v "ModuleNotFoundError\|ImportError" | tail -20
# Any failure that is NOT ModuleNotFoundError / ImportError is unexpected — investigate before Task 4.
```

**Expected delta**: 624 → 2 passing (`movedFiles_existAtNewPaths`, `movedFiles_absentFromOldPaths`). All others fail with `ModuleNotFoundError` on the moved paths. Full recovery to 624+ is Task 4's target.

---

## 8. Rollback

**Per-step**: each commit is independently revertible. `git mv` + `git rm` operations are reversible with a revert commit:
```bash
git revert <sha>    # new revert commit; does not alter prior history
```

Steps 1–6 are pure rename/delete operations. Reverting Step 4 (dissolve into `ai/`) does not undo the `runtime/` moves from Steps 1–2 because they are separate commits.

**Per-branch**: if verification reveals non-import failures that cannot be quickly diagnosed:
```bash
git reset --hard <pre-task3-sha>    # SHA recorded in pre-flight baseline
```

---

## 9. Deviations Allowed

- **A listed source file does not exist** — confirm with `git ls-files <old-module>/`; if genuinely absent, skip that `git mv`, remove the path from `expected` in the structural test, and add `Deviations: <path> absent, skipped` to the commit body.
- **`modules/ai/workflows/spec_gen/` not scaffolded by Task 2** — run `mkdir -p modules/ai/workflows/spec_gen` before the `git mv` in Step 4; log as deviation.
- **`_MODULES` name collides with existing variable in `tests/test_structural.py`** — reuse the existing `_REPO_ROOT / "modules"` expression; omit the `_MODULES =` line; note silently in commit body.
- **`spec_gen/` contains a `service.py` not found during Task 3 inspection** — move it to `modules/ai/services/spec_gen.py`; add `"ai/services/spec_gen.py"` to `expected` and `"spec_gen/service.py"` to `forbidden` in the structural test.
- **`context/` or `projects/` has a `tests/` directory not found above** — apply the same loop pattern used for `templates/`; add a `mkdir -p` for the destination `tests/` dir.
- **`git mv -f` fails on a stub overwrite** — manually copy the content (`cp src dest`), then `git add dest && git rm src`; log as deviation.
- **Side-effect required** (push, publish, schema migration) → STOP, mark `[REQUIRES APPROVAL]`, ask before continuing.

---

## 10. Out of Scope

This task ends in a known-broken state. Nothing here touches import declarations, Blueprint registrations, or test assertions — that is Task 4's entire scope.

- **Import-path rewrites** — every `from modules.chain.adapter import …` reference in routes, services, `create_app.py`, and test files is broken after Task 3; Task 4 repairs all ~50 occurrences
- **`create_app.py` `ENABLED_MODULES` block** — Blueprint dotted import paths still point at old locations; intentionally left broken until Task 4
- **Internal relative imports in moved `__init__.py` files** — `modules/runtime/workflows/__init__.py` re-exports `from .runtime import WorkflowRuntime`; that relative import is now correct, but any absolute `from modules.workflows…` references inside moved files break; Task 4 fixes those
- **`modules/ai/tests/spec_gen/__init__.py` and sibling stubs** — new test sub-packages under `ai/tests/` may need `__init__.py` for pytest collection; adding them is Task 4 cleanup, not a content concern here
- **`packages_areInExpectedHierarchy` structural test** — pins the four-package boundary with the `saas_optional` allowlist; Task 5's deliverable
- **Snapshot file content refresh** — `.ambr` snapshot files embed source-path strings that will need updating after Task 4's import rewrites; do not regenerate snapshots here
- **`modules/runtime/chain/tests/test_structural.py` content** — this chain-level structural test (which moved from `modules/chain/tests/`) contains import assertions that will need updating in Task 4

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — four-package hierarchy rationale
- [Epic](./epic.md) — full five-task execution plan
- [Timeline](./timeline.md) — update status to "in progress" on start; "done" when commit 7 lands