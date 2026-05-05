"""Domain-level return types (ACL) — ported from references.md:347–362."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ChainResult:
    text: str
    latency_ms: int
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None


@dataclass(frozen=True)
class ReviewResult:
    scores: dict[str, float]
    issues: list[str]
    raw: str
