# 🏗️ Solution Architecture: V2 Spec Doc — OpenAPI Contract + API Client + Mock

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The central problem is that tasks 2, 3, and 4 each need to assert that Flask routes return correct shapes — but spinning up a live Flask process to do this in every test run is slow, brittle, and creates a hard coupling between unrelated tasks. This architecture eliminates that coupling by introducing a typed contract layer: an OpenAPI YAML spec that serves as the single source of truth, and two implementations of the same abstract client — one that speaks HTTP, one that holds state in memory.

The mental model mirrors the chain module already in `flask/modules/chain/`: an abstract adapter defines the interface, a real provider implements it against the actual system, and a mock provider implements it in-memory for tests. Replacing "LLM call" with "HTTP call to Flask" is the only conceptual substitution. The adapter boundary is `ApiClient`; the real provider is `FlaskApiClient`; the mock provider is `MockApiClient`. Tests in tasks 2, 3, and 4 import `MockApiClient` and run instantly — no server dependency. End-to-end verification swaps in `FlaskApiClient` and runs the same assertions against a live process.

The architecture places all client code under `flask/client/` rather than in a standalone package. No second consumer exists yet — the only importers named in the epic are the task test suites within the same `flask/` tree. Promoting to a standalone package before a second importer is named would add packaging overhead with no payoff. The trigger to re-scope is a concrete second consumer, not speculative future reuse.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Contract before implementation | `openapi.yaml` is written first; both `ApiClient` dataclasses and the Flask routes are derived from it, not the other way around |
| Adapter pattern for swappable implementations | `ApiClient` defines the interface; `FlaskApiClient` and `MockApiClient` implement it; consumers are never aware of which they hold |
| One consumer drives the abstraction level | `flask/client/` is co-located with the Flask tree because the only importers are task test suites within that same tree — no premature packaging |
| No build step until route count justifies it | 13 hand-written routes cost less than the ongoing maintenance of a code-gen pipeline; re-evaluate at ~25 routes or deeply nested schemas |
| Determinism over realism in mocks | `MockApiClient` uses incrementing integer IDs and simple dicts; it only needs to return correct shapes, not simulate concurrency, persistence, or ID entropy |

---

## System Boundaries

### What This System Includes

- `openapi.yaml` — the canonical route contract covering all 13 Phase 1 routes: health check, projects CRUD (list, get, create, update, delete), context read/write
- `flask/client/client.py` — the `ApiClient` abstract base class with typed dataclasses for all response shapes; the shared interface both implementations conform to
- `flask/client/flask_client.py` — `FlaskApiClient`, the real HTTP implementation calling the Flask server at a configurable base URL; the integration test adapter
- `flask/client/mock_client.py` — `MockApiClient`, the in-memory implementation holding projects and context files in dicts; the unit test adapter for tasks 2, 3, and 4
- `flask/client/tests/test_mock_client.py` — the test suite that verifies `MockApiClient` is internally consistent; proves the mock is correct before it is used as the reference for real-client assertions

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| TypeScript / Angular client | Wrong layer — this is the Python test harness; Angular talks to Flask over HTTP and needs no generated client |
| Code-gen toolchain (datamodel-codegen, openapi-python-client) | 13 routes hand-written cost less than a build step with a fragile generated-code boundary; revisit at ~25 routes or deeply nested schemas |
| Standalone `spec_doc_client/` package | No second consumer exists; co-location under `flask/client/` is the correct scope until a named second importer appears |
| Shared parametrized pytest runner across mock and real clients | Assertion functions belong to tasks 2/3/4, not this epic; this epic only verifies the mock is internally correct |
| Auth, pagination, streaming endpoints | Phase 2 routes — excluded from `openapi.yaml` and all client methods |

---

## Component Design

### OpenAPI YAML Spec (`openapi.yaml`)

**Purpose**: Eliminates ambiguity about what shape Flask must return and what shape the client must expect. When both are derived from the same document, divergence becomes a validation error, not a runtime surprise.

**Key Parts**:
- Route definitions for all 13 Phase 1 routes — each with request body schema, response schema, and status codes
- Shared schema components for `Project`, `ContextFile`, and error response shapes — referenced by both request and response definitions so shape changes propagate automatically
- Written by hand before any implementation; no code-gen dependency on this artifact

**Patterns**: Contract-first design — the spec is the authoritative source, not a description of what already exists.

**Consumers**: Task 1 (the file itself is the deliverable); `ApiClient` dataclasses in Task 2 are derived from its schema components; Flask route implementation in Tasks 2 and 3 is validated against it.

---

### Abstract Client and Dataclasses (`flask/client/client.py`)

**Purpose**: Defines the shared interface that both `FlaskApiClient` and `MockApiClient` implement. Any test that types its client as `ApiClient` works identically against either implementation — the adapter boundary.

**Key Parts**:
- `ApiClient` — the abstract base class with one abstract method per route; typed return types use the dataclasses defined in the same file
- Response dataclasses (`ProjectRecord`, `ContextFileRecord`, `HealthStatus`, etc.) — match the schema components in `openapi.yaml` exactly; these are the shapes that tasks 2, 3, and 4 assert against

**Patterns**: Adapter pattern from `flask/modules/chain/adapter.py` — the abstract class is the boundary; implementations are interchangeable to callers.

**Consumers**: `FlaskApiClient` (Task 4) and `MockApiClient` (Task 3) both subclass `ApiClient`; task test suites type their client fixture as `ApiClient`.

---

### MockApiClient (`flask/client/mock_client.py`)

**Purpose**: Gives tasks 2, 3, and 4 a test fixture that returns correct response shapes without a live Flask process. This is the unblocking artifact — once it exists, all downstream test suites are independent of server availability.

**Key Parts**:
- `MockApiClient` — subclass of `ApiClient`; holds a `dict[str, ProjectRecord]` for projects and a `dict[str, dict[str, ContextFileRecord]]` for context files; all methods operate on these dicts and return the same dataclass shapes as `FlaskApiClient`
- ID generation — simple auto-incrementing integer counter; deterministic and easy to assert against in tests
- No I/O, no persistence, no network — the mock is a pure function of its initial state and the sequence of method calls made against it

**Patterns**: Mock provider from `flask/modules/chain/providers/` — same in-memory pattern, same role in the test hierarchy.

**Consumers**: `flask/client/tests/test_mock_client.py` (Task 3); task 2, 3, and 4 test suites import `MockApiClient` as their test fixture.

---

### FlaskApiClient (`flask/client/flask_client.py`)

**Purpose**: Provides a typed Python interface to the live Flask server so integration test suites can run the same method-level assertions as `MockApiClient` without managing raw HTTP calls in test code.

**Key Parts**:
- `FlaskApiClient` — subclass of `ApiClient`; each method sends the appropriate HTTP verb to `{base_url}/{route}` via `requests` and deserializes the JSON response into the shared dataclasses
- Configurable base URL — defaults to `http://localhost:3101` but accepts an override so CI environments can point at a different host
- Error handling — HTTP 4xx/5xx responses raise typed exceptions that callers can assert against; no retry logic in this integration harness

**Patterns**: Real provider from `flask/modules/chain/providers/` — concrete HTTP implementation behind the adapter boundary.

**Consumers**: Integration test suites for tasks 2, 3, and 4 when running against a live Flask process; acts as the end-to-end correctness proof.

---

### Mock Test Suite (`flask/client/tests/test_mock_client.py`)

**Purpose**: Verifies the mock is internally consistent before downstream task test suites rely on it as their reference. If the mock is wrong, every test that imports it is wrong — catching this in a dedicated suite avoids that cascading failure.

**Key Parts**:
- Method-level assertions covering all `ApiClient` methods — create/read/update/delete for projects, read/write for context files, health check
- Same assertion logic that tasks 2/3/4 will later run against `FlaskApiClient` — proving the mock and the real client are behaviorally equivalent

**Consumers**: Task 3 deliverable; indirectly validates that tasks 2/3/4 test suites are asserting against a correct reference.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Contract format | OpenAPI 3.0 YAML | Industry standard; validates with `openapi-spec-validator`; tooling ecosystem if code-gen becomes worth it later |
| Client interface | Python ABC + dataclasses | No dependencies; dataclasses provide typed shapes without the overhead of Pydantic at this scale |
| Real client HTTP | `requests` | Already in the Flask dev dependency tree; no new dependency introduced |
| Mock client | Pure Python dicts | Zero dependencies, deterministic, fast; matches the chain mock provider pattern already in the repo |
| Test runner | pytest | Already used across `flask/modules/`; no new tooling |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Hand-write `client.py` rather than code-generate from `openapi.yaml` | 13 routes is below the threshold where code-gen saves time; hand-written avoids a build step and a generated-code boundary that obscures the interface | If route count grows past ~25 or schemas become deeply nested, generated types would be more correct-by-construction than maintained-by-hand |
| Co-locate under `flask/client/` rather than a standalone package | The only named consumers are task test suites within the `flask/` tree; packaging adds overhead with no second importer to justify it | A standalone package becomes the right call the moment a second consumer outside `flask/` is named — Angular tooling, a CLI, or a second Flask service |
| Write `openapi.yaml` before either implementation (Task 1 before Task 2) | Forces the contract to be derived from intent, not from whatever Flask happened to return; divergence between Flask and the spec becomes a detectable error rather than silent drift | Requires discipline not to let the Flask implementation drift from the spec as routes evolve; the spec must be updated in lockstep |
| `MockApiClient` mirrors `FlaskApiClient` behavior, not Flask internals | The mock is an implementation of the `ApiClient` interface, not a simulation of Flask routing — this keeps it decoupled from Flask's implementation details | If a Flask route has side effects (file I/O, DB writes) that the mock omits, the mock tests pass while the real tests could still fail; the integration test suite catches this |
| No shared parametrized runner across mock and real clients in this epic | The assertion functions are owned by the task test suites, not this epic; this epic's test only proves the mock is internally correct | Tasks 2/3/4 must duplicate assertion logic across their mock and real client test suites — acceptable because each task's assertions are narrow and the duplication is at the task level, not cross-cutting |

---

## Patterns

### Adapter Pattern

**When to use**: When the same interface must be implemented by two or more concrete implementations that differ in their mechanism but must return identical shapes.

**How it works**: An abstract base class defines the interface. Each concrete implementation subclasses it and provides the mechanism — HTTP for the real provider, dicts for the mock. Callers type their dependency as the abstract class and never know which implementation they hold.

**Example in this system**: `ApiClient` is the abstract boundary. `FlaskApiClient` implements it over HTTP. `MockApiClient` implements it over in-memory dicts. Task test suites declare a fixture typed as `ApiClient` — the same test function runs against both without modification. This mirrors the `Adapter` / `ClaudeProvider` / `MockProvider` structure in `flask/modules/chain/`.

---

### Contract-First Design

**When to use**: When two implementations (Flask routes and the Python client) must agree on request/response shapes without one being derived from the other — i.e., when you cannot trust "just match what Flask returns" because Flask itself may be wrong.

**How it works**: The spec is written before either implementation exists. Both Flask and the client treat the spec as the authority. Drift between either implementation and the spec is detectable via spec validation rather than discovered at runtime through a failing assertion.

**Example in this system**: `openapi.yaml` is Task 1 — it exists before `client.py` (Task 2) and before the Flask routes (Tasks 2 and 3). The dataclasses in `client.py` are derived from the spec's schema components, not from Flask's actual response payloads. When `FlaskApiClient` passes the same assertions as `MockApiClient`, the contract is proven correct in both directions.

---

## Execution Flow

```
Task 1: openapi.yaml
         │
         ▼
Task 2: ApiClient + dataclasses (client.py)
         │
         ├──────────────────────────┐
         ▼                          ▼
Task 3: MockApiClient + tests    Task 4: FlaskApiClient
        (no server needed)       (requires Flask routes
                                  from Tasks 2+3)
```

Task 1 is the only hard prerequisite — neither client can be written without the response shapes the spec defines. Task 2 follows immediately: the abstract base and dataclasses are derived directly from the spec's schema components. Tasks 3 and 4 can proceed in parallel once Task 2 is complete, but Task 4 has an additional dependency on the Flask routes from the project and context tasks. In practice, Task 3 unblocks downstream test writing first; Task 4 arrives last as the integration verification step.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview