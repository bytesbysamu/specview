"""Tests for modules/ai/job_store.py.

Pure unit tests — no Flask, no I/O. Covers thread-safe create/get/complete/fail.
"""
from __future__ import annotations

import threading
import time

import pytest

import modules.ai.job_store as store


@pytest.fixture(autouse=True)
def _clear_jobs():
    """Isolate each test — clear shared state before and after."""
    store._JOBS.clear()
    yield
    store._JOBS.clear()


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------

def test_create_job_returns_skill_job():
    job = store.create_job("rewrite", "1.0.0")
    assert job.job_id
    assert job.skill_name == "rewrite"
    assert job.skill_version == "1.0.0"
    assert job.status == "running"
    assert job.result is None
    assert job.error is None


def test_create_job_stores_in_registry():
    job = store.create_job("rewrite", "1.0.0")
    assert store.get_job(job.job_id) is job


def test_create_job_generates_unique_ids():
    ids = {store.create_job("rewrite", "1.0.0").job_id for _ in range(20)}
    assert len(ids) == 20


# ---------------------------------------------------------------------------
# get_job
# ---------------------------------------------------------------------------

def test_get_job_returns_none_for_unknown_id():
    assert store.get_job("no-such-id") is None


def test_get_job_returns_job_after_creation():
    job = store.create_job("iterate", "1.0.0")
    assert store.get_job(job.job_id) is job


# ---------------------------------------------------------------------------
# complete_job
# ---------------------------------------------------------------------------

def test_complete_job_sets_status_and_result():
    job = store.create_job("review", "1.0.0")
    store.complete_job(job.job_id, {"scores": {"clarity": 5}, "issues": []})
    assert job.status == "done"
    assert job.result == {"scores": {"clarity": 5}, "issues": []}
    assert job.ended_at is not None


def test_complete_job_is_idempotent_on_unknown_id():
    # Must not raise if job_id doesn't exist
    store.complete_job("ghost-id", {"result": True})


# ---------------------------------------------------------------------------
# fail_job
# ---------------------------------------------------------------------------

def test_fail_job_sets_status_and_error():
    job = store.create_job("brainstorm", "1.0.0")
    store.fail_job(job.job_id, "AI provider timed out")
    assert job.status == "failed"
    assert job.error == "AI provider timed out"
    assert job.ended_at is not None


def test_fail_job_is_idempotent_on_unknown_id():
    store.fail_job("ghost-id", "error")


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

def test_concurrent_creates_produce_distinct_jobs():
    results: list = []
    lock = threading.Lock()

    def _create():
        job = store.create_job("rewrite", "1.0.0")
        with lock:
            results.append(job.job_id)

    threads = [threading.Thread(target=_create) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 50
    assert len(set(results)) == 50  # all IDs unique


def test_concurrent_complete_and_fail_do_not_corrupt_store():
    jobs = [store.create_job("rewrite", "1.0.0") for _ in range(20)]

    def _finish(job, i):
        if i % 2 == 0:
            store.complete_job(job.job_id, {"i": i})
        else:
            store.fail_job(job.job_id, f"error-{i}")

    threads = [threading.Thread(target=_finish, args=(j, i)) for i, j in enumerate(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for i, job in enumerate(jobs):
        if i % 2 == 0:
            assert job.status == "done"
        else:
            assert job.status == "failed"


# ---------------------------------------------------------------------------
# TTL eviction
# ---------------------------------------------------------------------------

class TestJobTTL:
    def test_fresh_job_is_retrievable(self):
        job = store.create_job("brainstorm", "1.0.0")
        assert store.get_job(job.job_id) is not None

    def test_expired_job_returns_none(self, monkeypatch):
        job = store.create_job("brainstorm", "1.0.0")
        original = time.monotonic
        monkeypatch.setattr(
            time, "monotonic",
            lambda: original() + store.JOB_TTL_SECONDS + 1,
        )
        assert store.get_job(job.job_id) is None

    def test_expired_job_is_evicted_from_dict(self, monkeypatch):
        job = store.create_job("brainstorm", "1.0.0")
        original = time.monotonic
        monkeypatch.setattr(
            time, "monotonic",
            lambda: original() + store.JOB_TTL_SECONDS + 1,
        )
        store.get_job(job.job_id)  # triggers eviction
        assert job.job_id not in store._JOBS
