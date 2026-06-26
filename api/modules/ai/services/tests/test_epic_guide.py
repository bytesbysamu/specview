"""Integration tests for modules/ai/services/epic_guide.py.

All chain calls are monkeypatched so no real AI provider is invoked.
run_generation() is called synchronously (not via start()) to keep tests
deterministic and to avoid threading races.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


from modules.runtime.chain.types import ChainResult
from modules.runtime.chain.errors import ProviderError
from modules.runtime.workflows.execution import WorkflowExecution, ExecutionStatus


# ---------------------------------------------------------------------------
# Helpers — wrapped in a class so pytest does not collect them via *_* rule
# ---------------------------------------------------------------------------

class _H:
    """Namespace for non-test helper functions."""

    @staticmethod
    def execution() -> WorkflowExecution:
        exc = WorkflowExecution(workflow_ref="epic_guide/test", inputs={})
        exc.start()
        return exc

    @staticmethod
    def seed(base: Path, project_id: str, *, with_epic: bool = True) -> Path:
        """Seed a minimal project directory. Returns base."""
        proj = base / project_id
        proj.mkdir(parents=True)
        (proj / "project.json").write_text(
            json.dumps({"name": "Test Project", "createdAt": "2024-01-01T00:00:00.000Z"}),
            encoding="utf-8",
        )
        if with_epic:
            (proj / "epic.md").write_text(
                "# Epic\n## Tasks\n| 1 | **Task One** | None | - | 1d | High |\n",
                encoding="utf-8",
            )
        return base


# ---------------------------------------------------------------------------
# is_running()
# ---------------------------------------------------------------------------

def test_is_running_returns_false_when_no_execution():
    """is_running should return False for an unknown project_id."""
    import modules.ai.services.epic_guide as svc
    assert svc.is_running("no-such-project-xyz") is False


def test_is_running_returns_true_when_execution_is_running():
    """is_running returns True when an IN_PROGRESS execution is registered."""
    import modules.ai.services.epic_guide as svc

    pid = "running-project-test"
    exc = _H.execution()
    with svc._LOCK:
        svc._EXECUTIONS[pid] = exc

    try:
        assert svc.is_running(pid) is True
    finally:
        with svc._LOCK:
            svc._EXECUTIONS.pop(pid, None)


# ---------------------------------------------------------------------------
# snapshot()
# ---------------------------------------------------------------------------

def test_snapshot_returns_idle_when_no_execution():
    """snapshot returns {running: False, done: False} for unknown project."""
    import modules.ai.services.epic_guide as svc
    result = svc.snapshot("never-seen-project-abc")
    assert result == {"running": False, "done": False}


def test_snapshot_returns_filename_when_execution_completes(tmp_path: Path):
    """snapshot includes filename when execution reaches COMPLETED."""
    import modules.ai.services.epic_guide as svc

    pid = "snap-complete-test"
    exc = _H.execution()
    exc.outputs["filename"] = "implementation-guide.md"
    exc.complete()
    with svc._LOCK:
        svc._EXECUTIONS[pid] = exc

    try:
        result = svc.snapshot(pid)
        assert result["running"] is False
        assert result["done"] is True
        assert result["filename"] == "implementation-guide.md"
    finally:
        with svc._LOCK:
            svc._EXECUTIONS.pop(pid, None)


def test_snapshot_returns_error_when_execution_fails():
    """snapshot includes error when execution is in ERROR state."""
    import modules.ai.services.epic_guide as svc

    pid = "snap-error-test"
    exc = _H.execution()
    exc.fail("chain timed out")
    with svc._LOCK:
        svc._EXECUTIONS[pid] = exc

    try:
        result = svc.snapshot(pid)
        assert result["done"] is True
        assert result["error"] == "chain timed out"
    finally:
        with svc._LOCK:
            svc._EXECUTIONS.pop(pid, None)


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

def test_start_returns_false_when_already_running():
    """start() returns False and does not spawn a second thread."""
    import modules.ai.services.epic_guide as svc

    pid = "start-dup-test"
    exc = _H.execution()
    with svc._LOCK:
        svc._EXECUTIONS[pid] = exc

    try:
        result = svc.start(pid, Path("/tmp"))
        assert result is False
    finally:
        with svc._LOCK:
            svc._EXECUTIONS.pop(pid, None)


def test_start_returns_true_and_spawns_thread_when_idle(tmp_path: Path):
    """start() returns True and spawns a daemon thread when no execution exists."""
    import modules.ai.services.epic_guide as svc

    pid = "start-idle-test"
    with svc._LOCK:
        svc._EXECUTIONS.pop(pid, None)

    fake_result = ChainResult(text="mock output", latency_ms=10)

    with patch("modules.ai.services.epic_guide.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.epic_guide.update_file"):
        result = svc.start(pid, tmp_path)

    assert result is True

    with svc._LOCK:
        svc._EXECUTIONS.pop(pid, None)


# ---------------------------------------------------------------------------
# run_generation()
# ---------------------------------------------------------------------------

def test_run_generation_calls_generate_with_empty_system_and_path_prompt(tmp_path: Path):
    """run_generation calls chain_adapter.generate with empty system string."""
    import modules.ai.services.epic_guide as svc

    pid = "gen-prompt-test"
    _H.seed(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text="generated guide", latency_ms=5)

    with patch("modules.ai.services.epic_guide.chain_adapter.generate", return_value=fake_result) as mock_gen, \
         patch("modules.ai.services.epic_guide.update_file"):
        svc.run_generation(pid, tmp_path, exc)

    mock_gen.assert_called_once()
    system_arg = mock_gen.call_args[0][0]
    prompt_arg = mock_gen.call_args[0][1]

    assert system_arg == "", f"Expected empty system string, got: {system_arg!r}"
    assert str(tmp_path / pid) in prompt_arg, "prompt must include project_dir path"


def test_run_generation_writes_output_file_via_update_file(tmp_path: Path):
    """run_generation calls update_file with the generated text."""
    import modules.ai.services.epic_guide as svc

    pid = "gen-write-test"
    _H.seed(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text="the guide content", latency_ms=5)

    with patch("modules.ai.services.epic_guide.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.epic_guide.update_file") as mock_write:
        svc.run_generation(pid, tmp_path, exc)

    mock_write.assert_called_once_with(tmp_path, pid, svc.OUTPUT_FILENAME, "the guide content")
    assert exc.status == ExecutionStatus.COMPLETED


def test_run_generation_sets_filename_output_on_success(tmp_path: Path):
    """run_generation sets execution.outputs['filename'] on success."""
    import modules.ai.services.epic_guide as svc

    pid = "gen-filename-test"
    _H.seed(tmp_path, pid)
    exc = _H.execution()
    fake_result = ChainResult(text="content", latency_ms=5)

    with patch("modules.ai.services.epic_guide.chain_adapter.generate", return_value=fake_result), \
         patch("modules.ai.services.epic_guide.update_file"):
        svc.run_generation(pid, tmp_path, exc)

    assert exc.outputs.get("filename") == svc.OUTPUT_FILENAME


def test_run_generation_fails_when_project_not_found(tmp_path: Path):
    """run_generation calls execution.fail when chain raises due to missing project."""
    import modules.ai.services.epic_guide as svc

    pid = "no-project-here"
    exc = _H.execution()

    # epic_guide passes project_dir to AI directly; simulate an error from chain.
    with patch("modules.ai.services.epic_guide.chain_adapter.generate",
               side_effect=ProviderError("project dir inaccessible")), \
         patch("modules.ai.services.epic_guide.update_file"):
        svc.run_generation(pid, tmp_path, exc)

    assert exc.status == ExecutionStatus.ERROR
    assert "project dir inaccessible" in exc.error


def test_run_generation_fails_when_chain_raises_provider_error(tmp_path: Path):
    """run_generation calls execution.fail when chain_adapter.generate raises ProviderError."""
    import modules.ai.services.epic_guide as svc

    pid = "gen-provider-error"
    _H.seed(tmp_path, pid)
    exc = _H.execution()

    with patch("modules.ai.services.epic_guide.chain_adapter.generate",
               side_effect=ProviderError("chain failed", 502)):
        svc.run_generation(pid, tmp_path, exc)

    assert exc.status == ExecutionStatus.ERROR
    assert "chain failed" in exc.error
