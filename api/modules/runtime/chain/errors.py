"""Provider-layer failure — ported from references.md:347–350."""
from __future__ import annotations


class ProviderError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
