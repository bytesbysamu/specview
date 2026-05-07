"""In-process job store for skill run jobs.

Keyed by UUID job_id. Jobs are never evicted — memory footprint is minimal
(one dict entry per skill run). Use get_job() for polling.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

_LOCK = threading.Lock()
_JOBS: dict[str, "SkillJob"] = {}


@dataclass
class SkillJob:
    job_id: str
    skill_name: str
    skill_version: str
    started_at: float = field(default_factory=time.monotonic)
    ended_at: float | None = None
    status: str = "running"  # running | done | failed
    result: Any = None
    error: str | None = None


def create_job(skill_name: str, skill_version: str) -> SkillJob:
    job = SkillJob(
        job_id=str(uuid.uuid4()),
        skill_name=skill_name,
        skill_version=skill_version,
    )
    with _LOCK:
        _JOBS[job.job_id] = job
    return job


def get_job(job_id: str) -> SkillJob | None:
    with _LOCK:
        return _JOBS.get(job_id)


def complete_job(job_id: str, result: Any) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job:
            job.status = "done"
            job.result = result
            job.ended_at = time.monotonic()


def fail_job(job_id: str, error: str) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job:
            job.status = "failed"
            job.error = error
            job.ended_at = time.monotonic()
