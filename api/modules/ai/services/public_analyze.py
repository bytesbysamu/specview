"""Service module for anonymous public analysis jobs.

Spawns a background thread that calls the chain adapter with the analysis
prompt and stores the result in the in-process job store.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid

from modules.runtime.chain import adapter
from modules.runtime.chain.errors import ProviderError

logger = logging.getLogger(__name__)

# ── in-process job store ────────────────────────────────────────────────────
# Keyed by UUID job_id.  Status dict mirrors PublicAnalyzeJobStatus fields.

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}

_ANALYSIS_SYSTEM = "You are a markdown spec writer."

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
[Decisions already made. Deadlines. Budget limits.]

## Open Questions
[Things the brain dump left ambiguous.]

## Dependencies & Sequencing
[What blocks what.]

## Explicitly Out of Scope
[Things mentioned that should NOT be in the epic.]

---

INPUT:
{braindump}"""


_TTL_SECONDS = 900  # 15 minutes


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
    with _LOCK:
        return _JOBS.get(job_id)


def _complete_job(job_id: str, analysis: str) -> None:
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


def start_analysis(braindump: str) -> str:
    """Create a job, spawn a daemon thread, and return the job_id.

    Prunes expired anonymous job entries (older than 15 minutes) on each call
    to prevent unbounded memory growth.
    """
    job_id = str(uuid.uuid4())
    with _LOCK:
        _prune_expired_jobs()
        _JOBS[job_id] = {
            "running": True,
            "done": False,
            "analysis": None,
            "error": None,
            "started_at": time.time(),
        }
    thread = threading.Thread(
        target=run_analysis,
        args=(job_id, braindump),
        daemon=True,
        name=f"public-analyze-{job_id[:8]}",
    )
    thread.start()
    logger.info("public_analyze: started job=%s", job_id)
    return job_id
