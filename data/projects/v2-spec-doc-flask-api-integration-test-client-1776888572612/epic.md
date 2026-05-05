# Epic: V2 Spec Doc — Flask API Integration Test Client

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The migration from Express (3100) to Flask (3101) has no automated verification layer. Without one, every route implemented in Tasks 2 and 3 requires a developer to manually load the Angular UI, exercise each endpoint, and eyeball the response — a process that is slow, incomplete, and non-repeatable. The integration client converts that manual ritual into a machine-verifiable gate: run `ng test`, get a pass/fail with named fields and both values on any mismatch.

The client also protects the migration timeline. Tasks 2 and 3 can be developed with confidence that their completion has a clear, objective definition: ContractCompareSpec passes. Without this gate, "done" is ambiguous and regressions are caught late.

This is an internal developer tool with no user-facing surface. Its value is entirely in migration velocity and migration correctness — the precondition for replacing Express in production.

**Value Proposition**: Replace manual UI eyeballing with a typed, automated diff of every Flask and Express endpoint so Tasks 2 and 3 have a machine-verifiable pass/fail gate.

---

## Scope

### What This Epic Covers

- **FlaskProjectsService** — typed Angular service calling `localhost:3101/api/projects` for all five CRUD operations, mirroring the existing `ProjectsService`
- **FlaskContextService** — typed Angular service covering `/api/builder`, `/api/principles`, `/api/codebase`, `/api/references` (read and write), mirroring existing context services
- **FlaskHealthService** — minimal typed service calling `localhost:3101/health`
- **ContractCompareSpec** — Karma/Jasmine spec that calls both backends for each endpoint and asserts response shapes match, with failure messages naming the endpoint, field, and both values

### What This Epic Does NOT Cover

- ❌ Replacing or modifying existing Express services — Express stays on 3100; Angular's production wiring is unchanged
- ❌ UI changes of any kind — no new tabs, routes, or panels
- ❌ Code generation from OpenAPI YAML — the contract is `flask/api-contract.md` (markdown); all three services are hand-written from it
- ❌ CI pipeline integration — the spec runs locally during migration only; re-scope when Flask fully replaces Express
- ❌ Persistent diff reports or log files — mismatches surface as Jasmine assertion failures in the terminal; no file I/O consumer exists yet

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Read api-contract.md and define Flask service interfaces** | None | — | 0.5 days | High |
| 2 | **Implement FlaskProjectsService and FlaskHealthService** | 1 | 3 | 1 day | High |
| 3 | **Implement FlaskContextService** | 1 | 2 | 1 day | High |
| 4 | **Write ContractCompareSpec** | 2, 3 | — | 1 day | High |

### Task 1: Read api-contract.md and define Flask service interfaces

Read `flask/api-contract.md` (produced in the Flask scaffold task) and extract typed TypeScript interfaces for every request and response shape used across all five service areas. These interfaces are the single source of truth that Tasks 2, 3, and 4 all import. This task produces no runtime code — only types in `src/app/services/flask/flask-api.types.ts`.

**Port budget**: ~50 lines of TypeScript interfaces in one file; no HTTP calls, no services, no error handling — just types derived directly from the contract document.

### Task 2: Implement FlaskProjectsService and FlaskHealthService

Write `FlaskProjectsService` covering the five CRUD operations against `localhost:3101/api/projects`, and `FlaskHealthService` covering `localhost:3101/health`. Both services mirror the method signatures of their Express counterparts so the compare spec can call them symmetrically. No retry logic, no error boundary, no shared base class.

**Port budget**: ~80 lines across two files; `localhost:3101` is hardcoded — no environment variable wiring, no interceptors, no abstractions shared with the Express services.

### Task 3: Implement FlaskContextService

Write `FlaskContextService` covering read and write operations for `/api/builder`, `/api/principles`, `/api/codebase`, and `/api/references` against `localhost:3101`. Method signatures mirror the existing Express context services. No shared base class with FlaskProjectsService — single consumer, no second use case yet.

**Port budget**: ~100 lines in one file covering four resource paths; no retry logic, no auth headers, no abstraction layer.

### Task 4: Write ContractCompareSpec

Write a Karma/Jasmine spec that imports all three Flask services and their Express counterparts, calls each endpoint through both clients with the same inputs, and asserts the response shapes match. Every failing assertion must name the endpoint, the field that differed, and both values (Express vs Flask). This spec is the only consumer of Tasks 2 and 3; it cannot produce meaningful results until Tasks 2 and 3 routes are implemented in Flask.

**Port budget**: ~120 lines in one spec file; Karma runner with both servers live, no file output, no custom reporter — standard Jasmine `expect` assertions only.

---

## Success Criteria

This epic is complete when:

- ✅ `FlaskProjectsService`, `FlaskContextService`, and `FlaskHealthService` compile with zero TypeScript errors
- ✅ `ContractCompareSpec` passes when Express (3100) and Flask (3101) are both running and Tasks 2 and 3 Flask routes are implemented
- ✅ Each failing assertion in `ContractCompareSpec` names the endpoint, the differing field, and both values (Express vs Flask) so mismatches require no further investigation to action
- ✅ No existing Express services, Angular routes, or UI components are modified

---

## Non-Goals

- ❌ Shared base class between Flask and Express services — one consumer exists; extract only when a second consumer appears
- ❌ Environment variable configuration for Flask base URL — no staging environment is in scope; re-evaluate if the harness needs to run outside localhost
- ❌ Persistent diff files or structured reports — no CI consumer; the terminal is the output medium during local migration
- ❌ Auth, retry logic, or error boundary UI — single-user local dev tool with no reliability requirement beyond the test run itself

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview