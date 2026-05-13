"""Unit coverage for the six webhook handlers.

Each handler is exercised through its registered key in service._HANDLERS so
the dispatch table itself is also under test.
"""
from __future__ import annotations
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from modules.auth.models import User
from modules.billing import service as billing_service
from modules.billing.models import Subscription


# ── helpers (wrapped in a class to bypass pytest's permissive collection) ───


class H:
    """Test helpers. Class wrapper hides them from pytest's python_functions
    glob ('test_*', '*_*') which would otherwise treat H.seed /
    H.user / H.sub as test cases and try to autoresolve their args."""

    @staticmethod
    def seed(
        db_session: Session,
        *,
        auth_user_id: str = "auth-x",
        email: str = "x@example.com",
        customer_id: str | None = None,
        subscription_id: str | None = None,
        plan: str = "free",
        status: str = "active",
    ) -> User:
        user = User(auth_user_id=auth_user_id, email=email, plan=plan)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        sub = Subscription(
            user_id=user.id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            plan=plan,
            status=status,
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)
        return user

    @staticmethod
    def user(db_session: Session, user_id: int) -> User:
        db_session.expire_all()
        return db_session.get(User, user_id)

    @staticmethod
    def sub(db_session: Session, user_id: int) -> Subscription:
        db_session.expire_all()
        return db_session.exec(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()


# ── registry ────────────────────────────────────────────────────────────────


def test_six_handlers_registered_with_locked_event_names():
    assert set(billing_service._HANDLERS.keys()) == {
        "checkout.session.completed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
        "invoice.upcoming",
    }


# ── checkout.session.completed ──────────────────────────────────────────────


def test_checkout_completed_promotes_user_to_pro(db_session, make_user):
    user = make_user(auth_user_id="auth-checkout", email="c@example.com")
    obj = {
        "metadata": {"auth_user_id": user.auth_user_id, "user_id": str(user.id)},
        "customer": "cus_abc",
        "subscription": "sub_abc",
    }
    handler = billing_service._HANDLERS["checkout.session.completed"]
    handler(db_session, obj)
    db_session.commit()

    sub = H.sub(db_session, user.id)
    assert sub is not None
    assert sub.plan == "pro"
    assert sub.status == "active"
    assert sub.stripe_customer_id == "cus_abc"
    assert sub.stripe_subscription_id == "sub_abc"
    assert H.user(db_session, user.id).plan == "pro"


def test_checkout_completed_ignored_when_user_id_metadata_missing(db_session):
    handler = billing_service._HANDLERS["checkout.session.completed"]
    handler(db_session, {"metadata": {}, "customer": "cus_x", "subscription": "sub_x"})
    db_session.commit()
    # No subscription rows should have been created.
    assert db_session.exec(select(Subscription)).first() is None


# ── customer.subscription.updated ───────────────────────────────────────────


def test_subscription_updated_writes_period_dates_and_status(db_session):
    user = H.seed(db_session, customer_id="cus_upd")
    handler = billing_service._HANDLERS["customer.subscription.updated"]
    handler(
        db_session,
        {
            "id": "sub_new",
            "customer": "cus_upd",
            "status": "active",
            "current_period_start": 1_700_000_000,
            "current_period_end": 1_702_000_000,
            "cancel_at_period_end": False,
        },
    )
    db_session.commit()

    sub = H.sub(db_session, user.id)
    assert sub.status == "active"
    assert sub.current_period_start == datetime.utcfromtimestamp(1_700_000_000)
    assert sub.current_period_end == datetime.utcfromtimestamp(1_702_000_000)
    assert sub.stripe_subscription_id == "sub_new"
    # Plan must NOT be touched by 'updated'.
    assert H.user(db_session, user.id).plan == "free"


def test_subscription_updated_records_canceled_at_when_cancel_scheduled(db_session):
    user = H.seed(db_session, customer_id="cus_cancel")
    handler = billing_service._HANDLERS["customer.subscription.updated"]
    handler(
        db_session,
        {
            "id": "sub_cancel",
            "customer": "cus_cancel",
            "status": "active",
            "current_period_start": 1_700_000_000,
            "current_period_end": 1_702_000_000,
            "cancel_at_period_end": True,
            "cancel_at": 1_703_000_000,
        },
    )
    db_session.commit()

    sub = H.sub(db_session, user.id)
    assert sub.canceled_at == datetime.utcfromtimestamp(1_703_000_000)


# ── customer.subscription.deleted ───────────────────────────────────────────


def test_subscription_deleted_reverts_user_to_free(db_session):
    user = H.seed(
        db_session, customer_id="cus_del", plan="pro", status="active"
    )
    db_session.get(User, user.id).plan = "pro"
    db_session.commit()

    handler = billing_service._HANDLERS["customer.subscription.deleted"]
    handler(db_session, {"customer": "cus_del"})
    db_session.commit()

    sub = H.sub(db_session, user.id)
    assert sub.plan == "free"
    assert sub.status == "canceled"
    assert sub.canceled_at is not None
    assert H.user(db_session, user.id).plan == "free"


# ── invoice.payment_succeeded ───────────────────────────────────────────────


def test_invoice_payment_succeeded_sets_active_and_bumps_period(db_session):
    user = H.seed(
        db_session, customer_id="cus_ok", subscription_id="sub_ok", status="past_due"
    )
    handler = billing_service._HANDLERS["invoice.payment_succeeded"]
    handler(
        db_session,
        {
            "subscription": "sub_ok",
            "lines": {"data": [{"period": {"end": 1_705_000_000}}]},
        },
    )
    db_session.commit()

    sub = H.sub(db_session, user.id)
    assert sub.status == "active"
    assert sub.current_period_end == datetime.utcfromtimestamp(1_705_000_000)


# ── invoice.payment_failed (Option B — 0-day grace) ─────────────────────────


def test_invoice_payment_failed_reverts_plan_to_lapsed_immediately(db_session):
    """Locked decision: Option B writes User.plan = 'lapsed' on FIRST failed payment."""
    user = H.seed(
        db_session,
        customer_id="cus_pd",
        subscription_id="sub_pd",
        plan="pro",
        status="active",
    )
    db_session.get(User, user.id).plan = "pro"
    db_session.commit()

    handler = billing_service._HANDLERS["invoice.payment_failed"]
    handler(db_session, {"subscription": "sub_pd"})
    db_session.commit()

    sub = H.sub(db_session, user.id)
    assert sub.status == "past_due"
    assert sub.plan == "lapsed"
    assert H.user(db_session, user.id).plan == "lapsed"


def test_invoice_payment_failed_noop_when_subscription_unknown(db_session):
    handler = billing_service._HANDLERS["invoice.payment_failed"]
    handler(db_session, {"subscription": "sub_unknown"})
    db_session.commit()
    assert db_session.exec(select(Subscription)).first() is None


# ── invoice.upcoming (renewal warning — log only) ───────────────────────────


def test_invoice_upcoming_does_not_mutate_state(db_session, caplog):
    user = H.seed(db_session, customer_id="cus_warn", plan="pro")
    db_session.get(User, user.id).plan = "pro"
    db_session.commit()

    handler = billing_service._HANDLERS["invoice.upcoming"]
    with caplog.at_level("INFO"):
        handler(db_session, {"customer": "cus_warn"})
    db_session.commit()

    sub = H.sub(db_session, user.id)
    # No changes — plan and status untouched.
    assert sub.plan == "pro"
    assert H.user(db_session, user.id).plan == "pro"


# ── webhook dispatch + signature verification ───────────────────────────────


def test_handle_webhook_raises_billing_signature_error_on_bad_sig(monkeypatch):
    import stripe

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    def _raise(*_a, **_kw):
        raise stripe.error.SignatureVerificationError("bad sig", "sig-header")

    monkeypatch.setattr(stripe.Webhook, "construct_event", _raise)
    with pytest.raises(billing_service.BillingSignatureError):
        billing_service.handle_webhook(b"{}", "sig-header")


def test_handle_webhook_dispatches_to_registered_handler(monkeypatch, db_session):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    user = H.seed(
        db_session,
        customer_id="cus_dispatch",
        subscription_id="sub_dispatch",
        plan="pro",
    )
    db_session.get(User, user.id).plan = "pro"
    db_session.commit()

    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"subscription": "sub_dispatch"}},
    }
    monkeypatch.setattr(
        "modules.billing.service.stripe.Webhook.construct_event",
        lambda *a, **kw: event,
    )

    billing_service.handle_webhook(b"{}", "ok-sig")

    sub = H.sub(db_session, user.id)
    assert sub.status == "past_due"
    assert H.user(db_session, user.id).plan == "lapsed"


def test_handle_webhook_ignores_unregistered_event_types(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    event = {"type": "some.other.event", "data": {"object": {}}}
    monkeypatch.setattr(
        "modules.billing.service.stripe.Webhook.construct_event",
        lambda *a, **kw: event,
    )
    # Must not raise.
    billing_service.handle_webhook(b"{}", "ok-sig")


# ── checkout / portal session SDK calls ─────────────────────────────────────


def test_create_checkout_session_invokes_stripe_with_pro_price(monkeypatch, make_user):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_PRO_PRICE_ID", "price_pro_test")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:4201")

    user = make_user(auth_user_id="auth-cs", email="cs@example.com")

    fake_customer = type("C", (), {"id": "cus_new"})()
    fake_session = type("S", (), {"url": "https://checkout.stripe.com/pay/x"})()

    with (
        patch.object(billing_service.stripe.Customer, "create", return_value=fake_customer) as customer_create,
        patch.object(
            billing_service.stripe.checkout.Session,
            "create",
            return_value=fake_session,
        ) as session_create,
    ):
        url = billing_service.create_checkout_session(user)

    assert url == "https://checkout.stripe.com/pay/x"
    customer_create.assert_called_once()
    kwargs = session_create.call_args.kwargs
    assert kwargs["customer"] == "cus_new"
    assert kwargs["mode"] == "subscription"
    assert kwargs["line_items"] == [{"price": "price_pro_test", "quantity": 1}]
    assert "upgrade?session_id=" in kwargs["success_url"]
    assert kwargs["cancel_url"].endswith("/upgrade")


def test_create_portal_session_returns_stripe_url(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:4201")
    fake_portal = type("P", (), {"url": "https://billing.stripe.com/p/session/abc"})()

    with patch.object(
        billing_service.stripe.billing_portal.Session, "create", return_value=fake_portal
    ) as portal_create:
        url = billing_service.create_portal_session("cus_zzz")

    assert url == "https://billing.stripe.com/p/session/abc"
    portal_create.assert_called_once()
    assert portal_create.call_args.kwargs["customer"] == "cus_zzz"
    assert portal_create.call_args.kwargs["return_url"].endswith("/settings")


# ── verify_session ───────────────────────────────────────────────────────────


def test_verify_session_returns_pro_for_paid_session(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    fake_cs = type("CS", (), {
        "payment_status": "paid",
        "metadata": {"user_id": "42"},
        "customer": None,
    })()
    with patch.object(
        billing_service.stripe.checkout.Session, "retrieve", return_value=fake_cs
    ) as retrieve:
        result = billing_service.verify_session("cs_test_abc", 42)

    retrieve.assert_called_once_with("cs_test_abc")
    assert result["plan"] == "pro"
    assert result["payment_status"] == "paid"


def test_verify_session_returns_free_for_unpaid_session(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    fake_cs = type("CS", (), {
        "payment_status": "unpaid",
        "metadata": {"user_id": "7"},
        "customer": None,
    })()
    with patch.object(
        billing_service.stripe.checkout.Session, "retrieve", return_value=fake_cs
    ):
        result = billing_service.verify_session("cs_test_xyz", 7)

    assert result["plan"] == "free"
    assert result["payment_status"] == "unpaid"


def test_verify_session_raises_ownership_error_on_user_mismatch(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    fake_cs = type("CS", (), {
        "payment_status": "paid",
        "metadata": {"user_id": "99"},
        "customer": None,
    })()
    with patch.object(
        billing_service.stripe.checkout.Session, "retrieve", return_value=fake_cs
    ):
        with pytest.raises(billing_service.BillingOwnershipError):
            billing_service.verify_session("cs_test_mismatch", 42)


def test_verify_session_raises_session_error_on_invalid_id(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    import stripe as _stripe

    with patch.object(
        billing_service.stripe.checkout.Session,
        "retrieve",
        side_effect=_stripe.error.InvalidRequestError("No such session", "session_id"),
    ):
        with pytest.raises(billing_service.BillingSessionError):
            billing_service.verify_session("cs_bad_id", 1)
