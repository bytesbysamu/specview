"""Email blueprint — POST /api/email/send

Thin HTTP wrapper around the email service. All products call this
endpoint to send transactional emails rather than owning Resend directly.

Request body:
  {
    "to":       "user@example.com",      # required
    "template": "subscription_activated" # required — see TEMPLATES below
    | "custom",                           # use subject + html directly
    "subject":  "...",                   # required if template="custom"
    "html":     "<p>...</p>",            # required if template="custom"
    "ctx": {                             # template-specific context
      "plan":     "Pro",
      "product":  "KI Bewerbungsfoto",
      "order_id": "ord_123",
      "link":     "https://...",         # for magic_link template
    }
  }

Responses:
  200  {"sent": true}
  400  {"code": "MISSING_FIELD", "message": "..."}
  500  {"sent": false, "code": "EMAIL_FAILED"}
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from modules.auth.decorators import require_auth

from .service import (
    send_email,
    send_magic_link,
    send_order_confirmation,
    send_payment_failed,
    send_subscription_activated,
    send_subscription_canceled,
)

email_bp = Blueprint("email", __name__, url_prefix="/api/email")

_TEMPLATES = {
    "subscription_activated",
    "subscription_canceled",
    "payment_failed",
    "magic_link",
    "order_confirmation",
    "custom",
}


@email_bp.post("/send")
@require_auth
def send():
    body = request.get_json(silent=True) or {}
    to = (body.get("to") or "").strip()
    template = (body.get("template") or "custom").strip()
    ctx = body.get("ctx") or {}

    if not to:
        return jsonify({"code": "MISSING_FIELD", "message": "to is required"}), 400
    if template not in _TEMPLATES:
        return jsonify({"code": "UNKNOWN_TEMPLATE",
                        "message": f"template must be one of: {sorted(_TEMPLATES)}"}), 400

    if template == "custom":
        subject = (body.get("subject") or "").strip()
        html = (body.get("html") or "").strip()
        if not subject or not html:
            return jsonify({"code": "MISSING_FIELD",
                            "message": "subject and html are required for custom template"}), 400
        sent = send_email(to=to, subject=subject, html=html)

    elif template == "subscription_activated":
        sent = send_subscription_activated(to, plan=ctx.get("plan", "Pro"))

    elif template == "subscription_canceled":
        sent = send_subscription_canceled(to)

    elif template == "payment_failed":
        sent = send_payment_failed(to)

    elif template == "magic_link":
        link = ctx.get("link", "")
        if not link:
            return jsonify({"code": "MISSING_FIELD", "message": "ctx.link is required"}), 400
        sent = send_magic_link(to, link)

    elif template == "order_confirmation":
        sent = send_order_confirmation(
            to,
            product=ctx.get("product", "oll.am"),
            order_id=ctx.get("order_id", ""),
        )
    else:
        sent = False

    if sent:
        return jsonify({"sent": True}), 200
    return jsonify({"sent": False, "code": "EMAIL_FAILED"}), 500
