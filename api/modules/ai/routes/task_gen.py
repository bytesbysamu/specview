"""Generate-task Blueprint — POST trigger + GET status.

Routes are nested under /api/projects/<project_id>/generate-task even
though the blueprint lives in modules.task_gen — keeps the URL surface
co-located with the project resource the Angular client already targets.

Each handler: validate → service call → jsonify. No generation logic
here; the background thread lives in service.run_generation.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from config import PROJECTS_DIR
from dtos.models import RegenerateTaskRequest
from modules.data.projects.errors import ProjectNotFoundError
from modules.data.projects.service import get_project

from modules.ai.services import task_gen as service
from modules.ai.services import epic_guide as epic_guide_service
from modules.runtime.workflows.execution import ExecutionStatus
from modules.auth.decorators import require_auth
from modules.usage.decorators import check_usage_limit

logger = logging.getLogger(__name__)

task_gen_bp = Blueprint("task_gen", __name__, url_prefix="/api/projects")

_PROJECTS_PATH = Path(PROJECTS_DIR)


@task_gen_bp.post("/<project_id>/generate-task")
@require_auth
@check_usage_limit("task_gen")
def start_generate_task(project_id: str):
    """Spawn the background thread and return 202.

    Rejects with 409 + alreadyRunning=true if a thread is already
    running for this project (the Angular client treats that as a
    no-op and continues polling).
    """
    try:
        project = get_project(_PROJECTS_PATH, project_id)
    except ValueError:
        logger.warning("generate-task invalid project_id=%s", project_id)
        return jsonify({"error": "Project not found"}), 404
    if project is None:
        raise ProjectNotFoundError(project_id)

    body = request.get_json(force=True, silent=True) or {}
    task_num = body.get("task_num") or None  # optional; None → find next missing

    started = service.start(project_id, _PROJECTS_PATH, task_num=task_num)
    if not started:
        return jsonify({"started": False, "alreadyRunning": True}), 409
    return jsonify({"started": True}), 202


@task_gen_bp.get("/<project_id>/generate-task/status")
@require_auth
def get_generate_task_status(project_id: str):
    """Return the current in-process state for the polling client.

    Returns 502 when error-severity lint flags blocked the write, so the
    Angular client can surface the flag list without a separate request.
    """
    data = service.snapshot(project_id)
    if data.get("lintErrors"):
        return jsonify(data), 502
    return jsonify(data)


@task_gen_bp.post("/<project_id>/cancel")
def task_gen_cancel(project_id: str):
    """Request cooperative cancellation of an in-flight task_gen job.

    Walks the per-project execution slots, picks the first running one,
    and flips it to CANCELLING via WorkflowExecution.request_cancel().
    Returns 404 when no execution exists for this project. Returns 409
    when an execution exists but is not in a cancellable state.
    """
    project_slots = service._project_slots(project_id)
    if not project_slots:
        return jsonify({"error": "no execution for project"}), 404
    running = [exc for exc in project_slots.values() if exc.is_running]
    execution = running[0] if running else list(project_slots.values())[-1]
    if execution.status not in (ExecutionStatus.NEW, ExecutionStatus.IN_PROGRESS):
        return jsonify({
            "error": "cannot cancel",
            "status": execution.status.value,
        }), 409
    execution.request_cancel()
    return jsonify({"status": execution.status.value}), 202


@task_gen_bp.post("/<project_id>/regenerate-task")
@check_usage_limit("task_gen")
def regenerate_task(project_id: str):
    """Delete the prior task-N-*.md and re-run the task_gen workflow.

    Body: {"task_num": "N"}. The deletion path is gated behind a
    git_store presence check — until the persistence brain dump lands,
    the regenerate path simply re-runs the workflow against the same
    task_num and the workflow's own write step overwrites the file.
    """
    try:
        req = RegenerateTaskRequest.model_validate(
            request.get_json(force=True, silent=False) or {}
        )
    except ValidationError:
        return jsonify({"error": "task_num is required"}), 400
    task_num = req.task_num.strip()
    if not task_num:
        return jsonify({"error": "task_num is required"}), 400

    try:
        project = get_project(_PROJECTS_PATH, project_id)
    except ValueError:
        return jsonify({"error": "Project not found"}), 404
    if project is None:
        return jsonify({"error": "Project not found"}), 404

    # Persistence brain dump (git_store) not yet wired — gate the file purge
    # until it ships; the workflow's update_file step overwrites the prior
    # task guide on success regardless.
    if hasattr(current_app, "git_store") and hasattr(current_app, "project_repository"):
        pattern = re.compile(rf"^task-{re.escape(task_num)}-")
        proj_obj = current_app.project_repository.get(project_id)
        for filename in current_app.git_store.list_files(proj_obj.id):
            if pattern.match(filename):
                current_app.git_store.delete_file(
                    proj_obj.id,
                    filename,
                    message=f"chore: regenerate task {task_num}",
                )

    started = service.start(project_id, _PROJECTS_PATH, task_num=task_num)
    if not started:
        return jsonify({"started": False, "alreadyRunning": True}), 409
    return jsonify({"started": True}), 202


@task_gen_bp.post("/<project_id>/generate-epic-guide")
@require_auth
@check_usage_limit("task_gen")
def start_generate_epic_guide(project_id: str):
    """Spawn background thread to generate implementation-guide.md for the full epic.

    Returns 202 on success, 409 if already running.
    """
    try:
        project = get_project(_PROJECTS_PATH, project_id)
    except ValueError:
        return jsonify({"error": "Project not found"}), 404
    if project is None:
        raise ProjectNotFoundError(project_id)

    started = epic_guide_service.start(project_id, _PROJECTS_PATH)
    if not started:
        return jsonify({"started": False, "alreadyRunning": True}), 409
    return jsonify({"started": True}), 202


@task_gen_bp.get("/<project_id>/generate-epic-guide/status")
@require_auth
def get_epic_guide_status(project_id: str):
    """Poll status for the epic guide generation."""
    return jsonify(epic_guide_service.snapshot(project_id))


@task_gen_bp.errorhandler(ProjectNotFoundError)
def _project_not_found(_exc: ProjectNotFoundError):
    return jsonify({"error": "Project not found"}), 404
