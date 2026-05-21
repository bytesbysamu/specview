"""Data structures for BullshitBench eval runner.

These are plain dataclasses — no Pydantic, no SQLModel — because this is a
standalone eval script, not a Flask model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class QuestionResult:
    """Per-question result record.

    Score fields are initialised to None so the judge pass can backfill them
    without touching the structure definition.
    """
    # ── original question metadata ─────────────────────────────────────────
    question_id: str
    question_text: str
    nonsensical_element: str
    domain: str
    domain_group: str
    technique: str
    difficulty: str
    difficulty_label: str
    is_control: bool

    # ── pipeline output ────────────────────────────────────────────────────
    prompt_sent: str          # full user prompt constructed for the adapter
    response_text: str        # raw text returned by adapter.rewrite() (or prompt in dry-run)
    latency_seconds: float    # wall-clock time for the adapter call
    dry_run: bool             # True when --dry-run was passed

    # ── split assignment and error state (all Optional, default None) ─────
    split: Optional[str] = None   # "tuning" | "holdout" | None (if splits.json absent)
    error: Optional[str] = None   # exception message if the call failed

    # ── judge scores (backfilled later, null by default) ──────────────────
    judge_score: Optional[int] = None
    judge_label: Optional[str] = None
    judge_reasoning: Optional[str] = None


@dataclass
class RunHeader:
    """Metadata envelope written once at the top of every result file."""
    model: str                  # confirmed model id used for the run
    provider: str               # CHAIN_PROVIDER value resolved at runtime
    timestamp_iso: str          # ISO-8601 UTC timestamp of run start
    git_commit: str             # short SHA of HEAD (or "unknown" if git unavailable)

    # ── CLI flags captured verbatim ───────────────────────────────────────
    flag_limit: Optional[int]
    flag_filter: Optional[str]
    flag_dry_run: bool
    flag_skip_judge: bool

    # ── fixture metadata ──────────────────────────────────────────────────
    fixture_version: str = ""   # value of data["version"] from questions.v2.json
    question_count: int = 0     # actual number of questions processed in this run
