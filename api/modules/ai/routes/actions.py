"""Thin action routes — the inline text-verb API surface.

Eight focused handlers: expand, compress, clarify, simplify, tldr, bullets,
rewrite, brainstorm. Each returns ``{"text": ..., "latencyMs": ...}`` — the
contract specview's frontend consumes (unchanged).

SEAM (the "no backend per product" PoC): ALL EIGHT verbs are NO LONGER run
in-process against per-product SKILL.md prompts. They forward to the shared oll-am
**write-service** (``POST /api/write/<verb>``) via ``write_client``, which owns the
prompt + the oll-model gateway call AND the Core auth/plan gate. specview's own
per-verb skill/model code path is fully retired for these verbs (their SKILL.md
dirs are deleted). The local skill runner (``generic_skill_service``) survives only
for specview's STATEFUL surface — the multi-step spec pipelines, git-backed project
data, and coherence lint — none of which live here.

  expand · compress · clarify · simplify · tldr · bullets → write_client.run_verb
  rewrite   → write_client.rewrite   (named ``style`` → free-form ``instructions``)
  brainstorm → write_client.brainstorm (optional ``question`` / ``context``)

Auth: each route keeps ``@require_auth`` + ``@check_usage_limit`` (specview is the
product front door with its own quota), then forwards the SAME Bearer to
write-service. In the deployed topology specview is a Core client, so the SPA's
JWT is a Core JWT (shared secret) that write-service re-validates via Core /me —
no double-gate of the model call.
"""
import logging
import time

from flask import Blueprint, jsonify, request

from modules.ai import write_client
from modules.ai.write_client import WriteServiceError
from modules.auth.decorators import require_auth
from modules.usage.decorators import check_usage_limit

logger = logging.getLogger(__name__)

actions_bp = Blueprint("actions", __name__, url_prefix="/api")

# specview's fixed set of named rewrite styles → the free-form ``instructions``
# string write-service's /rewrite folds into every pass. The named style is a
# specview-product concept; write-service is style-agnostic, so we translate each
# style to an explicit instruction here. This is the documented style→instructions
# mapping for the migration.
_STYLE_INSTRUCTIONS = {
    "Concise": "Rewrite in a concise style: cut every redundant word, keep only the essential meaning.",
    "Technical": "Rewrite in a technical style: precise terminology, unambiguous, aimed at an expert reader.",
    "Executive": "Rewrite in an executive style: lead with the outcome, keep it brief and decision-oriented.",
    "Narrative": "Rewrite in a narrative style: smooth, flowing prose with natural connective tissue.",
    "Punchy": "Rewrite in a punchy style: short, high-energy sentences built on strong verbs.",
}
_VALID_STYLES = list(_STYLE_INSTRUCTIONS)


def _text_or_400(body: dict):
    text = (body.get("text") or "").strip()
    if not text:
        return None, (jsonify({"error": "text is required"}), 400)
    return text, None


def _bearer_token() -> str:
    """Extract the raw token from a well-formed ``Authorization: Bearer`` header.

    Forwarded verbatim to write-service so it can auth + gate the caller. Returns
    "" when absent — ``@require_auth`` has already run, so in production a token is
    present; the dev SKIP_AUTH bypass sends a dummy Bearer the harness forwards.
    """
    header = request.headers.get("Authorization", "")
    parts = header.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return ""


def _relay_write_error(verb: str, exc: WriteServiceError):
    """Map a ``WriteServiceError`` to specview's HTTP response.

    Relays write-service's own status + envelope when known (401/402/429 pass
    through verbatim); a transport failure (no upstream status) → 502.
    """
    if exc.upstream_status is not None:
        return jsonify(exc.upstream_body or {"error": str(exc)}), exc.upstream_status
    logger.error("write-service %r call failed: %s", verb, exc)
    return jsonify({"error": "write-service unavailable"}), 502


def _make_handler(verb: str):
    @actions_bp.post(f"/{verb}")
    @require_auth
    @check_usage_limit("text")
    def _handler():
        body = request.get_json(force=True, silent=False) or {}
        text, err = _text_or_400(body)
        if err:
            return err
        t0 = time.monotonic()
        try:
            result = write_client.run_verb(verb, text, _bearer_token())
        except WriteServiceError as exc:
            return _relay_write_error(verb, exc)
        latency_ms = int((time.monotonic() - t0) * 1000)
        return jsonify({"text": result["text"], "latencyMs": latency_ms})

    # Give each generated function a unique name so Flask doesn't complain
    # about duplicate endpoint names.
    _handler.__name__ = verb
    return _handler


# Register the six single-input verbs — all served by write-service.
for _verb in ("expand", "compress", "clarify", "simplify", "tldr", "bullets"):
    _make_handler(_verb)


@actions_bp.post("/rewrite")
@require_auth
@check_usage_limit("text")
def rewrite():
    """Rewrite — served by write-service. specview's named ``style`` maps to
    write-service's free-form ``instructions`` (see ``_STYLE_INSTRUCTIONS``)."""
    body = request.get_json(force=True, silent=False) or {}
    text, err = _text_or_400(body)
    if err:
        return err
    style = (body.get("style") or "").strip()
    if style not in _STYLE_INSTRUCTIONS:
        return jsonify({"error": "invalid style"}), 400
    t0 = time.monotonic()
    try:
        result = write_client.rewrite(text, _STYLE_INSTRUCTIONS[style], _bearer_token())
    except WriteServiceError as exc:
        return _relay_write_error("rewrite", exc)
    latency_ms = int((time.monotonic() - t0) * 1000)
    return jsonify({"text": result["text"], "latencyMs": latency_ms})


@actions_bp.post("/brainstorm")
@require_auth
@check_usage_limit("text")
def brainstorm():
    """Brainstorm — served by write-service (``POST /api/write/brainstorm``).
    specview's optional ``question`` / ``context`` forward straight through; the
    markdown answer comes back in ``text``, same contract as before."""
    body = request.get_json(force=True, silent=False) or {}
    text, err = _text_or_400(body)
    if err:
        return err
    question = (body.get("question") or "").strip()
    context = (body.get("context") or "").strip()
    t0 = time.monotonic()
    try:
        result = write_client.brainstorm(text, question, context, _bearer_token())
    except WriteServiceError as exc:
        return _relay_write_error("brainstorm", exc)
    latency_ms = int((time.monotonic() - t0) * 1000)
    return jsonify({"text": result["text"], "latencyMs": latency_ms})
