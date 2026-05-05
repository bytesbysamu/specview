# 🔍 V2 Spec Doc Backend — Foundation + Project Management — Analysis

## The Problem

`server.js` is 1,652 lines in a single file handling projects, context files, AI operations, mock providers, and container management. Adding features means growing one file. The Bubls backend proved a modular Flask pattern (7 modules, 164 tests) that could replace this, but the brain dump bundles two separate concerns into one phase: working CRUD endpoints *and* AI infrastructure with zero current consumers.

## Hard Constraints

- Angular frontend: zero code changes. Every route path and response shape in the Express API is a contract — `/api/projects`, `/api/builder`, etc.
- 60 existing projects in `projects/` must load correctly on the new backend
- Port 3100 — both backends need to coexist during migration, so one must move or a proxy must arbitrate
- Flask, not FastAPI or Django — matches Bubls and builder's primary stack
- No database — V1 is filesystem-only
- No auth — single-user spec editor
- Claude CLI must remain the default AI provider (not SDK) — spec-doc users don't necessarily have `ANTHROPIC_API_KEY`

## Open Questions

- **Chain module: port now or port when Phase 2 starts?** The brain dump explicitly includes it in Phase 1, but the builder's own "ship the car, not the engine" principle says no infrastructure before first consumer. The chain module has zero callers in Phase 1. Counter-argument: it's proven code (164 tests), copy-paste not invention, and pytest validates it immediately. Which principle wins?
- **Context file storage pattern: flat files or manifest loader?** Spec-doc reads `builder.md`, `principles.md` etc. as flat files from the project root. Bubls uses a `manifest.json` → `prompts/*.md` indirection layer. Phase 1 context files are user-edited profiles, not prompt templates — the manifest pattern adds complexity for no gain here. Are these actually two different things (user context files vs. prompt templates)?
- **Env var naming: `AI_PROVIDER` or `CHAIN_PROVIDER`?** Express uses `AI_PROVIDER`, Bubls uses `CHAIN_PROVIDER`. Pick one before two modules diverge.
- **Port conflict during migration?** Brain dump says "both backends can run simultaneously." Both default to 3100. Who moves?

## Dependencies & Sequencing

- **Project CRUD must ship before context files** — context files are just specialized project-root files; validating the file I/O layer on projects proves the foundation
- **Route contract documentation must be locked before any Flask code** — the endpoint table in `references.md` is the spec; any ambiguity blocks implementation
- **Chain module (if included) has zero dependency on CRUD** — can run in parallel as a pure library with only pytest validating it
- **Walker port (JS → Python `os.walk`) blocks project listing** — the Express `walkProject` util in `server/walker.js` builds the file tree; must be ported first

## Explicitly Out of Scope

- **Chain module + providers + file parser + context loader** — zero named consumers in Phase 1. The brain dump says "none of this is exposed via endpoints yet." Defer to Phase 2 start, when the first AI endpoint provides the calibration. Trigger: Phase 2 kickoff. *(If the builder overrides this, it's fine — the cost is a folder copy + pytest run, not invention.)*
- **`core/database.py` / SQLAlchemy** — no DB tables in V1. Defer until a feature needs persistence beyond the filesystem. Trigger: multi-user or usage tracking.
- **SSE streaming endpoint (`/api/ai/implement`)** — marked as "V1 DEFERRED" in the endpoint map
- **Container management (4 endpoints)** — marked as "V1 CUT" in the endpoint map
- **ReviewResult type / review scoring** — AI-only, no Phase 1 consumer
- **`regen-task.mjs` compatibility testing** — the 39K-line script calls AI endpoints not shipping in Phase 1; validate it in Phase 2

---

*See [Epic](./epic.md) for scope and tasks. See [Solution Architecture](./architecture.md) for Flask module design.*