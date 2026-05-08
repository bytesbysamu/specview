"""Deterministic mock provider for tests.

Returns valid JSON that satisfies every skill's output_schema so the full
request path (route → run_skill → parse_and_validate) works end-to-end with
CHAIN_PROVIDER=mock and no real AI calls.

Schema coverage:
  {"text": "..."}                   — all 8 action skills (expand, compress, …)
  {"scores": {}, "issues": []}      — review skill
  {"status": "...", "files": []}    — spec-pipeline skill
"""
from __future__ import annotations

import json
from typing import Iterator

# Superset response: satisfies required fields of every known skill schema.
_MOCK_PAYLOAD = json.dumps({
    "text": "Mock AI output for testing.",
    "scores": {},
    "issues": [],
    "status": "complete",
    "files": [],
})


def create_message(
    system: str, prompt: str, *, model: str = "mock", max_tokens: int = 4096
) -> tuple[str, None, None]:
    """Return deterministic JSON. No usage data."""
    return _MOCK_PAYLOAD, None, None


def stream_message(
    system: str, prompt: str, *, model: str = "mock", max_tokens: int = 4096
) -> Iterator[str]:
    yield _MOCK_PAYLOAD


def stream_generate(
    *, system: str, prompt: str, model: str = "mock", max_tokens: int = 4096
) -> Iterator[str]:
    yield _MOCK_PAYLOAD
