# 📋 Spec Index: SaaS Anthropic SDK Provider

> Single source of truth for this capability's specifications.
> Claude Code reads this to understand available context.

---

## Active Specs

| Document | Purpose | Location |
|----------|---------|----------|
| Analysis | Problems driving this capability | [analysis.md](./analysis.md) |
| Epic | Scope, tasks, success criteria | [epic.md](./epic.md) |
| Architecture | System design & decisions | [architecture.md](./architecture.md) |
| Timeline | Status tracking | [timeline.md](./timeline.md) |

---

## Document Flow

```
Analysis ──→ Epic ──→ Architecture ──→ Implementation
(Problems)   (Scope)   (Design)        (How-to)
```

---

## Quick Reference

| When you need... | Read this |
|------------------|-----------|
| Why we're building this | [Analysis](./analysis.md) |
| What we're building | [Epic](./epic.md) |
| How it's designed | [Architecture](./architecture.md) |
| Task status | [Timeline](./timeline.md) |

---

## Related Capabilities (Already Shipped)

| Capability | Seam |
|------------|------|
| modular-restructure | This capability lands inside the new `modules/{ai,runtime,data,quality}` shape; no path drift |
| persistence | Independent track; this capability writes nothing to disk |
| monetisation | Consumes `/api/ai/stats` later for per-tenant attribution; no contract change here |
| operations-infra | Coolify deploy job sets `ANTHROPIC_API_KEY`; startup gate (Task 5) enforces the contract |

---

## For Claude Code

To work on this capability:

```
@saas-anthropic-sdk-provider/epic.md
@saas-anthropic-sdk-provider/architecture.md

Implement the next task from the backlog.
Follow patterns in architecture.md.
```

---

**Last Updated**: 2026-04-26
