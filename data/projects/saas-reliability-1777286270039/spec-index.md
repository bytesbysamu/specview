# 📋 Spec Index: SaaS Reliability

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

## Task Guides

| # | Task | Guide |
|---|------|-------|
| 1 | Cooperative Cancellation in WorkflowRuntime | [task-1-cooperative-cancellation.md](./task-1-cooperative-cancellation.md) |
| 2 | Streaming Partial Buffer in AICall | [task-2-streaming-partial-buffer.md](./task-2-streaming-partial-buffer.md) |
| 3 | Bootstrap Workflow + Per-Step Sub-Workflows | [task-3-bootstrap-sub-workflows.md](./task-3-bootstrap-sub-workflows.md) |
| 4 | Retry, Regenerate, Cancel Routes + Polling Surface | [task-4-retry-cancel-routes.md](./task-4-retry-cancel-routes.md) |
| 5 | Angular Live Preview, Cancel, Regenerate | [task-5-angular-live-preview.md](./task-5-angular-live-preview.md) |

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

## For Claude Code

To work on this capability:

```
@saas-reliability/epic.md
@saas-reliability/architecture.md

Implement the next task from the backlog.
Follow patterns in architecture.md.
```

---

**Last Updated**: 2026-04-26
