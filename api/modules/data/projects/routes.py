"""Project Blueprint — thin route handlers.

Each handler: validate → service call → jsonify. No filesystem logic here.
Ported from server.js:469–613.

Deviations from task-2 guide:
- Module is at flask/modules/projects/ (plural) not server/modules/project/ (singular)
- Blueprint exported as projects_bp (not bp) to match create_app.py ENABLED_MODULES
- Blueprint has url_prefix='/api/projects' so route decorators use relative paths
- PROJECTS_DIR from config is a str; wrapped with Path() here
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request
from pydantic import ValidationError

from config import PROJECTS_DIR
from modules.auth.decorators import require_auth
from .ownership import require_project_ownership
from dtos.models import (
    CommitEntry,
    FileDiffResponse,
    FileHistoryResponse,
    FileRevertRequest,
    FileRevertResponse,
    FileUpdateRequest,
    ProjectCreateRequest,
    SuccessResponse,
)
from .errors import ProjectNotFoundError
from .service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    repair_project,
    update_file,
)
from modules.data import git_store  # adapter boundary: only public package import for git ops
from modules.quality.coherence import lint_capability
import modules.data.public.service as public_service

logger = logging.getLogger(__name__)

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

_PROJECTS_PATH = Path(PROJECTS_DIR)


@projects_bp.get("")
@require_auth
def list_projects_route():
    # When SKIP_AUTH=1 is active in dev mode, g.current_user is None.
    # Fall back to the full filesystem scan so local development still works.
    if g.current_user is None:
        return jsonify(list_projects(_PROJECTS_PATH))

    repo = getattr(current_app, "project_repository", None)
    if repo is None:
        return jsonify(list_projects(_PROJECTS_PATH))

    projects = repo.list_for_user(g.current_user.id)
    # Delegate to the filesystem service for per-project content/metadata.
    results = []
    for p in projects:
        try:
            project_data = get_project(_PROJECTS_PATH, p.slug)
            if project_data is not None:
                results.append(project_data)
        except Exception as exc:
            logger.warning("list_projects skipping slug=%s error=%s", p.slug, exc)
    return jsonify(results)


@projects_bp.get("/<id>")
@require_auth
@require_project_ownership
def get_project_route(id: str):
    # g.project verified by @require_project_ownership; load filesystem content.
    try:
        project_data = get_project(_PROJECTS_PATH, id)
        if project_data is None:
            raise ProjectNotFoundError(id)
        return jsonify(project_data)
    except (ProjectNotFoundError, ValueError):
        logger.warning("get_project not_found project_id=%s", id)
        return jsonify({"error": "Project not found"}), 404


@projects_bp.post("")
@require_auth
def create_project_route():
    req = ProjectCreateRequest.model_validate(request.get_json(force=True) or {})

    # Write files to filesystem first to generate the slug/project_id.
    result = create_project(_PROJECTS_PATH, req.name, [f.model_dump() for f in req.files])

    # Dual-write to DB when a real user is authenticated and the repository is
    # available. When SKIP_AUTH=1 is active (g.current_user is None), we skip
    # the DB write so local development still works without a running database.
    repo = getattr(current_app, "project_repository", None)
    if repo is not None and g.current_user is not None:
        try:
            repo.create(
                user_id=g.current_user.id,
                name=result["name"],
                slug=result["id"],
                git_repo_path=str(_PROJECTS_PATH / result["id"]),
            )
        except Exception:
            logger.exception(
                "create_project db_write_failed slug=%s", result["id"]
            )
            # Non-fatal: filesystem write succeeded. The DB row can be
            # back-filled by a repair job; surface the error in logs only.

    return jsonify(result), 201


@projects_bp.put("/<id>/files/<filename>")
@require_auth
@require_project_ownership
def update_file_route(id: str, filename: str):
    req = FileUpdateRequest.model_validate(request.get_json(force=True) or {})
    try:
        found = update_file(_PROJECTS_PATH, id, filename, req.content)
        if not found:
            raise ProjectNotFoundError(id)
        return jsonify(SuccessResponse(success=True).model_dump())
    except (ProjectNotFoundError, ValueError):
        logger.warning("update_file not_found project_id=%s filename=%s", id, filename)
        return jsonify({"error": "Project not found"}), 404


@projects_bp.delete("/<id>")
@require_auth
@require_project_ownership
def delete_project_route(id: str):
    try:
        found = delete_project(_PROJECTS_PATH, id)
        if not found:
            raise ProjectNotFoundError(id)
        repo = getattr(current_app, "project_repository", None)
        if repo is not None:
            repo.delete(g.project.id)
        return jsonify(SuccessResponse(success=True).model_dump())
    except (ProjectNotFoundError, ValueError):
        logger.warning("delete_project not_found project_id=%s", id)
        return jsonify({"error": "Project not found"}), 404


@projects_bp.post("/<id>/repair")
@require_auth
@require_project_ownership
def repair_project_route(id: str):
    try:
        repaired = repair_project(_PROJECTS_PATH, id)
        if repaired is None:
            raise ProjectNotFoundError(id)
        return jsonify({"repaired": repaired})
    except (ProjectNotFoundError, ValueError):
        logger.warning("repair_project not_found project_id=%s", id)
        return jsonify({"error": "Project not found"}), 404


@projects_bp.post("/<id>/coherence")
@require_auth
@require_project_ownership
def coherence_route(id: str):
    """POST /api/projects/<id>/coherence — run the multi-doc coherence pass.

    Returns {flags: [...], summary: str}.
    Ownership is already verified by @require_project_ownership; g.project
    is the verified Project row. The path-traversal guard is preserved via
    the same _safe_path used by the filesystem helpers.
    """
    if ".." in id or "/" in id:
        return jsonify({"error": "Project not found"}), 404

    project_path = _PROJECTS_PATH / id
    flags = lint_capability(project_path)

    flag_dicts = [
        {
            "rule": f.rule,
            "severity": f.severity,
            "message": f.message,
            **({"line": f.line} if f.line is not None else {}),
        }
        for f in flags
    ]

    error_count = sum(1 for f in flags if f.severity == "error")
    warning_count = sum(1 for f in flags if f.severity == "warning")
    if not flags:
        summary = "No issues found."
    else:
        parts = []
        if error_count:
            parts.append(f"{error_count} error{'s' if error_count != 1 else ''}")
        if warning_count:
            parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")
        summary = f"{len(flags)} flag{'s' if len(flags) != 1 else ''}: {', '.join(parts)}."

    logger.info("coherence project_id=%s flags=%d", id, len(flags))
    return jsonify({"flags": flag_dicts, "summary": summary})


# ---------------------------------------------------------------------------
# Share endpoint
# ---------------------------------------------------------------------------

@projects_bp.post("/<id>/share")
@require_auth
@require_project_ownership
def share_project_route(id: str):
    """POST /api/projects/<id>/share — generate (or return existing) share slug.

    Returns {"shareSlug": slug, "url": "/s/<slug>"}
    Idempotent: repeated calls return the same slug.
    """
    project_path = _PROJECTS_PATH / id
    meta_path = project_path / "project.json"
    if not project_path.exists() or not meta_path.exists():
        return jsonify({"error": "Project not found"}), 404

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return jsonify({"error": "Project not found"}), 404

    existing_slug = meta.get("shareSlug")
    if existing_slug:
        return jsonify({"shareSlug": existing_slug, "url": f"/s/{existing_slug}"})

    slug = public_service.generate_slug()
    meta["shareSlug"] = slug
    try:
        meta_path.write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
    except OSError:
        logger.error("share_project_route write_failed project_id=%s", id)
        return jsonify({"error": "Could not save share slug"}), 500

    public_service.register_slug(slug, id)
    logger.info("share_project_route slug_created project_id=%s slug=%s", id, slug)
    return jsonify({"shareSlug": slug, "url": f"/s/{slug}"})


# ---------------------------------------------------------------------------
# File-history endpoints (Pers-T4)
#
# These three handlers expose the git_store's file-level operations behind
# stable HTTP routes. Each handler resolves the project through
# `current_app.project_repository` (a Pers-T3 seam) and delegates every git
# call to `modules.data.git_store` — the only public adapter for pygit2.
#
# Auth: assumes the auth middleware will populate `g.current_user`. No
# ownership check yet — the auth epic owns that wiring.
# ---------------------------------------------------------------------------

_AUTHOR_DEFAULT = "spec-doc[bot]"


def _resolve_project(project_id: str):
    """Return Project row by slug or None. Single seam for the 404 path."""
    repo = getattr(current_app, "project_repository", None)
    if repo is None:
        return None
    return repo.get_by_slug(project_id)


def _to_iso(ts) -> str:
    """git_store.get_history returns unix int timestamps; CommitEntry needs
    an ISO-8601 (date-time) string. Strings pass through unchanged for
    forward-compatibility with future git_store changes."""
    if isinstance(ts, str):
        return ts
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


@projects_bp.get("/<project_id>/files/<filename>/history")
@require_auth
@require_project_ownership
def get_file_history_route(project_id: str, filename: str):
    project = g.project  # verified by @require_project_ownership
    limit = request.args.get("limit", 20, type=int)
    try:
        rows = git_store.get_history(str(project.id), filename, limit)
    except KeyError:
        return jsonify({"error": "File not found in history"}), 404
    entries = [
        CommitEntry(
            sha=row["sha"],
            message=row["message"],
            author=row.get("author", _AUTHOR_DEFAULT),
            timestamp=_to_iso(row["timestamp"]),
        )
        for row in rows
    ]
    return jsonify(FileHistoryResponse(history=entries).model_dump(mode="json"))


@projects_bp.get("/<project_id>/files/<filename>/diff")
@require_auth
@require_project_ownership
def get_file_diff_route(project_id: str, filename: str):
    project = g.project  # verified by @require_project_ownership
    from_sha = request.args.get("from_sha") or request.args.get("from")
    to_sha = request.args.get("to_sha") or request.args.get("to")
    if not from_sha or not to_sha:
        return jsonify({
            "error": "from_sha and to_sha query parameters are required"
        }), 400
    try:
        diff = git_store.get_diff(str(project.id), filename, from_sha, to_sha)
    except KeyError:
        return jsonify({"error": "Unknown commit SHA"}), 422
    return jsonify(FileDiffResponse(diff=diff).model_dump(mode="json"))


@projects_bp.post("/<project_id>/files/<filename>/revert")
@require_auth
@require_project_ownership
def revert_file_route(project_id: str, filename: str):
    project = g.project  # verified by @require_project_ownership
    body = request.get_json(silent=True) or {}
    try:
        req = FileRevertRequest.model_validate(body)
    except ValidationError:
        return jsonify({"error": "to_sha is required"}), 400
    try:
        new_sha = git_store.revert_file(str(project.id), filename, req.to_sha)
    except KeyError:
        return jsonify({"error": "Unknown commit SHA or filename"}), 422

    # git_store.revert_file returns a SHA string; wrap into the response shape.
    # If a future revision returns a dict, accept it transparently.
    if isinstance(new_sha, dict):
        sha_value = new_sha.get("sha", "")
        message = new_sha.get(
            "message", f"revert: {filename} to {req.to_sha[:8]}"
        )
    else:
        sha_value = new_sha
        message = f"revert: {filename} to {req.to_sha[:8]}"

    # Sync the Project row's latest_commit_sha so list-projects queries stay
    # current. file_count is unchanged by a revert (same set of files), so we
    # preserve the existing value rather than re-counting.
    repo = current_app.project_repository
    try:
        repo.touch(project.id, sha_value, project.file_count)
    except Exception:
        # Non-fatal: the git commit succeeded. Surface in logs but don't
        # 500 — the next successful write will resync.
        logger.exception(
            "revert_file touch_failed project_id=%s sha=%s",
            project_id, sha_value,
        )

    return jsonify(
        FileRevertResponse(sha=sha_value, message=message).model_dump(mode="json")
    )
