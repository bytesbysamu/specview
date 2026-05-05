# Task 2: Git Store Module — Implementation Guide

## 1. Context

This task delivers `modules/git_store/`, the per-project git layer that underpins every SaaS persistence capability in this epic. Seven public operations — `init_repo`, `write_file`, `read_file`, `list_files`, `get_history`, `get_diff`, `revert_file`, and `delete_file` — wrap all `pygit2` calls behind a single module boundary, establishing the same adapter-wall for git that `modules/chain/adapter.py` establishes for AI. Without this module, Task 3 (SqlProjectRepository) cannot wire an atomic create (DB insert + git init), Task 4 cannot serve history/diff/revert endpoints, and Task 5 cannot migrate filesystem projects into version-controlled repos. The Docker image change for `libgit2` is a hard definition-of-done item: the image builds without it but crashes on first `init_repo` call at runtime. No Blueprint or HTTP route lands here — this is a pure service module consumed by higher layers.

**Trade-offs considered:**
- **subprocess + git CLI** — rejected; shell-injection risk on every file write, and per-commit subprocess overhead is measurable when bootstrapping dozens of files during migration.
- **shared monorepo (all projects in one git repo)** — rejected per architecture decision; cross-project blast radius, no independent GitHub export, garbage-collect-on-delete impossible without rewriting history.
- **`pygit2` with per-project working repository** — preferred; native libgit2 bindings eliminate shell risk, one `.git/` per project gives clean isolation and independent export path, revert-as-forward-commit preserves audit trail compatible with any future GitHub mirror.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From {WORKSPACE}/api/
git status                                        # Flag any unrelated M/?? entries
git diff HEAD -- requirements.txt config.py       # Confirm target files are clean
git diff HEAD -- Dockerfile ../Dockerfile         # Check both candidate Dockerfile locations
python -m pytest --tb=no -q 2>&1 | tail -3        # Record baseline; expect 624 passed, 1 skipped
```

**Also run** to determine Dockerfile base image before Step 2:

```bash
head -3 {WORKSPACE}/Dockerfile 2>/dev/null || head -3 {WORKSPACE}/api/Dockerfile 2>/dev/null
# Note: python:3.11-slim (Debian) → apt-get path; python:3.11-alpine → apk path
```

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**Baseline recorded**: 624 / 624 passing.

---

## 3. Files

### To Create (new)

- `api/modules/git_store/__init__.py` — public interface; re-exports all seven operations so callers never import from `.service` directly
- `api/modules/git_store/service.py` — all `pygit2` calls; the only file in the codebase that may `import pygit2`
- `api/modules/git_store/tests/__init__.py` — empty; makes the directory a pytest-discoverable package
- `api/modules/git_store/tests/test_service.py` — fifteen unit tests covering all eight public ops

### To Modify (cite CODEBASE CONTEXT)

- `api/requirements.txt` — add `pygit2>=1.14.0`; no equivalent currently present
- `api/config.py` — add `GIT_REPOS_DIR` resolution (defaults to `PROJECTS_DIR`); currently holds `SPEC_DOC_DIR`, `CONTEXT_PATHS`, `PROJECTS_DIR`
- `{WORKSPACE}/Dockerfile` — add `libgit2` system dependency; currently missing (definition-of-done requirement). Confirm path in Pre-flight; if both `Dockerfile` and `api/Dockerfile` exist, modify the one the CI build uses.
- `api/tests/test_structural.py` — add one coupling-guard test; currently contains `everyOpenapiPath_hasRouteHandler`

### To Leave Alone

- `api/modules/chain/adapter.py` — this task does not touch the AI adapter boundary; only the git boundary is established here
- `api/modules/projects/service.py` — still the filesystem implementation; Task 3 replaces it; touching it now creates a merge conflict with Task 1
- `api/dtos/models.py` — no new OpenAPI paths this task; no DTO regeneration needed
- `api/openapi.yaml` — history/diff/revert endpoints are Task 4; do not add them here

---

## 4. Implementation Steps

### Step 1: Add `pygit2` to requirements

**Action**: Append `pygit2>=1.14.0` to `api/requirements.txt`. Pin to `>=1.14.0` because that release ships manylinux wheels with bundled libgit2 on Debian-based images, eliminating the system package requirement on those targets.

**File**: `api/requirements.txt` (modify; exists per CODEBASE CONTEXT)

**Pattern**:
```text
# existing entries above...
pygit2>=1.14.0
```

**Verify**:
```bash
cd {WORKSPACE}/api && pip install -r requirements.txt && python -c "import pygit2; print(pygit2.__version__)"
# Expect: version string >= 1.14.0, no ImportError
```

---

### Step 2: Update Dockerfile for `libgit2`

**Action**: Add the `libgit2` system package to the Docker image. Locate the Dockerfile confirmed in Pre-flight. For a **Debian-slim** base (`python:3.11-slim`), add an `apt-get` layer in the system-deps block. For an **Alpine** base (`python:3.11-alpine`), add an `apk add` layer. Insert immediately before the `COPY requirements.txt` / `pip install` layer so Docker layer caching still applies on code-only changes.

**File**: `{WORKSPACE}/Dockerfile` (modify; exact path confirmed in Pre-flight)

**Pattern — Debian-slim base**:
```dockerfile
# --- system deps ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgit2-dev \
    && rm -rf /var/lib/apt/lists/*

# --- python deps (existing layer, unchanged) ---
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

**Pattern — Alpine base**:
```dockerfile
RUN apk add --no-cache libgit2-dev

COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

**Verify**:
```bash
# [REQUIRES APPROVAL] — builds a Docker image
docker build -t spec-doc-git-test {WORKSPACE} && \
  docker run --rm spec-doc-git-test python -c "import pygit2; print('libgit2 OK', pygit2.__version__)"
# Expect: "libgit2 OK <version>"
```

> If Docker build is not available locally, skip the docker build verify; the CI pipeline's docker-build job will catch failures. Mark this as a deviation in the commit body.

---

### Step 3: Add `GIT_REPOS_DIR` to config

**Action**: Add a `GIT_REPOS_DIR` key to `api/config.py` that resolves as `os.environ.get("GIT_REPOS_DIR") or PROJECTS_DIR`. This lets the git service read from `{SPEC_DOC_DIR}/projects/` in dev (same root as existing filesystem projects) and `/data/projects/` in Docker via an env override, with no additional `.env` entry required for local dev.

**File**: `api/config.py` (modify; exists per CODEBASE CONTEXT)

**Pattern** (add after `PROJECTS_DIR` resolution):
```python
# Existing resolution — keep as-is
PROJECTS_DIR: str = os.environ.get("PROJECTS_DIR", os.path.join(SPEC_DOC_DIR, "projects"))

# New — git repos base; defaults to PROJECTS_DIR so dev needs no extra .env entry
GIT_REPOS_DIR: str = os.environ.get("GIT_REPOS_DIR") or PROJECTS_DIR
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "import config; print(config.GIT_REPOS_DIR)"
# Expect: path matching PROJECTS_DIR value (e.g., .../spec-doc/projects)
```

---

### Step 4: Implement `git_store/service.py`

**Action**: Create `api/modules/git_store/service.py` with all eight public operations and three private helpers. `SYSTEM_AUTHOR` is a module-level constant; `_repos_base()` reads `GIT_REPOS_DIR` at call time (not at import time) so tests can override it via `monkeypatch.setenv`. Every write path commits immediately and returns the resulting SHA as a hex string.

**File**: `api/modules/git_store/service.py` (new)

**Pattern**:
```python
"""
modules/git_store/service.py
----------------------------
All pygit2 calls live here. No other module may import pygit2 directly.
Enforced by test_structural.py::test_pygit2_only_imported_via_git_store.
"""
import os
from pathlib import Path
from typing import List, Dict, Any

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
        raise RuntimeError("GIT_REPOS_DIR (or PROJECTS_DIR) environment variable is not set")
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
        try:
            commit.peel(pygit2.Tree)[filename]
            return True
        except KeyError:
            return False
    parent = commit.parents[0]
    diff = repo.diff(parent.peel(pygit2.Tree), commit.peel(pygit2.Tree))
    return any(
        p.delta.new_file.path == filename or p.delta.old_file.path == filename
        for p in diff
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def init_repo(project_id: str) -> str:
    """
    Initialise a bare working repository for project_id.
    Creates an empty initial commit so HEAD is always valid.
    Returns the initial commit SHA.
    """
    path = _repo_path(project_id)
    path.mkdir(parents=True, exist_ok=True)
    repo = pygit2.init_repository(str(path), bare=False)
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
        p.text for p in diff
        if p.delta.new_file.path == filename or p.delta.old_file.path == filename
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
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "
import os, tempfile
os.environ['GIT_REPOS_DIR'] = tempfile.mkdtemp()
from modules.git_store.service import init_repo, write_file, read_file
sha = init_repo('smoke-test')
sha2 = write_file('smoke-test', 'hello.md', '# Hello', 'test: smoke')
content = read_file('smoke-test', 'hello.md')
assert content == '# Hello', repr(content)
print('smoke OK, sha=', sha2[:8])
"
# Expect: "smoke OK, sha= <8 chars>"
```

---

### Step 5: Create `git_store/__init__.py`

**Action**: Create the public interface file. Callers (Task 3's `SqlProjectRepository`, Task 4's route handlers, Task 5's migration script) import from `modules.git_store`, never from `modules.git_store.service` directly. This keeps the module boundary clean and makes the coupling test in Step 6 meaningful.

**File**: `api/modules/git_store/__init__.py` (new)

**Pattern**:
```python
"""
modules/git_store
-----------------
Public interface for all git operations.
Import ONLY from this module — never from .service directly.
"""
from .service import (       # noqa: F401
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
```

**Verify**:
```bash
cd {WORKSPACE}/api && python -c "
import modules.git_store as gs
fns = ['init_repo','write_file','read_file','list_files','get_history','get_diff','revert_file','delete_file']
missing = [f for f in fns if not hasattr(gs, f)]
assert not missing, f'Missing from __init__: {missing}'
print('__init__ OK')
"
# Expect: "__init__ OK"
```

---

## 5. Tests

Create `api/modules/git_store/tests/__init__.py` (empty file) and `api/modules/git_store/tests/test_service.py`:

```python
"""
modules/git_store/tests/test_service.py
Unit tests for all eight public git_store operations.
"""
import pytest
import modules.git_store as git_store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT = "test-proj-xyz"


@pytest.fixture
def repos_dir(tmp_path, monkeypatch):
    """Redirect git_store to a temp directory; isolated per test."""
    monkeypatch.setenv("GIT_REPOS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def initialized_repo(repos_dir):
    """An initialized repo with no extra files; returns project_id."""
    git_store.init_repo(PROJECT)
    return PROJECT


@pytest.fixture
def repo_with_file(initialized_repo):
    """Repo pre-loaded with 'spec.md'; returns (project_id, write_sha)."""
    sha = git_store.write_file(initialized_repo, "spec.md", "# Spec v1", "feat: add spec")
    return initialized_repo, sha


# ---------------------------------------------------------------------------
# init_repo
# ---------------------------------------------------------------------------

def test_init_repo_creates_git_directory(repos_dir):
    git_store.init_repo(PROJECT)
    assert (repos_dir / PROJECT / ".git").is_dir(), ".git directory must exist after init"


def test_init_repo_returns_sha(repos_dir):
    sha = git_store.init_repo(PROJECT)
    assert isinstance(sha, str) and len(sha) == 40, f"Expected 40-char hex SHA, got {sha!r}"


def test_init_repo_head_is_valid(repos_dir):
    """HEAD must be resolvable immediately after init (no 'unborn HEAD' errors downstream)."""
    import pygit2
    git_store.init_repo(PROJECT)
    repo = pygit2.Repository(str(repos_dir / PROJECT))
    # revparse_single("HEAD") raises KeyError on unborn HEAD
    commit = repo.revparse_single("HEAD")
    assert str(commit.id), "HEAD must resolve to a valid commit OID"


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

def test_write_file_persists_content(initialized_repo):
    git_store.write_file(initialized_repo, "notes.md", "hello world", "add notes")
    content = git_store.read_file(initialized_repo, "notes.md")
    assert content == "hello world", f"Content mismatch: {content!r}"


def test_write_file_returns_40_char_sha(initialized_repo):
    sha = git_store.write_file(initialized_repo, "a.md", "A", "add a")
    assert len(sha) == 40, f"Expected 40-char SHA, got {sha!r}"


def test_write_file_commit_message_preserved(initialized_repo):
    import pygit2
    from pathlib import Path
    git_store.write_file(initialized_repo, "x.md", "X", "my: custom message")
    repo_path = str(Path(pytest.importorskip("os").environ["GIT_REPOS_DIR"]) / initialized_repo)
    repo = pygit2.Repository(repo_path)
    assert repo.head.peel(pygit2.Commit).message.strip() == "my: custom message"


def test_write_file_twice_produces_two_additional_commits(initialized_repo):
    import pygit2
    import os
    git_store.write_file(initialized_repo, "f.md", "v1", "v1")
    git_store.write_file(initialized_repo, "f.md", "v2", "v2")
    repo = pygit2.Repository(str(os.environ["GIT_REPOS_DIR"] + "/" + initialized_repo))
    walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL)
    shas = [str(c.id) for c in walker]
    # init commit + 2 write commits = 3 total
    assert len(shas) == 3, f"Expected 3 commits, got {len(shas)}"


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

def test_read_file_at_head(repo_with_file):
    project_id, _ = repo_with_file
    content = git_store.read_file(project_id, "spec.md")
    assert content == "# Spec v1"


def test_read_file_at_specific_sha(initialized_repo):
    sha1 = git_store.write_file(initialized_repo, "doc.md", "version one", "v1")
    git_store.write_file(initialized_repo, "doc.md", "version two", "v2")
    content_at_sha1 = git_store.read_file(initialized_repo, "doc.md", ref=sha1)
    assert content_at_sha1 == "version one", f"Expected v1 content at sha1, got {content_at_sha1!r}"


def test_read_file_missing_raises_key_error(initialized_repo):
    with pytest.raises(KeyError):
        git_store.read_file(initialized_repo, "does-not-exist.md")


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

def test_list_files_returns_written_filenames(initialized_repo):
    git_store.write_file(initialized_repo, "alpha.md", "a", "add alpha")
    git_store.write_file(initialized_repo, "beta.md", "b", "add beta")
    files = git_store.list_files(initialized_repo)
    assert files == ["alpha.md", "beta.md"], f"Unexpected listing: {files}"


def test_list_files_excludes_deleted_file(initialized_repo):
    git_store.write_file(initialized_repo, "keep.md", "keep", "add keep")
    git_store.write_file(initialized_repo, "drop.md", "drop", "add drop")
    git_store.delete_file(initialized_repo, "drop.md", "remove drop")
    files = git_store.list_files(initialized_repo)
    assert "drop.md" not in files, f"Deleted file still listed: {files}"
    assert "keep.md" in files


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

def test_get_history_includes_commit_touching_file(initialized_repo):
    git_store.write_file(initialized_repo, "story.md", "draft", "add story")
    history = git_store.get_history(initialized_repo, "story.md")
    assert len(history) == 1, f"Expected 1 history entry, got {len(history)}"
    assert "add story" in history[0]["message"]
    assert len(history[0]["sha"]) == 40


def test_get_history_excludes_unrelated_commits(initialized_repo):
    git_store.write_file(initialized_repo, "story.md", "v1", "add story")
    git_store.write_file(initialized_repo, "other.md", "x", "add other")  # does not touch story.md
    history = git_store.get_history(initialized_repo, "story.md")
    assert len(history) == 1, f"History for story.md should not include other.md commit; got {history}"


def test_get_history_respects_limit(initialized_repo):
    for i in range(5):
        git_store.write_file(initialized_repo, "log.md", f"v{i}", f"update {i}")
    history = git_store.get_history(initialized_repo, "log.md", limit=3)
    assert len(history) == 3, f"Expected 3 entries with limit=3, got {len(history)}"


# ---------------------------------------------------------------------------
# get_diff
# ---------------------------------------------------------------------------

def test_get_diff_returns_unified_patch(initialized_repo):
    sha_a = git_store.write_file(initialized_repo, "readme.md", "line one\n", "v1")
    sha_b = git_store.write_file(initialized_repo, "readme.md", "line one\nline two\n", "v2")
    diff = git_store.get_diff(initialized_repo, "readme.md", sha_a, sha_b)
    assert "+line two" in diff, f"Expected addition in diff, got:\n{diff}"


def test_get_diff_empty_for_untouched_file(initialized_repo):
    sha_a = git_store.write_file(initialized_repo, "a.md", "aaa", "add a")
    sha_b = git_store.write_file(initialized_repo, "b.md", "bbb", "add b")
    diff = git_store.get_diff(initialized_repo, "a.md", sha_a, sha_b)
    # a.md not changed between sha_a and sha_b
    assert diff == "", f"Expected empty diff for untouched file, got: {diff!r}"


# ---------------------------------------------------------------------------
# revert_file
# ---------------------------------------------------------------------------

def test_revert_file_restores_content_via_forward_commit(initialized_repo):
    sha_v1 = git_store.write_file(initialized_repo, "doc.md", "original\n", "v1")
    git_store.write_file(initialized_repo, "doc.md", "overwritten\n", "v2")
    git_store.revert_file(initialized_repo, "doc.md", sha_v1)
    current = git_store.read_file(initialized_repo, "doc.md")
    assert current == "original\n", f"Revert did not restore content: {current!r}"


def test_revert_file_does_not_rewrite_history(initialized_repo):
    import pygit2, os
    sha_v1 = git_store.write_file(initialized_repo, "doc.md", "v1\n", "v1")
    git_store.write_file(initialized_repo, "doc.md", "v2\n", "v2")
    git_store.revert_file(initialized_repo, "doc.md", sha_v1)
    repo = pygit2.Repository(os.environ["GIT_REPOS_DIR"] + "/" + initialized_repo)
    walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL)
    count = sum(1 for _ in walker)
    # init + v1 + v2 + revert = 4 commits; history must not be rewritten shorter
    assert count == 4, f"Expected 4 commits after revert, got {count}"


# ---------------------------------------------------------------------------
# delete_file
# ---------------------------------------------------------------------------

def test_delete_file_removes_file_from_listing(initialized_repo):
    git_store.write_file(initialized_repo, "temp.md", "temp content", "add temp")
    git_store.delete_file(initialized_repo, "temp.md", "remove temp")
    files = git_store.list_files(initialized_repo)
    assert "temp.md" not in files, f"File still present after delete: {files}"


def test_delete_file_returns_sha(initialized_repo):
    git_store.write_file(initialized_repo, "d.md", "d", "add d")
    sha = git_store.delete_file(initialized_repo, "d.md", "del d")
    assert len(sha) == 40, f"Expected 40-char SHA from delete, got {sha!r}"
```

**Structural test** — add to the existing `api/tests/test_structural.py`:

```python
def test_pygit2_only_imported_via_git_store():
    """
    ELA #1 adapter boundary for git: no file outside modules/git_store/ may
    import pygit2 directly. Enforces the same isolation contract as the chain
    adapter.
    """
    from pathlib import Path
    api_root = Path(__file__).resolve().parent.parent  # api/
    offenders = []
    for py_file in api_root.rglob("*.py"):
        relative = py_file.relative_to(api_root)
        parts = relative.parts
        if "git_store" in parts:
            continue  # allowed
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        if "import pygit2" in text or "from pygit2" in text:
            offenders.append(str(relative))
    assert not offenders, (
        f"pygit2 imported outside modules/git_store/ — move the call there:\n"
        + "\n".join(f"  {o}" for o in offenders)
    )
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes. Do not batch at the end.

1. `feat(requirements): add pygit2>=1.14.0 dependency` — after Step 1 — `api/requirements.txt`: add pygit2 pin
2. `build(docker): add libgit2 system dependency for pygit2` — after Step 2 — `{WORKSPACE}/Dockerfile`: apt-get or apk layer for libgit2-dev
3. `feat(config): add GIT_REPOS_DIR resolution with PROJECTS_DIR fallback` — after Step 3 — `api/config.py`: new `GIT_REPOS_DIR` constant
4. `feat(git_store): implement eight-operation git service and public interface` — after Steps 4 + 5 — `api/modules/git_store/__init__.py`, `api/modules/git_store/service.py`
5. `test(git_store): unit tests for all eight ops + pygit2 coupling guard` — after tests pass — `api/modules/git_store/tests/__init__.py`, `api/modules/git_store/tests/test_service.py`, `api/tests/test_structural.py`

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/api && python -m pytest --tb=short -q
```

**Expected delta**: 624 → 640 passing (16 new tests: 15 unit + 1 structural). Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each step has its own commit. `git revert <sha>` reverts cleanly without touching other steps. Steps 4 and 5 are the only ones with intra-module dependencies — if Step 5 is reverted, Step 4 is still safe to leave in place (no test-imposed runtime requirement).
- **Per-branch**: if the verification run produces broken pre-existing tests, `git reset --hard <pre-task-sha>` on the feature branch, or delete the branch and re-open from the baseline commit recorded in Pre-flight.
- **pip environment**: if pygit2 installation introduces a conflict, `pip install -r requirements.txt` after reverting `requirements.txt` restores the prior environment.

---

## 9. Deviations Allowed

- **Dockerfile path differs** from `{WORKSPACE}/Dockerfile` → locate via `find {WORKSPACE} -name Dockerfile -not -path '*/.git/*' | head -5`; modify the one the CI `docker build` command references; log deviation in commit 2's body.
- **Dockerfile base image is Alpine** → use `apk add --no-cache libgit2-dev` instead of the apt-get block; log deviation.
- **`test_structural.py` does not yet exist** → create it with the single test; do not look for it beyond `api/tests/`; log deviation.
- **`pygit2` wheel fails on the local platform** (rare; seen on M-series Macs with certain libgit2 versions) → `brew install libgit2 && pip install --no-binary pygit2 pygit2>=1.14.0`; log deviation in commit 1's body.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log in the commit.
- **Side-effect required** (docker push, pip publish) → STOP, mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

Task 2 delivers the git layer as a standalone service module. It deliberately stops there: no HTTP routes, no Blueprint registration, no database join between the git SHA and any Project row, and no migration of existing filesystem projects. All of that wiring happens in Tasks 3–5, where the correct abstractions (SqlProjectRepository, route handlers, migration script) already have clear homes. Absorbing any of the following into this task would couple Task 2 to Task 1's unreleased DB schema or Task 4's unreleased OpenAPI additions.

- **HTTP routes for history/diff/revert** — Task 4 scope; require OpenAPI additions, DTO regeneration, and a project Blueprint extension that depends on Task 3's `SqlProjectRepository`
- **`ProjectRepository.touch(sha)`** — Task 3 scope; depends on the `Project` SQLModel entity from Task 1
- **Alembic migration** — Task 1 scope; `git_repo_path` and `latest_commit_sha` columns land in the initial schema, not here
- **`migrate_filesystem_to_git_db.py`** — Task 5 scope; requires both the DB (Task 1+3) and this module to be fully wired before it can iterate existing project directories
- **Subdirectory traversal in `list_files`** — no current consumer requires it; re-evaluate when a nested-file UI exists
- **`delete_file` HTTP route** — architecture explicitly defers this until a UI consumer exists; do not add a route or OpenAPI path for it here

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for per-project repo shape, pygit2 choice, revert-as-forward-commit decision
- [Epic](./epic.md) – Full task list; Task 2 runs parallel with Task 1
- [Timeline](./timeline.md) – Update status to `done` after Step 7 verification passes