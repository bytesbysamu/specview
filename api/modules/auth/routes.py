"""Flask blueprint for /api/auth/* — login and me."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from sqlmodel import Session, select

from modules.auth.decorators import require_auth
from modules.auth.models import User
from modules.auth.service import create_token, verify_password
from modules.data.db.engine import get_engine

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
        user = session.exec(select(User).where(User.email == email)).first()

    if user is None or not user.password_hash:
        return jsonify({"error": "invalid credentials"}), 401

    if not verify_password(password, user.password_hash):
        return jsonify({"error": "invalid credentials"}), 401

    token = create_token(user.id, user.email)
    return jsonify({"token": token, "email": user.email}), 200


@auth_bp.get("/me")
@require_auth
def me():
    """GET /api/auth/me — returns {id, email, plan} for the authenticated user."""
    user: User = g.current_user
    return jsonify({"id": user.id, "email": user.email, "plan": user.plan}), 200
