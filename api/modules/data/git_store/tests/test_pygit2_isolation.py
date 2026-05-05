"""
modules/data/git_store/tests/test_pygit2_isolation.py
-----------------------------------------------------
Adapter-wall guard for the git layer.

Mirrors the contract that `modules/chain/adapter.py` enforces for AI: no
file outside `modules/data/git_store/` may import `pygit2` directly. All
git operations must flow through the eight public functions exposed by
`modules.data.git_store`.
"""
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[4]  # api/


def test_pygit2_only_imported_via_git_store():
    """
    No file outside modules/data/git_store/ may import pygit2.

    Rule: ELA Adapter Pattern — feature code imports the public git_store
          interface, never the pygit2 library directly. This keeps the
          libgit2 system dependency contained to one module and makes a
          future swap (e.g., to GitPython or a remote git service) a
          single-file change.

    Fix:  Move the call into modules/data/git_store/service.py and expose
          a public function from modules/data/git_store/__init__.py.
    """
    offenders = []
    for py_file in _API_ROOT.rglob("*.py"):
        relative = py_file.relative_to(_API_ROOT)
        parts = relative.parts
        # Allow anything inside the git_store package itself.
        if "git_store" in parts:
            continue
        # Skip virtualenvs / build artefacts that may sit under api/.
        if any(part in {".venv", "venv", "build", "dist"} for part in parts):
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "import pygit2" in line or "from pygit2" in line:
                offenders.append(f"{relative}:{lineno}: {stripped}")

    assert not offenders, (
        "pygit2 must only be imported inside modules/data/git_store/.\n"
        "Move the call into service.py and expose a public function via "
        "modules/data/git_store/__init__.py:\n"
        + "\n".join(f"  {o}" for o in offenders)
    )


def test_git_store_public_interface_complete():
    """
    The public package must export all eight ops by name. Catches a
    typo or missing re-export in __init__.py before consumers break.
    """
    import modules.data.git_store as gs

    expected = {
        "init_repo",
        "write_file",
        "read_file",
        "list_files",
        "get_history",
        "get_diff",
        "revert_file",
        "delete_file",
    }
    missing = sorted(name for name in expected if not hasattr(gs, name))
    assert not missing, (
        f"modules/data/git_store/__init__.py is missing re-exports: {missing}.\n"
        "Add each name to the `from .service import (...)` block and to __all__."
    )
