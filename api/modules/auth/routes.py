"""Flask blueprint for /api/auth/* — login, register, and me."""
from __future__ import annotations

import hashlib
import logging

from flask import Blueprint, g, jsonify, request
from sqlmodel import Session

from modules.auth.decorators import require_auth
from modules.auth.models import User
from modules.auth.rate_limit import ip_rate_limit
from modules.auth.service import (
    create_token,
    create_user,
    get_user_by_email,
    hash_password,
    normalize_email,
    refresh_token_for_user,
    token_expires_at_iso,
    validate_password_policy,
    verify_password,
)
from modules.data.db.engine import get_engine

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    """POST /api/auth/login — {email, password} → {token, email}."""
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    with Session(get_engine()) as session:
        user = get_user_by_email(session, email)

    if user is None or not user.password_hash:
        return jsonify({"error": "invalid credentials"}), 401

    if not verify_password(password, user.password_hash):
        return jsonify({"error": "invalid credentials"}), 401

    token = create_token(user.id, user.email)
    return jsonify({"token": token, "email": user.email}), 200


@auth_bp.post("/register")
def register():
    """POST /api/auth/register — {email, password} → {token, email} (201)."""
    body = request.get_json(silent=True) or {}
    email = normalize_email(body.get("email") or "")
    password = body.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    policy_error = validate_password_policy(password)
    if policy_error:
        return jsonify({"error": policy_error}), 400

    with Session(get_engine()) as session:
        existing = get_user_by_email(session, email)
        if existing is not None:
            return jsonify({"error": "email already registered"}), 409

        new_user = create_user(session, email, hash_password(password))

    token = create_token(new_user.id, new_user.email)
    email_hash = hashlib.sha256(new_user.email.encode()).hexdigest()[:12]
    logger.info("new user registered email_hash=%s", email_hash)
    return jsonify({"token": token, "email": new_user.email}), 201


@auth_bp.get("/me")
@require_auth
def me():
    """GET /api/auth/me — returns {id, email, plan, token_expires_at} for the authenticated user."""
    user: User = g.current_user
    raw_token = request.headers.get("Authorization", "")[len("Bearer "):]
    expires_at = token_expires_at_iso(raw_token) if raw_token else None
    return jsonify({"id": user.id, "email": user.email, "plan": user.plan, "token_expires_at": expires_at}), 200


@auth_bp.post("/refresh")
@require_auth
def refresh():
    """POST /api/auth/refresh — issues a fresh JWT for the authenticated user."""
    if g.current_user is None:
        return jsonify({"error": "authentication required"}), 401
    user: User = g.current_user
    token = refresh_token_for_user(user.id, user.email)
    user_id_hash = hashlib.sha256(str(user.id).encode()).hexdigest()[:12]
    logger.info("token refreshed for user_id_hash=%s", user_id_hash)
    return jsonify({"token": token, "email": user.email}), 200
