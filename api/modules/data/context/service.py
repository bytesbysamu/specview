from __future__ import annotations

import logging

from config import CONTEXT_PATHS  # single source of truth; honors SPEC_DOC_DIR env var

from .errors import ContextReadError

logger = logging.getLogger(__name__)


def read_context(key: str) -> str:
    """Return file content or '' if the file does not exist."""
    path = CONTEXT_PATHS[key]
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as exc:
        logger.error("Error reading %s: %s", key, exc)
        return ""


def write_context(key: str, content: str) -> None:
    """Overwrite the context file. Raises ContextReadError on I/O failure."""
    try:
        CONTEXT_PATHS[key].write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ContextReadError(str(exc)) from exc
    logger.info("[Context] %s updated (%d chars)", key, len(content))
