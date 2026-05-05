# 🎯 Epic: V2 Spec Doc — OpenAPI Mock Server

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The Angular frontend and Flask backend currently share no machine-readable contract. This matters because Tasks 2 and 3 must implement Flask routes — and without a validated spec, each route is a guess at what the frontend actually needs. The mock server converts that guess into a proof: if the Angular UI works against 3102, the contract is correct before a single production route is written.

The compounding value is in sequencing. A validated openapi.yaml becomes the authoritative reference for all future Flask routes and the source of generated DTOs. Every hour spent on Tasks 2 and 3 is de-risked by this epic. Without it, integration failures surface late, after route logic has already been written against the wrong shape.

This is internal developer infrastructure with no direct user-facing feature. The value is entirely in what it unblocks: confident, contract-first Flask implementation in Tasks 2 and 3.

**Value Proposition**: Prove the API contract works from the frontend's perspective before writing a single production Flask route.

---

## Scope

### What This Epic Covers

- **openapi.yaml** — Machine-readable contract for all Phase 1 routes: health, projects CRUD, context read/write across four keys
- **mock_server.py** — Flask app on port 3102 with in-memory state, pre-seeded projects, and full CRUD mutation for the session lifetime
- **DTO generation** — Python models generated from openapi.yaml via datamodel-codegen, shared between mock and future Flask routes
- **Angular base URL configuration** — Confirm and document the env var swap that points the frontend at 3102 with no Angular code changes

### What This Epic Does NOT Cover

- ❌ pytest suite — frontend integration against 3102 is the validation
- ❌ Persistence — mock state resets on restart by design; this is not a bug
- ❌ Auth, streaming, AI endpoints — Phase 2 scope
- ❌ Swagger UI or openapi.yaml serving — no named consumer until developer onboarding is an explicit need
- ❌ Request validation in the mock — validating incoming payloads is Flask's job in Tasks 2 and 3

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Write openapi.yaml** | None | — | 1 day | High |
| 2 | **Generate DTOs from spec** | 1 | 3 | 0.5 days | High |
| 3 | **Build mock_server.py** | 1 | 2 | 1 day | High |
| 4 | **Validate Angular integration** | 2, 3 | — | 0.5 days | High |

### Task 1: Write openapi.yaml

Author an OpenAPI 3.0 YAML spec covering all Phase 1 routes: `GET /health`, projects CRUD (`GET /api/projects`, `GET /api/projects/{id}`, `POST /api/projects`, `PUT /api/projects/{id}/files/{filename}`, `DELETE /api/projects/{id}`), and context read/write as separate endpoints per key (`GET /PUT /api/context/{key}` where key is one of `builder`, `principles`, `codebase`, `references`). The spec must define request and response schemas precisely enough that datamodel-codegen can generate unambiguous Python models from it. Validate with openapi-spec-validator before proceeding.

**Port budget**: ~150–200 lines of YAML covering 10–12 endpoints and 4–6 schema objects; no auth schemes, no streaming endpoints, no Swagger UI serving — those belong to Phase 2 and add tooling surface with no current consumer.

### Task 2: Generate DTOs from openapi.yaml

Run datamodel-codegen against openapi.yaml and place the output in `flask/dtos/`. Verify the generated models cover every schema object in the spec with no missing fields or type errors. These models are the shared serialization contract between mock_server.py and the Flask route implementations in Tasks 2 and 3 — placing them in a dedicated module avoids duplication across consumers.

**Port budget**: One generated file in `flask/dtos/`, one datamodel-codegen invocation documented in the project README; no custom base classes, no validation decorators — mock_server.py uses the models for serialization only, not input validation.

### Task 3: Build mock_server.py

Implement a Flask app on port 3102 that serves all Phase 1 routes using in-memory dicts for state. Pre-seed the store with 2–3 realistic projects so the sidebar renders immediately without a create step. All CRUD operations must mutate in-memory state for the session: create adds to the dict, update-file replaces the file content, delete removes the entry. Context endpoints read and write against a separate in-memory store keyed by context key name.

**Port budget**: ~150–200 lines in a single file; no persistence layer, no authentication middleware, no request schema validation — each of those belongs to Tasks 2 and 3 where the real Flask routes live.

### Task 4: Validate Angular Integration

Confirm the env var (or environment.ts value) that controls the Angular base URL, point it at 3102, and manually exercise: sidebar loads the pre-seeded projects, a file opens in the editor, auto-save writes back successfully, and all four context panels (`builder`, `principles`, `codebase`, `references`) read their pre-seeded content and accept a write. Document the exact env var name and swap procedure so Tasks 2 and 3 can repeat the same validation pattern against the real Flask backend.

**Port budget**: No Angular code changes — if a code change is required, that is a scope issue to resolve before closing this task; document the env var swap in one paragraph, not a runbook.

---

## Success Criteria

This epic is complete when:

- ✅ `openapi-spec-validator flask/openapi.yaml` exits 0 with no errors
- ✅ `datamodel-codegen` generates Python models from openapi.yaml with no missing fields or type errors, output placed in `flask/dtos/`
- ✅ `mock_server.py` starts on port 3102 with no errors and pre-seeded data visible
- ✅ Angular frontend pointed at 3102 via env var only: sidebar renders pre-seeded projects, editor opens a file, auto-save fires and the mutation is reflected in a subsequent GET
- ✅ All four context panels (`builder`, `principles`, `codebase`, `references`) read pre-seeded content and accept a write that persists within the session

---

## Non-Goals

- ❌ pytest suite — the Angular integration working against 3102 is the test; a passing pytest suite without a working frontend proves nothing useful here
- ❌ DTO generation as a CI build step — no pipeline consumer exists yet; run manually for this task and re-scope when Tasks 2 and 3 begin
- ❌ Swagger UI — adds a runtime dependency and serving logic with no named user until developer onboarding becomes an explicit requirement

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview