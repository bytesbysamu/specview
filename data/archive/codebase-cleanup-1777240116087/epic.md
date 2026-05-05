# 🎯 Epic: Codebase Cleanup

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Five queued SaaS epics (github-integration, spec-sharing, landing-page, onboarding, settings-page) will each land prompt functions into a 779-LOC god module and copy a half-migrated bootstrap pattern unless the foundation is cleared first. Silent migration debt — two code paths for the same operation, both passing tests — cannot be caught by CI; it compounds with every feature that copies the wrong pattern. The test suite is a necessary but insufficient correctness signal: `generate-spec` has two implementations (old inline, new WorkflowRuntime-backed), both green, but only one is the intended substrate.

Closing this debt now costs one day. Closing it after five features land means untangling five additional touch points per finding. The Workflow Domain Layer was designed as the single orchestration substrate for multi-step AI chains. Bootstrap bypasses it today. Every future feature that copies the bypass pattern erodes the architectural boundary that makes the system auditable and testable as a unit.

**Value Proposition**: Clear structural debt before five SaaS features land, so each arrives with clean patterns to copy rather than wrong ones.

---

## Scope

### What This Epic Covers

- **Duplicate route deletion** (§2) — remove the old `/api/ai/text/generate-spec` inline handler once Angular switches to the WorkflowRuntime-backed URL; drop the openapi path and regenerate DTOs
- **Bootstrap workflow migration** (§1) — complete or excise the dangling `workflow_ref` so bootstrap uses the same WorkflowRuntime substrate as `task_gen` and `spec_gen`; §1 classification (cleanup vs. feature-finish) is a scope gate resolved before this task starts
- **Prompts god-module split** (§3) — redistribute `modules/ai/prompts/__init__.py` (779 LOC) into per-feature files after §1 and §2 delete their prompt functions; `__init__.py` becomes a re-export shim
- **God-function decomposition + DRY extraction** (§4, §5) — break `run_generation` (139 LOC) into named sub-functions; extract a shared `_section()` helper from three parallel-shaped functions in `modules/data/templates/generators.py`

### What This Epic Does NOT Cover

- ❌ **Test coverage additions** (§6) — adds LOC; belongs in a coverage epic triggered when `context/` or `projects/` grow new features
- ❌ **Discovery beyond the six seed findings** — new findings from the audit go into `findings.md` for a follow-on pass; this epic is capped at the seed list
- ❌ **Single-step `chain_adapter` route migration** — single AI calls don't benefit from a workflow wrapper; leaving them inline is architecturally correct
- ❌ **FS→SQL persistence migration** — scoped to the persistence brain dump
- ❌ **`quality/` → `pipeline/` rename** — defer to the modular-restructure epic
- ❌ **Frontend Angular audit** — separate concern; revisit when frontend tech debt is felt
- ❌ **Full SOLID compliance audit** — this epic targets observed structural debt only

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Delete duplicate generate-spec route** | Angular URL switch (pre-req) | — | 0.5 days | High |
| 2 | **Complete bootstrap workflow migration** | Task 1; §1 classification gate | — | 0.5 days | High |
| 3 | **Split prompts god module** | Tasks 1 & 2 (prompt deletions must settle first) | — | 0.5 days | High |
| 4 | **Decompose run_generation + extract DRY helper** | None | ✓ with Task 3 | 0.5 days | Low |

### Task 1: Delete duplicate generate-spec route

The old `/api/ai/text/generate-spec` handler and its associated prompt function survive alongside the new WorkflowRuntime-backed `/api/spec-gen/generate`. Angular must switch its call URL before the old handler can be deleted; deletion then cascades to the openapi path and a `make generate-dtos` regeneration committed in the same changeset.

**Port budget**: ~60 LOC backend handler + ~30 LOC prompt function + ~15 LOC openapi path; DTO delta committed in same changeset.

### Task 2: Complete bootstrap workflow migration

Bootstrap returns 202 and creates a `WorkflowExecution` record with a mismatched `workflow_ref`, but the background thread calls `chain_adapter.generate()` three times inline instead of invoking `WorkflowRuntime`. The classification gate must be resolved before work starts: if the inline-to-runtime swap is structural (no observable behaviour change), the migration completes here; if it is a feature-finish (behaviour delta), this task is descoped to deleting the dangling `workflow_ref` only and the full migration is filed as a separate brain dump.

**Port budget**: ~310 LOC removed if migration completes (inline calls + now-unused bootstrap prompt functions); ~5 LOC if scoped to ref-deletion only.

### Task 3: Split prompts god module

`modules/ai/prompts/__init__.py` at 779 LOC is the primary future-debt magnet — five queued SaaS epics will each append to it if it remains a single file. After Tasks 1 and 2 delete their prompt functions, the remaining content is split into per-feature files; `__init__.py` shrinks to a re-export shim so no callers change.

**Port budget**: `__init__.py` 779 → ~30 LOC; +4 files of ~80–200 LOC each; net LOC unchanged but largest-file metric drops from 779 to ≤200.

### Task 4: Decompose run_generation + extract DRY helper

Two independent structural improvements with no interaction with Tasks 1–3: break `run_generation` (139 LOC) into named sub-functions (~20 LOC each), and extract a `_section()` helper from the three parallel-shaped markdown-emitting functions in `modules/data/templates/generators.py`. Neither changes behaviour.

**Port budget**: ~60 LOC net removed from `generators.py`; `task_gen.py` net-zero (decomposition, not deletion).

---

## Success Criteria

- ✅ All tests green at every commit — count same or higher, zero forced reverts
- ✅ Net ≥ 500 LOC removed from `modules/` (excluding generated DTOs and test files)
- ✅ Largest single file ≤ 200 LOC (down from 779)
- ✅ Largest single function ≤ 30 LOC (down from 139)
- ✅ Zero new lint violations (`make lint` clean after every commit)
- ✅ `findings.md` artifact committed with discovery-prompt output and per-finding disposition
- ✅ `featureModules_mustNotImportProvidersDirectly` coupling test stays green throughout
- ✅ `dtos/models.py` regenerated and committed in the same changeset as every openapi.yaml edit

---

## Non-Goals

- ❌ **Adding new tests** — net-positive LOC; belongs in a coverage epic
- ❌ **Behaviour changes** — if a refactor requires changing test logic, revert and file a separate bug-fix PR
- ❌ **New shared abstractions** — no generic runners, registries, or base classes introduced for a single consumer
- ❌ **openapi.yaml shape changes beyond §2 path deletion** — no route URL moves, no new paths

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview