"""Public share slug service — in-memory slug index for unauthenticated spec access.

Slugs are generated with secrets.token_urlsafe(6) (~8 url-safe chars).
The index is populated at startup by scanning all project.json files.
"""
from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path

from config import PROJECTS_DIR

logger = logging.getLogger(__name__)

# Module-level index: share_slug -> project_id
_slug_index: dict[str, str] = {}


def build_index() -> None:
    """Scan all project.json files in PROJECTS_DIR and populate _slug_index.

    Called once at app startup after blueprint registration.
    Non-fatal: any unreadable project.json is skipped with a warning.
    """
    global _slug_index
    projects_dir = Path(PROJECTS_DIR)
    if not projects_dir.exists():
        logger.warning("build_index: PROJECTS_DIR %s does not exist — skipping", projects_dir)
        return

    loaded = 0
    for d in projects_dir.iterdir():
        if not d.is_dir():
            continue
        meta_path = d / "project.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("build_index: skipping unreadable project.json at %s", d)
            continue
        slug = meta.get("shareSlug")
        if slug and isinstance(slug, str):
            _slug_index[slug] = d.name
            loaded += 1

    logger.info("build_index: loaded %d share slug(s)", loaded)


def generate_slug() -> str:
    """Generate a collision-free url-safe slug (~8 chars).

    Retries on the extremely unlikely collision against existing index entries.
    """
    for _ in range(10):
        candidate = secrets.token_urlsafe(6)
        if candidate not in _slug_index:
            return candidate
    # Extremely rare: fall back to a longer token to guarantee uniqueness
    return secrets.token_urlsafe(12)


def resolve_slug(slug: str) -> str | None:
    """Return the project_id for a share slug, or None if not found."""
    return _slug_index.get(slug)


def register_slug(slug: str, project_id: str) -> None:
    """Add a new slug -> project_id mapping to the in-memory index."""
    _slug_index[slug] = project_id
