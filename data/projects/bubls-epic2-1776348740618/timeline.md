---
sidebar_position: 4
---

# 📅 Spec Route + Chain Primitive – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | User model: builder + principles | backlog | Alembic migration + SQLModel update + OpenAPI regen |
| 2 | Chain primitive (`agent_runtime`) | backlog | `run_chain`, `capture_signal`, providers, logging, mock, tests |
| 3 | Spec module + chain definition | backlog | Port prompts, wire chain, Flask routes, OpenAPI YAML |
| 4 | Spec frontend route + SSE rendering | backlog | `/spec` standalone component, adapter, feature-registry entry |
| 5 | Onboarding route + builder form | backlog | `/onboarding` route, guard, `PUT /api/user/builder` |
| 6 | Photoshoot retrofit onto primitive | backlog | Zero user-facing change; existing e2e test must pass unchanged |

---

## Status Legend

- `backlog` — Not started
- `in_progress` — Currently working
- `done` — Completed
- `blocked` — Waiting on dependency

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-16 | — | Epic created | Brain dump captured; scope locked to 6 tasks; photoshoot retrofit scoped in-epic |
