"""WorkflowRuntime — Layer D synchronous generator engine.

Iterates a Workflow's steps in order, threads a shared StepContext
through each, and re-yields the StepEvents that AbstractStep already
emits.  The runtime is responsible only for:

  - driving the WorkflowExecution lifecycle
        NEW -> IN_PROGRESS -> COMPLETED | ERROR
  - constructing the shared StepContext from execution.inputs
  - propagating step outputs (already written by AbstractStep into
    context.outputs[step.name]) onto execution.outputs
  - halting on the first failed step and recording the error

It does NOT emit events itself — AbstractStep.execute is the sealed
Template Method that owns event emission.  Drainable directly in tests
without an HTTP layer; the SSE wrapper is a Task 5 concern.
"""
from __future__ import annotations

from typing import Iterator

from .execution import ExecutionStatus, WorkflowExecution
from .steps import StepContext, StepEvent
from .workflow import Workflow


class WorkflowRuntime:
    """Synchronous generator-based execution engine.

    Usage::

        for event in WorkflowRuntime().run(execution, workflow):
            ...

    Precondition: ``execution.status is ExecutionStatus.NEW``.
    """

    def run(
        self,
        execution: WorkflowExecution,
        workflow: Workflow,
    ) -> Iterator[StepEvent]:
        """Drive *execution* through *workflow*, yielding StepEvents in order.

        Lifecycle:
            1. ``execution.start()`` — NEW -> IN_PROGRESS (raises if not NEW).
            2. For each step in ``workflow.steps`` (ordered tuple):
                a. Drain ``step.execute(context)`` and re-yield each event.
                b. If the step's generator raises, yield-then-re-raise is
                   handled by AbstractStep itself; we catch the re-raise here,
                   call ``execution.fail(...)``, and stop iterating.
            3. On clean completion: ``execution.complete()`` — IN_PROGRESS -> COMPLETED.

        Outputs from each step land in ``context.outputs[step.name]`` (written
        by AbstractStep before StepCompleted is yielded).  The runtime mirrors
        these onto ``execution.outputs`` after each successful step so the
        Command object is the durable record of the run.

        Cancellation:
            Between every step iteration the runtime checks
            ``execution.status is ExecutionStatus.CANCELLING``.  If a caller
            invoked ``execution.request_cancel()`` from another thread, the
            runtime transitions ``CANCELLING -> CANCELLED`` and returns
            before the next step starts.  Cancellation is cooperative
            (between-steps); an in-flight ``step.execute()`` always runs to
            completion.  Cancellation latency is at most one full step.
        """
        execution.start()

        context = StepContext(
            run_id=execution.execution_id,
            inputs=dict(execution.inputs),
            outputs={},
        )

        for step in workflow.steps:
            if execution.status is ExecutionStatus.CANCELLING:
                execution.cancel()
                return
            last_event: StepEvent | None = None
            try:
                for event in step.execute(context):
                    last_event = event
                    yield event
            except Exception as exc:
                # AbstractStep yields StepFailed *then* re-raises; the
                # StepFailed event has already been forwarded above.  Defensive
                # fallback: if a non-AbstractStep object raised before yielding
                # StepFailed, fabricate nothing — propagation of the original
                # exception's message into execution.error is sufficient.
                _ = last_event  # retained for clarity / future tracing
                if not execution.is_terminal:
                    execution.fail(str(exc))
                return

            # AbstractStep wrote the step's output into context.outputs[name];
            # mirror it onto execution.outputs so callers can read results
            # without holding the StepContext.
            if step.name in context.outputs:
                execution.outputs[step.name] = context.outputs[step.name]

        execution.complete()
