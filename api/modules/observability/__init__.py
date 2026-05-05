"""observability — structured logging, error/Sentry capture, health checks.

SAAS_OPTIONAL package. Submodules:
  - logging.py   (Task 1) — init_logging(): structlog with JSON output + request_id
  - sentry.py    (Task 2) — init_sentry(app): Sentry SDK init (no-op if SENTRY_DSN unset)
  - errors.py    (Task 2) — register_error_handlers(app): JSON error envelopes
  - health.py    (Task 3) — health_bp blueprint: /api/health/{anthropic,neon,stripe}

Consumers import the specific submodule they need; this package re-exports
init_logging only so app startup can pull it from the package root.
"""

from modules.observability.logging import init_logging

__all__ = ["init_logging"]
