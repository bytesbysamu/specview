"""Templates Blueprint — markdown generators behind HTTP.

Three endpoints:
- GET  /api/templates/spec-index?project_name=<str>
- GET  /api/templates/readme?project_name=<str>
- POST /api/templates/timeline   body: {project_name, tasks: [{num, name, effort}]}

GET is used for the two endpoints that take only a project_name; POST is used
for timeline because the tasks list is a structured array of objects.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from dtos.models import TemplateResponse, TimelineRequest

from .generators import generate_readme, generate_spec_index, generate_timeline

logger = logging.getLogger(__name__)

templates_bp = Blueprint("templates", __name__, url_prefix="/api/templates")


def _project_name_from_query() -> str | None:
    name = (request.args.get("project_name") or "").strip()
    return name or None


@templates_bp.get("/spec-index")
def get_spec_index_template():
    project_name = _project_name_from_query()
    if not project_name:
        return jsonify({"error": "project_name query parameter is required"}), 400
    content = generate_spec_index(project_name)
    logger.info("get_spec_index_template project_name=%r", project_name)
    return jsonify(TemplateResponse(content=content).model_dump())


@templates_bp.get("/readme")
def get_readme_template():
    project_name = _project_name_from_query()
    if not project_name:
        return jsonify({"error": "project_name query parameter is required"}), 400
    content = generate_readme(project_name)
    logger.info("get_readme_template project_name=%r", project_name)
    return jsonify(TemplateResponse(content=content).model_dump())


@templates_bp.post("/timeline")
def post_timeline_template():
    payload = request.get_json(silent=True) or {}
    try:
        req = TimelineRequest.model_validate(payload)
    except ValidationError as exc:
        return jsonify({
            "error": "validation_failed",
            "details": exc.errors(),
        }), 400
    if not req.project_name.strip():
        return jsonify({"error": "project_name must not be blank"}), 400
    content = generate_timeline(
        req.project_name,
        [t.model_dump() for t in req.tasks],
    )
    logger.info(
        "post_timeline_template project_name=%r task_count=%d",
        req.project_name, len(req.tasks),
    )
    return jsonify(TemplateResponse(content=content).model_dump())
