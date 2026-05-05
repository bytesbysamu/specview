"""Sentry initialisation for the Flask app.

Opt-in via the ``SENTRY_DSN`` environment variable. When the DSN is absent,
``init_sentry`` is a silent no-op so local development and CI run without a
Sentry project. The Flask integration is wired so unhandled exceptions
captured by Sentry's middleware include request metadata; explicit
``sentry_sdk.capture_exception`` calls in :mod:`modules.observability.errors`
ensure handler-consumed exceptions are also reported.

Environment variables:
    SENTRY_DSN                  Project DSN. Empty/unset disables Sentry.
    SENTRY_TRACES_SAMPLE_RATE   Float; defaults to 0.1 (10%).
    APP_ENV                     ``environment`` tag; defaults to "production".
    APP_RELEASE                 ``release`` tag; defaults to "dev".
"""

import os

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


def init_sentry(app) -> None:
    """Initialise the Sentry SDK.

    Silent no-op when ``SENTRY_DSN`` is unset or empty — local dev and CI
    must run without a Sentry project, and an absent DSN is not an error.
    """
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(
            os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")
        ),
        environment=os.environ.get("APP_ENV", "production"),
        release=os.environ.get("APP_RELEASE", "dev"),
        send_default_pii=False,
    )


def set_sentry_user(user_id: str) -> None:
    """Populate per-user Sentry scope.

    TODO(auth): Phase-1 auth middleware should call this from a
    ``before_request`` hook once ``g.current_user`` is populated. Until then
    this stub is unused. ``sentry_sdk.set_user`` is safe to call
    unconditionally — when Sentry is not initialised it is a no-op.
    """
    sentry_sdk.set_user({"id": user_id})
