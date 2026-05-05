# Solution Architecture: Integration Tests + OpenAPI

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The compatibility gate between Express (3100) and Flask (3101) rests on a single insight: the contract is already written in `api-contract.md`. The architecture converts that prose contract into two executable artifacts — a Pydantic DTO layer generated from OpenAPI, and a pytest suite that uses those DTOs as the assertion mechanism. When Flask can deserialize its own responses into the DTOs, it is provably shape-compatible.

The system has three discrete phases that touch different files and run at different times. `openapi.yaml` and `flask/dto.py` are built once from the spec. `capture.py` runs once while Express is live and produces committed fixture files. `test_contract.py` is the permanent suite, running against Flask with no Express dependency — it uses the captured fixtures only for seeding CRUD operations, not for response comparison.

The key trade-off in this design is preferring DTO deserialization failure over explicit assertion failure. A misshapen Flask response raises a Pydantic `ValidationError` before any assertion runs. This means the test failure message names the missing field and its expected type, not just "assertion failed on key `x`". The DTOs do the heavy lifting; the assertions focus on meaningful invariants (non-empty lists, boolean states, string lengths), not exhaustive field enumeration.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| DTOs as validation, not documentation | `dto.py` is generated from `openapi.yaml` and used directly in `test_contract.py` — the same types serve both purposes; no hand-authored validator duplication |
| Fixtures as seed data, not comparison targets | Captured JSON fixtures give CRUD tests a stable project ID and known-good data to operate against; tests assert DTO shape, not byte-for-byte response equality |
| Capture once, test forever | `capture.py` is not a CI artifact; it runs while Express is live, writes committed files, and is never needed again — Express can be decommissioned without breaking the test suite |
| One file, one job | `capture.py` generates data; `dto.py` defines shapes; `test_contract.py` runs assertions — these responsibilities do not overlap |
| Simplest assertion that catches real breakage | Shape validation via DTO deserialization plus one or two invariant assertions per test; no brittle field enumeration, no snapshot diffing |

---

## System Boundaries

### What This System Includes

- `openapi.yaml` — machine-readable schema for all 13 routes, derived strictly from `api-contract.md`
- `flask/dto.py` — Pydantic v2 models generated from `openapi.yaml` via `datamodel-codegen`; consumed by `test_contract.py`
- `flask/tests/capture.py` — one-time script that calls Express on 3100 and writes simplified JSON to `flask/tests/fixtures/`
- `flask/tests/fixtures/` — committed JSON files providing stable seed data for CRUD-dependent tests
- `flask/tests/test_contract.py` — permanent pytest suite asserting Flask API compatibility via DTO deserialization

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Pydantic validation in Flask route handlers | No untrusted external traffic today; adding request validation before public consumers exist adds complexity with no observable benefit |
| CI fixture regeneration | `capture.py` has no trigger condition while Express is still primary; re-scope when Express decommission is scheduled |
| Swagger UI / OpenAPI browser | `openapi.yaml` is a codegen input; a documentation portal implies public API consumers, none of which exist yet |
| Response diffing against fixture snapshots | Fixtures establish stable seed data; diffing every response field would make tests brittle to any benign schema evolution |
| Parametrized edge-case coverage | Baseline compatibility is the goal; edge cases (malformed inputs, auth failures) belong in a dedicated error-contract suite scoped separately |

---

## Component Design

### OpenAPI Schema (`openapi.yaml`)

**Purpose**: Single source of truth for the API contract — consumed by `datamodel-codegen` to produce `dto.py`.

**Key Parts**:
- Path definitions for all 13 routes from `api-contract.md` — methods, request bodies, response shapes, required fields
- Schema components for shared object shapes (project, spec, context file, principles, codebase, references) referenced across multiple paths

**Patterns**: Schema-first design — the YAML is the authority; any drift between `openapi.yaml` and the actual Flask routes is a test failure waiting to happen, not a documentation gap.

The file is intentionally minimal: no authentication schemes, no pagination extensions, no webhook definitions. Those have no current consumer and would inflate the schema without improving the codegen output.

### DTO Layer (`flask/dto.py`)

**Purpose**: Gives `test_contract.py` typed response models that validate shape automatically upon deserialization.

**Key Parts**:
- Generated Pydantic v2 models for each response schema defined in `openapi.yaml` — `Project`, `ProjectSpec`, `ContextFile`, `Principles`, `Codebase`, `References`, `Health`
- No hand-authored validators or serialization overrides; the file is committed as a codegen artifact and regenerated only when `openapi.yaml` changes

**Patterns**: Generated code as a first-class artifact. `dto.py` is not scaffolding to be modified — it is the compiled form of `openapi.yaml`. Treating it as editable would cause it to drift from the spec, defeating its purpose as a contract enforcement layer.

`test_contract.py` is the sole consumer of `dto.py` in this capability.

### Capture Script (`flask/tests/capture.py`)

**Purpose**: Produces stable, committed fixture data from live Express responses without requiring Express to be available during test runs.

**Key Parts**:
- HTTP calls to Express on 3100, one per logical resource (project list, single project, context, principles, codebase, references, health)
- Simplification step before writing — strips volatile fields (timestamps, generated IDs beyond what's needed for CRUD seeding) so fixtures don't become stale after a single write

**Patterns**: Write-once data capture. The script is a one-time operation, not a CI step. Its output (`fixtures/*.json`) is committed to the repository and becomes the stable test substrate.

The simplification step is deliberate: fixture JSON that includes every field from an Express response would couple `test_contract.py` to Express's exact output, reintroducing the brittle diffing the design explicitly avoids.

### Integration Test Suite (`flask/tests/test_contract.py`)

**Purpose**: The executable compatibility certificate — 13 tests that collectively prove Flask is a drop-in replacement for Express on the shared API contract.

**Key Parts**:
- `flask` pytest fixture — a `requests.Session` pointed at `localhost:3101`; the only configuration required to run the suite
- One test per endpoint — calls Flask, deserializes the response into the appropriate DTO from `dto.py`, asserts one or two meaningful invariants
- CRUD tests for project operations — seed the project ID from `fixtures/project.json` rather than creating and tearing down their own data, avoiding test-order dependencies

**Patterns**: DTO deserialization as the primary assertion. Calling `Project(**response.json())` is both a shape check and a type check; it fails loudly with a field-level error message if Flask's response diverges from the spec. Explicit assertions on top of that check invariants (list non-empty, boolean truthy, string non-empty) without duplicating the field enumeration that Pydantic already handles.

CRUD seeding from committed fixtures keeps tests hermetic with respect to Express while keeping them stateful with respect to real Flask behavior — the suite exercises actual database reads and writes on 3101.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Schema | OpenAPI 3.1 YAML | Industry standard; `datamodel-codegen` has first-class support; human-readable enough to review against `api-contract.md` |
| DTO generation | `datamodel-codegen` (Pydantic v2 output) | Eliminates hand-authoring drift; Pydantic v2 provides fast validation and clear error messages on deserialization failure |
| Test runner | pytest | Already in the Flask test stack; fixtures, parametrize, and conftest patterns are well-understood |
| HTTP client in tests | `requests` | Simpler than `httpx` for synchronous calls against a local server; no async overhead needed |
| Fixture format | JSON | Directly consumed by `**` unpacking into Pydantic constructors; no deserialization step between fixture read and DTO instantiation |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| DTO deserialization as primary assertion | A `ValidationError` names the offending field and expected type — more actionable than `AssertionError: key missing`. It also means adding a required field to the OpenAPI spec automatically makes existing tests fail, enforcing spec discipline. | Tests are coupled to the DTO structure; if a field is marked optional in the spec but always present in practice, the test won't catch its absence |
| Fixtures as seed data, not comparison targets | Prevents tests from failing on benign changes (whitespace in content, reordering of list items, added optional fields). Flask can evolve without breaking the gate as long as shape is preserved. | A Flask response that drops a field the fixture contained will not be caught unless that field appears in the DTO as required |
| `capture.py` not in CI | Express is still the primary server; there is no trigger condition for regenerating fixtures automatically. Running it in CI would fail the moment Express is decommissioned. | Fixtures can drift from Express behavior over time if Express routes evolve — acceptable because the fixture's job is to seed CRUD tests, not mirror Express exactly |
| `openapi.yaml` covers exactly 13 routes | Spec is derived from `api-contract.md` with no additions. Any route added to Flask that isn't in the spec is untested by this suite, but the scope boundary is intentional — this suite validates compatibility, not completeness. | New Flask routes require an `openapi.yaml` update to get DTO coverage; they won't be automatically tested by this capability |
| No Pydantic validation in Flask route handlers | The only current consumers of the Flask API are the integration tests themselves and, shortly, Angular frontend traffic. Both are trusted. Adding request validation before untrusted external consumers exist adds complexity with no current payoff. | If a malformed internal request reaches Flask, it will fail without a clean error response — acceptable at this stage |

---

## Execution Flow

```
[Build Phase — one time]
  openapi.yaml ──→ datamodel-codegen ──→ flask/dto.py (committed)

[Capture Phase — one time, Express must be live]
  capture.py ──→ Express 3100 ──→ fixtures/*.json (committed)

[Test Phase — runs in CI, Flask must be live on 3101]
  test_contract.py ──→ Flask 3101 ──→ DTO deserialization ──→ assertions
                          ↑
              fixtures/*.json (seed data for CRUD tests)
```

Build and Capture phases run in parallel — `dto.py` and `fixtures/` have no dependency on each other. The Test phase depends on both being present. After the initial setup, only the Test phase runs; Build re-runs only when `openapi.yaml` changes, Capture never runs again until Express decommission is scoped.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview