# Spec Doc Self-Spec -- Analysis

**Purpose**: Identify the problems that make self-speccing necessary now, not later.

**Date**: 2026-04-16

---

## Summary

- **Total Issues**: 12
- **Critical**: 3
- **High**: 4
- **Medium**: 5

---

## Core Problem

Spec Doc enforces a strict documentation hierarchy on every product it bootstraps -- Analysis, Epic, Architecture, Timeline, Implementation Guides -- but does not follow that hierarchy itself. The product's core logic lives in 9 system prompts embedded as inline strings in `server.js` (lines 617-1305). These prompts encode the constellation methodology, quality rubrics, and context-block injection patterns, but none of this is documented in a spec. A new operator opening the repo finds a `specs/` folder full of philosophy documents and dated reflections, but no entry point, no task table, no architecture doc explaining why the prompts are structured the way they are. The pipeline chain (braindump -> lint -> generate -> review -> regen-task -> execute -> deviation-count) emerged over multiple sessions but lives only in conversation history, not in a spec.

---

## Structural Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No spec-index entry point for the product itself | CRITICAL | Task 1: Create self-spec folder |
| 9 system prompts undocumented -- purpose, inputs, outputs, evolution history | CRITICAL | Task 3: Document prompt inventory |
| Pipeline chain not captured anywhere (braindump -> lint -> generate -> review -> regen -> execute) | CRITICAL | Task 4: Document pipeline flow |
| `specs/architecture.md` describes a superseded Spring Boot stack, not the current Express + Claude CLI stack | HIGH | Task 5: Architecture doc for current stack |

---

## Knowledge Capture Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| 13 reflections in `specs/reflections/` contain key learnings that are not cross-referenced by any architecture or epic doc | HIGH | Task 6: Distill reflections into architecture |
| Quality rubric (`specs/quality-rubric.md`) exists but is not referenced by the architecture or used programmatically by the review prompt | HIGH | Task 7: Wire rubric into review prompt |
| 4 context blocks (builder, principles, codebase, references) are a proven pattern but not documented as an architectural decision | MEDIUM | Task 5: Architecture doc |
| Template drift between `ImplementationGuideService` and `regen-task.mjs` -- same prompt, two copies | HIGH | Task 8: Extract shared prompt template |

---

## Operational Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No onboarding path -- new contributor cannot discover what the product does without reading all of `server.js` | MEDIUM | Task 1: spec-index + Task 3: prompt inventory |
| `builder.md` and `principles.md` are persisted flat files with no UI for first-time setup | MEDIUM | Task 10: Builder/principles onboarding |
| Iteration prompt (`/api/ai/text/iterate`) has no quality gate -- output is returned raw | MEDIUM | Task 11: Add review step to iterate |
| Container execution mode (`CONTAINER_MODE`) is half-wired -- endpoints exist but no integration test | MEDIUM | Task 12: Container integration test |
| The `specs/epic.md` describes a 14-week MVP plan for a Spring Boot + GitHub + Docusaurus product that no longer matches reality | MEDIUM | This self-spec supersedes it |

---

## Open Question: Prompt Extraction

The braindump posed this question: should the 9 system prompts be extracted from `server.js` into versioned `.md` files (like the context blocks) so they can be iterated independently of code deploys, or should they stay inline because the server IS the product?

**Arguments for extraction**:
- Prompts are iterated more frequently than server code
- Versioned `.md` files enable diff-based prompt review
- Non-developer contributors could edit prompts without touching `server.js`
- Aligns with "system prompts are code" philosophy from CLAUDE.md

**Arguments for inline**:
- Server IS the product; prompts and routing logic are tightly coupled
- Extraction adds indirection (file reads, template interpolation)
- Context blocks (builder, principles, codebase, references) are already external; prompts are the glue
- Risk of drift between template placeholders and code that fills them

**Recommendation**: Extract to a `prompts/` folder with `{{placeholder}}` interpolation. The context blocks are already external files; prompts should follow the same pattern. This is Task 9 in the Epic.

---

## Out of Scope

- Rewriting the existing `specs/` philosophy documents -- they remain as historical context
- Building a prompt versioning system with rollback -- that is a future capability, not this self-spec
- Multi-user or SaaS concerns -- Spec Doc is a single-operator tool today
- Container orchestration and sandboxing -- documented as a capability but not redesigned here

---

## Related Documents

- [Epic](./epic.md) -- Scope and tasks
- [Architecture](./architecture.md) -- Technical design
- [Timeline](./timeline.md) -- Status tracking
- [Product Thesis](../../specs/spec-doc-spec.md) -- Why Spec Doc exists
- [Quality Rubric](../../specs/quality-rubric.md) -- Scoring criteria
