# 🎯 Epic: V2 Spec Doc Backend — Foundation + Project Management

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

`server.js` at 1,651 lines is a growth ceiling. Every new capability — AI operations, context panels, project management improvements — lands in the same file with no isolation. The Bubls backend proved that a modular Flask pattern (7 modules, 164 tests) absorbs new features without regression. Porting spec-doc's backend to the same pattern means Phase 2 AI operations land on infrastructure that's already tested, and bug fixes in shared modules propagate to both products.

Phase 1 delivers the non-AI surface first because it has zero AI dependency and validates the foundation cleanly. Project files load, context panels save, and the Angular frontend notices nothing changed. If CRUD works, the plumbing is solid. Phase 2 (AI operations) inherits that confidence instead of building on untested ground.

The user sees no change. Same sidebar, same editor, same auto-save behavior. The business case is entirely internal: replace a monolith that blocks growth with a modular backend that enables it.

**Value Proposition**: Replace the Express monolith with a tested, modular Flask backend that serves the same frontend without modification, so Phase 2 AI features ship on verified infrastructure.

---

## Scope

### What This Epic Covers

- **Flask app factory + module registry** — Bubls pattern adapted for spec-doc's port and origins; the scaffold everything else registers into
- **Project CRUD module** — create, list, get, update file, delete; byte-identical API contract to Express
- **Context file module** — read/write for builder profile, principles, codebase context, and reference files
- **Chain module port** — adapter, three providers (Claude SDK, CLI subprocess, mock), file marker parser, context block loader; internal only, no endpoints exposed

### What This Epic Does NOT Cover

- ❌ AI text endpoints (rewrite, generate, iterate) — no Phase 1 consumer; these are Phase 2's first task
- ❌ Walker (filesystem scanner) — no Phase 1 endpoint calls it; ships with the scan endpoint in Phase 2
- ❌ Quality pipeline (review, lint-braindump, scan) — Phase 2
- ❌ Streaming (SSE) — deferred until AI endpoints are defined
- ❌ Frontend changes — zero Angular modifications; API contract is locked before Flask is built

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **API Contract + Flask Scaffold** | None | — | 1 day | High |
| 2 | **Project CRUD Module** | 1 | 3 | 1 day | High |
| 3 | **Context File Module** | 1 | 2 | 1 day | High |
| 4 | **Chain Module Port** | 1 | — | 1 day | Low |

### Task 1: API Contract + Flask Scaffold

Lock the full API contract (routes, payloads, response shapes) against the live Express server before writing Flask. Stand up the app factory with Blueprint registration, CORS for `localhost:4201`, and a `GET /health` endpoint. This task resolves the port strategy question — Flask runs on 3101 during migration so both backends run simultaneously; the frontend ENV swap is a one-line change at cutover, not a code change.

**Port budget**: ~80 lines — app factory, module registry, CORS config, health route; no business logic, no database drivers, no authentication middleware.

### Task 2: Project CRUD Module

Implement create, list, get, update-file, and delete against the `projects/` filesystem layout. Verify that all 64 existing project directories load correctly before the first line of Flask is written, confirming no migration is needed. The module is complete when the Angular sidebar and editor behave identically against Flask as against Express.

**Port budget**: ~150 lines — five route handlers plus filesystem helpers; no pagination, no search, no archive/restore, no schema validation beyond what Express currently enforces.

### Task 3: Context File Module

Implement read and write for the four context file types: builder profile, principles, codebase context, and reference files. Each maps to a fixed path; the module is a thin read/write layer with no transformation. Complete when the four context panels in the Angular frontend save and load correctly against Flask.

**Port budget**: ~80 lines — eight route handlers (read + write per type); no versioning, no diffing, no conflict resolution.

### Task 4: Chain Module Port

Copy the chain adapter, three providers (Claude SDK, CLI subprocess, mock), file marker parser, and context block loader from the Bubls backend. Strip Bubls-specific fixtures and types. Run the ported test suite with pytest. No endpoints are registered — this is internal infrastructure that Phase 2 wires up.

**Port budget**: ~300 lines copied, ~50 lines modified (strip Bubls types, adapt imports); no new providers, no retry/backoff logic, no circuit-breaker patterns — those ship when Phase 2 defines failure modes for real AI calls.

---

## Success Criteria

This epic is complete when:

- ✅ Angular frontend operates against the Flask backend with zero frontend code changes
- ✅ All project CRUD operations pass: create, list, get, update file, delete
- ✅ All four context file operations pass: read and write for builder, principles, codebase, references
- ✅ All 64 existing `projects/` directories load correctly without migration
- ✅ Chain module pytest suite passes (ported from Bubls, Bubls-specific fixtures stripped)
- ✅ Flask (3101) and Express (3100) run simultaneously; frontend cutover is a one-line ENV change

---

## Non-Goals

- ❌ AI text endpoints — no Phase 1 consumer exists; adding them now violates the "ship the car, not the engine" principle
- ❌ Walker — named in the brain dump as out of scope for Phase 1; no endpoint calls it until the scan endpoint is defined in Phase 2
- ❌ Database, auth, user management — spec-doc is a single-user filesystem tool; adding persistence layers solves a problem that doesn't exist

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview