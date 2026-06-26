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
from pydantic import ValidationError

from dtos.models import EmailSendRequest, EmailSendResponse
from modules.auth.decorators import require_auth
from modules.observability.errors import core_error

from .service import (
    send_email,
    send_magic_link,
    send_order_confirmation,
    send_payment_failed,
    send_subscription_activated,
    send_subscription_canceled,
)

email_bp = Blueprint("email", __name__, url_prefix="/api/email")


@email_bp.post("/send")
@require_auth
def send():
    try:
        req = EmailSendRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", ())) or "body"
        return core_error("INVALID_REQUEST", f"{loc}: {first.get('msg', 'invalid')}", 400)

    to = str(req.to)
    template = req.template.value
    ctx = req.ctx or {}

    # Recipient scoping: a user may only email their own address. This is the
    # only writer of `to` reachable over HTTP; webhook-driven emails go through
    # the service layer directly and are not subject to this check.
    own_email = getattr(g.current_user, "email", None) if g.current_user else None
    if not own_email or to.lower() != own_email.lower():
        return core_error("FORBIDDEN_RECIPIENT",
                          "recipient must be your own account email", 403)

    if template == "custom":
        subject = (req.subject or "").strip()
        html = (req.html or "").strip()
        if not subject or not html:
            return core_error("MISSING_FIELD",
                              "subject and html are required for custom template", 400)
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
            return core_error("MISSING_FIELD", "ctx.link is required", 400)
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
        return jsonify(EmailSendResponse(sent=True).model_dump()), 200
    return core_error("EMAIL_FAILED", "email provider did not accept the message", 500)
