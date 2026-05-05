# modules/implementation_guide/tests/test_impl_guide_prompts_snapshots.py
"""Snapshot tests for build_implementation_guide_prompt().

Run:    pytest -m snapshot
Update: pytest -m snapshot --snapshot-update

Pin the full (system, user) tuple for a representative call. Any future change
to the prompt wording produces a visible, attributable diff against the golden.
"""
import pytest

from modules.ai.prompts import impl_guide as _prompts
# Alias without underscores avoids collection under python_functions=["test_*", "*_*"]
buildPrompt = _prompts.build_implementation_guide_prompt

# Stable minimal inputs — deliberately small; only enough to exercise all sections.
_TASK_NUM = "2"
_TASK_NAME = "Migrate Prompts to Flask"
_TASK_EFFORT = "1.5 days"
_TASK_DESC = "### Task 2: Migrate Prompts to Flask\nCreate PromptBuilder class."
_ARCH = "## Architecture Overview\nBuilder pattern for prompts."
_BUILDER = "I am a solo founder shipping fast."
_PRINCIPLES = "Ship fast, validate first."
_CODEBASE = "modules/ai/prompts/__init__.py"
_REFERENCES = "# Reference\nExisting prompt functions."
_PRIOR = "### task-1-unify-context-services.md\nContext unified."


class TestBuildImplementationGuidePromptSnapshot:
    @pytest.mark.snapshot
    def test_allSections_returnsStablePrompt(self, snapshot):
        assert buildPrompt(
            task_num=_TASK_NUM,
            task_name=_TASK_NAME,
            task_effort=_TASK_EFFORT,
            task_desc=_TASK_DESC,
            arch=_ARCH,
            builder=_BUILDER,
            principles=_PRINCIPLES,
            codebase=_CODEBASE,
            references=_REFERENCES,
            prior=_PRIOR,
        ) == snapshot

    @pytest.mark.snapshot
    def test_noOptionalContext_returnsStablePrompt(self, snapshot):
        assert buildPrompt(
            task_num=_TASK_NUM,
            task_name=_TASK_NAME,
            task_effort=_TASK_EFFORT,
            task_desc=_TASK_DESC,
            arch=_ARCH,
        ) == snapshot
