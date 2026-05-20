"""Daemon thread that periodically purges anonymous projects past their TTL.

Usage (in create_app.py, guarded by not app.config.get("TESTING")):

    from modules.ai.services.anonymous_cleanup import start_cleanup_thread
    start_cleanup_thread(ttl_hours=48, interval_hours=6)

The thread is a daemon so it never blocks interpreter shutdown.
"""
from __future__ import annotations

import logging
import shutil
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import PROJECTS_DIR

logger = logging.getLogger(__name__)


def _delete_project_dir(slug: str) -> None:
    """Remove the on-disk directory for an anonymous project.

    Validates that the slug does not contain path-traversal sequences
    before touching the filesystem.  Logs at DEBUG level; does nothing
    if the directory does not exist.
    """
    if ".." in slug:
        logger.warning(
            "anonymous_cleanup: rejected slug with path traversal: %r", slug
        )
        return

    project_dir = Path(PROJECTS_DIR) / slug
    if not project_dir.exists():
        logger.debug(
            "anonymous_cleanup: directory does not exist, skipping: %s", project_dir
        )
        return

    try:
        shutil.rmtree(project_dir)
        logger.debug("anonymous_cleanup: deleted directory %s", project_dir)
    except OSError:
        logger.exception(
            "anonymous_cleanup: failed to delete directory %s", project_dir
        )


def _run_cleanup(ttl_hours: int) -> None:
    """Query the DB for expired anonymous projects and delete each one.

    Per-project errors are caught and logged so a single bad row never
    aborts the entire sweep.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=ttl_hours)

    from modules.data.projects.repository import SqlProjectRepository

    repo = SqlProjectRepository()
    try:
        projects = repo.list_anonymous_older_than(cutoff)
    except Exception:
        logger.exception("anonymous_cleanup: failed to query expired projects")
        return

    deleted = 0
    errors = 0
    for project in projects:
        try:
            _delete_project_dir(project.slug)
            repo.delete_by_id(project.id)
            deleted += 1
            logger.debug(
                "anonymous_cleanup: removed project id=%s slug=%s",
                project.id,
                project.slug,
            )
        except Exception:
            logger.exception(
                "anonymous_cleanup: error removing project id=%s slug=%s",
                project.id,
                project.slug,
            )
            errors += 1

    logger.info(
        "anonymous_cleanup: sweep complete — cutoff=%s deleted=%d errors=%d",
        cutoff.isoformat(),
        deleted,
        errors,
    )


def start_cleanup_thread(ttl_hours: int = 48, interval_hours: int = 6) -> None:
    """Spawn a background daemon thread that runs the cleanup on a fixed interval.

    The thread sleeps *first* so the first sweep happens after one full
    interval — this avoids a burst of DB queries during app startup.

    Args:
        ttl_hours: Projects older than this many hours are considered expired.
        interval_hours: How often to run the sweep.
    """
    interval_seconds = interval_hours * 3600

    def _loop() -> None:
        logger.info(
            "anonymous_cleanup: thread started — ttl=%dh interval=%dh",
            ttl_hours,
            interval_hours,
        )
        while True:
            time.sleep(interval_seconds)
            try:
                _run_cleanup(ttl_hours)
            except Exception:
                logger.exception("anonymous_cleanup: unhandled error in cleanup loop")

    thread = threading.Thread(
        target=_loop,
        daemon=True,
        name="anonymous-project-cleanup",
    )
    thread.start()
    logger.info(
        "anonymous_cleanup: daemon thread started (ttl=%dh, interval=%dh)",
        ttl_hours,
        interval_hours,
    )
