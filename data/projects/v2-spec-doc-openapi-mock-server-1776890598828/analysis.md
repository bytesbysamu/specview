# 🔍 V2 Spec Doc — OpenAPI Mock Server — Analysis

## The Problem
The Angular frontend and Flask backend share no formal contract today — routes exist in Express (port 3100) but nothing machine-readable enforces their shape. Tasks 2 and 3 can't safely build Flask routes without a spec to target. The mock is the contract's proof-of-life before Flask routes exist.

## Hard Constraints
- Flask only for the mock (port 3102, in-memory state, no persistence)
- Phase 1 routes only: health, projects CRUD (list/get/create/update-file/delete), context read/write (builder, principles, codebase, references)
- No pytest suite — frontend integration IS the test
- Angular must reach 3102 via config only — no Angular code changes beyond an env swap

## Open Questions
- **Context API shape**: Are the four context keys separate endpoints (`GET/PUT /api/context/builder`) or one endpoint with a key param? — Separate allows independent reads; a single endpoint simplifies the spec but couples updates.
- **`update-file` semantics**: Does this update a file's content within a project, update project metadata, or both? Affects the route signature and DTO shape before the spec can be written.
- **DTO placement**: If DTOs are shared between mock_server.py and Tasks 2+3 Flask routes, do they live in `flask/dtos/` as a shared module, or does each consumer own its own models? — Needs a decision before mock_server.py imports anything.
- **Angular base URL mechanism**: Does `projects.service.ts` already support a configurable base URL via environment.ts? Or does pointing at 3102 require a code change that's untracked here?

## Dependencies & Sequencing
- openapi.yaml must be finalized before mock_server.py is written or DTOs are generated
- DTO generation (datamodel-codegen) blocks mock_server.py if DTOs are used for serialization — this adds a tooling dependency that plain dicts would avoid
- Mock running on 3102 must precede Angular integration test
- Angular base URL path must be confirmed before the integration test is designed

## Explicitly Out of Scope
- **DTO generation as an automated build step** — no CI consumer exists yet; run manually for this task; re-scope when Tasks 2+3 route implementation begins
- **Request validation in the mock** — mock returns correct shapes; validating incoming payloads is Flask's job in Tasks 2+3
- **Swagger UI / openapi.yaml serving** — no named consumer; defer until developer onboarding need is explicit
- **Auth, streaming, AI endpoints** — Phase 2 (explicitly stated)