"""Flask blueprint for /api/auth/* — login, verify, logout, me.

Routes are thin: parse via DTO, call service, serialize. The @require_auth
decorator is mounted only on /api/auth/me; the other three routes must remain
public so unauthenticated users can request and exchange a magic link.
"""
from __future__ import annotations

import requests
from flask import Blueprint, current_app, g, jsonify, request

from dtos.models import (
    MagicLinkRequest,
    MagicLinkResponse,
    MeResponse,
    VerifyRequest,
    VerifyResponse,
)
from modules.auth.decorators import require_auth
from modules.auth.service import (
    get_or_create_user_from_claims,
    send_magic_link,
    verify_magic_link,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    req = MagicLinkRequest.model_validate(request.get_json() or {})
    try:
        result = send_magic_link(req.email)
    except requests.HTTPError as exc:
        return jsonify({"error": f"neon auth rejected request: {exc}"}), 502
    return jsonify(MagicLinkResponse(request_id=result["request_id"]).model_dump()), 202


@auth_bp.post("/verify")
def verify():
    req = VerifyRequest.model_validate(request.get_json() or {})
    try:
        exchange = verify_magic_link(req.token)
    except requests.HTTPError as exc:
        return jsonify({"error": f"invalid or expired token: {exc}"}), 400

    user = get_or_create_user_from_claims(
        exchange["claims"], _current_app_user_repository()
    )
    payload = VerifyResponse(
        jwt=exchange["jwt"],
        user=MeResponse(id=user.id, email=user.email, auth_user_id=user.auth_user_id),
    )
    return jsonify(payload.model_dump()), 200


@auth_bp.post("/logout")
def logout():
    # Server-side no-op — Neon Auth owns session lifecycle. The client clears
    # localStorage; we acknowledge with 204.
    return ("", 204)


@auth_bp.get("/me")
@require_auth
def me():
    user = g.current_user
    payload = MeResponse(id=user.id, email=user.email, auth_user_id=user.auth_user_id)
    return jsonify(payload.model_dump()), 200


# ── helper ───────────────────────────────────────────────────────────────────

def _current_app_user_repository():
    """Indirection so tests can monkeypatch a repo without app context tricks."""
    return current_app.user_repository
