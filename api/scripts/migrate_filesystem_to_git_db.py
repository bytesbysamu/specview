#!/usr/bin/env python3
"""One-shot idempotent migration: on-disk filesystem projects -> SQL + git.

Walks every slug directory under PROJECTS_DIR, and for each one not already
present as a Project row:

  1. Bootstrap-creates a User row (if one for --owner-email is missing)
  2. Calls SqlProjectRepository.create() which atomically writes the
     Project row AND initialises the per-project git repo at
     GIT_REPOS_DIR/<project_id>/ (rolls back the row on git failure).
  3. Streams every *.md file through git_store.write_file(), one commit
     per file.
  4. Calls repo.touch() with the final SHA + total file count.

Idempotence: re-running is a no-op. The check `repo.get_by_slug(slug) is
not None` short-circuits any project already migrated, so partial runs
can be safely retried after fixing whatever caused the failure.

Usage (from api/):

    python -m scripts.migrate_filesystem_to_git_db \\
        --owner-email you@example.com [--dry-run] \\
        [--projects-dir /override] [--git-repos-dir /override]

Exit code: 0 on full success, 1 if any project errored.

Deviations from task-5 spec (see commit body):
  - SqlProjectRepository.create() requires git_repo_path as a 4th arg
  - get_session lives at modules.data.db.session (not modules.db.session)
  - Instantiate SqlProjectRepository() directly (create_app.py does not
    yet wire current_app.project_repository — out of scope to add)
  - User.id is int (not UUID); we pass project.user_id as int.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Make api/ importable when executed as a standalone script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.data import git_store  # noqa: E402  – adapter boundary


def _get_or_create_owner(email: str) -> int:
    """Find or bootstrap-create a User row; return its integer PK.

    Bootstrap users are tagged `auth_user_id="bootstrap:<email>"` so the
    auth epic can later distinguish them from real Neon Auth-issued IDs.
    """
    from sqlmodel import select  # local import to defer DB engine warm-up

    from modules.auth.models import User
    from modules.data.db.session import get_session

    with get_session() as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            user = User(
                auth_user_id=f"bootstrap:{email}",
                email=email,
                plan="free",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        assert user.id is not None, "User.id must be assigned after commit"
        return int(user.id)


def _project_name(slug_dir: Path, slug: str) -> str:
    """Prefer the `name` from project.json when present; fall back to a
    title-cased version of the slug. Mirrors the on-disk convention used
    by every existing project (see e.g. babyname-1776249304927/project.json).
    """
    project_json = slug_dir / "project.json"
    if project_json.is_file():
        try:
            data = json.loads(project_json.read_text(encoding="utf-8"))
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        except (json.JSONDecodeError, OSError):
            pass
    return slug.replace("-", " ").title()


def _migrate_one(
    slug_dir: Path,
    owner_id: int,
    repo,
    git_repos_dir: Path,
    dry_run: bool,
) -> tuple[str, int]:
    """Migrate a single project directory.

    Returns (status, files_written) where status is one of
    "migrated" | "skipped" | "error".
    """
    slug = slug_dir.name
    if repo.get_by_slug(slug) is not None:
        return ("skipped", 0)

    md_files = sorted(slug_dir.glob("*.md"))
    if not md_files:
        return ("skipped", 0)

    if dry_run:
        return ("migrated", len(md_files))

    try:
        project = repo.create(
            user_id=owner_id,
            name=_project_name(slug_dir, slug),
            slug=slug,
            git_repo_path=str(git_repos_dir / slug),
        )
        last_sha: Optional[str] = None
        for f in md_files:
            last_sha = git_store.write_file(
                str(project.id),
                f.name,
                f.read_text(encoding="utf-8"),
                f"migrate: {f.name}",
            )
        if last_sha is not None:
            repo.touch(project.id, last_sha, len(md_files))
        return ("migrated", len(md_files))
    except Exception as exc:  # pragma: no cover - exercised via test
        print(f"  ERROR {slug}: {exc}", file=sys.stderr)
        return ("error", 0)


def _build_repo():
    """Construct SqlProjectRepository against the module-level engine.

    Lazy-imports to defer SQLModel metadata registration until after env
    overrides (DATABASE_URL, GIT_REPOS_DIR) are applied by main().
    """
    # Side-effect imports register User + Project tables
    import modules.auth.models  # noqa: F401
    import modules.data.projects.models  # noqa: F401

    from modules.data.projects.repository import SqlProjectRepository

    return SqlProjectRepository()


def _resolve_dirs(args) -> tuple[Path, Path]:
    """Resolve projects_dir and git_repos_dir from args + env, with the
    same precedence used by config.py and git_store._repos_base()."""
    from config import PROJECTS_DIR  # late import: respects env at call time

    projects_dir = Path(args.projects_dir) if args.projects_dir else Path(PROJECTS_DIR)
    git_repos_dir = Path(
        args.git_repos_dir
        or os.environ.get("GIT_REPOS_DIR")
        or os.environ.get("PROJECTS_DIR")
        or projects_dir
    )
    return projects_dir, git_repos_dir


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Migrate on-disk projects into the SQL + git layer.",
    )
    p.add_argument(
        "--owner-email",
        required=True,
        help="Email of the project owner (User row created if absent).",
    )
    p.add_argument(
        "--projects-dir",
        default=None,
        help="Override the on-disk projects source dir (default: PROJECTS_DIR).",
    )
    p.add_argument(
        "--git-repos-dir",
        default=None,
        help="Override the destination git repos root (default: GIT_REPOS_DIR).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without touching the DB or creating repos.",
    )
    args = p.parse_args(argv)

    projects_dir, git_repos_dir = _resolve_dirs(args)

    if not projects_dir.is_dir():
        print(f"ERROR: projects dir not found: {projects_dir}", file=sys.stderr)
        return 1

    if not args.dry_run:
        git_repos_dir.mkdir(parents=True, exist_ok=True)
        # git_store._repos_base() reads GIT_REPOS_DIR at call time. Pin it so
        # write_file/init_repo write under the chosen destination regardless
        # of how the script was launched.
        os.environ["GIT_REPOS_DIR"] = str(git_repos_dir)

    repo = _build_repo()
    owner_id = (
        _get_or_create_owner(args.owner_email) if not args.dry_run else 0
    )

    counts = {"migrated": 0, "skipped": 0, "error": 0}
    files_total = 0

    for slug_dir in sorted(projects_dir.iterdir()):
        if not slug_dir.is_dir():
            continue
        status, files_written = _migrate_one(
            slug_dir, owner_id, repo, git_repos_dir, args.dry_run
        )
        counts[status] += 1
        files_total += files_written
        tag = "DRY  " if args.dry_run and status == "migrated" else ""
        print(f"  {tag}{status.upper():9s}  {slug_dir.name}")

    print(
        f"\nImported {counts['migrated']} projects, {files_total} files, "
        f"{counts['skipped']} skipped, {counts['error']} errors"
    )
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
