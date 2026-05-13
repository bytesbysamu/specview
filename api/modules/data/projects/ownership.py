"""@require_project_ownership decorator — project-scoped authorization.

Must be stacked immediately after @require_auth on every route that accepts
a slug/project-id path parameter. On success the verified Project row is
attached to g.project so that the route handler can skip a redundant lookup.

Decorator contract
------------------
- Extracts the first slug-shaped path kwarg (``id`` or ``project_id``).
- Calls current_app.project_repository.get_by_slug() — the single DB seam.
- Returns 404 JSON if no project exists for that slug.
- Returns 403 JSON if project.user_id != g.current_user.id.
- Returns 401 JSON if g.current_user is None (SKIP_AUTH=1 in dev mode).
- Sets g.project to the loaded Project row on success.
"""
from __future__ import annotations

import logging
from functools import wraps

from flask import current_app, g, jsonify

logger = logging.getLogger(__name__)


def require_project_ownership(fn):
    """Route decorator that enforces project ownership.

    Must be stacked after @require_auth so that g.current_user is already
    populated before this decorator runs.

    Usage::

        @projects_bp.get("/<id>")
        @require_auth
        @require_project_ownership
        def get_project_route(id: str):
            project = g.project  # already verified
            ...
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Guard: SKIP_AUTH=1 in dev sets g.current_user to None.
        # We cannot enforce ownership without a real user identity — return 401
        # so that development sessions are aware they must pass a token or
        # disable SKIP_AUTH before ownership-protected routes work.
        if g.get("current_user") is None:
            return jsonify({"error": "authentication required"}), 401

        if g.current_user.id is None:
            return jsonify({"error": "authentication required"}), 401

        # Extract the slug from route path kwargs. The projects blueprint uses
        # two different kwarg names depending on the route family:
        #   /<id>/...                   → kwargs["id"]
        #   /<project_id>/files/...     → kwargs["project_id"]
        slug = kwargs.get("id") or kwargs.get("project_id")
        if not slug:
            logger.error(
                "require_project_ownership: no slug kwarg in %s kwargs=%s",
                fn.__name__, list(kwargs.keys()),
            )
            return jsonify({"error": "Project not found"}), 404

        repo = getattr(current_app, "project_repository", None)
        if repo is None:
            logger.error(
                "require_project_ownership: project_repository not configured"
            )
            return jsonify({"error": "Project not found"}), 404

        project = repo.get_by_slug(slug)
        if project is None:
            logger.warning(
                "require_project_ownership not_found slug=%s fn=%s",
                slug, fn.__name__,
            )
            return jsonify({"error": "Project not found"}), 404

        if project.user_id != g.current_user.id:
            logger.warning(
                "require_project_ownership access_denied slug=%s fn=%s",
                slug, fn.__name__,
            )
            return jsonify({"error": "access denied"}), 403

        g.project = project
        return fn(*args, **kwargs)

    return wrapper
