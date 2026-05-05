"""Unit tests for modules.observability.logging.

Coverage targets:
  - initLogging() runs without raising and is idempotent
  - JSON output shape (parsable, expected keys present)
  - request_id / user_id propagation via structlog.contextvars
  - LOG_LEVEL env-var driven level filtering
  - _add_request_context behaviour with and without bound context
"""

from __future__ import annotations

import json
import logging

import pytest
import structlog
from structlog import contextvars as _ctxvars

from modules.observability import logging as obs_logging

# Local rebindings use camelCase to dodge pytest's
# `python_functions = ["test_*", "*_*"]` collection rule, which would
# otherwise treat each imported helper as a test function and try to run it.
initLogging = obs_logging.init_logging
addRequestContext = obs_logging._add_request_context
resolveLogLevel = obs_logging._resolve_log_level
bindContextvars = _ctxvars.bind_contextvars
clearContextvars = _ctxvars.clear_contextvars
getContextvars = _ctxvars.get_contextvars


# --------------------------------------------------------------------------- #
# Shared fixture: clear context vars and re-init logging around every test so #
# global structlog state never leaks between cases.                           #
# --------------------------------------------------------------------------- #
@pytest.fixture(autouse=True)
def _isolated_structlog_state(monkeypatch):
    clearContextvars()
    # Ensure tests do not inherit a stray LOG_LEVEL from the host env.
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    initLogging()
    yield
    clearContextvars()


# --------------------------------------------------------------------------- #
# init_logging — basic invariants                                             #
# --------------------------------------------------------------------------- #
class TestInitLogging:
    def test_init_does_not_raise(self):
        """Bare initLogging() call must complete silently."""
        initLogging()

    def test_init_is_idempotent(self):
        """Re-invoking initLogging() must not corrupt the logger chain."""
        initLogging()
        initLogging()
        log = structlog.get_logger("idempotent.test")
        # An info call after double-configure must still succeed.
        log.info("idempotency_check", step="test")

    def test_get_logger_returns_usable_logger(self):
        """structlog.get_logger() must return a non-None bound logger."""
        log = structlog.get_logger("init.test")
        assert log is not None


# --------------------------------------------------------------------------- #
# _resolve_log_level — env-var parsing                                        #
# --------------------------------------------------------------------------- #
class TestResolveLogLevel:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("DEBUG", logging.DEBUG),
            ("debug", logging.DEBUG),     # case-insensitive
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("WARN", logging.WARNING),    # alias
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
            ("  info  ", logging.INFO),   # whitespace tolerated
        ],
    )
    def test_known_level_strings_map_to_stdlib_ints(self, raw, expected):
        assert resolveLogLevel(raw) == expected

    def test_none_defaults_to_info(self):
        assert resolveLogLevel(None) == logging.INFO

    def test_empty_string_defaults_to_info(self):
        assert resolveLogLevel("") == logging.INFO

    def test_unknown_string_defaults_to_info(self):
        # Operational hardening: a typo'd LOG_LEVEL must not crash startup.
        assert resolveLogLevel("BANANAS") == logging.INFO


# --------------------------------------------------------------------------- #
# _add_request_context — processor behaviour                                  #
# --------------------------------------------------------------------------- #
class TestAddRequestContext:
    def test_missing_context_keys_are_omitted(self):
        """No request_id / user_id bound -> processor leaves event_dict alone."""
        event = {"event": "x"}
        out = addRequestContext(None, "info", dict(event))
        assert "request_id" not in out
        assert "user_id" not in out
        assert out["event"] == "x"

    def test_request_id_from_contextvars_is_added(self):
        bindContextvars(request_id="req-abc")
        # merge_contextvars normally runs first; emulate by passing it pre-merged.
        merged = {"event": "x", "request_id": "req-abc"}
        out = addRequestContext(None, "info", merged)
        assert out["request_id"] == "req-abc"

    def test_explicit_event_value_wins_over_context(self):
        """If the event already has request_id (e.g. caller-supplied), keep it."""
        bindContextvars(request_id="ctx-id")
        out = addRequestContext(None, "info", {"event": "x", "request_id": "explicit"})
        assert out["request_id"] == "explicit"

    def test_user_id_is_propagated_when_present(self):
        bindContextvars(user_id="user-42")
        out = addRequestContext(None, "info", {"event": "x"})
        assert out["user_id"] == "user-42"


# --------------------------------------------------------------------------- #
# JSON output shape — capture stdout and parse                                #
# --------------------------------------------------------------------------- #
class TestJsonRendering:
    def test_emitted_line_is_valid_json(self, capsys):
        log = structlog.get_logger("json.shape.test")
        log.info("hello_event", foo="bar", count=3)
        out = capsys.readouterr().out.strip()
        assert out, "expected at least one log line on stdout"
        last = out.splitlines()[-1]
        parsed = json.loads(last)  # raises if not valid JSON
        assert parsed["event"] == "hello_event"
        assert parsed["foo"] == "bar"
        assert parsed["count"] == 3

    def test_log_event_includes_level_and_logger_and_timestamp(self, capsys):
        log = structlog.get_logger("modules.shape.test")
        log.warning("warn_event")
        last = capsys.readouterr().out.strip().splitlines()[-1]
        parsed = json.loads(last)
        assert parsed["level"] == "warning"
        assert parsed["logger"] == "modules.shape.test"
        assert "timestamp" in parsed
        # ISO8601 timestamps from TimeStamper(fmt="iso") contain a 'T'.
        assert "T" in parsed["timestamp"]


# --------------------------------------------------------------------------- #
# request_id propagation through the full chain                               #
# --------------------------------------------------------------------------- #
class TestRequestIdPropagation:
    def test_bound_request_id_appears_in_log_line(self, capsys):
        bindContextvars(request_id="req-xyz-123")
        log = structlog.get_logger("propagation.test")
        log.info("downstream_event")
        last = capsys.readouterr().out.strip().splitlines()[-1]
        parsed = json.loads(last)
        assert parsed["request_id"] == "req-xyz-123"

    def test_bound_user_id_appears_in_log_line(self, capsys):
        bindContextvars(request_id="req-1", user_id="user-7")
        log = structlog.get_logger("propagation.test")
        log.info("downstream_event")
        parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert parsed["request_id"] == "req-1"
        assert parsed["user_id"] == "user-7"

    def test_unbound_request_id_means_key_absent(self, capsys):
        # No bind_contextvars call — the key must simply not appear.
        log = structlog.get_logger("propagation.test")
        log.info("orphan_event")
        parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert "request_id" not in parsed
        assert "user_id" not in parsed

    def test_clear_contextvars_strips_request_id(self, capsys):
        bindContextvars(request_id="will-be-cleared")
        clearContextvars()
        log = structlog.get_logger("propagation.test")
        log.info("post_clear_event")
        parsed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert "request_id" not in parsed

    def test_context_state_persists_across_loggers(self, capsys):
        """contextvars are process-wide — every logger sees the same request_id."""
        bindContextvars(request_id="shared-req")
        structlog.get_logger("module.a").info("a_event")
        structlog.get_logger("module.b").info("b_event")
        lines = capsys.readouterr().out.strip().splitlines()
        a, b = json.loads(lines[-2]), json.loads(lines[-1])
        assert a["request_id"] == "shared-req"
        assert b["request_id"] == "shared-req"
        assert a["logger"] == "module.a"
        assert b["logger"] == "module.b"


# --------------------------------------------------------------------------- #
# LOG_LEVEL env-var filtering                                                 #
# --------------------------------------------------------------------------- #
class TestLogLevelFiltering:
    def test_default_level_info_drops_debug(self, capsys, monkeypatch):
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        initLogging()
        log = structlog.get_logger("level.test")
        log.debug("debug_should_be_dropped")
        out = capsys.readouterr().out
        assert "debug_should_be_dropped" not in out

    def test_default_level_info_keeps_info(self, capsys, monkeypatch):
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        initLogging()
        log = structlog.get_logger("level.test")
        log.info("info_should_pass")
        out = capsys.readouterr().out
        assert "info_should_pass" in out

    def test_log_level_debug_env_keeps_debug(self, capsys, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        initLogging()
        log = structlog.get_logger("level.test")
        log.debug("debug_kept_when_env_set")
        out = capsys.readouterr().out
        assert "debug_kept_when_env_set" in out

    def test_log_level_warning_drops_info(self, capsys, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        initLogging()
        log = structlog.get_logger("level.test")
        log.info("info_dropped_when_warning_env")
        log.warning("warning_kept")
        out = capsys.readouterr().out
        assert "info_dropped_when_warning_env" not in out
        assert "warning_kept" in out

    def test_log_level_error_drops_warning(self, capsys, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        initLogging()
        log = structlog.get_logger("level.test")
        log.warning("warning_dropped_when_error_env")
        log.error("error_kept")
        out = capsys.readouterr().out
        assert "warning_dropped_when_error_env" not in out
        assert "error_kept" in out

    def test_unknown_log_level_falls_back_to_info(self, capsys, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "BOGUS")
        initLogging()
        log = structlog.get_logger("level.test")
        log.debug("debug_dropped_under_fallback_info")
        log.info("info_kept_under_fallback_info")
        out = capsys.readouterr().out
        assert "debug_dropped_under_fallback_info" not in out
        assert "info_kept_under_fallback_info" in out

    def test_init_logging_re_reads_env_each_call(self, capsys, monkeypatch):
        """A second initLogging() under a new LOG_LEVEL must take effect."""
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        initLogging()
        log = structlog.get_logger("level.reread.test")
        log.info("first_phase_info_dropped")
        # Now widen the level threshold and re-init — info should pass.
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        initLogging()
        log = structlog.get_logger("level.reread.test")
        log.info("second_phase_info_kept")
        out = capsys.readouterr().out
        assert "first_phase_info_dropped" not in out
        assert "second_phase_info_kept" in out


# --------------------------------------------------------------------------- #
# Direct contextvars-API smoke check (no Flask coupling — middleware lands later) #
# --------------------------------------------------------------------------- #
class TestContextVarsIntegration:
    def test_get_contextvars_reflects_binding(self):
        bindContextvars(request_id="r1", user_id="u1")
        ctx = getContextvars()
        assert ctx["request_id"] == "r1"
        assert ctx["user_id"] == "u1"

    def test_clear_contextvars_empties_state(self):
        bindContextvars(request_id="r2")
        clearContextvars()
        assert "request_id" not in getContextvars()
