"""Callable registry for Compute steps — ELA Pattern #27 (Registry).

Only named, pre-registered callables are legal. No eval, no anonymous dispatch.
Registered callables must have the signature: fn(context: StepContext) -> Any.
The callable reads ``context.inputs`` and ``context.outputs`` and returns any
JSON-serialisable value.

This module exposes both standalone functions and a ``CallableRegistry`` namespace
class (useful for dependency-injection in tests without re-importing each function).
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_registry: dict[str, Callable[..., Any]] = {}


# ---------------------------------------------------------------------------
# Module-level API
# ---------------------------------------------------------------------------


def register(name: str, fn: Callable[..., Any]) -> None:
    """Register *fn* under *name*.

    Raises
    ------
    TypeError   if *fn* is not callable.
    ValueError  if *name* is already registered (prevents silent overwrites).
    """
    if not callable(fn):
        raise TypeError(
            f"Expected a callable for {name!r}, got {type(fn).__name__}"
        )
    if name in _registry:
        raise ValueError(
            f"Callable {name!r} is already registered. "
            "Choose a unique name or call clear() between registrations (tests only)."
        )
    _registry[name] = fn
    logger.debug("registered compute callable %r", name)


def get(name: str) -> Callable[..., Any]:
    """Return the callable registered under *name*.

    Raises
    ------
    KeyError  if *name* has no registration.
    """
    if name not in _registry:
        raise KeyError(
            f"No callable registered under {name!r}. "
            f"Registered names: {sorted(_registry)}"
        )
    return _registry[name]


def registered_names() -> list[str]:
    """Return a sorted list of all registered callable names."""
    return sorted(_registry.keys())


def clear() -> None:
    """Remove all registrations.

    Call only from test teardown (autouse fixture in conftest.py).
    Never call in production code — there is no undo.
    """
    _registry.clear()


def register_compute(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: register a function as a named Compute step callable.

    Usage::

        @register_compute("format-output")
        def format_output(context: StepContext) -> str:
            return context.inputs["text"].strip()

    The decorated function is returned unchanged so it remains importable and
    directly callable in Python workflows.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        register(name, fn)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Namespace class — thin wrapper for dependency-injection scenarios
# ---------------------------------------------------------------------------


class CallableRegistry:
    """Class-level namespace mirroring the module-level functions.

    Prefer the module-level functions in production code.  This class exists
    so tests can inject the registry as a single object without importing each
    function separately.
    """

    register = staticmethod(register)
    get = staticmethod(get)
    registered_names = staticmethod(registered_names)
    clear = staticmethod(clear)
    register_compute = staticmethod(register_compute)
