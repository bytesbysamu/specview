"""GET /api/ai/stats — org-wide AI usage and cost snapshot.

ELA #2: route file owns no business logic. Aggregation lives in
runtime/chain/adapter.py; this module only marshals the snapshot to JSON.

Blueprint registration in create_app.ENABLED_MODULES is deferred to the
SaaS Anthropic SDK Provider wrap-up commit. Until then the structural test
``everyOpenapiPath_hasRouteHandler`` will flag /api/ai/stats as declared
in openapi.yaml but missing from Flask's url_map — expected by Task 3.
"""
from __future__ import annotations

from flask import Blueprint, jsonify

from dtos.models import AiStatsResponse
from modules.auth.decorators import require_auth
from modules.runtime.chain import adapter

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/api/ai/stats")
@require_auth
def get_ai_stats():
    snapshot = adapter.get_usage_summary()
    # Validate against the generated DTO so contract drift fails the test
    # suite, not a downstream consumer.
    payload = AiStatsResponse(**snapshot)
    return jsonify(payload.model_dump())
