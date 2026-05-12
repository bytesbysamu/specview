import importlib
import os
import sys
import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory, abort
from flask_cors import CORS

from modules.observability import init_logging
from modules.observability.errors import register_error_handlers
from modules.observability.health import health_bp
from modules.observability.sentry import init_sentry

load_dotenv()

# Add module path + exported blueprint name here to register a new module.
ENABLED_MODULES = [
    ('modules.data.projects.routes',  'projects_bp'),
    ('modules.data.context.routes',   'context_bp'),
    ('modules.ai.routes.text',   'ai_bp'),
    ('modules.data.templates.routes', 'templates_bp'),
    ('modules.ai.routes.task_gen',  'task_gen_bp'),
    ('modules.ai.routes.spec_gen',  'spec_gen_bp'),   # Task 5
    ('modules.billing.routes',      'billing_bp'),    # SaaS Foundation Wave 2 (Mon-T2)
    ('modules.ai.routes.stats',     'stats_bp'),      # SaaS Anthropic SDK Provider (SDK-T3)
    ('modules.auth.routes',         'auth_bp'),       # SaaS Auth Magic Link (Auth-T2)
    ('modules.ai.routes.generic_skill_route', 'skill_bp'),  # Thin API Phase 2 — generic skill route
    ('modules.ai.routes.actions', 'actions_bp'),            # Thin API Phase 3 — action routes
]


def _parse_cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


def _enforce_production_startup_gate() -> None:
    """Warn (never crash) when production env vars look misconfigured.

    Deployment must always succeed so the container stays healthy. Missing
    credentials are surfaced as 502s at request time via ProviderError, which
    is far better than an unhealthy container that blocks the whole stack.
    """
    if os.environ.get("APP_ENV") != "production":
        return
    provider = os.environ.get("CHAIN_PROVIDER", "").lower()
    if provider in ("", "mock", "cli"):
        sys.stderr.write(
            f"WARNING: APP_ENV=production but CHAIN_PROVIDER={provider!r} — "
            "set CHAIN_PROVIDER=claude in production (AI calls will fail until fixed).\n"
        )
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        sys.stderr.write(
            "WARNING: APP_ENV=production but ANTHROPIC_API_KEY is unset — "
            "AI calls will return 502 until the key is configured.\n"
        )


def create_app(config=None):
    # SDK Provider Task 5: production startup gate before anything else binds.
    _enforce_production_startup_gate()

    # Observability stack — initialised in the contractual order:
    # structlog → Sentry → JSON error handlers → blueprints → health → web catch-all.
    init_logging()

    app = Flask(__name__)

    if config:
        app.config.update(config)

    init_sentry(app)
    register_error_handlers(app)

    CORS(app, origins=_parse_cors_origins())

    @app.after_request
    def _add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        return response

    for module_path, blueprint_attr in ENABLED_MODULES:
        module = importlib.import_module(module_path)
        bp = getattr(module, blueprint_attr)
        app.register_blueprint(bp)

    app.register_blueprint(health_bp)

    from pathlib import Path
    from modules.runtime.workflows.repository.fs_adapter import WorkflowRepositoryFs
    app.workflow_repository = WorkflowRepositoryFs.from_modules_dir(
        Path(__file__).parent / "modules"
    )

    @app.get('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.get('/api/health/security')
    def health_security():
        skip_auth_active = os.environ.get("SKIP_AUTH", "").lower() in ("1", "true", "yes")
        flask_env = os.environ.get("FLASK_ENV", "")
        if skip_auth_active and flask_env != "development":
            return jsonify({
                "status": "misconfigured",
                "error": "SKIP_AUTH is active in a non-development environment",
                "flask_env": flask_env or "(unset)",
            }), 503
        return jsonify({"status": "ok", "skip_auth_bypassed": False})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found", "status": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "method not allowed", "status": 405}), 405

    from config import BASE_DIR

    @app.get('/specs/<path:filename>')
    def serve_spec(filename):
        specs_dir = BASE_DIR / 'specs'
        if not specs_dir.is_dir():
            abort(404)
        return send_from_directory(str(specs_dir), filename)

    @app.before_request
    def _block_path_traversal():
        from flask import request as _req
        if ".." in _req.path:
            return jsonify({"error": "not found", "status": 404}), 404

    return app
