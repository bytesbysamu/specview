# Task 5 — Add Production Startup Gate to `create_app`

**Effort**: 0.1 days

## 1. Context

The deploy container has no `claude` binary. Tasks 1–4 made the SDK provider correct, observable, and cost-tuned, but nothing prevents shipping a container that simultaneously has `FLASK_DEBUG=0` (production), no `ANTHROPIC_API_KEY` (no SDK auth), and no `CHAIN_PROVIDER=mock` override (no test escape hatch). Today that misconfiguration crashes only when a user makes the first AI call — silent until traffic.

This task adds a single guard at the top of `create_app()` that raises `RuntimeError` on the bad configuration. The error message names the two recovery paths: set `ANTHROPIC_API_KEY` to enable the SDK provider, or set `CHAIN_PROVIDER=mock` for tests. Crash on startup is loud, fast, and visible in the deploy job's first-boot log; users never see a cryptic 500.

This is the smallest task in the epic and lands last because it depends on Task 2's auto-detection: the gate is correct only if "API key set" is the same signal the adapter uses to pick the SDK provider. Without that alignment, the gate would pass while the adapter still defaulted to CLI.

---

## 2. Pre-flight

```bash
git status -- api/create_app.py api/tests/
cd {WORKSPACE}/api && python -m pytest --tb=no -q 2>&1 | tail -3
```

Confirm Tasks 1, 2, and 3 have merged (Task 4 is parallel; either order works). Recorded test count is `R`.

---

## 3. Files

### To Modify

- `{WORKSPACE}/api/create_app.py` — add a guard block near the top of `create_app()` after `load_dotenv()` and before any blueprint registration

### To Create (new)

- `{WORKSPACE}/api/tests/test_startup_gate.py` (new) — covers the four branches: API key set → ok; FLASK_DEBUG=1 → ok; CHAIN_PROVIDER=mock → ok; otherwise → raise

### To Leave Alone

- `{WORKSPACE}/api/modules/runtime/chain/*` — Tasks 1–3 finished
- `{WORKSPACE}/api/modules/ai/workflows/*` — Task 4 finished (or parallel)
- `{WORKSPACE}/api/openapi.yaml` — no contract change

---

## 4. Implementation Steps

### Step 1: Add the guard helper and call it from `create_app`

**File**: `{WORKSPACE}/api/create_app.py`

**Pattern** (define above `create_app`; call as the first action inside `create_app`):

```python
def _enforce_production_provider_config() -> None:
    """Crash on startup if production env is missing the SDK API key.

    Three escape conditions (any one suffices):
      * FLASK_DEBUG truthy   — developer machine; CLI fallback is fine
      * ANTHROPIC_API_KEY set — production-ready; SDK provider can authenticate
      * CHAIN_PROVIDER=mock  — explicit test escape hatch

    Anything else (production-mode boot with no API key and no mock override)
    means the deployed container would crash on the first AI call.
    Raise on startup so the deploy job's first-boot log shows the error.
    """
    debug = os.environ.get("FLASK_DEBUG", "0") not in ("", "0", "false", "False")
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    explicit_mock = os.environ.get("CHAIN_PROVIDER", "").lower() == "mock"
    if debug or has_key or explicit_mock:
        return
    raise RuntimeError(
        "Production mode requires ANTHROPIC_API_KEY to be set so the "
        "Anthropic SDK provider can authenticate. To override for tests, "
        "set CHAIN_PROVIDER=mock. To run in development with the Claude "
        "Code CLI, set FLASK_DEBUG=1."
    )


def create_app(config=None):
    _enforce_production_provider_config()
    app = Flask(__name__)
    # ... rest of create_app unchanged ...
```

The helper is module-level (testable in isolation). The call inside `create_app` is one line.

---

### Step 2: Test the four branches

**File**: `{WORKSPACE}/api/tests/test_startup_gate.py` **(new)**

```python
"""Verify the production startup gate covers all four branches."""
from __future__ import annotations

import pytest

from create_app import _enforce_production_provider_config, create_app


def _clear_env(monkeypatch):
    for key in ("FLASK_DEBUG", "ANTHROPIC_API_KEY", "CHAIN_PROVIDER"):
        monkeypatch.delenv(key, raising=False)


def test_gate_passes_when_flask_debug_is_truthy(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("FLASK_DEBUG", "1")
    _enforce_production_provider_config()  # must not raise


def test_gate_passes_when_anthropic_api_key_is_set(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-anything")
    _enforce_production_provider_config()  # must not raise


def test_gate_passes_when_chain_provider_is_mock(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    _enforce_production_provider_config()  # must not raise


def test_gate_raises_when_production_env_is_inconsistent(monkeypatch):
    _clear_env(monkeypatch)
    with pytest.raises(RuntimeError) as excinfo:
        _enforce_production_provider_config()
    msg = str(excinfo.value)
    assert "ANTHROPIC_API_KEY" in msg
    assert "CHAIN_PROVIDER=mock" in msg
    assert "FLASK_DEBUG" in msg


def test_create_app_invokes_gate(monkeypatch):
    """create_app() must crash before any blueprint registration on bad env."""
    _clear_env(monkeypatch)
    with pytest.raises(RuntimeError):
        create_app({"TESTING": True})


def test_create_app_succeeds_with_mock_provider(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("CHAIN_PROVIDER", "mock")
    app = create_app({"TESTING": True})
    assert app is not None
    # Health endpoint registered means we passed the gate AND blueprint loop.
    with app.test_client() as c:
        resp = c.get("/health")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}
```

---

## 5. Tests

```bash
cd {WORKSPACE}/api && python -m pytest tests/test_startup_gate.py -q
cd {WORKSPACE}/api && python -m pytest -q
```

**Expected delta**: `R → R+6 passing` (4 isolated gate tests + 2 create_app integration tests).

If the existing test suite uses an autouse fixture that pre-sets `CHAIN_PROVIDER=mock`, the gate's "no env" test must clear it explicitly (the helper above does so via `monkeypatch.delenv`). Do not weaken the gate to accommodate a leaky fixture; clean the fixture instead.

---

## 6. Commit Plan

```bash
cd {WORKSPACE}
git add api/create_app.py api/tests/test_startup_gate.py

git commit -m "$(cat <<'EOF'
feat(create_app): production startup gate for AI provider config

create_app() raises RuntimeError when FLASK_DEBUG is off, no
ANTHROPIC_API_KEY is set, and CHAIN_PROVIDER is not mock. The error
message names the three escape conditions so the deploy log surfaces
remediation, not just a stack trace. Crash on startup is loud and fast;
the alternative is a silent failure on the first AI call.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: `R → R+6 passing`.

Manual check:

```bash
# Should crash:
cd {WORKSPACE}/api && env -u FLASK_DEBUG -u ANTHROPIC_API_KEY -u CHAIN_PROVIDER \
  python -c "from create_app import create_app; create_app()" 2>&1 | tail -3

# Should succeed:
cd {WORKSPACE}/api && CHAIN_PROVIDER=mock python -c "
from create_app import create_app; print(create_app() and 'OK')"
```

The first command exits non-zero with the RuntimeError message. The second prints `OK`.

---

## 8. Rollback

```bash
git revert <sha-of-this-task>
```

Reverting removes the gate. The deploy will go back to silent first-call failure on misconfiguration, which is the regression path Task 5 was added to prevent. Other capabilities are unaffected.

---

## 9. Deviations Allowed

- **Existing tests rely on `create_app()` working with no env at all**: convert those tests to set `CHAIN_PROVIDER=mock` in a fixture. Do NOT weaken the gate to accommodate them.
- **A future deploy environment uses a different secret name** (e.g., `CLAUDE_API_KEY`): update both the gate's check and the SDK provider to accept the new name; align them in the same commit so the gate can never pass while the provider still cannot authenticate.
- **The deploy uses `gunicorn --preload` and the gate fires once per worker**: acceptable; the cost is one cheap env-var read per startup. If `--preload` is added later, the gate runs once at master process boot — same outcome.
- **`FLASK_DEBUG` value is set to a non-standard truthy string** (e.g., `"yes"`): the parser above accepts anything other than `""`, `"0"`, `"false"`, `"False"`. Extend if a new convention emerges; document the change inline.

---

## 10. Out of Scope

- Validating other production-required env vars (`SPEC_DOC_DIR`, `CORS_ORIGINS`) — separate operations-infra concern; that capability already owns the deploy-config contract
- A startup-gate framework that other modules can plug into — ELA #5; one consumer, one gate, no abstraction
- Deploy-job-side preflight in `deploy.yml` — operations-infra capability
- A `/api/health/ready` endpoint that surfaces gate status post-boot — separate observability capability if/when needed

---

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
