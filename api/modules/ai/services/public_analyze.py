"""Service module for anonymous public analysis jobs.

Spawns a background thread that calls the chain adapter with the analysis
prompt and stores the result in the in-process job store. Each job is also
persisted to the filesystem so results survive beyond the in-process TTL.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from config import PROJECTS_DIR
from modules.data.projects.service import _make_id
from modules.data.public.service import generate_slug, register_slug
from modules.runtime.chain import adapter
from modules.runtime.chain.errors import ProviderError

logger = logging.getLogger(__name__)

# ── in-process job store ────────────────────────────────────────────────────
# Keyed by project_id / job_id (same value).  Status dict mirrors
# PublicAnalyzeJobStatus fields.

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}

_ANALYSIS_SYSTEM = """\
You are a markdown spec writer.
Distinguish user data from domain claims. The user's own measurements, tool \
choices, and business decisions are legitimate input — analyze them without \
challenge. Claims presented as universal domain facts (industry standards, \
named methodologies, benchmark thresholds) without attribution should be \
flagged as unverified in Open Questions. When precise numbers are stated as \
domain facts rather than the user's own data, note them as unverified. When \
a proper-noun framework or protocol is referenced that you don't recognize, \
flag it as requiring verification rather than assuming it exists.\
"""

_ANALYSIS_USER = """\
You are a filter between a messy brain dump and a structured analysis.
Keep it SHORT — 30-40 lines max. No severity tables. No analogies.

## Output Format
OUTPUT ONLY markdown. Start with #. No preamble.

---

# Analysis

## The Problem
[2-3 sentences. What exists today, why it's broken, what changes.]

## Hard Constraints
[The user's own decisions, measurements, deadlines, and budget. Exclude domain assertions or external standards the user did not explicitly choose.]

## Open Questions
[Things the brain dump left ambiguous, plus unverified domain claims: specific numbers presented as industry facts, unfamiliar named frameworks, and standards that need verification.]

## Dependencies & Sequencing
[Concrete systems, teams, or deliverables the user named. Do not infer dependencies from frameworks or standards — only include things the user explicitly mentioned.]

## Explicitly Out of Scope
[Things mentioned that should NOT be in the epic.]

---

INPUT:
{braindump}"""


_TTL_SECONDS = 900  # 15 minutes

_VALID_JOB_ID = re.compile(r'^[a-z0-9-]+$')


def _prune_expired_jobs() -> None:
    """Remove job entries older than _TTL_SECONDS. Must be called under _LOCK."""
    now = time.time()
    expired = [
        jid for jid, job in _JOBS.items()
        if now - job.get("started_at", now) > _TTL_SECONDS
    ]
    for jid in expired:
        del _JOBS[jid]
    if expired:
        logger.debug("public_analyze: pruned %d expired job(s)", len(expired))


def get_job(job_id: str) -> dict | None:
    """Return the job dict for job_id.

    Checks the in-process store first; if the job has been evicted, falls
    back to reading completed results from the filesystem.
    """
    if not job_id or len(job_id) > 100 or not _VALID_JOB_ID.match(job_id):
        return None

    with _LOCK:
        job = _JOBS.get(job_id)
        if job is not None:
            return job

    # Disk fallback — job may have been pruned but files remain on disk.
    project_dir = Path(PROJECTS_DIR) / job_id
    analysis_path = project_dir / "analysis.md"
    if not analysis_path.exists():
        return None

    braindump: str | None = None
    braindump_path = project_dir / "braindump.md"
    if braindump_path.exists():
        try:
            braindump = braindump_path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("public_analyze: could not read braindump.md for job=%s", job_id)

    try:
        analysis = analysis_path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("public_analyze: could not read analysis.md for job=%s", job_id)
        return None

    # Attempt to recover share_slug from project.json on disk.
    share_slug: str | None = None
    meta_path = project_dir / "project.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            share_slug = meta.get("shareSlug") or None
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "running": False,
        "done": True,
        "analysis": analysis,
        "error": None,
        "project_id": job_id,
        "braindump": braindump,
        "share_slug": share_slug,
        "started_at": 0,
    }


def _complete_job(job_id: str, analysis: str) -> None:
    # Write to disk first, then update in-memory state.
    project_dir = Path(PROJECTS_DIR) / job_id
    try:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "analysis.md").write_text(analysis, encoding="utf-8")
        logger.debug("public_analyze: wrote analysis.md for job=%s", job_id)
    except OSError:
        logger.exception("public_analyze: failed to write analysis.md for job=%s", job_id)

    with _LOCK:
        job = _JOBS.get(job_id)
        if job:
            job["running"] = False
            job["done"] = True
            job["analysis"] = analysis


def _fail_job(job_id: str, error: str) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job:
            job["running"] = False
            job["done"] = True
            job["error"] = error


def run_analysis(job_id: str, braindump: str) -> None:
    """Background thread target: call the chain adapter and store the result."""
    try:
        prompt = _ANALYSIS_USER.format(braindump=braindump)
        result = adapter.rewrite(
            system=_ANALYSIS_SYSTEM,
            prompt=prompt,
            model="claude-haiku-4-5",
            max_tokens=2048,
        )
        _complete_job(job_id, result.text)
        logger.info("public_analyze: job=%s completed successfully", job_id)
    except ProviderError as exc:
        logger.warning("public_analyze: job=%s provider error: %s", job_id, exc)
        _fail_job(job_id, str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("public_analyze: job=%s unexpected error", job_id)
        _fail_job(job_id, str(exc))


def start_analysis(braindump: str) -> tuple[str, str]:
    """Create a project directory, spawn a daemon thread, and return (job_id, share_slug).

    The job_id equals the project slug so no mapping table is required.
    Prunes expired anonymous job entries (older than 15 minutes) on each
    call to prevent unbounded memory growth.
    """
    # Generate a slug-based job_id from the first 40 chars of the braindump.
    project_id = _make_id(braindump[:40])

    # Create project directory and write initial files.
    project_dir = Path(PROJECTS_DIR) / project_id
    try:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "braindump.md").write_text(braindump, encoding="utf-8")

        created_at = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        slug = generate_slug()
        meta = {
            "name": braindump[:40].strip(),
            "createdAt": created_at,
            "anonymous": True,
            "shareSlug": slug,
        }
        (project_dir / "project.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        register_slug(slug, project_id)
        logger.debug("public_analyze: initialised project directory for job=%s slug=%s", project_id, slug)
    except OSError:
        logger.exception(
            "public_analyze: failed to initialise project directory for job=%s", project_id
        )
        slug = generate_slug()  # still provide a slug even if file write fails

    # Attempt DB write; log and continue on failure.
    try:
        from modules.data.projects.repository import SqlProjectRepository
        repo = SqlProjectRepository()
        repo.create_anonymous(name=braindump[:40].strip(), slug=project_id)
        logger.debug("public_analyze: DB row created for job=%s", project_id)
    except Exception:  # noqa: BLE001
        logger.warning(
            "public_analyze: DB write skipped for job=%s (non-fatal)", project_id
        )

    with _LOCK:
        _prune_expired_jobs()
        _JOBS[project_id] = {
            "running": True,
            "done": False,
            "analysis": None,
            "error": None,
            "project_id": project_id,
            "braindump": braindump,
            "share_slug": slug,
            "started_at": time.time(),
        }

    thread = threading.Thread(
        target=run_analysis,
        args=(project_id, braindump),
        daemon=True,
        name=f"public-analyze-{project_id[:8]}",
    )
    thread.start()
    logger.info("public_analyze: started job=%s slug=%s", project_id, slug)
    return project_id, slug
