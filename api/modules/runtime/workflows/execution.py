"""WorkflowExecution — Layer D Command object + lifecycle state machine.

The state machine is the single authoritative encoding of the lifecycle:

    NEW ──► IN_PROGRESS ──► COMPLETED
                       └──► ERROR
                       └──► TIMEOUT
                       └──► CANCELLING ──► CANCELLED

No other code branches on status strings; mutation is funnelled through
``transition()`` so every illegal arc raises ``InvalidStatusTransition``.

WorkflowExecution is the Command object encapsulating a workflow run
request. It owns ``inputs`` (caller-supplied), ``outputs`` (accumulated
by the runtime as steps complete), and ``error`` (set by ``fail``).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ExecutionStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"


_VALID_TRANSITIONS: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
    ExecutionStatus.NEW:        frozenset({ExecutionStatus.IN_PROGRESS}),
    ExecutionStatus.IN_PROGRESS: frozenset({
        ExecutionStatus.COMPLETED,
        ExecutionStatus.ERROR,
        ExecutionStatus.TIMEOUT,
        ExecutionStatus.CANCELLING,
    }),
    ExecutionStatus.CANCELLING: frozenset({ExecutionStatus.CANCELLED}),
    ExecutionStatus.COMPLETED:  frozenset(),
    ExecutionStatus.ERROR:      frozenset(),
    ExecutionStatus.TIMEOUT:    frozenset(),
    ExecutionStatus.CANCELLED:  frozenset(),
}


class InvalidStatusTransition(Exception):
    """Raised when a status transition not in _VALID_TRANSITIONS is attempted."""


@dataclass
class WorkflowExecution:
    """Command object encapsulating a workflow run request.

    Attributes
    ----------
    workflow_ref   Identifier of the Workflow to run (e.g. "task_gen/<project_id>").
                   Stored as a str so this module does not import Layer C types.
    inputs         Caller-supplied inputs; passed unchanged into the runtime.
    execution_id   Stable UUID generated once at construction.
    submitted_at   UTC wall-clock at construction.
    status         Current lifecycle status; mutate only via the transition helpers.
    error          Set by ``fail(message)``; None otherwise.
    outputs        Accumulated step outputs; populated by the runtime as steps complete.
    """

    workflow_ref: str
    inputs: dict[str, Any]
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    status: ExecutionStatus = ExecutionStatus.NEW
    error: str | None = None
    outputs: dict[str, Any] = field(default_factory=dict)
    # Task 4 (saas-reliability): warnings accumulated by truncation heuristics
    # in WorkflowRuntime after each successful step completes. Single-writer:
    # only the runtime appends; route handlers read.
    warnings: list[str] = field(default_factory=list)
    # Task 4 (saas-reliability): name of the step currently being driven by
    # WorkflowRuntime; surfaced in the polling response so the Angular live
    # preview can label which step's _partials buffer it is rendering.
    current_step_name: str | None = None

    # ── Transition primitives ─────────────────────────────────────────────

    def transition(self, new_status: ExecutionStatus) -> None:
        """Move ``status`` to ``new_status`` if the arc is in _VALID_TRANSITIONS."""
        allowed = _VALID_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidStatusTransition(
                f"Cannot transition {self.status.value} -> {new_status.value}. "
                f"Allowed from {self.status.value}: "
                f"{sorted(s.value for s in allowed) or '[]'}"
            )
        self.status = new_status

    def start(self) -> None:
        """NEW -> IN_PROGRESS."""
        self.transition(ExecutionStatus.IN_PROGRESS)

    def complete(self) -> None:
        """IN_PROGRESS -> COMPLETED."""
        self.transition(ExecutionStatus.COMPLETED)

    def timeout(self) -> None:
        """IN_PROGRESS -> TIMEOUT."""
        self.transition(ExecutionStatus.TIMEOUT)

    def request_cancel(self) -> None:
        """IN_PROGRESS -> CANCELLING."""
        self.transition(ExecutionStatus.CANCELLING)

    def cancel(self) -> None:
        """CANCELLING -> CANCELLED."""
        self.transition(ExecutionStatus.CANCELLED)

    def fail(self, error: str) -> None:
        """IN_PROGRESS -> ERROR; also records ``error`` message."""
        self.transition(ExecutionStatus.ERROR)
        self.error = error

    # ── Predicates ────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self.status is ExecutionStatus.IN_PROGRESS

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.ERROR,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED,
        }
