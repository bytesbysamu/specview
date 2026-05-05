# Task 5: Filesystem Migration Script — Implementation Guide

**Purpose**: Imports every on-disk project into the SQL + git layer in a single idempotent CLI pass. Once verified, flipping `PROJECT_REPOSITORY=sql` in `.env` retires the filesystem path entirely.

**Effort**: 0.25 days

**Dependencies**: Task 3 (SqlProjectRepository + atomic create) must be merged.

**Parallel With**: Task 4 (history/diff/revert endpoints)

**Blocks**: Switching `PROJECT_REPOSITORY=sql` in dev and production `.env`; enables all auth and monetisation epics that assume SQL project ownership.

---

## 1. Context

The existing codebase holds project files as plain directories under `PROJECTS_DIR`; the new two-tier architecture owns the same content through `SqlProjectRepository` (row-level metadata) and `git_store` (file history). This task bridges the gap with a ~55 LOC CLI script that walks `PROJECTS_DIR`, skips any slug already present as a DB row, and for each new project calls `project_repo.create()` (atomic DB insert + git init, as shipped by Task 3) then writes each `.md` file through `git_store.write_file()`. It is a one-shot manual step, not a background job or cron — ELA Pattern #7 applies: no queue, no persistent job state, in-process iteration. A companion startup guard in `create_app.py` makes `PROJECT_REPOSITORY=fs` a hard error after cut-over, turning an ambiguous silent failure into a clear actionable message.

**Trade-offs considered:**

- **Alembic data migration** (`op.execute` SQL inside a revision) — rejected because it cannot call `git_store.init_repo()` per project; git init must happen in-process alongside the DB write.
- **Background daemon thread with polling endpoint** (ELA Pattern #4) — rejected because this is a single manual run on a known finite dataset; 202 + polling adds complexity with no benefit for a one-shot tool.
- **CLI script with explicit app context bootstrap** — preferred because it reuses `create_app()` (gets config, registered repo, DB engine for free), keeps the script under 60 LOC, and is trivially re-runnable if it fails mid-way.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
cd {WORKSPACE}/spec-doc/api

git status                                             # flag any unrelated M / ?? entries
git diff HEAD -- create_app.py                         # confirm target is clean
python -m pytest --tb=no -q 2>&1 | tail -3            # record baseline
```

**If working tree is dirty on `create_app.py`**: stash or commit unrelated changes first.

**Baseline recorded**: 624 / 624 passing (1 skipped).

---

## 3. Files

### To Create (new)

- `spec-doc/api/scripts/__init__.py` — empty; makes `scripts` a package importable by pytest
- `spec-doc/api/scripts/migrate_filesystem_to_git_db.py` — one-shot CLI migration; imports `_migrate_one` and `_get_or_create_owner` as testable helpers
- `spec-doc/api/tests/test_migration_script.py` — 7 pytest tests covering idempotency, dry-run, file writes, touch signature, error path, and the startup guard

### To Modify (cite CODEBASE CONTEXT)

- `spec-doc/api/create_app.py` — add `PROJECT_REPOSITORY=fs` guard at the top of `create_app()` body; `import os` is almost certainly already present

### To Leave Alone

- `spec-doc/api/openapi.yaml` — no new HTTP endpoints; migration is a CLI tool
- `spec-doc/api/dtos/models.py` — no DTO changes; `make check-dtos` must still pass
- `spec-doc/api/modules/projects/models.py` — consumed via `current_app.project_repository`; not modified
- `spec-doc/api/modules/git_store/service.py` — consumed as-is; no changes to the adapter boundary
- `spec-doc/api/modules/auth/models.py` — `User` entity consumed for owner bootstrap; not modified

---

## 4. Implementation Steps

### Step 1: Add `PROJECT_REPOSITORY=fs` startup guard to `create_app.py`

**Action**: Open `create_app.py` and insert the guard as the very first statement inside `create_app()`, before `Flask(__name__)` is instantiated. Confirm `import os` is already at the top of the file; add it if absent.

**File**: `spec-doc/api/create_app.py` (existing — CODEBASE CONTEXT)

**Pattern**:
```python
import os

def create_app(config=None):
    # Guard: filesystem repository retired post-migration (Task 5)
    if os.getenv("PROJECT_REPOSITORY") == "fs":
        raise RuntimeError(
            "PROJECT_REPOSITORY=fs is retired. "
            "Run scripts/migrate_filesystem_to_git_db.py, verify output, "
            "then set PROJECT_REPOSITORY=sql in .env."
        )
    app = Flask(__name__)
    # ... rest of existing factory unchanged ...
```

**Verify**: `PROJECT_REPOSITORY=fs python -c "from create_app import create_app; create_app()"` — expect `RuntimeError: PROJECT_REPOSITORY=fs is retired.`
Then: `python -m pytest --tb=short -q` — expect 624 passing (0 regressions; guard only fires when env var is `"fs"`).

---

### Step 2: Create `api/scripts/__init__.py`

**Action**: Create an empty `__init__.py` so `scripts` is a proper Python package importable by pytest running from `api/`.

**File**: `spec-doc/api/scripts/__init__.py` (new)

**Pattern**:
```python
# intentionally empty — makes scripts/ importable as a package
```

**Verify**: `python -c "import scripts"` from `api/` — expect no error.

---

### Step 3: Create the migration script

**Action**: Create the migration script. Key design points:
- `sys.path.insert` at module level so the script is runnable as `python scripts/migrate_filesystem_to_git_db.py` (adds `api/` to path for plain-script invocation; harmless when run as a package).
- `git_store` imported at module level (adapter boundary — the only import point for git ops, per ELA Pattern #1).
- `os.environ["PROJECT_REPOSITORY"] = "sql"` inside `main()` only — not at module level — so tests can control the env var freely.
- `_get_or_create_owner` and `_migrate_one` are module-level functions, importable by tests with no Flask context required.
- **Verify `repo.create()` and `repo.touch()` signatures against the Task 3 implementation before running** — the calls below match the architecture spec; adapt if Task 3 chose different parameter names.

**File**: `spec-doc/api/scripts/migrate_filesystem_to_git_db.py` (new)

**Pattern**:
```python
#!/usr/bin/env python3
"""One-shot idempotent migration: on-disk filesystem projects → DB + git.

Usage (run from api/):
    python scripts/migrate_filesystem_to_git_db.py \
        --owner-email you@example.com [--dry-run] [--projects-dir /override]
"""
import argparse
import os
import sys
from pathlib import Path

# Make api/ importable when executed as a standalone script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.git_store import service as git_store  # noqa: E402


def _get_or_create_owner(email: str) -> str:
    """Find or create a User row; return its PK as a string."""
    from sqlmodel import select
    from modules.auth.models import User
    from modules.db.session import get_session

    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            user = User(auth_user_id=f"bootstrap:{email}", email=email, plan="free")
            session.add(user)
            session.commit()
            session.refresh(user)
        return str(user.id)


def _migrate_one(slug_dir: Path, owner_id: str, repo, dry_run: bool) -> str:
    """Return 'migrated' | 'skipped' | 'error'."""
    slug = slug_dir.name
    if repo.get_by_slug(slug) is not None:
        return "skipped"
    md_files = sorted(slug_dir.glob("*.md"))
    if not md_files:
        return "skipped"
    if dry_run:
        return "migrated"
    try:
        project = repo.create(
            user_id=owner_id,
            name=slug.replace("-", " ").title(),
            slug=slug,
        )
        sha = None
        for f in md_files:
            sha = git_store.write_file(
                project.id, f.name, f.read_text(encoding="utf-8"), f"migrate: {f.name}"
            )
        if sha:
            repo.touch(project.id, sha, len(md_files))
        return "migrated"
    except Exception as exc:
        print(f"  ERROR {slug}: {exc}", file=sys.stderr)
        return "error"


def main() -> None:
    os.environ["PROJECT_REPOSITORY"] = "sql"  # pin SQL backend regardless of .env
    from create_app import create_app  # noqa: E402 – after env override

    p = argparse.ArgumentParser(description="Migrate on-disk projects to DB + git")
    p.add_argument("--owner-email", required=True, help="Email of project owner (created if absent)")
    p.add_argument("--projects-dir", default=None, help="Override PROJECTS_DIR from config")
    p.add_argument("--dry-run", action="store_true", help="Print plan without writing")
    args = p.parse_args()

    app = create_app()
    with app.app_context():
        from flask import current_app

        projects_dir = Path(args.projects_dir or current_app.config["PROJECTS_DIR"])
        if not projects_dir.is_dir():
            print(f"ERROR: {projects_dir} not found", file=sys.stderr)
            sys.exit(1)

        repo = current_app.project_repository
        owner_id = _get_or_create_owner(args.owner_email)
        counts = {"migrated": 0, "skipped": 0, "error": 0}

        for slug_dir in sorted(projects_dir.iterdir()):
            if not slug_dir.is_dir():
                continue
            status = _migrate_one(slug_dir, owner_id, repo, args.dry_run)
            counts[status] += 1
            tag = "DRY  " if args.dry_run and status == "migrated" else ""
            print(f"  {tag}{status.upper():9s}  {slug_dir.name}")

    print(
        f"\nDone — migrated={counts['migrated']} skipped={counts['skipped']} errors={counts['error']}"
    )
    sys.exit(1 if counts["error"] else 0)


if __name__ == "__main__":
    main()
```

**Verify**: `python scripts/migrate_filesystem_to_git_db.py --help` from `api/` — expect argparse help text with `--owner-email`, `--projects-dir`, `--dry-run`.
Then: `flake8 scripts/migrate_filesystem_to_git_db.py` — expect 0 violations.

---

### Step 4: Write tests

**Action**: Create the test file. Tests import `_migrate_one` directly (no Flask context needed). The guard test calls `create_app()` after `monkeypatch.setenv`, relying on the guard reading `os.getenv()` at call time (not import time).

**File**: `spec-doc/api/tests/test_migration_script.py` (new)

**Pattern**: see §5 Tests below — the full assertion bodies ARE the pattern.

**Verify**: `python -m pytest tests/test_migration_script.py -v` — expect 7 passed, 0 failed.

---

### Step 5: Dry-run verification against dev dataset

**Action**: Run a dry-run against the actual dev projects directory and inspect output for correctness before committing to a live write.

**File**: N/A — read-only inspection step

**Pattern**:
```bash
cd {WORKSPACE}/spec-doc/api
python scripts/migrate_filesystem_to_git_db.py \
    --owner-email sam@example.com \
    --dry-run
# Expected: each project slug printed as DRY  MIGRATED  <slug>
# No DB writes, no git repos created
```

**Verify**: Output lists all existing project slugs as `DRY  MIGRATED`. Zero `ERROR` lines. Exit code 0 (`echo $?`).

---

## 5. Tests

```python
"""Tests for scripts/migrate_filesystem_to_git_db.py."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure SQL backend before any module import touches the guard
os.environ.setdefault("PROJECT_REPOSITORY", "sql")

# Import testable helpers directly (no Flask context required)
from scripts.migrate_filesystem_to_git_db import _migrate_one


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _slug_dir(tmp_path: Path, slug: str, files: dict = None) -> Path:
    d = tmp_path / slug
    d.mkdir()
    for name, content in (files or {}).items():
        (d / name).write_text(content, encoding="utf-8")
    return d


def _repo(existing: bool = False):
    r = MagicMock()
    r.get_by_slug.return_value = MagicMock() if existing else None
    proj = MagicMock()
    proj.id = "proj-id-1"
    r.create.return_value = proj
    return r


# ---------------------------------------------------------------------------
# _migrate_one — idempotency and happy path
# ---------------------------------------------------------------------------

class TestMigrateOne:
    def test_skips_existing_slug(self, tmp_path):
        slug_dir = _slug_dir(tmp_path, "my-proj", {"spec.md": "# Hello"})
        repo = _repo(existing=True)

        result = _migrate_one(slug_dir, "user-1", repo, dry_run=False)

        assert result == "skipped", "existing slug must be skipped without writing"
        repo.create.assert_not_called()

    def test_skips_directory_with_no_markdown_files(self, tmp_path):
        slug_dir = _slug_dir(tmp_path, "empty-proj")  # no files

        result = _migrate_one(slug_dir, "user-1", _repo(), dry_run=False)

        assert result == "skipped", "directory with no .md files must be skipped"

    def test_dry_run_returns_migrated_without_any_writes(self, tmp_path):
        slug_dir = _slug_dir(tmp_path, "new-proj", {"spec.md": "# Spec"})
        repo = _repo()

        with patch("scripts.migrate_filesystem_to_git_db.git_store") as mock_gs:
            result = _migrate_one(slug_dir, "user-1", repo, dry_run=True)

        assert result == "migrated", "dry-run should report as migrated"
        repo.create.assert_not_called()
        mock_gs.write_file.assert_not_called()

    def test_creates_project_row_and_writes_each_file(self, tmp_path):
        slug_dir = _slug_dir(tmp_path, "new-proj", {
            "spec.md": "# Spec",
            "timeline.md": "# Timeline",
        })
        repo = _repo()
        owner_id = "user-uuid-1"

        with patch("scripts.migrate_filesystem_to_git_db.git_store") as mock_gs:
            mock_gs.write_file.return_value = "sha-abc"
            result = _migrate_one(slug_dir, owner_id, repo, dry_run=False)

        assert result == "migrated"
        repo.create.assert_called_once_with(
            user_id=owner_id,
            name="New Proj",
            slug="new-proj",
        )
        assert mock_gs.write_file.call_count == 2, "one write_file call per .md file"

    def test_touch_called_with_last_sha_and_file_count(self, tmp_path):
        slug_dir = _slug_dir(tmp_path, "proj-a", {"a.md": "A", "b.md": "B"})
        repo = _repo()
        proj = repo.create.return_value

        with patch("scripts.migrate_filesystem_to_git_db.git_store") as mock_gs:
            mock_gs.write_file.side_effect = ["sha-a", "sha-b"]
            _migrate_one(slug_dir, "user-1", repo, dry_run=False)

        repo.touch.assert_called_once_with(proj.id, "sha-b", 2)

    def test_returns_error_on_repo_create_failure(self, tmp_path):
        slug_dir = _slug_dir(tmp_path, "bad-proj", {"spec.md": "# X"})
        repo = _repo()
        repo.create.side_effect = RuntimeError("DB failure")

        with patch("scripts.migrate_filesystem_to_git_db.git_store"):
            result = _migrate_one(slug_dir, "user-1", repo, dry_run=False)

        assert result == "error", "exception during create must be caught and reported as error"


# ---------------------------------------------------------------------------
# Startup guard
# ---------------------------------------------------------------------------

class TestStartupGuard:
    def test_create_app_raises_when_project_repository_is_fs(self, monkeypatch):
        monkeypatch.setenv("PROJECT_REPOSITORY", "fs")

        from create_app import create_app

        with pytest.raises(RuntimeError, match="PROJECT_REPOSITORY=fs"):
            create_app()
```

---

## 6. Commit Plan

**Executor instruction**: run each commit immediately after completing the corresponding step — not at the end of the task.

1. `feat(create_app): reject PROJECT_REPOSITORY=fs at startup` — **after Step 1** — `create_app.py`: guard raises RuntimeError when env var is `"fs"`
2. `feat(scripts): add filesystem-to-db migration init` — **after Step 2** — `scripts/__init__.py`: empty package marker
3. `feat(scripts): one-shot idempotent filesystem migration script` — **after Step 3** — `scripts/migrate_filesystem_to_git_db.py`: full script; `flake8` clean
4. `test(scripts): migration script and startup guard unit tests` — **after Step 4, tests green** — `tests/test_migration_script.py`: 7 tests; 624 → 631 passing
5. *(No commit for Step 5 — dry-run is a read-only verification pass)*

**Deviation logging**: if any step deviates from this guide (e.g., `repo.touch()` has a different signature), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc/api
python -m pytest --tb=short -q
```

**Expected delta**: 624 → **631 passing** (7 new tests). Zero pre-existing tests broken.

```bash
flake8 scripts/migrate_filesystem_to_git_db.py tests/test_migration_script.py
```

**Expected**: 0 violations.

```bash
make check-dtos
```

**Expected**: exit 0 — DTOs unchanged.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible: `git revert <sha>`. The guard commit (Step 1) can be reverted independently of the script commit (Step 3) if the script needs more work.
- **Per-branch**: if verification fails catastrophically: `git reset --hard <pre-task-sha>` on the feature branch, or delete the branch and re-open from `master`.
- **Data safety**: the script only writes; it never deletes on-disk files. A failed migration leaves the filesystem intact. Re-running after fixing the error is safe — the idempotency check skips already-migrated slugs.

---

## 9. Deviations Allowed

- **`repo.create()` parameter names differ from `(user_id, name, slug)`** → inspect `modules/projects/models.py` (Task 3 output), adapt the call, log in commit body.
- **`repo.touch()` does not accept `file_count`** → drop the third argument; update the `test_touch_called_with_last_sha_and_file_count` assertion to match actual arity.
- **`get_session()` is a generator, not a context manager** → wrap with `contextlib.contextmanager` or use the pattern the Task 1 implementation established; do not invent a new pattern.
- **`User` model field names differ** (`auth_user_id`, `plan`) → match Task 1's `modules/auth/models.py` exactly; adapt `_get_or_create_owner` accordingly.
- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, stop and flag — do not invent.
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task delivers exactly the migration script and its startup guard. It does not touch any HTTP surface, frontend, or deployment config. An eager executor might notice adjacent opportunities — all are explicitly deferred:

- **Automated migration trigger (CI job, Makefile target)** — the architecture mandates a manual CLI step per environment; automation adds risk with no benefit for a one-shot operation.
- **`PROJECT_REPOSITORY=fs` soft-deprecation warning** (warn instead of raise) — rejected in architecture; hard error is intentional to prevent silent data divergence after cut-over.
- **`Subscription` and `UsageCounter` entities in `_get_or_create_owner`** — monetisation epic owns those class files; this task only creates a `User` bootstrap row with `plan="free"`.
- **Production `.env` flip (`PROJECT_REPOSITORY=sql`)** — this is an operator action after the script is run and verified on the target environment; it is not a code change and must not be committed to the repo.
- **Deleting on-disk project files post-migration** — a destructive operation that requires explicit operator sign-off `[REQUIRES APPROVAL]`; not part of this task.
- **`0001_initial_schema.py` coordination with the monetisation epic** — the migration script assumes the schema is already applied (`make migrate` has been run); schema authorship is Task 1's concern.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for two-tier storage and migration trigger decision
- [Epic](./epic.md) – Task scope and execution phase diagram
- [Timeline](./timeline.md) – Update status to ✅ Done after dry-run verification passes