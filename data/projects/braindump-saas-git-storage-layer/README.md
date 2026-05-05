# spec-doc — Git-backed Storage Layer for Markdown Content

> **MERGED** into `braindump-saas-persistence.md` on 2026-04-26 (one consolidated dump per bucket).
>
> Original kept for git history; do not generate a spec from this file.
> Read the consolidated version instead.

---

## (Original brain dump below — do not act on)

> **Priority**: P1 — foundational; differentiating storage choice.
> **Effort**: ~1 day (six pygit2 ops + three new endpoints + tests).
> **Blocks**: SaaS launch (multi-tenant content needs durable per-user storage),
>             "Connect GitHub" upsell (Phase 4 — free side-effect of this layer).
> **Depends on**: data-layer (Project entity must hold `git_repo_path` + `latest_commit_sha`).
> **Siblings**: `braindump-saas-data-layer.md` (paired — DB metadata + git content),
>               `braindump-saas-auth-magic-link.md` (per-project repo lives under the user).
> **Net new architecture** — bubls/trendfy don't have this pattern (their content is
> structured rows, not text). Do not look for a "port from" source.

## What

Replace the filesystem-as-truth model with a **per-project git repository** as the canonical store for every markdown file spec-doc produces. Each project gets its own bare-or-working git repo at `/data/projects/<id>/.git/`. Every `update_file()` call commits. History, diff, blame, and revert are first-class capabilities served by git directly. No DB rows for file content, no version tables, no diff machinery to write.

This is the load-bearing storage decision for the SaaS migration. Markdown is text — git is the right tool. SQL would force inventing version-table schemas, diff functions, and history queries that git does in microseconds. Bubls/trendfy don't have this pattern (they store generated images and structured form data, where SQL is correct); spec-doc is text-first, so spec-doc gets git.

The future "Connect GitHub" feature (Phase 4) is a one-line `git push` away once this layer exists — the user's data lives in a real git repo from day one and can be exported wholesale to their own GitHub account.

### 1. New module — `api/modules/git_store/`

```
modules/git_store/
├── __init__.py
├── service.py          # all the public ops below
├── errors.py           # GitStoreError, FileNotFound, RepoCorrupt
└── tests/
    ├── conftest.py     # tmp_path fixture for isolated repos
    └── test_service.py
```

### 2. The public surface — `service.py`

Everything the rest of the app needs is six functions. Implemented via `pygit2` (libgit2 bindings — fast, in-process, no subprocess overhead). Subprocess `git` fallback is documented in §9.

```python
from pathlib import Path
import pygit2

_DATA_ROOT = Path(os.environ.get("SPEC_DOC_DATA_ROOT", "/data/projects"))
_AUTHOR    = pygit2.Signature("spec-doc", "system@spec-doc.app")


def init_repo(project_id: int) -> Path:
    """Create an empty repo with an initial commit. Returns the .git dir path."""
    repo_path = _DATA_ROOT / str(project_id)
    repo_path.mkdir(parents=True, exist_ok=False)
    repo = pygit2.init_repository(str(repo_path), bare=False, initial_head="main")
    # Empty initial commit so HEAD always exists
    tree = repo.TreeBuilder().write()
    repo.create_commit("HEAD", _AUTHOR, _AUTHOR, "chore: initialise project", tree, [])
    return repo_path / ".git"


def write_file(project_id: int, filename: str, content: str, message: str | None = None) -> str:
    """Write filename → content; commit; return the new SHA."""
    repo = _open(project_id)
    (repo.workdir / filename).write_text(content)
    repo.index.add(filename)
    repo.index.write()
    tree = repo.index.write_tree()
    parent = [repo.head.target]
    sha = repo.create_commit(
        "HEAD", _AUTHOR, _AUTHOR,
        message or f"feat({filename}): update",
        tree, parent,
    )
    return str(sha)


def read_file(project_id: int, filename: str, ref: str = "HEAD") -> str:
    """Return the content of filename at the given ref (default HEAD)."""
    repo = _open(project_id)
    commit = repo.revparse_single(ref)
    blob = commit.tree[filename]      # raises KeyError if absent
    return repo[blob.id].data.decode("utf-8")


def list_files(project_id: int, ref: str = "HEAD") -> list[str]:
    """Return all .md filenames at the given ref. Excludes .git, hidden files."""
    repo = _open(project_id)
    tree = repo.revparse_single(ref).tree
    return sorted(entry.name for entry in tree if entry.name.endswith(".md"))


def get_history(project_id: int, filename: str | None = None, limit: int = 50) -> list[dict]:
    """Return commit metadata. If filename given, restrict to commits touching it."""
    repo = _open(project_id)
    walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TIME)
    out = []
    for commit in walker:
        if filename and not _commit_touches(repo, commit, filename):
            continue
        out.append({
            "sha":       str(commit.id),
            "message":   commit.message.strip(),
            "author":    commit.author.name,
            "timestamp": commit.commit_time,
        })
        if len(out) >= limit:
            break
    return out


def get_diff(project_id: int, filename: str, from_sha: str, to_sha: str = "HEAD") -> str:
    """Return unified diff of filename between two refs."""
    repo = _open(project_id)
    a = repo.revparse_single(from_sha).tree[filename]
    b = repo.revparse_single(to_sha).tree[filename]
    return repo.diff_blob_to_blob(repo[a.id], repo[b.id]).patch


def revert_file(project_id: int, filename: str, to_sha: str) -> str:
    """Restore filename to its content at to_sha; commit; return new SHA."""
    content = read_file(project_id, filename, ref=to_sha)
    return write_file(project_id, filename, content, message=f"revert({filename}): to {to_sha[:8]}")
```

### 3. Wiring into existing routes

```python
# modules/projects/routes.py
from modules.git_store import service as git_store

@projects_bp.put("/<slug>/files/<filename>")
@require_auth
def update_file(slug: str, filename: str):
    project = current_app.project_repository.get_by_slug(g.current_user.id, slug)
    body = request.get_json(force=True)
    new_sha = git_store.write_file(project.id, filename, body["content"])
    current_app.project_repository.touch(project.id, new_sha)
    return jsonify({"sha": new_sha})


@projects_bp.get("/<slug>/files/<filename>")
@require_auth
def read_file(slug: str, filename: str):
    project = current_app.project_repository.get_by_slug(g.current_user.id, slug)
    ref = request.args.get("ref", "HEAD")  # ?ref=<sha> for time-travel
    return jsonify({"content": git_store.read_file(project.id, filename, ref=ref)})
```

`task_gen` and `spec_gen` workflows call `git_store.write_file()` instead of writing to the filesystem directly. The repository's `Project.touch()` updates `latest_commit_sha` after each successful write; failed writes leave the row alone, so the DB is always consistent with the repo.

### 4. New routes the git layer unlocks (Phase 1, free with the layer)

```python
@projects_bp.get("/<slug>/files/<filename>/history")
def file_history(slug, filename):
    project = ...resolve...
    return jsonify(git_store.get_history(project.id, filename=filename))


@projects_bp.get("/<slug>/files/<filename>/diff")
def file_diff(slug, filename):
    project = ...resolve...
    from_sha = request.args["from"]
    to_sha = request.args.get("to", "HEAD")
    return Response(git_store.get_diff(project.id, filename, from_sha, to_sha), mimetype="text/x-diff")


@projects_bp.post("/<slug>/files/<filename>/revert")
def file_revert(slug, filename):
    project = ...resolve...
    to_sha = request.json["sha"]
    new_sha = git_store.revert_file(project.id, filename, to_sha)
    current_app.project_repository.touch(project.id, new_sha)
    return jsonify({"sha": new_sha})
```

These three endpoints together produce a "doc edit history" feature in Angular without any extra backend work. **History is a free side-effect of the storage choice.**

### 5. Commit message conventions

Auto-commit messages from the runtime:

| Trigger | Commit message |
|---|---|
| `bootstrap_project` workflow writes a file | `feat(<filename>): generated by bootstrap` |
| `task_gen` writes a file | `feat(<filename>): generated by task_gen` |
| User edits file in Angular | `edit(<filename>): user edit` |
| Revert call | `revert(<filename>): to <short-sha>` |
| Project created | `chore: initialise project` |

These are the executor's bookkeeping; users see them in the history view but aren't expected to read them as documentation.

### 6. Dependencies

```
# requirements.txt — add
pygit2>=1.15.0
```

`pygit2` ships compiled wheels for linux/macos x86_64 and arm64. The Coolify deploy container (python:3.11-slim) installs it cleanly via pip.

### 7. .env additions

```
SPEC_DOC_DATA_ROOT=/data/projects     # production path (Coolify volume)
                                      # dev: ./data/projects (gitignored)
```

The Coolify production deploy mounts `/data/projects` as a persistent volume. Container restarts preserve the data; the DB and git both survive.

### 8. Tests

```python
# modules/git_store/tests/test_service.py
def init_repo_creates_emptyHeadCommit(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.git_store.service._DATA_ROOT", tmp_path)
    git_store.init_repo(42)
    assert (tmp_path / "42" / ".git").is_dir()
    assert git_store.list_files(42) == []   # empty initial commit

def write_file_returnsCommitSha(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.git_store.service._DATA_ROOT", tmp_path)
    git_store.init_repo(1)
    sha = git_store.write_file(1, "epic.md", "# Epic\n")
    assert len(sha) == 40  # full git SHA
    assert git_store.read_file(1, "epic.md") == "# Epic\n"

def get_history_filtersToFilename(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.git_store.service._DATA_ROOT", tmp_path)
    git_store.init_repo(1)
    git_store.write_file(1, "epic.md", "v1")
    git_store.write_file(1, "analysis.md", "a1")
    git_store.write_file(1, "epic.md", "v2")
    history = git_store.get_history(1, filename="epic.md")
    assert len(history) == 2  # only epic.md commits
```

Each test gets its own `tmp_path`-scoped data root, so tests run in parallel without colliding.

### 9. Subprocess fallback (out of scope by default)

If `pygit2` is somehow unavailable on a target platform, the same six functions can be implemented via `subprocess.run(["git", ...])`. Slower (one process per op) but works. The Protocol shape stays identical so the swap is a binding change. Don't implement until needed.

## Why now

The data-layer brain dump's user-tenant work is meaningless without a content store that scales with the multi-user load. SQL for content would mean rewriting bytes per edit, slow full-text queries, painful diff implementations, and no native versioning. Git solves all four for free; pygit2 makes it a library call, not a process spawn.

The bubls + trendfy codebases never had this need (their content is structured rows, not text), so there's no "port from" — this is **net-new architecture for spec-doc** that no sibling app has. That's a feature, not a bug: spec-doc's content shape is genuinely different from the others, and forcing it into bubls's row-based model would be a worse design.

The "Connect GitHub" upsell (Phase 4) is essentially free once this exists — `git remote add origin <user-github-url> && git push`. Compared to a SQL-backed system that would need a custom export pipeline, this is a 10x reduction in feature surface for the most differentiated piece of the product positioning.

## What's missing

One decision: **per-project repo (Option A) or shared monorepo with branches (Option B)?**

- (a) **Per-project repo** at `/data/projects/<id>/.git/` (proposed) — clean boundary, easy to mirror to user's GitHub later, easy to garbage-collect on project delete. Drawback: more inodes; storage scales linearly with project count.
- (b) **Shared monorepo** with `project/<id>` branch per project — single repo to back up, deduplicates blob storage. Drawback: more complex export-to-user-GitHub story; one corrupt repo affects everyone.

(a) is right. Storage is cheap; isolation matters more than dedup; the GitHub-mirror story is the killer-app argument.

## Explicitly out of scope

- **GitHub OAuth + push-to-user-repo flow** — separate brain dump (`braindump-saas-github-integration.md`); requires this layer to exist first.
- **Branching / collaboration / merge requests within spec-doc** — the git repo *supports* it but the UI does not; speculative until a consumer asks.
- **Custom commit signing** — signed commits are a Phase 4+ enterprise feature.
- **LFS for non-text artifacts** — spec-doc is markdown-only; if image generation lands later, that's a different storage decision.
- **A pure libgit2-bindings replacement for `pygit2`** — `pygit2` is the standard; switch only if it stops being maintained.
- **Webhook on every commit (for external consumers)** — Phase 4+ once a consumer is named.
- **Garbage collection / repack scheduling** — git auto-gc handles it; revisit only if storage becomes a concern.
- **Cross-project copy / fork** — speculative; revisit if "create a project from another's analysis" is a real use case.
