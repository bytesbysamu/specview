# 🏗️ Solution Architecture: Modular Restructure

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

`api/modules/` currently holds 10 flat peer packages. The flat shape was appropriate at 3 modules because the groupings were obvious; at 10, the conceptual clusters — AI generation, execution infrastructure, storage, and pipeline quality — exist only in the developer's head. The filesystem offers no signal. Every new SaaS module added without a restructure deepens that silence until `modules/` becomes a 17–20 entry index that requires prior knowledge to navigate.

The restructure externalizes the existing mental model into four named packages: `ai/` (all generation routes, prompts, and services), `runtime/` (chain adapter and workflow engine), `data/` (projects, context, templates), and `quality/` (pipeline self-improvement, already cohesive). Future SaaS capabilities — auth, billing, usage, observability — land as independent peer packages at the `modules/` root, not sub-domains of the four core packages. The structural test enforces this boundary so the sprawl cannot re-emerge silently.

The change is purely mechanical: file moves and import-path rewrites. No function body is touched, no route URL changes, no Blueprint names change, no DTOs drift. `make test` passes before the first file moves (scaffold) and must pass again after the last import fix (import rewrite). The diff is large in line count and zero in semantic content.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| ELA #1 — Adapter Boundary | `modules/runtime/chain/adapter.py` remains the sole AI import point; its internal path changes but its role does not |
| ELA #2 — Blueprint Module Structure | `routes.py`, `service.py`, `prompts.py` ownership per module is preserved; files move, not their responsibility split |
| ELA #5 — Not-Yet-Built | `runtime/` is described as the concrete `chain/` + `workflows/` pair it houses today, not as a generic runner framework |
| ELA #6 — Workflow Domain Layer | `runtime/workflows/` continues to own `WorkflowRuntime` and `AbstractStep`; AI-specific workflow definitions live in `ai/workflows/` |

---

## System Boundaries

### What This System Includes

- Four top-level packages (`ai/`, `runtime/`, `data/`, `quality/`) replacing 10 flat modules
- `__init__.py` scaffolding for each new subdirectory before any source files move
- File relocation for 16 source files per the confirmed mapping in the Epic
- Import-path rewrites for ~50 `from modules.X import Y` references across routes, services, `create_app.py`, and tests
- An updated `ENABLED_MODULES` block in `create_app.py` pointing to new dotted import paths
- A `packages_areInExpectedHierarchy` assertion in `tests/test_structural.py` that pins the 4-package boundary and documents the `saas_optional` allowlist decision

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Logic changes of any kind | Constraint is absolute; zero semantic change in this refactor |
| API URL changes | Blueprint URL prefixes live in Blueprint declarations, not file paths |
| Blueprint name changes | `spec_gen_bp`, `task_gen_bp`, etc. are the registered app names; import path is separate |
| `openapi.yaml` changes | The contract is independent of package layout |
| Test assertion changes | Test logic moves with its module; only file location and import paths change |
| SaaS module code (auth, billing, usage, observability) | This epic creates their slots; each SaaS capability is its own epic |
| Per-package `CLAUDE.md` files | `api/CLAUDE.md` remains the single source of truth |
| `dtos/` relocation | Generated artifact at api root; stays where `datamodel-codegen` writes it |
| Renaming `quality/` to `pipeline/` | Separate concern, separate PR |
| Splitting `chain/` into sub-packages | Exactly one consumer (`ai/`) exists today; ELA #5 prohibits speculative splits |

---

## Component Design

### `ai/` Package

**Purpose**: Consolidates all AI generation: the six text endpoints, spec generation, task generation, and implementation guide prompts. These three flat modules shared the chain adapter through the same workflow runtime and had no meaningful boundary between them — grouping them makes their coupling an asset, not noise.

**Key Parts**:
- `ai/routes/text.py` — was `modules/ai/routes.py`; consumed by Angular frontend via HTTP
- `ai/routes/spec_gen.py` — was `modules/spec_gen/routes.py`; consumer: Angular spec generation view
- `ai/routes/task_gen.py` — was `modules/task_gen/routes.py`; consumer: Angular task view with 202 polling
- `ai/services/spec_gen.py` and `ai/services/task_gen.py` — pure business logic; no Flask imports
- `ai/prompts/` — all prompt-construction functions; consumers are the service files above
- `ai/workflows/spec_gen/generate_spec.py` — AI-specific Workflow definition; consumed by `ai/services/spec_gen.py` through `runtime/workflows/`

**Patterns**: ELA #2 (routes own no logic; services own no Flask); ELA #6 (Workflow definitions owned by the domain that uses them, not the runtime that runs them)

---

### `runtime/` Package

**Purpose**: Generic execution infrastructure that the `ai/` package depends on but does not own. `chain/` provides the adapter boundary; `workflows/` provides the execution engine. Neither has consumers outside `ai/` today — they live in `runtime/` because they are infrastructure, not because they are shared.

**Key Parts**:
- `runtime/chain/adapter.py` — sole AI import point; provider selected by `CHAIN_PROVIDER` env var; consumer: every service in `ai/`
- `runtime/chain/providers/` — `cli.py` and `anthropic_sdk.py` behind the adapter interface
- `runtime/workflows/runtime.py` — `WorkflowRuntime` execution driver; consumer: `ai/services/spec_gen.py`
- `runtime/workflows/repository.py` — `WorkflowRepository` FS adapter; consumer: `WorkflowRuntime`
- `runtime/workflows/steps/` — `AbstractStep`, `AICall`, `Compute`; consumer: `ai/workflows/spec_gen/`

**Patterns**: ELA #1 (adapter boundary enforced); ELA #6 (runtime drives, domain defines)

---

### `data/` Package

**Purpose**: All filesystem-backed storage and content retrieval. `projects/`, `context/`, and `templates/` were already peers conceptually — grouping them names the boundary explicitly.

**Key Parts**:
- `data/projects/service.py` — `get_project()`, `update_file()`, `list_projects()`; consumers: `ai/` routes and `quality/` pipeline
- `data/context/service.py` — `read_context()`, `write_context()`; consumers: `ai/` prompt builders
- `data/templates/` — deterministic generators (spec-index, timeline, README); consumer: Angular template view via HTTP

**Patterns**: ELA #2 (service files only; no Flask in business logic)

---

### `quality/` Package

**Purpose**: Pipeline self-improvement linter. Already cohesive; moved in place. Sits at `modules/quality/` before and after the restructure.

**Key Parts**: Unchanged — whatever `quality/` contains today is preserved exactly.

**Patterns**: Treated as a peer top-level package, not a sub-domain of the four core packages.

---

### Structural Shape Test

**Purpose**: Prevents silent re-sprawl. The `packages_areInExpectedHierarchy` test asserts that every directory under `modules/` is either in the four-package set, in the `saas_optional` allowlist, or fails CI. Any engineer adding a fifth top-level package must explicitly acknowledge it in this test — the PR diff makes the decision visible.

**Key Parts**: One test function in `tests/test_structural.py`; one inline comment recording the `saas_optional` allowlist decision and its rationale. Consumer: CI pipeline.

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Nest packages under `modules/{ai,runtime,data,quality}/` | The cluster boundary is conceptual, not cosmetic; a real namespace should reflect it | One extra import segment in every `from modules.X` reference; ~50 mechanical edits |
| SaaS modules as peer top-level packages, not sub-domains | Auth, billing, usage, observability are independent capabilities with their own routes, services, and DTOs; forcing them under `ai/` or `data/` would be a false grouping | `modules/` root grows by one entry per SaaS module; the structural test manages this with an explicit allowlist |
| `quality/` stays at top level, unchanged | It's already cohesive and has no sibling that belongs beside it inside one of the three core packages | Asymmetry with `ai/runtime/data/` hierarchy — `quality/` is flat while peers are nested; acceptable given it's already correct |
| `chain/` stays whole inside `runtime/` | Exactly one consumer (`ai/`) exists today; ELA #5 prohibits splitting for a single consumer | If a second non-AI consumer of the chain adapter emerges, `runtime/chain/` may need to become a public cross-package API |
| Exhaustive `saas_optional` allowlist vs naming convention | Decision deferred to Task 1 inspection — must be resolved before Task 5 codes the test | Exhaustive list is safe but requires a PR edit for each new SaaS module; naming convention is open-ended but harder to audit |
| Scaffold directories before moving files | `make test` can pass between Task 2 and Task 3; broken imports only exist between Task 3 and Task 4 | One extra task boundary; reduces the blast radius of a mid-move interruption |

---

## Execution Flow

```
Task 1 (read-only)
  Confirm module inventory + resolve 3 open questions
  → Outputs: confirmed file-by-file mapping, saas_optional decision

Task 2 (additive only)
  Scaffold directory trees + __init__.py stubs
  → make test must pass

Task 3 (moves only)
  Relocate 16 source files per confirmed mapping
  → Imports intentionally broken; make test expected to fail

Task 4 (import rewrites)
  Rewrite ~50 from-modules imports; update ENABLED_MODULES in create_app.py
  → make test must pass; no assertion changes

Task 5 (pin structure)
  Add packages_areInExpectedHierarchy to tests/test_structural.py
  → make test must pass; saas_optional decision from Task 1 encoded inline
```

---

## Open Questions

- **Does `implementation_guide/routes.py` exist?** If it does, it needs a Blueprint entry in `ENABLED_MODULES`; if it doesn't, it's prompt-only and needs no route registration. Inspection in Task 1 resolves this before any files move.

- **Does `quality/` register a Blueprint in `create_app.py`?** If yes, `ENABLED_MODULES` must include the (unchanged) `modules.quality.routes` entry. If no, it's a service-only module and requires no update. Task 1 resolves this.

- **Exhaustive `saas_optional` allowlist or naming-convention check?** An exhaustive `{"auth", "billing", "usage", "observability"}` set is auditable and fails loudly for any unexpected name; a convention check (`name in known_saas_names or name.startswith("saas_")`) is more open-ended. The correct answer depends on whether the four named SaaS modules are the complete set or an open-ended list. Task 1 must record the decision; Task 5 must encode it with the rationale inline.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview