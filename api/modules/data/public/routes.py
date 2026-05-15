"""Public Blueprint — unauthenticated read-only spec access via share slug.

No auth decorators on any route. Slugs are resolved via the in-memory index
built at startup.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify

from config import PROJECTS_DIR
from modules.data.projects.service import _safe_path
from . import service as public_service

logger = logging.getLogger(__name__)

public_bp = Blueprint("public", __name__, url_prefix="/api/public")

_PROJECTS_PATH = Path(PROJECTS_DIR)


@public_bp.get("/share/<slug>")
def get_shared_spec(slug: str):
    """GET /api/public/share/<slug> — resolve slug and return project docs.

    Returns {"name": str, "id": str, "docs": [{"filename": str, "label": str, "content": str}]}
    or 404 if the slug is unknown.
    """
    project_id = public_service.resolve_slug(slug)
    if project_id is None:
        logger.debug("get_shared_spec slug_not_found slug=%s", slug)
        return jsonify({"error": "Share link not found"}), 404

    try:
        project_path = _safe_path(_PROJECTS_PATH, project_id)
    except ValueError:
        logger.warning("get_shared_spec path_traversal slug=%s project_id=%s", slug, project_id)
        return jsonify({"error": "Share link not found"}), 404

    meta_path = project_path / "project.json"
    if not project_path.exists() or not meta_path.exists():
        logger.warning("get_shared_spec project_missing slug=%s project_id=%s", slug, project_id)
        return jsonify({"error": "Share link not found"}), 404

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.error("get_shared_spec unreadable_meta slug=%s project_id=%s", slug, project_id)
        return jsonify({"error": "Share link not found"}), 404

    docs = []
    for f in sorted(project_path.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8")
        except OSError:
            content = ""
        label = f.name.replace(".md", "").replace("-", " ").title()
        docs.append({
            "filename": f.name,
            "label": label,
            "content": content,
        })

    return jsonify({
        "name": meta.get("name", project_id),
        "id": project_id,
        "docs": docs,
    })
