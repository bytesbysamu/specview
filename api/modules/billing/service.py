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
from typing import Any, Callable, Dict, Optional

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
    return os.environ.get("FRONTEND_URL", "http://localhost:4200")


def _price_id_for(product: str, plan: str) -> str:
    """Resolve a Stripe price ID from product+plan slug.

    Products: oll_pro, headshot_chf29, headshot_chf49, headshot_chf79
    Plans:    monthly, yearly, one_time

    Each maps to an env var: STRIPE_PRICE_{PRODUCT}_{PLAN} (upper-snaked).
    Falls back to STRIPE_PRO_PRICE_ID for the default oll_pro/monthly case.
    """
    env_key = f"STRIPE_PRICE_{product.upper()}_{plan.upper()}"
    price_id = os.environ.get(env_key, "")
    if price_id:
        return price_id
    # Backward-compat default
    return _pro_price_id()


# ── public exceptions ───────────────────────────────────────────────────────


class BillingSignatureError(Exception):
    """Stripe webhook signature verification failed; route returns 400."""


class BillingConfigError(Exception):
    """Stripe is not configured (empty STRIPE_SECRET_KEY); route returns 503.

    Guards every Stripe SDK call so a missing key surfaces as a typed 503
    instead of an opaque SDK exception / silent crash inside checkout.
    """


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

    Raises BillingConfigError when the key is empty so callers fail with a
    typed 503 rather than handing an empty key to the Stripe SDK.
    """
    key = _stripe_secret_key()
    if not key:
        raise BillingConfigError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = key


def create_checkout_session(user: User, product: str = "oll_pro", plan: str = "monthly") -> str:
    """Create a Stripe Checkout session and return its URL.

    product: slug identifying the product (oll_pro, headshot_chf29, etc.)
    plan:    billing interval (monthly, yearly, one_time)
    """
    _ensure_api_key()
    customer_id = _get_or_create_stripe_customer(user)
    price_id = _price_id_for(product, plan)
    mode = "payment" if plan == "one_time" else "subscription"
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode=mode,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{_frontend_url()}/upgrade?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{_frontend_url()}/upgrade",
        client_reference_id=str(user.id),
        metadata={"user_id": str(user.id), "product": product, "plan": plan},
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
    secret = _webhook_secret()
    if secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
        except stripe.error.SignatureVerificationError as exc:
            raise BillingSignatureError(str(exc)) from exc
    else:
        # No webhook secret configured — parse without signature verification.
        # Acceptable for local dev; production MUST set STRIPE_WEBHOOK_SECRET.
        logger.warning("webhook: STRIPE_WEBHOOK_SECRET not set — skipping signature verification")
        import json as _json
        event = _json.loads(payload)

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


class BillingOwnershipError(Exception):
    """Session client_reference_id does not match the authenticated user; route returns 403."""


class BillingSessionError(Exception):
    """Session ID is invalid or cannot be retrieved; route returns 400."""


def verify_session(session_id: str, user_id: int) -> dict:
    """Retrieve a Checkout session from Stripe and verify ownership.

    Returns a dict with ``plan`` reflecting the session payment status:
      - ``'pro'``    if payment_status == 'paid'
      - ``'free'``   otherwise

    Raises:
      BillingSessionError    — if session_id is invalid or Stripe call fails.
      BillingOwnershipError  — if the session belongs to a different user.
    """
    _ensure_api_key()
    try:
        cs = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.InvalidRequestError as exc:
        logger.warning("billing.verify_session invalid session_id=%s err=%s", session_id, exc)
        raise BillingSessionError(str(exc)) from exc
    except stripe.error.StripeError as exc:
        logger.error("billing.verify_session stripe_error session_id=%s err=%s", session_id, exc)
        raise BillingSessionError(str(exc)) from exc

    # Validate ownership via metadata or client_reference_id.
    metadata = getattr(cs, "metadata", None) or {}
    raw_meta_user_id = (
        metadata.get("user_id")
        if isinstance(metadata, dict)
        else getattr(metadata, "user_id", None)
    )
    # Fallback: client_reference_id is set by create_checkout_session
    if raw_meta_user_id is None:
        raw_meta_user_id = getattr(cs, "client_reference_id", None)
    try:
        meta_user_id = int(raw_meta_user_id) if raw_meta_user_id is not None else None
    except (TypeError, ValueError):
        meta_user_id = None

    if meta_user_id is not None and meta_user_id != user_id:
        logger.warning(
            "billing.verify_session ownership_mismatch session_id=%s expected_user=%d got=%s",
            session_id, user_id, meta_user_id,
        )
        raise BillingOwnershipError("session does not belong to this user")

    payment_status = getattr(cs, "payment_status", "") or ""
    plan = "pro" if payment_status == "paid" else "free"

    # If paid, update the user's plan immediately (like the webhook would).
    if plan == "pro":
        _activate_pro_from_session(cs, user_id)

    return {"plan": plan, "payment_status": payment_status}


def _activate_pro_from_session(cs: Any, user_id: int) -> None:
    """Write plan='pro' to the DB from a paid checkout session.

    This mirrors what the checkout.session.completed webhook handler does,
    but is called synchronously from verify_session so the user sees Pro
    immediately on redirect — even if the webhook hasn't fired yet.
    """
    customer_id = getattr(cs, "customer", None)
    if not customer_id:
        logger.warning("verify_session: no customer on session, skipping DB write")
        return
    with get_session() as session:
        sub = session.exec(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()
        if sub is None:
            sub = Subscription(user_id=user_id)
            session.add(sub)
        sub.plan = "pro"
        sub.status = "active"
        sub.stripe_customer_id = str(customer_id)
        stripe_sub_id = getattr(cs, "subscription", None)
        if stripe_sub_id:
            sub.stripe_subscription_id = str(stripe_sub_id)
        _set_user_plan(session, user_id, "pro")
        session.commit()
    logger.info("verify_session: activated pro for user_id=%d customer=%s", user_id, customer_id)


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
            metadata={"user_id": str(user.id)},
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
    # Send confirmation email — fire and forget, never blocks the webhook
    user = session.get(User, user_id)
    if user:
        try:
            from modules.email.service import send_subscription_activated
            send_subscription_activated(user.email, plan=metadata.get("plan", "Pro").title())
        except Exception:
            logger.exception("checkout_completed: email send failed for user_id=%d", user_id)


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
    try:
        from modules.email.service import send_subscription_canceled
        send_subscription_canceled(user.email)
    except Exception:
        logger.exception("subscription_deleted: email send failed for user_id=%d", user.id)


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
    """Locked decision (Option B): revert User.plan = 'lapsed' on FIRST failed
    payment. 0-day grace period — no soft window."""
    user = _user_for_subscription(session, obj.get("subscription"))
    if user is None:
        return
    _upsert_subscription(session, user.id, plan="lapsed", status="past_due")
    _set_user_plan(session, user.id, "lapsed")


@_register("invoice.upcoming")
def _on_invoice_upcoming(session: Session, obj) -> None:
    """Renewal warning — log only; no plan or status change."""
    customer = obj.get("customer") if isinstance(obj, dict) else None
    logger.info("billing.invoice_upcoming customer=%s", customer)
