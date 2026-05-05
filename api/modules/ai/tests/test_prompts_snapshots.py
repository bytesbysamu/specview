"""Snapshot tests for prompt functions in modules.ai.prompts.

Run:    pytest -m snapshot
Update: pytest -m snapshot --snapshot-update

Each prompt function returns a (system, user_prompt) tuple. We pin both
halves with one syrupy assertion per representative input. Any future
change to prompt wording will produce a visible PR diff against the
committed golden snapshot in __snapshots__/test_prompts_snapshots.ambr.

Inputs are deliberately small and deterministic — NOT realistic
production values; only enough to exercise the templating logic.
"""
import pytest

from modules.ai import prompts as _prompts

# Aliases without underscores avoid double-collection under
# python_functions = ["test_*", "*_*"] in flask/pyproject.toml.
rewritePrompt = _prompts.rewrite_prompt
generatePrompt = _prompts.generate_prompt
iteratePrompt = _prompts.iterate_prompt
generateSpecPrompt = _prompts.generate_spec_prompt
reviewPrompt = _prompts.review_prompt
lintBraindumpPrompt = _prompts.lint_braindump_prompt
scanPrompt = _prompts.scan_prompt


# Stable, minimal inputs. Edit only with deliberate intent — every
# change requires regenerating the goldens.
_BRAINDUMP = "A tool that helps solo founders write better product specs."
_TEXT = "Make this text better."
_INSTRUCTION = "Expand with more detail."
_BUILDER = "I am a solo founder shipping fast."
_PRINCIPLES = "Ship fast, validate first."
_TONE = "concise"
_BASE_SPEC = "Scope: spec generator MVP."
_CURRENT = "## Current document\nDraft content."
_DOCUMENTS = {"epic.md": "# Epic\nScope content.", "architecture.md": "# Architecture\nDesign."}
_TREE = "src/\n  main.py\n  utils.py"


class TestRewritePromptSnapshot:
    @pytest.mark.snapshot
    def test_textAndInstruction_returnsStablePrompt(self, snapshot):
        assert rewritePrompt(_TEXT, _INSTRUCTION) == snapshot


class TestGeneratePromptSnapshot:
    @pytest.mark.snapshot
    def test_allContextEmbedded_returnsStablePrompt(self, snapshot):
        assert generatePrompt("Write a spec", _BUILDER, _PRINCIPLES, _TONE) == snapshot


class TestIteratePromptSnapshot:
    @pytest.mark.snapshot
    def test_baseSpecAndCurrent_returnsStablePrompt(self, snapshot):
        assert iteratePrompt(_BASE_SPEC, _CURRENT, _BUILDER, _PRINCIPLES) == snapshot


class TestGenerateSpecPromptSnapshot:
    @pytest.mark.snapshot
    def test_braindumpWithContext_returnsStablePrompt(self, snapshot):
        assert generateSpecPrompt(_BRAINDUMP, _BUILDER, _PRINCIPLES) == snapshot


class TestReviewPromptSnapshot:
    @pytest.mark.snapshot
    def test_documentsDict_returnsStablePrompt(self, snapshot):
        assert reviewPrompt(_DOCUMENTS) == snapshot


class TestLintBraindumpPromptSnapshot:
    @pytest.mark.snapshot
    def test_braindumpInput_returnsStablePrompt(self, snapshot):
        assert lintBraindumpPrompt(_BRAINDUMP) == snapshot


class TestScanPromptSnapshot:
    @pytest.mark.snapshot
    def test_treeText_returnsStablePrompt(self, snapshot):
        assert scanPrompt(_TREE) == snapshot
