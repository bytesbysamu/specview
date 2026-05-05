from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from config import CONTEXT_PATHS
from dtos.models import ContextResponse, ContextUpdateRequest, SuccessResponse
from .service import read_context, write_context

logger = logging.getLogger(__name__)
context_bp = Blueprint("context", __name__)

_VALID_KEYS: frozenset[str] = frozenset(CONTEXT_PATHS.keys())
# {'builder', 'principles', 'codebase', 'references'} — derived from config,
# not hardcoded, so adding a key to CONTEXT_PATHS is the only change needed.


def _get_handler(key: str):
    content = read_context(key)
    return jsonify(ContextResponse(content=content, exists=len(content) > 0).model_dump())


def _put_handler(key: str):
    payload = ContextUpdateRequest.model_validate(request.get_json(force=True) or {})
    try:
        write_context(key, payload.content)
    except OSError:
        logger.error("Failed to write context file: %s", key)
        return jsonify({"error": f"Failed to save {key}"}), 500
    return jsonify(SuccessResponse(success=True).model_dump())


@context_bp.get("/api/context/<key>")
def get_context(key: str):
    if key not in _VALID_KEYS:
        return jsonify({"error": f"Unknown context key: {key!r}"}), 404
    return _get_handler(key)


@context_bp.put("/api/context/<key>")
def put_context(key: str):
    if key not in _VALID_KEYS:
        return jsonify({"error": f"Unknown context key: {key!r}"}), 404
    return _put_handler(key)
