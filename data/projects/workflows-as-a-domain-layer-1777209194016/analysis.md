# 🔍 Workflows as a Domain Layer — Analysis

## The Problem
Routes on master do their own multi-step orchestration inline; there is no runner. A GUI consumer requires workflows to be *data*, which flips the settled "chains-as-code" default and is explicitly a one-way door. This epic introduces the data-first model while keeping Python as an escape hatch for steps the data form cannot express.

## Hard Constraints
- `featureModules_mustNotImportProvidersDirectly` structural test must stay green throughout — any Step/Workflow refactor that breaks it ships broken.
- `chain.adapter` rename is out of scope here; a separate cleanup epic owns that and the test update it triggers.
- No anonymous callables in JSON workflows — `Compute` steps are registered by name only (security + discoverability).
- Interpreter pattern is a hard line: no DSL, no expression language, no `eval`, ever.

## Open Questions
- **chain-primitive epic fate** — Re-scope as Phase 1 (cleaner; its `ChainStep` becomes a `Step` kind), or ship it standalone first and treat this as a follow-on (avoids mid-flight pivot). Unresolved; blocks Phase 1 scope.
- **Layer name** — `workflows` (recommended) vs keeping `chain`. This names a directory and import path; once merged it's another test-update epic to rename.
- **`WorkflowExecution` persistence in Phase 1** — In-memory only (replacing `task_gen`'s status dict), or also written to FS alongside `WorkflowRepository`? The brain dump promotes the Command type but does not commit execution storage to disk.
- **`task_gen` migration path** — Deleted when Phase 1 lands, wrapped by the new runtime, or left running in parallel? Parallel means two status-tracking systems during the transition window.

## Dependencies & Sequencing
- `AbstractStep` (Template Method) must exist before Decorator wrappers can compose around it.
- `WorkflowRepository` FS adapter must exist before feature modules can migrate off inline orchestration.
- Phase 2 (Bridge + Pool + Composite) requires Phase 1's Step/Workflow container to be stable.
- Phase 3 (JSON loader + GUI endpoints) requires Phase 2's Registry and ProviderPool.

## Explicitly Out of Scope
- **Chain of Responsibility middleware** (auth → quota → execute pipeline) — no current consumer; trigger: a second feature needing workflow-level pre-execute hooks.
- **`WorkflowRepositoryDb`** — deferred until multi-user persistence is a named requirement; trigger: team/tenant feature request.
- **Async execution** — deferred until a `Parallel` step ships with a latency SLA; trigger: concrete parallel-branch use case.
- **Actual multi-modal vendor integrations** (Replicate, ElevenLabs, Whisper, etc.) — Bridge defines the shape in Phase 2; implementations land only when a consuming feature is scoped.
- **GUI builder endpoints** (`GET /api/providers`, `GET /api/step-kinds`) — Phase 3 only; trigger: a GUI consumer is named.