"""Test fixtures scoped to modules/workflows/tests/.

autouse clear_callable_registry ensures every test starts with an empty
registry and leaves none of its registrations behind, regardless of whether
the test passes or raises.  This is the correct isolation mechanism for
module-level global state.
"""
from __future__ import annotations

import pytest

from modules.runtime.workflows.steps import registry


@pytest.fixture(autouse=True)
def clear_callable_registry():
    """Reset the CallableRegistry before and after every test in this directory."""
    registry.clear()
    yield
    registry.clear()
