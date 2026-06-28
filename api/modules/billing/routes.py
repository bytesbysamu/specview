"""Billing Blueprint — POST /api/billing/create-checkout-session
                        POST /api/billing/webhook
                        GET  /api/billing/status
                        GET  /api/billing/verify-session
                        POST /api/billing/portal

Routes import only from .service; no direct stripe import lives here.
The service layer is the sole Stripe adapter (Adapter pattern, Ch.6).

Fix: _get_or_create_user was keyed on auth_user_id which is None for
password-auth users — replaced with direct g.current_user (already loaded
from DB by require_auth).
"""
from __future__ import annotations

from datetime import timezone
from typing import Optional

from flask import Blueprint, g, jsonify, request
from sqlmodel import select

from dtos.models import (
    BillingStatusResponse,
    CheckoutSessionResponse,
    Plan1,
    PortalSessionResponse,
    Status1,
    WebhookAckResponse,
)
from modules.auth.models import User
from modules.data.db.session import get_session

from modules.auth.decorators import require_auth
from modules.observability.errors import core_error

from .models import Subscription
from .service import (
    BillingConfigError,
    BillingError,
    BillingOwnershipError,
    BillingSessionError,
    BillingSignatureError,
    create_checkout_session,
    create_portal_session,
    handle_webhook,
    verify_session,
)

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


def _to_aware_iso(dt) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


@billing_bp.post("/create-checkout-session")
@require_auth
def create_checkout():
    """POST /api/billing/create-checkout-session

    Optional body:
      { "product": "oll_pro", "plan": "monthly" }  — defaults to oll_pro/monthly

    Returns: { "url": "https://checkout.stripe.com/..." }
    """
    body = request.get_json(silent=True) or {}
    product = body.get("product", "oll_pro")
    plan = body.get("plan", "monthly")
    user: User = g.current_user
    try:
        url = create_checkout_session(user, product=product, plan=plan)
    except BillingConfigError as exc:
        return core_error("STRIPE_NOT_CONFIGURED", str(exc), 503)
    except BillingError as exc:
        return core_error("CHECKOUT_FAILED", str(exc), 502)
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


@billing_bp.get("/status")
@require_auth
def billing_status():
    """GET /api/billing/status — returns plan + subscription state for the authed user."""
    if g.current_user is None:
        return jsonify(BillingStatusResponse(
            plan=Plan1("free"), status=None,
            current_period_end=None, manage_url=None,
        ).model_dump(mode="json")), 200

    user: User = g.current_user

    with get_session() as session:
        sub = session.exec(
            select(Subscription).where(Subscription.user_id == user.id)
        ).first()

    raw_plan = (sub.plan if sub else None) or user.plan or "free"
    plan_value = "pro" if raw_plan == "pro" else "free"
    status_value: Optional[str] = sub.status if sub else None
    period_end = sub.current_period_end if sub else None
    customer_id = sub.stripe_customer_id if sub else None

    manage_url: Optional[str] = None
    if customer_id:
        try:
            manage_url = create_portal_session(customer_id)
        except Exception:
            # Degrade gracefully — a portal-URL failure (Stripe down or
            # unconfigured) must not 500 the whole status read. The client
            # simply gets manage_url=null.
            manage_url = None

    body = BillingStatusResponse(
        plan=Plan1(plan_value),
        status=Status1(status_value) if status_value else None,
        current_period_end=_to_aware_iso(period_end),
        manage_url=manage_url,
    )
    return jsonify(body.model_dump(mode="json")), 200


@billing_bp.get("/verify-session")
@require_auth
def verify_checkout_session():
    """GET /api/billing/verify-session?session_id=cs_...

    Confirms payment completed after Stripe Checkout redirect.
    Returns: { "plan": "pro"|"free", "payment_status": str }
    """
    session_id = request.args.get("session_id", "").strip()
    if not session_id:
        return core_error("MISSING_PARAM", "missing session_id", 400)

    user: User = g.current_user
    try:
        result = verify_session(session_id, user.id)
    except BillingOwnershipError as exc:
        return core_error("OWNERSHIP_MISMATCH", str(exc), 403)
    except BillingSessionError as exc:
        return core_error("INVALID_SESSION", str(exc), 400)
    except BillingConfigError as exc:
        return core_error("STRIPE_NOT_CONFIGURED", str(exc), 503)

    return jsonify(result), 200


@billing_bp.post("/portal")
@require_auth
def billing_portal():
    """POST /api/billing/portal — returns Stripe Customer Portal URL.

    Returns: { "url": "https://billing.stripe.com/..." }
    """
    user: User = g.current_user

    with get_session() as session:
        sub = session.exec(
            select(Subscription).where(Subscription.user_id == user.id)
        ).first()

    customer_id = sub.stripe_customer_id if sub else None
    if not customer_id:
        return core_error("NO_SUBSCRIPTION", "no active subscription found", 404)

    try:
        url = create_portal_session(customer_id)
    except BillingConfigError as exc:
        return core_error("STRIPE_NOT_CONFIGURED", str(exc), 503)
    return jsonify(PortalSessionResponse(url=url).model_dump()), 200
