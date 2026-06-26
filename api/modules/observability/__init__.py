"""observability — structured logging, error/Sentry capture, health checks.

SAAS_OPTIONAL package. Submodules:
  - logging.py   (Task 1) — init_logging(): structlog with JSON output + request_id
  - sentry.py    (Task 2) — init_sentry(app): Sentry SDK init (no-op if SENTRY_DSN unset)
  - errors.py    (Task 2) — register_error_handlers(app): JSON error envelopes
  - health.py    (Task 3) — health_bp blueprint: /api/health/{anthropic,neon,stripe}
  - audit.py            — audit(event, **fields): the house outcome/failure
                          audit helper (external-call outcomes, webhooks,
                          request failures) correlated by request_id.

Consumers import the specific submodule they need; this package re-exports
init_logging and audit so app startup / call sites can pull them from the
package root.
"""

from modules.observability.audit import audit
from modules.observability.logging import init_logging

__all__ = ["init_logging", "audit"]
