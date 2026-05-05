"""Verify per-step model routing on the bootstrap-project workflow.

Network is never touched — the assertions read AICall step attributes
directly. Cost reduction itself is verified manually via /api/ai/stats.
"""
from __future__ import annotations

from modules.ai.workflows.spec_gen import bootstrap as _bootstrap_module

bootstrap_workflow = _bootstrap_module._build_workflow()


def findStep(step_name: str):
    for s in bootstrap_workflow.steps:
        if s.name == step_name:
            return s
    raise AssertionError(f"step {step_name!r} missing from bootstrap_workflow")


def test_analysisfindStep_uses_haiku_for_cost():
    assert findStep("analysis").model == "claude-haiku-4-5"


def test_epicfindStep_uses_sonnet_explicitly():
    assert findStep("epic").model == "claude-sonnet-4-5"


def test_architecturefindStep_uses_opus_for_quality():
    assert findStep("architecture").model == "claude-opus-4-7"


def test_all_workflow_models_are_priced_in_adapter():
    """Catches drift: every model used by the workflow must have a price entry.

    Skipped until Task 3 merges _PRICING into modules/runtime/chain/adapter.py.
    Once available, this test pins workflow models to priced entries so an
    unpriced model cannot ship silently.
    """
    import pytest

    from modules.runtime.chain import adapter
    pricing = getattr(adapter, "_PRICING", None)
    if pricing is None:
        pytest.skip("_PRICING not yet present in adapter (depends on Task 3)")
    used_models = {s.model for s in bootstrap_workflow.steps if hasattr(s, "model")}
    missing = used_models - set(pricing)
    assert missing == set(), (
        f"Workflow uses models with no _PRICING entry: {missing}. "
        f"Add them to modules/runtime/chain/adapter.py:_PRICING."
    )
