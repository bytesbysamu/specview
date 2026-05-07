"""Thin action routes — Phase 3 API surface.

Eight focused handlers: expand, compress, clarify, simplify, tldr, bullets,
brainstorm, rewrite. Each delegates to the skill service (load_skill_registry
+ run_skill) and returns {"text": ..., "latencyMs": ...}.
"""
import json
import time

from flask import Blueprint, jsonify, request

from modules.ai.routes.generic_skill_service import load_skill_registry, run_skill
from modules.auth.decorators import require_auth
from modules.usage.decorators import check_usage_limit

actions_bp = Blueprint("actions", __name__, url_prefix="/api")

_VALID_STYLES = ["Concise", "Technical", "Executive", "Narrative", "Punchy"]


def _text_or_400(body: dict):
    text = (body.get("text") or "").strip()
    if not text:
        return None, (jsonify({"error": "text is required"}), 400)
    return text, None


def _make_handler(verb: str):
    @actions_bp.post(f"/{verb}")
    @require_auth
    @check_usage_limit("text")
    def _handler():
        body = request.get_json(force=True, silent=False) or {}
        text, err = _text_or_400(body)
        if err:
            return err
        try:
            registry = load_skill_registry(verb)
        except FileNotFoundError:
            return jsonify({"error": f"skill unavailable: {verb}"}), 503
        t0 = time.monotonic()
        try:
            result = run_skill(verb, json.dumps({"text": text}), registry)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        latency_ms = int((time.monotonic() - t0) * 1000)
        return jsonify({"text": result["text"], "latencyMs": latency_ms})

    # Give each generated function a unique name so Flask doesn't complain
    # about duplicate endpoint names.
    _handler.__name__ = verb
    return _handler


# Register the six uniform-verb handlers.
for _verb in ("expand", "compress", "clarify", "simplify", "tldr", "bullets"):
    _make_handler(_verb)


@actions_bp.post("/brainstorm")
@require_auth
@check_usage_limit("text")
def brainstorm():
    body = request.get_json(force=True, silent=False) or {}
    text, err = _text_or_400(body)
    if err:
        return err
    question = (body.get("question") or "").strip()
    context = (body.get("context") or "").strip()
    try:
        registry = load_skill_registry("brainstorm")
    except FileNotFoundError:
        return jsonify({"error": "skill unavailable: brainstorm"}), 503
    t0 = time.monotonic()
    try:
        result = run_skill(
            "brainstorm",
            json.dumps({"text": text, "question": question, "context": context}),
            registry,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    latency_ms = int((time.monotonic() - t0) * 1000)
    return jsonify({"text": result["text"], "latencyMs": latency_ms})


@actions_bp.post("/rewrite")
@require_auth
@check_usage_limit("text")
def rewrite():
    body = request.get_json(force=True, silent=False) or {}
    text, err = _text_or_400(body)
    if err:
        return err
    style = (body.get("style") or "").strip()
    if style not in _VALID_STYLES:
        return jsonify({"error": "invalid style"}), 400
    try:
        registry = load_skill_registry("rewrite")
    except FileNotFoundError:
        return jsonify({"error": "skill unavailable: rewrite"}), 503
    t0 = time.monotonic()
    try:
        result = run_skill(
            "rewrite",
            json.dumps({"text": text, "style": style}),
            registry,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    latency_ms = int((time.monotonic() - t0) * 1000)
    return jsonify({"text": result["text"], "latencyMs": latency_ms})
