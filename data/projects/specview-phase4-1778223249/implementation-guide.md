# 🛠️ Implementation Guide: Specview Phase 4 — Quality & Reliability

> Generated: 2026-05-08
> Source docs: `epic.md`, `architecture.md`
> Baseline backend test count: **701**

---

## How to Use This Guide

**Tasks 1, 2, and 3 are fully parallel.**
**Task 4 opens only after Tasks 1 and 2 are green.**
**Task 5 opens only after Tasks 1, 3, and 4 are green.**

Each task has exact files, ordered steps, and an acceptance checklist.
Never hand-edit files under `web-ng/src/app/api/` — that directory is generator output.

---

## Task 1 — Dead-Route Cleanup & Client Regeneration

**What**: Remove four phantom routes from `openapi.yaml`, regenerate the Angular client, delete orphaned TS files.
**Why**: The contract matrix iterates over registered routes — `openapi.yaml` must be truthful first.
**Effort**: 0.5 days | **Parallel with**: Tasks 2, 3 | **Blocks**: Tasks 4, 5

### Files to Touch

| File | Action |
|------|--------|
| `openapi.yaml` (repo root) | Remove four `paths` entries |
| `web-ng/` | Re-run the OpenAPI generator |
| `web-ng/src/app/api/` | Delete any orphaned `*.ts` files after regen |
| `web-ng/src/app/` (consumers) | Fix any import errors from deleted files |

### Steps

**1.1 — Delete the four dead paths from `openapi.yaml`**

Remove the following `paths` keys and all content under them:
```
/text/rewrite
/text/generate
/text/lint-braindump
/text/review
```
Also remove any `components/schemas` entries referenced exclusively by those four paths.

**1.2 — Regenerate the Angular client**
```bash
cd web-ng && npm run generate-api
```
Confirm zero errors.

**1.3 — Delete any orphaned generated files**

If the generator does not clean them up automatically:
```bash
cd web-ng && npm run build 2>&1 | grep "error TS"
```
Delete any file the build flags as unused or missing. Do not stub them.

**1.4 — Verify build passes**
```bash
cd web-ng && npm run build
```

### Acceptance Checklist
- [ ] `openapi.yaml` has zero entries for the four deleted paths
- [ ] No generated TS files in `web-ng/src/app/api/` correspond to deleted routes
- [ ] `npm run build` exits 0

---

## Task 2 — Skill-Boundary Hardening

**What**: Four reliability rails — 120s timeout, structured error envelope, job-state TTL, frontend max-retries.
**Why**: Each rail closes a distinct failure mode; all four together make the boundary fail predictably.
**Effort**: 1 day | **Parallel with**: Tasks 1, 3

### Files to Touch

| File | Action |
|------|--------|
| `api/modules/ai/routes/actions.py` | Timeout + error envelope |
| `api/modules/ai/job_store.py` | TTL expiry on `SkillJob` |
| Angular polling component | Max-retries + user-visible error |

### Rail 1 — 120s Timeout Ceiling

In `actions.py`, wrap every `run_skill()` call:

```python
import concurrent.futures

SKILL_TIMEOUT_SECONDS = 120


def _run_with_timeout(skill_name: str, user_input: str, registry: dict):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_skill, skill_name, user_input, registry)
        try:
            return future.result(timeout=SKILL_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(f"skill timed out after {SKILL_TIMEOUT_SECONDS}s")
```

Replace direct `run_skill(...)` calls in every route handler with `_run_with_timeout(...)`.

### Rail 2 — Structured Error Envelope

Every failure in `actions.py` must return `{"error": "..."}` + 500.
The existing `except RuntimeError` already returns 502 — change status to 500 and add the missing cases:

```python
t0 = time.monotonic()
try:
    result = _run_with_timeout(skill_name, user_input, registry)
except RuntimeError as exc:
    return jsonify({"error": str(exc)}), 500

if "text" not in result:
    return jsonify({"error": "skill returned unexpected output shape"}), 500

latency_ms = int((time.monotonic() - t0) * 1000)
return jsonify({"text": result["text"], "latencyMs": latency_ms})
```

Always log before returning the error envelope:
```python
except RuntimeError as exc:
    logger.exception("skill %s failed: %s", skill_name, exc)
    return jsonify({"error": str(exc)}), 500
```

### Rail 3 — Job-State TTL

Add TTL to `api/modules/ai/job_store.py`. The `SkillJob` dataclass already has `started_at`. Add a TTL check to `get_job()`:

```python
JOB_TTL_SECONDS = 3600  # 1 hour after start

def get_job(job_id: str) -> SkillJob | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return None
        if time.monotonic() - job.started_at > JOB_TTL_SECONDS:
            del _JOBS[job_id]
            return None
        return job
```

Expiry is opportunistic on read — no background eviction thread needed.

### Rail 4 — Frontend Max-Retries

In the Angular polling component (wherever `setInterval` is used for job polling):

```typescript
private readonly POLL_MAX_RETRIES = 30;   // 30 × 2s = 60s ceiling
private readonly POLL_INTERVAL_MS = 2000;
private pollRetries = 0;
private pollIntervalId: ReturnType<typeof setInterval> | null = null;
pollingError = signal<string | null>(null);

startPolling(jobId: string): void {
  this.pollRetries = 0;
  this.pollingError.set(null);
  this.pollIntervalId = setInterval(async () => {
    this.pollRetries++;
    if (this.pollRetries > this.POLL_MAX_RETRIES) {
      this.stopPolling();
      this.pollingError.set('Generation is taking too long. Please try again.');
      return;
    }
    try {
      const status = await this.projectsService.pollJob(jobId);
      if (status.done) { this.stopPolling(); this.handleSuccess(status); }
      else if (status.error) { this.stopPolling(); this.pollingError.set(status.error); }
    } catch {
      this.stopPolling();
      this.pollingError.set('Could not reach the server.');
    }
  }, this.POLL_INTERVAL_MS);
}

stopPolling(): void {
  if (this.pollIntervalId !== null) {
    clearInterval(this.pollIntervalId);
    this.pollIntervalId = null;
  }
}

ngOnDestroy(): void { this.stopPolling(); }
```

Add to the component template (Angular 17 control flow):
```html
@if (pollingError()) {
  <div data-test="polling-error" class="error-state">{{ pollingError() }}</div>
}
```

### Acceptance Checklist
- [ ] Every action route enforces 120s ceiling; timeout returns `{"error": "..."}` + 500
- [ ] Missing `text` key in skill output returns envelope + 500, not a Python traceback
- [ ] `get_job()` returns `None` for jobs older than `JOB_TTL_SECONDS`
- [ ] Polling stops after `POLL_MAX_RETRIES`; `[data-test="polling-error"]` is rendered
- [ ] `clearInterval` is called in `stopPolling()` and `ngOnDestroy()`

---

## Task 3 — Product-Behavior Contract Document

**What**: Write `product-behavior.md`; update `CLAUDE.md` to link it.
**Why**: The five Gherkin feature files in Task 5 mirror this document 1:1 — without it, E2E has no explicit target.
**Effort**: 0.5 days | **Parallel with**: Tasks 1, 2

### Files to Touch

| File | Action |
|------|--------|
| `product-behavior.md` (repo root) | Create |
| `CLAUDE.md` (repo root) | Add reference link |

### Steps

**3.1 — Create `product-behavior.md`** with exactly five flows.
Each flow: trigger, steps, duration class, failure shape.

```markdown
# Product Behavior Contract
> Mirrored 1:1 by `e2e/features/`. Any flow change here must be reflected there.

## Flow 1 — Brainstorm
**Trigger**: User submits text to the brainstorm action.
**Steps**: POST /api/brainstorm → 200 + {text, latencyMs} → result rendered inline.
**Duration class**: Short (< 60s synchronous).
**Failure shape**: 500 + {"error": "..."} → error message shown in UI.

## Flow 2 — Brainstorm → Pipeline
**Trigger**: User starts spec pipeline from brainstorm output.
**Steps**: POST /api/bootstrap → {job_id} → poll /api/bootstrap/{job_id} → done:true → files listed in sidebar.
**Duration class**: Long (60–180s async).
**Failure shape**: Poll returns error field → [data-test="polling-error"] visible.

## Flow 3 — Epic-Guide Generation
**Trigger**: User clicks "Generate Guide" on a project.
**Steps**: POST /api/projects/{id}/generate-epic-guide → {job_id} → poll status → done:true → guide file appears.
**Duration class**: Medium (30–90s async).
**Failure shape**: Same as Flow 2.

## Flow 4 — Billing Gate (Free Tier)
**Trigger**: Free-tier user calls an AI action above their daily limit.
**Steps**: Backend checks usage → 429 + {error, limit, reset_at, upgrade_url} → upgrade prompt shown; no skill invoked.
**Duration class**: Immediate (< 1s).
**Failure shape**: 429 response; no job enqueued; no polling.

## Flow 5 — Pro Subscription Check
**Trigger**: Authenticated user calls an AI action.
**Steps**: Backend reads user.plan from DB → if "pro", skip usage check → action proceeds.
**Duration class**: Immediate (adds < 5ms to any AI action).
**Failure shape**: If plan lookup fails → action proceeds as free-tier (fail-safe).
```

**3.2 — Update `CLAUDE.md`** — add under the non-negotiable rules section:
```markdown
- **Product behavior is defined in `product-behavior.md`** — five core flows, expected
  steps, duration classes, and failure shapes; mirrored 1:1 by `e2e/features/`.
```

### Acceptance Checklist
- [ ] `product-behavior.md` exists at repo root with all five flows
- [ ] Each flow has trigger, steps, duration class, failure shape
- [ ] `CLAUDE.md` links to `product-behavior.md`

---

## Task 4 — Backend Test Pyramid (Unit + Contract Matrix)

**What**: Extend existing test files with timeout/envelope coverage; add TTL tests; add skill integration test; add parametrized contract matrix.
**Effort**: 2 days | **Requires**: Tasks 1 and 2 complete

### Files to Touch

| File | Action |
|------|--------|
| `api/modules/ai/routes/tests/test_actions.py` | Add timeout + malformed-output classes (file already exists) |
| `api/modules/ai/tests/test_job_store.py` | Add TTL test cases (file already exists) |
| `api/modules/ai/routes/tests/test_skill_integration.py` | New — SKILL.md + skill.json validation |
| `api/tests/integration/test_contract_matrix.py` | New — parametrized CORS / envelope / schema |

Note: `api/modules/runtime/chain/tests/` already has `test_adapter.py`, `test_context_loader.py`, `test_file_parser.py`, and `test_structural.py`. Do not duplicate. Add tests only if gaps remain after reading those files.

### 4.1 — Extend `test_actions.py` with Hardening Cases

Add two classes to the existing file:

```python
class TestActionTimeout:
    """Rail 1: 120s ceiling — timeout returns envelope + 500."""

    @pytest.mark.parametrize("route", [
        "/api/brainstorm", "/api/expand", "/api/compress", "/api/clarify",
        "/api/simplify", "/api/tldr", "/api/bullets",
    ])
    def test_timeout_returns_500_envelope(self, client, route, monkeypatch):
        def _timeout(*a, **kw):
            raise RuntimeError("skill timed out after 120s")
        monkeypatch.setattr("modules.ai.routes.actions._run_with_timeout", _timeout)
        resp = client.post(route, json={"text": "hello"}, headers=AUTH)
        assert resp.status_code == 500
        assert "error" in resp.get_json()


class TestActionMalformedOutput:
    """Rail 2: missing 'text' key returns envelope + 500."""

    def test_missing_text_key_returns_500_envelope(self, client, monkeypatch):
        monkeypatch.setattr(
            "modules.ai.routes.actions._run_with_timeout",
            lambda *a, **kw: {"wrong_key": "value"},
        )
        resp = client.post("/api/brainstorm", json={"text": "hello"}, headers=AUTH)
        assert resp.status_code == 500
        assert "error" in resp.get_json()
```

### 4.2 — Extend `test_job_store.py` with TTL Cases

```python
class TestJobTTL:
    def test_fresh_job_is_retrievable(self):
        job = store.create_job("brainstorm", "1.0.0")
        assert store.get_job(job.job_id) is not None

    def test_expired_job_returns_none(self, monkeypatch):
        job = store.create_job("brainstorm", "1.0.0")
        # Advance monotonic clock past TTL
        original = time.monotonic
        monkeypatch.setattr(
            time, "monotonic",
            lambda: original() + store.JOB_TTL_SECONDS + 1,
        )
        assert store.get_job(job.job_id) is None

    def test_expired_job_is_evicted_from_dict(self, monkeypatch):
        job = store.create_job("brainstorm", "1.0.0")
        original = time.monotonic
        monkeypatch.setattr(
            time, "monotonic",
            lambda: original() + store.JOB_TTL_SECONDS + 1,
        )
        store.get_job(job.job_id)  # triggers eviction
        assert job.job_id not in store._JOBS
```

### 4.3 — New: Skill Integration Test

Create `api/modules/ai/routes/tests/test_skill_integration.py`:

```python
"""Validates each plugin skill without making an AI call.

Checks: SKILL.md exists, skill.json is valid JSON with required keys,
and load_skill_registry() can read it without errors.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.ai.routes.generic_skill_service import load_skill_registry, _load_instructions

SKILLS_DIR = Path(__file__).parents[6] / "plugin" / "skills"
SKILL_DIRS = [p.parent for p in SKILLS_DIR.glob("*/SKILL.md")]


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=lambda p: p.name)
class TestSkillIntegration:
    def test_skill_md_exists(self, skill_dir):
        assert (skill_dir / "SKILL.md").is_file()
        assert (skill_dir / "SKILL.md").read_text().strip()

    def test_skill_json_has_required_keys(self, skill_dir):
        data = json.loads((skill_dir / "skill.json").read_text())
        assert "name" in data
        assert "description" in data
        assert "execution_model" in data

    def test_load_skill_registry_succeeds(self, skill_dir, monkeypatch):
        monkeypatch.setenv("PLUGIN_DIR", str(skill_dir.parents[1]))
        registry = load_skill_registry(skill_dir.name)
        assert registry["name"] == skill_dir.name

    def test_load_instructions_succeeds(self, skill_dir, monkeypatch):
        monkeypatch.setenv("PLUGIN_DIR", str(skill_dir.parents[1]))
        instructions = _load_instructions(skill_dir.name)
        assert len(instructions) > 0
```

### 4.4 — New: Contract Integration Matrix

Create `api/tests/integration/test_contract_matrix.py`:

```python
"""Parametrized contract matrix — CORS, error envelope, OpenAPI response shape.

Runs once per registered route. Adding a new route means adding it to the
app; the matrix picks it up automatically from app.url_map.
"""
from __future__ import annotations

import yaml
import jsonschema
import pytest


def _all_routes(app):
    return [
        r.rule for r in app.url_map.iter_rules()
        if not r.rule.startswith("/static") and "<" not in r.rule
    ]


@pytest.fixture(scope="module")
def app():
    from create_app import create_app as _ca
    return _ca({"TESTING": True})


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def routes(app):
    return _all_routes(app)


@pytest.fixture(scope="module")
def openapi_spec():
    with open("openapi.yaml") as f:
        return yaml.safe_load(f)


class TestCORSHeaders:
    def test_all_routes_have_cors_header_on_options(self, client, routes):
        missing = []
        for route in routes:
            resp = client.options(route)
            if not resp.headers.get("Access-Control-Allow-Origin"):
                missing.append(route)
        assert not missing, f"Routes missing CORS header: {missing}"


class TestErrorEnvelopeShape:
    """Every 4xx/5xx response must be JSON with an 'error' key."""

    _BAD_PAYLOADS = [
        ("/api/brainstorm", "POST", {}),
        ("/api/expand",     "POST", {}),
        ("/api/compress",   "POST", {}),
        ("/api/clarify",    "POST", {}),
        ("/api/simplify",   "POST", {}),
        ("/api/tldr",       "POST", {}),
        ("/api/bullets",    "POST", {}),
        ("/api/rewrite",    "POST", {"text": "x", "style": "invalid"}),
    ]

    @pytest.mark.parametrize("route,method,payload", _BAD_PAYLOADS)
    def test_error_response_is_envelope(self, client, route, method, payload):
        resp = getattr(client, method.lower())(
            route, json=payload, headers={"Authorization": ""}
        )
        # Skip routes that return 200 even on bad input
        if resp.status_code < 400:
            pytest.skip(f"{route} returned {resp.status_code}")
        body = resp.get_json()
        assert body is not None, "Response is not JSON"
        assert "error" in body, f"Missing 'error' key: {body}"


class TestOpenAPIResponseShape:
    """Happy-path 200 responses must match the openapi.yaml schema."""

    def test_registered_routes_subset_openapi(self, routes, openapi_spec):
        """Every route in openapi.yaml paths must be reachable in the app."""
        spec_paths = set(openapi_spec.get("paths", {}).keys())
        # Normalise Flask param syntax {id} vs openapi {id}
        app_paths = {r.replace("<", "{").replace(">", "}") for r in routes}
        unmatched = spec_paths - app_paths
        assert not unmatched, f"openapi.yaml declares routes not in app: {unmatched}"
```

### Acceptance Checklist
- [ ] `test_actions.py` extended with timeout and malformed-output classes
- [ ] `test_job_store.py` extended with TTL and eviction tests
- [ ] `test_skill_integration.py` parametrizes over all `plugin/skills/*/SKILL.md`
- [ ] `test_contract_matrix.py` covers CORS across all routes, envelope on all error paths, openapi path consistency
- [ ] `CHAIN_PROVIDER=mock` used in every test that calls through the adapter
- [ ] `pytest` runs green; test count meaningfully above 701 baseline

---

## Task 5 — Frontend Specs + Mock Factories + E2E Gherkin

**What**: Per-service mock factories, polling lifecycle spec, five Gherkin feature files, real-server E2E.
**Effort**: 2.5 days | **Requires**: Tasks 1, 3, 4 complete

### 5.1 — Service Mock Factories

Create alongside the real service files in `web-ng/src/app/services/`:

**`web-ng/src/app/services/ai.service.mock.ts`**
```typescript
import { AiService, TextOperationResponse } from './ai.service';

const MOCK_RESULT: TextOperationResponse = { text: 'mock result', latencyMs: 100 };

export function createAiServiceMock(): jasmine.SpyObj<AiService> {
  const mock = jasmine.createSpyObj<AiService>('AiService', [
    'brainstorm', 'expand', 'compress', 'clarify',
    'simplify', 'tldr', 'bullets', 'styleAs',
  ]);
  mock.brainstorm.and.returnValue(Promise.resolve(MOCK_RESULT));
  mock.expand.and.returnValue(Promise.resolve(MOCK_RESULT));
  return mock;
}
```

**`web-ng/src/app/services/projects.service.mock.ts`**
```typescript
import { ProjectsService } from './projects.service';

export function createProjectsServiceMock(): jasmine.SpyObj<ProjectsService> {
  return jasmine.createSpyObj<ProjectsService>('ProjectsService', [
    'getProjects', 'getProject', 'createProject', 'saveFile',
    'bootstrapProject', 'pollBootstrap',
    'generateEpicGuide', 'pollEpicGuide',
  ]);
}
```

Both files: one named export per file, under 50 lines.

### 5.2 — Polling Lifecycle Spec

Create `web-ng/src/app/services/polling.component.spec.ts` (or add to the existing component spec):

```typescript
describe('Polling lifecycle', () => {
  it('stops polling when job returns done:true', fakeAsync(() => {
    projectsService.pollBootstrap.and.returnValue(
      Promise.resolve({ done: true, files: [] })
    );
    component.startPolling('job-1');
    tick(2000);
    expect(component['pollIntervalId']).toBeNull();
    discardPeriodicTasks();
  }));

  it('stops and shows error after POLL_MAX_RETRIES', fakeAsync(() => {
    projectsService.pollBootstrap.and.returnValue(
      Promise.resolve({ done: false })
    );
    component.startPolling('job-2');
    tick(component['POLL_INTERVAL_MS'] * (component['POLL_MAX_RETRIES'] + 2));
    expect(component['pollIntervalId']).toBeNull();
    expect(component.pollingError()).toBeTruthy();
    discardPeriodicTasks();
  }));

  it('clears interval on ngOnDestroy', fakeAsync(() => {
    component.startPolling('job-3');
    component.ngOnDestroy();
    expect(component['pollIntervalId']).toBeNull();
    discardPeriodicTasks();
  }));

  it('renders [data-test="polling-error"] when pollingError is set', () => {
    component.pollingError.set('Something went wrong');
    fixture.detectChanges();
    const el = fixture.nativeElement.querySelector('[data-test="polling-error"]');
    expect(el).not.toBeNull();
    expect(el.textContent).toContain('Something went wrong');
  });
});
```

### 5.3 — E2E Session-Scoped Fixture

Create `e2e/conftest.py`:

```python
import os
import socket
import subprocess
import time
import pytest


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"Server did not start on {host}:{port} within {timeout}s")


@pytest.fixture(scope="session")
def flask_server():
    env = {**os.environ, "CHAIN_PROVIDER": "mock", "FLASK_APP": "create_app:create_app"}
    proc = subprocess.Popen(
        ["python", "-m", "flask", "run", "--port", "5001"],
        cwd="api", env=env,
    )
    _wait_for_port("127.0.0.1", 5001)
    yield "http://127.0.0.1:5001"
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def angular_server():
    proc = subprocess.Popen(
        ["npx", "ng", "serve", "--port", "4201", "--poll", "0"],
        cwd="web-ng",
    )
    _wait_for_port("127.0.0.1", 4201, timeout=60.0)
    yield "http://localhost:4201"
    proc.terminate()
    proc.wait()
```

### 5.4 — [data-test] Selector Inventory

Add these to templates if missing (add only as E2E feature files require them):

| Selector | Location |
|----------|----------|
| `data-test="braindump-input"` | braindump textarea |
| `data-test="brainstorm-button"` | brainstorm submit |
| `data-test="brainstorm-result"` | result display panel |
| `data-test="polling-spinner"` | loading indicator |
| `data-test="polling-error"` | error state (Task 2 Rail 4) |
| `data-test="pipeline-trigger"` | run pipeline button |
| `data-test="epic-guide-trigger"` | generate guide button |
| `data-test="billing-gate-message"` | usage limit message |

### 5.5 — Five Gherkin Feature Files

Mirror `product-behavior.md` exactly. Example for Flow 1:

`e2e/features/brainstorm.feature`:
```gherkin
Feature: Brainstorm — synchronous text operation

  Scenario: User submits text and receives brainstorm result
    Given the app is loaded
    When the user types "I want to build a habit tracker" into "[data-test='braindump-input']"
    And the user clicks "[data-test='brainstorm-button']"
    Then "[data-test='brainstorm-result']" contains text within 60 seconds

  Scenario: Skill failure shows error message
    Given the backend returns a 500 error for brainstorm
    When the user submits text to brainstorm
    Then "[data-test='polling-error']" is visible
```

Create equivalents for: `bootstrap-pipeline`, `epic-guide`, `billing-gate`, `pro-check`.
Step definitions in `e2e/steps/` call page object methods — no selectors in step files.

### 5.6 — CI Coverage Artifact

Add to CI config (no `--cov-fail-under`):
```yaml
- name: Run backend tests with coverage
  run: cd api && pytest --cov=. --cov-report=xml:coverage.xml

- name: Upload coverage artifact
  uses: actions/upload-artifact@v4
  with:
    name: backend-coverage
    path: api/coverage.xml
  if: always()
```

### Acceptance Checklist
- [ ] `ai.service.mock.ts` and `projects.service.mock.ts` in `web-ng/src/app/services/`; return `Promise.resolve(...)`, not `Observable`
- [ ] Polling lifecycle spec has four tests covering success, max-retries, destroy, and DOM rendering
- [ ] Five `.feature` files in `e2e/features/`, mirroring `product-behavior.md` flows 1:1
- [ ] All E2E selectors use `[data-test]` — zero class-name or tag selectors in step definitions or page objects
- [ ] Session-scoped Flask + Angular fixture (not per-test restart)
- [ ] Coverage artifact published to CI; no `--cov-fail-under` flag

---

## Master Checklist

| # | Criterion | Task |
|---|-----------|------|
| 1 | `openapi.yaml` clean; no dead generated TS files; `npm run build` passes | 1 |
| 2 | 120s ceiling + error envelope on all action routes | 2 |
| 3 | Job TTL + frontend max-retries with `[data-test="polling-error"]` | 2 |
| 4 | `test_actions.py` covers timeout + malformed output | 4 |
| 5 | Contract matrix: CORS, envelope, OpenAPI path consistency | 4 |
| 6 | Skill integration test: SKILL.md + skill.json + registry loader | 4 |
| 7 | Mock factories return Promises; polling spec has 4 non-trivial tests | 5 |
| 8 | `product-behavior.md` + `CLAUDE.md` reference | 3 |
| 9 | Five Gherkin features on real Flask + Angular servers | 5 |
| 10 | Coverage XML artifact published; no fail-fast gate | 5 |
| 11 | Backend test count > 701; full suite clean | 4+5 |

---

## Common Pitfalls

| Pitfall | How to Avoid |
|---------|--------------|
| Hand-editing `web-ng/src/app/api/` | Never — run the generator; delete what it stops producing |
| `session.commit()` in a route handler | Service layer only |
| Importing from `providers.*` in feature modules | Use `chain/adapter.py` exclusively |
| `get_registered_routes()` at module collection time | Use a `scope="module"` fixture, not a module-level call |
| Class-name or tag selectors in E2E step files | `[data-test]` exclusively |
| Per-test server restart in E2E | Session-scoped fixture only |
| `--cov-fail-under` in CI | Documented lesson: thresholds produce gamed coverage |
| Observable in mock factories | Services return `Promise` — mocks must match |
| `*ngIf` / `*ngFor` in new templates | Use `@if` / `@for` (Angular 17+ control flow) |

---

*Generated from `epic.md` + `architecture.md` — Specview Phase 4.*
