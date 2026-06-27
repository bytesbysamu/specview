"""Flask blueprint for /api/auth/* — passwordless magic-link auth.

Flow:
  1. POST /api/auth/magic-link {email}  → emails a single-use sign-in link.
  2. POST /api/auth/verify {token}      → validates the token, find-or-creates
                                          the User, returns a JWT.
  3. GET  /api/auth/me                   → current user.
  4. POST /api/auth/refresh              → re-issue a JWT.

There are no passwords anywhere in the product.
"""
from __future__ import annotations

import hashlib
import logging

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError
from sqlmodel import Session

from dtos.models import (
    AuthTokenResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    MeResponse,
    VerifyRequest,
    VerifyResponse,
)
from modules.auth.decorators import require_auth
from modules.auth.models import User
from modules.auth.rate_limit import ip_rate_limit
from modules.auth.service import (
    consume_magic_link_token,
    create_magic_link_token,
    create_token,
    find_or_create_user,
    normalize_email,
    refresh_token_for_user,
    token_expires_at_iso,
)
from config import verify_base_for_product
from modules.data.db.engine import get_engine
from modules.email.service import send_magic_link
from modules.observability.errors import core_error

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/magic-link")
@ip_rate_limit
def magic_link():
    """POST /api/auth/magic-link — {email, product?} → {sent: true} (always 200).

    Mints a single-use token, emails the sign-in link, and ALWAYS reports
    success so the response cannot be used to enumerate which emails have
    accounts. Rate-limited per IP.

    ``product`` selects which frontend the verify link points at, resolved
    against Core's per-product allow-list. An unknown product is rejected 400
    — that leaks nothing about the account (it is purely a config error), so
    anti-enumeration is preserved.
    """
    try:
        req = MagicLinkRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError:
        # Uniform 200 even on a malformed email keeps this endpoint free of
        # account-enumeration / probing signal.
        return jsonify(MagicLinkResponse(sent=True).model_dump()), 200

    product = getattr(req, "product", None)
    verify_base = verify_base_for_product(product)
    if verify_base is None:
        return core_error("INVALID_PRODUCT", f"unknown product: {product}", 400)

    email = normalize_email(str(req.email))

    with Session(get_engine()) as session:
        raw_token = create_magic_link_token(session, email)

    link = f"{verify_base}/auth/verify?token={raw_token}"
    send_magic_link(email, link)  # best-effort; never raises, never blocks 200

    email_hash = hashlib.sha256(email.encode()).hexdigest()[:12]
    logger.info("magic link issued email_hash=%s", email_hash)
    return jsonify(MagicLinkResponse(sent=True).model_dump()), 200


@auth_bp.post("/verify")
def verify():
    """POST /api/auth/verify — {token} → {token, email}.

    Validates the single-use magic-link token, marks it used, find-or-creates
    the User by email, and issues a JWT.
    """
    try:
        req = VerifyRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError:
        return core_error("INVALID_TOKEN", "invalid or expired token", 401)

    with Session(get_engine()) as session:
        email = consume_magic_link_token(session, req.token)
        if email is None:
            return core_error("INVALID_TOKEN", "invalid or expired token", 401)
        user = find_or_create_user(session, email)
        user_id, user_email = user.id, user.email

    token = create_token(user_id, user_email)
    email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:12]
    logger.info("magic link verified email_hash=%s", email_hash)
    return jsonify(VerifyResponse(token=token, email=user_email).model_dump()), 200


@auth_bp.get("/me")
@require_auth
def me():
    """GET /api/auth/me — returns {id, email, plan, token_expires_at} for the authenticated user."""
    user: User = g.current_user
    raw_token = request.headers.get("Authorization", "")[len("Bearer "):]
    expires_at = None
    if raw_token:
        try:
            expires_at = token_expires_at_iso(raw_token)
        except Exception:
            # The token already passed require_auth; a decode failure here
            # (e.g. a non-JWT test stub) must not 500 the endpoint.
            expires_at = None
    body = MeResponse(
        id=user.id,
        email=user.email,
        plan=(user.plan or "free"),
        token_expires_at=expires_at,
    )
    return jsonify(body.model_dump(mode="json")), 200


@auth_bp.post("/refresh")
@require_auth
def refresh():
    """POST /api/auth/refresh — issues a fresh JWT for the authenticated user."""
    if g.current_user is None:
        return core_error("UNAUTHORIZED", "authentication required", 401)
    user: User = g.current_user
    token = refresh_token_for_user(user.id, user.email)
    user_id_hash = hashlib.sha256(str(user.id).encode()).hexdigest()[:12]
    logger.info("token refreshed for user_id_hash=%s", user_id_hash)
    return jsonify(AuthTokenResponse(token=token, email=user.email).model_dump()), 200
