# 📋 Spec Index: Workflows as a Domain Layer

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
| 1.1 | AbstractStep Foundation | [task-1.1-abstractstep-foundation.md](./task-1.1-abstractstep-foundation.md) |
| 1.2 | Concrete Step Kinds (AICall + Compute) | [task-1.2-concrete-step-kinds-aicall-compute.md](./task-1.2-concrete-step-kinds-aicall-compute.md) |
| 2 | Workflow Container | [task-2-workflow-container.md](./task-2-workflow-container.md) |
| 3 | Workflow Runtime | [task-3-workflow-runtime.md](./task-3-workflow-runtime.md) |
| 4 | WorkflowRepository (FS Adapter) | [task-4-workflowrepository-fs-adapter-.md](./task-4-workflowrepository-fs-adapter-.md) |
| 5 | Migrate spec_gen to WorkflowRuntime | [task-5-migrate-spec-gen-to-workflowruntime.md](./task-5-migrate-spec-gen-to-workflowruntime.md) |

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
@workflows-as-a-domain-layer/epic.md
@workflows-as-a-domain-layer/architecture.md

Implement the next task from the backlog.
Follow patterns in architecture.md.
```

---

**Last Updated**: 2026-04-26
