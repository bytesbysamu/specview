# 🔍 Playground & V2 Test Coverage — Analysis

## The Problem
257 tests exist but cover services/simple components only. Twelve files (including the 1,087-line `app-v2.component`) have zero tests. V3 will extract state into `AppStateService`—without pre-extraction tests, there's no regression net to prove the extraction didn't break behavior.

## Hard Constraints
- Must complete before any V3 extraction work begins
- Existing 257 tests must remain green throughout
- Angular test tooling only (`ng test`, Jasmine, TestBed)
- `app-v2` pre-V3 tests must be structured for trivial `component.x()` → `service.x()` migration

## Open Questions
- **app-v2 test count is contradictory**: playground section says ~15 tests, pre-V3 section says ~48. Are these additive (63 total) or does 48 replace 15? → Likely 48 is the real number and 15 was a draft estimate.
- **pg-components-app + pg-components-ui**: listed as MISSING/MEDIUM but have no test designs and unknown line counts. In scope or deferred? → Need line counts before committing.
- **Where does "shallow" stop?** live-playground uses `NO_ERRORS_SCHEMA`, but state-matrix renders sub-components in specific states. Are those integration tests or still shallow?
- **Total target**: 87 + 48 = 135, but 87 already includes 15 for app-v2. Actual net new = 87 − 15 + 48 = **120**? Clarify the math before the epic locks a number.

## Dependencies & Sequencing
- `css-read.util.spec` → unblocks `pg-tokens` (tokens call `getCssVar`)
- `pg-tokens`, `pg-animations`, `pg-state-matrix` → can parallelize, no interdependency
- `live-playground` shallow-renders children → write child specs first so failures are attributable
- `app-v2` pre-V3 tests (48) → must land on `main` before V3 branch forks

## Explicitly Out of Scope
- **landing-pitch.component** — pure presentational, 0 logic; re-scope if it gains interactivity
- **playground-demo-data tests** — data shape validated implicitly by state-matrix tests; no standalone spec
- **V3 extraction itself** — this epic is the safety net, not the surgery
- **pg-components-app / pg-components-ui** — unknown size, no test design provided; defer to a follow-up unless line audit shows logic worth covering