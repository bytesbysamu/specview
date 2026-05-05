"""AbstractStep — Template Method foundation for all workflow step kinds.

AbstractStep is a frozen Pydantic v2 BaseModel + ABC. Concrete step kinds
(AICall, Compute — Task 1.2) inherit from it and add their own fields; they
remain frozen value objects with equality-by-value semantics.

Execute lifecycle (sealed — subclasses must NOT override `execute`):
  1. _validate_inputs → raises ValueError on missing keys; no events emitted
  2. StepStarted      → yielded
  3. _invoke          → subclass-defined; result stored in context.outputs[name]
  4a. StepCompleted   → yielded (success)
  4b. StepFailed      → yielded then original exception re-raised (failure)
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator

from pydantic import BaseModel, ConfigDict

from .events import StepCompleted, StepEvent, StepFailed, StepStarted


@dataclass
class StepContext:
    """Shared execution bag threaded through every step in a workflow run.

    Attributes:
        run_id:  Stable identifier for the enclosing WorkflowExecution.
        inputs:  Caller-supplied data; treat as read-only inside _invoke.
        outputs: Accumulated step results; written by AbstractStep.execute(),
                 keyed by step name.  Read by later steps to chain results.
    """

    run_id: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] = field(default_factory=dict)


class AbstractStep(BaseModel, ABC):
    """Template Method base for all step kinds.

    Frozen Pydantic v2 BaseModel — subclass instances are immutable and compare
    equal by field values. ``name`` is a Pydantic field; subclasses pass it as
    a constructor kwarg (no property override required).

    Subclasses MUST implement:
        _invoke       — the step's work; return value becomes the step output

    Subclasses MAY override:
        required_inputs — frozenset of input keys that must exist in context.inputs
    """

    model_config = ConfigDict(frozen=True)

    name: str

    @property
    def required_inputs(self) -> frozenset[str]:
        """Input keys required before _invoke is called.

        Default: empty (no validation).  Override to declare dependencies.
        Validation failure raises ValueError *before* any event is emitted.
        """
        return frozenset()

    def _validate_inputs(self, context: StepContext) -> None:
        """Raise ValueError if any key in required_inputs is absent from context.inputs."""
        missing = self.required_inputs - context.inputs.keys()
        if missing:
            raise ValueError(
                f"Step '{self.name}' missing required inputs: {sorted(missing)}"
            )

    @abstractmethod
    def _invoke(self, context: StepContext) -> Any:
        """Perform the step's work and return the output.

        - Read from context.inputs and context.outputs (prior step results).
        - Do NOT write to context.outputs — execute() does that after invoke returns.
        - Raise any exception to trigger the StepFailed branch.
        """

    def execute(self, context: StepContext) -> Iterator[StepEvent]:
        """Sealed Template Method — emits lifecycle events around _invoke.

        Yields:
            StepStarted   — always (after validation succeeds)
            StepCompleted — on success; context.outputs[self.name] is set before yield
            StepFailed    — on failure; the original exception is re-raised after yield

        Raises:
            ValueError  — if required_inputs are missing (no events emitted)
            Exception   — re-raised from _invoke after StepFailed has been yielded
        """
        self._validate_inputs(context)

        started_at = time.monotonic()
        yield StepStarted(
            step_name=self.name,
            run_id=context.run_id,
            started_at=started_at,
        )

        try:
            output = self._invoke(context)
            completed_at = time.monotonic()
            context.outputs[self.name] = output
            yield StepCompleted(
                step_name=self.name,
                run_id=context.run_id,
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=int((completed_at - started_at) * 1000),
                output=output,
            )
        except Exception as exc:
            failed_at = time.monotonic()
            yield StepFailed(
                step_name=self.name,
                run_id=context.run_id,
                started_at=started_at,
                failed_at=failed_at,
                latency_ms=int((failed_at - started_at) * 1000),
                error=str(exc),
            )
            raise
