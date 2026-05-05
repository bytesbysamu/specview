# Task 2: Sentry + Error Handlers — Implementation Guide

## 1. Context

Task 1 (Structured Logging) established `modules/observability/` and wired `init_logging(app)` as the first call in `create_app()`. Task 2 extends that module with two additions: an opt-in Sentry integration that stamps every captured event with the `request_id` already flowing through structlog's contextvars, and a set of JSON error handlers that give Angular's HTTP interceptor a uniform error envelope regardless of error type. Together they close the observability loop: a 500 in production maps to a structured log line, a correlated Sentry event, and an identifiable `request_id` — all from `create_app()` wiring, no business-logic changes required.

**Trade-offs considered:**
- **Global `before_send` hook to attach `request_id` to all Sentry events** vs. injecting it only in the unhandled-exception handler — the global hook wins because it catches exceptions that other integrations (e.g., FlaskIntegration background captures) report independently, ensuring no event loses correlation.
- **`sentry_sdk.capture_exception(exc)` called explicitly in `handle_unhandled`** vs. relying on FlaskIntegration's automatic capture — explicit wins because once an `@app.errorhandler(Exception)` handler returns a response, the exception no longer propagates and FlaskIntegration never sees it; silent automatic-only capture would miss every handled 500.
- **Single `register_error_handlers(app)` function in `errors.py`** vs. decorator-per-file — single function respects ELA #5 (one consumer: `create_app()`) and keeps LOC under the 45-line budget; decorator-per-file introduces an abstraction with no second consumer.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
cd {WORKSPACE}/api

git status                                              # Flag any unrelated M/?? entries
git diff HEAD -- create_app.py requirements.txt         # Confirm target files are clean
git diff HEAD -- modules/observability/                 # Confirm Task 1 files are committed

python -m pytest --tb=short -q                         # Record baseline pass count
```

**If working tree is dirty on target files**: stash unrelated changes with `git stash push -m "pre-task2-stash"` before starting.

**Baseline recorded**: 624 / 624 passing (1 skipped — web-root check; expected).

**Task 1 pre-condition**: `modules/observability/logging.py` and `modules/observability/__init__.py` must exist and be committed. If they are absent, stop and complete Task 1 first.

---

## 3. Files

### To Create (new)

- `api/modules/observability/sentry.py` — `init_sentry(app)` with DSN guard + `_before_send` hook for `request_id` correlation + `set_sentry_user` Phase-1 stub
- `api/modules/observability/errors.py` — `register_error_handlers(app)` with three handlers: `HTTPException`, `ValidationError`, bare `Exception`
- `api/modules/observability/tests/test_sentry.py` — unit tests for `init_sentry` and `set_sentry_user`
- `api/modules/observability/tests/test_errors.py` — integration tests for all three error handlers using Flask test client

### To Modify (cite CODEBASE CONTEXT)

- `api/requirements.txt` — add `sentry-sdk[flask]` pin; structlog already added by Task 1
- `api/create_app.py` — add `init_sentry(app)` and `register_error_handlers(app)` calls in the correct initialization order (after `init_logging`, before blueprint registration)

### To Leave Alone

- `api/modules/observability/logging.py` — Task 1's work; `request_id` binding via `before_request` is already wired; do not modify
- `api/modules/observability/__init__.py` — Task 1's work; add no public exports from this task
- `api/modules/observability/tests/__init__.py` — Task 1's work; empty marker file, leave as-is
- `api/openapi.yaml` — no contract changes; error responses use existing `4xx`/`5xx` shapes
- `api/dtos/models.py` — generated; never hand-edit

---

## 4. Implementation Steps

### Step 1: Pin `sentry-sdk[flask]` in requirements

**Action**: Open `api/requirements.txt` and append the Sentry dependency after the structlog line (added by Task 1).

**File**: `api/requirements.txt` (existing)

**Pattern**:
```text
structlog>=24.0,<25          # added by Task 1
sentry-sdk[flask]>=2.0,<3   # Task 2
```

**Verify**:
```bash
cd {WORKSPACE}/api
pip install -r requirements.txt
pip show sentry-sdk | grep Version   # Expect: Version: 2.x.x
```

---

### Step 2: Create `modules/observability/sentry.py`

**Action**: Create the Sentry initialisation module. `init_sentry` is a no-op when `SENTRY_DSN` is absent. `_before_send` reads `request_id` from structlog's contextvars (set by Task 1's `before_request` hook) and stamps it onto every outbound Sentry event. `set_sentry_user` is the Phase-1 stub — two lines that auth middleware calls without this module changing.

**File**: `api/modules/observability/sentry.py` (new)

**Pattern**:
```python
import os
from typing import Any, Dict, Optional

import sentry_sdk
import structlog
from sentry_sdk.integrations.flask import FlaskIntegration
from structlog.contextvars import get_contextvars

logger = structlog.get_logger(__name__)


def _before_send(
    event: Dict[str, Any], hint: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Stamp every Sentry event with the request_id from structlog context vars."""
    rid = get_contextvars().get("request_id")
    if rid:
        event.setdefault("tags", {})["request_id"] = rid
    return event


def init_sentry(app) -> None:
    """Initialise Sentry SDK. Silent no-op when SENTRY_DSN is absent."""
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_RATE", "0.1")),
        send_default_pii=False,
        before_send=_before_send,
    )
    logger.info("sentry_initialized")


def set_sentry_user(user_id: str) -> None:
    """Populate per-user Sentry scope. Called by auth middleware (Phase 1).
    No-op when SENTRY_DSN is absent — sentry_sdk.set_user is safe to call unconditionally."""
    sentry_sdk.set_user({"id": user_id})
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "from modules.observability.sentry import init_sentry, set_sentry_user; print('ok')"
# Expect: ok
```

---

### Step 3: Create `modules/observability/errors.py`

**Action**: Create the error-handler registration module. `handle_http` preserves the upstream status code. `handle_validation` returns 422 with Pydantic's field-level detail list — the same shape works for both Pydantic v1 (`exc.errors()`) and v2 (`exc.errors()`). `handle_unhandled` logs first (so the structured log is recorded even if Sentry is down), then captures to Sentry explicitly because `FlaskIntegration` does not re-see exceptions that are consumed by a registered handler.

**File**: `api/modules/observability/errors.py` (new)

**Pattern**:
```python
import sentry_sdk
import structlog
from flask import jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

logger = structlog.get_logger(__name__)


def register_error_handlers(app) -> None:
    """Register JSON error handlers. Call after init_logging(app), before blueprint registration."""

    @app.errorhandler(HTTPException)
    def handle_http(exc: HTTPException):
        return jsonify({"error": exc.description, "status": exc.code}), exc.code

    @app.errorhandler(ValidationError)
    def handle_validation(exc: ValidationError):
        return jsonify({"error": "validation_error", "detail": exc.errors()}), 422

    @app.errorhandler(Exception)
    def handle_unhandled(exc: Exception):
        logger.error("unhandled_exception", exc_info=True)
        sentry_sdk.capture_exception(exc)
        return jsonify({"error": "internal_server_error"}), 500
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "from modules.observability.errors import register_error_handlers; print('ok')"
# Expect: ok
```

---

### Step 4: Wire both into `create_app.py`

**Action**: Add two imports and two calls in `create_app()`, in the mandated order: `init_logging` → `init_sentry` → `register_error_handlers` → blueprint registration. Do not touch any existing blueprint registration lines.

**File**: `api/create_app.py` (existing — from CODEBASE CONTEXT: App factory; registers all blueprints)

**Pattern** — add to the imports block and the factory body:
```python
# existing Task-1 import:
from modules.observability.logging import init_logging
# add these two:
from modules.observability.sentry import init_sentry
from modules.observability.errors import register_error_handlers


def create_app():
    app = Flask(__name__)

    # --- Observability (order is the contract) ---
    init_logging(app)          # structlog + request_id — Task 1
    init_sentry(app)           # opt-in Sentry — Task 2
    register_error_handlers(app)  # JSON error envelope — Task 2

    # --- existing blueprint registrations below; do not reorder ---
    ...
    return app
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -c "
from create_app import create_app
app = create_app()
rules = [str(r) for r in app.url_map.iter_rules()]
print('app created ok, rules:', len(rules))
"
# Expect: app created ok, rules: <N> (same count as before + no exception)
```

---

### Step 5: Write tests

**Action**: Create two test files in `api/modules/observability/tests/`. Use `PROPAGATE_EXCEPTIONS=False` so Flask's error handlers fire during test-client requests (with `TESTING=True` Flask would otherwise propagate exceptions directly, bypassing handlers).

**File**: `api/modules/observability/tests/test_sentry.py` (new)

```python
import os
from unittest.mock import patch

import pytest
from flask import Flask

from modules.observability.sentry import init_sentry, set_sentry_user


class TestInitSentry:
    def test_noop_when_dsn_absent(self):
        """init_sentry must not call sentry_sdk.init when SENTRY_DSN is unset."""
        app = Flask(__name__)
        env_without_dsn = {k: v for k, v in os.environ.items() if k != "SENTRY_DSN"}
        with patch.dict(os.environ, env_without_dsn, clear=True):
            with patch("sentry_sdk.init") as mock_init:
                init_sentry(app)
                mock_init.assert_not_called()

    def test_calls_sdk_init_when_dsn_present(self):
        """init_sentry must call sentry_sdk.init with the provided DSN."""
        app = Flask(__name__)
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch("sentry_sdk.init") as mock_init:
                init_sentry(app)
                mock_init.assert_called_once()
                kwargs = mock_init.call_args.kwargs
                assert kwargs["dsn"] == "https://key@sentry.io/123"
                assert kwargs["send_default_pii"] is False

    def test_flask_integration_included_when_dsn_present(self):
        """FlaskIntegration must be in the integrations list."""
        from sentry_sdk.integrations.flask import FlaskIntegration
        app = Flask(__name__)
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch("sentry_sdk.init") as mock_init:
                init_sentry(app)
                integrations = mock_init.call_args.kwargs.get("integrations", [])
                assert any(isinstance(i, FlaskIntegration) for i in integrations)

    def test_traces_sample_rate_defaults_to_0_1(self):
        """Default traces_sample_rate is 0.1 when SENTRY_TRACES_RATE is unset."""
        app = Flask(__name__)
        env = {"SENTRY_DSN": "https://key@sentry.io/123"}
        with patch.dict(os.environ, env):
            env_clean = {k: v for k, v in os.environ.items() if k != "SENTRY_TRACES_RATE"}
            with patch.dict(os.environ, env_clean, clear=True):
                with patch.dict(os.environ, env):
                    with patch("sentry_sdk.init") as mock_init:
                        init_sentry(app)
                        assert mock_init.call_args.kwargs["traces_sample_rate"] == pytest.approx(0.1)

    def test_traces_sample_rate_reads_env_override(self):
        """SENTRY_TRACES_RATE env var overrides the default sample rate."""
        app = Flask(__name__)
        env = {"SENTRY_DSN": "https://key@sentry.io/123", "SENTRY_TRACES_RATE": "0.5"}
        with patch.dict(os.environ, env):
            with patch("sentry_sdk.init") as mock_init:
                init_sentry(app)
                assert mock_init.call_args.kwargs["traces_sample_rate"] == pytest.approx(0.5)

    def test_before_send_hook_is_registered(self):
        """A before_send hook must be passed to sentry_sdk.init."""
        app = Flask(__name__)
        with patch.dict(os.environ, {"SENTRY_DSN": "https://key@sentry.io/123"}):
            with patch("sentry_sdk.init") as mock_init:
                init_sentry(app)
                assert callable(mock_init.call_args.kwargs.get("before_send"))


class TestSetSentryUser:
    def test_delegates_to_sdk_set_user(self):
        """set_sentry_user must call sentry_sdk.set_user with the id dict."""
        with patch("sentry_sdk.set_user") as mock_set:
            set_sentry_user("user-42")
            mock_set.assert_called_once_with({"id": "user-42"})

    def test_callable_without_dsn_configured(self):
        """set_sentry_user must not raise even when Sentry is not initialised."""
        with patch("sentry_sdk.set_user"):
            # Should complete without exception regardless of SDK init state
            set_sentry_user("no-dsn-user")
```

**File**: `api/modules/observability/tests/test_errors.py` (new)

```python
from unittest.mock import patch

import pytest
from flask import Flask
from pydantic import BaseModel
from werkzeug.exceptions import Forbidden, NotFound

from modules.observability.errors import register_error_handlers
from modules.observability.logging import init_logging


@pytest.fixture()
def app():
    a = Flask(__name__)
    a.config["TESTING"] = True
    # PROPAGATE_EXCEPTIONS defaults True when TESTING=True; disable so error handlers fire.
    a.config["PROPAGATE_EXCEPTIONS"] = False
    init_logging(a)
    register_error_handlers(a)
    return a


@pytest.fixture()
def client(app):
    return app.test_client()


class TestHTTPExceptionHandler:
    def test_404_returns_json_with_correct_status(self, app, client):
        @app.route("/trigger-404")
        def trigger_404():
            raise NotFound("resource not found")

        resp = client.get("/trigger-404")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["status"] == 404
        assert isinstance(data["error"], str)
        assert len(data["error"]) > 0

    def test_403_returns_json_with_correct_status(self, app, client):
        @app.route("/trigger-403")
        def trigger_403():
            raise Forbidden("access denied")

        resp = client.get("/trigger-403")
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == 403

    def test_response_content_type_is_json(self, app, client):
        @app.route("/trigger-ct")
        def trigger_ct():
            raise NotFound("not here")

        resp = client.get("/trigger-ct")
        assert resp.content_type.startswith("application/json")


class TestValidationErrorHandler:
    def test_pydantic_validation_error_returns_422(self, app, client):
        class Strict(BaseModel):
            age: int

        @app.route("/trigger-validation")
        def trigger_validation():
            Strict(age="not-a-number")
            return "ok"

        resp = client.get("/trigger-validation")
        assert resp.status_code == 422
        data = resp.get_json()
        assert data["error"] == "validation_error"

    def test_validation_detail_is_list(self, app, client):
        class Item(BaseModel):
            price: float

        @app.route("/trigger-validation-detail")
        def trigger_validation_detail():
            Item(price="bad")
            return "ok"

        resp = client.get("/trigger-validation-detail")
        data = resp.get_json()
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) >= 1

    def test_validation_detail_contains_field_location(self, app, client):
        class Model(BaseModel):
            count: int

        @app.route("/trigger-validation-loc")
        def trigger_validation_loc():
            Model(count="not-an-int")
            return "ok"

        resp = client.get("/trigger-validation-loc")
        data = resp.get_json()
        # Pydantic v1 and v2 both include a 'loc' key in each error dict
        first_error = data["detail"][0]
        assert "loc" in first_error or "location" in first_error or "input" in first_error, (
            f"Expected field location info in error dict, got: {first_error}"
        )


class TestUnhandledExceptionHandler:
    def test_unhandled_exception_returns_500(self, app, client):
        @app.route("/trigger-500")
        def trigger_500():
            raise RuntimeError("boom")

        resp = client.get("/trigger-500")
        assert resp.status_code == 500

    def test_unhandled_exception_body_is_json(self, app, client):
        @app.route("/trigger-500-body")
        def trigger_500_body():
            raise RuntimeError("body test")

        resp = client.get("/trigger-500-body")
        data = resp.get_json()
        assert data is not None, "Response body must be valid JSON"
        assert data["error"] == "internal_server_error"

    def test_unhandled_exception_calls_capture_exception(self, app, client):
        @app.route("/trigger-sentry")
        def trigger_sentry():
            raise ValueError("sentry capture test")

        with patch("sentry_sdk.capture_exception") as mock_capture:
            client.get("/trigger-sentry")
            mock_capture.assert_called_once()
            captured_exc = mock_capture.call_args.args[0]
            assert isinstance(captured_exc, ValueError), (
                f"Expected ValueError passed to capture_exception, got {type(captured_exc)}"
            )

    def test_unhandled_exception_emits_structured_log(self, app, client):
        import structlog.testing

        @app.route("/trigger-log")
        def trigger_log():
            raise RuntimeError("log test")

        with structlog.testing.capture_logs() as logs:
            with patch("sentry_sdk.capture_exception"):
                client.get("/trigger-log")

        error_logs = [
            entry for entry in logs
            if entry.get("event") == "unhandled_exception"
        ]
        assert len(error_logs) == 1, (
            f"Expected exactly one 'unhandled_exception' log entry, got {error_logs}"
        )
        assert error_logs[0].get("log_level") == "error"
```

**Verify**:
```bash
cd {WORKSPACE}/api
python -m pytest modules/observability/tests/test_sentry.py modules/observability/tests/test_errors.py -v
# Expect: all 16 tests collected and passing, 0 errors
```

---

## 6. Commit Plan

**Executor instruction**: commit after **each step** completes — not at the end of the task. Run the commit command shown before moving to the next step.

1. `chore(observability): pin sentry-sdk[flask] 2.x in requirements` — after Step 1 — files: `api/requirements.txt`
2. `feat(observability): add init_sentry with opt-in DSN guard and request_id before_send` — after Step 2 — files: `api/modules/observability/sentry.py`
3. `feat(observability): add JSON error handlers for HTTP, validation, and unhandled exceptions` — after Step 3 — files: `api/modules/observability/errors.py`
4. `feat(observability): wire init_sentry and register_error_handlers into create_app` — after Step 4 — files: `api/create_app.py`
5. `test(observability): add tests for sentry init, set_sentry_user, and all three error handlers` — after Step 5, tests passing — files: `api/modules/observability/tests/test_sentry.py`, `api/modules/observability/tests/test_errors.py`

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api
python -m pytest --tb=short -q
```

**Expected delta**: 624 → 640 passing (16 new tests: 8 in `test_sentry.py`, 8 in `test_errors.py`). Zero pre-existing tests broken.

The 1 pre-existing skip (web-root check) remains; do not attempt to fix it.

---

## 8. Rollback

- **Per-step**: every step produces an independent commit. Revert any single step with:
  ```bash
  git revert <sha> --no-edit
  ```
  The revert is safe because each commit touches only the files listed in the Commit Plan.

- **Per-branch (catastrophic)**: if verification fails unrecoverably:
  ```bash
  git reset --hard <pre-task2-sha>   # sha = last commit from Task 1
  ```
  Or delete the feature branch entirely and re-cut from `master`.

- **Partial rollback (Step 4 only)**: if `create_app.py` wiring causes a regression but the modules themselves are correct, revert commit 4 and leave commits 1–3 in place. The modules are safe to commit independently; they have no effect until wired.

---

## 9. Deviations Allowed

- **`PROPAGATE_EXCEPTIONS` key name differs in your Flask version** → check `app.config` docs for your Flask pin; the equivalent flag must suppress exception propagation in test mode. Log in commit body.
- **Pydantic v1 vs v2 `exc.errors()` shape difference** → `test_validation_detail_contains_field_location` uses a permissive assertion (`"loc" in first_error or "location" in first_error or "input" in first_error`) intentionally; translate to the actual key your Pydantic version produces and log the deviation.
- **`structlog.testing.capture_logs()` not available in your structlog version** → check structlog changelog; if absent, mock `structlog.get_logger` to capture calls instead. Log in commit body.
- **`sentry_sdk.init` call signature differs** → inspect `sentry_sdk.__version__` first; if `before_send` is passed differently in v1.x, adapt and log.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log as deviation in the commit.
- **Side-effect required** (push, schema change, `rm -rf`) → STOP, mark **[REQUIRES APPROVAL]**, and do not proceed.

---

## 10. Out of Scope

This task installs the Sentry integration and error-handler envelope. It does **not** activate the per-user Sentry scope (the `set_sentry_user` stub is written but is a no-op until Phase-1 auth middleware calls it), extend health checks, or touch the CI pipeline. The CI smoke test in Task 4 will target `/api/health/anthropic` — that endpoint contract is Task 3's concern and must not be pre-empted here.

- **`set_sentry_user` activation** — deferred to Phase-1 auth middleware; no changes to `sentry.py` are required when that lands — only the auth middleware adds a `before_request` call to `set_sentry_user(user.id)`.
- **Sentry Replay and performance tracing tuning** — deferred until first hard-to-reproduce user bug; `SENTRY_TRACES_RATE` env var is already wired if the decision reverses.
- **`/api/health` blueprint** — Task 3; not part of this module even though it lives in `modules/observability/`.
- **Angular HTTP interceptor to consume the uniform error envelope** — deferred to the web task; the backend shape (`{"error": "...", "status": N}`) is stable and ready to consume.
- **Open Architecture question: Anthropic health probe via adapter vs SDK direct** — Task 3's decision to make; this guide makes no ruling on it.
- **Log aggregation / BetterStack wiring** — deferred until first production log-search incident per the architecture's open question on log destination.

**Rule for the executor**: if a change appears helpful but appears on this list, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale and initialization-order contract
- [Epic](./epic.md) — Task scope and dependency graph
- [Timeline](./timeline.md) — Update status to ✅ after verification passes