# 🎯 Epic: V2 Spec Doc — OpenAPI Contract + API Client + Mock

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Flask routes today are verified manually via curl with no shared assertion layer across tasks 2, 3, and 4. Every implementation that touches those routes must spin up a live server to assert anything — a slow, brittle feedback loop that compounds as the route count grows. A formal OpenAPI contract paired with a mock client eliminates that dependency entirely: tests run instantly, shapes are guaranteed by the same spec Flask implements against, and divergence becomes detectable rather than silent.

The mock client is the forcing function. Once tasks 2 and 3 can import `MockApiClient` and run assertions without a live server, the test cycle drops from minutes to seconds and the three tasks become independently workable. The real client (`FlaskApiClient`) then acts as an integration harness: when it passes the same assertions against a live server, the contract is proven correct end-to-end.

This follows the Bubls adapter pattern already proven in the chain module. No new architecture is being introduced — the same abstract base / real provider / mock provider structure is applied to the HTTP layer.

**Value Proposition**: A typed contract and mock client give tasks 2, 3, and 4 a shared, server-free assertion layer so Flask routes can never silently diverge from their documented shapes.

---

## Scope

### What This Epic Covers

- **openapi.yaml** — hand-written OpenAPI 3.0 spec covering all Phase 1 routes (health, projects CRUD, context read/write); the single source of truth for both Flask implementation and client types
- **client.py** — abstract base class defining the API interface with typed dataclasses matching response shapes; no I/O, no HTTP
- **flask_client.py** — real implementation calling `localhost:3101`; the integration test adapter
- **mock_client.py** — in-memory implementation holding projects and context in dicts; deterministic, no I/O; the unit test adapter
- **tests/test_mock_client.py** — verifies the mock is internally consistent using the same assertions tasks 2/3/4 will run against the real client

### What This Epic Does NOT Cover

- ❌ TypeScript / Angular client — wrong layer; this is the Python test harness only
- ❌ Code-gen toolchain (datamodel-codegen, openapi-python-client) — adds a build step with no payoff at 13 routes; revisit if route count exceeds ~25 or schemas become deeply nested
- ❌ Standalone `spec_doc_client/` package — no second consumer exists; co-locate under `flask/client/` and re-scope when a second importer is named
- ❌ Shared parametrized test runner across mock and real clients — assertion functions belong in tasks 2/3/4; this epic only proves the mock is internally correct
- ❌ Auth, pagination, streaming — Phase 2 routes

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **OpenAPI YAML spec** | None | — | 0.5 days | High |
| 2 | **Abstract client + dataclasses** | 1 | — | 0.5 days | High |
| 3 | **MockApiClient + tests** | 2 | 4 | 1 day | High |
| 4 | **FlaskApiClient** | 2, Tasks 2+3 routes | 3 | 0.5 days | High |

### Task 1: OpenAPI YAML Spec

Hand-write `openapi.yaml` covering all 13 Phase 1 routes defined in `flask/api-contract.md`: health check, projects CRUD (list, get, create, update, delete), and context read/write. This file is the single artifact both Flask implementation and client types are derived from — it is correct before either the client or Flask routes are written.

**Port budget**: ~150–200 lines of YAML across 13 route definitions; does not include authentication schemes, pagination parameters, or streaming response types — all deferred to Phase 2.

### Task 2: Abstract Client and Dataclasses

Define the `ApiClient` abstract base class in `flask/client/client.py` with one method per route and typed dataclasses for all request/response shapes. This is the interface contract both `FlaskApiClient` and `MockApiClient` implement — written once, imported by both.

**Port budget**: ~80–100 lines; one dataclass per response shape, one abstract method per route; does not include retry logic, timeout configuration, or request middleware — those belong in the real client only.

### Task 3: MockApiClient and Unit Tests

Implement `MockApiClient` in `flask/client/mock_client.py` holding projects in a dict and context files in a dict; write `tests/test_mock_client.py` asserting correct behavior for all methods. The mock is the unblocking artifact for tasks 2, 3, and 4 — once it exists, those tasks can write and run assertions without a live server.

**Port budget**: ~120–150 lines for the mock, ~100 lines for tests; does not include persistence, concurrency handling, or ID generation beyond simple incrementing integers — the mock only needs to be deterministic, not realistic.

### Task 4: FlaskApiClient

Implement `FlaskApiClient` in `flask/client/flask_client.py` calling `localhost:3101` (configurable base URL) via `requests`. This runs last because it requires both the abstract client (Task 2) and the Flask routes from Tasks 2 and 3 to exist. Its test suite imports the same assertion functions as `test_mock_client.py`.

**Port budget**: ~80–100 lines; one method per route using `requests.get/post/put/delete`; does not include connection pooling, retry with backoff, or response caching — integration harness only.

---

## Success Criteria

This epic is complete when:

- ✅ `openapi.yaml` validates against the OpenAPI 3.0 schema with zero errors
- ✅ `MockApiClient` passes all method-level assertions in `test_mock_client.py` without a Flask process running
- ✅ Tasks 2 and 3 test suites import `MockApiClient` and execute without any live server dependency
- ✅ `FlaskApiClient` passes the same method-level assertions as `MockApiClient` when Flask is running on port 3101 with Tasks 2 and 3 routes implemented
- ✅ All 13 Phase 1 routes are covered by both the spec and the client interface

---

## Non-Goals

- ❌ Code generation from openapi.yaml — 13 hand-written routes is faster and removes a build step; re-evaluate at 25+ routes
- ❌ Standalone installable package — no second consumer yet; co-location under `flask/client/` is sufficient until a second importer exists
- ❌ Shared parametrized pytest runner — assertion functions are owned by tasks 2/3/4, not this epic

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview