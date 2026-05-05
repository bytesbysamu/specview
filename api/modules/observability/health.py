"""Per-dependency health probes — `/api/health/{anthropic,neon,stripe}`.

This blueprint is the per-dependency liveness layer; the root `/health`
route in `create_app.py` is the basic Flask liveness check and stays put.
CI smoke tests and future uptime monitors target the routes here.

Contract (locked by SaaS Operations & Infra Task 3):

- `GET /api/health/anthropic` — live probe.
    * `ANTHROPIC_API_KEY` unset      -> 200 {"status": "skipped"}
    * `count_tokens` succeeds        -> 200 {"status": "ok"}
    * exception (incl. timeout)      -> 503 {"status": "degraded",
                                              "error": "<truncated 100 chars>"}
- `GET /api/health/neon`             -> 200 {"status": "skipped"} (stub)
- `GET /api/health/stripe`           -> 200 {"status": "skipped"} (stub)

Stubs return `skipped` until those dependencies are actually wired in;
the endpoint shape is stable today so monitoring can be configured against
the final URLs without a contract change later.

Anthropic call uses `Anthropic(timeout=5.0)` to bound the probe; importing
the SDK lazily inside the handler keeps test collection fast and keeps the
import out of the cold-start path when the env var is unset.
"""

from __future__ import annotations

import os

from flask import Blueprint, jsonify

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
    """Live probe of the Anthropic API via SDK count_tokens."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
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
    """Stub — returns skipped until Neon SQL connection wiring lands."""
    return jsonify({"status": "skipped"}), 200


@health_bp.get("/stripe")
def stripe_health():
    """Stub — returns skipped until Stripe SDK is configured in production."""
    return jsonify({"status": "skipped"}), 200
