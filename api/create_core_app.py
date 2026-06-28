"""Core-only Flask app factory — the slice that becomes oll-core.

``create_core_app()`` boots ONLY Core's infrastructure surface: auth, billing,
email and health. It is the exact application that gets lifted into the
standalone ``oll-core`` service and deployed at ``core.api.oll.am`` — built and
proven here, inside specview, before the move (the house "develop-in-specview,
lift verbatim" rule).

It deliberately excludes everything that makes specview a *product*: the AI /
projects / context / templates / public blueprints, the filesystem→DB project
migration, the anonymous-cleanup thread, and the workflow/project repositories.
Core is frozen infrastructure; product logic lives in the services that call it
over HTTP.

Middleware (request-id, security headers, CORS, the unified error envelope, and
the secret boot gate) is shared with ``create_app`` so Core behaves identically
to the matching slice of the monolith.
"""
from __future__ import annotations

import importlib
import uuid

from flask import Flask, jsonify
from flask_cors import CORS

# Reuse the monolith's boot gate + CORS parsing verbatim — single source of
# truth for the security gate. These small helpers move with Core at lift time.
from create_app import _enforce_secret_boot_gate, _parse_cors_origins
from modules.observability import init_logging
from modules.observability.errors import register_error_handlers
from modules.observability.health import health_bp
from modules.observability.sentry import init_sentry

# Core's HTTP surface — auth + billing + email only. Health is registered
# separately (its per-dependency blueprint + the root liveness route below).
CORE_MODULES = [
    ("modules.auth.routes", "auth_bp"),
    ("modules.billing.routes", "billing_bp"),
    ("modules.email.routes", "email_bp"),
]


def create_core_app(config=None):
    """Build the Core-only Flask app (auth + billing + email + health)."""
    # Same security boot gate as create_app: in production, refuse to boot
    # without the JWT signing secret and the Stripe webhook secret.
    _enforce_secret_boot_gate()

    init_logging()

    app = Flask(__name__)
    if config:
        app.config.update(config)

    init_sentry(app)
    register_error_handlers(app)
    CORS(app, origins=_parse_cors_origins())

    @app.before_request
    def _assign_request_id():
        from flask import g, request as _req
        g.request_id = _req.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.before_request
    def _block_path_traversal():
        from flask import request as _req
        if ".." in _req.path:
            return jsonify({"error": "not found", "status": 404}), 404

    @app.after_request
    def _add_security_headers(response):
        from flask import g
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Request-ID"] = getattr(g, "request_id", None) or str(uuid.uuid4())
        return response

    for module_path, blueprint_attr in CORE_MODULES:
        module = importlib.import_module(module_path)
        app.register_blueprint(getattr(module, blueprint_attr))

    app.register_blueprint(health_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found", "status": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "method not allowed", "status": 405}), 405

    return app
