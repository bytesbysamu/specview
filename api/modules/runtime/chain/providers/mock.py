"""Deterministic mock provider — ported verbatim from references.md:227–261."""
from __future__ import annotations

from typing import Iterator


def create_message(
    system: str, prompt: str, *, model: str = "mock", max_tokens: int = 4096
) -> tuple[str, None, None]:
    """Deterministic stub. Returns ``(text, None, None)`` — no usage data."""
    return f"MOCK[{model}]::sys={system[:20]}::prompt={prompt[:40]}", None, None


def stream_message(system: str, prompt: str, *, model: str = "mock", max_tokens: int = 4096) -> Iterator[str]:
    yield f"MOCK[{model}]"
    yield "::"
    yield f"sys={system[:20]}"
    yield "::"
    yield f"prompt={prompt[:40]}"


def stream_generate(*, system: str, prompt: str, model: str = "mock", max_tokens: int = 4096) -> Iterator[str]:
    """Deterministic streaming stub for tests of AICall(stream=True)."""
    yield f"MOCK[{model}]"
    yield "::"
    yield f"sys={system[:20]}"
    yield "::"
    yield f"prompt={prompt[:40]}"
