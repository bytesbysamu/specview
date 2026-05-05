"""
modules/data/git_store
----------------------
Public interface for all git operations.
Import ONLY from this module — never from .service directly.

This module is the sole adapter wall for `pygit2`: feature code that needs
git operations imports the eight functions below; no other file in the
codebase may `import pygit2`. The structural test in
`tests/test_pygit2_isolation.py` enforces that contract.
"""
from .service import (  # noqa: F401
    init_repo,
    write_file,
    read_file,
    list_files,
    get_history,
    get_diff,
    revert_file,
    delete_file,
)

__all__ = [
    "init_repo",
    "write_file",
    "read_file",
    "list_files",
    "get_history",
    "get_diff",
    "revert_file",
    "delete_file",
]
