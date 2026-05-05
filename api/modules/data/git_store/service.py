"""
modules/data/git_store/service.py
---------------------------------
All pygit2 calls live here. No other module may import pygit2 directly.
Enforced by tests/test_pygit2_isolation.py.

Eight public operations form the git contract:
  init_repo, write_file, read_file, list_files,
  get_history, get_diff, revert_file, delete_file.

All write-paths commit immediately and return the resulting SHA as a
40-character hex string. `_repos_base()` is resolved at call time (not
import time) so tests can override it with `monkeypatch.setenv`.
"""
import os
from pathlib import Path
from typing import Any, Dict, List

import pygit2

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYSTEM_AUTHOR_NAME = "spec-doc[bot]"
_SYSTEM_AUTHOR_EMAIL = "spec-doc@localhost"
_MAIN_REF = "refs/heads/main"
_BLOB_MODES = {pygit2.GIT_FILEMODE_BLOB, pygit2.GIT_FILEMODE_BLOB_EXECUTABLE}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _repos_base() -> Path:
    """Resolved at call time so tests can override via monkeypatch.setenv."""
    base = os.environ.get("GIT_REPOS_DIR") or os.environ.get("PROJECTS_DIR")
    if not base:
        raise RuntimeError(
            "GIT_REPOS_DIR (or PROJECTS_DIR) environment variable is not set"
        )
    return Path(base)


def _repo_path(project_id: str) -> Path:
    return _repos_base() / project_id


def _open_repo(project_id: str) -> pygit2.Repository:
    return pygit2.Repository(str(_repo_path(project_id)))


def _sig() -> pygit2.Signature:
    return pygit2.Signature(_SYSTEM_AUTHOR_NAME, _SYSTEM_AUTHOR_EMAIL)


def _commit(repo: pygit2.Repository, tree_oid: pygit2.Oid, msg: str, parents: list) -> str:
    sig = _sig()
    oid = repo.create_commit(_MAIN_REF, sig, sig, msg, tree_oid, parents)
    return str(oid)


def _commit_touches_file(repo: pygit2.Repository, commit: pygit2.Commit, filename: str) -> bool:
    """True if commit adds/modifies/deletes filename vs its first parent."""
    if not commit.parents:
        # Root commit: file exists in this commit iff it appears in the tree.
        try:
            commit.peel(pygit2.Tree)[filename]
            return True
        except KeyError:
            return False
    parent = commit.parents[0]
    diff = repo.diff(parent.peel(pygit2.Tree), commit.peel(pygit2.Tree))
    for patch in diff:
        delta = patch.delta
        if delta.new_file.path == filename or delta.old_file.path == filename:
            return True
    return False


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def init_repo(project_id: str) -> str:
    """
    Initialise a working repository for project_id.
    Creates an empty initial commit so HEAD is always valid.
    Returns the initial commit SHA.
    """
    path = _repo_path(project_id)
    path.mkdir(parents=True, exist_ok=True)
    repo = pygit2.init_repository(str(path), bare=False)
    # pygit2 defaults the unborn HEAD to refs/heads/master regardless of the
    # user's git config. Pin it to refs/heads/main *before* the initial commit
    # so that _commit() writing to _MAIN_REF leaves HEAD pointing at a real
    # ref. Use set_target() rather than create_reference() because HEAD is a
    # pre-existing symbolic reference on a fresh init_repository.
    repo.references["HEAD"].set_target(_MAIN_REF)
    empty_tree = repo.TreeBuilder().write()
    return _commit(repo, empty_tree, "chore: init project repo", [])


def write_file(project_id: str, filename: str, content: str, msg: str) -> str:
    """
    Write content to filename in the working tree and commit.
    Returns the new commit SHA.
    """
    repo = _open_repo(project_id)
    file_path = _repo_path(project_id) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    repo.index.read()
    repo.index.add(filename)
    repo.index.write()

    tree_oid = repo.index.write_tree()
    parent = repo.head.target
    return _commit(repo, tree_oid, msg, [parent])


def read_file(project_id: str, filename: str, ref: str = "HEAD") -> str:
    """
    Return the text content of filename at the given ref (default HEAD).
    Raises KeyError if filename does not exist at ref.
    """
    repo = _open_repo(project_id)
    commit = repo.revparse_single(ref)
    tree = commit.peel(pygit2.Tree)
    entry = tree[filename]
    blob = repo.get(entry.id)
    return blob.data.decode("utf-8")


def list_files(project_id: str, ref: str = "HEAD") -> List[str]:
    """
    Return sorted list of blob filenames at the top-level tree of ref.
    Subdirectory entries (trees) are not traversed.
    """
    repo = _open_repo(project_id)
    commit = repo.revparse_single(ref)
    tree = commit.peel(pygit2.Tree)
    return sorted(entry.name for entry in tree if entry.filemode in _BLOB_MODES)


def get_history(project_id: str, filename: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Walk the commit log and return up to `limit` entries that touched filename.
    Each entry: {"sha": str, "message": str, "timestamp": int (unix)}.
    """
    repo = _open_repo(project_id)
    walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL)
    results: List[Dict[str, Any]] = []
    for commit in walker:
        if _commit_touches_file(repo, commit, filename):
            results.append({
                "sha": str(commit.id),
                "message": commit.message.strip(),
                "timestamp": commit.commit_time,
            })
            if len(results) >= limit:
                break
    return results


def get_diff(project_id: str, filename: str, from_sha: str, to_sha: str) -> str:
    """
    Return the unified diff of filename between from_sha and to_sha.
    Empty string if filename is untouched between the two commits.
    """
    repo = _open_repo(project_id)
    a_tree = repo.revparse_single(from_sha).peel(pygit2.Tree)
    b_tree = repo.revparse_single(to_sha).peel(pygit2.Tree)
    diff = repo.diff(a_tree, b_tree)
    return "".join(
        patch.text for patch in diff
        if patch.delta.new_file.path == filename
        or patch.delta.old_file.path == filename
    )


def revert_file(project_id: str, filename: str, to_sha: str) -> str:
    """
    Restore filename to its state at to_sha via a *forward* commit.
    Never rewrites history — safe for any future GitHub mirror.
    Returns the new (forward) commit SHA.
    """
    content = read_file(project_id, filename, ref=to_sha)
    return write_file(
        project_id,
        filename,
        content,
        f"revert: {filename} to {to_sha[:8]}",
    )


def delete_file(project_id: str, filename: str, msg: str) -> str:
    """
    Remove filename from the working tree and commit.
    Internal use only — no HTTP route exposes this operation.
    Returns the new commit SHA.
    """
    repo = _open_repo(project_id)
    file_path = _repo_path(project_id) / filename
    file_path.unlink(missing_ok=True)

    repo.index.read()
    repo.index.remove(filename)
    repo.index.write()

    tree_oid = repo.index.write_tree()
    parent = repo.head.target
    return _commit(repo, tree_oid, msg, [parent])
