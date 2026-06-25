"""Email delivery via Resend — Core shared email service.

Pattern: wardrobai email.py, generalized for multi-product use.
- Returns bool, never raises — email failure must not fail a request.
- Template variants for billing events (checkout, subscription, magic-link).
- FROM_EMAIL configurable per-product via ctx["from_email"] override.
"""
from __future__ import annotations

import logging
import os

_log = logging.getLogger(__name__)

_RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
_FROM_EMAIL = os.environ.get("FROM_EMAIL", "oll.am <hello@oll.am>")
_SITE_URL = os.environ.get("SITE_URL", "https://oll.am")


def send_email(to: str, subject: str, html: str, from_email: str | None = None) -> bool:
    """Send a transactional email via Resend. Returns True on success, False on failure."""
    if not _RESEND_API_KEY:
        _log.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return False
    try:
        import resend
        resend.api_key = _RESEND_API_KEY
        resend.Emails.send({
            "from": from_email or _FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        _log.info("email sent to=%s subject=%s", to, subject)
        return True
    except Exception as exc:
        _log.error("email failed to=%s: %s", to, exc)
        return False


def send_subscription_activated(email: str, plan: str = "Pro") -> bool:
    return send_email(
        to=email,
        subject=f"Welcome to oll.am {plan}!",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px;">
          <h2 style="color:#567B95;">You're now on oll.am {plan} ✓</h2>
          <p>Your subscription is active. All Pro features are now unlocked across every oll.am product.</p>
          <p style="text-align:center;margin:28px 0;">
            <a href="{_SITE_URL}" style="background:#567B95;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;">Open oll.am</a>
          </p>
          <p style="color:#718096;font-size:13px;">Manage your subscription anytime from your account settings.</p>
        </div>
        """,
    )


def send_subscription_canceled(email: str) -> bool:
    return send_email(
        to=email,
        subject="Your oll.am Pro subscription has been canceled",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px;">
          <h2 style="color:#567B95;">Subscription Canceled</h2>
          <p>Your oll.am Pro subscription has been canceled. You'll keep access until the end of your current billing period.</p>
          <p>You can resubscribe anytime at <a href="{_SITE_URL}/pricing">{_SITE_URL}/pricing</a>.</p>
          <p style="color:#718096;font-size:13px;">Questions? Reply to this email.</p>
        </div>
        """,
    )


def send_payment_failed(email: str) -> bool:
    return send_email(
        to=email,
        subject="oll.am — payment failed",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px;">
          <h2 style="color:#C41E3A;">Payment failed</h2>
          <p>We couldn't charge your payment method for your oll.am Pro subscription.</p>
          <p>Please update your payment details to keep Pro access:</p>
          <p style="text-align:center;margin:28px 0;">
            <a href="{_SITE_URL}/account" style="background:#567B95;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;">Update payment method</a>
          </p>
          <p style="color:#718096;font-size:13px;">Your account has been downgraded to the free plan until payment is resolved.</p>
        </div>
        """,
    )


def send_magic_link(email: str, link: str) -> bool:
    return send_email(
        to=email,
        subject="Your oll.am sign-in link",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px;">
          <h2 style="color:#567B95;">Sign in to oll.am</h2>
          <p>Click the button below to sign in. This link expires in 15 minutes.</p>
          <p style="text-align:center;margin:28px 0;">
            <a href="{link}" style="background:#567B95;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;">Sign in</a>
          </p>
          <p style="color:#718096;font-size:13px;">If you didn't request this link, you can ignore this email.</p>
        </div>
        """,
    )


def send_order_confirmation(email: str, product: str, order_id: str) -> bool:
    return send_email(
        to=email,
        subject=f"Order confirmed — {product}",
        html=f"""
        <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px;">
          <h2 style="color:#567B95;">Order confirmed!</h2>
          <p>Thanks for your purchase of <strong>{product}</strong>.</p>
          <p>Order ID: <code style="background:#f5f5f0;padding:2px 6px;border-radius:3px;">{order_id}</code></p>
          <p style="text-align:center;margin:28px 0;">
            <a href="{_SITE_URL}" style="background:#567B95;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;">Open oll.am</a>
          </p>
        </div>
        """,
    )
