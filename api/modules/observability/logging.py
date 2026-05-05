"""Structured logging — configure structlog once at startup.

Public API
----------
init_logging()  — call once from `create_app()` before any logger is used.

Design (locked)
---------------
- Output is JSON (one event per line) via `structlog.processors.JSONRenderer`.
- `request_id` (and `user_id`, when auth middleware lands) flow automatically
  via `structlog.contextvars`. Future middleware will call
  `structlog.contextvars.bind_contextvars(request_id=..., user_id=...)`
  inside a Flask `before_request` hook; this module does not own that
  binding — it only ensures the keys are surfaced on every event.
- The level threshold is read from the `LOG_LEVEL` env var (default `INFO`)
  and applied via `make_filtering_bound_logger` so below-threshold calls
  are discarded cheaply.
- Module pattern at every call site:
      import structlog
      logger = structlog.get_logger(__name__)
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, MutableMapping, TextIO

import structlog


_LEVEL_NAMES: dict[str, int] = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def _resolve_log_level(raw: str | None) -> int:
    """Map a LOG_LEVEL env-var string to a stdlib logging level int.

    Unknown / empty values fall back to INFO — operational tooling should
    never crash a process for a typo'd log level.
    """
    if not raw:
        return logging.INFO
    return _LEVEL_NAMES.get(raw.strip().upper(), logging.INFO)


class _NamedPrintLoggerFactory:
    """PrintLoggerFactory variant that preserves the logger name.

    structlog's stock `PrintLoggerFactory` discards the name passed via
    `structlog.get_logger(__name__)`, which breaks `add_logger_name`
    (it reads `logger.name`). This factory stores the first positional
    argument as `.name` on the produced PrintLogger so the `logger`
    field appears in JSON output as expected.
    """

    def __init__(self, file: TextIO | None = None) -> None:
        self._file = file

    def __call__(self, *args: Any) -> structlog.PrintLogger:
        logger = structlog.PrintLogger(self._file or sys.stdout)
        # Stamp the caller-provided name (e.g. __name__) for add_logger_name.
        logger.name = args[0] if args else ""
        return logger


def _add_request_context(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Surface `request_id` / `user_id` on every event when present.

    `merge_contextvars` (run earlier in the chain) already copies any keys
    bound via `structlog.contextvars.bind_contextvars` into `event_dict`.
    This processor exists as a stable hook so future enrichment (tenant_id,
    trace_id, etc.) lands in one well-named place rather than scattered
    through the chain. Missing keys are tolerated — pre-middleware events
    (startup, CLI calls) simply omit them.
    """
    ctx = structlog.contextvars.get_contextvars()
    request_id = ctx.get("request_id")
    if request_id is not None and "request_id" not in event_dict:
        event_dict["request_id"] = request_id
    user_id = ctx.get("user_id")
    if user_id is not None and "user_id" not in event_dict:
        event_dict["user_id"] = user_id
    return event_dict


def init_logging() -> None:
    """Configure structlog for JSON-to-stdout output.

    Idempotent — safe to re-invoke (test suites, factory reloads). The level
    threshold comes from the `LOG_LEVEL` env var and is resolved at every
    call so test cases can mutate the env and re-init.
    """
    level = _resolve_log_level(os.environ.get("LOG_LEVEL"))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            _add_request_context,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=_NamedPrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
