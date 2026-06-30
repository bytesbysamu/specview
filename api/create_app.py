import importlib
import logging
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

logger = logging.getLogger(__name__)

DEFAULT_OWNER_EMAIL = "sam@specview.app"

# Add module path + exported blueprint name here to register a new module.
ENABLED_MODULES = [
    ('modules.data.projects.routes',  'projects_bp'),
    ('modules.data.context.routes',   'context_bp'),
    ('modules.ai.routes.text',   'ai_bp'),
    ('modules.data.templates.routes', 'templates_bp'),
    ('modules.ai.routes.task_gen',  'task_gen_bp'),
    ('modules.ai.routes.spec_gen',  'spec_gen_bp'),   # Task 5
    ('modules.ai.routes.stats',     'stats_bp'),      # SaaS Anthropic SDK Provider (SDK-T3)
    ('modules.ai.routes.generic_skill_route', 'skill_bp'),  # Thin API Phase 2 — generic skill route
    ('modules.ai.routes.actions', 'actions_bp'),            # Thin API Phase 3 — action routes
    ('modules.data.public.routes', 'public_bp'),            # Task 1 — public shareable spec URLs
    ('modules.ai.routes.public_analyze', 'public_analyze_bp'),  # Anonymous analysis endpoint
]
# NOTE: auth/billing/email blueprints were retired (2026-06-30) — they were the
# in-repo dev-bench for Core. The deployed product proxies /api/(auth|billing|
# email)/* to the remote oll-core (core.oll.am); the local copies were dead by
# routing. The live SSO spine (require_auth → verify_token, the shared
# AUTH_JWT_SECRET, and the User model) is retained outside this list.


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


def _enforce_secret_boot_gate() -> None:
    """Fail-fast in production when security-critical secrets are unset.

    Unlike the AI-provider gate (which only warns so the container stays
    healthy), a missing auth secret is a hard security failure: an unsigned
    JWT must never be possible, since the JWT is the live SSO spine that
    protects every product route. In production we refuse to boot rather than
    run insecurely; outside production we warn so local dev stays frictionless.

    The Stripe webhook secret is no longer required here: billing was retired
    from this product container (it proxies /api/billing/* to the remote
    oll-core, which owns the webhook). Only the JWT secret remains mandatory.
    """
    is_production = os.environ.get("APP_ENV") == "production"
    jwt_secret = os.environ.get("AUTH_JWT_SECRET") or os.environ.get("JWT_SECRET")

    missing = []
    if not jwt_secret:
        missing.append("AUTH_JWT_SECRET (or JWT_SECRET)")

    if not missing:
        return
    if is_production:
        raise RuntimeError(
            "refusing to boot: missing required secret(s) in production: "
            + ", ".join(missing)
        )
    sys.stderr.write(
        "WARNING: missing secret(s): " + ", ".join(missing)
        + " — required before production deploy.\n"
    )


def create_app(config=None):
    # Security boot gate: refuse to boot in prod without auth/webhook secrets.
    _enforce_secret_boot_gate()
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

    @app.before_request
    def _assign_request_id():
        from flask import g, request as _req
        g.request_id = _req.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def _add_security_headers(response):
        from flask import g
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Request-ID"] = getattr(g, "request_id", None) or str(uuid.uuid4())
        return response

    for module_path, blueprint_attr in ENABLED_MODULES:
        module = importlib.import_module(module_path)
        bp = getattr(module, blueprint_attr)
        app.register_blueprint(bp)

    app.register_blueprint(health_bp)

    # Build the public share slug index from existing project.json files.
    from modules.data.public.service import build_index as _build_slug_index
    try:
        _build_slug_index()
    except Exception:
        logger.exception("create_app: build_index failed — app will still start")

    from pathlib import Path
    from modules.runtime.workflows.repository.fs_adapter import WorkflowRepositoryFs
    app.workflow_repository = WorkflowRepositoryFs.from_modules_dir(
        Path(__file__).parent / "modules"
    )

    from modules.data.projects.repository import SqlProjectRepository
    app.project_repository = SqlProjectRepository()

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

    _run_startup_migration(app)

    if not app.config.get("TESTING"):
        from modules.ai.services.anonymous_cleanup import start_cleanup_thread
        _anon_ttl = int(os.environ.get("ANON_PROJECT_TTL_HOURS", "48"))
        start_cleanup_thread(ttl_hours=_anon_ttl, interval_hours=6)

    return app


def _run_startup_migration(app) -> None:
    """Flyway-style idempotent filesystem-to-DB migration on app startup.

    Checks whether the project table already has rows. If the table is
    empty, runs the filesystem-to-DB migration automatically using the
    owner email from MIGRATION_OWNER_EMAIL (defaulting to
    DEFAULT_OWNER_EMAIL). Skips entirely when projects already exist.

    This runs AFTER Alembic migrations (schema must exist before any
    SELECT on the project table is valid), but the Alembic CLI is
    typically invoked before gunicorn/flask starts, so the schema is
    guaranteed to be present by the time create_app() is called in
    production.
    """
    if app.config.get("TESTING"):
        logger.debug("startup_migration: TESTING=True — skipping")
        return

    owner_email = os.environ.get("MIGRATION_OWNER_EMAIL", DEFAULT_OWNER_EMAIL)
    try:
        from sqlmodel import Session, select, func
        from modules.data.db.engine import get_engine
        from modules.data.projects.models import Project

        with Session(get_engine()) as session:
            row_count = session.exec(select(func.count()).select_from(Project)).one()

        if row_count > 0:
            logger.info(
                "startup_migration: %d project(s) already in DB — skipping filesystem import",
                row_count,
            )
            return

        logger.info(
            "startup_migration: project table is empty — running filesystem-to-DB migration "
            "(owner=%s)",
            owner_email,
        )
        _do_filesystem_migration(owner_email)
    except Exception:
        # Migration failures must never prevent app startup; log and continue.
        logger.exception("startup_migration: migration failed — app will still start")


def _do_filesystem_migration(owner_email: str) -> None:
    """Run the core filesystem-to-DB import logic.

    Mirrors migrate_filesystem_to_git_db.main() but without argparse /
    sys.exit() so it can be called safely from an app factory context.
    """
    import json
    from pathlib import Path
    from typing import Optional

    from sqlmodel import Session, select

    from modules.auth.models import User
    from modules.data.db.engine import get_engine
    from modules.data import git_store
    from modules.data.projects.repository import SqlProjectRepository
    from config import PROJECTS_DIR

    projects_dir = Path(PROJECTS_DIR)
    if not projects_dir.is_dir():
        logger.warning(
            "startup_migration: projects_dir %s does not exist — nothing to migrate",
            projects_dir,
        )
        return

    git_repos_dir = Path(
        os.environ.get("GIT_REPOS_DIR")
        or os.environ.get("PROJECTS_DIR")
        or str(projects_dir)
    )
    git_repos_dir.mkdir(parents=True, exist_ok=True)
    os.environ["GIT_REPOS_DIR"] = str(git_repos_dir)

    # Look up the owner user row.
    with Session(get_engine()) as session:
        user = session.exec(select(User).where(User.email == owner_email)).first()

    if user is None:
        logger.warning(
            "startup_migration: no User row for email '%s' — skipping migration. "
            "Register the account first.",
            owner_email,
        )
        return

    owner_id = int(user.id)

    # Import modules used by the per-project migration.
    import modules.auth.models  # noqa: F401 — registers User table metadata
    import modules.data.projects.models  # noqa: F401 — registers Project table metadata

    repo = SqlProjectRepository()

    counts = {"migrated": 0, "skipped": 0, "error": 0}
    files_total = 0

    for slug_dir in sorted(projects_dir.iterdir()):
        if not slug_dir.is_dir():
            continue
        slug = slug_dir.name
        if repo.get_by_slug(slug) is not None:
            counts["skipped"] += 1
            continue
        md_files = sorted(slug_dir.glob("*.md"))
        if not md_files:
            counts["skipped"] += 1
            continue
        # Resolve project name from project.json, fall back to slug.
        name = slug.replace("-", " ").title()
        project_json = slug_dir / "project.json"
        if project_json.is_file():
            try:
                data = json.loads(project_json.read_text(encoding="utf-8"))
                candidate = data.get("name")
                if isinstance(candidate, str) and candidate.strip():
                    name = candidate.strip()
            except (json.JSONDecodeError, OSError):
                pass
        try:
            project = repo.create(
                user_id=owner_id,
                name=name,
                slug=slug,
                git_repo_path=str(git_repos_dir / slug),
            )
            last_sha: Optional[str] = None
            for f in md_files:
                last_sha = git_store.write_file(
                    str(project.id),
                    f.name,
                    f.read_text(encoding="utf-8"),
                    f"migrate: {f.name}",
                )
            if last_sha is not None:
                repo.touch(project.id, last_sha, len(md_files))
            counts["migrated"] += 1
            files_total += len(md_files)
            logger.debug("startup_migration: migrated %s (%d files)", slug, len(md_files))
        except Exception:
            logger.exception("startup_migration: failed to migrate project %s", slug)
            counts["error"] += 1

    logger.info(
        "startup_migration: done — migrated=%d skipped=%d errors=%d files=%d",
        counts["migrated"],
        counts["skipped"],
        counts["error"],
        files_total,
    )
