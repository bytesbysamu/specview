# 🔍 Analysis: SpecDocV2

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-03-31

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 5 |
| MEDIUM | 4 |

---

## The Core Problem

Non-technical founders and freelancers have ideas but no efficient path from concept to working prototype. Current options force a false choice: either learn to code (months of investment), hire developers (expensive, slow communication cycles), or use no-code tools (limited, lock-in, can't customize). The gap between "I know what I want" and "I have something that works" remains unnecessarily wide.

Existing AI coding assistants help developers write code faster, but they assume the user can already code. They're power tools for carpenters, not tools that let anyone build furniture. Meanwhile, spec documents exist in Google Docs, disconnected from the code they describe—they go stale immediately and become fiction within days of implementation.

Consider: Jupyter notebooks transformed data science by connecting documentation to execution. Scientists write explanations alongside code, and both stay synchronized because they live in the same artifact. Spec Doc aims to do the same for application development—specs that execute, not specs that describe.

---

## Symptoms

Users experience:

- Writing detailed specs that developers interpret differently than intended
- Specs becoming outdated the moment implementation begins
- No visibility into what the AI agent is actually doing during code generation
- Fear of AI-generated code having security issues or bugs with no review process
- Difficulty understanding which parts of their spec produced which code
- Prototype environments that take hours to configure before any building starts
- Generated code that doesn't follow consistent patterns or conventions
- No way to iterate on specific parts without regenerating everything

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Specs disconnected from execution | Brain dump: "specs only generate... this covers 80% of prototyping needs" implies current tools don't connect specs to code | Task: Spec block implementation with agent connection |
| No code review for AI output | Brain dump: "no human reviews the code... we want multi-agent review" | Task: Multi-agent review pipeline |
| Environment setup friction | Brain dump: "containers are pre-built with next.js + shadcn... npm run dev already running" indicates this is a known blocker | Task: Pre-configured container templates |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No visibility into agent execution | Brain dump: "output streams back to the editor" listed as key feature, meaning absence is painful | Task: Implementation panel with streaming output |
| Generated code inconsistency | Brain dump: "CLAUDE.md baked in with our rules and patterns" shows need for enforced conventions | Task: Container template with embedded conventions |
| Iteration requires full regeneration | Brain dump: "block-level" mentioned as unique differentiator | Task: Block-scoped implementation |
| Preview requires manual refresh/setup | Brain dump: "live preview shows the running app" called out specifically | Task: Integrated preview panel |
| Review failures need manual intervention | Brain dump: "fixer agent addresses only what failed. max 3 iterations" | Task: Automated fix loop |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Editor capabilities limited without investment | Brain dump: "plate plus is €299... don't buy until we validate" | Task: Start with free Plate, evaluate later |
| Backend generation complexity | Brain dump: "frontend only for now... minimal pre-built backend" explicitly scopes this out | Task: Pre-built backend template |
| Container resource management | Brain dump: "each user gets their own docker container" implies isolation needs | Task: Container orchestration design |
| Agent communication reliability | Brain dump: "websocket to container" mentioned as required component | Task: Agent connector implementation |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Backend code generation | Explicitly deferred: "frontend only for now" — covers 80% of needs |
| Authentication flows | Pre-built in container template: "optional auth" |
| Database schema design | Handled by Supabase: "supabase CRUD" in template |
| Custom deployment pipelines | Beyond prototyping scope — users export or continue elsewhere |
| Collaboration features | Single-user focus for POC validation |
| Version control for specs | Later phase after core loop validated |
| Plate Plus premium components | Deferred: "don't buy until we validate" |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview