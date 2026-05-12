# 🏗️ Solution Architecture: Test Phase 3 — Unit & Component Tests

## Architecture Overview

This phase establishes the frontend's first durable testing layer by targeting the highest-value, lowest-friction code: pure functions and service methods that encode business rules without touching the DOM. The backend already demonstrates the pattern — files like `test_service_helpers.py` and `test_lint.py` prove that testing pure logic with zero framework ceremony catches real regressions at near-zero maintenance cost. The frontend has the same shape of testable code (taxonomy classification, teaser generation, content parsing) but no coverage today beyond four smoke tests on `AppComponent`.

The core architectural insight is that this phase has two distinct shapes of testable code, and each demands a different testing ergonomic. True pure functions (`firstNonHeadingSentence`, `countTasks`) need zero Angular infrastructure — they are imported and called directly, identical to the backend's pytest pattern. Service methods that live behind Angular's dependency injection (`sectionFor`, signal derivations, auth state checks) need `TestBed` with mock providers, but remain fast because they never touch the DOM or make HTTP calls. The architecture must handle both shapes without forcing the heavier TestBed ceremony onto the simpler case.

The coverage gap scan is not an "additional" activity — it is the prerequisite that scopes the entire phase. Without it, the taxonomy and teaser tests are well-defined but the "scan-surfaced logic" task is unbounded. The scan produces a prioritized backlog ranked by complexity and change frequency, converting an open-ended directive into a concrete, estimable work list. The CI gate with coverage ratchet then locks in whatever coverage this phase achieves, preventing silent erosion during subsequent phases.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | Mock factories stay as simple factory functions until the third mock forces a structural decision. No generic test harness, no base test class, no builder pattern until co-location vs. centralization is resolved by actual count. |
| P7 — File Size and Structure | Each test file covers one source module. Test files follow the same under-200-lines target as production code. If a test file exceeds this, the source module's API surface is too wide — flag for future refactoring, do not split the test file artificially. |
| P1 — Adapter Boundary (applied to mocks) | Mock factories are the test-side equivalent of the adapter boundary. Feature tests never construct mock internals inline — they call a factory that returns a shaped spy. This keeps tests decoupled from service implementation details. |
| Backend testing conventions (ported) | The backend's pattern of aliasing imports to avoid test-runner collection issues, grouping tests by function under comment headers, and using descriptive camelCase test names carries forward to the frontend as Jasmine `describe`/`it` blocks with equivalent clarity. |
| Test current behavior, not ideal behavior | Every test asserts what the code does today. If a test reveals surprising behavior (dead branches, inconsistent states), the finding is captured as a follow-up issue — not fixed inline. Refactoring under test is explicitly out of scope. |

## Component Design

### Coverage Gap Scanner

**Purpose**: Transforms the open-ended "scan all services" directive into a concrete, prioritized backlog before any scan-surfaced tests are written.

The scanner runs `ng test --code-coverage` against the existing four tests to produce an Istanbul report. This report is the artifact — it maps every untested file, function, and branch in the frontend. The prioritization layer then ranks uncovered code by three factors: cyclomatic complexity (higher complexity means more value from testing), git change frequency (frequently changed code has higher regression risk), and proximity to the taxonomy/teaser layer (code that feeds into the project lifecycle state machine matters more than utility formatting). The output is a prioritized backlog document that gates Task 3.

### Taxonomy Test Suite

**Purpose**: Full branch coverage for the project lifecycle state machine — the classification logic that determines which section a project appears in and what its display priority is.

`sectionFor` encodes an implicit priority chain: active job overrides everything, then archived status, then file-based classification by spec presence. The test suite makes this priority chain explicit by testing each precedence level and each transition. This is not just coverage — the test descriptions become the authoritative documentation of the lifecycle rules until feature specs exist. Approximately 12 test cases organized into three `describe` groups: active-state precedence, file-based classification, and archive override.

`SECTION_ORDER` gets a structural assertion: exactly five sections in the declared order. This catches silent reordering that would change the dashboard layout without any other test failing.

### Teaser Test Suite

**Purpose**: Full branch coverage for the content extraction and display-string generation that populates project cards across all five lifecycle sections.

This suite has three layers. First, `firstNonHeadingSentence` — a pure string parser with approximately 14 cases covering empty input, markdown-only input, sentence extraction, truncation at 120 characters, and mixed content. Second, `countTasks` — a simple heading counter with approximately 6 cases covering boundary matching. Third, `projectTeaser` — a join function that consumes outputs from taxonomy, content parsing, and project metadata to produce display strings. The teaser function has at least 14 cases across five section branches plus a fallback.

The teaser suite is the natural integration point within the unit test layer. It does not make HTTP calls or touch the DOM, but it exercises the interaction between taxonomy classification, content extraction, and metadata formatting. If upstream functions change shape, teaser tests break first — making them an early warning system.

### Scan-Surfaced Test Suites

**Purpose**: Cover the highest-priority untested pure logic discovered by the coverage gap scan, extending mock infrastructure as needed.

The scope is explicitly bounded by the scan output, but the braindump identifies likely candidates: `AiService` response parsing and error mapping, `AuthService` token parsing and expiry checks, `ProjectsService` sorting or filtering logic, standalone utility functions, and computed signal derivations. Each of these falls into one of the two testing shapes — pure function (no TestBed) or service method (TestBed with mocks) — and the test file structure follows accordingly.

The mock convention decision happens here. When the third mock factory is needed (beyond the existing `createProjectsServiceMock` and `createAiServiceMock`), the co-location vs. centralization question must be resolved before writing it. The decision criteria: if mocks are consumed by only one test file, co-locate; if shared across multiple test files, centralize in a `testing/` directory. This is decided by observed usage, not predicted usage.

### Signal Testing Strategy

**Purpose**: Define how Angular signal derivations are tested without requiring DOM rendering.

Computed signals that derive state from other signals are high-value test targets — they encode business rules about what the UI should show given a combination of state inputs. The testing approach extracts the computation logic: if a signal's derivation is a pure function that happens to be wrapped in `computed()`, test the function directly. If the derivation depends on multiple source signals and the interaction matters, use `TestBed` with `createEnvironmentInjector` to instantiate the signal graph, set source values, and assert derived values. Neither approach touches the DOM. The key constraint is that signal tests must remain under the millisecond-speed threshold — if any signal test requires component instantiation, it belongs in a later phase.

### CI Pipeline Gate

**Purpose**: Convert Phase 3 coverage from a one-time effort into a durable quality floor that holds as the codebase evolves.

The pipeline adds a `test-frontend` job to GitHub Actions that runs `ng test --watch=false --browsers=ChromeHeadless --code-coverage` on every PR to master. The existing `ChromeHeadlessCI` configuration in `karma.conf.js` is reused — no new Karma configuration needed. Coverage HTML report is uploaded as a CI artifact for inspection. No hard coverage threshold — hard thresholds produce gamed line coverage (empty branches and trivial assertions added to hit numbers). The "no untested public method" rule enforced during code review is the real quality gate.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Test runner | Karma (existing) | Already configured in the Angular project with `ChromeHeadlessCI` browser. No migration cost. Jasmine is the assertion library. |
| Coverage tool | Istanbul via `ng test --code-coverage` | Built into Angular CLI. Produces lcov and JSON summary reports. No additional dependency. |
| Mock pattern | Jasmine `SpyObj` via factory functions | Two factories already exist and work. Consistent with Angular testing conventions. No additional mock library needed. |
| CI runner | GitHub Actions (`ubuntu-latest`) | Matches the backend CI environment. Node 20 for Angular CLI compatibility. |
| Coverage reporting | Istanbul HTML via `ng test --code-coverage` | Uploaded as CI artifact. No threshold enforcement — hard gates produce gamed coverage. Visual inspection via HTML report. |
| Parameterized tests | Jasmine `forEach` over test data arrays | The teaser and taxonomy tests are truth tables by nature. Expressing them as data arrays with `forEach` reduces boilerplate and makes adding cases trivial. No additional library needed. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Coverage scan as Step 0, not a parallel activity | The scan output scopes Task 3 entirely. Without it, "scan-surfaced logic tests" is unbounded work. Running it first converts an estimate into a backlog. | Adds a half-day gate before Task 3 can start. Tasks 1 and 2 can still run in parallel. |
| Co-location vs. centralization decided at mock #3, not upfront | Two mocks exist — both patterns work fine at that scale. Premature centralization creates directory structure for one consumer. Deciding at three mocks means the usage pattern is visible. | Risks a small refactor (moving two files) if centralization wins. Acceptable for a solo developer. |
| Pure functions tested without TestBed | `firstNonHeadingSentence`, `countTasks`, and any standalone utilities are plain TypeScript functions. TestBed adds setup cost with zero benefit for code that has no Angular dependencies. | Requires that these functions are exported independently, not only as class methods. If they are currently class methods, the test still works via TestBed — but the finding is flagged as a candidate for extraction in a future refactor. |
| Parameterized test style for truth-table cases | `projectTeaser` has 15+ cases that differ only in inputs and expected output. Writing each as a standalone `it()` block triples the line count without adding clarity. A data array with `forEach` makes the truth table scannable and extensible. | Slightly harder to debug a single failing case (must read the parameterized index). Mitigated by descriptive labels in the test data. |
| Coverage as artifact, not gate | Hard coverage thresholds produce gamed line coverage — empty branches and trivial assertions written to hit numbers, not meaningful behavioral coverage (ELA lesson). Surface HTML reports in CI; enforce quality through code review ("no untested public method" rule). | No automated regression detection. Acceptable — a solo developer reviewing their own PRs sees the coverage report directly. |
| No property-based testing in this phase | Libraries like `fast-check` would find edge cases in `firstNonHeadingSentence` that hand-written cases miss (Unicode, extreme lengths). But they add a dependency and a learning curve for a solo developer. | May miss edge cases that property tests would catch. Mitigated by the thorough hand-written case list (14 cases for one function). Re-evaluate after the base suite exists. |
| `projectTeaser` tested as-is, not refactored first | The function has high cyclomatic complexity (five section branches with sub-branches). Refactoring to a lookup table would reduce test count but changes behavior before it is captured. Test-first is the safer sequence. | Writing 15+ test cases for one function feels heavy. But these tests become the safety net for the refactor that follows. The test-first approach is a prerequisite, not overhead. |
| Ten-second speed ceiling for full suite | A solo developer abandons slow test suites. If the full suite exceeds ten seconds on `ChromeHeadless`, something is wrong — likely a test that accidentally bootstraps a component or makes a real HTTP call. The ceiling is a diagnostic, not just a goal. | Forces discipline about what belongs in this phase vs. later phases. A test that needs DOM rendering is deferred even if it tests "logic" — the rendering overhead pushes it past the speed threshold. |
| TestBed for all Angular tests, no shallow-render | TestBed is the standard Angular testing API. Shallow-render adds a third-party dependency and a different mental model. TestBed with mock providers is fast enough for service-level tests and keeps the testing approach consistent across the codebase. | More verbose setup than shallow-render for component tests. Acceptable — component tests are deferred to a later phase, and service tests need minimal TestBed configuration. |

## Test File Organization

Test files are co-located with their source modules following Angular CLI conventions. Each test file mirrors the source file it covers: `section-taxonomy.service.ts` is tested by `section-taxonomy.service.spec.ts` in the same directory. This is consistent with the existing `app.component.spec.ts` placement and avoids a separate test directory that creates navigation overhead for a solo developer.

Mock factories follow the same co-location pattern established by `projects.service.mock.ts` and `ai.service.mock.ts`. If the coverage scan surfaces a third service requiring a mock that is consumed by multiple test files, the convention shifts: all mock factories move to a shared `testing/` directory under `src/app/`. This decision is deferred to the point where the data exists, not predicted in advance.

The test data for parameterized tests (the truth tables for `projectTeaser` and `sectionFor`) lives inline in the test file, not in separate fixture files. The data arrays are small enough to scan visually and benefit from proximity to the assertions that consume them.

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Coverage scan reveals 3× more untested logic than estimated | High — the brainstorm flagged this explicitly | The scan produces a prioritized backlog, not an obligation to test everything. Task 3 is timeboxed to two days. The backlog captures what was deferred and why, feeding future phases. |
| `sectionFor` or `projectTeaser` are not exported as testable units | Medium — they may be private methods or inline in components | If so, the test uses TestBed to instantiate the containing service and calls through the public API. The finding is logged as a future refactoring candidate (extract to standalone function). No refactoring in this phase. |
| ChromeHeadless environment differences between local and CI | Low — but environment-specific failures are common in headless browser testing | The existing `ChromeHeadlessCI` configuration in `karma.conf.js` is already tuned for CI. The pipeline uses the same Node version (20) and runs `npm ci` for deterministic dependencies. |
| Coverage ratchet is set too low and does not meaningfully gate | Medium — if the baseline after Phase 3 is only 25% line coverage, it does not prevent most regressions | The ratchet is a floor, not a target. The real enforcement comes from the "no untested public method" rule applied during code review. The ratchet catches gross coverage drops, not individual method omissions. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving this design
- [Epic](./epic.md) – Scope, tasks, and success criteria
- [Timeline](./timeline.md) – Status tracking