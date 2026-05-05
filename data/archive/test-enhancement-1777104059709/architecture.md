# 🏗️ Solution Architecture: Test Enhancement

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The existing 250-test backend suite proves that individual endpoints exist and return correct shapes when called in isolation — but the Flask test client bypasses WSGI serialisation, every test runs against `CHAIN_PROVIDER=mock`, and no test exercises the bootstrap workflow end-to-end. The two production failures that motivated this epic were integration-level failures: a silent template fallback on AI error and a cross-test module leak in full-suite ordering. Neither was structurally catchable by a unit test. The architecture here closes that gap by adding the layers that the current suite structurally cannot provide, without duplicating what the existing 250 tests already cover well.

The design is a three-layer pyramid with a hard sequencing constraint at the base. The first layer reorganises and enriches existing unit tests — pytest class grouping, parametrized matrices, payload factories, snapshot goldens — so that later layers can build on consistent conventions rather than independently inventing them. The second layer adds contract integration tests that cross the boundaries the test client cannot reach: CORS headers, error-envelope consistency across all routes, OpenAPI runtime response-shape validation, and crucially the first test that exercises `CHAIN_PROVIDER=claude` rather than the mock path. The third layer adds browser-driven E2E coverage for the five shipped workflows that currently rely on manual smoke testing.

The single most consequential architectural decision is running all three layers under one test runner: pytest for backend and E2E, Jasmine/Karma for frontend service specs. Adding `@playwright/test` to the frontend stack would split the E2E runner from pytest, require separate CI steps, and duplicate fixture infrastructure across two languages. Keeping Python-only for backend and E2E means one `make test-all` covers the whole pyramid with shared fixtures, shared markers, and no context-switching between runners.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Parametrize over duplicate | One test class covers all six AI routes for missing-field, whitespace, and provider-error cases — per-route duplication is replaced by a single parametrized matrix |
| Factory fixtures over inline data | Named factory functions in `tests/fixtures/payloads.py` replace repeated inline JSON strings throughout the suite; per-service mock factory files eliminate per-test setup in component tests |
| API-based setup, UI-based assertions | Every E2E scenario seeds project state via `POST /api/projects` rather than clicking through the bootstrap modal — the UI test starts at the assertion-relevant moment |
| `data-test` selectors only | E2E page objects and future component tests query exclusively by `data-test` attributes; class and element selectors break on redesign, `data-test` attributes do not |
| Default isolation, not opt-in | `SPEC_DOC_DIR=tmp_path` is the conftest default for all filesystem-touching tests — isolation is automatic, not a per-test opt-in that individual tests can forget |
| Single provider stub per boundary | `pytest-httpserver` is the only mechanism for simulating Claude API responses; no per-test URL patching or SDK-internal mocking of the Anthropic client |

---

## System Boundaries

### What This System Includes

- **Test infrastructure baseline** — pytest class organisation as a `@Nested`-equivalent, parametrized matrices for repeated route shapes, a shared payload factory module, and a default filesystem-isolation fixture in `conftest.py`
- **Frontend service specs** — specs for the five uncovered services (`ai.service.ts`, `principles.service.ts`, `codebase.service.ts`, `references.service.ts`, `implementation.service.ts`) plus per-service mock factory files following the pattern established in `builder.service.spec.ts`
- **Snapshot layer** — `syrupy` golden-file assertions for all Python prompt functions; Karma `toEqual` fixture objects for TypeScript generators (`generateSpecIndex`, `generateTimeline`)
- **Contract integration tests** — CORS preflight and actual-request matrix, error-envelope shape matrix, OpenAPI runtime response-shape validation, and a `pytest-httpserver` stub test for the Claude SDK provider path
- **E2E foundation** — `pytest-playwright` and `pytest-bdd` setup, `[data-test]` selector retrofit scoped to the components the first five feature files exercise, page objects, and five Gherkin feature files covering bootstrap happy-path, bootstrap fail-fast, edit-spec, context-editor, and rewrite-operation
- **Pytest marker registry** — five markers (`unit`, `integration`, `e2e`, `snapshot`, `real_claude`) registered in `pyproject.toml`; `real_claude` ships as infrastructure only — no test body carries it in this epic

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| `@playwright/test` in `package.json` | Splits E2E into a second runner, duplicates fixture infrastructure. Trigger: a TS-only E2E concern that cannot be expressed in Python |
| Angular component test authoring | Service mock factories from Task 2 are the prerequisite; authoring starts when at least one factory file has a confirmed real consumer. Trigger: the first retrofitted component needs behaviour verification before it ships |
| Real-Claude tests in CI default | Each run is a billable Anthropic API call. `real_claude` marker provides local runability; CI promotion is triggered by the first paying user justifying the per-run cost |
| Visual regression, mutation testing, accessibility, cross-browser, load testing | Each carries a named trigger in the analysis. None is triggered by current usage or user reports |
| Coverage thresholds as build gates | ELA's documented lesson: local thresholds produce gamed line coverage. Coverage is surfaced as CI artefacts, not enforced as fail-fast gates |

---

## Component Design

### Test Infrastructure Baseline

**Purpose**: Provides the shared foundation every subsequent task depends on. Without it, Tasks 2, 3, and 4 each invent their own fixture style and the suite drifts apart rather than composing.

**Consumer**: Tasks 2, 3, 4, and 5 all import directly from this layer's `conftest.py` and `tests/fixtures/payloads.py`.

**Key Parts**:
- `conftest.py` (root-level) — expands to include the `SPEC_DOC_DIR=tmp_path` default fixture and a session-scoped `app` fixture; session-level for the expensive Flask factory, function-level for mutable state that must not leak between tests
- `tests/fixtures/payloads.py` — named factory functions (`make_rewrite_request`, `make_iterate_request`, `make_generate_request`, and so on) that replace every inline JSON string in the existing suite; the factory interface becomes the single definition of what each route expects as a valid payload
- Pytest class refactor of existing flat test files — grouping by HTTP verb and scenario (`class GetProject`, `class CreateProject`, `class DeleteProject`) so that `pytest tests/test_project.py::GetProject -v` runs a focused slice without string-matching across unrelated files

**Patterns**: Factory Method (payload builders), Fixture Scope management (session vs. function boundaries matched to setup cost and mutability)

---

### Frontend Service Specs

**Purpose**: Closes the five-of-seven uncovered service gap and establishes the mock factory convention that component tests will consume when that epic begins.

**Consumer**: Task 2 (five service specs); future component test authoring epic (mock factory files).

**Key Parts**:
- Five service spec files (`ai.service.spec.ts`, `principles.service.spec.ts`, `codebase.service.spec.ts`, `references.service.spec.ts`, `implementation.service.spec.ts`) — each follows the absolute-URL and `HttpClientTestingModule` pattern already established in `builder.service.spec.ts` and `projects.service.spec.ts`; no new testing pattern is introduced
- Per-service mock factory files (`ai.service.mock.ts`, and equivalents) — each exports a `createMockAiService()` function returning a typed Jasmine spy object; component tests import the factory and receive a consistent mock without duplicating setup; the mock shape mirrors the service interface, not its internal implementation

**Patterns**: Adapter (mock factory exposes the same interface as the real service, keeping component tests decoupled from service internals); Port of existing absolute-URL pattern from `builder.service.spec.ts`

---

### Snapshot Test Layer

**Purpose**: Makes prompt and generator outputs auditable — any change to a prompt function or TypeScript generator produces a visible diff before it reaches production rather than silently passing.

**Consumer**: Task 3 (Python prompt snapshots via `syrupy`; TypeScript generator fixtures via Karma `toEqual`).

**Key Parts**:
- `syrupy` integration in `modules/ai/tests/test_prompts.py` — one `assert_match_snapshot` call per prompt function; first run writes goldens under `__snapshots__/`; `--snapshot-update` regenerates all goldens in one command without manual file editing; this is the Python equivalent of ApprovalTests with auto-generated approved files
- Committed TypeScript fixture objects for `generateSpecIndex()` and `generateTimeline()` — Karma `toEqual` against a `spec/fixtures/generators/` directory; Jasmine 4+ snapshot support is not confirmed, so `toEqual` against a committed static object is the conservative choice; the fixture file is the golden and updates are explicit, not magic
- `snapshot` pytest marker on all syrupy tests — runnable in isolation via `pytest -m snapshot`, updatable without running the full suite

**Patterns**: Approval Testing (golden-file comparison produces a diff on any output change); Conservative default (Karma `toEqual` over unconfirmed Jasmine snapshot API)

---

### Contract Integration Tests

**Purpose**: Catches whole classes of bugs that unit tests and the test client structurally cannot — CORS misconfiguration on newly-registered routes, error-envelope inconsistency across all routes, response schema drift from `openapi.yaml`, and the completely untested `CHAIN_PROVIDER=claude` SDK path.

**Consumer**: Task 4 exclusively; each test class maps to one named gap from the epic's integration-level section.

**Key Parts**:
- CORS contract class — parametrized over every registered route; asserts both `OPTIONS` preflight and actual-request `Access-Control-Allow-Origin` headers reflect the `CORS_ORIGINS` environment variable; catches the class of bug where a new blueprint is registered but the CORS decorator is not applied
- Error-envelope contract class — parametrized over every registered route with malformed JSON, missing required field, non-existent path, and forced internal error; asserts `Content-Type: application/json` and `{error}` shape on every 4xx/5xx response; this is the runtime equivalent of Spring's `@ControllerAdvice` coverage guarantee — one class, all routes, one rule
- OpenAPI response-shape class — for each endpoint's happy-path fixture, calls the route and validates the actual response JSON against the OpenAPI YAML response schema using `jsonschema`; catches the "I renamed the response field in code but forgot `openapi.yaml`" failure mode that the existing structural test for paths does not reach
- `pytest-httpserver` Claude SDK stub class — sets `ANTHROPIC_BASE_URL` to the stub server's URL and `CHAIN_PROVIDER=claude`; verifies that a realistic Claude API response propagates through at least one route end-to-end without the mock provider; this is the only test in the entire suite that exercises the `claude` provider path — the 250 existing tests leave this entirely open
- `real_claude` marker declaration in `pyproject.toml` — ships as infrastructure; no test body carries it in this task; the marker exists so local Claude smoke tests can be run via `pytest -m real_claude` before a deploy

**Patterns**: Parametrized Contract Matrix (N routes, one test class per contract); Provider Stub (`pytest-httpserver` as the Python equivalent of MockWebServer); Runtime Schema Validation (OpenAPI spec enforces itself at test time, not just at lint time)

---

### E2E Foundation and Feature Files

**Purpose**: Replaces manual browser smoke as the safety net for the bootstrap workflow — the highest-risk shipped surface with zero automated coverage and the direct source of the production failures that motivated this epic.

**Consumer**: Task 5 (foundation setup and five feature files); future E2E expansion once the pattern is proven with passing feature files.

**Key Parts**:
- `pytest-playwright` and `pytest-bdd` setup — Python-native, reuses pytest fixtures and parametrize, single `make test-e2e` entry point; no separate `npm run test:e2e` step or package.json addition
- `[data-test]` selector retrofit — applied only to the four components the five feature files exercise (new-project modal, operation-bar, sidebar, output-panel); wider retrofit is deferred until the E2E pattern is proven with real passing scenarios; touching every template at once is not justified before the first feature file exists
- `e2e/pages/{feature}.page.py` page objects — each wraps Playwright's `Page` object and exposes named action and assertion methods backed exclusively by `[data-test]` selectors; Gherkin step implementations call page object methods and never reference selectors directly; a selector change in a template requires one page object method update, not a search across every step definition
- `e2e/features/bootstrap.feature`, `edit_spec.feature`, `context_editor.feature`, `rewrite_operation.feature`, `fail_fast.feature` — five Gherkin feature files; each scenario seeds state via `POST /api/projects` before the browser step begins; no scenario intercepts the network layer; Gherkin is reserved for multi-step user journeys, not assertions that belong at the unit layer

**Patterns**: Page Object (data-test-only selectors, one selector definition location); API-based Setup (seed via Flask before UI interaction begins); BDD (Gherkin only for multi-step workflows that read as user narratives)

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend unit / integration | pytest + pytest-flask | Already the test runner; pytest-flask provides a live-server fixture without custom threading; consistent with existing 250-test suite |
| Snapshot testing | syrupy | Pytest-native, auto-generates `__snapshots__/` directory, assertion integrates with pytest's diff output, `--snapshot-update` regenerates all goldens in one command |
| Provider stubbing | pytest-httpserver | Intercepts HTTP at the network layer, testing the full SDK→WSGI→route path without patching SDK internals; Python equivalent of MockWebServer |
| Coverage tracking | pytest-cov | Integrates with pytest, generates HTML artefacts for CI; no local threshold enforcement |
| E2E runner | pytest-playwright + pytest-bdd | Single language across unit, integration, and E2E; pytest fixtures and parametrize are available in E2E scenarios; Gherkin feature files without a second JS runtime |
| Frontend unit | Jasmine + Karma (existing) | Already in place; five new service specs and mock factories follow the pattern established in `builder.service.spec.ts` — no new framework introduced |
| TypeScript snapshot equivalent | Karma `toEqual` + committed fixture files | Jasmine 4+ snapshot support is unconfirmed; `toEqual` against a committed fixture object is conservative, diffable in PRs, and portable across Jasmine versions |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Python-only E2E via pytest-playwright, not @playwright/test | Single test runner across all three layers; pytest fixtures and parametrize available in E2E step definitions; one `make test-all` command covers the pyramid | TS-side Playwright API is more ergonomic for TS-heavy assertions; if E2E ever needs Angular internals (component state, change detection), this forces a refactor |
| `data-test` selector retrofit scoped to the five feature files' components | Incremental convention prevents a large diff that touches every template before a single E2E test passes; each future feature file extends the retrofit as it goes | Components not yet retrofitted are unreachable by E2E; any accidental class-selector query in a step fails loudly rather than passing on a fragile match |
| pytest classes for `@Nested`-equivalent organisation | `pytest tests/test_project.py::GetProject -v` runs a focused slice; class grouping makes the test's concern legible at a glance; consistent with how ELA's `@Nested` organises by HTTP verb and scenario | One additional indentation level; trivially simple files with one or two tests gain nothing from a class wrapper — parametrize remains the better tool for those |
| syrupy over a custom golden-file approach | Integrates with pytest's assertion protocol, auto-generates the `__snapshots__/` directory, `--snapshot-update` is a one-command regeneration; custom `open("golden.txt").read()` requires manual snapshot management and produces no pytest diff output | syrupy is an additional dependency; the custom approach is more transparent for anyone unfamiliar with the library |
| `pytest-httpserver` over Anthropic SDK mocking | Testing at the HTTP layer verifies the full SDK→WSGI→route path; patching SDK internals risks validating the mock shape rather than the actual provider path | HTTP-level interception requires starting the stub server as a fixture; adds measurable latency per integration test; the trade-off is worthwhile given the cost of the "mock provider passes, real provider broken" failure mode |
| Karma `toEqual` fixtures for TypeScript generators | Confirmed capability over speculative API; Jasmine 4+ snapshot support is not confirmed and adding an uncertain dependency risks the TypeScript test infrastructure | Less ergonomic to update than `--snapshot-update`; acceptable because the TypeScript generators (`generateSpecIndex`, `generateTimeline`) change infrequently and the fixture file is always an explicit, reviewable artefact |
| No coverage thresholds as local build gates | ELA's documented lesson: hard local thresholds produce gamed line coverage — empty branches and trivial assertions added to hit numbers, not meaningful behavioural coverage | Coverage surface is invisible without gates; mitigated by surfacing HTML report as a CI artefact and reviewing per sprint |
| API-based setup for all E2E scenarios | `POST /api/projects` to seed state is deterministic, fast, and immune to UI changes in the setup flow | If the projects API itself is broken, the E2E setup step fails with a confusing error; mitigated by Task 4's contract integration tests confirming the API shape before E2E runs |

---

## Patterns

### Parametrized Contract Matrix

**When to use**: One assertion applies to N inputs where N is known at write time — all six AI routes, all registered error cases, all CORS-decorated routes.

**How it works**: A single test class is parametrized over the N input cases; each combination produces an independently reportable pass or fail; adding a new route means adding one entry to the parametrize list, not authoring a new test function.

**Example in this system**: The error-envelope contract class in Task 4 asserts `{error}` JSON shape on every 4xx/5xx response across all registered routes — one test class, one `parametrize` decorator, all routes covered; the CORS contract class does the same for preflight and actual-request headers.

---

### Provider Stub

**When to use**: Testing a code path that calls an external HTTP API, where the goal is to prove the path propagates a response correctly end-to-end rather than to test the external API itself.

**How it works**: `pytest-httpserver` starts a local HTTP server within the test process; the test overrides `ANTHROPIC_BASE_URL` to point at the stub; the Anthropic SDK sends its request to the stub rather than Anthropic's production endpoint; the stub returns a pre-configured response body; the test asserts the response value propagates through the route's output.

**Example in this system**: The Task 4 Claude SDK stub test is the first and only test in the suite that sets `CHAIN_PROVIDER=claude` — the 250 existing tests never leave the mock path. This single test is the proof that the provider path is not entirely untested.

---

### Page Object

**When to use**: Any E2E scenario that interacts with more than one element on a screen; any `[data-test]` selector that would otherwise appear in more than one step definition file.

**How it works**: A Python class in `e2e/pages/` wraps Playwright's `Page` object and exposes named action and assertion methods backed exclusively by `[data-test]` selectors; step implementations call page object methods and never reference selectors directly; when a selector changes, one method in one page object file is the only update required.

**Example in this system**: `NewProjectPage.fill_braindump(text)` and `NewProjectPage.click_generate()` are the only locations in the entire E2E suite that know the `[data-test]` values for those modal elements; the bootstrap feature file's Gherkin steps call these methods without knowing or caring which selector backs them.

---

### Factory Fixture

**When to use**: Any test that constructs a request payload inline; any payload structure that appears in more than one test file or test class.

**How it works**: Named factory functions in `tests/fixtures/payloads.py` accept required parameters and return fully-formed request dicts; when a route's required field names change, one factory function update propagates to every test that uses it rather than requiring a search-and-replace across test files.

**Example in this system**: Tasks 4 and 5 both consume the payload factories established in Task 1; the CORS contract tests and the error-envelope contract tests both call `make_rewrite_request` with deliberately invalid inputs — the factory is the single authoritative definition of what a valid rewrite payload looks like.

---

## Execution Flow

```
[Phase 1 — Infrastructure (Task 1)]
  pytest class refactor ──→ payload factories ──→ default tmp_path fixture
  (hard prerequisite — Tasks 2, 3, 4 all import from here)

[Phase 2 — Parallel Coverage (Tasks 2, 3, 4)]
  Task 2: Frontend service specs + mock factories
  Task 3: Snapshot tests (syrupy goldens + TS fixtures)       ← parallel
  Task 4: Contract integration tests (CORS, envelope, OpenAPI, httpserver)

[Phase 3 — E2E (Task 5)]
  data-test retrofit ──→ page objects ──→ feature files
  (depends on Task 1 fixture patterns + Task 2 service mocks)
```

Task 1 is the hard prerequisite: the payload factories and default `tmp_path` fixture it establishes are consumed directly by Tasks 2, 3, and 4. Once Task 1 ships, those three tasks have no dependency on one another and can run in parallel. Task 5 depends on Task 1 for fixture patterns and on Task 2 for service mock conventions that E2E scenarios exercise indirectly through the Angular app, but does not depend on Tasks 3 or 4.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview