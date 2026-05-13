"""Billing Blueprint — three routes match openapi.yaml operationIds.

  POST /api/billing/create-checkout-session  -> createCheckoutSession
  POST /api/billing/webhook                  -> stripeWebhook
  GET  /api/billing/status                   -> getBillingStatus

Routes import only from .service / .decorators and modules.data.db; no
direct stripe import lives here. The service layer is the sole Stripe
adapter (ELA #1).
"""
from __future__ import annotations

from datetime import timezone
from typing import Optional

from flask import Blueprint, g, jsonify, request
from sqlmodel import select

from dtos.models import (
    BillingStatusResponse,
    CheckoutSessionResponse,
    Plan,
    Status1,
    WebhookAckResponse,
)
from modules.auth.models import User
from modules.data.db.session import get_session

from modules.auth.decorators import require_auth

from .models import Subscription
from .service import (
    BillingOwnershipError,
    BillingSessionError,
    BillingSignatureError,
    create_checkout_session,
    create_portal_session,
    handle_webhook,
    verify_session,
)


billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


def _get_or_create_user(auth_user_id: str, email: str) -> User:
    """Idempotent User lookup keyed on auth_user_id (Neon Auth subject)."""
    with get_session() as session:
        user = session.exec(
            select(User).where(User.auth_user_id == auth_user_id)
        ).first()
        if user is None:
            user = User(auth_user_id=auth_user_id, email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user


@billing_bp.post("/create-checkout-session")
@require_auth
def create_checkout():
    user = _get_or_create_user(g.current_user.auth_user_id, g.current_user.email)
    url = create_checkout_session(user)
    return jsonify(CheckoutSessionResponse(url=url).model_dump()), 200


@billing_bp.post("/webhook")
def stripe_webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        handle_webhook(payload, sig)
    except BillingSignatureError:
        return jsonify({"error": "invalid_signature"}), 400
    return jsonify(WebhookAckResponse(received=True).model_dump()), 200


def _to_aware_iso(dt) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@billing_bp.get("/status")
@require_auth
def billing_status():
    """Canonical BillingStatus shape consumed by Mon-T4 (Angular SubscriptionService).

    Response mirrors openapi.yaml#/components/schemas/BillingStatusResponse:
      - plan: 'free' | 'pro' (always present)
      - status: 'active' | 'past_due' | 'canceled' | None
      - current_period_end: ISO-8601 UTC datetime | None
      - manage_url: live Stripe Customer Portal URL | None
    """
    user = _get_or_create_user(g.current_user.auth_user_id, g.current_user.email)

    with get_session() as session:
        sub = session.exec(
            select(Subscription).where(Subscription.user_id == user.id)
        ).first()

    raw_plan = (sub.plan if sub else None) or user.plan or "free"
    # 'lapsed' is a valid DB state (payment failed, no grace period) but is not
    # a Plan enum value in the openapi contract.  Surface it as 'free' so the
    # response DTO validates cleanly; the Angular layer treats both identically.
    _PLAN_MAP = {"pro": "pro"}
    plan_value = _PLAN_MAP.get(raw_plan, "free")
    status_value: Optional[str] = sub.status if sub else None
    period_end = sub.current_period_end if sub else None
    customer_id = sub.stripe_customer_id if sub else None

    manage_url: Optional[str] = None
    if customer_id:
        manage_url = create_portal_session(customer_id)

    body = BillingStatusResponse(
        plan=Plan(plan_value),
        status=Status1(status_value) if status_value else None,
        current_period_end=_to_aware_iso(period_end),
        manage_url=manage_url,
    )
    return jsonify(body.model_dump(mode="json")), 200


@billing_bp.get("/verify-session")
@require_auth
def verify_checkout_session():
    """Resolve plan state after Stripe Checkout redirect.

    POST-checkout the SPA lands on /billing/success?session_id=<id>. It calls
    this endpoint to confirm the payment completed before trusting g.current_user.plan,
    which lags by up to one webhook delivery.

    Query params:
      session_id (required) — Stripe Checkout session ID (cs_…)

    Returns:
      200 {"plan": "pro"|"free", "payment_status": str}
      400 {"error": "missing session_id"} — query param absent
      400 {"error": str} — invalid / unresolvable session
      403 {"error": str} — session belongs to a different user
    """
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "missing session_id"}), 400

    user = _get_or_create_user(g.current_user.auth_user_id, g.current_user.email)
    try:
        result = verify_session(session_id, user.id)
    except BillingOwnershipError as exc:
        return jsonify({"error": str(exc)}), 403
    except BillingSessionError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result), 200
