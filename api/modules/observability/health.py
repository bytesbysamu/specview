"""Per-dependency health probes — `/api/health/{anthropic,neon,stripe}`.

This blueprint is the per-dependency liveness layer; the root `/health`
route in `create_app.py` is the basic Flask liveness check and stays put.
CI smoke tests and future uptime monitors target the routes here.

Contract:

- `GET /api/health/anthropic` — live probe.
    * `CHAIN_PROVIDER=cli`, no API key -> runs `claude -p ok` subprocess
        - exit 0                        -> 200 {"status": "ok"}
        - non-zero / timeout            -> 503 {"status": "degraded", "error": ...}
    * `ANTHROPIC_API_KEY` set          -> SDK count_tokens probe
        - succeeds                      -> 200 {"status": "ok"}
        - exception (incl. timeout)     -> 503 {"status": "degraded", "error": ...}
    * neither                          -> 200 {"status": "skipped"}
- `GET /api/health/neon` — database connectivity probe.
    * `DATABASE_URL` not set           -> 200 {"status": "skipped"}
    * configured                       -> executes `SELECT 1` with 5s timeout
        - succeeds                     -> 200 {"status": "ok"}
        - exception                    -> 503 {"status": "degraded", "error": ...}
- `GET /api/health/stripe` — Stripe API probe.
    * `STRIPE_SECRET_KEY` not set      -> 200 {"status": "skipped"}
    * configured                       -> calls `stripe.Balance.retrieve()`
        - succeeds                     -> 200 {"status": "ok"}
        - exception                    -> 503 {"status": "degraded", "error": ...}

Anthropic SDK call uses `Anthropic(timeout=5.0)` to bound the probe; importing
the SDK lazily inside the handler keeps test collection fast and keeps the
import out of the cold-start path when the env var is unset.

CLI probe uses `subprocess.run` with a 15-second timeout. The subprocess exit
code is authoritative — stdout/stderr are captured and the first 100 chars of
combined output are surfaced in degraded responses.

Neon probe executes a trivial `SELECT 1` via SQLAlchemy with a 5-second
connect_timeout (passed through the query string for Postgres URLs). On any
exception the probe degrades and surfaces a truncated error message.

Stripe probe lazily imports the `stripe` SDK and calls `Balance.retrieve()`
with a 5-second request timeout. Lazy import keeps the dependency optional
so the app starts cleanly when Stripe is not wired.
"""

from __future__ import annotations

import logging
import os
import subprocess

import sqlalchemy
from flask import Blueprint, jsonify

from modules.data.db.engine import get_engine

logger = logging.getLogger(__name__)

# url_prefix matches the openapi.yaml paths exactly; do not append a trailing
# slash to the route strings or Flask's strict_slashes will produce 308s that
# break the structural everyOpenapiPath_hasRouteHandler test.
health_bp = Blueprint("health", __name__, url_prefix="/api/health")

# Truncation budget for the upstream error message returned in degraded
# responses. Kept short so a misbehaving upstream cannot bloat the JSON
# payload returned to monitoring tools.
_MAX_ERROR_CHARS = 100

# Model and probe message used for the Anthropic count_tokens call. count_tokens
# is the cheapest authenticated round-trip the SDK exposes — it does not consume
# generation credits but still verifies API key validity + network reachability.
_PROBE_MODEL = "claude-haiku-4-5"
_PROBE_MESSAGES = [{"role": "user", "content": "ping"}]
_PROBE_TIMEOUT_SECONDS = 5.0


@health_bp.get("/anthropic")
def anthropic_health():
    """Live probe of the Anthropic backend — CLI subprocess or SDK count_tokens.

    When CHAIN_PROVIDER=cli (and no ANTHROPIC_API_KEY is set) the probe runs
    `claude -p ok --output-format text` as a lightweight auth check. A zero
    exit code means the CLI is authenticated and operational.

    When ANTHROPIC_API_KEY is set the probe uses the SDK count_tokens call,
    which is the cheapest authenticated round-trip the SDK exposes.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    chain_provider = os.environ.get("CHAIN_PROVIDER", "")

    if not api_key and chain_provider == "cli":
        # CLI path: validate that `claude` is authenticated.
        # We use `--model claude-haiku-4-5` (cheapest model) to minimise credit
        # cost. Note: the SDK path uses count_tokens (zero generation credits);
        # this CLI path does consume a generation credit per probe call, so the
        # docker-compose healthcheck interval is set to 300s (5 min) to keep
        # daily usage to ~288 calls — negligible on Claude Max flat-rate plans.
        try:
            result = subprocess.run(
                [
                    "claude",
                    "-p",
                    "ok",
                    "--output-format",
                    "text",
                    "--model",
                    "claude-haiku-4-5",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except Exception as exc:  # noqa: BLE001 — probe must survive all failure modes
            return (
                jsonify({"status": "degraded", "error": str(exc)[:_MAX_ERROR_CHARS]}),
                503,
            )

        if result.returncode == 0:
            return jsonify({"status": "ok"}), 200

        # Surface stdout first (contains error text), fall back to stderr.
        error_output = (result.stdout or result.stderr or "non-zero exit").strip()
        return (
            jsonify({"status": "degraded", "error": error_output[:_MAX_ERROR_CHARS]}),
            503,
        )

    if not api_key:
        # No API key and not using CLI — nothing to probe.
        return jsonify({"status": "skipped"}), 200

    try:
        # Lazy import: anthropic is a heavy SDK; importing at module top would
        # add cold-start cost to every request even when the key is unset.
        from anthropic import Anthropic

        client = Anthropic(timeout=_PROBE_TIMEOUT_SECONDS)
        client.messages.count_tokens(
            model=_PROBE_MODEL,
            messages=_PROBE_MESSAGES,
        )
        return jsonify({"status": "ok"}), 200
    except Exception as exc:  # noqa: BLE001 — probe must catch every failure mode
        return (
            jsonify(
                {
                    "status": "degraded",
                    "error": str(exc)[:_MAX_ERROR_CHARS],
                }
            ),
            503,
        )


@health_bp.get("/neon")
def neon_health():
    """Database connectivity probe — executes SELECT 1 via SQLAlchemy.

    When DATABASE_URL is not configured the probe returns skipped (200) so
    the health endpoint stays green in local dev environments without a
    database.  When configured a trivial query is issued with a 5-second
    connect_timeout; any exception degrades the probe to 503.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return jsonify({"status": "skipped"}), 200

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception as exc:  # noqa: BLE001 — probe must survive all failure modes
        logger.warning("neon health probe degraded: %s", str(exc)[:_MAX_ERROR_CHARS])
        return (
            jsonify({"status": "degraded", "error": str(exc)[:_MAX_ERROR_CHARS]}),
            503,
        )


@health_bp.get("/stripe")
def stripe_health():
    """Stripe API probe — calls Balance.retrieve() as a lightweight auth check.

    When STRIPE_SECRET_KEY is not set the probe returns skipped (200).  When
    set, the probe calls stripe.Balance.retrieve() with a 5-second timeout.
    The stripe SDK is imported lazily so the app starts cleanly when Stripe is
    not wired.
    """
    secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not secret_key:
        return jsonify({"status": "skipped"}), 200

    try:
        import stripe  # noqa: PLC0415 — lazy import by design

        stripe.Balance.retrieve(
            stripe_version=None,
            api_key=secret_key,
            stripe_account=None,
            timeout=5,
        )
        return jsonify({"status": "ok"}), 200
    except Exception as exc:  # noqa: BLE001 — probe must survive all failure modes
        logger.warning("stripe health probe degraded: %s", str(exc)[:_MAX_ERROR_CHARS])
        return (
            jsonify({"status": "degraded", "error": str(exc)[:_MAX_ERROR_CHARS]}),
            503,
        )
