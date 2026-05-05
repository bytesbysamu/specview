"""Unit tests for template generator functions.

Each test verifies a behavioural invariant that must hold regardless of exact
wording. Exact wording is locked by the companion snapshot tests.
"""
import pytest

from modules.data.templates import generators as _generators

# Aliases without underscores avoid double-collection under
# python_functions = ["test_*", "*_*"] in pyproject.toml.
generateSpecIndex = _generators.generate_spec_index
generateTimeline = _generators.generate_timeline
generateReadme = _generators.generate_readme


_FIXED_TODAY = "2026-04-25"


class TestGenerateSpecIndex:
    @pytest.mark.unit
    def test_projectNameInOutput(self):
        result = generateSpecIndex("My Project", today=_FIXED_TODAY)
        assert "My Project" in result

    @pytest.mark.unit
    def test_capabilitySlugInOutput(self):
        result = generateSpecIndex("My Project", today=_FIXED_TODAY)
        assert "@my-project/epic.md" in result
        assert "@my-project/architecture.md" in result

    @pytest.mark.unit
    def test_includesDocumentFlowDiagram(self):
        result = generateSpecIndex("P", today=_FIXED_TODAY)
        assert "Analysis ──→ Epic ──→ Architecture ──→ Implementation" in result

    @pytest.mark.unit
    def test_includesLastUpdatedFooter(self):
        result = generateSpecIndex("P", today=_FIXED_TODAY)
        assert f"**Last Updated**: {_FIXED_TODAY}" in result

    @pytest.mark.unit
    def test_returnsStr(self):
        assert isinstance(generateSpecIndex("P", today=_FIXED_TODAY), str)


class TestGenerateTimeline:
    @pytest.mark.unit
    def test_projectNameInOutput(self):
        result = generateTimeline("My Project", [], today=_FIXED_TODAY)
        assert "My Project" in result

    @pytest.mark.unit
    def test_emptyTasks_rendersPlaceholderRow(self):
        result = generateTimeline("P", [], today=_FIXED_TODAY)
        # Backlog placeholder row
        assert "| — | — | — | — | — |" in result
        assert "| Backlog | 0 |" in result
        assert "| **Total** | **0** |" in result

    @pytest.mark.unit
    def test_tasksRenderAsBacklogRows(self):
        tasks = [
            {"num": "1", "name": "First Task", "effort": "2 days"},
            {"num": "2", "name": "Second Task", "effort": "3 days"},
        ]
        result = generateTimeline("P", tasks, today=_FIXED_TODAY)
        assert "| 1 | **First Task** | TBD | 2 days | — |" in result
        assert "| 2 | **Second Task** | TBD | 3 days | — |" in result
        assert "| Backlog | 2 |" in result
        assert "| **Total** | **2** |" in result

    @pytest.mark.unit
    def test_returnsStr(self):
        assert isinstance(generateTimeline("P", [], today=_FIXED_TODAY), str)

    @pytest.mark.unit
    def test_includesLastUpdatedHeader(self):
        result = generateTimeline("P", [], today=_FIXED_TODAY)
        assert f"**Last Updated**: {_FIXED_TODAY}" in result


class TestGenerateReadme:
    @pytest.mark.unit
    def test_projectNameInOutput(self):
        result = generateReadme("My Project", today=_FIXED_TODAY)
        assert "My Project" in result

    @pytest.mark.unit
    def test_includesQuickStartSection(self):
        result = generateReadme("P", today=_FIXED_TODAY)
        assert "## Quick Start" in result

    @pytest.mark.unit
    def test_includesCreatedFooter(self):
        result = generateReadme("P", today=_FIXED_TODAY)
        assert f"**Created**: {_FIXED_TODAY}" in result

    @pytest.mark.unit
    def test_returnsStr(self):
        assert isinstance(generateReadme("P", today=_FIXED_TODAY), str)
