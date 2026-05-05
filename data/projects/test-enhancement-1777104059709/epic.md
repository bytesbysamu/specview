# 🎯 Epic: Test Enhancement

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The spec-doc-api bootstrap workflow chains four-to-N AI calls, three template generations, and N file saves in a single user action — yet zero tests exercise that chain end-to-end. Two production failures in the last sprint exposed this directly: a silent template fallback on AI error was caught only by manual browser smoke, and a cross-test module leak only appeared in full-suite ordering. Both are integration-level failures that unit tests structurally cannot catch. Closing this gap is the difference between a suite that proves individual endpoints exist and one that proves the product works.

The frontend surface carries the same exposure. Seven services drive every AI interaction and fifteen components render every user-facing screen, but five services have no specs and zero components have tests. Without `[data-test]` selectors and a Page Object convention established first, every future test becomes a brittle CSS query waiting to break on the next layout change. Establishing these conventions now — before the chain-primitive port adds more surface — is the lowest-cost moment to do so.

Each layer compounds. Parametrized contract tests cover all six AI routes in a single assertion and catch a whole class of envelope drift no per-route test addresses. Snapshot tests make prompt-tweaks auditable without spinning up HTTP. E2E with API-based setup makes the bootstrap workflow deterministic. Together they close the gap from "250 tests prove endpoints in isolation" to "the test suite would have caught both production failures."

**Value Proposition**: Replace manual browser smoke as the regression safety net for spec-doc-api's shipped workflows with a layered test suite that catches integration and E2E failures before production.

---

## Scope

### What This Epic Covers

- **Test infrastructure baseline** — pytest class organisation, parametrize patterns for repeated shapes, shared payload factory functions, and filesystem isolation as the default fixture
- **Frontend service specs** — the five uncovered service units and mock-factory conventions that unblock future component tests
- **Snapshot coverage for generated content** — golden-file verification for all prompt functions and a committed-fixture approach for TypeScript generator outputs
- **Contract integration tests** — CORS matrix, error-envelope matrix, OpenAPI-response-shape validation, and stub-Claude HTTP tests via `pytest-httpserver`
- **E2E layer** — Playwright + pytest-bdd setup, `[data-test]` selector retrofit on the components the first feature files touch, page objects, and feature files covering bootstrap, edit-spec, context-editor, rewrite-operation, and fail-fast workflows

### What This Epic Does NOT Cover

- ❌ `@playwright/test` in package.json — one language, one E2E runner; Python-only per the analysis decision
- ❌ `real_claude` test authoring — the marker infrastructure ships in Task 4; actual Anthropic API stubs are deferred until httpserver tests prove the provider path works
- ❌ Angular component test authoring — service mock conventions ship in Task 2 and unblock component tests, but component test authoring is a follow-on epic
- ❌ Visual regression, mutation testing, accessibility, cross-browser, and load testing — each carries a named trigger condition in the analysis; none is triggered today

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Test infrastructure baseline** | None | — | 1 day | High |
| 2 | **Frontend service specs** | 1 | 3, 4 | 0.5 days | High |
| 3 | **Snapshot tests for generated content** | 1 | 2, 4 | 0.5 days | High |
| 4 | **Contract integration tests** | 1 | 2, 3 | 1 day | High |
| 5 | **E2E foundation and feature files** | 1, 2 | — | 2 days | High |

### Task 1: Test infrastructure baseline

Reorganise every existing backend test file from flat functions into pytest classes, apply `@pytest.mark.parametrize` to the three repeated-shape patterns (missing field → 422, whitespace input → 400, provider error → 502) across all AI routes, extract a shared payload factory module replacing inline JSON strings throughout the suite, and make `SPEC_DOC_DIR=tmp_path` the conftest default so filesystem-touching tests get isolation without opting in. This is the mechanical prerequisite that keeps every later task's fixtures and parametrize patterns consistent rather than independently invented.

**Port budget**: ~60 lines of infrastructure across `conftest.py` and the payload factory module; excludes snapshot golden files (Task 3), `pytest-httpserver` fixtures (Task 4), and all E2E infrastructure (Task 5) — none of those has a current consumer at this step.

### Task 2: Frontend service specs

Write service specs for the five uncovered services — `ai.service.ts`, `principles.service.ts`, `codebase.service.ts`, `references.service.ts`, `implementation.service.ts` — following the absolute-URL and HttpClient mock pattern already established in `builder.service.spec.ts` and `projects.service.spec.ts`, and extract a per-service mock factory file so component tests can consume a consistent mock without duplicating setup. The open question about TestBed versus a render wrapper for component tests must be resolved before this task starts, because the mock factory shape it establishes locks in the component test convention.

**Port budget**: ~25 lines per service spec across five services plus one mock factory per service; excludes component test authoring, which is a follow-on epic once the mock factory pattern is proven with real consumers.

### Task 3: Snapshot tests for generated content

Install `syrupy` and write one snapshot assertion per Python prompt function in `modules/ai/tests/test_prompts.py`, verifying the full output text of each golden; for the TypeScript generators (`generateSpecIndex()`, `generateTimeline()`), use Karma's `toEqual` against a committed fixture object rather than a Python-only snapshot tool. The frontend snapshot mechanism must be decided — Karma `toEqual` is the default unless Jasmine 4+ snapshot support is confirmed — before this task starts.

**Port budget**: ~30 lines of Python snapshot tests plus committed TypeScript fixture objects; excludes any changes to prompt logic or generator behaviour — this task only observes and pins existing outputs.

### Task 4: Contract integration tests

Add four contracts that unit tests structurally cannot verify: a parametrized CORS preflight and actual-request matrix across all routes, a parametrized error-envelope matrix asserting `{error}` JSON shape on every 4xx/5xx response, an OpenAPI-response-shape test that validates each happy-path response against the YAML schema at runtime, and a `pytest-httpserver` stub test that sets `CHAIN_PROVIDER=claude` and points `ANTHROPIC_BASE_URL` at the stub server to verify the claude SDK provider path propagates a response through at least one route end-to-end. The `real_claude` pytest marker is registered here; no actual Anthropic API stubs are authored.

**Port budget**: ~80 lines across four new test classes; CORS and error-envelope tests reuse the payload factories from Task 1; `real_claude` authoring is explicitly deferred — the marker existence is the deliverable here, not any test that carries it.

### Task 5: E2E foundation and feature files

Install `pytest-playwright` and `pytest-bdd`, register the five pytest markers in `pyproject.toml`, retrofit `[data-test]` selectors onto the components the first feature files exercise (new-project modal, operation-bar, sidebar, output-panel), write page objects in `e2e/pages/` for each retrofitted component, and author five Gherkin feature files: bootstrap happy-path, bootstrap fail-fast, edit-spec with auto-save persistence, context-editor CRUD, and rewrite-operation. Every E2E scenario uses `POST /api/projects` to seed state via the API and hits real Flask plus real Angular — no network interception.

**Port budget**: ~200 lines across feature files and page objects; `[data-test]` selector retrofit is limited to the components the five feature files actually touch; component tests and real-Claude E2E smoke are explicitly excluded — component tests are a follow-on epic, real-Claude smoke is deferred until Task 4's httpserver tests prove the provider path is stable.

---

## Success Criteria

This epic is complete when:

- ✅ Every AI route's missing-field, whitespace, and provider-error cases are covered by a single parametrized test each — no per-route duplication
- ✅ All seven frontend services have specs; each has a mock factory file that can be imported by component tests without additional setup
- ✅ Every Python prompt function has a snapshot assertion; running `--snapshot-update` regenerates all goldens without manual edits
- ✅ CORS headers, error-envelope shape, and OpenAPI-response-shape are each verified by a single parametrized contract test that exercises all routes
- ✅ The `pytest-httpserver` stub test passes with `CHAIN_PROVIDER=claude`, proving the SDK provider path — not just the mock path — carries a response through at least one route
- ✅ The bootstrap workflow — happy-path and fail-fast — passes as a Playwright feature file with API-based setup; no manual browser smoke required to confirm these scenarios
- ✅ The edit-spec, context-editor, and rewrite-operation workflows each have a passing Playwright feature file

---

## Non-Goals

- ❌ Angular component test authoring — service mock conventions from Task 2 are the prerequisite; component test authoring is deferred until the factory pattern has at least one real consumer
- ❌ Real-Claude CI integration — the `real_claude` marker ships in Task 4, but running Anthropic API calls in default CI is deferred until the httpserver tests prove the provider path reliable and per-run cost is justified by a paying user
- ❌ Coverage thresholds as build gates — coverage is tracked and surfaced in CI artefacts; local fail-fast thresholds produce gamed line coverage and are not introduced
- ❌ Cross-browser E2E — Chrome via Playwright is sufficient; Safari support is triggered only by a confirmed user bug report

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview