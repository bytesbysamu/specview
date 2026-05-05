# V2 Spec Doc — OpenAPI Contract + API Client + Mock — Analysis

## The Problem

Flask routes are verified manually via curl; there is no shared assertion layer for tasks 2, 3, and 4. Without a formal contract, Flask implementations can silently diverge from documentation, and each task must spin up a live server to test anything. A typed client bound to a single OpenAPI spec closes both gaps.

## Hard Constraints

- Must follow the Bubls adapter pattern exactly: abstract base → real provider → mock provider
- Flask runs on port 3101; that port is the integration target
- Phase 1 routes only: health, projects CRUD, context read/write — scope is fixed by api-contract.md (Task 1)
- Python only — no TypeScript client at this layer

## Open Questions

- **Hand-write vs code-gen:** 13 routes makes hand-writing faster and removes a build step, but code-gen is correct-by-construction. Which matters more — delivery speed or schema drift prevention?
- **Package location:** `flask/client/` (co-located, simpler imports) vs `spec_doc_client/` (standalone, importable by future tooling). No second consumer exists yet — which is the working assumption?
- **Shared test parameterization:** Tasks 2/3/4 need to run the same assertions against both mock and real client. Is the mechanism a pytest fixture that swaps implementations, or separate test files that import the same assertion functions? This must be decided before mock_client.py is written.

## Dependencies & Sequencing

- openapi.yaml must be finalized before client.py — abstract types must match the spec, not the other way around
- client.py (abstract base + dataclasses) must exist before flask_client.py and mock_client.py can be written
- mock_client.py must be complete before tasks 2/3/4 can import it — it is a blocker for those tasks
- flask_client.py integration tests cannot run until Tasks 2 and 3 Flask routes exist — these run last
- test_mock_client.py can be written in parallel with mock_client.py

## Explicitly Out of Scope

- `spec_doc_client/` as a standalone installable package — no second consumer exists; re-scope when a second importer (CLI tool, Angular test bridge) is named
- Code-gen toolchain (datamodel-codegen, openapi-python-client) — speculative build infrastructure for 13 routes; re-scope if route count exceeds ~25 or response schemas become deeply nested
- Shared parametrized test runner across mock and real clients — useful, but the assertion functions belong in tasks 2/3/4, not here; this task only proves the mock is internally consistent