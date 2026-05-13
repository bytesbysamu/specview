"""@require_auth decorator — the only Flask-aware seam in modules/auth/."""
from __future__ import annotations

import os
from functools import wraps

import jwt
from flask import g, jsonify, request
from sqlmodel import Session

from modules.auth.models import User
from modules.auth.service import verify_token
from modules.data.db.engine import get_engine
from modules.observability.sentry import set_sentry_user


def _load_user(user_id: int) -> User | None:
    with Session(get_engine()) as session:
        return session.get(User, user_id)


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if (
            os.environ.get("FLASK_ENV") == "development"
            and os.environ.get("SKIP_AUTH", "").lower() in ("1", "true", "yes")
        ):
            g.current_user = None
            return fn(*args, **kwargs)

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "missing bearer token"}), 401

        token = header[len("Bearer "):]
        try:
            claims = verify_token(token)
        except jwt.PyJWTError as exc:
            return jsonify({"error": f"invalid token: {exc.__class__.__name__}"}), 401

        user = _load_user(int(claims["sub"]))
        if user is None:
            return jsonify({"error": "user not found"}), 401

        g.current_user = user
        set_sentry_user(str(user.id), getattr(user, "email", None))
        return fn(*args, **kwargs)

    return wrapper
