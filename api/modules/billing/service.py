"""Billing service — sole Stripe SDK import boundary (ELA #1 adapter).

Public surface:
  - create_checkout_session(user) -> str  (Stripe-hosted URL)
  - create_portal_session(stripe_customer_id) -> str
  - handle_webhook(payload, sig_header) -> None  (raises BillingSignatureError)
  - BillingSignatureError                  (signature failures bubble as 400)

Private webhook handlers (six events; locked decision):
  - checkout.session.completed     -> Subscription upsert + User.plan = pro
  - customer.subscription.updated  -> period dates + status; no plan write
  - customer.subscription.deleted  -> Subscription canceled + User.plan = free
  - invoice.payment_succeeded      -> status=active, bump current_period_end
  - invoice.payment_failed         -> User.plan = free (Option B; 0-day grace)
  - invoice.upcoming               -> log only; no state change

The webhook is the SOLE writer of User.plan. No other code path may
mutate User.plan; the test suite enforces that boundary.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Callable, Dict, Optional

import stripe
from sqlmodel import Session, select

from modules.auth.models import User
from modules.data.db.session import get_session

from .models import Subscription


logger = logging.getLogger(__name__)


# ── env config (read at module load; tests override via monkeypatch) ────────


def _stripe_secret_key() -> str:
    return os.environ.get("STRIPE_SECRET_KEY", "")


def _webhook_secret() -> str:
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def _pro_price_id() -> str:
    return os.environ.get("STRIPE_PRO_PRICE_ID", "")


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:4201")


# ── public exceptions ───────────────────────────────────────────────────────


class BillingSignatureError(Exception):
    """Stripe webhook signature verification failed; route returns 400."""


# ── handler registry ────────────────────────────────────────────────────────


_HANDLERS: Dict[str, Callable[[Session, dict], None]] = {}


def _register(event_type: str):
    def decorator(fn):
        _HANDLERS[event_type] = fn
        return fn

    return decorator


# ── Stripe SDK calls (the only place stripe.* is used) ──────────────────────


def _ensure_api_key() -> None:
    """Set the Stripe SDK api_key from env on every call.

    Tests monkeypatch STRIPE_SECRET_KEY between cases; reading it here keeps
    the module import-time cache in sync with whatever the test set.
    """
    stripe.api_key = _stripe_secret_key()


def create_checkout_session(user: User) -> str:
    """Create a Stripe Checkout session for the Pro plan and return its URL."""
    _ensure_api_key()
    customer_id = _get_or_create_stripe_customer(user)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": _pro_price_id(), "quantity": 1}],
        success_url=f"{_frontend_url()}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{_frontend_url()}/upgrade",
        metadata={"auth_user_id": user.auth_user_id, "user_id": str(user.id)},
    )
    return session.url


def create_portal_session(stripe_customer_id: str) -> str:
    """Create a one-shot Stripe Customer Portal URL for self-service management."""
    _ensure_api_key()
    portal = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{_frontend_url()}/settings",
    )
    return portal.url


def handle_webhook(payload: bytes, sig_header: str) -> None:
    """Verify the Stripe signature, then dispatch the event to its handler.

    Raises BillingSignatureError on signature failure so routes.py can return 400
    without importing stripe directly. Unrecognised event types are ignored
    (Stripe sends events the app doesn't subscribe to in some account configs).
    """
    _ensure_api_key()
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, _webhook_secret()
        )
    except stripe.error.SignatureVerificationError as exc:
        raise BillingSignatureError(str(exc)) from exc

    event_type = event["type"] if isinstance(event, dict) else event.type
    obj = (
        event["data"]["object"]
        if isinstance(event, dict)
        else event.data.object
    )

    handler = _HANDLERS.get(event_type)
    if handler is None:
        logger.info("billing.webhook ignored event_type=%s", event_type)
        return

    with get_session() as session:
        handler(session, obj)
        session.commit()


def _get_or_create_stripe_customer(user: User) -> str:
    """Return the User's Stripe customer ID, creating one lazily on first call."""
    with get_session() as session:
        sub = session.exec(
            select(Subscription).where(Subscription.user_id == user.id)
        ).first()
        if sub and sub.stripe_customer_id:
            return sub.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            metadata={"auth_user_id": user.auth_user_id, "user_id": str(user.id)},
        )
        if sub is None:
            sub = Subscription(
                user_id=user.id,
                stripe_customer_id=customer.id,
                plan="free",
                status="active",
            )
        else:
            sub.stripe_customer_id = customer.id
        session.add(sub)
        session.commit()
        return customer.id


# ── webhook handlers (six total — one per locked-decision event) ────────────


def _ts_to_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.utcfromtimestamp(int(value))


def _user_for_customer(session: Session, customer_id: Optional[str]) -> Optional[User]:
    if not customer_id:
        return None
    sub = session.exec(
        select(Subscription).where(Subscription.stripe_customer_id == customer_id)
    ).first()
    if sub is None:
        return None
    return session.get(User, sub.user_id)


def _user_for_subscription(
    session: Session, subscription_id: Optional[str]
) -> Optional[User]:
    if not subscription_id:
        return None
    sub = session.exec(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    ).first()
    if sub is None:
        return None
    return session.get(User, sub.user_id)


def _upsert_subscription(
    session: Session, user_id: int, **fields
) -> Subscription:
    sub = session.exec(
        select(Subscription).where(Subscription.user_id == user_id)
    ).first()
    if sub is None:
        sub = Subscription(user_id=user_id, **fields)
    else:
        for key, value in fields.items():
            setattr(sub, key, value)
    session.add(sub)
    return sub


def _set_user_plan(session: Session, user_id: int, plan: str) -> None:
    """Sole writer of User.plan in the codebase. Both Subscription.plan and
    User.plan are mutated in the same session for atomicity."""
    user = session.get(User, user_id)
    if user is not None:
        user.plan = plan
        session.add(user)


@_register("checkout.session.completed")
def _on_checkout_completed(session: Session, obj) -> None:
    metadata = obj.get("metadata") or {}
    raw_user_id = metadata.get("user_id")
    if raw_user_id is None:
        return
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError):
        return
    _upsert_subscription(
        session,
        user_id,
        plan="pro",
        status="active",
        stripe_customer_id=obj.get("customer"),
        stripe_subscription_id=obj.get("subscription"),
    )
    _set_user_plan(session, user_id, "pro")


@_register("customer.subscription.updated")
def _on_subscription_updated(session: Session, obj) -> None:
    user = _user_for_customer(session, obj.get("customer"))
    if user is None:
        return
    fields: dict = {
        "status": obj.get("status", "active"),
        "current_period_start": _ts_to_dt(obj.get("current_period_start")),
        "current_period_end": _ts_to_dt(obj.get("current_period_end")),
        "stripe_subscription_id": obj.get("id"),
    }
    if obj.get("cancel_at_period_end") and obj.get("cancel_at"):
        fields["canceled_at"] = _ts_to_dt(obj.get("cancel_at"))
    _upsert_subscription(session, user.id, **fields)


@_register("customer.subscription.deleted")
def _on_subscription_deleted(session: Session, obj) -> None:
    user = _user_for_customer(session, obj.get("customer"))
    if user is None:
        return
    _upsert_subscription(
        session,
        user.id,
        plan="free",
        status="canceled",
        canceled_at=datetime.utcnow(),
    )
    _set_user_plan(session, user.id, "free")


@_register("invoice.payment_succeeded")
def _on_invoice_payment_succeeded(session: Session, obj) -> None:
    user = _user_for_subscription(session, obj.get("subscription"))
    if user is None:
        return
    fields: dict = {"status": "active"}
    lines = (obj.get("lines") or {}).get("data") or []
    if lines:
        period = (lines[0].get("period") or {})
        end = period.get("end")
        if end is not None:
            fields["current_period_end"] = _ts_to_dt(end)
    _upsert_subscription(session, user.id, **fields)


@_register("invoice.payment_failed")
def _on_invoice_payment_failed(session: Session, obj) -> None:
    """Locked decision (Option B): revert User.plan = 'free' on FIRST failed
    payment. 0-day grace period — no soft window."""
    user = _user_for_subscription(session, obj.get("subscription"))
    if user is None:
        return
    _upsert_subscription(session, user.id, plan="free", status="past_due")
    _set_user_plan(session, user.id, "free")


@_register("invoice.upcoming")
def _on_invoice_upcoming(session: Session, obj) -> None:
    """Renewal warning — log only; no plan or status change."""
    customer = obj.get("customer") if isinstance(obj, dict) else None
    logger.info("billing.invoice_upcoming customer=%s", customer)
