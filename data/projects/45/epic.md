# 🎯 Epic: Test Phase 3 — Unit & Component Tests

## Business Value

Every refactor and feature addition to the Angular frontend is a coin flip. The backend has meaningful test coverage; the frontend has four tests covering one component. When taxonomy classification changes or teaser generation breaks, there is no safety net — bugs reach the UI silently. For a solo developer shipping across multiple projects, silent regressions are the most expensive kind of defect: they compound while attention is elsewhere and surface as user-facing breakage days or weeks later.

This phase closes the frontend coverage gap by testing all pure logic — the functions and service methods that encode business rules around project lifecycle, content parsing, and state derivation. These tests run in milliseconds, require no DOM or server, and provide the foundation for every subsequent testing phase. Without them, integration tests have no stable base, E2E tests are premature, and the long-term goal of spec-driven development has no enforcement mechanism.

The CI gate is equally critical. Tests that don't block merges rot immediately. Wiring `ng test` into the PR pipeline converts this phase from a one-time effort into a durable quality floor that holds as the codebase evolves through Phases 4+.

## Scope

### What This Epic Covers

- **Coverage gap scan** — Run coverage tooling against existing tests to produce a concrete map of untested services, helpers, pipes, and signal derivations across the frontend. This scan determines the real scope of the phase and replaces the open-ended "scan all services" directive with a prioritized backlog.
- **Taxonomy and teaser unit tests** — Full branch coverage for `sectionFor`, `firstNonHeadingSentence`, `countTasks`, and `projectTeaser` — the pure logic that encodes project lifecycle classification and card display rules (~45 test cases).
- **Scan-surfaced logic tests** — Unit tests for testable pure logic discovered by the coverage scan (e.g., `AiService` response parsing, `AuthService` token/expiry checks, utility functions, computed signal derivations). Scope is capped by the scan results and prioritized by complexity and change frequency.
- **Mock infrastructure** — Extend the existing mock factory pattern (`createProjectsServiceMock`, `createAiServiceMock`) to cover newly tested services. Decide co-location vs. centralized `testing/` directory before the third mock is created.
- **CI enforcement** — Add `ng test` to the GitHub Actions pipeline so frontend tests run on every PR, with coverage artifacts uploaded and a coverage ratchet that fails PRs which drop below the established baseline.

### What This Epic Does NOT Cover

- ❌ **Template and component rendering tests** — UX is actively churning; DOM-coupled tests would be throwaway work at current churn rates
- ❌ **Project detail page tests** — Editor, text ops, diff view, and file sidebar are scoped to a separate phase
- ❌ **Integration tests** — Real HTTP calls to the Flask API come after unit coverage is solid
- ❌ **E2E and visual regression** — Playwright flows and screenshot comparison require stable UX and stable integration tests first
- ❌ **Feature documentation** — Full spec coverage of all features is a later phase
- ❌ **Refactoring under test** — Test current behavior first; refactoring `sectionFor`, `projectTeaser`, or any other function happens after coverage exists, not before
- ❌ **Property-based testing** — Libraries like `fast-check` are interesting for edge-case discovery but add a dependency; re-evaluate after the base suite exists

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Coverage gap scan** — Run `ng test --code-coverage` against existing 4 tests, analyze the Istanbul output to identify all untested services/helpers/pipes/signals, and produce a prioritized test backlog ranked by complexity and change frequency | None | — | 0.5 days | High |
| 2 | **Taxonomy + teaser test suites** — Write unit tests for `sectionFor`, `SECTION_ORDER`, `firstNonHeadingSentence`, `countTasks`, and `projectTeaser` covering all branches identified in the spec (~45 cases) | None | ∥ with T1 | 1.5 days | High |
| 3 | **Scan-surfaced logic tests** — Using the backlog from T1, write unit tests for the highest-priority untested pure logic (auth state, AI response parsing, signal derivations, utilities); extend mock factories as needed, establishing the co-location-vs-centralized convention before mock #3 | T1, T2 | — | 2 days | High |
| 4 | **CI pipeline gate** — Add the `ng test` job to GitHub Actions, configure `ChromeHeadless` in the runner, upload coverage HTML report as artifact for inspection. No hard coverage threshold — coverage is a CI artifact, not a build gate | T2, T3 | — | 0.5 days | High |

## Success Criteria

- ✅ Every public method in pure-logic services, helpers, and pipes has at least one unit test (no-untested-public-method rule as floor)
- ✅ Branch coverage for `sectionFor` and `projectTeaser` is 100% — these encode the project lifecycle state machine
- ✅ Full test suite runs in under 10 seconds on `ChromeHeadless` — anything slower gets abandoned by a solo dev
- ✅ `ng test --watch=false --browsers=ChromeHeadless` passes in CI on every PR to master
- ✅ Coverage HTML report uploaded as CI artifact on every PR for inspection
- ✅ Coverage gap scan produces a concrete artifact (prioritized backlog) before any scan-surfaced tests are written

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design and testing patterns
- [Timeline](./timeline.md) – Status tracking