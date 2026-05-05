"""Domain exceptions for the AI module."""
from __future__ import annotations


class AIProviderError(Exception):
    """Feature-layer signal that the AI provider failed.
    Translated from chain.errors.ProviderError at the route boundary.
    """
