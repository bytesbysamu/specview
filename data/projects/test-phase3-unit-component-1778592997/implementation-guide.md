# Implementation Guide: Test Phase 3 — Unit & Component Tests

## Overview
This epic delivers the Angular frontend's first meaningful test coverage by targeting pure functions and service methods that encode business rules — taxonomy classification, teaser generation, and content parsing — without touching the DOM. The four tasks sequence as follows: Task 1 (coverage gap scan) and Task 2 (taxonomy + teaser suites) run in parallel; Task 3 (scan-surfaced logic tests) depends on both to define its scope and establish mock conventions; Task 4 (CI pipeline gate) runs last to lock in coverage as a durable quality floor.

## Shared Pre-flight
- Run `npm ci` inside `web-ng/` to ensure deterministic dependencies
- Confirm `ng test --watch=false --browsers=ChromeHeadless` passes with the existing four tests in `web-ng/src/app/app.component.spec.ts`
- Verify `karma.conf.js` at the project root contains the `ChromeHeadlessCI` browser configuration
- Confirm Istanbul coverage output lands in `web-ng/coverage/` after a `--code-coverage` run
- Review existing mock factories in `web-ng/src/app/services/projects.service.mock.ts` and `web-ng/src/app/services/ai.service.mock.ts` to understand the SpyObj pattern in use
- Verify that `sectionFor`, `firstNonHeadingSentence`, `countTasks`, and `projectTeaser` are exported from their respective modules and can be imported directly into a test file
- Ensure Node 20 is available locally and matches the CI runner target
- Confirm GitHub Actions is enabled on the repository and that `.github/workflows/` exists

---

## Task 1: Coverage Gap Scan  [Effort: 0.5 days]

### What
Run coverage tooling against the existing four tests to produce a concrete map of every untested service, helper, pipe, and signal derivation in the frontend. This scan replaces the open-ended "scan all services" directive with a prioritized backlog that scopes Task 3 entirely.

### Files
- **Modify**: `web-ng/karma.conf.js` — enable JSON summary reporter alongside HTML if not already configured, so the coverage output is machine-parseable
- **Create**: `web-ng/coverage-backlog.md` — the prioritized backlog artifact ranking uncovered code by cyclomatic complexity, git change frequency, and proximity to the taxonomy/teaser layer

### Steps
1. Run `ng test --watch=false --browsers=ChromeHeadless --code-coverage` from the `web-ng/` directory to generate the Istanbul coverage report against the existing four tests.
2. Open the HTML report at `web-ng/coverage/index.html` and inventory every file, function, and branch that shows zero or partial coverage.
3. For each uncovered file, assess cyclomatic complexity by inspecting the function structure — count conditional branches, switch cases, and nested logic paths.
4. Run `git log --oneline --since="3 months ago" -- web-ng/src/app/services/` to rank uncovered files by change frequency — files changed more often carry higher regression risk.
5. Score each uncovered unit on three axes (complexity, change frequency, proximity to taxonomy/teaser) and sort into a prioritized list.
6. Write the prioritized backlog into `web-ng/coverage-backlog.md`, grouping entries into tiers: high priority (test in Task 3), medium priority (test if time permits), and deferred (future phases).
7. Record the baseline coverage percentages (statements, branches, functions, lines) at the top of the backlog document for reference — coverage is a CI artifact, not a gate.

### Verify
- `web-ng/coverage/index.html` exists and opens in a browser showing per-file coverage
- `web-ng/coverage-backlog.md` exists and contains at least three tiers of prioritized untested code
- The backlog includes baseline coverage percentages for statements, branches, functions, and lines
- Every service file under `web-ng/src/app/services/` appears in either the "already covered" or "untested" section of the backlog

---

## Task 2: Taxonomy + Teaser Test Suites  [Effort: 1.5 days]

### What
Write unit tests achieving full branch coverage for `sectionFor`, `SECTION_ORDER`, `firstNonHeadingSentence`, `countTasks`, and `projectTeaser` — the pure logic that encodes the project lifecycle state machine and card display rules. These approximately 45 test cases become the authoritative documentation of lifecycle and display rules until feature specs exist.

### Files
- **Create**: `web-ng/src/app/services/section-taxonomy.service.spec.ts` — test suite for `sectionFor` (approximately 10 cases covering active-state precedence, file-based classification, and archive override) and `SECTION_ORDER` (structural assertion on count and order)
- **Create**: `web-ng/src/app/services/project-teaser.spec.ts` — test suite for `firstNonHeadingSentence` (approximately 14 cases), `countTasks` (approximately 6 cases), and `projectTeaser` (approximately 15 cases across all five section branches plus fallback)

### Steps
1. Create `section-taxonomy.service.spec.ts` co-located with the source module. Import `sectionFor` and `SECTION_ORDER` directly — these are pure functions that need no TestBed.
2. Add a `describe('SECTION_ORDER')` block with an assertion that the array contains exactly five sections in the declared order: Active, Ready to build, Specced, Braindumps, Archive.
3. Add a `describe('sectionFor')` block organized into three sub-groups: active-state precedence (hasActiveJob overrides file state), file-based classification (implementation-guide maps to Specced, architecture/epic maps to Ready to build, braindump-only maps to Braindumps, empty specs maps to Braindumps), and archive override (archived flag wins over all file states).
4. Use parameterized test style — define a data array of input/expected-output pairs and iterate with `forEach` — so the truth table is scannable and new cases are trivial to add.
5. Create `project-teaser.spec.ts` co-located with the source module. Import `firstNonHeadingSentence`, `countTasks`, and `projectTeaser` directly.
6. Add a `describe('firstNonHeadingSentence')` block covering: empty string, whitespace-only, headers-only, bullet-only, blockquote-only, table-only, sentence after header, exclamation, question mark, multi-sentence (first only), line over 120 characters (truncated with ellipsis), line exactly 120 characters (no truncation), mixed content, and code-block content.
7. Add a `describe('countTasks')` block covering: no Task headings, one heading, three headings, TaskExtra without space boundary, h3 Task (should not count), and Task heading in middle of content.
8. Add a `describe('projectTeaser')` block organized by section: Active (with step, without step with content, without step without content), Specced (with task count plural, singular, zero with content, no content), Ready to build (with content, without content), Braindumps (with content, without content), Archive (valid date, invalid date, no date), and unknown section fallback.
9. Run `ng test --watch=false --browsers=ChromeHeadless` and confirm all new tests pass alongside the existing four.
10. If any function is not directly importable (e.g., it is a private method on a service class), use TestBed to instantiate the containing service and call through the public API, then note the function as a candidate for extraction in a future refactor.

### Verify
- `ng test --watch=false --browsers=ChromeHeadless` passes with zero failures
- `ng test --code-coverage` shows 100% branch coverage for `sectionFor` and `projectTeaser`
- The test count has increased from 4 to approximately 49 (4 existing + approximately 45 new)
- Full suite completes in under 10 seconds on ChromeHeadless

---

## Task 3: Scan-Surfaced Logic Tests  [Effort: 2 days]

### What
Using the prioritized backlog from Task 1, write unit tests for the highest-priority untested pure logic discovered by the coverage scan. This task also resolves the mock factory convention — co-location versus centralized `testing/` directory — before the third mock is created.

### Files
- **Create**: `web-ng/src/app/services/auth.service.spec.ts` — tests for token parsing, expiry checks, and login-state derivation in `AuthService`
- **Create**: `web-ng/src/app/services/ai.service.spec.ts` — tests for response parsing, error mapping, and stream-handling logic in `AiService`
- **Modify**: `web-ng/src/app/services/ai.service.mock.ts` — extend the existing mock factory if new spy methods are needed for the test cases
- **Create or Modify**: Additional spec files as dictated by the coverage backlog (e.g., utility functions, computed signal derivations, `ProjectsService` sorting/filtering logic)
- **Create** (conditional): `web-ng/src/app/testing/` directory with centralized mock factories — only if the third mock is consumed by multiple test files; otherwise keep mocks co-located

### Steps
1. Review the prioritized backlog in `web-ng/coverage-backlog.md` and select all high-priority entries for implementation. Confirm the list with the backlog before writing any tests.
2. For each high-priority entry, determine its testing shape: pure function (no TestBed needed) or service method (TestBed with mock providers). Group entries by shape to batch setup work.
3. Start with `AuthService` tests. Create `auth.service.spec.ts` using TestBed with a mock HTTP backend. Write tests for token parsing from login responses, expiry timestamp checks, and the `isLoggedIn` signal derivation.
4. Continue with `AiService` tests. Create `ai.service.spec.ts` using TestBed. Write tests for response parsing (extracting structured data from AI responses), error mapping (HTTP errors to user-facing messages), and any stream or retry logic.
5. Before creating the third mock factory, inspect how many test files will consume it. If only one test file needs it, co-locate the mock next to that test file following the existing pattern. If multiple test files need it, create `web-ng/src/app/testing/` and move all mock factories there, updating imports in existing test files.
6. Document the mock convention decision as a comment at the top of the mock file or testing directory index so future contributors follow the same pattern.
7. For any computed signal derivations surfaced by the scan, extract the computation logic and test the underlying function directly. If extraction is not possible without refactoring, use TestBed with `createEnvironmentInjector` to instantiate the signal graph, set source values, and assert derived values.
8. For any standalone utility functions surfaced by the scan, write direct import tests with no Angular infrastructure.
9. Run the full suite after each new spec file to catch regressions early — no new test should break existing tests.
10. After all high-priority backlog entries are covered, run `ng test --code-coverage` and compare the new coverage percentages against the baseline recorded in Task 1.

### Verify
- `ng test --watch=false --browsers=ChromeHeadless` passes with zero failures including all tests from Task 2
- Every high-priority entry in `web-ng/coverage-backlog.md` has a corresponding spec file with at least one test per public method
- The mock convention decision (co-location or centralized) is resolved and consistently applied across all mock factories
- Full suite still completes in under 10 seconds on ChromeHeadless

---

## Task 4: CI Pipeline Gate  [Effort: 0.5 days]

### What
Add a `test-frontend` job to GitHub Actions so that `ng test` runs on every PR to master, with coverage HTML uploaded as an artifact. This converts Phase 3 coverage from a one-time effort into a durable quality floor.

### Files
- **Modify**: `.github/workflows/ci.yml` — add a `test-frontend` job that checks out code, installs Node 20, runs `npm ci`, executes `ng test --watch=false --browsers=ChromeHeadless --code-coverage`, and uploads the `web-ng/coverage/` directory as a CI artifact
- **Modify**: `web-ng/karma.conf.js` — confirm `ChromeHeadlessCI` browser is configured with appropriate flags for the CI environment (no-sandbox, disable-gpu); add or verify these flags if missing

### Steps
1. Open the existing `.github/workflows/ci.yml` and identify where to add the new `test-frontend` job. Place it alongside any existing backend test jobs so frontend and backend tests run in parallel.
2. Define the `test-frontend` job with `runs-on: ubuntu-latest`. Add steps for `actions/checkout@v4`, `actions/setup-node@v4` with Node 20, `npm ci` in the `web-ng/` directory, and the `ng test` command with `--watch=false --browsers=ChromeHeadless --code-coverage`.
3. Add an `actions/upload-artifact@v4` step that uploads `web-ng/coverage/` as a named artifact called `coverage` so reviewers can inspect the HTML report directly from the PR checks tab.
4. Verify that `karma.conf.js` has the `ChromeHeadlessCI` custom launcher with `--no-sandbox` and `--disable-gpu` flags, which are required for headless Chrome in the GitHub Actions Ubuntu runner.
5. Push the workflow change to a branch and open a test PR to trigger the new job. Confirm the job runs, tests pass, and the coverage artifact appears in the PR checks.
6. Verify the full CI pipeline completes in a reasonable time — the frontend test job should add no more than two minutes to the total pipeline duration.

### Verify
- The `test-frontend` job appears in the GitHub Actions workflow and runs on every PR to master
- `ng test --watch=false --browsers=ChromeHeadless` passes in the CI environment with all tests green
- The coverage HTML artifact is uploaded and downloadable from the PR checks tab
- The CI pipeline total duration has not increased by more than two minutes compared to the pre-Phase-3 baseline