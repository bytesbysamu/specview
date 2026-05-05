"""WorkflowRepository port — ELA hexagonal boundary (Layer E).

INVARIANT: All consumers import from this module only.
           Never import from fs_adapter directly outside the app factory.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Workflow is from Tasks 1–3; not imported at runtime to avoid
    # circular-import risk before that task is complete.
    from ..workflow import Workflow


class WorkflowNotFound(Exception):
    """Raised by WorkflowRepository.get() when name has no registered workflow."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Workflow not found: {name!r}")
        self.name = name


class WorkflowRepository(ABC):
    """Port: the only legal access path to workflow definitions.

    Implementors: WorkflowRepositoryFs (Phase 1), WorkflowRepositoryDb (Phase 3+).
    """

    @abstractmethod
    def get(self, name: str) -> "Workflow":
        """Return the Workflow registered under *name*.

        Raises WorkflowNotFound if no workflow is registered under that name.
        Qualified names use the form ``feature/workflow-name``
        (e.g. ``spec_gen/generate-spec``).
        """

    @abstractmethod
    def list(self) -> list[str]:
        """Return a sorted list of all registered qualified workflow names."""

    @abstractmethod
    def save(self, workflow: "Workflow") -> None:
        """Register *workflow* under its name.

        Overwrites any existing registration for the same name.
        Phase 1 callers: _PrefixedRepo (internal to fs_adapter) and tests.
        """
