# 🎯 Epic: Modular Restructure

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The 10-flat-module layout was correct when spec-doc had three modules. At 10, navigating `api/modules/` requires the reader to already know which flat peers are AI generators, which are runtime infrastructure, and which are storage — that knowledge lives only in the developer's head, not the structure. Five incoming SaaS capabilities (auth, billing, usage, observability, and notifications) plus ~4 bucket-7 differentiators push the count to 17–20 flat packages by Phase 4, at which point the folder actively impedes navigation and onboarding.

Regrouping into four cohesive packages (`ai`, `runtime`, `data`, `quality`) creates named, stable homes before the SaaS modules are written. Every subsequent module lands in its correct place from day one rather than being shuffled retroactively after its routes, services, and tests are settled. The Bubls codebase already ships this shape and validates the pattern at scale.

This is a prerequisite for clean feature delivery, not a feature itself. One day of mechanical import-path rewrites now averts a two-sprint reshuffle of freshly stabilised SaaS code in Phase 2.

**Value Proposition**: One day of import-path rewrites prevents a 17–20-module sprawl that would slow every subsequent feature drop through Phase 4.

---

## Scope

### What This Epic Covers

- **Module inventory confirmation** — resolving the open questions from [Analysis](./analysis.md) before any files move: whether `implementation_guide/routes.py` exists, whether `quality/` registers a Blueprint, and how the structural test handles a fifth SaaS module
- **Package scaffolding** — creating the `ai/`, `runtime/`, and `data/` subdirectory trees with `__init__.py` files
- **File moves** — relocating 16 source files per the confirmed mapping table
- **Import path rewrites** — updating ~50 `from modules.X import Y` references across routes, services, `create_app.py`, and tests
- **Structural shape test** — a `test_structural.py` assertion that pins the 4-package boundary and forces any future top-level package to be explicitly acknowledged

### What This Epic Does NOT Cover

- ❌ Logic changes — no function bodies modified; this constraint is absolute
- ❌ API URL changes — Blueprint URL prefixes are unchanged
- ❌ Blueprint name changes — `spec_gen_bp`, `task_gen_bp`, etc. are unchanged
- ❌ `openapi.yaml` changes — the contract is independent of file layout
- ❌ Test assertion changes — test logic is unchanged; only file locations and import paths move
- ❌ Renaming `quality/` to `pipeline/` — separate concern, separate PR
- ❌ Splitting `chain/` into sub-packages — already cohesive; no second consumer exists
- ❌ SaaS module implementation — auth, billing, usage, observability are each a separate epic; this restructure creates their slots only
- ❌ Per-package `CLAUDE.md` files — `api/CLAUDE.md` remains the single source of truth

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Confirm module inventory and resolve open questions** | None | — | 0.1 days | High |
| 2 | **Scaffold 4-package directory structure** | Task 1 | — | 0.1 days | High |
| 3 | **Move files to new locations** | Task 2 | — | 0.3 days | High |
| 4 | **Rewrite import paths and update create_app.py** | Task 3 | — | 0.3 days | High |
| 5 | **Add structural shape test** | Task 4 | — | 0.2 days | High |

### Task 1: Confirm Module Inventory and Resolve Open Questions

Inspect the current filesystem to confirm the exact contents of `implementation_guide/` and `quality/` before any files move. Three open questions from [Analysis](./analysis.md) must be answered and recorded: whether `implementation_guide/routes.py` exists and needs a Blueprint entry in `create_app.py`; whether `quality/` registers a Blueprint and belongs in `ENABLED_MODULES`; and whether the `saas_optional` allowlist in the structural test is exhaustive (`{auth, billing, usage, observability}`) or should use a naming-convention check. The output is a confirmed file-by-file mapping and a documented decision on the allowlist. No files are modified.

**Port budget**: Read-only inspection; confirmed mapping document as output.

### Task 2: Scaffold 4-Package Directory Structure

Create the new directory trees (`ai/routes/`, `ai/prompts/`, `ai/services/`, `ai/workflows/spec_gen/`, `runtime/chain/`, `runtime/workflows/`, `data/projects/`, `data/context/`, `data/templates/`) with `__init__.py` files. The old flat modules remain in place; `make test` must pass after this step.

**Port budget**: Directory creates and `__init__.py` stubs only; no source logic.

### Task 3: Move Files to New Locations

Relocate the 16 source files per the confirmed mapping from Task 1. Imports are intentionally broken at the end of this step; `make test` is expected to fail until Task 4 completes. The old flat module directories are deleted after all files are confirmed moved.

**Port budget**: File moves only; zero content changes.

### Task 4: Rewrite Import Paths and Update create_app.py

Update every `from modules.X import Y` to its new dotted path, update `ENABLED_MODULES` in `create_app.py` to the new module import strings, and rename any test files that would collide under merged package `tests/` folders. `make test` must pass at the end of this task with no assertion changes.

**Port budget**: ~50 import-path lines; `ENABLED_MODULES` block; test file renames only.

### Task 5: Add Structural Shape Test

Add the `packages_areInExpectedHierarchy` assertion to `tests/test_structural.py`. The test must pass on the new shape and must encode the `saas_optional` decision reached in Task 1 — exhaustive allowlist or naming-convention check — with the rationale documented inline so the next developer knows the intent when adding a fifth SaaS module.

**Port budget**: One test function; one inline decision comment.

---

## Success Criteria

- ✅ `make test` passes on the restructured codebase with no assertion logic changes
- ✅ `make check-dtos` passes — `dtos/` is untouched
- ✅ All API routes respond at their unchanged URLs — Blueprint prefixes intact
- ✅ `modules/` root contains exactly `{ai, runtime, data, quality}` as top-level packages (plus any explicitly declared SaaS modules)
- ✅ No flat `spec_gen/`, `task_gen/`, `implementation_guide/`, `chain/`, `workflows/`, `projects/`, `context/`, or `templates/` directories remain at the `modules/` root
- ✅ `test_structural.py` asserts the 4-package shape with the `saas_optional` decision documented in-test
- ✅ The three open questions from [Analysis](./analysis.md) are resolved and recorded before any files move

---

## Non-Goals

- ❌ Logic changes of any kind — function bodies, route handlers, and service methods are untouched
- ❌ URL changes — all endpoints remain at their current paths
- ❌ New abstractions — no base classes, registries, or generic runners for a single consumer
- ❌ SaaS module code — auth, billing, usage, and observability are slots, not implementations
- ❌ Per-package documentation — `api/CLAUDE.md` remains the single source of truth

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview