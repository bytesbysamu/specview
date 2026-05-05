"""Domain exceptions for the context module."""
from __future__ import annotations


class ContextReadError(OSError):
    """Raised when a context file cannot be written.
    Subclasses OSError so existing except OSError clauses in routes catch it.
    """
