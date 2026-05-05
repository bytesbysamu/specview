# Task 2: Config Hardening — Implementation Guide

## 1. Context

This task makes the Flask server's environment surface explicit and overridable without editing source files. `create_app.py` currently hardcodes one CORS origin and has no dotenv loading. The change is: add `python-dotenv` to deps, call `load_dotenv()` once at module import in `create_app.py`, parse `CORS_ORIGINS` from the environment (comma-separated, defaulting to the current hardcoded value), and document every env var the server reads in a new `.env.example`. No new routes, no new config module, no schema changes.

**Trade-offs considered:**
- Dedicated `config.py` module for env vars — rejected: `CORS_ORIGINS` has exactly one caller (`create_app.py`); the existing `flask/config.py` handles filesystem paths; adding a second config module adds import indirection with zero current benefit.
- `load_dotenv()` inside `create_app()` body — considered; placing it at module level is equivalent (dotenv is idempotent on repeated calls) and slightly cleaner since it runs once at import time rather than once per test fixture invocation.
- Hardcode `http://localhost:4201,http://localhost:4202` as the new default — rejected: the current code only contains `http://localhost:4201`; defaulting to what's actually there avoids silently expanding the allowed-origin surface. The `.env.example` demonstrates multi-origin syntax.

---

## 2. Pre-flight

```bash
# Run from workspace root (spec-doc/)
git status
git diff HEAD -- flask/create_app.py flask/requirements.txt

# Baseline test count — record before any edits
cd flask && python -m pytest -q --tb=no 2>&1 | tail -3
```

**If working tree is dirty on `flask/create_app.py` or `flask/requirements.txt`**: stash or commit unrelated changes first.

**Baseline recorded**: run the command above and note `N passed` before proceeding.

---

## 3. Files

### To Create (new)
- `flask/.env.example` — documents all env vars the Flask server reads; ~14 lines

### To Modify (cite CODEBASE CONTEXT)
- `flask/requirements.txt` — add `python-dotenv>=1.0.0`; currently 7 lines, no dotenv entry
- `flask/create_app.py` — add `load_dotenv()` at module level; replace `origins=['http://localhost:4201']` with env-var parsed list

### New tests (new)
- `flask/tests/test_config_envvar.py` — 3 focused tests for CORS env-var parsing; does not modify existing tests

### To Leave Alone
- `flask/config.py` — filesystem path constants (`BASE_DIR`, `PROJECTS_DIR`, `CONTEXT_FILES`); one-caller pattern, already correct; no env vars needed here
- `flask/app.py` — already reads `PORT` from env (`os.environ.get('PORT', 3101)`); no change needed
- `flask/tests/conftest.py` — app fixture uses default env (no `CORS_ORIGINS` set), will continue to work after the change
- `flask/tests/test_health.py` — all CORS tests pass with the default value; no modifications needed
- All other test files — no changes

---

## 4. Implementation Steps

### Step 1: Add python-dotenv to requirements

**Action**: Append `python-dotenv>=1.0.0` to `flask/requirements.txt`

**File**: `flask/requirements.txt`

**Pattern**:
```
flask>=3.0.0
flask-cors>=4.0.0
pytest>=8.0.0
anthropic
openapi-spec-validator>=0.5
pydantic>=2.0.0
pyyaml
python-dotenv>=1.0.0
```

**Verify**: `cd flask && pip install -r requirements.txt --quiet && python -c "import dotenv; print('ok')"` — expect `ok`

---

### Step 2: Add load_dotenv and CORS_ORIGINS parsing to create_app.py

**Action**: Add `from dotenv import load_dotenv` and `load_dotenv()` at module level; replace the hardcoded CORS list with env-var parsing inside `create_app()`

**File**: `flask/create_app.py`

**Pattern**:
```python
import importlib
import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

load_dotenv()

# Add module path + exported blueprint name here to register a new module.
ENABLED_MODULES = [
    ('modules.projects.routes', 'projects_bp'),
    ('modules.context.routes',  'context_bp'),
    ('modules.ai.routes',       'ai_bp'),
]

def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.update(config)

    # CORS: read from CORS_ORIGINS env var; default to Angular dev server
    _raw_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:4201')
    origins = [o.strip() for o in _raw_origins.split(',') if o.strip()]
    CORS(app, origins=origins)

    # Register all modules. Import inside factory so failures surface at startup.
    for module_path, blueprint_attr in ENABLED_MODULES:
        module = importlib.import_module(module_path)
        bp = getattr(module, blueprint_attr)
        app.register_blueprint(bp)

    @app.get('/health')
    def health():
        return jsonify({'status': 'ok'})

    return app
```

**Verify**: `cd flask && python -c "from create_app import create_app; a = create_app(); print('ok')"` — expect `ok`

---

### Step 3: Create .env.example

**Action**: Create `flask/.env.example` documenting all env vars the Flask server reads

**File**: `flask/.env.example` (new)

**Pattern**:
```bash
# Flask API — copy to .env and fill in values.
# Environment variables always take precedence over .env file values.

# AI chain provider: "claude" (default, requires ANTHROPIC_API_KEY) or "mock" (tests only)
# Note: the Express server used AI_PROVIDER; the Flask chain module uses CHAIN_PROVIDER.
CHAIN_PROVIDER=claude

# Anthropic API key — required when CHAIN_PROVIDER=claude
ANTHROPIC_API_KEY=

# Port the Flask server listens on (default: 3101)
PORT=3101

# Absolute path to the spec-doc workspace root.
# Leave blank to use the default (derived from flask/config.py file location).
SPEC_DOC_DIR=

# Comma-separated list of CORS-allowed origins (default: http://localhost:4201)
# Example for two dev ports: http://localhost:4201,http://localhost:4202
CORS_ORIGINS=http://localhost:4201
```

**Verify**: `cat flask/.env.example` — expect 14 lines, no blank key values other than `ANTHROPIC_API_KEY=` and `SPEC_DOC_DIR=`

---

### Step 4: Add env-var parsing tests

**Action**: Create `flask/tests/test_config_envvar.py` with three focused assertions for the CORS env-var behavior

**File**: `flask/tests/test_config_envvar.py` (new)

**Pattern**: see Tests section below

**Verify**: `cd flask && python -m pytest tests/test_config_envvar.py -v` — expect 3 passed, 0 failed

---

## 5. Tests

Framework: pytest + Flask test client (matching `flask/tests/test_health.py`).

```python
# flask/tests/test_config_envvar.py
"""Tests for CORS_ORIGINS env-var parsing in create_app.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_corsOriginsNotSet_defaultsToLocalhost4201(monkeypatch):
    """When CORS_ORIGINS is absent, the default permits http://localhost:4201."""
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        resp = client.get("/health", headers={"Origin": "http://localhost:4201"})
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    assert acao == "http://localhost:4201", (
        f"default CORS origin must be http://localhost:4201; got '{acao}'"
    )


def test_corsOriginsEnvVar_singleCustomOrigin_reflectsCustomOrigin(monkeypatch):
    """When CORS_ORIGINS is set to a custom origin, that origin is allowed."""
    monkeypatch.setenv("CORS_ORIGINS", "http://staging.example.com")
    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        resp = client.get("/health", headers={"Origin": "http://staging.example.com"})
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    assert acao == "http://staging.example.com", (
        f"CORS_ORIGINS env var not reflected; got '{acao}'"
    )


def test_corsOriginsEnvVar_commaSeparated_parsesMultipleOrigins(monkeypatch):
    """When CORS_ORIGINS is comma-separated, all listed origins are allowed."""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:4201,http://localhost:4202")
    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        resp1 = client.get("/health", headers={"Origin": "http://localhost:4201"})
        resp2 = client.get("/health", headers={"Origin": "http://localhost:4202"})
    acao1 = resp1.headers.get("Access-Control-Allow-Origin", "")
    acao2 = resp2.headers.get("Access-Control-Allow-Origin", "")
    assert acao1 == "http://localhost:4201", (
        f"first CORS origin must be allowed; got '{acao1}'"
    )
    assert acao2 == "http://localhost:4202", (
        f"second CORS origin must be allowed; got '{acao2}'"
    )
```

---

## 6. Commit Plan

1. `chore(deps): add python-dotenv to requirements.txt` — `flask/requirements.txt`: adds `python-dotenv>=1.0.0`

2. `feat(config): load dotenv at startup; CORS_ORIGINS from env` — `flask/create_app.py`: `load_dotenv()` at module level, `CORS_ORIGINS` env-var parsed list replaces hardcoded origin

3. `docs(config): add .env.example with all Flask env vars` — `flask/.env.example`: documents `CHAIN_PROVIDER`, `ANTHROPIC_API_KEY`, `PORT`, `SPEC_DOC_DIR`, `CORS_ORIGINS`

4. `test(config): add CORS env-var parsing tests` — `flask/tests/test_config_envvar.py`: 3 assertions for default, single override, and comma-separated multi-origin parsing

**Deviation logging**: prefix any commit body with `Deviations:` and one line per deviation if reality diverges from this guide.

---

## 7. Verification

```bash
cd flask && python -m pytest -q --tb=short
```

**Expected delta**: baseline N → N+3 passing (3 new tests in `test_config_envvar.py`). Zero pre-existing tests broken. The `test_cors_allows_angular_origin_exactly` test in `test_health.py` must still pass because the default remains `http://localhost:4201`.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>`
- **Per-branch**: `git reset --hard <pre-task-sha>` to undo all four commits. The `.env.example` file is new (untracked until committed) — if the executor abandons mid-task before commit 3, delete it manually with `rm flask/.env.example`.
- **No schema migrations, no DB changes, no side effects** — all rollbacks are pure file reversions.

---

## 9. Deviations Allowed

- **Epic says `AI_PROVIDER`; Flask code uses `CHAIN_PROVIDER`** — The epic was written when `AI_PROVIDER` was the Express server convention. The Flask chain adapter reads `CHAIN_PROVIDER` (confirmed in `flask/modules/chain/tests/test_adapter.py` monkeypatch calls). Document `CHAIN_PROVIDER` in `.env.example`, not `AI_PROVIDER`. Log as deviation in commit 3 body.
- **`create_app.py` comment says "Tasks 2 and 3 do NOT edit this file"** — that comment is stale/incorrect; Task 2 explicitly modifies `create_app.py`. Remove or update the comment when editing the file.
- **Test framework mismatch** — if a future pytest version rejects the `condition_expectedOutcome` naming without `pyproject.toml` (Task 1), rename the three new test functions to `test_<condition>_<outcome>` and note the deviation.
- **Side-effect required** (git push, pip publish) → STOP, mark `[REQUIRES APPROVAL]` and ask.
- **`python-dotenv` already present** → skip Step 1, log deviation in commit 2 body.

---

## 10. Out of Scope

This task adds dotenv loading and env-var-driven CORS. It does not restructure how config flows through the app. The following items are explicitly deferred and must not be absorbed:

- **`SPEC_DOC_DIR` env var wiring into `config.py`** — `.env.example` documents the intent, but `flask/config.py` still derives `BASE_DIR` from `__file__` location. Wiring `os.environ.get('SPEC_DOC_DIR')` into `config.py` is a separate task; one caller (`config.py`) is not yet worth the override logic.
- **`requirements-dev.txt` split** — separating prod and dev deps is Task 1 scope (Build tooling); do not add it here.
- **`pyproject.toml` pytest configuration** — also Task 1; `python_functions = ["test_*", "*_*"]` does not land in this task.
- **`@app.errorhandler` centralized handler** — Task 3 (Error handling); do not add to `create_app.py` in this task even though the file is already open.
- **Logging config in `create_app.py`** — Task 4 (Observability); defer.
- **`CONTEXT_PROVIDER` and other chain env vars in `.env.example`** — the four vars specified by the epic (`CHAIN_PROVIDER` / `ANTHROPIC_API_KEY` / `PORT` / `SPEC_DOC_DIR` / `CORS_ORIGINS`) are sufficient; do not enumerate every env var in the codebase.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update `Task 2` to `done` after verification passes)