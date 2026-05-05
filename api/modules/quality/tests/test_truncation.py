"""Tests for the truncation heuristic helper used by Task 4 (saas-reliability).

Each heuristic is verified in isolation; the public ``detect_truncation``
function fans out and aggregates the warnings list.

Naming convention (matches modules/quality/tests/test_lint.py):
    pyproject.toml sets python_functions = ["test_*", "*_*"]; module-level
    helpers and re-exports must be camelCase (no underscores) so they are
    not collected as tests. The alias below replaces the snake_case import
    with a collection-safe name.
"""
from __future__ import annotations

from modules.quality import truncation as _truncation

# Alias without underscores avoids test collection of the function definition.
detectTruncation = _truncation.detect_truncation


def detectTruncation_unclosedCodeFence_emitsWarning():
    text = "```python\nprint('x')\n"  # one opening fence, no closing
    warnings = detectTruncation(text, max_tokens=4096)
    assert any("unclosed_code_fence" in w for w in warnings), (
        f"Expected unclosed_code_fence warning; got {warnings}"
    )


def detectTruncation_balancedCodeFences_emitsNoFenceWarning():
    text = "```python\nprint('x')\n```\n"
    warnings = detectTruncation(text, max_tokens=4096)
    assert not any("unclosed_code_fence" in w for w in warnings), (
        f"Balanced fences must not warn; got {warnings}"
    )


def detectTruncation_shortOutputAtHighMaxTokens_emitsSuspiciouslyShort():
    text = "tiny output\n"  # < 200 chars with max_tokens=16384
    warnings = detectTruncation(text, max_tokens=16384)
    assert any("suspiciously_short" in w for w in warnings), (
        f"Expected suspiciously_short warning; got {warnings}"
    )


def detectTruncation_shortOutputAtLowMaxTokens_emitsNoShortWarning():
    text = "tiny output\n"
    warnings = detectTruncation(text, max_tokens=512)
    assert not any("suspiciously_short" in w for w in warnings), (
        f"Low max_tokens must not flag short output; got {warnings}"
    )


def detectTruncation_missingTerminalNewline_emitsWarning():
    text = "no trailing newline"
    warnings = detectTruncation(text, max_tokens=4096)
    assert any("missing_terminal_newline" in w for w in warnings), (
        f"Expected missing_terminal_newline warning; got {warnings}"
    )


def detectTruncation_cleanLongOutput_emitsEmptyList():
    text = ("clean line\n" * 100)  # >> 200 chars, balanced (no fences), trailing \n
    warnings = detectTruncation(text, max_tokens=16384)
    assert warnings == [], f"Clean output must not warn; got {warnings}"
