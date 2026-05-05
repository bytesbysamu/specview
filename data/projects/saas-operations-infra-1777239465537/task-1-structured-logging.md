# Task 1: Structured Logging — Implementation Guide

## 1. Context

This task installs `structlog` as the sole logging framework for spec-doc's Flask backend, exposes two public functions (`configure_logging`, `bind_request_id`) from a new `modules/observability/` package, wires them into `create_app.py`, and migrates every existing module from the stdlib `logging.getLogger` pattern to `structlog.get_logger`. The result is JSON-structured log lines that automatically carry a `request_id` context variable — set once per request by a `before_request` hook — through every module without manual threading. Tasks 2 (Sentry + error handlers) and 3 (health blueprint) are directly blocked on this: both call `structlog.get_logger(__name__)` and both depend on `request_id` being present in every log event.

**Trade-offs considered:**
- **stdlib `logging` with a JSON formatter (e.g., `python-json-logger`)** — rejected because context-var propagation (`request_id` flows automatically into every log call on the same thread without passing it explicitly) is not available in stdlib without significant boilerplate; structlog's `merge_contextvars` processor gives it for free.
- **OpenTelemetry trace context as the correlation mechanism** — rejected because it adds a full APM SDK, a collector sidecar, and a vendor integration for a single-developer service where Sentry + structured logs cover the debugging case; revisit at the first multi-service boundary.
- **`structlog` with `contextvars`** — preferred because `merge_contextvars` makes `request_id` automatic across all call stacks on a request thread, JSON output is machine-parseable in Coolify's log viewer, existing `logger.info("msg")` call sites need no changes, and `make_filtering_bound_logger` keeps the interface identical to stdlib.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From repo root (adjust to your workspace)
git status                                        # Flag any unrelated M/?? entries
git diff HEAD -- api/create_app.py api/modules/  # Confirm target files are clean
cd api && python -m pytest --tb=no -q            # Baseline — record the passing count

# Identify every file that currently imports stdlib logging
grep -rn "^import logging\|logging\.getLogger" api/ \
  --include="*.py" \
  --exclude-dir=__pycache__ \
  --exclude-dir=tests
```

The grep output is your authoritative migration list for Step 5. Save it; the guide lists the expected files below but the grep output wins if reality diverges.

**If working tree is dirty on target files**: stash or commit unrelated changes separately before starting.

**Baseline recorded**: 624 / 624 passing (1 skipped; web-root check).

---

## 3. Files

### To Create (new)

- `api/modules/observability/__init__.py` — package init; re-exports `configure_logging` and `bind_request_id` as the public interface
- `api/modules/observability/logging.py` — `configure_logging()` and `bind_request_id()`; the only file in the project that calls `structlog.configure()`
- `api/modules/observability/tests/__init__.py` — empty package marker
- `api/modules/observability/tests/test_logging.py` — unit tests for both public functions

### To Modify (cite CODEBASE CONTEXT)

- `api/requirements.txt` — add `structlog>=24.1.0`
- `api/create_app.py` (app factory, CODEBASE CONTEXT) — add `configure_logging()` call as first line of factory; register `bind_request_id` as `before_request` hook
- All modules identified by the pre-flight grep — replace `import logging` + `logging.getLogger(__name__)` with `import structlog` + `structlog.get_logger(__name__)`; expected set (verify against grep output):
  - `api/modules/ai/routes.py`
  - `api/modules/chain/adapter.py`
  - `api/modules/chain/providers/cli.py`
  - `api/modules/context/routes.py`
  - `api/modules/context/service.py`
  - `api/modules/projects/service.py`
  - `api/modules/task_gen/routes.py`
  - `api/modules/task_gen/service.py`
  - `api/modules/workflows/runtime.py`
  - `api/modules/spec_gen/` (any file in this module using logging)
  - `api/modules/implementation_guide/` (any file in this module using logging)

### To Leave Alone

- `api/openapi.yaml` — no new API endpoints; Task 1 has no HTTP surface
- `api/dtos/models.py` — generated artifact; `make check-dtos` must still pass unchanged
- `api/modules/observability/sentry.py` — does not exist yet; Task 2 scope
- `api/modules/observability/errors.py` — does not exist yet; Task 2 scope
- `api/modules/observability/health.py` — does not exist yet; Task 3 scope
- `api/tests/` structural tests — no blueprint or OpenAPI changes; all existing structural tests must remain green

---

## 4. Implementation Steps

### Step 1: Add `structlog` to requirements

**Action**: Append `structlog>=24.1.0` to the requirements file. Do not pin to an exact version — the floor is sufficient for `contextvars` support and `make_filtering_bound_logger`.

**File**: `api/requirements.txt` (CODEBASE CONTEXT)

**Pattern**:
```text
# --- existing entries unchanged above ---
structlog>=24.1.0
```

**Verify**:
```bash
cd api && pip install -r requirements.txt
python -c "import structlog; print(structlog.__version__)"
```
Expect: version string ≥ 24.1.0 printed with no import error.

---

### Step 2: Create the observability package and `logging.py`

**Action**: Create the package directory, the `logging.py` module, and the `__init__.py`. `logging.py` owns exactly two public functions: `configure_logging` (called once at app startup) and `bind_request_id` (called once per request via `before_request`).

> **Naming note**: `logging.py` inside a package is safe in Python 3 because `import logging` resolves to the stdlib absolute import, not to the local file. Do not rename the file; the architecture contract names it explicitly.

**File**: `api/modules/observability/logging.py` (new)

**Pattern**:
```python
"""
Structured logging — configure once at startup, bind per-request.

Public API
----------
configure_logging()  — call once in create_app(), before any logger is used.
bind_request_id()    — call from before_request hook; returns the new UUID string.
"""
import logging
import uuid

import structlog


_SHARED_PROCESSORS: list = [
    structlog.contextvars.merge_contextvars,      # injects request_id (and any other bound vars)
    structlog.stdlib.add_log_level,               # adds "level": "info"
    structlog.stdlib.add_logger_name,             # adds "logger": "modules.task_gen.service"
    structlog.processors.TimeStamper(fmt="iso"),  # adds "timestamp": "2026-04-26T..."
    structlog.processors.StackInfoRenderer(),     # renders stack_info kwarg if present
    structlog.processors.format_exc_info,         # renders exc_info kwarg as string (needed by Task 2)
    structlog.processors.JSONRenderer(),          # final JSON line to stdout
]


def configure_logging() -> None:
    """Configure structlog for JSON-to-stdout output.

    Idempotent — safe to call multiple times (test suite, factory reloads).
    Must be called before any structlog logger is first used; once a logger
    is cached (cache_logger_on_first_use=True) reconfiguration has no effect
    on that logger.
    """
    structlog.configure(
        processors=_SHARED_PROCESSORS,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_request_id() -> str:
    """Clear stale context vars and bind a fresh UUID4 as request_id.

    Must be called from a Flask before_request hook so that every log event
    emitted during the request carries the same request_id automatically via
    merge_contextvars.

    Returns the new request_id string (UUID4 canonical form, 36 chars).
    Callers that need to forward the ID (e.g. response headers) can use
    the return value; other callers may discard it.
    """
    req_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()           # flush stale state from reused gthread
    structlog.contextvars.bind_contextvars(request_id=req_id)
    return req_id
```

**File**: `api/modules/observability/__init__.py` (new)

**Pattern**:
```python
from modules.observability.logging import bind_request_id, configure_logging

__all__ = ["configure_logging", "bind_request_id"]
```

**File**: `api/modules/observability/tests/__init__.py` (new — empty file)

**Verify**:
```bash
cd api && python -c "from modules.observability import configure_logging, bind_request_id; print('ok')"
```
Expect: `ok` with no import error.

---

### Step 3: Wire `configure_logging` and the `before_request` hook into `create_app.py`

**Action**: In `create_app.py`, import and call `configure_logging()` as the first statement in the factory function body (before any `Flask(...)` call). Register `bind_request_id` as a `before_request` hook immediately after the Flask app is instantiated. The `configure_logging()` call must precede all other initialisation so that any logger used during blueprint registration emits structured JSON.

**File**: `api/create_app.py` (CODEBASE CONTEXT — app factory)

**Pattern**:
```python
from modules.observability import configure_logging, bind_request_id

def create_app():
    configure_logging()          # ① structlog first — before any logger is used

    app = Flask(__name__)

    @app.before_request
    def _bind_request_id():
        bind_request_id()        # ② fresh request_id on every request

    # ... existing blueprint registrations, config loading, etc. unchanged below
```

**Verify**:
```bash
cd api && python -c "from create_app import create_app; app = create_app(); print('ok')"
```
Expect: `ok`; JSON log lines (if any init-time logging exists) written to stdout; no exceptions.

---

### Step 4: Migrate all modules from stdlib logger to structlog

**Action**: For every file identified by the pre-flight grep, apply the two-line mechanical substitution below. **Call sites are unchanged** — `logger.info(...)`, `logger.error(...)`, `logger.warning(...)`, `logger.debug(...)`, and `logger.exception(...)` all work identically on a `structlog` bound logger. Do not touch any logic, only the import and logger construction lines.

**Files**: all files from Step 5 pre-flight grep (CODEBASE CONTEXT; expected list in §3)

**Pattern** — the only change per file:
```python
# BEFORE (remove these two lines)
import logging
logger = logging.getLogger(__name__)

# AFTER (replace with these two lines)
import structlog
logger = structlog.get_logger(__name__)
```

If a file imports `logging` for constants other than `getLogger` (e.g., `logging.INFO`, `logging.WARNING`), keep the `import logging` line for those constants and add `import structlog` alongside it:

```python
# BEFORE
import logging
logger = logging.getLogger(__name__)
# ... uses logging.WARNING elsewhere in the same file

# AFTER
import logging                           # keep — still needed for logging.WARNING constant
import structlog
logger = structlog.get_logger(__name__)
```

**Verify** after all files are updated:
```bash
# Confirm no file outside tests still uses getLogger
grep -rn "logging\.getLogger" api/ --include="*.py" --exclude-dir=__pycache__
```
Expect: zero matches. Any remaining match is a file missed in the migration.

```bash
# Confirm structlog is now the logger in each migrated module
grep -rn "structlog\.get_logger" api/modules/ --include="*.py" --exclude-dir=__pycache__
```
Expect: one match per previously-migrated file.

---

### Step 5: Write and run the tests

**Action**: Create the test file (full body in §5 below). Run the test file in isolation to confirm all new tests pass before running the full suite.

**File**: `api/modules/observability/tests/test_logging.py` (new)

**Pattern**: see §5 for the complete file.

**Verify**:
```bash
cd api && python -m pytest modules/observability/tests/ -v
```
Expect: 7 passed, 0 failed, 0 errors.

```bash
cd api && python -m pytest --tb=short -q
```
Expect: 631 passed, 1 skipped. Zero pre-existing failures.

---

## 5. Tests

The repo uses `pytest` (confirmed: `make test` → `python -m pytest` from `api/`). Tests live in `modules/*/tests/`. No fixtures are needed for these pure unit tests.

```python
# api/modules/observability/tests/test_logging.py
"""Unit tests for modules.observability.logging."""
import uuid

import structlog
import pytest
from structlog.contextvars import bind_contextvars, clear_contextvars, get_contextvars

from modules.observability.logging import bind_request_id, configure_logging


class TestConfigureLogging:
    """configure_logging() must be safe to call at startup and idempotently thereafter."""

    def test_configure_does_not_raise(self):
        """Calling configure_logging() once must not raise."""
        configure_logging()  # should complete silently

    def test_configure_is_idempotent(self):
        """Calling configure_logging() twice must not raise or corrupt the logger chain."""
        configure_logging()
        configure_logging()
        log = structlog.get_logger(__name__)
        # Logging a line must not raise even after double-configure
        log.info("idempotency_check", step="test")

    def test_get_logger_returns_usable_logger(self):
        """structlog.get_logger() must return a non-None bound logger after configure."""
        configure_logging()
        log = structlog.get_logger(__name__)
        assert log is not None


class TestBindRequestId:
    """bind_request_id() must set a fresh UUID4 in structlog context vars each call."""

    def setup_method(self):
        configure_logging()
        clear_contextvars()

    def teardown_method(self):
        clear_contextvars()

    def test_sets_request_id_key_in_context(self):
        """After bind_request_id(), context vars must contain 'request_id'."""
        bind_request_id()
        ctx = get_contextvars()
        assert "request_id" in ctx, "request_id must be present in structlog context vars"

    def test_request_id_is_valid_uuid4(self):
        """The stored request_id must be a valid UUID version 4."""
        bind_request_id()
        raw = get_contextvars()["request_id"]
        parsed = uuid.UUID(raw)          # raises ValueError if malformed
        assert parsed.version == 4, f"Expected UUID4, got version {parsed.version}"

    def test_returns_request_id_string(self):
        """Return value must match the value stored in context vars."""
        returned = bind_request_id()
        stored = get_contextvars()["request_id"]
        assert returned == stored, "Return value must equal the context-var value"
        assert len(returned) == 36, f"UUID canonical form is 36 chars; got {len(returned)}"

    def test_clears_previous_context_vars(self):
        """bind_request_id() must evict stale keys from a previously used thread context."""
        bind_contextvars(stale_key="stale_value", another_key=42)
        bind_request_id()
        ctx = get_contextvars()
        assert "stale_key" not in ctx, "stale_key must be cleared by bind_request_id()"
        assert "another_key" not in ctx, "another_key must be cleared by bind_request_id()"
        assert "request_id" in ctx, "request_id must be present after clearing"

    def test_successive_calls_produce_unique_ids(self):
        """Two consecutive bind_request_id() calls must yield different UUIDs."""
        id_a = bind_request_id()
        id_b = bind_request_id()
        assert id_a != id_b, "Each call must generate a distinct request_id"
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end of the task.

1. `chore(deps): add structlog>=24.1.0 to requirements` — after **Step 1** — `api/requirements.txt`: adds structlog dependency

2. `feat(observability): add logging module with configure_logging and bind_request_id` — after **Step 2** — `api/modules/observability/__init__.py`, `api/modules/observability/logging.py`, `api/modules/observability/tests/__init__.py`: new package + public API

3. `feat(observability): wire configure_logging and before_request hook into create_app` — after **Step 3** — `api/create_app.py`: structlog initialised before app creation; request_id bound per request

4. `refactor(modules): migrate stdlib logger to structlog across all feature modules` — after **Step 4** — all migrated module files: `import logging` + `getLogger` replaced by `import structlog` + `get_logger`; call sites unchanged

5. `test(observability): unit tests for configure_logging and bind_request_id` — after **Step 5** (all 7 tests passing) — `api/modules/observability/tests/test_logging.py`: full assertion bodies, no stubs

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation (e.g., `Deviations: modules/spec_gen/routes.py used logging.WARNING constant; kept import logging alongside structlog`).

---

## 7. Verification

```bash
cd api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → **631** passing (7 new tests in `modules/observability/tests/test_logging.py`). Zero pre-existing tests broken. The 1 skipped test (web-root check) remains skipped.

```bash
# Confirm no stdlib getLogger remains outside tests and generated DTOs
grep -rn "logging\.getLogger" api/ \
  --include="*.py" \
  --exclude-dir=__pycache__ \
  --exclude="dtos/models.py"
```
Expect: zero matches.

```bash
# Confirm DTOs have not drifted (structural CI gate)
cd api && make check-dtos
```
Expect: `OK` — no changes to `openapi.yaml` or `dtos/models.py` in this task.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>    # creates a new revert commit; does not rewrite history
  ```
- **Per-branch**: if verification fails catastrophically after multiple commits, reset to the pre-task SHA:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — discards all Task 1 commits
  ```
  Identify the pre-task SHA before starting: `git rev-parse HEAD` and record it in your notes.

---

## 9. Deviations Allowed

- **A module uses `logging.WARNING` / `logging.INFO` constants in its own logic** — keep `import logging` for the constant and add `import structlog` alongside it; update only the `logger = ...` line. Log the deviation in the commit body.
- **`structlog.stdlib.add_logger_name` produces unexpected output in tests** — if frame-inspection returns a structlog-internal module name instead of the caller's, replace `add_logger_name` with a custom processor `lambda _, __, ed: {**ed}` (no-op) and log the deviation. Do not remove it silently.
- **A module uses `logger.exception(msg)` with `exc_info` already set explicitly** — structlog's `exception()` method works the same way; no change needed.
- **Pre-flight grep reveals a module not listed in §3** — include it in Step 4 and add it to the Step 4 commit. Do not defer it.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log deviation in commit.
- **Side-effect required** (pip publish, git push, schema change) — STOP, mark **[REQUIRES APPROVAL]** and ask.

---

## 10. Out of Scope

This task establishes the logging foundation only — the processor chain, the `request_id` context variable, and the mechanical migration of existing modules. Everything that *uses* that foundation (Sentry event capture, JSON error handlers, the health blueprint, per-user `user_id` injection) is the job of Tasks 2 and 3. An eager executor might see the `modules/observability/` directory and be tempted to stub in the Sentry or health files; do not.

- **`modules/observability/sentry.py`** — Task 2 scope; blocked on `configure_logging` being shipped first (this task)
- **`modules/observability/errors.py`** — Task 2 scope; the `logger.exception("unhandled_exception")` call is pre-wired by including `format_exc_info` in the processor chain here, but the handler itself is Task 2
- **`modules/observability/health.py`** — Task 3 scope; depends on both Task 1 (logger) and Task 2 (error shape); the open question about Anthropic health check via adapter vs SDK direct (Architecture §Open Questions) is a Task 3 decision
- **Per-user `user_id` in log context** — deferred to Phase 1 auth middleware; `bind_request_id()` binds only `request_id` now; `bind_contextvars(user_id=...)` is a one-liner addition when auth middleware lands, no change to `logging.py` required
- **Log destination beyond stdout** — stdout captured by Coolify is the current contract; BetterStack/Logtail upgrade is triggered by the first incident requiring log search across time windows
- **`ng build` CI gate / multi-stage Dockerfile** — Task 4 scope

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale including open question on Anthropic health check adapter boundary
- [Epic](./epic.md) — full task list; Tasks 2 and 3 are unblocked when this task's PR merges
- [Timeline](./timeline.md) — update Task 1 status to ✅ Done after `git push` and PR merge