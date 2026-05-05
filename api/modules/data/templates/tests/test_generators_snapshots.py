"""Snapshot tests for template generator functions.

Run:    pytest -m snapshot
Update: pytest -m snapshot --snapshot-update

Pin the full string output for stable representative inputs. Any future
wording change produces a visible, attributable diff against the golden.
The `today` argument is pinned so the snapshot is deterministic.
"""
import pytest

from modules.data.templates import generators as _generators

# Aliases without underscores avoid double-collection under
# python_functions = ["test_*", "*_*"] in pyproject.toml.
generateSpecIndex = _generators.generate_spec_index
generateTimeline = _generators.generate_timeline
generateReadme = _generators.generate_readme

_PROJECT = "My Project"
_TODAY = "2026-04-25"
_TASKS = [
    {"num": "1", "name": "Extract context loader", "effort": "1 day"},
    {"num": "2", "name": "Migrate prompts to Flask", "effort": "2 days"},
    {"num": "3", "name": "Extract template generators", "effort": "1 day"},
]


class TestGenerateSpecIndexSnapshot:
    @pytest.mark.snapshot
    def test_withProjectName_returnsStableMarkdown(self, snapshot):
        assert generateSpecIndex(_PROJECT, today=_TODAY) == snapshot


class TestGenerateTimelineSnapshot:
    @pytest.mark.snapshot
    def test_withTasks_returnsStableMarkdown(self, snapshot):
        assert generateTimeline(_PROJECT, _TASKS, today=_TODAY) == snapshot

    @pytest.mark.snapshot
    def test_emptyTasks_returnsStableMarkdown(self, snapshot):
        assert generateTimeline(_PROJECT, [], today=_TODAY) == snapshot


class TestGenerateReadmeSnapshot:
    @pytest.mark.snapshot
    def test_withProjectName_returnsStableMarkdown(self, snapshot):
        assert generateReadme(_PROJECT, today=_TODAY) == snapshot
