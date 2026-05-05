# Spec Doc -- Self-Spec

> The product that generates spec folders for every other product, documented in its own format.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [Analysis](./analysis.md) | Problems driving the self-spec |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | Technical design: how the pipeline works and why |
| [Timeline](./timeline.md) | Status tracking |

## Overview

Spec Doc is a document-first AI editor where text operations replace chat, specs become the source of truth, and documents are actionable. The product enforces a strict document hierarchy -- Analysis, Epic, Architecture, Timeline, Implementation Guides -- on every project it bootstraps. Today, Spec Doc itself has 35+ markdown files scattered across `specs/`, 13 reflections, a quality rubric, and 9 system prompts embedded inline in `server.js`, but none of it follows the hierarchy the product enforces on others.

This self-spec applies the product's own methodology to itself. It carves Spec Doc into 6 capabilities, documents the 9 system prompts that are the product's core logic, and creates the entry point a new operator (or future-Sam) needs to understand what the product does and why.

The irony is the point. If Spec Doc cannot spec itself, the methodology it sells is incomplete. This set of documents closes that gap.

## Capabilities

| # | Capability | Summary |
|---|-----------|---------|
| 1 | Project Management | CRUD for project folders, file persistence, metadata |
| 2 | AI Text Operations | Rewrite, expand, compress, clarify, generate -- the atomic text transforms |
| 3 | Spec Bootstrapping | Braindump to 5-file capability folder (generate-spec prompt) |
| 4 | Task-Spec Generation | Per-task implementation guides with 7 context blocks (impl-guide prompt) |
| 5 | Quality Gating | Lint (braindump pre-flight), Review (6-dimension scoring), deviation counting |
| 6 | Codebase Scanning | Walk filesystem + LLM summary to produce codebase.md context |

## Document Flow

```
Analysis (what's broken)
    |
    v
Epic (what to build, 14 tasks across 6 capabilities)
    |
    v
Architecture (how it works: 9 prompts, 4 context blocks, adapter pattern)
    |
    v
Timeline (status tracking -- ONLY place for status)
```

## For Claude Code

```
@projects/spec-doc-self-spec-1776416446652/spec-index.md
@projects/spec-doc-self-spec-1776416446652/epic.md
@projects/spec-doc-self-spec-1776416446652/architecture.md

Implement task N from the epic. Follow the architecture patterns.
```

## Related Documents

- [Product Thesis](../../specs/spec-doc-spec.md) -- Why this product exists
- [Quality Rubric](../../specs/quality-rubric.md) -- Scoring criteria for generated docs
- [Hierarchy Definition](../../specs/hierarchy-definition.md) -- Product > Capability > Feature structure
- [Existing Epic](../../specs/epic.md) -- Original MVP roadmap (pre-dates this self-spec)
- [Existing Architecture](../../specs/architecture.md) -- Original Spring Boot architecture (superseded by current Express stack)

---

**Last Updated**: 2026-04-16
