"""Prompt context assembly — adapted from references.md:363–376.

Spec-doc adaptation: accepts plain strings for builder and principles,
not Bubls user objects. Context injection happens at the adapter boundary only.
"""
from __future__ import annotations


def with_context(system: str, builder: str = "", principles: str = "") -> str:
    """Prepend builder profile and principles to system prompt if provided."""
    parts = [system]
    if builder:
        parts.append(f"\n\n## BUILDER CONTEXT\n{builder}")
    if principles:
        parts.append(f"\n\n## PRINCIPLES\n{principles}")
    return "".join(parts)
