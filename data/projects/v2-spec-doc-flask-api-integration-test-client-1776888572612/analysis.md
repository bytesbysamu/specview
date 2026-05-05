# V2 Spec Doc — Flask API Integration Test Client — Analysis

## The Problem
Express (3100) is the current backend; Flask (3101) is being built as a replacement. Tasks 2 and 3 implement Flask routes, but "works against Flask" currently means manual eyeballing of the Angular UI. The integration client creates a machine-verifiable gate: call the same endpoints on both backends and diff the responses.

## Hard Constraints
- Client is hand-written from api-contract.md (markdown) — no code generation tooling
- Flask runs on localhost:3101; Express stays on 3100 — both coexist during migration
- No UI changes, no new Angular routes, no user-facing surface
- ContractCompareSpec cannot pass until Tasks 2 and 3 are complete — this is a trailing artifact, not a leading one

## Open Questions
- **Runner environment**: Does ContractCompareSpec run in Karma (browser, requires both servers live during the run) or as a Node/ts-node script (no browser, runs independently)? Karma gives you Angular's HttpClient and TestBed wiring; Node needs a separate HTTP client and manual DI
- **Base URL**: Is localhost:3101 hardcoded or driven by `environment.ts`? Hardcoded is simpler for a local-only dev tool; env var is only needed if the harness ever runs against a non-localhost Flask instance (no stated intent)
- **Mismatch output**: Do failures surface as failing Jasmine assertions (test runner output only) or as a structured diff written to a file? A file survives runner exit and is easier to read for large payloads, but adds file I/O with no stated consumer beyond the developer's terminal

## Dependencies & Sequencing
- Task 1 must be complete first: flask/api-contract.md is the source of truth for all three Flask services
- FlaskProjectsService, FlaskContextService, and FlaskHealthService can be written from the contract now — they compile independently of Flask being fully implemented
- ContractCompareSpec cannot produce meaningful results until Tasks 2 and 3 are done; FlaskHealthService assertions are the only ones that can pass earlier

## Explicitly Out of Scope
- Shared base class or abstraction between Flask services and Express services — single consumer; extract only when a second consumer exists
- Persistent diff reports or log files — no current consumer beyond local debugging; re-scope when CI integration is added
- CI pipeline integration — explicitly deferred by the brain dump; trigger: when Flask fully replaces Express and Tasks 2+3 are merged to main
- Environment variable configuration for Flask base URL — no staging environment stated; trigger: if the harness needs to run outside localhost