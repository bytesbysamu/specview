# modules/ai/prompts/builder.py
"""Fluent prompt assembler.

PromptBuilder accumulates named sections and joins them in declaration order.
No I/O. No side effects. Call build() to get the final string.

Usage:
    system = (
        PromptBuilder("You are a spec writer.")
        .section("Builder Profile", builder_ctx)
        .section("Principles", principles_ctx)
        .build()
    )
"""
from __future__ import annotations


class PromptBuilder:
    """Accumulate prompt sections and produce a plain string via build()."""

    def __init__(self, base: str = "") -> None:
        self._parts: list[str] = [base] if base else []

    def section(self, heading: str, content: str) -> "PromptBuilder":
        """Append ``## heading\\ncontent`` block. No-op when content is blank."""
        if content and content.strip():
            self._parts.append(f"\n\n## {heading}\n{content}")
        return self

    def raw(self, text: str) -> "PromptBuilder":
        """Append raw text without a heading wrapper. No-op when text is empty."""
        if text:
            self._parts.append(text)
        return self

    def build(self) -> str:
        """Return the assembled string."""
        return "".join(self._parts)
