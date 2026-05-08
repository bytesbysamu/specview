# Spec-Doc API — Braindump

## What it is

A standalone Flask backend replacing the original monolithic `server.js` (1,651 lines, no module boundaries) that powered the Spec Doc tool. Lives at `~/Projects/2026/spec-doc-api/`, runs on port 3101. The Angular frontend at port 4201 talks to it without any code changes — the API contract is byte-identical to the Express backend it replaces.

## Problem it solves

The Express `server.js` was unmaintainable: no modules, no tests, no typed contract. Every new AI feature had to be bolted onto an untested monolith. The Flask port brings: modular blueprints, an OpenAPI-first contract (openapi.yaml → generated DTOs via datamodel-codegen), 192 pytest tests, and a clean foundation for Phase 2 AI endpoints. The Bubls Flask backend (7 modules, 164 tests) was the reference pattern.

## Current state

Phase 1 (Epic 1 + 2) is complete. 13 commits, 2,279 lines, 94+ tests passing. Two epics shipped:

- **Epic 1 — Foundation**: App factory (`create_app.py`), project CRUD module (list/get/create/update-file/delete), context file module (builder/principles/codebase/references read+write), chain module ported from Bubls.
- **Epic 2 — OpenAPI Mock**: `openapi.yaml` written and locked, DTOs generated from spec (`dtos/models.py`, never hand-edited), mock server on port 3102, Angular integration validated.

Key files: `openapi.yaml` (contract), `dtos/models.py` (generated), `modules/ai/routes.py`, `modules/chain/adapter.py` (sole AI import point), `modules/context/service.py`.

## Key decisions already made

- **Port to 3101, Express stays on 3100**: Both run simultaneously during migration — Angular flips port via env var at cutover. No frontend code changes ever.
- **OpenAPI-first**: `openapi.yaml` is the truth. Routes implement the spec; DTOs are generated. `make check-dtos` fails CI if out of sync.
- **Bubls chain module ported verbatim**: No re-architecture during port — it's dead code in Phase 1, used in Phase 2. "No infrastructure before first user" was flagged as tension but overridden by sequencing constraint.
- **Filesystem-only, no DB**: 64 existing `projects/` directories load without migration. Project IDs are directory names; `project.json` holds name + createdAt.
- **AI routes deferred to Phase 2**: Rewrite/generate/iterate/lint-braindump/scan/implement endpoints exist in Express; Flask exposes none of them in Phase 1.
- **Walker deferred**: Ambiguous ownership (JS vs Python, existing vs new) — explicitly out of scope until Phase 2 defines the scan endpoint.

## Open questions

- **Port cutover timing**: When does the Angular frontend flip from 3100 to 3101 in production? What's the rollback plan if Flask breaks something?
- **Phase 2 scope**: Which AI endpoints ship first — rewrite/generate (text ops) or implement (SSE streaming task runner)?
- **Container routes**: `/api/container/*` (Docker status, workspace preview) — Phase 2+ and undefined in Flask; these need a concrete spec before they can be designed.
- **Walker ownership**: Still unresolved. The `scan` endpoint needs Walker — is it a Python port of the JS version, or a new design?

## Next steps

- Define Phase 2 epic: first AI endpoint to port (likely `/api/ai/text/rewrite` — simplest, no SSE).
- Lock cutover date for Angular to target 3101 instead of 3100.
- Decommission `server.js` once cutover is verified stable.
- Add streaming support (SSE) to the Flask chain adapter for the `implement` endpoint.
