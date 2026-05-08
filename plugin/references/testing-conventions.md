# Testing Conventions — specview

This reference describes the testing strategy for the specview stack.
All agents and skills that write or modify tests must read this file first.

## The Test Pyramid

Three layers. Each layer catches a distinct class of failure. Do not skip layers.

```
[E2E]              — Gherkin feature files, Playwright + pytest-bdd
[Contract]         — CORS, error envelope, OpenAPI schema validation
[Unit]             — Individual routes, services, signals in isolation
```

Unit tests catch: wrong response shapes, missing fields, auth failures.
Contract tests catch: CORS misconfiguration on new routes, error envelope drift across all routes, OpenAPI schema divergence, provider path gaps.
E2E tests catch: route renames, template changes, broken API contracts — integration failures that unit tests structurally cannot reach.

**Coverage is a CI artifact, not a build gate.** ELA's documented lesson: hard local thresholds produce gamed line coverage — empty branches and trivial assertions added to hit numbers, not meaningful behavioral coverage. Surface HTML reports in CI; never enforce a percentage threshold as a fail-fast.

---

## Backend Testing (pytest)

### Module structure

Tests live in `api/modules/{name}/tests/test_{name}.py`.
One test file per module. Parametrize over per-route duplication.

### Fixtures

**Factory functions over inline data.** Named factory functions in `tests/fixtures/payloads.py` replace repeated inline JSON strings:

```python
# tests/fixtures/payloads.py
def make_brainstorm_request(text="hello", **overrides):
    return {"text": text, **overrides}
```

When a route's required field changes, one factory update propagates everywhere.
Without factories, a field rename requires a search-and-replace across all test files.

**Default isolation, not opt-in.** The root `conftest.py` applies `tmp_path` as the default for all filesystem-touching tests. Tests that touch `SPEC_DOC_DIR` or project files must not set their own temp dir — they inherit the default fixture. Isolation is automatic; opt-out requires justification.

**Fixture scope:** Session-scoped for expensive setup (Flask app factory, DB engine). Function-scoped for mutable state that must not leak (session, in-memory job dicts).

### Test organisation

Use pytest classes for `@Nested`-equivalent grouping — by HTTP verb and scenario:

```python
class TestGetProject:
    def test_returns_project_for_owner(self, client): ...
    def test_returns_404_for_unknown(self, client): ...

class TestCreateProject:
    def test_creates_project_and_returns_201(self, client): ...
```

`pytest tests/test_project.py::TestGetProject -v` runs a focused slice.
Trivially simple files with one or two tests gain nothing from a class wrapper — use parametrize instead.

### Parametrized contract matrix

One test class per contract concern, all registered routes as the parametrize input:

```python
@pytest.mark.parametrize("route,method", ALL_ROUTES)
class TestErrorEnvelope:
    def test_malformed_json_returns_error_shape(self, client, route, method):
        resp = client.open(route, method=method, data=b"not-json")
        assert resp.status_code in (400, 422)
        assert "error" in resp.get_json()
```

CORS, error envelope, and OpenAPI response shape are each a single class covering all routes. Adding a new route means adding one entry to `ALL_ROUTES`.

### Provider stub

Test the `CHAIN_PROVIDER=claude` path (SDK provider) using `pytest-httpserver`:

```python
def test_sdk_provider_propagates_response(httpserver, monkeypatch):
    httpserver.expect_request("/v1/messages").respond_with_json({...})
    monkeypatch.setenv("ANTHROPIC_BASE_URL", httpserver.url_for("/"))
    monkeypatch.setenv("CHAIN_PROVIDER", "claude")
    resp = client.post("/api/brainstorm", json={"text": "hello"})
    assert resp.status_code == 200
```

`pytest-httpserver` intercepts at the HTTP layer — verifies the full SDK→WSGI→route path without patching SDK internals.

### Snapshot testing (prompt functions)

Use `syrupy` for golden-file assertions on prompt functions:

```python
def test_brainstorm_prompt_matches_snapshot(snapshot):
    result = build_brainstorm_prompt("my text")
    assert result == snapshot
```

First run writes the golden. `--snapshot-update` regenerates all goldens.
Any change to a prompt function produces a visible diff in the PR — not a silently passing test.

### Pytest markers

Five markers registered in `pyproject.toml`:
- `unit` — fast, no external I/O
- `integration` — crosses a service boundary (DB, subprocess, HTTP)
- `e2e` — requires a live browser
- `snapshot` — syrupy golden-file tests
- `real_claude` — calls the real Anthropic API (never runs in CI by default)

---

## Frontend Testing (Jasmine/Karma)

### What requires a spec

- Every `*.service.ts` in `services/` — HTTP contract and error handling.
- The polling component — `clearInterval` called on completion and on error.
- The billing gate component — free-tier error state renders correctly.

### Per-service mock factories

Each service has a mock factory file alongside its spec:

```
services/
├── ai.service.ts
├── ai.service.spec.ts
└── ai.service.mock.ts       ← exports createMockAiService()
```

```typescript
// ai.service.mock.ts
export function createMockAiService(): jasmine.SpyObj<AiService> {
  return jasmine.createSpyObj('AiService', ['brainstorm', 'expand', 'rewrite']);
}
```

Component tests import `createMockAiService()` from the mock file.
Never duplicate spy setup inline — it drifts apart across test files.

### Service spec pattern

Follow the established `builder.service.spec.ts` pattern:
- Use `HttpClientTestingModule` and `HttpTestingController`.
- Absolute URLs in expectations (match what the service sends).
- One `describe` block per method, one `it` per scenario.

```typescript
it('brainstorm posts to /api/brainstorm and returns text', async () => {
  const promise = service.brainstorm('hello');
  const req = httpMock.expectOne('/api/brainstorm');
  req.flush({ text: 'result', latencyMs: 100 });
  const result = await promise;
  expect(result.text).toBe('result');
});
```

### Polling component spec

The polling component (`setInterval` / `clearInterval`) requires explicit verification:

```typescript
it('clears the interval when job completes', fakeAsync(() => {
  spyOn(window, 'clearInterval');
  component.startPolling('job-1');
  // Simulate done response
  tick(3000);
  expect(clearInterval).toHaveBeenCalled();
}));
```

Never leave a `setInterval` without a `clearInterval` test.

---

## E2E Testing (pytest-playwright + pytest-bdd)

### Real servers, not mocks

E2E tests exercise the full Angular + Flask stack because the regressions they catch — route renames, template changes, broken API contracts — are integration failures that a mocked layer cannot surface.

### Selector contract

`[data-test]` attributes are the **only** selector mechanism in E2E tests.
Class names, IDs, and tag structures change on redesign; `[data-test]` attributes do not.

Retrofit `[data-test]` attributes to components as E2E feature files require them — not all at once before a single test exists, and not ad hoc in step definitions.

### Page objects

One page object per Angular component. Page objects are the single place where selectors live:

```python
# e2e/pages/operation_bar.page.py
class OperationBarPage:
    def __init__(self, page):
        self.page = page

    def trigger_brainstorm(self):
        self.page.click("[data-test='brainstorm-btn']")

    def wait_for_result(self):
        self.page.wait_for_selector("[data-test='output-text']")
```

Step definitions call page object methods — never reference selectors directly.
When a selector changes, one page object method update is the only repair required.

### Shared server fixture

Session-scoped. Not function-scoped. Server startup is expensive:

```python
# e2e/conftest.py
@pytest.fixture(scope="session")
def live_app():
    # Start Flask on port 8095 and Angular on port 4201
    # Poll health endpoints before yielding
    yield
    # Teardown
```

All five feature files import this fixture by name.
No feature file knows which port either server uses.

### API-based setup

E2E scenarios seed project state via `POST /api/projects` before the browser step begins:

```python
@given("a project with a braindump exists")
def project_exists(live_app, api_client):
    api_client.post("/api/projects", json={"name": "test"})
    # upload braindump.md
```

The UI test starts at the assertion-relevant moment — never clicks through setup flows. If setup flows break, contract integration tests catch it first.

### Gherkin scope

Gherkin is reserved for multi-step user journeys that read as product narratives. Assertions that belong at the unit layer do not belong in Gherkin scenarios. A failing scenario names a broken workflow in product language, not a broken assertion in test language.

Five core workflows warrant Gherkin feature files:
1. `bootstrap-happy` — braindump input → spec files generated
2. `bootstrap-fail-fast` — empty name surfaces error before AI call
3. `brainstorm-to-pipeline` — brainstorm output → spec pipeline triggered
4. `epic-guide` — generate epic guide, poll to completion
5. `rewrite-operation` — rewrite action returns result in output panel

---

## What NOT to do

- Do not mock the database in backend tests that depend on ORM behavior — get burned when mocked tests pass but the real query fails.
- Do not assert on class selectors or element IDs in E2E — they are visual details, not behavioral contracts.
- Do not write parametrize-less test functions for each of the N action routes — one parametrized class covers all N.
- Do not set a hard coverage percentage threshold as a CI gate — it produces gamed line coverage.
- Do not run E2E tests against a mocked HTTP layer — the failures E2E is designed to catch live precisely in the integration path.
- Do not duplicate spy setup inline in component tests — always use the mock factory file.
- Do not write snapshot tests without `--snapshot-update` in the repository's `Makefile` or `README` — snapshots that can't be regenerated with one command are a maintenance burden.
