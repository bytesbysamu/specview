"""Generic skill route — single entry point for all plugin skills.

POST /api/skills/run/<skill_name>
  - Security gate: name regex → skill.json existence → validated
  - sync skill  → 200 {"result": ...} + X-Job-Id header
  - async skill → 202 {"job_id": "..."}

GET /api/skills/jobs/<job_id>
  - Poll async job status

GET /api/skills/
  - List all available skills (from skill.json metadata)
"""
from __future__ import annotations

import json
import logging
import re
import threading

from flask import Blueprint, jsonify, request

from modules.auth.decorators import require_auth
from modules.ai.job_store import create_job, get_job
from .generic_skill_service import load_skill_registry, run_skill, run_skill_async

logger = logging.getLogger(__name__)

skill_bp = Blueprint("skills", __name__, url_prefix="/api/skills")

_SKILL_NAME_RE = re.compile(r'^[a-z][a-z0-9-]{0,63}$')


@skill_bp.post("/run/<skill_name>")
@require_auth
def run_skill_endpoint(skill_name: str):
    # Security gate 1: name regex (before any filesystem access)
    if not _SKILL_NAME_RE.match(skill_name):
        return jsonify({"error": f"invalid skill name: {skill_name!r}"}), 400

    # Security gate 2: skill.json must exist
    try:
        registry = load_skill_registry(skill_name)
    except FileNotFoundError:
        return jsonify({"error": f"skill not found: {skill_name!r}"}), 404

    # Parse request body — passed verbatim as JSON string to the skill
    body = request.get_json(force=True, silent=True) or {}
    user_input = json.dumps(body, ensure_ascii=False)

    execution_model = registry.get("execution_model", "sync")
    skill_version = registry.get("version", "unknown")
    job = create_job(skill_name, skill_version)

    if execution_model == "sync":
        try:
            result = run_skill(skill_name, user_input, registry)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        response = jsonify({"result": result})
        response.headers["X-Job-Id"] = job.job_id
        return response, 200

    # async
    threading.Thread(
        target=run_skill_async,
        args=(skill_name, user_input, registry, job.job_id),
        name=f"skill-{skill_name}[{job.job_id[:8]}]",
        daemon=True,
    ).start()
    return jsonify({"job_id": job.job_id}), 202


@skill_bp.get("/jobs/<job_id>")
@require_auth
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404

    body: dict = {
        "job_id": job.job_id,
        "skill": job.skill_name,
        "version": job.skill_version,
        "status": job.status,
        "done": job.status in ("done", "failed"),
    }
    if job.status == "done":
        body["result"] = job.result
    elif job.status == "failed":
        body["error"] = job.error

    return jsonify(body)


@skill_bp.get("/")
def list_skills():
    """List all available skills from their skill.json metadata."""
    from .generic_skill_service import _skills_dir
    import json as _json
    skills = []
    skills_dir = _skills_dir()
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_json = skill_dir / "skill.json"
            if skill_json.exists():
                try:
                    with open(skill_json) as f:
                        meta = _json.load(f)
                    skills.append(meta)
                except Exception:
                    pass
    return jsonify({"skills": skills})
