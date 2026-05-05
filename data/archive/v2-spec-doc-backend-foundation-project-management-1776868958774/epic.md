Now I have the full picture. Let me generate the Epic.

# 🎯 Epic: V2 Spec Doc Backend — Foundation + Project Management

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Spec Doc's backend is a 1,652-line Express monolith in a single file. Every feature — project CRUD, context file I/O, AI operations, container management — lives in `server.js`. Adding capabilities means growing one file. The Bubls backend proved a modular Flask pattern (seven modules, 164 tests, three shipped epics with zero regressions) that directly replaces this. Porting spec-doc to the same pattern means two products share AI infrastructure, bug fixes propagate both ways, and new features are a folder with three files, not more lines appended to a monolith.

Phase 1 ships the non-AI surface first because project CRUD and context files have zero AI dependency. If 61 projects load and four context panels save correctly against Flask, the file I/O foundation is proven. Testing is instant — no Claude calls, no prompt mocking, no waiting. Phase 2 (AI operations) builds on verified infrastructure rather than untested plumbing.

The user sees nothing change. Same sidebar, same editor, same preview. The only difference is the backend process is Python instead of Node. This is the kind of migration that pays compound interest: every future feature ships faster because the codebase is modular and testable.

**Value Proposition**: Replace a brittle single-file monolith with a modular Flask backend that serves the same frontend, shares infrastructure with Bubls, and makes every future feature cheaper to build.

---

## Scope

### What This Epic Covers

- **Flask app scaffold** – App factory, module registry, config, health endpoint, and `walkProject` port from JS to Python `os.walk`
- **Project CRUD module** – 5 endpoints (`/api/projects` surface) with identical paths and response shapes to Express
- **Context files module** – 8 endpoints (builder, principles, codebase, references GET/PUT) with identical contract
- **Chain module port** – Copy `modules/chain/` from Bubls (adapter, 3 providers, file parser, types, errors, context injection) as an internal library; pytest validates the 164-test suite against the copy; no endpoints exposed

### What This Epic Does NOT Cover

- ❌ **AI text operation endpoints** (7 routes) — Phase 2; requires chain module wiring + prompt templates, which need the foundation this epic ships
- ❌ **SSE streaming endpoint** (`/api/ai/implement`) — Marked V1 DEFERRED in the endpoint map; ship when implementation execution has a consumer
- ❌ **Container management** (4 endpoints) — Marked V1 CUT; `regen-task.mjs` calls AI endpoints directly
- ❌ **Database / SQLAlchemy** — V1 is filesystem-only; defer until a feature needs persistence beyond flat files
- ❌ **Auth / multi-user** — Single-user spec editor; no sessions, no tokens
- ❌ **`regen-task.mjs` compatibility testing** — The 39K-line script calls AI endpoints not shipping in this phase

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Flask scaffold + core config + walker** | None | — | 0.5 days | High |
| 2 | **Project CRUD module** | 1 | 3 | 1.5 days | High |
| 3 | **Context files module** | 1 | 2 | 1 day | High |
| 4 | **Chain module port** | 1 | 2, 3 | 1 day | Low |

### Task 1: Flask Scaffold + Core Config + Walker

Stand up the Flask app factory with CORS, module registry (`ENABLED_MODULES` list), health endpoint, and `core/config.py` for env vars (`PORT`, `WEB_ORIGIN`, `AI_PROVIDER`). Port `server/walker.js` to Python `os.walk` — this utility builds the project file tree and blocks Task 2's project listing endpoint. Env var naming resolves the open question from [Analysis](./analysis.md): use `CHAIN_PROVIDER` internally (matches Bubls) but accept `AI_PROVIDER` as a fallback alias for backwards compatibility.

**Port budget**: ~140 lines across 4 files (app.py, config.py, walker.py, `__init__.py`). Does not include database.py (no DB in V1), auth middleware (single-user), or logging configuration (Flask defaults suffice until production deployment).

### Task 2: Project CRUD Module

Implement 5 endpoints that replicate the Express project surface: list all projects, get single project with file contents, create project, update file, delete project. The `projects/` directory is the store — each project is a timestamped folder of markdown files. Response shapes match the contract table in [references.md](../references.md) exactly: `{ id, name, createdAt, files }`. See [Solution Architecture](./architecture.md) for module structure (routes → service → dto).

**Port budget**: ~200 lines across 3 files (routes.py, service.py, dto.py) plus ~100 lines of tests. Does not include pagination (61 projects fit in one response), search/filter (no UI for it), or project metadata beyond what Express returns today.

### Task 3: Context Files Module

Implement 8 endpoints (GET/PUT for builder, principles, codebase, references) that read and write flat markdown files from the project root. These are user-edited profiles, not prompt templates — they use direct file I/O, not the manifest-based context loader from Bubls. Response shape is `{ content: string }` for GET and `{ success: true }` for PUT, matching Express exactly. See [Solution Architecture](./architecture.md) for file storage paths.

**Port budget**: ~150 lines across 3 files plus ~80 lines of tests. Does not include manifest.json indirection (user context files ≠ prompt templates — analysis identified these as separate concerns), file history/versioning, or validation beyond confirming the write succeeded.

### Task 4: Chain Module Port

Copy `modules/chain/` from Bubls into the V2 backend as an internal library. This includes the adapter, three providers (Claude SDK, CLI subprocess, mock), file marker parser, types, errors, and context injection — ~500 lines across 8 files plus the context block loader (~120 lines). Run the existing 164 pytest tests against the copy to validate the port. No endpoints are exposed; no routes import from chain. This is the foundation Phase 2 wires up. The analysis flagged this as deferrable since it has zero Phase 1 consumers — it's included because it's a copy-paste (not invention), it validates the pytest infrastructure on proven code before new code depends on it, and the builder explicitly scoped it in.

**Port budget**: ~620 lines copied verbatim plus test runner config. Does not include new providers (e.g. Groq, OpenAI), ReviewResult endpoint wiring (no consumer), or context block manifest for spec-doc prompts (Phase 2 creates these when the first AI endpoint needs them).

---

## Success Criteria

This epic is complete when:

- ✅ Angular frontend works against the Flask backend with zero frontend code changes — same sidebar, editor, and preview behavior
- ✅ All 5 project CRUD endpoints return identical response shapes to Express (verified by running the frontend against Flask)
- ✅ All 8 context file endpoints read/write correctly — builder, principles, codebase, references panels save and reload
- ✅ All 61 existing projects in `projects/` load correctly on the Flask backend
- ✅ Chain module's pytest suite passes (copied from Bubls, adapted import paths only)
- ✅ Both backends can run simultaneously during migration (Flask on a different port or behind a proxy — see [Solution Architecture](./architecture.md) for coexistence strategy)

---

## Non-Goals

- ❌ **Performance optimization** — 61 projects, single user, filesystem I/O; there is no performance problem to solve
- ❌ **API versioning** — one consumer (Angular frontend), one backend; versioning adds ceremony for zero benefit
- ❌ **Prompt template migration** — Express prompt strings move to `context/prompts/` in Phase 2, when the AI endpoints that use them ship
- ❌ **Test coverage targets** — validate the port works, don't chase a coverage number; the chain module's 164 tests are the coverage floor, new modules test the contract

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – Flask module design, coexistence strategy, walker port
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview