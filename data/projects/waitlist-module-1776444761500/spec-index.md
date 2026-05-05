---
sidebar_position: 0
---

# Waitlist Module — Spec Index

**Product**: Bubls
**Capability**: Email capture for landing page and Trendfy subscriber port
**Status**: Spec complete, not started

---

## Documents

| Spec | Purpose | Status |
|------|---------|--------|
| [Analysis](./analysis.md) | Constraints, open questions, scope knife | Done |
| [Epic](./epic.md) | Scope, tasks, success criteria | Done |
| [Architecture](./architecture.md) | Technical design, module layout, migration plan | Done |
| [Timeline](./timeline.md) | Task status tracker | Done |

---

## One-Line Summary

Replace the standalone `email-api/` microservice with a proper `server/modules/waitlist/` submodule inside the Bubls Flask backend. Port Trendfy `bubls_subscribers` into the same table with a `source` column.

---

## Related

- Braindump: `braindump-waitlist-module.md`
- Principles: `specs/principles.md`
- Bubls CLAUDE.md: `/projects/bubls/CLAUDE.md`
