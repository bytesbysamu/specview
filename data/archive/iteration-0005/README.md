# 📖 Spec Doc

> Overview and quick start for this capability.

---

## What This Is

Spec Doc is a capability defined by the following documents:

| Document | Purpose |
|----------|---------|
| [📋 Spec Index](./spec-index.md) | Entry point for Claude Code |
| [🔍 Analysis](./analysis.md) | Problems we're solving |
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | System design |
| [📅 Timeline](./timeline.md) | Status tracking |

---

## Document Type Legend

| Emoji | Type | Purpose |
|-------|------|---------|
| 📖 | README | Overview and quick start |
| 📋 | Spec Index | Entry point, document directory |
| 🔍 | Analysis | Problems driving this capability |
| 🎯 | Epic | Scope, tasks, success criteria |
| 🏗️ | Architecture | System design and decisions |
| 🛠️ | Implementation | Task-specific how-to guide |
| 📅 | Timeline | Status tracking (ONLY place for status) |

---

## Quick Start

1. Read [🔍 Analysis](./analysis.md) to understand the problems
2. Read [🎯 Epic](./epic.md) to understand scope and tasks
3. Read [🏗️ Architecture](./architecture.md) before implementing
4. Track progress in [📅 Timeline](./timeline.md)

---

## For Claude Code

```
@spec-index.md
@epic.md
@architecture.md

Implement the next task in the backlog.
```

---

## Execution Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Task 1 (Editor)                                           │
│        │                                                     │
│        ├──────────────────────────┐                         │
│        │                          │                          │
│        ▼                          ▼                          │
│   ┌─────────────────┐     ┌─────────────────┐               │
│   │ Task 2: AI Ops  │     │ Task 5: Git     │  PARALLEL     │
│   └────────┬────────┘     └─────────────────┘               │
│            │                                                 │
│            ▼                                                 │
│   ┌─────────────────┐                                       │
│   │ Task 3: Bootstrap│                                      │
│   └────────┬────────┘                                       │
│            │                                                 │
│            ▼                                                 │
│   ┌─────────────────┐                                       │
│   │ Task 4: Agent   │                                       │
│   └─────────────────┘                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Documents

- [📋 Spec Index](./spec-index.md) – Full document list
- [🎯 Epic](./epic.md) – What we're building
- [📅 Timeline](./timeline.md) – Current status
