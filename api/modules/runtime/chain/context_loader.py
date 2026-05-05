"""Context file loader for spec-doc V2.

Adapted from references.md:383–460 (Bubls context/loader.py).
Spec-doc change: no manifest.json — four fixed files at workspace root.
Mock mode: set CONTEXT_PROVIDER=mock.

Structural invariant: this is the ONLY module that reads the four workspace
context files. Feature modules call load_context() / load_all_context() here.
"""
from __future__ import annotations

import os
from pathlib import Path

# Workspace root = spec-doc/ = parents[3] from flask/modules/chain/context_loader.py
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]

_CONTEXT_FILES: dict[str, Path] = {
    "builder": _WORKSPACE_ROOT / "builder.md",
    "principles": _WORKSPACE_ROOT / "principles.md",
    "codebase": _WORKSPACE_ROOT / "codebase.md",
    "references": _WORKSPACE_ROOT / "references.md",
}


def _is_mock() -> bool:
    return os.environ.get("CONTEXT_PROVIDER", "").lower() == "mock"


def load_context(name: str) -> str:
    """Load a single context file by name.

    Returns empty string if the file does not exist (panels may not be populated).
    Raises KeyError for unknown names.
    """
    if _is_mock():
        return f"MOCK_CONTEXT[{name}]"
    path = _CONTEXT_FILES.get(name)
    if path is None:
        raise KeyError(
            f"Unknown context file {name!r}. Available: {sorted(_CONTEXT_FILES)}"
        )
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_all_context() -> dict[str, str]:
    """Load all four context files. Missing files return empty string."""
    return {name: load_context(name) for name in _CONTEXT_FILES}
