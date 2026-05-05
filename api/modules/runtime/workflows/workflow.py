"""Workflow aggregate — Layer C.
ELA Patterns: #1 (Builder), #8 (Facade), #20 (Aggregate Root).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowRef:
    """Stable identifier for a named Workflow.

    External callers (route handlers, WorkflowExecution) hold WorkflowRef,
    not the Workflow object itself.

    name: qualified identifier — ``"<feature>/<workflow-name>"``,
          e.g. ``"spec_gen/generate-spec"``.
    """
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError(
                "WorkflowRef.name must be a non-empty, non-blank string"
            )

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"WorkflowRef({self.name!r})"


class WorkflowBuilder:
    """Fluent Builder (ELA Pattern #1). Only legal construction path for Workflow.

    Usage::

        wf = (
            Workflow.builder("spec_gen/generate-spec")
            .inputs("braindump", "project_name")
            .outputs("spec_markdown")
            .step(step_a)
            .step(step_b)
            .build()
        )
    """

    def __init__(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("Workflow name must not be empty or blank")
        self._name: str = name
        self._inputs: set[str] = set()
        self._outputs: set[str] = set()
        self._steps: list[Any] = []

    # ── Fluent setters ──────────────────────────────────────────────────────

    def inputs(self, *names: str) -> "WorkflowBuilder":
        """Declare one or more input names. Chainable."""
        self._inputs.update(names)
        return self

    def outputs(self, *names: str) -> "WorkflowBuilder":
        """Declare one or more output names. Chainable."""
        self._outputs.update(names)
        return self

    def step(self, s: Any) -> "WorkflowBuilder":
        """Append one Step to the ordered step list. Chainable."""
        self._steps.append(s)
        return self

    # ── Terminal ────────────────────────────────────────────────────────────

    def build(self) -> "Workflow":
        """Validate all invariants and return a frozen Workflow.

        Raises ValueError listing every unmet invariant (not just the first).
        """
        errors: list[str] = []
        if not self._inputs:
            errors.append("at least one input must be declared (.inputs(...))")
        if not self._outputs:
            errors.append("at least one output must be declared (.outputs(...))")
        if not self._steps:
            errors.append("at least one step must be appended (.step(...))")
        if errors:
            raise ValueError(
                f"Cannot build Workflow {self._name!r}: " + "; ".join(errors)
            )
        return Workflow(
            ref=WorkflowRef(self._name),
            inputs=frozenset(self._inputs),
            outputs=frozenset(self._outputs),
            steps=tuple(self._steps),
        )

    # ── Internal ────────────────────────────────────────────────────────────

    @classmethod
    def _from_workflow(cls, w: "Workflow") -> "WorkflowBuilder":
        """Reconstruct a mutable builder from a frozen Workflow (for to_builder())."""
        b = cls(w.ref.name)
        b._inputs = set(w.inputs)
        b._outputs = set(w.outputs)
        b._steps = list(w.steps)
        return b


@dataclass(frozen=True)
class Workflow:
    """Aggregate Root (ELA Pattern #20). Named, immutable, ordered Step container.

    Construct exclusively via ``Workflow.builder(name)``.
    Direct instantiation bypasses all builder-enforced invariants.

    steps: ordered tuple of AbstractStep instances.
           Authorised consumer: WorkflowRuntime (Layer D) only.
           Route handlers must not enumerate or reference individual steps.
    """
    ref: WorkflowRef
    inputs: frozenset[str]
    outputs: frozenset[str]
    steps: tuple[Any, ...]

    # ── Read-only derived ──────────────────────────────────────────────────

    @property
    def step_count(self) -> int:
        """Number of steps in this workflow."""
        return len(self.steps)

    # ── Construction ───────────────────────────────────────────────────────

    @staticmethod
    def builder(name: str) -> WorkflowBuilder:
        """Fluent Builder entry point. The sole legal construction path."""
        return WorkflowBuilder(name)

    def to_builder(self) -> WorkflowBuilder:
        """Return a Builder pre-populated from this Workflow for creating variations.

        The returned builder is independent; calling build() produces a new
        Workflow and leaves this one unchanged (frozen).
        """
        return WorkflowBuilder._from_workflow(self)
