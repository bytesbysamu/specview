"""audit.py — the house audit helper.

A thin, structured wrapper over structlog for recording the OUTCOME of
external calls (Resend email, Stripe), webhook processing, and request
failures so they are visible end-to-end and correlated by ``request_id``.

Why this exists
---------------
External-call outcomes used to be logged ad hoc via stdlib ``logging`` (or not
at all — an email send could fail SILENTLY). That made successes/failures of
side-effecting calls invisible and impossible to correlate with the request
that triggered them. ``audit`` is the single, reusable pattern other products
adopt so every outcome lands as one structured line.

Usage
-----
    from modules.observability.audit import audit

    audit("email.send", outcome="success", to=to, template=subject,
          provider_id=msg_id)
    audit("billing.checkout", outcome="success", user_id=uid,
          price_id=price, session_id=sid)
    audit("request.failure", level="error", code="internal_error", status=500)

Every audit line carries:
  - the ``event`` name (dotted, e.g. ``email.send``, ``billing.webhook``)
  - ``audit=True`` — a stable filter key so audit lines are easy to grep/route
  - ``request_id`` — pulled from the active Flask request when present
  - any caller-supplied ``**fields``

The helper NEVER raises — auditing must not be able to fail the thing it is
auditing. It is a no-op-safe wrapper: a logging error is swallowed.
"""
from __future__ import annotations

from typing import Any

import structlog

_audit_log = structlog.get_logger("audit")

# Levels callers may request via the reserved ``level`` kwarg. Anything else
# falls back to info so a typo can never silence (or crash) an audit line.
_LEVELS = {"debug", "info", "warning", "error", "critical"}


def _current_request_id() -> str | None:
    """Best-effort ``request_id`` from the active Flask request.

    Reads ``g.request_id`` (set by the app's ``before_request`` hook). Returns
    ``None`` outside a request context (startup, CLI, background threads) so
    those lines simply omit the field rather than inventing a fake id.
    """
    try:
        from flask import g, has_request_context

        if has_request_context():
            return getattr(g, "request_id", None)
    except Exception:
        return None
    return None


def audit(event: str, **fields: Any) -> None:
    """Record one structured audit line for an outcome or failure.

    Args:
        event:  Dotted event name, e.g. ``"email.send"`` / ``"billing.webhook"``.
        level:  Reserved kwarg — log level (``info`` default; ``error`` for
                failures). Popped from ``fields`` before rendering.
        **fields: Arbitrary structured fields (outcome, ids, recipient, ...).
    """
    level = str(fields.pop("level", "info")).lower()
    if level not in _LEVELS:
        level = "info"

    rid = _current_request_id()
    if rid is not None:
        fields.setdefault("request_id", rid)

    try:
        getattr(_audit_log, level, _audit_log.info)(event, audit=True, **fields)
    except Exception:  # auditing must never fail the audited operation
        pass
