# Epic: Integration Tests + OpenAPI — Flask/Express API Compatibility

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Flask on port 3101 is the planned replacement for Express on 3100. Without an automated compatibility gate, that swap is a manual process — someone has to run every endpoint by hand, compare outputs, and sign off. That's a risky step that scales poorly as routes are added and is impossible to enforce in CI.

This capability turns the prose in `api-contract.md` into an executable test suite. When `test_contract.py` passes, Flask is provably API-compatible with Express. The gate exists; the swap becomes a config change, not a judgment call.

**Value Proposition**: Replace Express with Flask confidently — one green test run is the entire sign-off process.

---

## Scope

### What This Epic Covers

- `openapi.yaml` — machine-readable schema for all 13 routes, derived from `api-contract.md`
- `flask/dto.py` — Pydantic models generated from the OpenAPI spec; DTO deserialization is the primary assertion mechanism
- `flask/tests/capture.py` — one-time script that hits Express on 3100 and writes simplified JSON fixtures
- `flask/tests/test_contract.py` — pytest suite that calls Flask on 3101, deserializes responses into DTOs, and seeds CRUD tests from fixtures

### What This Epic Does NOT Cover

- ❌ Flask route-level DTO validation at runtime — no untrusted external traffic yet; deferred until Flask serves public consumers
- ❌ Fixture regeneration in CI — no trigger condition exists while Express is still primary; re-scope when Express is decommissioned
- ❌ OpenAPI browser / Swagger UI — `openapi.yaml` is a codegen input, not a documentation portal
- ❌ Schema diffing between fixture snapshots and live Express output — fixtures are write-once reference data, not a living diff tool

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Write `openapi.yaml`** | None | — | 0.5 days | High |
| 2 | **Generate `flask/dto.py`** | 1 | — | 0.5 days | High |
| 3 | **Write and run `capture.py`** | None | 1, 2 | 0.5 days | High |
| 4 | **Write `test_contract.py`** | 2, 3 | — | 1 day | High |

### Task 1: Write `openapi.yaml`

Translate every route in `api-contract.md` into an OpenAPI 3.1 schema — paths, methods, request bodies, response shapes, and required fields. This file is the single source of truth for all downstream generation; its accuracy determines whether the DTOs and tests reflect the actual contract. No routes beyond what `api-contract.md` defines are added here.

**Port budget**: ~200 lines covering 13 routes; no authentication schemes, no pagination extensions, no webhook definitions — those have no current consumer.

### Task 2: Generate `flask/dto.py`

Run `datamodel-codegen` against `openapi.yaml` to produce Pydantic v2 models for every response schema. The output is committed as a generated file — it is not hand-authored. These models are the validation layer used by `test_contract.py`; a response that fails DTO deserialization fails the test automatically.

**Port budget**: ~80–120 lines of generated Pydantic models; no custom validators, no serialization overrides — only what codegen produces from the spec.

### Task 3: Write and run `capture.py`

A standalone script that calls every Express endpoint on port 3100 and writes simplified JSON files to `flask/tests/fixtures/`. Fixtures are committed once and become the stable seed data for CRUD tests in `test_contract.py`. The script is not part of the test suite and is not run in CI — it runs once while Express is live.

**Port budget**: ~60 lines; one fixture file per logical resource (project, context, principles, references, codebase, health); no authentication flow capture, no error-response fixtures — happy-path shapes only.

### Task 4: Write `test_contract.py`

The permanent pytest suite. Each test calls Flask on 3101, parses the response into the relevant DTO from `dto.py`, and asserts meaningful field-level invariants. CRUD tests that require a real project use the committed fixture for the project ID rather than creating and tearing down their own data. A full passing run with Flask on 3101 is the compatibility certificate.

**Port budget**: ~120 lines; one test per endpoint (13 total) plus a `flask` fixture pointing at `localhost:3101`; no mock servers, no response diffing against fixtures, no parametrized edge-case coverage — baseline compatibility only.

---

## Success Criteria

This epic is complete when:

- ✅ `openapi.yaml` covers all 13 routes defined in `api-contract.md` with no hand-authored additions
- ✅ `flask/dto.py` is generated from `openapi.yaml` via `datamodel-codegen` and committed
- ✅ `flask/tests/fixtures/` contains committed JSON files for every route captured from Express 3100
- ✅ `pytest flask/tests/test_contract.py` passes with Flask running on 3101 and no Express required
- ✅ Every test uses DTO deserialization as its primary assertion — no raw dict key checks

---

## Non-Goals

- ❌ Pydantic validation inside Flask route handlers — no external traffic today; adds complexity before there is a reason
- ❌ CI fixture regeneration — Express decommission is the trigger; that event hasn't happened

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview