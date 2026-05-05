# Solution Architecture: V2 Spec Doc — Flask API Integration Test Client

**Purpose**: Long-lived system design document.

**References**: Addresses issues in [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The integration test client is a parallel service layer that lives inside the Angular frontend without touching any production code path. It mirrors the structure of the existing Express-facing services (`ProjectsService`, `BuilderService`, etc.) but points every HTTP call at `localhost:3101` instead of `localhost:3100`. Because it mirrors those signatures exactly, a single compare spec can call Express and Flask symmetrically — same inputs, two clients, one assertion per field — without any conditional logic or dual-path wiring.

The key structural insight is that the compare spec is the only consumer of all three Flask services. Nothing else imports them. That constraint drives every design decision: no shared base class, no environment variable indirection, no error boundary UI, no custom reporter. Each of those additions would serve a second consumer that does not exist in this epic's scope. The architecture is designed to be replaced or extended when Flask fully replaces Express — not to anticipate that replacement prematurely.

The system resolves three open questions left in the epic input. The compare spec runs in Karma (not a Node script) because Angular's Karma runner is already configured and the Flask services depend on Angular's `HttpClient` and DI container — standing up a parallel Node HTTP client outside Angular DI costs more than it saves during a local migration. The Flask base URL is hardcoded to `localhost:3101` because no staging environment is in scope and `environment.ts` indirection adds configuration surface area for a temporary migration tool with one consumer. Mismatches surface as Jasmine assertion failures in the terminal, not as diff files, because no CI consumer reads those files and writing them would add a dependency with no reader.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| One consumer, no abstraction | Flask services have exactly one consumer (ContractCompareSpec). No shared base class, no injectable base URL, no interceptors. Extract abstractions only when a second consumer is named. |
| Mirror, don't invent | Flask service method signatures replicate those of their Express counterparts so the compare spec calls both backends symmetrically. Diverging from Express signatures would require conditional logic in the spec. |
| Types as single source of truth | All request/response shapes are defined once in `flask-api.types.ts` and imported by every service and the spec. Drift between services becomes a compile error, not a runtime mismatch. |
| Terminal as the output medium | Mismatch reporting uses standard Jasmine `expect` assertions. No file I/O, no custom reporter. The assertion message names the endpoint, field, and both values — enough to act on without additional tooling. |
| Hardcode what has no second value | `localhost:3101` is the only Flask base URL that exists or is planned. Environment variable indirection would be configuration complexity serving a deployment scenario that has not been scoped. |

---

## System Boundaries

### What This System Includes

- `flask-api.types.ts` — TypeScript interfaces for all request and response shapes across all five endpoint areas, derived directly from `flask/api-contract.md`
- `FlaskProjectsService` — Angular service calling `localhost:3101/api/projects` for the five CRUD operations, mirroring `ProjectsService`
- `FlaskHealthService` — Angular service calling `localhost:3101/health`, mirroring the Express health check
- `FlaskContextService` — Angular service calling `localhost:3101/api/builder`, `/api/principles`, `/api/codebase`, and `/api/references` (read and write), mirroring the existing context services
- `ContractCompareSpec` — Karma/Jasmine spec that imports all three Flask services and their Express counterparts, calls each endpoint through both clients with identical inputs, and asserts response shapes match with field-level failure messages

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Shared base class for Flask services | One consumer exists (ContractCompareSpec). A base class would add indirection for a single instantiation. Re-scope when a second consumer is named. |
| `environment.ts` configuration for Flask base URL | No staging or remote Flask environment is in scope. Re-scope when the harness needs to run outside localhost. |
| Node script runner for the compare spec | Flask services depend on Angular's `HttpClient` and DI container. A standalone Node script would require a parallel HTTP client with no shared infrastructure benefit during a local migration. |
| Diff report files | No CI consumer reads them. File I/O adds a write dependency with no reader during the migration window. Re-scope when CI integration is planned. |
| Auth headers, retry logic, error boundary UI | This is a single-user local dev tool. Reliability requirements end at "the test run completes." |
| Modification of existing Express services | Express stays on 3100. The Angular production wiring is unchanged. |

---

## Component Design

### Type Layer: `flask-api.types.ts`

**Purpose**: Provides a single compile-time source of truth for all request and response shapes used across the three Flask services and the compare spec. Eliminates shape drift between services by making inconsistency a TypeScript error rather than a runtime surprise.

**Key Parts**:
- Interfaces for project list, project detail, project create/update payloads, and project delete responses — derived from `flask/api-contract.md`, mirroring the shapes used in `projects.service.ts`
- Interfaces for builder, principles, codebase, and references read/write payloads — mirroring the shapes used in the existing context services
- Health response interface

**Consumers**: `FlaskProjectsService` (Task 2), `FlaskHealthService` (Task 2), `FlaskContextService` (Task 3), `ContractCompareSpec` (Task 4)

**Pattern**: Type-first derivation from `flask/api-contract.md`. The contract document is the authority; the TypeScript file is a translation. Any ambiguity in the contract is resolved here, once, rather than resolved differently in each service.

---

### Projects and Health Layer: `FlaskProjectsService`, `FlaskHealthService`

**Purpose**: Provides `ContractCompareSpec` with typed Angular HTTP clients for the project CRUD operations and the health endpoint, callable symmetrically alongside their Express counterparts.

**Key Parts**:
- `FlaskProjectsService` — five methods (list, get, create, update-file, delete) calling `localhost:3101/api/projects`, returning typed observables using interfaces from `flask-api.types.ts`. Method names and return types replicate `ProjectsService` so the compare spec can call both with identical call sites.
- `FlaskHealthService` — one method calling `localhost:3101/health`, returning a typed observable. Mirrors the Express health check method signature.

**Consumer**: `ContractCompareSpec` (Task 4)

**Pattern**: Symmetric mirror. The design constraint is that the compare spec must be able to call `expressProjectsService.list()` and `flaskProjectsService.list()` on the same line with no adapter logic between them. That symmetry is the only architectural requirement; everything else (error handling, retries, interceptors) is out of scope.

---

### Context Layer: `FlaskContextService`

**Purpose**: Provides `ContractCompareSpec` with typed HTTP access to the four context resource paths (`/api/builder`, `/api/principles`, `/api/codebase`, `/api/references`), mirroring the existing Express context services.

**Key Parts**:
- `FlaskContextService` — read and write methods for each of the four resource paths, returning typed observables using interfaces from `flask-api.types.ts`. Method signatures replicate those of `BuilderService`, `PrinciplesService`, `CodebaseService`, and `ReferencesService`.

**Consumer**: `ContractCompareSpec` (Task 4)

**Why one service, not four**: The existing Express side separates concerns across four service files because each is wired into different parts of the UI. `FlaskContextService` has exactly one consumer (the compare spec) and that consumer calls all four paths in the same test suite. Splitting into four files adds file overhead with no isolation benefit for a single-consumer, temporary harness.

---

### Verification Layer: `ContractCompareSpec`

**Purpose**: Provides a machine-verifiable pass/fail gate for Tasks 2 and 3 by calling every endpoint through both the Express and Flask clients with identical inputs and asserting that response shapes match at the field level.

**Key Parts**:
- One `describe` block per service area (projects, context resources, health), each containing one `it` per endpoint
- Symmetric call pattern: call Express client, call Flask client, compare response shapes field by field using Jasmine `expect`
- Assertion messages that name the endpoint, the differing field, and both the Express and Flask values — making each failure immediately actionable without additional investigation

**Consumer**: Developer running `ng test` during Tasks 2 and 3 implementation

**Pattern**: Symmetric assertion. The spec is not testing whether Flask is correct in isolation — it is testing whether Flask agrees with Express. The Express response is the reference; the Flask response is the candidate. A mismatch is a signal to the Task 2 or 3 implementer, not a test framework concern.

**Why Karma, not a Node script**: `FlaskProjectsService` and `FlaskContextService` are Angular services that depend on `HttpClient` and Angular's DI container. Running them in Karma reuses the existing Angular test configuration with no additional setup. A Node script would require standing up a separate HTTP client, losing the DI integration, and duplicating the service logic in a non-Angular execution context — more complexity for no migration benefit.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Test runner | Karma + Jasmine (existing Angular configuration) | Already configured in the project; Flask services require Angular DI; no new tooling dependency |
| HTTP client | Angular `HttpClient` (existing) | Flask services are Angular services; `HttpClient` integrates with the DI container and is already used by the Express services being mirrored |
| Type definitions | TypeScript interfaces derived from `flask/api-contract.md` | Markdown contract is the authoritative source; TypeScript enforces shape consistency at compile time |
| Flask target | `localhost:3101` hardcoded | No staging environment is in scope; environment variable indirection adds configuration surface for a single deployment scenario |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Karma over Node script | Flask services are Angular services with `HttpClient` DI dependencies; Karma is already configured; no new tooling | Browser-based runner requires both servers live and a browser process; cannot run headlessly without additional Karma configuration |
| Hardcode `localhost:3101` | No staging environment exists or is planned in this epic; `environment.ts` indirection adds config complexity for one deployment scenario | If Flask ever needs to run at a non-localhost address during migration, the base URL must be changed in source rather than configuration |
| Jasmine assertions over diff files | No CI consumer reads diff files; terminal output during local migration is sufficient; file I/O adds a write dependency with no reader | Mismatch history is not persisted across test runs; developers cannot diff two runs without re-running |
| One `FlaskContextService` covering four paths | Single consumer (ContractCompareSpec); splitting would add file overhead with no isolation benefit for a temporary harness | If a UI feature ever needs to call a subset of context endpoints through Flask, the service would need to be split or the UI would import a service designed for test purposes |
| No shared base class | One consumer exists; a base class would add indirection for a single concrete case with no second instantiation | If a second consumer appears (e.g., an A/B toggle during cutover), the lack of a base class means duplicating the base URL and HTTP setup |
| Mirror method signatures exactly | Enables symmetric calling in the compare spec; diverging signatures would require adapter logic in the spec, defeating the purpose of the mirror pattern | Flask services cannot deviate from Express method shapes even if the Flask API has a cleaner interface; any Flask-specific ergonomics must wait until Express is retired |

---

## Patterns

### Mirror Pattern

**When to use**: When a new service must be callable interchangeably with an existing service from a single call site, without conditional logic at the call site.

**How it works**: The new service's public interface — method names, parameter types, return types — is defined to match the existing service exactly. The call site (here, `ContractCompareSpec`) imports both, calls both with identical arguments, and compares the results without needing to know which client it is calling.

**Example**: `FlaskProjectsService.list()` has the same signature as `ProjectsService.list()`. The compare spec calls both on adjacent lines and diffs the responses. If the signatures diverged, the spec would need adapter logic — negating the value of the symmetry.

### Type-First Derivation

**When to use**: When multiple components must agree on the same data shapes and those shapes are defined in an external document rather than inferred from existing code.

**How it works**: The external document (`flask/api-contract.md`) is the authority. A single TypeScript file (`flask-api.types.ts`) translates that document into typed interfaces. Every component that touches those shapes imports from that file. Ambiguity in the contract is resolved once, at the type layer, and enforced by the compiler everywhere else.

**Example**: Both `FlaskProjectsService` and `ContractCompareSpec` import `ProjectListResponse` from `flask-api.types.ts`. If the Flask API contract changes, one file changes and the compiler identifies every affected call site.

---

## Execution Flow

```
[Phase 1 — Foundation]
  Task 1: Read api-contract.md, define flask-api.types.ts
               │
               ▼
[Phase 2 — Services, parallel]
  Task 2: FlaskProjectsService + FlaskHealthService
  Task 3: FlaskContextService
               │
               ▼
[Phase 3 — Verification]
  Task 4: ContractCompareSpec
```

Tasks 2 and 3 depend on Task 1 (they import from `flask-api.types.ts`) but are independent of each other and can be developed in parallel. Task 4 depends on Tasks 2 and 3 compiling correctly but can be written structurally before the Flask routes in Tasks 2 and 3 are implemented — it will fail assertions until those routes exist, which is the expected state during migration. The spec becomes green when Flask agrees with Express for every covered endpoint.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview