# 🔍 Codebase Cleanup — Analysis

## The Problem
spec-doc-api carries silent migration debt: bootstrap and generate-spec are both half-migrated to WorkflowRuntime, but tests pass on both old and new paths, so the debt is invisible. Five queued SaaS epics will each land prompt functions into the 779-LOC god module and copy the half-migrated bootstrap pattern if the foundation isn't cleared first.

## Hard Constraints
- All 764 tests stay green at every commit — no test-logic changes, no exceptions.
- No behavior changes — **but §1 violates this**: swapping three inline `chain_adapter.generate()` calls for `WorkflowRuntime.run()` changes execution semantics, not just structure. This is a feature-finish, not a cleanup. Resolve before work begins.
- Blueprint names, route URLs, and openapi.yaml path shapes are frozen (except §2's deletion).
- No speculative abstractions — builder context explicitly bans it.

## Open Questions
- **§1 classification**: is the bootstrap migration cleanup (structural) or a feature-finish (behavior delta)? Options: (a) complete it here with a runtime smoke test added; (b) delete only the dangling `workflow_ref` string, leave inline calls intact, file migration as a separate PR; (c) skip §1 entirely this pass.
- **Scope ceiling for the open-ended audit**: discovery prompts may surface 10+ findings beyond the six seeds. Options: (a) fix everything found in one PR; (b) fix the six seeds, document the rest in `findings.md` for a follow-on; (c) two-day hard stop regardless of list length.
- **Modular-restructure sequencing**: both this pass and `braindump-modular-restructure.md` touch `modules/ai/` and `prompts/`. If restructure moves files first, §3's split targets wrong paths. Options: (a) this cleanup lands first, restructure rebases on top; (b) restructure lands first, cleanup is re-scoped; (c) one combined PR.

## Dependencies & Sequencing
- §2 requires the Angular URL switch before the backend deletion — deleting the old route while Angular still calls it breaks the running app.
- §3 (split prompts module) must follow §1 and §2 — both delete prompt functions that would otherwise be redistributed into the new files.
- `make generate-dtos` runs after every openapi.yaml edit; regenerated `dtos/models.py` commits in the same changeset.
- §4 and §5 are fully independent and can land in any order.

## Explicitly Out of Scope
- **§6 (add context/ and projects/ tests)** — adds lines; contradicts the LOC-removal frame; belongs in a test-coverage epic. Trigger: when those modules grow new features.
- **Unbounded open-ended discovery** — "open-ended + ≥500 LOC target" is a scope inflation machine. Cap this PR at the six seed findings; new discoveries land in `findings.md` for a follow-on.
- Everything the brain dump already excluded: full SOLID audit, frontend, FS→SQL migration, type annotations, chain_adapter migration for single-step routes.