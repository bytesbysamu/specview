"""Service-level integration tests for the lint gate in run_generation().

Uses monkeypatch to control: chain_adapter.generate (returns fixed text),
lint_task_guide (returns controlled flags), and update_file (tracks calls).

run_generation() is called synchronously (the existing in-test pattern)
so the thread state machine is exercised without spawning a real thread.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from modules.quality.lint import Flag
from modules.ai.services import task_gen as service
from modules.runtime.workflows.execution import ExecutionStatus, WorkflowExecution


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

EPIC_MD = """\
# Epic

| # | Task | Dependencies | Parallel With | Effort | Priority |
|---|------|--------------|---------------|--------|----------|
| 1 | **Alpha Task** | None | — | 1 day | High |

### Task 1: Alpha Task
Build the alpha component.
"""


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    p = tmp_path / "proj-abc"
    p.mkdir()
    (p / "epic.md").write_text(EPIC_MD)
    return tmp_path


@pytest.fixture()
def seeded_project(project_dir: Path, monkeypatch: pytest.MonkeyPatch):
    """Monkeypatch get_project to return a minimal project with epic.md."""
    monkeypatch.setattr(
        "modules.ai.services.task_gen.get_project",
        lambda _dir, _id: {
            "id": "proj-abc",
            "specs": [{"filename": "epic.md", "content": EPIC_MD}],
        },
    )


@pytest.fixture()
def mock_chain(monkeypatch: pytest.MonkeyPatch):
    """Patch chain_adapter.generate to return a controlled result object."""
    result = MagicMock()
    result.text = "# Clean Guide\n\n" + "\n".join(
        f"## {i}. Section {i}\nBody.\n" for i in range(1, 11)
    ) + "\n## 7. Verification\n**Expected delta**: +1 passing.\n"
    monkeypatch.setattr(
        "modules.ai.services.task_gen.chain_adapter.generate",
        lambda *a, **kw: result,
    )
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def runGeneration_errorFlags_failsExecutionNeverCallsUpdateFile(
    project_dir: Path,
    seeded_project,
    mock_chain,
    monkeypatch: pytest.MonkeyPatch,
):
    """Error-severity lint flags must fail the execution and skip update_file."""
    error_flag = Flag("personal-path", "error", "/Users/sam appeared", line=2)
    monkeypatch.setattr(
        "modules.ai.services.task_gen.lint_task_guide",
        lambda _t: [error_flag],
    )

    update_calls: list = []
    monkeypatch.setattr(
        "modules.ai.services.task_gen.update_file",
        lambda *a: update_calls.append(a),
    )

    execution = WorkflowExecution(
        workflow_ref="task_gen/proj-abc",
        inputs={"project_id": "proj-abc", "task_num": "1"},
    )
    execution.start()

    service.run_generation(
        "proj-abc", project_dir, task_num="1", execution=execution,
    )

    assert execution.status == ExecutionStatus.ERROR, "execution must reach ERROR state"
    assert update_calls == [], "update_file must NOT be called when error flags present"
    assert "lintErrors" in execution.outputs, "lintErrors must be stored in outputs"
    assert execution.outputs["lintErrors"][0]["rule"] == "personal-path"


def runGeneration_warningFlags_writesFileAndStoresWarnings(
    project_dir: Path,
    seeded_project,
    mock_chain,
    monkeypatch: pytest.MonkeyPatch,
):
    """Warning-severity lint flags must still write the file and store warnings."""
    warn_flag = Flag("stale-attribution", "warning", "Co-Authored-By hardcoded", line=5)
    monkeypatch.setattr(
        "modules.ai.services.task_gen.lint_task_guide",
        lambda _t: [warn_flag],
    )

    update_calls: list = []
    monkeypatch.setattr(
        "modules.ai.services.task_gen.update_file",
        lambda *a: update_calls.append(a),
    )

    execution = WorkflowExecution(
        workflow_ref="task_gen/proj-abc",
        inputs={"project_id": "proj-abc", "task_num": "1"},
    )
    execution.start()

    service.run_generation(
        "proj-abc", project_dir, task_num="1", execution=execution,
    )

    assert execution.status == ExecutionStatus.COMPLETED, (
        "execution must reach COMPLETED state"
    )
    assert len(update_calls) == 1, "update_file must be called exactly once"
    assert "warnings" in execution.outputs, "warnings must be stored in outputs"
    assert execution.outputs["warnings"][0]["rule"] == "stale-attribution"


def runGeneration_noFlags_writesFileCleanOutputs(
    project_dir: Path,
    seeded_project,
    mock_chain,
    monkeypatch: pytest.MonkeyPatch,
):
    """When lint returns no flags, update_file is called and outputs have no lint keys."""
    monkeypatch.setattr(
        "modules.ai.services.task_gen.lint_task_guide",
        lambda _t: [],
    )

    update_calls: list = []
    monkeypatch.setattr(
        "modules.ai.services.task_gen.update_file",
        lambda *a: update_calls.append(a),
    )

    execution = WorkflowExecution(
        workflow_ref="task_gen/proj-abc",
        inputs={"project_id": "proj-abc", "task_num": "1"},
    )
    execution.start()

    service.run_generation(
        "proj-abc", project_dir, task_num="1", execution=execution,
    )

    assert execution.status == ExecutionStatus.COMPLETED
    assert len(update_calls) == 1
    assert "lintErrors" not in execution.outputs
    assert "warnings" not in execution.outputs


def snapshot_executionHasLintErrors_includesLintErrorsField(monkeypatch: pytest.MonkeyPatch):
    """snapshot() must surface lintErrors from execution outputs."""
    execution = WorkflowExecution(
        workflow_ref="task_gen/proj-xyz",
        inputs={"project_id": "proj-xyz", "task_num": "1"},
    )
    execution.start()
    execution.outputs["lintErrors"] = [
        {"rule": "personal-path", "severity": "error", "message": "msg", "line": 3}
    ]
    execution.fail("lint blocked 1 error-severity flag(s)")

    slot_key = "proj-xyz::1"
    monkeypatch.setitem(service._EXECUTIONS, slot_key, execution)

    snap = service.snapshot("proj-xyz")

    assert "lintErrors" in snap, "snapshot must include lintErrors key"
    assert snap["lintErrors"][0]["rule"] == "personal-path"
    assert snap["done"] is True
    assert snap["running"] is False
