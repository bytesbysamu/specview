"""Unit tests for the CallableRegistry."""
from __future__ import annotations

import pytest

from modules.runtime.workflows.steps.registry import CallableRegistry

# Bind module-level helpers via a class namespace to avoid pytest's *_* collection
# rule picking up module-level functions that contain underscores.
register = CallableRegistry.register
get = CallableRegistry.get
clear = CallableRegistry.clear
registerCompute = CallableRegistry.register_compute
registeredNames = CallableRegistry.registered_names

# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


def register_addsCallableByName():
    def fn(context):
        return "result"

    register("my-fn", fn)
    assert get("my-fn") is fn, "get() must return the exact object that was registered"


def register_duplicateName_raisesValueError():
    def fn(context):
        return "a"

    register("dup", fn)
    with pytest.raises(ValueError, match="dup"):
        register("dup", fn)


def register_nonCallable_raisesTypeError():
    with pytest.raises(TypeError, match="callable"):
        register("bad", "not-a-function")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


def get_unknownName_raisesKeyError():
    with pytest.raises(KeyError, match="unknown-fn"):
        get("unknown-fn")


def get_afterClear_raisesKeyError():
    register("temp", lambda c: None)
    clear()
    with pytest.raises(KeyError):
        get("temp")


# ---------------------------------------------------------------------------
# registeredNames()
# ---------------------------------------------------------------------------


def registeredNames_returnsAlphabeticallySortedNames():
    register("zebra", lambda c: None)
    register("alpha", lambda c: None)
    names = registeredNames()
    assert names == ["alpha", "zebra"], f"expected alphabetical order, got {names}"


def registeredNames_emptyRegistry_returnsEmptyList():
    assert registeredNames() == [], "fresh registry must be empty"


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


def clear_removesAllEntries():
    register("temp", lambda c: None)
    clear()
    assert registeredNames() == [], "clear() must empty the registry"


# ---------------------------------------------------------------------------
# registerCompute() decorator
# ---------------------------------------------------------------------------


def registerCompute_decoratorRegistersFunction():
    @registerCompute("decorated-fn")
    def my_fn(context):
        return context.inputs.get("x", 0) * 2

    assert get("decorated-fn") is my_fn, "decorator must register the function by name"


def registerCompute_decoratorPreservesCallableIdentity():
    from modules.runtime.workflows.steps.base import StepContext

    @registerCompute("passthrough")
    def passthrough(context):
        return context.inputs

    # The decorated function must still be directly callable
    result = passthrough(StepContext(run_id="r", inputs={"k": "v"}))
    assert result == {"k": "v"}, "decorator must return the original function unchanged"


# ---------------------------------------------------------------------------
# CallableRegistry class namespace
# ---------------------------------------------------------------------------


def callableRegistry_classMethods_delegateToModuleFunctions():
    """CallableRegistry class-level API must be a transparent wrapper."""

    def fn(c):
        return "ok"

    CallableRegistry.register("cls-test", fn)
    assert CallableRegistry.get("cls-test") is fn, (
        "CallableRegistry.get() must find what CallableRegistry.register() stored"
    )
    assert "cls-test" in CallableRegistry.registered_names(), "cls-test must appear in registered_names()"
