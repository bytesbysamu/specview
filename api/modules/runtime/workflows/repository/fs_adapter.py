"""WorkflowRepositoryFs — filesystem adapter for WorkflowRepository port.

Startup walk (called once from create_app):
  for each modules/<feature>/workflows/[!_]*.py:
      import file → call register_workflows(_PrefixedRepo(repo, feature))

_PrefixedRepo transparently qualifies workflow names as "feature/workflow.name"
so workflow definition files use plain names (e.g. "generate-spec") and the
repository stores qualified names (e.g. "spec_gen/generate-spec").
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from . import WorkflowNotFound, WorkflowRepository


def _workflow_name(workflow: object) -> str:
    """Extract a workflow's plain name.

    Supports both the real Workflow aggregate (Tasks 1–3) which exposes
    ``workflow.ref.name`` (frozen WorkflowRef) and lightweight stand-ins
    used by tests that expose ``workflow.name`` directly.
    """
    ref = getattr(workflow, "ref", None)
    if ref is not None and hasattr(ref, "name"):
        return ref.name
    return workflow.name  # type: ignore[attr-defined]


class WorkflowRepositoryFs(WorkflowRepository):
    """In-process, dict-backed workflow registry.

    Populated at startup by from_modules_dir().
    """

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    # ── Port implementation ────────────────────────────────────────────────

    def get(self, name: str) -> object:
        if name not in self._store:
            raise WorkflowNotFound(name)
        return self._store[name]

    def list(self) -> list[str]:
        return sorted(self._store)

    def save(self, workflow: object) -> None:
        self._store[_workflow_name(workflow)] = workflow

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def from_modules_dir(cls, modules_dir: Path) -> "WorkflowRepositoryFs":
        """Walk modules_dir for workflow definition files and register them.

        Searches two layouts:
          1. modules_dir/<feature>/workflows/[!_]*.py            (legacy flat layout)
          2. modules_dir/ai/workflows/<feature>/[!_]*.py         (post-restructure layout)

        Skips files whose name begins with '_' (e.g. __init__.py).
        Skips Python files that define no register_workflows() function.
        Excludes the runtime workflow engine itself (modules/runtime/workflows/).
        """
        repo = cls()

        # Layout 1: legacy <feature>/workflows/*.py
        for workflows_dir in sorted(modules_dir.glob("*/workflows")):
            if not workflows_dir.is_dir():
                continue
            feature = workflows_dir.parent.name
            # Skip the runtime workflow engine itself and ai (which uses Layout 2).
            if feature in ("runtime", "ai"):
                continue
            prefixed = _PrefixedRepo(repo, feature)
            for py_file in sorted(workflows_dir.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                _import_and_register(py_file, feature, prefixed)

        # Layout 2: post-restructure ai/workflows/<feature>/*.py
        ai_workflows = modules_dir / "ai" / "workflows"
        if ai_workflows.is_dir():
            for feature_dir in sorted(ai_workflows.iterdir()):
                if not feature_dir.is_dir() or feature_dir.name.startswith("_"):
                    continue
                feature = feature_dir.name
                prefixed = _PrefixedRepo(repo, feature)
                for py_file in sorted(feature_dir.glob("*.py")):
                    if py_file.name.startswith("_"):
                        continue
                    _import_and_register(py_file, feature, prefixed)

        return repo


# ── Internal helpers ───────────────────────────────────────────────────────

def _import_and_register(
    py_file: Path,
    feature: str,
    repo: WorkflowRepository,
) -> None:
    """Import py_file and call register_workflows(repo) if the function exists."""
    module_name = f"_workflow_def_{feature}_{py_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, py_file)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load workflow definition file {py_file}: {exc}"
        ) from exc
    if callable(getattr(mod, "register_workflows", None)):
        mod.register_workflows(repo)


class _PrefixedRepo(WorkflowRepository):
    """Internal adapter that qualifies workflow names with a feature prefix.

    Workflow files call repo.save(workflow) using plain names like "generate-spec";
    _PrefixedRepo stores and retrieves them under "feature/generate-spec".
    """

    def __init__(self, delegate: WorkflowRepositoryFs, feature: str) -> None:
        self._delegate = delegate
        self._feature = feature

    def get(self, name: str) -> object:
        return self._delegate.get(f"{self._feature}/{name}")

    def list(self) -> list[str]:
        prefix = f"{self._feature}/"
        return [n[len(prefix):] for n in self._delegate.list() if n.startswith(prefix)]

    def save(self, workflow: object) -> None:
        qualified = f"{self._feature}/{_workflow_name(workflow)}"
        self._delegate._store[qualified] = workflow
