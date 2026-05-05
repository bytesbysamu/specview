# Task 5: Retire Express — Implementation Guide

## 1. Context

Task 5 is the final phase of the Express retirement migration. Tasks 1–4 migrated the four remaining Express-only AI endpoints (`iterate`, `lint-braindump`, `review`, `generate-spec`) to Flask and added each path to `proxy.conf.json` atomically with its route. Task 5 does the one thing that was deliberately deferred until all four were confirmed working: remove the Express fallback entry (`"/api" → 3100`) from `proxy.conf.json` and strip the `api` start script from `package.json`. Once the fallback is gone, any unrouted `/api` traffic gets a clean error rather than silently hitting a retired process. The smoke test pass confirms Flask serves all four migrated endpoints before the fallback is cut.

**Trade-offs considered:**

- **Leave Express as an optional fallback indefinitely** — rejected because it doubles the runtime maintenance surface and masks missing route registrations (a path not migrated would silently succeed rather than fail visibly)
- **Delete `server.js` and all Express test files in this task** — rejected; the Epic scopes this to "Config changes only — proxy diff, package.json diff"; `server.js` deletion and its test cleanup are a follow-up task with their own blast radius
- **Remove the fallback at the end of Task 4** — the architecture explicitly defers this to Task 5 to provide a clean rollback boundary; Tasks 1–4 each carry their own revert path, and the fallback removal belongs in its own commit so it can be independently reverted if a post-migration issue surfaces

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status
git diff HEAD -- proxy.conf.json package.json
```

**Verify Tasks 1–4 are complete before proceeding.** The proxy must already contain all four migrated paths pointing to 3101:

```bash
python3 -c "
import json
required = [
    '/api/ai/text/iterate',
    '/api/ai/text/lint-braindump',
    '/api/ai/text/review',
    '/api/ai/text/generate-spec',
]
proxy = json.load(open('proxy.conf.json'))
missing = [p for p in required if p not in proxy]
print('MISSING (Tasks 1-4 incomplete):', missing) if missing else print('OK — all four entries present')
"
```

If any path is missing: **STOP.** The missing task must be completed and committed first. Do not proceed.

```bash
cd flask && python -m pytest -q 2>/dev/null | tail -3
```

**Baseline recorded**: _/_ passing (record actual count before editing).

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

---

## 3. Files

### To Create (new)
- `flask/tests/test_retire_express.py` — smoke tests verifying proxy config correctness and Flask route reachability for all four migrated endpoints

### To Modify (cite CODEBASE CONTEXT)
- `proxy.conf.json` — remove the `"/api"` fallback entry (currently line 38–43); all remaining entries target `http://localhost:3101`
- `package.json` — remove `"api": "node server.js"` script; update `"dev"` from `"npm run api & npm run start"` to `"npm run start"`

### To Leave Alone
- `server.js` — Express server source; retirement of the process is complete once scripts are removed from package.json; file deletion is explicitly out of scope for this task (see §10)
- `server.test.js` — Express unit tests; deferred with `server.js`
- `server.integration.test.js` — same
- `flask/modules/ai/routes.py` — no route changes in this task; all four handlers were added in Tasks 1–4
- `flask/openapi.yaml` — no contract changes; already updated in Tasks 1–4
- `flask/dtos/models.py` — generated artifact; not touched
- `flask/tests/test_ai_rewrite.py` — existing endpoint tests; not touched

---

## 4. Implementation Steps

### Step 1: Remove Express fallback from proxy.conf.json

**Action**: Delete the `"/api"` catch-all entry from `proxy.conf.json`. The remaining entries (all targeting `http://localhost:3101`) cover every registered route. After this change, Angular dev-server will not attempt to proxy unrecognised `/api` traffic to port 3100.

**File**: `proxy.conf.json`

**Pattern** — remove this block (currently lines 38–43; the exact line numbers may differ after Tasks 1–4 added their entries):
```json
  "/api": {
    "target": "http://localhost:3100",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "warn"
  }
```

The resulting file must contain no entry whose key is exactly `"/api"`. All remaining keys begin with `/api/` (sub-paths) and target port `3101`.

**Verify**:
```bash
python3 -c "
import json; p = json.load(open('proxy.conf.json'))
assert '/api' not in p, 'fallback entry still present'
bad = [k for k, v in p.items() if '3100' in v.get('target','')]
assert not bad, f'entries still targeting 3100: {bad}'
print('OK')
"
```
Expect: `OK`

---

### Step 2: Remove Express scripts from package.json

**Action**: Remove the `"api"` script entirely. Update `"dev"` to start only Angular; Flask is started separately via `cd flask && make dev`.

**File**: `package.json`

**Pattern** — target state for the `"scripts"` block:
```json
"scripts": {
  "ng": "ng",
  "start": "ng serve --port 4201",
  "dev": "npm run start",
  "build": "ng build",
  "watch": "ng build --watch --configuration development",
  "test": "ng test",
  "test:server": "node --test server.test.js",
  "test:deviations": "node --test scripts/deviation-report.test.mjs",
  "test:regen-task": "node --test scripts/regen-task.test.mjs",
  "test:integration": "node --test server.integration.test.js",
  "test:integration:approve": "APPROVE=1 node --test server.integration.test.js",
  "test:mock": "AI_PROVIDER=mock node server.js",
  "test:all": "node --test server.test.js && node --test scripts/deviation-report.test.mjs && node --test scripts/regen-task.test.mjs && node --test server.integration.test.js",
  "deviation-report": "node scripts/deviation-report.mjs"
}
```

Two changes from the current file: `"api"` key deleted; `"dev"` value changed.

**Verify**:
```bash
python3 -c "
import json; s = json.load(open('package.json'))['scripts']
assert 'api' not in s, 'api script still present'
assert 'server.js' not in s.get('dev',''), 'dev still references server.js'
assert 'npm run start' in s.get('dev','') or 'ng serve' in s.get('dev',''), 'dev must start Angular'
print('OK')
"
```
Expect: `OK`

---

### Step 3: Add smoke tests

**Action**: Create `flask/tests/test_retire_express.py` with structural checks (proxy.conf.json, package.json) and Flask route reachability tests for all four migrated endpoints.

**File**: `flask/tests/test_retire_express.py` (new)

**Pattern**:
```python
# Structural + route-reachability smoke tests for Express retirement.
# Run from flask/: python -m pytest tests/test_retire_express.py -v
```

See §5 for the complete test bodies.

**Verify**:
```bash
cd flask && python -m pytest tests/test_retire_express.py -v
```
Expect: all tests in the new file pass.

---

## 5. Tests

```python
"""Smoke tests confirming Express retirement is complete.

Structural tests: proxy.conf.json and package.json are in the correct
post-retirement state.
Route tests: Flask serves all four migrated endpoints (non-404 means Flask
handles the request; Tasks 1–4 tests own the per-endpoint contract tests).

Run from flask/: python -m pytest tests/test_retire_express.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import os

FLASK_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = Path(os.environ.get("SPEC_DOC_DIR", str(FLASK_ROOT.parent / "spec-doc")))

sys.path.insert(0, str(FLASK_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(monkeypatch):
    """Flask test client with CHAIN_PROVIDER=mock."""
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Structural — proxy.conf.json
# ---------------------------------------------------------------------------

def proxyConf_hasNoExpressFallbackEntry():
    """The bare /api catch-all entry (targeting :3100) must be absent."""
    proxy = json.loads((REPO_ROOT / "proxy.conf.json").read_text())
    assert "/api" not in proxy, (
        "Express fallback '/api' entry must be removed from proxy.conf.json. "
        "All /api traffic now routes explicitly to Flask :3101."
    )


def proxyConf_noEntryTargets3100():
    """No remaining proxy entry may target port 3100 after Express retirement."""
    proxy = json.loads((REPO_ROOT / "proxy.conf.json").read_text())
    still_express = [
        k for k, v in proxy.items()
        if "3100" in v.get("target", "")
    ]
    assert still_express == [], (
        f"These proxy entries still target Express :3100: {still_express}"
    )


def proxyConf_hasAllFourMigratedEndpoints():
    """All four AI endpoints migrated in Tasks 1–4 must have explicit proxy entries."""
    proxy = json.loads((REPO_ROOT / "proxy.conf.json").read_text())
    required = [
        "/api/ai/text/iterate",
        "/api/ai/text/lint-braindump",
        "/api/ai/text/review",
        "/api/ai/text/generate-spec",
    ]
    missing = [p for p in required if p not in proxy]
    assert missing == [], (
        f"proxy.conf.json is missing these migrated endpoint entries: {missing}. "
        f"Run Tasks 1–4 first."
    )


# ---------------------------------------------------------------------------
# Structural — package.json
# ---------------------------------------------------------------------------

def packageJson_hasNoApiScript():
    """'api' script must be removed — it was the Express start command."""
    scripts = json.loads((REPO_ROOT / "package.json").read_text())["scripts"]
    assert "api" not in scripts, (
        "package.json still contains 'api' script ('node server.js'). "
        "Remove it; Flask is started via 'cd flask && make dev'."
    )


def packageJson_devScriptDoesNotStartExpress():
    """'dev' script must not reference server.js after retirement."""
    scripts = json.loads((REPO_ROOT / "package.json").read_text())["scripts"]
    dev = scripts.get("dev", "")
    assert "server.js" not in dev, (
        f"'dev' script still references server.js: {dev!r}. "
        f"Update to 'npm run start' (Angular only)."
    )
    assert "npm run start" in dev or "ng serve" in dev, (
        f"'dev' script must start Angular; got: {dev!r}"
    )


# ---------------------------------------------------------------------------
# Route reachability — Flask test client with mock provider
# ---------------------------------------------------------------------------

def iterate_validRequest_flaskHandlesIt(client):
    """POST /api/ai/text/iterate must be registered on Flask (non-404)."""
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"document": "# Original Spec", "instruction": ""}),
        content_type="application/json",
    )
    assert r.status_code != 404, (
        f"/api/ai/text/iterate returned 404 — route not registered. "
        f"Ensure Task 1 (iterate route) is complete. Got: {r.status_code}"
    )


def iterate_validRequest_returns200WithText(client):
    """iterate endpoint returns 200 with text envelope when mock provider is active."""
    r = client.post(
        "/api/ai/text/iterate",
        data=json.dumps({"document": "# Spec", "instruction": ""}),
        content_type="application/json",
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.data}"
    body = json.loads(r.data)
    assert "text" in body, f"Response must include 'text'; got keys: {list(body)}"
    assert "latencyMs" in body, f"Response must include 'latencyMs'; got keys: {list(body)}"
    assert isinstance(body["latencyMs"], int)


def lintBraindump_validRequest_flaskHandlesIt(client):
    """POST /api/ai/text/lint-braindump must be registered on Flask (non-404).

    With the mock provider, JSON parsing of the mock response will fail;
    the handler raises ServiceError → 502. 502 is acceptable here — it proves
    Flask handled the request. The per-endpoint contract test (Tasks 2) owns
    the 200 + {ready, flags} shape assertion.
    """
    r = client.post(
        "/api/ai/text/lint-braindump",
        data=json.dumps({"braindump": "I want to build a product that does X"}),
        content_type="application/json",
    )
    assert r.status_code != 404, (
        f"/api/ai/text/lint-braindump returned 404 — route not registered. "
        f"Ensure Task 2 (lint-braindump route) is complete. Got: {r.status_code}"
    )
    body = json.loads(r.data)
    # With mock, response is either {ready, flags} (if handler has a fallback)
    # or {error} (if ServiceError raised on parse failure). Either is valid here.
    assert "ready" in body or "error" in body, (
        f"Response must contain 'ready' or 'error'; got keys: {list(body)}"
    )


def review_validRequest_flaskHandlesIt(client):
    """POST /api/ai/text/review must be registered on Flask (non-404).

    With mock provider and raw-string fallback (matching Express behavior),
    expects 200 with 'review' key. If handler raises instead, 502 is acceptable
    as a smoke signal that Flask owns the route.
    """
    r = client.post(
        "/api/ai/text/review",
        data=json.dumps({"documents": {"spec.md": "# My Spec\n\nContent here."}}),
        content_type="application/json",
    )
    assert r.status_code != 404, (
        f"/api/ai/text/review returned 404 — route not registered. "
        f"Ensure Task 3 (review route) is complete. Got: {r.status_code}"
    )


def generateSpec_validRequest_flaskHandlesIt(client):
    """POST /api/ai/text/generate-spec must be registered on Flask (non-404)."""
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({"input": "A product that helps developers write specs"}),
        content_type="application/json",
    )
    assert r.status_code != 404, (
        f"/api/ai/text/generate-spec returned 404 — route not registered. "
        f"Ensure Task 4 (generate-spec route) is complete. Got: {r.status_code}"
    )


def generateSpec_validRequest_returns200WithText(client):
    """generate-spec endpoint returns 200 with text envelope containing FILE markers."""
    r = client.post(
        "/api/ai/text/generate-spec",
        data=json.dumps({"input": "A CLI tool for developers"}),
        content_type="application/json",
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.data}"
    body = json.loads(r.data)
    assert "text" in body, f"Response must include 'text'; got keys: {list(body)}"
    assert isinstance(body.get("latencyMs"), int), "latencyMs must be an integer"
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step — not at the end. Each commit boundary corresponds to one step above.

1. `chore(proxy): remove Express fallback route from proxy.conf.json` — after Step 1 — `proxy.conf.json`: remove `/api → :3100` catch-all entry
2. `chore(scripts): retire Express start scripts from package.json` — after Step 2 — `package.json`: remove `api` script, update `dev` to Angular-only
3. `test(retire-express): smoke tests for proxy config and migrated Flask routes` — after Step 3 passes — `flask/tests/test_retire_express.py`: structural + reachability assertions

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd flask && python -m pytest -q
```

**Expected delta**: baseline → baseline + 10 passing (the 10 new functions in `test_retire_express.py`). Zero pre-existing tests broken.

Additionally, verify the proxy change is structurally correct:
```bash
python3 -c "
import json
p = json.load(open('proxy.conf.json'))
print(f'Entries: {len(p)}')
print(f'Fallback gone: {chr(10).join(k for k in p if k==\"/api\") or \"yes\"}')
targets = set(v[\"target\"] for v in p.values())
print(f'Targets: {targets}')
"
```
Expect: no `/api` key, all targets `http://localhost:3101`.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - Step 1: `git revert <sha>` restores the Express fallback entry; Angular dev-server resumes routing unknown `/api` traffic to 3100 while Flask is still running
  - Step 2: `git revert <sha>` restores the `api` and `dev` scripts; `npm run dev` resumes starting both processes
  - Step 3: `git revert <sha>` removes the smoke test file; no functional change
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch and re-apply from Tasks 1–4's final commit

---

## 9. Deviations Allowed

- **proxy.conf.json entry count differs from expected** — Tasks 1–4 may have added entries in a different order; the invariant is `"/api" absent` and `all targets :3101`, not a specific count. Verify with the Step 1 verify command, not by counting lines.
- **Test framework signals a collection issue** — `flask/pyproject.toml` configures `python_functions = ["test_*", "*_*"]`; if functions in `test_retire_express.py` are not collected, verify `pyproject.toml` is in place (confirmed at `flask/pyproject.toml`).
- **`lintBraindump_validRequest_flaskHandlesIt` or `review_validRequest_flaskHandlesIt` returns 200 instead of expected keys** — Tasks 2 and 3 may implement a JSON fallback that returns 200 rather than raising ServiceError. Adjust the assertion to match the actual response shape; log as a deviation. The invariant (non-404) is what matters.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]` and ask.
- **Prescribed path doesn't exist** → verify against the file listing above; if still missing, flag — do not invent.

---

## 10. Out of Scope

Task 5 is strictly configuration surgery. The following work was explicitly excluded to keep the blast radius to a proxy diff and a package.json diff:

- **`server.js` deletion** — the Express server file is not deleted in this task; removing it requires auditing all imports (`services/container.service`, `server/walker`, etc.) and cleaning up all transitive references. That is a separate cleanup task with its own commit surface.
- **Express test file cleanup** (`server.test.js`, `server.integration.test.js`) — these test an Express server that is no longer started; they are dead weight but deleting them is coupled to `server.js` deletion above.
- **`test:server`, `test:mock`, `test:all` script removal** — these npm test scripts reference `server.js` and `server.integration.test.js`; they become no-ops once Express isn't started but removing them is bundled with the `server.js` deletion task.
- **`express` dependency removal from `package.json`** — removing the npm dependency is the final step after `server.js` and all its imports are gone. Removing it before then breaks `npm install` on any machine that still runs `node --test server.test.js`.
- **`generate` endpoint migration** — already specced as Phase 2 work per the Epic; explicitly out of scope.
- **Flask `start:flask` convenience script in package.json** — a `"flask": "cd flask && python app.py"` convenience script in package.json would be helpful but is new code beyond the "Config changes only" port budget.

**Rule for the executor**: if any of the above appear helpful during this task, STOP and flag as a proposed follow-up rather than expanding the commit surface.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale and execution flow
- [Epic](./epic.md) — Task scope and port budget
- [Timeline](./timeline.md) — Update Task 5 status to `done` after verification passes