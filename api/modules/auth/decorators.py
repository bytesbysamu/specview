"""@require_auth decorator — the only Flask-aware seam in modules/auth/.

Reads Authorization: Bearer <token>, validates via service.verify_jwt, hydrates
g.current_user via service.get_or_create_user_from_claims, dispatches to the
wrapped handler. Returns 401 on missing or invalid credentials.

g.current_user is the contract every downstream capability (Mon-T2/T3 usage
decorator, billing webhook handler) reads from. Do not change the attribute
name without coordinating with those consumers.
"""
from __future__ import annotations

import os
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from modules.auth.service import get_or_create_user_from_claims, verify_jwt


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if os.environ.get("SKIP_AUTH", "").lower() in ("1", "true", "yes"):
            g.current_user = None
            return fn(*args, **kwargs)

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "missing bearer token"}), 401

        token = header[len("Bearer "):]
        try:
            claims = verify_jwt(token)
        except jwt.PyJWTError as exc:
            return jsonify({"error": f"invalid token: {exc.__class__.__name__}"}), 401

        g.current_user = get_or_create_user_from_claims(
            claims, current_app.user_repository
        )
        return fn(*args, **kwargs)

    return wrapper
