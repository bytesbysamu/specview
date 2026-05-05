# 📅 Timeline: Spec Doc

**Last Updated**: 2026-03-30

> Status tracking for this capability. This is the ONLY place for status.
> Epic and Architecture docs contain Priority, not Status.

---

## Done

| # | Task | Completed | Effort | Notes |
|---|------|-----------|--------|-------|
| — | — | — | — | — |

---

## In Progress

| # | Task | Started | Effort | Notes |
|---|------|---------|--------|-------|
| — | — | — | — | — |

---

## Backlog

| # | Task | Effort | Priority | Parallel | Notes |
|---|------|--------|----------|----------|-------|
| 1 | **Document-First Editor** | 3 days | High | — | Foundation |
| 2 | **AI Text Operations** | 2 days | High | 5 | Core primitives |
| 3 | **Spec Bootstrap** | 2 days | High | — | Brain dump → specs |
| 4 | **Agent Integration** | 2 days | High | — | Specs → Claude Code |
| 5 | **Git Integration** | 1 day | Medium | 2 | Export & versioning |

---

## Epic Progress

| Metric | Count |
|--------|-------|
| Done | 0 |
| In Progress | 0 |
| Backlog | 5 |
| **Total** | **5** |

---

## Execution Order

```
┌─────────────────────────────────────────────────────────────┐
│  MAIN TRACK                │  PARALLEL TRACK               │
├────────────────────────────┼────────────────────────────────┤
│                            │                                │
│  Task 1 (Editor)           │                                │
│       │                    │                                │
│       ├────────────────────┼────────────┐                   │
│       │                    │            │                   │
│       ▼                    │            ▼                   │
│  Task 2 (AI)               │       Task 5 (Git)             │
│       │                    │                                │
│       ▼                    │                                │
│  Task 3 (Bootstrap)        │                                │
│       │                    │                                │
│       ▼                    │                                │
│  Task 4 (Agent)            │                                │
│                            │                                │
└────────────────────────────┴────────────────────────────────┘
```

---

## Related Documents

- [🎯 Epic](./epic.md) – Task definitions and scope
- [🏗️ Architecture](./architecture.md) – Design decisions
- [📋 Spec Index](./spec-index.md) – Document overview
