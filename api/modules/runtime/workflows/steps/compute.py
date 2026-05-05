"""Compute — concrete Step that dispatches to a registered pure-Python callable.

Design constraints (hard lines from architecture)
-------------------------------------------------
- No eval.  No exec.  No anonymous functions at dispatch time.
- ``fn_name`` is resolved from the CallableRegistry at _invoke time, not at
  Compute construction time.  This allows Workflows to be defined before their
  callables are registered (e.g. at module import vs. app startup order).
- The callable's return value is returned directly from _invoke; no wrapping.

Callable contract
-----------------
    fn(context: StepContext) -> Any

The same StepContext that AbstractStep.execute() received is forwarded
unchanged. Callables read ``context.inputs`` and ``context.outputs`` and
return any JSON-serialisable value.
"""
from __future__ import annotations

from typing import Any

from .base import AbstractStep, StepContext
from .registry import get as _registry_get


class Compute(AbstractStep):
    """Frozen value object: one registered callable invocation.

    Fields
    ------
    name      Step identity string; must be unique within a Workflow.
              Inherited from AbstractStep.
    fn_name   Name the callable was registered under in the CallableRegistry.
              Resolved at _invoke time — not validated at construction time.
    """

    fn_name: str

    def _invoke(self, context: StepContext) -> Any:
        fn = _registry_get(self.fn_name)  # raises KeyError if not registered
        return fn(context)
