# Implementation Guide — Task 1: Test Infrastructure Baseline

## 1. Context

Task 1 is the mechanical prerequisite that every later task in this epic depends on directly. Without it, Tasks 2, 3, 4, and 5 each invent their own fixture style, payload construction approach, and filesystem-isolation strategy, and the suite fragments rather than composes. The work has four parts: reorganise existing flat test functions into pytest classes (the Python `@Nested` equivalent, enabling `pytest tests/test_ai_routes.py::TestRewrite -v` scoped runs without string-matching across unrelated functions); apply `@pytest.mark.parametrize` to the three repeated route-shape patterns (missing required field → 422, whitespace-only input → 400, provider error → 502) across all AI routes; extract a `tests/fixtures/payloads.py` module whose named factory functions become the single authoritative definition of each route's expected payload shape; and add `SPEC_DOC_DIR=tmp_path` as a conftest `autouse` default so every filesystem-touching test is isolated without opting in. The port budget is ~60 lines of new infrastructure (conftest additions + payload factory module); the remainder of the work is structural refactoring of existing test functions with no assertion-body changes.

**Trade-offs considered:**
- **pytest-factoryboy or faker for payload generation** — rejected; the payload shapes are small and stable; a plain factory-function module has zero runtime magic, is grep-able, and adds no dependency for one module whose content is three functions
- **One flat file with parametrize-only coverage (no class grouping)** — rejected; class grouping by resource and HTTP verb makes `pytest tests/test_project_routes.py::TestCreateProject -v` a focused slice; flat parametrize-only files obscure intent when a single scope has 15+ combinations
- **pytest classes with `autouse` conftest isolation** — preferred; the `autouse` fixture makes isolation opt-out rather than opt-in, matching ELA's "default isolation, not opt-in" principle; it mirrors the session/function scope discipline already demonstrated in Bubls' `server/tests/`

---

## 2. Pre-flight

Run from `{WORKSPACE}` (the spec-doc project root) **before editing any file**:

```bash
# Confirm git state — flag any unrelated M/?? entries before starting
git status
git diff HEAD -- backend/conftest.py backend/tests/ backend/pyproject.toml

# Inspect existing test layout — confirm file names match guide's Step 4 and 5 targets
ls backend/tests/
ls backend/tests/fixtures/ 2>/dev/null || echo "(fixtures/ does not exist yet — expected)"

# Detect flat test functions (not in a class) — records what will be refactored
grep -rn "^def test_" backend/tests/ | head -60

# Confirm how SPEC_DOC_DIR is consumed (startup config vs per-request os.environ read)
# If it appears in create_app() config dict, see Deviations Allowed §spec_doc_dir
grep -rn "SPEC_DOC_DIR" backend/

# Confirm real AI route paths for the parametrize matrices in Step 5
cd backend && python -c "
from app import create_app
app = create_app({'TESTING': True})
for r in sorted(app.url_map.iter_rules(), key=str):
    print(r.methods, str(r))
"

# Record baseline test count — fill in [N] before editing
cd backend && python -m pytest --tb=no -q 2>&1 | tail -5
```

**If the working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: `[N]` / `[N]` passing — executor fills this in before the first edit.

**Route inventory**: the parametrize matrices in Step 5 list `/api/ai/text/rewrite`, `/api/ai/text/generate`, and `/api/ai/text/iterate`. If the `url_map` output shows different paths, update `AI_ROUTES` and each matrix to match; note the deviation.

---

## 3. Files

### To Create (new)
- `backend/tests/fixtures/__init__.py` — empty package marker; required for `from tests.fixtures.payloads import …` to resolve
- `backend/tests/fixtures/payloads.py` — three factory functions (`make_rewrite_request`, `make_generate_request`, `make_iterate_request`); ~35 lines
- `backend/tests/test_conftest_isolation.py` — three smoke tests verifying the `spec_doc_dir` autouse fixture provides per-test isolation

### To Modify (cite CODEBASE CONTEXT)
- `backend/conftest.py` — add `spec_doc_dir` autouse fixture; verify session-scoped `app` + function-scoped `client` fixtures already exist (pattern from Bubls `server/app.py` factory); do not duplicate existing fixtures
- `backend/tests/test_ai_routes.py` — wrap flat functions in named classes; add three parametrized matrix classes for the missing-field, whitespace, and provider-error patterns
- `backend/tests/test_project_routes.py` — wrap flat functions in `TestGetProjects`, `TestCreateProject`, `TestDeleteProject` classes
- `backend/pyproject.toml` — add `[tool.pytest.ini_options] markers` block with five named markers

### To Leave Alone
- `backend/modules/` — all feature module source; this task touches only test infrastructure
- `backend/app.py` — Flask factory; no route registration or app-config changes in this task
- `server.js` — existing Express API; entirely separate from Flask backend test infrastructure
- Any file not listed under To Create or To Modify

---

## 4. Implementation Steps

### Step 1: Create the payload factory module

**Action**: Create `backend/tests/fixtures/__init__.py` (empty) and `backend/tests/fixtures/payloads.py` with one factory function per AI route. Each factory accepts required fields as keyword-only arguments with sane defaults and returns a fully-formed `dict`. This is the single authoritative definition of each route's expected payload; when a required field name changes, one function update propagates everywhere.

**File**: `backend/tests/fixtures/payloads.py` (new)

**Pattern** (shape derived from humanize-me `parse_text_rewrite` dict conventions; generalised for spec-doc AI routes):

```python
"""
Payload factory functions — single source of truth for request shapes.

Each factory is the authoritative definition of one route's valid request.
When a required field name changes, update the factory; every test that
imports it updates automatically.
"""
from __future__ import annotations


def make_rewrite_request(
    *,
    text: str = "The utilisation of AI tools is increasingly prevalent.",
    instruction: str = "Make it sound more casual",
    operation: str = "rewrite",
) -> dict:
    return {"text": text, "instruction": instruction, "operation": operation}


def make_generate_request(
    *,
    prompt: str = "Write an analysis section for a note-taking SaaS product.",
    tone: str | None = "balanced",
) -> dict:
    payload: dict = {"prompt": prompt}
    if tone is not None:
        payload["tone"] = tone
    return payload


def make_iterate_request(
    *,
    text: str = "# Analysis\n\nThe market opportunity is large.",
    spec_content: str = "# Epic\n\nShip in one week.",
    instruction: str = "Add a competitive landscape section",
) -> dict:
    return {"text": text, "spec_content": spec_content, "instruction": instruction}
```

**Verify**:
```bash
cd backend && python -c "
from tests.fixtures.payloads import (
    make_rewrite_request, make_generate_request, make_iterate_request
)
r = make_rewrite_request()
assert 'text' in r and 'instruction' in r and 'operation' in r, r
g = make_generate_request()
assert 'prompt' in g and 'tone' in g, g
i = make_iterate_request()
assert 'text' in i and 'spec_content' in i and 'instruction' in i, i
print('payloads OK')
"
```
Expect: prints `payloads OK`, exits 0.

---

### Step 2: Add `spec_doc_dir` isolation fixture to `conftest.py`

**Action**: Open `backend/conftest.py`. Verify the session-scoped `app` fixture and function-scoped `client` fixture already exist; do not duplicate them. Add a new `spec_doc_dir` fixture marked `autouse=True` that calls `monkeypatch.setenv("SPEC_DOC_DIR", str(tmp_path))`. Every test — without explicit opt-in — runs against its own isolated directory.

**File**: `backend/conftest.py` (existing)

**Pattern** (autouse isolation principle from architecture doc; `monkeypatch.setenv` is standard pytest-flask):

```python
import pytest

# ── Existing fixtures — verify present, do NOT duplicate ─────────────────────
# @pytest.fixture(scope="session")
# def app():
#     from app import create_app
#     yield create_app({"TESTING": True, "CHAIN_PROVIDER": "mock"})
#
# @pytest.fixture
# def client(app):
#     return app.test_client()


# ── New: default filesystem isolation ─────────────────────────────────────────
@pytest.fixture(autouse=True)
def spec_doc_dir(tmp_path, monkeypatch):
    """Set SPEC_DOC_DIR to a fresh tmp_path for every test.

    autouse=True means every test in the suite gets isolation without
    explicitly requesting this fixture. Tests that write files use
    spec_doc_dir directly — it is the same directory the env var points to.

    If the app reads SPEC_DOC_DIR from its Flask config dict (set at
    create_app() time) rather than from os.environ per-request, see
    Deviations Allowed §spec_doc_dir for the function-scoped app workaround.
    """
    monkeypatch.setenv("SPEC_DOC_DIR", str(tmp_path))
    return tmp_path
```

**Verify**:
```bash
cd backend && python -m pytest --collect-only -q 2>&1 | tail -5
```
Expect: collection succeeds (no import errors; collected count matches baseline N).

---

### Step 3: Register pytest markers in `pyproject.toml`

**Action**: Add a `[tool.pytest.ini_options]` markers block to `backend/pyproject.toml`. If the block already exists, merge rather than replace. Five markers: `unit`, `integration`, `e2e`, `snapshot`, `real_claude`. The `real_claude` marker is infrastructure-only — no test body carries it in this task.

**File**: `backend/pyproject.toml` (existing)

**Pattern**:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: fast, in-process tests; no I/O beyond in-memory SQLite or mock provider",
    "integration: crosses a real HTTP boundary or a real DB engine",
    "e2e: browser-driven; requires the dev server to be running",
    "snapshot: syrupy golden-file assertions; regenerate with --snapshot-update",
    "real_claude: exercises CHAIN_PROVIDER=claude; requires ANTHROPIC_API_KEY set",
]
```

**Verify**:
```bash
cd backend && python -m pytest --markers 2>&1 \
  | grep -E "@pytest.mark.(unit|integration|e2e|snapshot|real_claude)"
```
Expect: exactly five matching lines, one per marker, no "unknown mark" warnings.

---

### Step 4: Refactor `test_project_routes.py` into pytest classes

**Action**: Wrap existing flat test functions in classes grouped by HTTP verb and resource (`TestGetProjects`, `TestCreateProject`, `TestDeleteProject`). Do not change assertion bodies — add class wrappers, apply `@pytest.mark.unit` to each class, and rename methods to the `condition_expectedOutcome` convention where they are not already there.

**File**: `backend/tests/test_project_routes.py` (existing)

**Pattern** (naming convention from Bubls `server/tests/test_routes.py`; class grouping from architecture doc):

```python
import pytest


@pytest.mark.unit
class TestGetProjects:
    """GET /api/projects"""

    def test_noProjects_returnsEmptyList(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert data == []

    def test_existingProject_returnsProjectInList(self, client, spec_doc_dir):
        # spec_doc_dir == tmp_path; SPEC_DOC_DIR env var already points here
        (spec_doc_dir / "my-project").mkdir()
        (spec_doc_dir / "my-project" / "epic.md").write_text("# Epic")
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        names = [p["name"] for p in resp.get_json()]
        assert "my-project" in names, f"expected 'my-project' in {names}"


@pytest.mark.unit
class TestCreateProject:
    """POST /api/projects"""

    def test_validPayload_returns201(self, client):
        resp = client.post("/api/projects", json={"name": "alpha", "content": "# Brain dump"})
        assert resp.status_code == 201

    def test_missingName_returns422(self, client):
        resp = client.post("/api/projects", json={"content": "# Brain dump"})
        assert resp.status_code == 422
        assert "error" in resp.get_json()

    def test_missingContent_returns422(self, client):
        resp = client.post("/api/projects", json={"name": "alpha"})
        assert resp.status_code == 422
        assert "error" in resp.get_json()


@pytest.mark.unit
class TestDeleteProject:
    """DELETE /api/projects/<name>"""

    def test_existingProject_returns204(self, client, spec_doc_dir):
        (spec_doc_dir / "to-delete").mkdir()
        resp = client.delete("/api/projects/to-delete")
        assert resp.status_code == 204

    def test_unknownProject_returns404(self, client):
        resp = client.delete("/api/projects/does-not-exist")
        assert resp.status_code == 404
        assert "error" in resp.get_json()
```

**Verify**:
```bash
cd backend && python -m pytest tests/test_project_routes.py -v --tb=short
```
Expect: all tests green; count equals the pre-refactor count for this file (zero regressions from wrapping).

---

### Step 5: Refactor `test_ai_routes.py` — classes + parametrize matrices

**Action**: Wrap existing happy-path AI route tests in named classes. Add three parametrized matrix classes covering the repeated patterns across all AI routes. Place the route registry at module level (`AI_ROUTES`) so adding a new route is one list entry, not a new test function. Monkeypatch both `chain_adapter.generate` and `chain_adapter.stream` for the provider-error matrix to cover routes that use either code path.

**File**: `backend/tests/test_ai_routes.py` (existing)

**Pattern** (adapter monkeypatch idiom from Bubls `server/tests/test_text_routes.py`; parametrize-over-routes from architecture doc):

```python
import pytest
from tests.fixtures.payloads import (
    make_rewrite_request,
    make_generate_request,
    make_iterate_request,
)

# ── Route registry — update when new AI routes are added ─────────────────────
# Executor: verify against url_map output from pre-flight; update to match.
AI_ROUTES = [
    ("/api/ai/text/rewrite",  make_rewrite_request()),
    ("/api/ai/text/generate", make_generate_request()),
    ("/api/ai/text/iterate",  make_iterate_request()),
]


# ── Matrix 1: Missing required field → 422 ───────────────────────────────────
@pytest.mark.unit
@pytest.mark.parametrize("route,payload", [
    ("/api/ai/text/rewrite",  {"instruction": "Be casual"}),            # text missing
    ("/api/ai/text/rewrite",  {"text": "Hello world"}),                 # instruction missing
    ("/api/ai/text/generate", {}),                                       # prompt missing
    ("/api/ai/text/iterate",  {"text": "# Doc", "instruction": "X"}),   # spec_content missing
])
class TestAiRoutesMissingField:
    def test_missingRequiredField_returns422(self, client, route, payload):
        resp = client.post(route, json=payload)
        assert resp.status_code == 422, (
            f"{route}: expected 422 for payload {payload!r}; got {resp.status_code}"
        )
        body = resp.get_json()
        assert "error" in body, f"{route}: expected 'error' key in body; got {body!r}"


# ── Matrix 2: Whitespace-only input → 400 ────────────────────────────────────
@pytest.mark.unit
@pytest.mark.parametrize("route,payload", [
    ("/api/ai/text/rewrite",  make_rewrite_request(text="   \t")),
    ("/api/ai/text/generate", make_generate_request(prompt="\n\n")),
    ("/api/ai/text/iterate",  make_iterate_request(text="   ")),
])
class TestAiRoutesWhitespaceInput:
    def test_whitespaceOnlyInput_returns400(self, client, route, payload):
        resp = client.post(route, json=payload)
        assert resp.status_code == 400, (
            f"{route}: expected 400 for whitespace-only input; got {resp.status_code}"
        )
        body = resp.get_json()
        assert "error" in body, f"{route}: expected 'error' key in body; got {body!r}"


# ── Matrix 3: Provider error → 502 ───────────────────────────────────────────
@pytest.mark.unit
@pytest.mark.parametrize("route,payload", AI_ROUTES)
class TestAiRoutesProviderError:
    def test_providerError_returns502(self, client, route, payload, monkeypatch):
        import modules.chain.adapter as chain_adapter

        def _raise_provider_error(*args, **kwargs):
            # Raises the error the app's errorhandler maps to 502.
            # Verify the correct path with: grep -rn "class ServiceError" backend/
            # If the class lives elsewhere, update this import and note deviation.
            from core.errors import ServiceError
            raise ServiceError("stub: upstream unavailable", 502)

        monkeypatch.setattr(chain_adapter, "generate", _raise_provider_error)
        monkeypatch.setattr(chain_adapter, "stream",   _raise_provider_error)

        resp = client.post(route, json=payload)
        assert resp.status_code == 502, (
            f"{route}: expected 502 on provider error; got {resp.status_code}"
        )
        body = resp.get_json()
        assert "error" in body, f"{route}: expected 'error' key in body; got {body!r}"


# ── Happy-path classes (existing tests, wrapped) ──────────────────────────────
@pytest.mark.unit
class TestRewrite:
    """POST /api/ai/text/rewrite"""

    def test_validPayload_returns200WithText(self, client):
        resp = client.post("/api/ai/text/rewrite", json=make_rewrite_request())
        assert resp.status_code == 200
        body = resp.get_json()
        assert "text" in body, f"expected 'text' key; got {body!r}"
        assert len(body["text"]) > 0


@pytest.mark.unit
class TestGenerate:
    """POST /api/ai/text/generate"""

    def test_validPayload_returns200WithText(self, client):
        resp = client.post("/api/ai/text/generate", json=make_generate_request())
        assert resp.status_code == 200
        body = resp.get_json()
        assert "text" in body, f"expected 'text' key; got {body!r}"
        assert len(body["text"]) > 0


@pytest.mark.unit
class TestIterate:
    """POST /api/ai/text/iterate"""

    def test_validPayload_returns200WithText(self, client):
        resp = client.post("/api/ai/text/iterate", json=make_iterate_request())
        assert resp.status_code == 200
        body = resp.get_json()
        assert "text" in body, f"expected 'text' key; got {body!r}"
        assert len(body["text"]) > 0
```

**Verify**:
```bash
cd backend && python -m pytest tests/test_ai_routes.py -v --tb=short
```
Expect: all tests green. Count for this file increases by 10 (4 missing-field + 3 whitespace + 3 provider-error matrix cases) above the pre-refactor count.

---

### Step 6: Add conftest isolation smoke tests

**Action**: Create `backend/tests/test_conftest_isolation.py` with three tests that verify the `spec_doc_dir` autouse fixture provides per-test isolation. The ordering of the second and third tests is significant — pytest runs them in definition order by default.

**File**: `backend/tests/test_conftest_isolation.py` (new)

**Pattern**:

```python
"""
Smoke tests for the spec_doc_dir autouse fixture.

Verifies:
  1. SPEC_DOC_DIR is set in os.environ to the tmp_path value.
  2. Each test receives a fresh, empty directory.
  3. Files written in one test are absent in the next — no cross-test leakage.

The third test must run after the second; definition order guarantees this.
"""
import os
import pytest


@pytest.mark.unit
def test_specDocDir_setsEnvVarToExistingPath(spec_doc_dir):
    env_val = os.environ.get("SPEC_DOC_DIR")
    assert env_val is not None, "SPEC_DOC_DIR must be set by the autouse fixture"
    assert env_val == str(spec_doc_dir), (
        f"SPEC_DOC_DIR={env_val!r} does not match spec_doc_dir={spec_doc_dir!r}"
    )
    assert spec_doc_dir.exists(), "spec_doc_dir must be an existing directory"


@pytest.mark.unit
def test_specDocDir_isWritable_firstTest(spec_doc_dir):
    """Write a sentinel; must NOT appear in the next test's directory."""
    sentinel = spec_doc_dir / "sentinel.txt"
    sentinel.write_text("isolation-check")
    assert sentinel.exists()


@pytest.mark.unit
def test_specDocDir_doesNotLeakFromPreviousTest_secondTest(spec_doc_dir):
    """Sentinel written by firstTest must be absent — different tmp_path per test."""
    assert not (spec_doc_dir / "sentinel.txt").exists(), (
        "SPEC_DOC_DIR leaked between tests. "
        "Confirm spec_doc_dir fixture is function-scoped (default for tmp_path). "
        "If the app fixture is overriding SPEC_DOC_DIR at session scope, see Deviations Allowed."
    )
```

**Verify**:
```bash
cd backend && python -m pytest tests/test_conftest_isolation.py -v
```
Expect: three tests pass in declaration order.

---

## 5. Tests

All test bodies for this task appear in full in Steps 4, 5, and 6 above. There are no stubs. Each parametrized assertion carries an f-string failure message that identifies the failing route and payload without requiring the developer to inspect test source. The three isolation smoke tests in `test_conftest_isolation.py` are the additional infrastructure-specific assertions and carry their own diagnostic message in the final assertion.

---

## 6. Commit Plan

**Executor instruction**: commit after each step completes. Do **not** batch commits at the end. Each boundary below maps to one step number.

1. `feat(tests): add payload factory module` — after Step 1 — files: `backend/tests/fixtures/__init__.py`, `backend/tests/fixtures/payloads.py`
2. `feat(tests): add spec_doc_dir autouse isolation fixture` — after Step 2 — files: `backend/conftest.py`
3. `chore(tests): register five pytest markers in pyproject.toml` — after Step 3 — files: `backend/pyproject.toml`
4. `refactor(tests): group project route tests into pytest classes` — after Step 4 — files: `backend/tests/test_project_routes.py`
5. `refactor(tests): group AI route tests into classes; add parametrize matrices` — after Step 5 — files: `backend/tests/test_ai_routes.py`
6. `test(tests): add conftest isolation smoke tests` — after Step 6 — files: `backend/tests/test_conftest_isolation.py`

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation. Example:

```
Deviations: SPEC_DOC_DIR env var is named PROJECT_DIR in the actual codebase — substituted throughout
Deviations: /api/ai/text/iterate does not exist; removed from AI_ROUTES and matrices
```

---

## 7. Verification

```bash
cd backend && python -m pytest --tb=short -q
```

**Expected delta**: `[N]` → `[N + 13]` passing minimum, where 13 = 4 (missing-field matrix) + 3 (whitespace matrix) + 3 (provider-error matrix) + 3 (isolation smoke tests). The pre-existing test count must not drop — the refactor replaces flat functions 1-to-1 with class methods.

Marker query verification (must produce zero "unknown mark" warnings):

```bash
cd backend && python -m pytest -m unit --collect-only -q
cd backend && python -m pytest -m integration --collect-only -q
cd backend && python -m pytest -m e2e --collect-only -q
```

All three commands exit 0.

---

## 8. Rollback

- **Per-step**: each step maps to one commit. `git revert <sha>` reverts it cleanly. Run `python -m pytest --tb=no -q` after each revert to confirm the test count returns to the pre-step baseline.
- **Per-branch**: `git reset --hard <pre-task-sha>` if verification fails catastrophically; confirm the test count returns to baseline `[N]`. If working on a feature branch, `git checkout main` and delete the branch.

---

## 9. Deviations Allowed

- **`backend/` is not the Flask backend directory** → run `find . -name "conftest.py" | grep -v node_modules | head -10` to locate the actual root; substitute throughout every step and note deviation in each affected commit
- **`SPEC_DOC_DIR` env var name differs** → `grep -rn "os.environ\|os.getenv\|SPEC_DOC_DIR" backend/` to find the actual name; substitute throughout; note deviation in commit 2
- **App reads `SPEC_DOC_DIR` from Flask config dict at `create_app()` time (not from `os.environ` per-request)** → the `autouse` `monkeypatch.setenv` approach will not reach the already-initialised config; fix: change `conftest.py` to use a function-scoped `app` fixture that passes `{"SPEC_DOC_DIR": str(tmp_path)}` to `create_app()`, accepting the per-test app-construction cost; note deviation in commit 2
- **Route paths differ from `AI_ROUTES` list** → update `AI_ROUTES` and each `@pytest.mark.parametrize` list to match `url_map` output from pre-flight; note deviation in commit 5
- **`core.errors.ServiceError` import path is wrong** → `grep -rn "class ServiceError" backend/` to find the correct module; substitute in Step 5's provider-error matrix; note deviation in commit 5
- **Existing tests are already in classes** → skip the wrapping step for whichever files already comply; confirm `@pytest.mark.unit` is present; note which files were already compliant in the relevant commit body
- **A route returns a different status code than specified** (e.g., 400 instead of 422 for missing fields) → match the assertion to the actual status code; note deviation in commit 4 or 5 as applicable; flag it as a gap for Task 4's error-envelope contract tests
- **Step N produces a simplification that benefits Step N+1** → take it; log it in the commit body

---

## 10. Out of Scope

This task covers only the mechanical test infrastructure: class grouping, parametrize matrices, payload factories, conftest isolation, and marker registration. No application code changes, no new API routes, no new test dependencies beyond what pytest already provides, and no test layers above the unit level.

Explicitly deferred — the executor must STOP and flag rather than absorb any of these:

- **syrupy golden-file assertions** (Task 3) — the `snapshot` marker is registered but no test body carries it; `syrupy` is not installed here
- **`pytest-httpserver` Claude SDK stub** (Task 4) — the `real_claude` marker is registered but no test body carries it; `pytest-httpserver` is not installed here
- **Frontend service specs and mock factories** (Task 2) — Angular/Karma infrastructure is entirely out of scope for this backend-only task
- **E2E foundation** (Task 5) — `pytest-playwright`, `pytest-bdd`, page objects, and Gherkin feature files are deferred; no `[data-test]` selector retrofit in this task
- **CORS contract matrix** (Task 4) — the parametrize pattern from Step 5 will be reused there, but CORS-specific assertions belong in the integration task
- **Coverage thresholds or `pytest-cov` configuration** — coverage artefacts are a CI concern not addressed here; no `--cov` flag added to any command in this task
- **Additional factory functions beyond `make_rewrite_request`, `make_generate_request`, `make_iterate_request`** — `make_context_request`, `make_project_bootstrap_request`, or any other factory belongs in the task that first has a consumer for it

**Rule for the executor**: if a change appears helpful but is named above, STOP, note it as a deviation in the commit body, and do not expand this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Three-layer pyramid design, component design, technology stack rationale
- [Epic](./epic.md) — Task scope, success criteria, port budget
- [Timeline](./timeline.md) — Update Task 1 status to ✅ Done after verification passes