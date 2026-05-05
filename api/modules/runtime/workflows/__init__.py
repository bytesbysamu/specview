"""Workflow domain — Layers B, C, D.

Public surface
--------------
Layer B — Step kinds (modules.runtime.workflows.steps)
    AbstractStep, StepContext, AICall, Compute
    StepStarted, StepCompleted, StepFailed, StepEvent

Layer C — Workflow aggregate (modules.runtime.workflows.workflow)
    Workflow, WorkflowBuilder, WorkflowRef

Layer D — Execution engine (modules.runtime.workflows.execution / .runtime)
    WorkflowExecution      — Command object; owns the lifecycle state machine
    ExecutionStatus        — NEW | IN_PROGRESS | COMPLETED | ERROR | TIMEOUT |
                             CANCELLING | CANCELLED
    InvalidStatusTransition — raised on illegal transition
    WorkflowRuntime        — synchronous generator engine
"""
from .execution import (
    ExecutionStatus,
    InvalidStatusTransition,
    WorkflowExecution,
)
from .runtime import WorkflowRuntime
from .steps import (
    AbstractStep,
    StepContext,
    StepCompleted,
    StepEvent,
    StepFailed,
    StepStarted,
)
from .workflow import Workflow, WorkflowRef

__all__ = [
    # Layer B — Steps
    "AbstractStep",
    "StepContext",
    "StepStarted",
    "StepCompleted",
    "StepFailed",
    "StepEvent",
    # Layer C — Workflow
    "Workflow",
    "WorkflowRef",
    # Layer D — Execution
    "ExecutionStatus",
    "InvalidStatusTransition",
    "WorkflowExecution",
    "WorkflowRuntime",
]
