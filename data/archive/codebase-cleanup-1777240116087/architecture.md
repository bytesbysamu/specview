# 🏗️ Solution Architecture: Codebase Cleanup

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

This epic removes structural debt from the existing system; it adds nothing new. The mental model is a **deletion cascade with a settlement dependency**: Tasks 1 and 2 delete prompt functions from `modules/ai/prompts/__init__.py`; only after those deletions settle can Task 3 correctly partition what remains into per-feature files. Splitting before deleting means splitting content about to disappear — rework and merge conflicts. The ordering is not about risk; every task is independently safe. It is about minimising the surface the split must cover.

The second key insight is that bootstrap's apparent migration is illusory. `_run_bootstrap_thread` wraps three inline `chain_adapter.generate()` calls behind a `WorkflowExecution` facade but never invokes `WorkflowRuntime`. The facade creates the impression of Workflow Domain Layer compliance without delivering it. Resolving this is the architectural heart of the epic: either bootstrap runs through the runtime (migration completes) or the dangling `workflow_ref` is removed and the inline pattern is acknowledged as intentional. Either outcome closes the ambiguity; the half-migrated state is not acceptable because every future feature that reads `_run_bootstrap_thread` copies a pattern that violates ELA #6.

The four tasks together move the codebase from a state where the Workflow Domain Layer is the substrate for two of three AI orchestration paths (`task_gen`, `spec_gen`) to a state where all three use consistent patterns, no prompt function lives in a file with 600-LOC neighbours, and the largest function is narrow enough to read without scrolling.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| ELA #1 — Adapter Boundary | `chain_adapter` remains the sole AI call site after bootstrap migration; no new direct provider imports introduced |
| ELA #2 — Blueprint Module Structure | Prompt functions move to per-feature `prompts/` files within their owning module, not to a shared library |
| ELA #3 — OpenAPI-First | Every `openapi.yaml` edit (Task 1 path deletion) is followed immediately by `make generate-dtos`; DTOs committed in the same changeset |
| ELA #4 — Async 202 + Polling | Bootstrap's 202 contract is preserved regardless of whether the internal thread calls the runtime or `chain_adapter` directly |
| ELA #5 — Not-Yet-Built | `_section()` in `generators.py` is a private module-local helper, not a shared utility; its only consumer is that one file |
| ELA #6 — Workflow Domain Layer | Bootstrap's migration either completes or the `workflow_ref` string is deleted; the half-migrated facade is exactly the failure mode this principle prohibits |

---

## System Boundaries

### What This System Includes

- Deletion of the duplicate `/api/ai/text/generate-spec` route, its prompt function, and its openapi path — contingent on Angular switching its call URL first
- Resolution of bootstrap's migration status: complete the `WorkflowRuntime` invocation or remove the dangling `workflow_ref` — one or the other, not the current hybrid
- Redistribution of `modules/ai/prompts/__init__.py` into per-feature files with `__init__.py` retained as a re-export shim for caller compatibility
- Decomposition of `run_generation` in `task_gen/service.py` into named sub-functions
- Extraction of a module-private `_section()` helper from the three parallel markdown-emitting functions in `modules/data/templates/generators.py`
- A `findings.md` artifact committed at the start of the PR documenting discovery-prompt output and per-finding disposition

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Test coverage additions for `context/` and `projects/` | Net-positive LOC; belongs in a dedicated coverage epic |
| FS→SQL persistence migration | Separate brain dump; different risk profile and scope |
| `quality/` → `pipeline/` rename | Deferred to modular-restructure epic |
| Migration of single-step `chain_adapter` calls to WorkflowRuntime | Single AI calls don't benefit from a workflow wrapper; inline is architecturally correct |
| Frontend Angular audit | Separate concern; not yet a felt pain |
| Full SOLID compliance audit | Targets theoretical violations; this epic targets observed structural debt only |
| New shared abstractions | No second concrete consumer exists for any extracted helper |

---

## Component Design

### Task 1 — Duplicate Route Elimination

**Purpose**: The old `/api/ai/text/generate-spec` handler and the new `/api/spec-gen/generate` route serve the same domain operation. Keeping both means Angular can silently drift back to the old inline path, and the WorkflowRuntime-backed implementation accumulates zero real-world usage signal. The old route is the deletion target because the new one uses `WorkflowRuntime`, the intended substrate.

**Key Parts**:
- Angular `ai.service.ts` URL switch — the hard pre-condition; deleting the backend handler before this change breaks the live product
- `text.py` handler removal — the inline spec-gen implementation and its `generate_spec_prompt` caller in `prompts/__init__.py` are deleted together; they have no other consumers
- `openapi.yaml` path removal followed by `make generate-dtos` — the deletion must flow through the contract layer; DTOs committed in the same changeset

**Patterns**: OpenAPI-first (ELA #3); the contract drives the deletion, not the route file.

---

### Task 2 — Bootstrap Migration Resolution

**Purpose**: `_run_bootstrap_thread` simulates Workflow Domain Layer participation without actually using it. The `workflow_ref` string points at a registered workflow the thread never invokes. This is the primary instance of silent migration debt: tests pass, but the architectural invariant is violated. Future features that read this code will copy the wrong pattern.

**Key Parts**:
- Classification gate — the implementation guide must resolve before coding begins whether replacing the three inline `chain_adapter.generate()` calls with `WorkflowRuntime.run()` is a structural swap (no observable behaviour change) or a feature-finish (behaviour delta). Structural → migration completes here. Feature-finish → dangling `workflow_ref` deleted, full migration filed as a separate brain dump.
- `_BOOTSTRAP_JOBS` state dict in `modules/ai/routes.py` — the 202/polling contract is preserved regardless of classification outcome; state shape does not change
- Bootstrap prompt function deletion (~287 LOC across three functions) — contingent on full migration completing; ref-deletion-only path removes ~5 LOC

**Patterns**: Workflow Domain Layer (ELA #6); Async 202 + Polling (ELA #4).

---

### Task 3 — Prompts God-Module Redistribution

**Purpose**: `modules/ai/prompts/__init__.py` at 779 LOC is the primary debt accumulation point for the five queued SaaS epics. Every new feature that adds a prompt function extends this file unless it is partitioned first. The redistribution is invisible to callers: `__init__.py` becomes a re-export shim, so all existing `from modules.ai.prompts import X` call sites resolve without modification.

**Key Parts**:
- `prompts/text.py` — rewrite, iterate, generate prompt functions; sole consumers are `modules/ai/routes.py` text handlers
- `prompts/review.py` — review, lint-braindump, scan prompt functions; sole consumers are review route handlers
- `prompts/bootstrap.py` — bootstrap prompt functions, only if Task 2 does not delete them; sole consumer is `_run_bootstrap_thread`
- `prompts/__init__.py` (shim) — re-exports from per-feature files; shrinks from 779 LOC to ~30 LOC
- Content-routing constants — co-located with the file that uses them, not promoted to a shared constants module

**Why shim rather than direct imports**: Changing all callers to import from new paths in the same PR that moves the files doubles the diff surface and creates merge conflicts if any queued feature branch touches the same import sites. The shim decouples file reorganisation from caller updates.

**Dependency on Tasks 1 and 2**: Task 1 deletes `generate_spec_prompt`; Task 2 deletes the bootstrap prompt functions if migration completes. Splitting a file that contains content about to be deleted means the split must be re-done — wasted effort and a merge conflict source.

**Patterns**: Blueprint Module Structure (ELA #2); per-feature ownership of prompt functions.

---

### Task 4 — Structural Decomposition (Parallel-eligible)

**Purpose**: Two independent file-local improvements with no interaction with Tasks 1–3 and no shared files between them.

**Key Parts**:
- `task_gen/service.py::run_generation` decomposition — the 139-LOC function broken into named sub-functions (`_load_inputs`, `_select_task`, `_build_prompt`, `_invoke_chain`, `_persist_result`, `_record_completion`); each ~20 LOC with a single clear responsibility. The sole consumer of each sub-function is the `run_generation` orchestrator in the same file.
- `generators.py::_section()` extraction — the three parallel markdown-emitting functions in `modules/data/templates/generators.py` share a section-emission shape. The extracted helper is module-private; it is not promoted to a shared utility because its only consumer is this one file (ELA #5).

**Patterns**: Not-Yet-Built (ELA #5); the extracted helper is private by design, not an oversight.

---

## Execution Flow

```
[Pre-condition]
  Angular URL switch ──→ unblocks Task 1

[Phase 1 — Deletions settle]
  Task 1: Delete duplicate route + openapi path + generate-dtos
  Task 2: Classification gate → full migration OR ref-deletion

[Phase 2 — Partition the settled remainder]
  Task 3: Split prompts __init__.py into per-feature files

[Phase 2 — Independent, parallel with Task 3]
  Task 4: Decompose run_generation + extract _section()

[Every commit invariant]
  make lint → make test (all green before next commit)
  openapi.yaml edit → make generate-dtos → DTOs in same commit
```

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Prompts `__init__.py` becomes a re-export shim rather than being deleted | Callers don't change; reorganisation is invisible to all existing import sites | The shim is a permanent indirection layer; callers never see the true source module unless they opt in to direct imports later |
| Bootstrap classification gate before any implementation begins | The LOC delta swings from ~5 to ~310 depending on the answer; implementing without the gate risks building on a wrong premise | Adds a decision step before coding; acceptable cost given the scope difference |
| Task 4 runs parallel to Task 3 | No shared files; no merge conflicts | Slightly higher cognitive load if both tasks are open simultaneously; acceptable for a solo developer |
| Delete by default; document only what cannot be deleted | Deletions appear in code review; reverts are cheap; documenting-without-deleting accumulates more debt than it removes | Risk of deleting a non-obvious consumer; mitigated by cross-file grep before any deletion |
| `_section()` stays private to `generators.py` | ELA #5: exactly one consumer exists today; promoting it would create an abstraction for one use case | If a second consumer appears, the helper is promoted then, not speculatively now |

---

## Open Questions

- **Bootstrap classification gate**: Is replacing the three inline `chain_adapter.generate()` calls in `_run_bootstrap_thread` with `WorkflowRuntime.run()` a structural swap (no observable behaviour change) or a feature-finish (behaviour delta requiring new or changed tests)? Options: (A) structural — migrate fully in Task 2; (B) feature-finish — delete only the dangling `workflow_ref` and file a separate brain dump. Re-decision trigger: reading the existing bootstrap workflow definition in `modules/ai/workflows/spec_gen/bootstrap.py` against the three inline calls to determine whether outputs and side-effects are identical.

- **Audit discoveries beyond the six seed findings**: The open-ended charter requires the executor to add findings to `findings.md` as the walk surfaces them. Items added may require scope adjustment. Re-decision trigger: any new finding whose fix exceeds 0.5 days of effort, or that touches Blueprint registration, openapi paths, or inter-module interfaces — escalate before implementing.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview