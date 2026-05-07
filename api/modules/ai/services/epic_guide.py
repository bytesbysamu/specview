"""Background thread + in-process state for generate-epic-guide.

Generates a single implementation-guide.md covering every task in the epic.
One execution slot per project — only one epic guide generation runs at a time.

Public surface:
    is_running(project_id)  — predicate
    snapshot(project_id)    — read-only summary for the GET route
    start(project_id, projects_dir) — spawn thread
    run_generation(...)     — thread body
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from modules.runtime.chain import adapter as chain_adapter
from modules.data.projects.service import update_file
from modules.runtime.workflows.execution import WorkflowExecution

logger = logging.getLogger(__name__)

_EXECUTIONS: dict[str, WorkflowExecution] = {}
_LOCK = threading.Lock()

OUTPUT_FILENAME = "implementation-guide.md"


def is_running(project_id: str) -> bool:
    with _LOCK:
        exc = _EXECUTIONS.get(project_id)
        return exc is not None and exc.is_running


def snapshot(project_id: str) -> dict:
    with _LOCK:
        exc = _EXECUTIONS.get(project_id)
    if exc is None:
        return {"running": False, "done": False}
    out: dict = {"running": exc.is_running, "done": exc.is_terminal}
    if exc.outputs.get("filename"):
        out["filename"] = exc.outputs["filename"]
    if exc.error is not None:
        out["error"] = exc.error
    return out


def run_generation(
    project_id: str,
    projects_dir: Path,
    execution: WorkflowExecution,
) -> None:
    """Background thread: build prompt → call AI → write file."""
    try:
        project_dir = projects_dir / project_id

        result = chain_adapter.generate(
            "",
            f"Generate implementation-guide.md for the project at {project_dir}. Read epic.md and architecture.md from that directory.",
            max_tokens=8192,
        )

        update_file(projects_dir, project_id, OUTPUT_FILENAME, result.text)
        execution.outputs["filename"] = OUTPUT_FILENAME
        execution.complete()

    except Exception as exc:
        logger.exception(
            "generate-epic-guide thread failed project_id=%s", project_id
        )
        execution.fail(str(exc))


def start(project_id: str, projects_dir: Path) -> bool:
    """Spawn background thread. Returns False if already running."""
    with _LOCK:
        existing = _EXECUTIONS.get(project_id)
        if existing and existing.is_running:
            return False
        execution = WorkflowExecution(
            workflow_ref=f"epic_guide/{project_id}",
            inputs={"project_id": project_id, "projects_dir": str(projects_dir)},
        )
        execution.start()
        _EXECUTIONS[project_id] = execution

    thread = threading.Thread(
        target=run_generation,
        args=(project_id, projects_dir, execution),
        name=f"generate-epic-guide[{project_id}]",
        daemon=True,
    )
    thread.start()
    return True
