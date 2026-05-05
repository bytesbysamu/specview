"""Service-layer tests for modules/quality/coherence.py.

Tests each of the eight invariants in isolation using tmp_path.
No Flask, no monkeypatching — only filesystem and the lint_capability function.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.quality import coherence as _coh
from modules.quality import lint as _lint

# Aliases without underscores — pyproject.toml's *_* python_functions rule
# would otherwise collect snake_case re-exports as test functions.
lintCapability = _coh.lint_capability
Flag = _lint.Flag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def writeFile(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def projectDir(tmp_path: Path) -> Path:
    """Return a minimal valid project directory (project.json only)."""
    (tmp_path / "project.json").write_text(
        json.dumps({"name": "Test", "createdAt": "2025-01-01T00:00:00.000Z"}),
        encoding="utf-8",
    )
    return tmp_path


def flagsForRule(flags, rule):
    return [f for f in flags if f.rule == rule]


# ---------------------------------------------------------------------------
# Invariant 1 — Symbol uniqueness
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSymbolUniqueness:
    def test_duplicateNewPath_inTwoTasks_flaggedAsError(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "task-1-setup.md", (
            "## 3. Files\n### To Create (new)\n"
            "- `modules/foo/bar.py` — first declaration\n"
        ))
        writeFile(d / "task-2-extend.md", (
            "## 3. Files\n### To Create (new)\n"
            "- `modules/foo/bar.py` — duplicate declaration\n"
        ))
        flags = flagsForRule(lintCapability(d), "symbol_uniqueness")
        assert len(flags) == 1, "exactly one flag for one duplicated path"
        assert flags[0].severity == "error"
        assert "modules/foo/bar.py" in flags[0].message
        assert "task-1-setup.md" in flags[0].message
        assert "task-2-extend.md" in flags[0].message

    def test_uniqueNewPaths_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "task-1-setup.md", (
            "## 3. Files\n### To Create (new)\n"
            "- `modules/foo/bar.py` — task 1 only\n"
        ))
        writeFile(d / "task-2-extend.md", (
            "## 3. Files\n### To Create (new)\n"
            "- `modules/foo/baz.py` — task 2 only\n"
        ))
        flags = flagsForRule(lintCapability(d), "symbol_uniqueness")
        assert flags == [], f"no flags expected for unique paths, got: {flags}"


# ---------------------------------------------------------------------------
# Invariant 2 — Import-path consistency
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestImportPathConsistency:
    def test_undeclaredModuleImport_inCodeFence_flaggedAsWarning(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "task-1-setup.md", (
            "## 4. Steps\n\n"
            "```python\n"
            "from modules.quality.lint import Flag\n"
            "```\n"
        ))
        # modules/quality/lint.py is NOT declared in any To Create section
        flags = flagsForRule(lintCapability(d), "import_path_consistency")
        assert len(flags) >= 1
        assert flags[0].severity == "warning"
        assert "modules.quality.lint" in flags[0].message

    def test_declaredModuleImport_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "task-1-setup.md", (
            "## 3. Files\n### To Create (new)\n"
            "- `modules/quality/lint.py` — the linter\n\n"
            "## 4. Steps\n\n"
            "```python\n"
            "from modules.quality.lint import Flag\n"
            "```\n"
        ))
        flags = flagsForRule(lintCapability(d), "import_path_consistency")
        assert flags == [], f"declared import must not produce flags, got: {flags}"


# ---------------------------------------------------------------------------
# Invariant 3 — Epic filename alignment
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEpicFilenameAlignment:
    def test_epicTaskWithNoMatchingFile_flaggedAsError(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "epic.md", (
            "| 1 | **Task One** | 2d |\n"
            "| 2 | **Task Two** | 3d |\n"
        ))
        # Only task-1 file exists; task-2 is missing
        writeFile(d / "task-1-setup.md", "# Task 1\n")
        flags = flagsForRule(lintCapability(d), "epic_filename_alignment")
        errors = [f for f in flags if f.severity == "error"]
        assert len(errors) == 1
        assert "task 2" in errors[0].message.lower()

    def test_orphanTaskFile_withNoEpicRow_flaggedAsWarning(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "epic.md", "| 1 | **Task One** | 2d |\n")
        writeFile(d / "task-1-setup.md", "# Task 1\n")
        writeFile(d / "task-2-extra.md", "# Task 2 (not in epic)\n")
        flags = flagsForRule(lintCapability(d), "epic_filename_alignment")
        warnings = [f for f in flags if f.severity == "warning"]
        assert len(warnings) == 1
        assert "task-2-extra.md" in warnings[0].message

    def test_alignedEpicAndFiles_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "epic.md", (
            "| 1 | **Task One** | 2d |\n"
            "| 2 | **Task Two** | 3d |\n"
        ))
        writeFile(d / "task-1-setup.md", "# Task 1\n")
        writeFile(d / "task-2-extend.md", "# Task 2\n")
        flags = flagsForRule(lintCapability(d), "epic_filename_alignment")
        assert flags == [], f"aligned state must produce no flags, got: {flags}"


# ---------------------------------------------------------------------------
# Invariant 4 — spec-index.md accuracy
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSpecIndexAccuracy:
    def test_missingReferencedFile_flaggedAsError(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "spec-index.md", "[Epic](./epic.md)\n[Missing](./missing.md)\n")
        writeFile(d / "epic.md", "# Epic\n")
        # missing.md does not exist
        flags = flagsForRule(lintCapability(d), "spec_index_accuracy")
        assert len(flags) == 1
        assert flags[0].severity == "error"
        assert "missing.md" in flags[0].message

    def test_allReferencedFilesExist_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "spec-index.md", "[Epic](./epic.md)\n")
        writeFile(d / "epic.md", "# Epic\n")
        flags = flagsForRule(lintCapability(d), "spec_index_accuracy")
        assert flags == [], f"all files present must produce no flags, got: {flags}"

    def test_missingSpecIndexFile_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        # spec-index.md absent — repair endpoint handles structural absence,
        # not this invariant
        flags = flagsForRule(lintCapability(d), "spec_index_accuracy")
        assert flags == [], "absent spec-index.md must not produce flags"


# ---------------------------------------------------------------------------
# Invariant 5 — timeline.md-to-epic alignment
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTimelineEpicAlignment:
    def test_epicTaskMissingFromTimeline_flaggedAsWarning(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "epic.md", (
            "| 1 | **Task One** | 2d |\n"
            "| 2 | **Task Two** | 3d |\n"
        ))
        writeFile(d / "timeline.md", "Task 1 — In Progress\n")
        # Task 2 not mentioned in timeline
        flags = flagsForRule(lintCapability(d), "timeline_epic_alignment")
        assert len(flags) == 1
        assert flags[0].severity == "warning"
        assert "task 2" in flags[0].message.lower()

    def test_allEpicTasksInTimeline_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "epic.md", (
            "| 1 | **Task One** | 2d |\n"
            "| 2 | **Task Two** | 3d |\n"
        ))
        writeFile(d / "timeline.md", "Task 1 — Done\nTask 2 — TODO\n")
        flags = flagsForRule(lintCapability(d), "timeline_epic_alignment")
        assert flags == [], f"all tasks present must produce no flags, got: {flags}"


# ---------------------------------------------------------------------------
# Invariant 6 — Architecture-task coverage
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestArchitectureTaskCoverage:
    def test_componentWithNoTaskMention_flaggedAsWarning(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "architecture.md", (
            "### Pre-emit Linter — `modules/quality/lint.py`\n"
            "Description of the linter component.\n"
        ))
        # No task guide mentions "Pre-emit Linter"
        writeFile(d / "task-1-setup.md", "# Task 1: Something else entirely\n")
        flags = flagsForRule(lintCapability(d), "architecture_task_coverage")
        assert len(flags) == 1
        assert flags[0].severity == "warning"
        assert "Pre-emit Linter" in flags[0].message

    def test_componentMentionedInTask_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "architecture.md", (
            "### Pre-emit Linter — `modules/quality/lint.py`\n"
            "Description.\n"
        ))
        writeFile(d / "task-1-lint.md", "# Task 1\nImplements the Pre-emit Linter.\n")
        flags = flagsForRule(lintCapability(d), "architecture_task_coverage")
        assert flags == [], f"covered component must produce no flags, got: {flags}"


# ---------------------------------------------------------------------------
# Invariant 7 — Pre-flight dependency order
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPreflightDependencyOrder:
    def test_preflightRefersToLaterTaskFile_flaggedAsError(self, tmp_path: Path):
        d = projectDir(tmp_path)
        # Task 2 creates modules/foo/bar.py
        writeFile(d / "task-2-impl.md", (
            "## 3. Files\n### To Create (new)\n"
            "- `modules/foo/bar.py` — created in task 2\n"
        ))
        # Task 1's pre-flight references it (dependency order violation)
        writeFile(d / "task-1-setup.md", (
            "## 2. Pre-flight\n"
            "```bash\n"
            "python -c 'from modules.foo.bar import X'\n"
            "```\n"
            "Verify `modules/foo/bar.py` exists.\n"
        ))
        flags = flagsForRule(lintCapability(d), "preflight_dependency_order")
        assert len(flags) == 1
        assert flags[0].severity == "error"
        assert "task-1-setup.md" in flags[0].message
        assert "modules/foo/bar.py" in flags[0].message
        assert "task 2" in flags[0].message

    def test_preflightRefersToEarlierTaskFile_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        # Task 1 creates the file
        writeFile(d / "task-1-setup.md", (
            "## 3. Files\n### To Create (new)\n"
            "- `modules/foo/bar.py` — created in task 1\n"
        ))
        # Task 2's pre-flight references it — correct order
        writeFile(d / "task-2-impl.md", (
            "## 2. Pre-flight\n"
            "Verify `modules/foo/bar.py` exists.\n"
        ))
        flags = flagsForRule(lintCapability(d), "preflight_dependency_order")
        assert flags == [], f"correct dependency order must produce no flags, got: {flags}"


# ---------------------------------------------------------------------------
# Invariant 8 — Content routing
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestContentRouting:
    def test_todoInEpicDoc_flaggedAsWarning(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "epic.md", "# Epic\n\nStatus: TODO\n")
        flags = flagsForRule(lintCapability(d), "content_routing")
        assert len(flags) >= 1
        assert flags[0].severity == "warning"
        assert "epic.md" in flags[0].message
        assert "TODO" in flags[0].message

    def test_statusEmojiInTaskGuide_flaggedAsWarning(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "task-1-setup.md", "# Task 1\n\nDone ✅\n")
        flags = flagsForRule(lintCapability(d), "content_routing")
        assert len(flags) >= 1
        assert any("task-1-setup.md" in f.message for f in flags)

    def test_statusTermInTimeline_noFlags(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "timeline.md", "Task 1 — TODO\nTask 2 — In Progress\n")
        flags = flagsForRule(lintCapability(d), "content_routing")
        assert flags == [], "status terms in timeline.md must not be flagged"

    def test_lineNumberIncluded_inFlag(self, tmp_path: Path):
        d = projectDir(tmp_path)
        writeFile(d / "epic.md", "# Epic\n\n\nStatus: Blocked\n")
        flags = flagsForRule(lintCapability(d), "content_routing")
        assert len(flags) >= 1
        assert flags[0].line == 4, (
            f"'Blocked' is on line 4; got line {flags[0].line}"
        )


# ---------------------------------------------------------------------------
# End-to-end — clean project produces empty flag list
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLintCapabilityCleanProject:
    def test_emptyProjectDir_returnsEmptyList(self, tmp_path: Path):
        d = projectDir(tmp_path)
        flags = lintCapability(d)
        assert isinstance(flags, list), "always returns a list"
        # A bare project.json produces no cross-document flags
        # (individual invariants skip gracefully when source docs are absent)
        assert flags == [], f"bare project must produce no flags, got: {flags}"
