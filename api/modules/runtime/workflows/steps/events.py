"""StepEvent domain types — Observer contract for AbstractStep lifecycle.

Every AbstractStep.execute() call yields exactly two events:
  success path  → StepStarted, StepCompleted
  failure path  → StepStarted, StepFailed

All three are frozen Pydantic v2 models: safe to cache, compare by value,
and serialise directly to SSE payloads without a separate DTO layer.
"""
from __future__ import annotations

from typing import Any, Union

from pydantic import BaseModel, ConfigDict


class StepStarted(BaseModel):
    """Emitted after input validation passes, before _invoke is called."""

    model_config = ConfigDict(frozen=True)

    step_name: str
    run_id: str
    started_at: float  # time.monotonic() snapshot at execution entry


class StepCompleted(BaseModel):
    """Emitted after _invoke returns successfully."""

    model_config = ConfigDict(frozen=True)

    step_name: str
    run_id: str
    started_at: float
    completed_at: float
    latency_ms: int
    output: Any


class StepFailed(BaseModel):
    """Emitted after _invoke raises; the exception is re-raised after emission."""

    model_config = ConfigDict(frozen=True)

    step_name: str
    run_id: str
    started_at: float
    failed_at: float
    latency_ms: int
    error: str


#: Union alias consumed by AbstractStep.execute() return annotation and the runtime.
StepEvent = Union[StepStarted, StepCompleted, StepFailed]
