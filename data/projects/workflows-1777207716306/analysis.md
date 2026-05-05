# 🔍 Workflows — Analysis

## The Problem
Routes on master inline their own multi-step orchestration; there is no shared runner, no typed execution state, and no event contract. The "chains-as-code" default was a deliberate deferral — the moment a GUI consumer names itself, workflows must become serializable data, not callable closures. This is a one-way door: once workflows are data, Python callables become the escape hatch, not the default.

## Hard Constraints
- The Adapter boundary (`from modules.chain import adapter`) is structurally enforced by an existing test and must not break across any phase.
- No DSL, no expression language, no `eval` in workflow templates — named hard line, not a preference.
- No anonymous callables in JSON workflows; compute steps must be registered by name before the JSON loader can reference them.
- `ChainResult` as ACL and `MockProvider` as Null Object are shipped invariants; the new layer extends them, does not replace them.
- No direct push to `master` — always PR.

## Open Questions
- **GUI consumer identity** — the entire one-way door is motivated by "a GUI consumer," but no GUI is named, scoped, or committed. Is the GUI in this epic or a downstream consumer epic gated on Phase 3? (Options: GUI is Phase 3 of this epic / GUI is a separate epic / confirm a GUI exists and name it.)
- **`chain-primitive` epic disposition** — re-scope as Phase 1 of this work (`ChainStep` becomes a Step kind) or ship standalone then integrate. Must resolve before Phase 1 scope locks.
- **Layer name** — `workflows` recommended, not ratified. Must settle before routes and tests are written. (Options: `workflows` / `pipeline` / clean up `chain` in place.)
- **Cross-feature workflow ownership** — when `spec_gen` composes a sub-workflow from `photoshoot`, who owns the contract? (Options: owning feature keeps ownership and consumer imports by ref / shared workflows live in a `common` module / cross-feature composition deferred until a second case exists.)

## Dependencies & Sequencing
- `chain-primitive` disposition blocks Phase 1 scope lock.
- `WorkflowRepository` FS adapter must exist before the JSON loader can read workflow definitions.
- StepKind Registry must be populated before the JSON loader's dispatch table can resolve step kinds.
- `GET /api/step-kinds` and `GET /api/providers` are prerequisites to any GUI palette work.
- Phase 1 (workflows-as-code) gates Phase 2 (multi-modal); Phase 2 gates Phase 3 (JSON + GUI).

## Explicitly Out of Scope
- **The GUI builder** — this epic is the backend contract the GUI consumes; the GUI is a separate consumer epic. Re-scope trigger: a named GUI project with a committed timeline.
- **Database adapter for `WorkflowRepository`** — no multi-user persistence requirement exists. Re-scope trigger: a second user context or a persistence SLA.
- **Async runtime** — synchronous generators carry Phase 1 and Phase 2. Re-scope trigger: parallel step branches sharing a thread pool.
- **Workflow-level middleware (Chain of Responsibility)** — no auth/quota pipeline consumer named. Re-scope trigger: a second workflow-level pre-execute concern.
- **Workflow versioning and migration** — brain dump is silent on this; speculative infrastructure until a breaking schema change occurs.