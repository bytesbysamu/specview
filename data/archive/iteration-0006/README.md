# 📖 Spec Doc

> Overview and quick start for this capability.

**Generated**: 2026-03-30
**Generator**: Spec Doc v1.0

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

| Emoji | Type | ONE Job |
|-------|------|---------|
| 📖 | README | Overview and quick start |
| 📋 | Spec Index | Entry point, document directory |
| 🔍 | Analysis | Problems driving this capability |
| 🎯 | Epic | Scope, tasks, success criteria |
| 🏗️ | Architecture | System design and decisions |
| 🛠️ | Implementation | Task-specific how-to guide |
| 📅 | Timeline | Status tracking (ONLY place for status!) |

---

## Reading Order

**For Understanding** (read in order):

```
🔍 Analysis → 🎯 Epic → 🏗️ Architecture → 🛠️ Tasks
  (Why)        (What)      (How)           (Do)
```

**For Implementation** (reference as needed):

```
📋 Spec-Index → 🎯 Epic → 🛠️ Task Guide → 📅 Timeline
   (Find)        (Scope)     (Steps)        (Track)
```

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

**Execution Notes**:
- Task 1 is foundation (blocks all others)
- Tasks 2 and 5 can run in parallel
- Main chain: 1 → 2 → 3 → 4
- Total effort: 10 days (8 sequential, 1 parallel)

---

## Related Documents

- [📋 Spec Index](./spec-index.md) – Full document list
- [🎯 Epic](./epic.md) – What we're building
- [📅 Timeline](./timeline.md) – Current status
