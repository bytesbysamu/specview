# Analysis: Integration Tests + OpenAPI — Flask/Express API Compatibility

## The Problem
Flask needs to be a drop-in replacement for Express (port 3100 → 3101), but no automated check exists to confirm response shape compatibility. api-contract.md defines the contract, but it's a document — not executable. This adds a machine-verifiable gate before Flask can replace Express in production.

## Hard Constraints
- Express on 3100, Flask on 3101 — ports are fixed, both run locally
- `datamodel-codegen` + Pydantic chosen for DTO generation — not negotiable (decision already made in conversation)
- No mocks — tests call a live Flask server; fixture capture calls a live Express server
- Fixtures are captured once and committed — not regenerated per test run

## Open Questions
- Are DTOs only for tests, or will Flask route handlers also use them for request/response validation? (Test-only vs. also enforced at runtime — changes dto.py placement and import surface)
- CRUD endpoints (create project, write doc) need a real project to exist — does the test fixture include a pre-seeded project ID, or does `test_contract.py` create and tear down its own data?
- When Express is eventually removed, what's the re-capture strategy if the contract changes? (Fixtures become stale with no live server — manual update vs. a re-capture step in CI)

## Dependencies & Sequencing
- `openapi.yaml` must be written before `dto.py` can be generated — blocks everything else
- `capture.py` must run against live Express before `test_contract.py` has fixture data
- `test_contract.py` requires both `dto.py` and `fixtures/` — can only run after both are complete
- Flask routes on 3101 must be running for `test_contract.py` to pass — tests don't validate Flask exists, they validate it behaves correctly

## Explicitly Out of Scope
- Flask route-level DTO validation (Pydantic in request handlers) — no named consumer in the brain dump; defer until Flask handles untrusted external input
- Auto-regenerating fixtures in CI — no trigger condition yet; re-scope when Express is decommissioned or contract changes
- Swagger UI / OpenAPI browser — `openapi.yaml` is a codegen input, not a docs portal; defer until external consumers exist
- Schema diffing between fixtures and current Express output — fixtures are write-once reference data, not a living diff tool