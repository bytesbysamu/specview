# 🏗️ Solution Architecture: V2 Spec Doc — OpenAPI Mock Server

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The central insight of this system is that `openapi.yaml` is not documentation — it is the build artifact. Everything else in this capability derives from it: DTOs are generated from it, `mock_server.py` implements it, and the Flask routes in Tasks 2 and 3 will be validated against it. The spec is written once and consumed in three directions. That asymmetry is why the spec must be authored before any other work begins.

The mock server exists to answer one question from one perspective: does the contract work from the Angular frontend's point of view? It is not a staging environment, not a test double, and not a prototype. It is a proof-of-contract. The Angular UI is the validator. If the sidebar renders pre-seeded projects, the editor opens a file, auto-save fires and the mutation is reflected on the next GET, and all four context panels read and write without error — the spec is correct. That proof is the only deliverable that matters here.

The DTO layer sits between the spec and its two consumers. `mock_server.py` uses the generated models for response serialization in Task 3. Flask route implementations in Tasks 2 and 3 will use the same models for input validation and serialization, ensuring the contract is enforced by the same types in both environments. This eliminates the class of integration failure where mock and production diverge silently because they were written from the spec by hand.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Contract before implementation | `openapi.yaml` is written and validated before `mock_server.py` is started. No route shape is invented during mock implementation — it is read from the spec. |
| One consumer, one concrete description | The mock has exactly one consumer: the Angular frontend during Task 4 validation. The architecture describes the concrete case; no abstraction layer is introduced. |
| Minimal surface for throwaway infrastructure | `mock_server.py` is explicitly temporary. It carries no persistence, no auth middleware, no request validation. Complexity added here has zero downstream payoff. |
| Shared types prevent silent drift | DTOs generated once from `openapi.yaml` are the serialization contract for both mock and Flask. Manual re-implementation of schemas in two places is the root cause of the integration failures this epic exists to prevent. |
| Env var swap, not code change | The Angular frontend must reach 3102 without a source code change. If a code change is required, the architecture has a gap — the env var boundary must be respected as a design constraint, not a nice-to-have. |

---

## System Boundaries

### What This System Includes

- `flask/openapi.yaml` — OpenAPI 3.0 contract for all Phase 1 routes: health, projects CRUD, and context read/write across four named keys
- `flask/dtos/` — Python models generated from `openapi.yaml` via datamodel-codegen; shared serialization contract between mock and Flask
- `flask/mock_server.py` — Flask app on port 3102; in-memory state for projects and context; pre-seeded with realistic data; full CRUD mutation for the session lifetime
- Angular base URL configuration — the env var (or `environment.ts` entry) that redirects the frontend at 3102; documented precisely enough that Tasks 2 and 3 can repeat the same swap against the real Flask backend

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| pytest suite for the mock | The Angular frontend working against 3102 is the test. A passing pytest suite without a working frontend proves nothing about the contract from the consumer's perspective. |
| Persistence in the mock | Resets on restart are a feature. The mock exists for a single validation session, not as a durable data store. |
| Request validation in the mock | Validating incoming payloads is Flask's responsibility in Tasks 2 and 3. Adding it to the mock introduces logic that must be maintained in two places for no benefit during this phase. |
| Swagger UI or openapi.yaml serving | There is no named consumer for a browsable API explorer at this stage. Adding the tooling surface incurs a runtime dependency with no identified user until developer onboarding becomes an explicit requirement. |
| Auth, streaming, AI endpoints | Phase 2 scope. Including them in the spec now would expand the contract surface before the frontend has validated even the Phase 1 shape. |
| DTO generation as a CI step | No pipeline consumer exists. The generation is a one-time manual invocation for this epic, re-scoped when Tasks 2 and 3 begin and require repeatable builds. |

---

## Component Design

### openapi.yaml

**Purpose**: Authoritative, machine-readable description of every Phase 1 route. The single artifact that makes all downstream work derivable rather than invented.

**Key Parts**:
- Health endpoint — `GET /health`; consumed by `mock_server.py` (Task 3) to confirm startup
- Projects CRUD — `GET /api/projects`, `GET /api/projects/{id}`, `POST /api/projects`, `PUT /api/projects/{id}/files/{filename}`, `DELETE /api/projects/{id}`; consumed by `mock_server.py` (Task 3) and by Angular during Task 4 validation
- Context endpoints — `GET` and `PUT` per key (`builder`, `principles`, `codebase`, `references`) at `/api/context/{key}`; consumed by `mock_server.py` (Task 3) and the four context panels in the Angular frontend (Task 4)
- Schema objects — request and response shapes for Project, File, and ContextEntry; consumed by datamodel-codegen (Task 2) to produce `flask/dtos/`

**Patterns**: Schema-first — routes reference schema objects by `$ref`; schemas are defined once in `components/schemas` and shared across request and response bodies. This is what makes datamodel-codegen output unambiguous.

### flask/dtos/

**Purpose**: Eliminate the risk of mock and Flask routes serializing responses with different field names or types. Both consumers derive from the same generated file; neither writes schema definitions by hand.

**Key Parts**:
- Generated models — one file output by datamodel-codegen covering every schema object in `openapi.yaml`; consumed by `mock_server.py` (Task 3) for response serialization and by Flask route implementations in Tasks 2 and 3 for validation

**Patterns**: Code generation from spec — models are not authored, they are derived. The workflow is: update `openapi.yaml`, re-run datamodel-codegen, commit the output. Manual edits to the generated file are a red flag that the spec is incomplete.

### mock_server.py

**Purpose**: Implement every Phase 1 route against in-memory state so the Angular frontend can exercise the full contract before a single production Flask route is written.

**Key Parts**:
- Projects store — an in-memory dict seeded at startup with 2–3 realistic projects; consumed by the Angular sidebar (Task 4) to confirm list and detail rendering without a create step
- Context store — a separate in-memory dict keyed by context key name (`builder`, `principles`, `codebase`, `references`); consumed by the four Angular context panels (Task 4) to confirm read and write
- Route handlers — one handler per route in `openapi.yaml`; each handler returns a response serialized using the `flask/dtos/` models; consumed by Angular during Task 4 validation

**Patterns**: Thin handler over in-memory dict — no service layer, no repository pattern, no persistence abstraction. The mock has one consumer and one purpose; indirection adds maintenance cost for zero benefit. The explicit anti-pattern here is building a proper Flask application architecture for infrastructure that is intended to be replaced.

### Angular Base URL Configuration

**Purpose**: Ensure the Angular frontend reaches 3102 through a single env var swap with no source code changes required, and that the swap procedure is documented precisely enough to repeat for Tasks 2 and 3.

**Key Parts**:
- Env var or `environment.ts` entry — the single point of control for the backend base URL; consumed by `projects.service.ts` and `ai.service.ts` (existing Angular services) when constructing HTTP requests
- Documented swap procedure — one paragraph describing the exact variable name and value, so Tasks 2 and 3 can repeat the pattern when pointing back at the real Flask backend on 3100

**Patterns**: Environment-driven base URL — the Angular frontend has no hardcoded port references; the base URL is externalized. If a code change is required to reach 3102, that is a gap to close in this task, not a scope issue to defer.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Contract format | OpenAPI 3.0 YAML | Supported by datamodel-codegen for DTO generation and openapi-spec-validator for contract validation; YAML is more readable than JSON for a ~150–200 line spec authored by hand |
| Contract validation | openapi-spec-validator | Zero-configuration CLI; a zero-exit run is the gating success criterion for Task 1 before any downstream work begins |
| DTO generation | datamodel-codegen | Generates Pydantic models from OpenAPI schemas; the same models work for serialization in the mock and for input validation in Flask; no manual schema transcription |
| Mock server | Flask (port 3102) | Same runtime as the production Flask backend; no new dependency for the project; a single file is sufficient for in-memory CRUD with no framework overhead |
| Frontend | Angular 19 (existing, no changes) | The validation instrument; no new code, no new dependencies; the env var swap is the only configuration change |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Single file for mock_server.py | The mock is throwaway infrastructure. A modular layout (blueprints, services, repositories) adds maintenance cost to code that exists only to prove a contract and will be replaced by Tasks 2 and 3. | A single file becomes unwieldy if scope expands beyond Phase 1 routes; that is the trigger to re-scope, not to add structure preemptively. |
| Port 3102, not 3100 | Keeps mock and production backend ports distinct. A developer can run both simultaneously without a port conflict, which is useful when validating that the env var swap works correctly. | Adds one more port to the mental model of the local dev environment. |
| No request validation in the mock | The mock's job is to return the correct response shape, not to police inputs. Adding validation to the mock would require maintaining it in sync with the Flask validation logic in Tasks 2 and 3, creating two sources of truth for the same rules. | Malformed requests from Angular will succeed silently against the mock but fail against Flask; this is acceptable because the validation gap surfaces in the same Task 4 session. |
| DTOs generated, not authored | Manual transcription of spec schemas into Python models is the root cause of silent mock-vs-production drift. Generated code is the spec, not an interpretation of it. | datamodel-codegen output must be committed and re-generated whenever the spec changes; the workflow is slightly more mechanical than editing a handwritten file. |
| Angular integration as the test, not pytest | A pytest suite that mocks HTTP responses proves the Python logic but cannot detect a contract mismatch between what Angular sends and what Flask expects. The only test that proves the contract from both sides simultaneously is the Angular frontend exercising 3102. | No automated regression coverage for the mock routes; acceptable because the mock is replaced by Flask in Tasks 2 and 3, at which point the same Angular validation pattern is repeated. |

---

## Patterns

### Contract-First Route Definition

**When to use**: Before implementing any route handler — in the mock, in Flask, or in any future service.

**How it works**: The route shape (path, method, request body schema, response schema) is defined in `openapi.yaml` first, validated with openapi-spec-validator, and only then implemented. The implementation reads from the spec; it does not define the spec by implication.

**Example**: The `PUT /api/projects/{id}/files/{filename}` route exists in `openapi.yaml` with its request body schema and 200 response schema before `mock_server.py` defines a handler for it. The handler returns a response that satisfies the schema; it does not invent the schema shape during implementation.

### Single-Source DTO Derivation

**When to use**: Any time the same data shape is serialized in more than one place.

**How it works**: Schema objects live in `openapi.yaml` under `components/schemas`. Every consumer — mock serialization, Flask validation, future clients — derives its type definitions from a single datamodel-codegen invocation. The spec is updated; the types follow.

**Example**: The `Project` schema in `openapi.yaml` produces a `Project` Pydantic model in `flask/dtos/`. `mock_server.py` uses that model to serialize list and detail responses. Flask route handlers in Tasks 2 and 3 use the same model for response construction and input validation. Neither consumer defines what a `Project` is independently.

### Env-Var-Controlled Base URL

**When to use**: Any time the same Angular frontend must point at different backend URLs across environments (local mock, local Flask, staging, production).

**How it works**: The HTTP base URL used by Angular services is read from an env var or `environment.ts` entry, never hardcoded. Switching environments is a single-value change with no source modification.

**Example**: Task 4 points Angular at 3102 by changing one value. When Tasks 2 and 3 are complete, the same swap reverses to 3100. The validation procedure is identical; only the port differs.

---

## Execution Flow

```
[Phase 1 — Contract]
  Task 1: openapi.yaml
       │
       ├──────────────────┐
       ▼                  ▼
[Phase 2 — Parallel]
  Task 2: DTOs     Task 3: mock_server.py
       │                  │
       └──────────┬───────┘
                  ▼
[Phase 3 — Validation]
  Task 4: Angular integration against 3102
```

Task 1 is a strict prerequisite for everything else. Tasks 2 and 3 are independent of each other and can proceed in parallel once the spec is validated. Task 4 requires both: the DTOs must be generated cleanly before `mock_server.py` can use them, and `mock_server.py` must be running before Angular can exercise it. The parallel window between Tasks 2 and 3 is the only scheduling opportunity in the whole epic; everything else is a chain.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview