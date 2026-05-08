"""Integration tests for modules/ai/services/task_gen.run_generation().

run_generation() is called synchronously (not via start()) to keep
tests deterministic and avoid threading races.

All chain adapter calls are monkeypatched. File system is isolated
using tmp_path.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


from modules.runtime.chain.types import ChainResult
from modules.runtime.chain.errors import ProviderError
from modules.runtime.workflows.execution import WorkflowExecution, ExecutionStatus
from modules.quality.lint import Flag


# ---------------------------------------------------------------------------
# Fixtures and constants
# ---------------------------------------------------------------------------

EPIC_MD = """\
# Epic: Test Project

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Setup DB** | None | — | 1 day | High |
| 2 | **Build API** | Task 1 | — | 2 days | High |

### Task 1: Setup DB
Create and migrate the database schema.

### Task 2: Build API
Implement the REST endpoints.
"""

CLEAN_GUIDE = """\
# Task 1: Setup DB

## 1. Overview
Sets up the database.

## 2. Context
No prior tasks.

## 3. Files

### To Create (new)
- `db/schema.sql`

### To Modify
- `config/settings.py`

## 4. Steps
Apply migration.

## 5. Tests
Write migration tests.

## 6. Verification

Before: 0 passing
After: 0 → 0 + 3 passing

## 7. Verification
+3 passing

## 8. Rollback
Drop the table.

## 9. Dependencies
None.

## 10. Notes
None.
"""


# ---------------------------------------------------------------------------
# Helpers — wrapped in a class so pytest does not collect them via *_* rule
# ---------------------------------------------------------------------------

class _H:
    """Non-test helper namespace."""

    @staticmethod
    def execution() -> WorkflowExecution:
        exc = WorkflowExecution(workflow_ref="task_gen/test", inputs={})
        exc.start()
        return exc

    @staticmethod
    def project(
        base: Path,
        pid: str,
        *,
        epic: str = EPIC_MD,
        extra: dict[str, str] | None = None,
    ) -> Path:
        """Seed a project directory. Returns base."""
        proj = base / pid
        proj.mkdir(parents=True, exist_ok=True)
        (proj / "project.json").write_text(
            json.dumps({"name": "Test Project", "createdAt": "2024-01-01T00:00:00.000Z"}),
            encoding="utf-8",
        )
        (proj / "epic.md").write_text(epic, encoding="utf-8")
        if extra:
            for fname, content in extra.items():
                (proj / fname).write_text(content, encoding="utf-8")
        return base

    @staticmethod
    def lint_clean(text: str) -> list[Flag]:  # noqa: ARG004
        return []

    @staticmethod
    def lint_error(text: str) -> list[Flag]:  # noqa: ARG004
        return [Flag(rule="preamble-leak", severity="error", message="Reasoning text detected", line=1)]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def test_run_generation_builds_prompt_with_task_num_name_and_dir(tmp_path: Path):
    """Prompt includes task number, task name, and the project_dir path."""
    import modules.ai.services.task_gen as svc

    pid = "prompt-test-1"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result) as mock_gen, \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_clean), \
         patch("modules.ai.services.task_gen.update_file"):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert mock_gen.called
    prompt = mock_gen.call_args[0][1]
    assert "1" in prompt
    assert "Setup DB" in prompt
    assert str(tmp_path / pid) in prompt


def test_run_generation_appends_prior_contracts_when_non_empty(tmp_path: Path):
    """Prompt includes prior task contracts when task 2 is generated after task 1."""
    import modules.ai.services.task_gen as svc

    pid = "prior-contracts-test"
    task1_content = "# Task 1: Setup DB\n\n## 3. Files\n\n### To Create (new)\n- `db/schema.sql`\n"
    _H.project(tmp_path, pid, extra={"task-1-setup-db.md": task1_content})
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result) as mock_gen, \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_clean), \
         patch("modules.ai.services.task_gen.update_file"):
        svc.run_generation(pid, tmp_path, task_num="2", execution=exc)

    prompt = mock_gen.call_args[0][1]
    assert "db/schema.sql" in prompt or "task-1" in prompt.lower()


def test_run_generation_does_not_append_contracts_when_empty(tmp_path: Path):
    """Prompt has no prior contracts section when task 1 is the first."""
    import modules.ai.services.task_gen as svc

    pid = "no-contracts-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result) as mock_gen, \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_clean), \
         patch("modules.ai.services.task_gen.update_file"):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    prompt = mock_gen.call_args[0][1]
    assert "Do NOT re-declare" not in prompt


def test_run_generation_calls_generate_with_empty_system_string(tmp_path: Path):
    """chain_adapter.generate is called with an empty system string."""
    import modules.ai.services.task_gen as svc

    pid = "empty-system-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result) as mock_gen, \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_clean), \
         patch("modules.ai.services.task_gen.update_file"):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    system_arg = mock_gen.call_args[0][0]
    assert system_arg == "", f"Expected empty system, got: {system_arg!r}"


# ---------------------------------------------------------------------------
# Lint gate
# ---------------------------------------------------------------------------

def test_run_generation_calls_lint_on_result_text(tmp_path: Path):
    """lint_task_guide is called with the text returned by chain_adapter.generate."""
    import modules.ai.services.task_gen as svc

    pid = "lint-call-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)
    captured: list[str] = []

    def record_lint(text: str) -> list[Flag]:
        captured.append(text)
        return []

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=record_lint), \
         patch("modules.ai.services.task_gen.update_file"):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert captured == [CLEAN_GUIDE]


def test_run_generation_calls_execution_fail_when_lint_returns_error_flags(tmp_path: Path):
    """When lint returns error-severity flags, execution.fail is called and update_file is not."""
    import modules.ai.services.task_gen as svc

    pid = "lint-error-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text="bad output", latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_error), \
         patch("modules.ai.services.task_gen.update_file") as mock_write:
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert exc.status == ExecutionStatus.ERROR
    mock_write.assert_not_called()


def test_run_generation_writes_file_and_completes_when_lint_passes(tmp_path: Path):
    """When lint returns no error flags, update_file is called and execution completes."""
    import modules.ai.services.task_gen as svc

    pid = "lint-pass-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_clean), \
         patch("modules.ai.services.task_gen.update_file") as mock_write:
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    mock_write.assert_called_once()
    assert exc.status == ExecutionStatus.COMPLETED


def test_run_generation_sets_lint_errors_on_outputs_when_lint_blocks(tmp_path: Path):
    """execution.outputs['lintErrors'] is populated when lint blocks the write."""
    import modules.ai.services.task_gen as svc

    pid = "lint-errors-output"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text="bad", latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_error), \
         patch("modules.ai.services.task_gen.update_file"):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert "lintErrors" in exc.outputs
    assert len(exc.outputs["lintErrors"]) == 1
    assert exc.outputs["lintErrors"][0]["rule"] == "preamble-leak"


# ---------------------------------------------------------------------------
# Filename derivation
# ---------------------------------------------------------------------------

def test_run_generation_writes_correct_filename(tmp_path: Path):
    """update_file receives the task-{num}-{slug}.md filename."""
    import modules.ai.services.task_gen as svc

    pid = "filename-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)
    written: list[str] = []

    def capture(base, proj, fname, content):  # noqa: ARG001
        written.append(fname)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_clean), \
         patch("modules.ai.services.task_gen.update_file", side_effect=capture):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert written == ["task-1-setup-db.md"]


# ---------------------------------------------------------------------------
# execution.outputs on success
# ---------------------------------------------------------------------------

def test_run_generation_sets_task_outputs_on_success(tmp_path: Path):
    """execution.outputs includes taskNum, taskName, and filename on success."""
    import modules.ai.services.task_gen as svc

    pid = "outputs-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text=CLEAN_GUIDE, latency_ms=5)

    with patch("modules.ai.services.task_gen.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.task_gen.lint_task_guide", side_effect=_H.lint_clean), \
         patch("modules.ai.services.task_gen.update_file"):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert exc.outputs["taskNum"] == "1"
    assert exc.outputs["taskName"] == "Setup DB"
    assert exc.outputs["filename"] == "task-1-setup-db.md"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_run_generation_fails_when_chain_raises_provider_error(tmp_path: Path):
    """execution.fail is called when chain_adapter.generate raises ProviderError."""
    import modules.ai.services.task_gen as svc

    pid = "chain-error-test"
    _H.project(tmp_path, pid)
    exc = _H.execution()

    with patch("modules.ai.services.task_gen.chain_adapter.generate",
               side_effect=ProviderError("upstream timeout", 504)):
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert exc.status == ExecutionStatus.ERROR
    assert "upstream timeout" in exc.error


def test_run_generation_fails_when_project_not_found(tmp_path: Path):
    """execution.fail is called when get_project returns None (project dir missing)."""
    import modules.ai.services.task_gen as svc

    pid = "missing-project-xyz"
    exc = _H.execution()

    with patch("modules.ai.services.task_gen.chain_adapter.generate") as mock_gen:
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert exc.status == ExecutionStatus.ERROR
    assert "project not found" in exc.error
    mock_gen.assert_not_called()


def test_run_generation_fails_when_epic_md_missing(tmp_path: Path):
    """execution.fail is called when epic.md is missing from the project."""
    import modules.ai.services.task_gen as svc

    pid = "no-epic-test"
    proj = tmp_path / pid
    proj.mkdir(parents=True)
    (proj / "project.json").write_text(
        json.dumps({"name": "No Epic", "createdAt": "2024-01-01T00:00:00.000Z"}),
        encoding="utf-8",
    )
    # Intentionally omit epic.md

    exc = _H.execution()

    with patch("modules.ai.services.task_gen.chain_adapter.generate") as mock_gen:
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert exc.status == ExecutionStatus.ERROR
    assert "epic.md missing" in exc.error
    mock_gen.assert_not_called()


def test_run_generation_fails_when_no_tasks_parseable(tmp_path: Path):
    """execution.fail is called when epic.md contains no task table rows."""
    import modules.ai.services.task_gen as svc

    empty_epic = "# Epic: Empty\n\nNo tasks here.\n"
    pid = "no-tasks-test"
    _H.project(tmp_path, pid, epic=empty_epic)
    exc = _H.execution()

    with patch("modules.ai.services.task_gen.chain_adapter.generate") as mock_gen:
        svc.run_generation(pid, tmp_path, task_num="1", execution=exc)

    assert exc.status == ExecutionStatus.ERROR
    assert exc.error is not None
    mock_gen.assert_not_called()
