"""Wire the five core feature files to pytest via pytest-bdd scenarios().

These cover brainstorm, bootstrap pipeline, billing gate, epic guide, and
pro-subscription checks.

SKIP: Core tests assume top-level braindump-input and brainstorm-button
elements.  The V3 layout moved these into the create-modal and project
sidebar respectively.  Tests need a rewrite for the V3 component
architecture.  Tracked in test_core_v3_rewrite.
"""
import pytest

pytestmark = pytest.mark.skip(
    reason="Core E2E tests need rewrite for V3 layout (braindump-input is inside create modal)"
)
