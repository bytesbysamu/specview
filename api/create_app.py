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
