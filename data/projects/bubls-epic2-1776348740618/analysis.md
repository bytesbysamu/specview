---
sidebar_position: 1
---

# 🔍 Spec Route + Chain Primitive – Analysis

**Purpose**: Filter the brain dump against builder principles, surface unmade decisions, and kill scope before the epic inflates.

**Date**: 2026-04-16

---

## Problem

Epic 1 shipped photoshoot with chain orchestration hardcoded in `server/modules/photoshoot/service.py`. Adding a second AI feature — Spec Doc's generation pipeline — would duplicate the orchestration, the builder/principles injection, the streaming, and the signal capture. Porting Spec Doc without extracting the shared surface is a short-term win that guarantees a rewrite on feature three.

## Hard Constraints

- **Neon only for user data.** `builder` + `principles` JSONB on `superapp_users`. No Supabase. No third-party auth.
- **Always ORM.** Chain primitive and spec module use SQLAlchemy/SQLModel. No raw SQL anywhere.
- **OpenAPI-first.** `/spec` endpoints defined in YAML, DTOs generated both sides, drift check in CI.
- **Feature module shape.** `server/modules/spec/` mirrors `server/modules/photoshoot/`. Feature-registry entry, feature-gate middleware.
- **Routes never call Replicate/Claude directly.** All model calls go through the chain primitive.
- **≤200 lines per file, standalone components, OnPush, signals, `data-test` selectors.**

## Open Questions

1. **Where does the chain primitive live?** `server/agent_runtime/` signals future package extraction; `server/modules/chain/` matches existing structure. → Lean `server/agent_runtime/` because it is not a user-facing feature, has no route, and is genuinely cross-cutting. Extraction to a package happens when a second *product* needs it.
2. **Does photoshoot retrofit land in Epic 2 or Epic 3?** → In-epic. The primitive is unvalidated until it runs two chains. Deferring ships an abstraction of one.
3. **Streaming transport — SSE or WebSockets?** → SSE. One-way, stateless, matches Spec Doc today, nothing in Bubls needs bidirectional yet.
4. **Onboarding UX — modal, dedicated route, or inline?** → Dedicated `/onboarding` route with "skip for now" escape hatch. Routable, returnable from settings, not dismissable by accident.
5. **Principles storage shape.** → Namespaced JSONB (`{photoshoot: {...}, spec: {...}}`). Costs nothing now, prevents a migration later.

## Dependencies

- Task 1 (schema migration) blocks every other task — both the chain primitive and the feature modules read `builder`/`principles`.
- Task 2 (chain primitive) blocks Tasks 3, 4, 6.
- Tasks 3, 4, 5 can run in parallel after 2.
- Task 6 (photoshoot retrofit) runs last — it is the validation step that the primitive survives two chains.

## Explicitly Out of Scope

- Correction loop aggregation (signal endpoint is a stub that persists; Epic 3 consumes it).
- `/spec` UX polish — textarea + submit + stream view only, no editor, no file tree.
- Migrating existing Spec Doc projects into Bubls.
- Bringing the Plate editor or principles editor inside Bubls.
- Publishing the chain primitive as an external package.
- Any change to photoshoot's user-facing behaviour — retrofit is invisible.

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
