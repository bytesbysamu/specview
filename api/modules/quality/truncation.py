"""Pure-function heuristics that flag malformed step output.

Each heuristic returns a warning string (or None). The public
``detect_truncation`` function fans them out and returns the non-empty
list. Callers append the result to ``WorkflowExecution.warnings``.

Composes with the lint and coherence helpers already in
``modules.quality``; future quality checks (structural, citation) can
add new heuristics here without changing the call site.
"""
from __future__ import annotations

_MIN_REASONABLE_LENGTH = 200


def _odd_triple_backticks(text: str) -> str | None:
    fence_count = text.count("```")
    if fence_count % 2 == 1:
        return f"unclosed_code_fence: {fence_count} triple-backticks (odd)"
    return None


def _too_short(text: str, max_tokens: int) -> str | None:
    if max_tokens >= 4096 and len(text) < _MIN_REASONABLE_LENGTH:
        return (
            f"suspiciously_short: {len(text)} chars with max_tokens={max_tokens}"
        )
    return None


def _missing_terminal_newline(text: str) -> str | None:
    if text and not text.endswith("\n"):
        return "missing_terminal_newline"
    return None


def detect_truncation(text: str, *, max_tokens: int = 4096) -> list[str]:
    """Return a list of warning strings for each heuristic that fired.

    Empty list means no warnings detected. Callers extend
    ``WorkflowExecution.warnings`` with the result.
    """
    warnings: list[str] = []
    for fn in (
        lambda: _odd_triple_backticks(text),
        lambda: _too_short(text, max_tokens),
        lambda: _missing_terminal_newline(text),
    ):
        warning = fn()
        if warning is not None:
            warnings.append(warning)
    return warnings
