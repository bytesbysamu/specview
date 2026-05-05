# Spec Index: Spec Doc

> Entry point for Claude Code and humans to understand this capability.

**Last Updated**: 2026-03-30

---

## Active Specs

| Document | Purpose | Location |
|----------|---------|----------|
| **Analysis** | Problems driving this capability | [analysis.md](./analysis.md) |
| **Epic** | Scope, tasks, success criteria | [epic.md](./epic.md) |
| **Architecture** | System design and decisions | [architecture.md](./architecture.md) |
| **Timeline** | Status tracking | [timeline.md](./timeline.md) |
| **Task 1** | Document-First Editor guide | [task-1-document-first-editor.md](./task-1-document-first-editor.md) |
| **Task 2** | AI Text Operations guide | [task-2-ai-text-operations.md](./task-2-ai-text-operations.md) |
| **Task 3** | Spec Bootstrap guide | [task-3-spec-bootstrap.md](./task-3-spec-bootstrap.md) |
| **Task 4** | Agent Integration guide | [task-4-agent-integration.md](./task-4-agent-integration.md) |
| **Task 5** | Git Integration guide | [task-5-git-integration.md](./task-5-git-integration.md) |

---

## Document Flow

```
Analysis (problems)
    │
    ▼
Epic (scope, tasks)
    │
    ▼
Architecture (design)
    │
    ▼
Implementation (per task)
    │
    ▼
Timeline (status)
```

---

## Quick Reference

| When you need... | Read this |
|------------------|-----------|
| Why we're building this | [Analysis](./analysis.md) |
| What we're building | [Epic](./epic.md) |
| How we're building it | [Architecture](./architecture.md) |
| How to implement a task | Task guides (task-*.md) |
| Current status | [Timeline](./timeline.md) |

---

## For Claude Code

To work on this capability:

```
@spec-index.md
@epic.md
@architecture.md

What's the next task to implement?
```

To implement a specific task:

```
@spec-index.md
@architecture.md
@task-1-document-first-editor.md

Implement Task 1: Document-First Editor
```

---

## Key Concepts

- **Document-first**: No chat interface. All interaction through the document.
- **Specs as source**: Markdown files are the source of truth.
- **AI operations**: Rewrite, expand, compress, clarify, generate — the primitives.
- **Local-first**: Files on disk. No cloud dependency.

---

## Related Documents

- [Analysis](./analysis.md) – Problems
- [Epic](./epic.md) – Scope
- [Architecture](./architecture.md) – Design
- [Timeline](./timeline.md) – Status
