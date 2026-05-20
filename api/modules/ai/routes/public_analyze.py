"""Public (unauthenticated) analysis endpoint.

POST /api/public/analyze  — submit a braindump, receive a job_id (202).
GET  /api/public/analyze/<job_id>  — poll for the analysis result.

Rate limited to 3 requests per IP per 24 hours via ip_rate_limit.
This is an unauthenticated public endpoint (security-boundary convention).
"""
from __future__ import annotations

import logging
import re

from flask import Blueprint, jsonify, request

from modules.auth.rate_limit import ip_rate_limit
from modules.ai.services.public_analyze import get_job, start_analysis

logger = logging.getLogger(__name__)

_VALID_JOB_ID = re.compile(r'^[a-z0-9-]+$')

public_analyze_bp = Blueprint("public_analyze", __name__, url_prefix="/api/public")


@public_analyze_bp.post("/analyze")
@ip_rate_limit(max_requests=3, window_seconds=86400)
def submit_analysis():
    """Accept a braindump and start an analysis job in the background."""
    body = request.get_json(silent=True) or {}
    raw_braindump = body.get("braindump", "")

    if not isinstance(raw_braindump, str):
        return jsonify({"error": "braindump is required and must be a non-empty string"}), 400

    braindump = raw_braindump.strip()

    if not braindump:
        return jsonify({"error": "braindump is required and must be a non-empty string"}), 400

    if len(braindump) > 10000:
        return jsonify({"error": "braindump exceeds maximum length of 10000 characters"}), 400

    job_id, share_slug = start_analysis(braindump)
    return jsonify({"job_id": job_id, "project_id": job_id, "share_slug": share_slug}), 202


@public_analyze_bp.get("/analyze/<job_id>")
def get_analysis_status(job_id: str):
    """Return the current status of an analysis job."""
    if not job_id or len(job_id) > 100 or not _VALID_JOB_ID.match(job_id):
        return jsonify({"error": "invalid job_id"}), 400
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "job not found"}), 404

    return jsonify({
        "running": job["running"],
        "done": job["done"],
        "analysis": job.get("analysis"),
        "error": job.get("error"),
        "project_id": job.get("project_id"),
        "braindump": job.get("braindump"),
        "share_slug": job.get("share_slug"),
    }), 200
