"""Unit + integration tests for SqlProjectRepository.

Wires:
  - Pers-T1's DB engine (SQLModel + SQLite in-memory for tests)
  - Pers-T2's git_store (PROJECTS_DIR pointed at tmp_path)
into the SqlProjectRepository contract.

Scope:
  - Each protocol method (create, get_by_slug, list_for_user, touch, delete)
    has at least one positive case.
  - Atomic-create rollback is asserted against a forced git_store failure.
  - Integration: a real init_repo call produces a working .git directory and
    a 40-char SHA stored on the Project row.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy
from sqlmodel import SQLModel, Session, select

# Import side-effect: register User + Project tables in SQLModel.metadata
import modules.auth.models  # noqa: F401
import modules.data.projects.models  # noqa: F401

from modules.data.projects.models import Project
from modules.data.projects.repository import SqlProjectRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sqlite_engine(tmp_path: Path):
    """Per-test SQLite engine bound to a file under tmp_path.

    A file-backed SQLite (not :memory:) lets multiple Sessions opened by
    the repository see each other's commits — :memory: is per-connection.
    """
    db_url = f"sqlite:///{tmp_path}/repo_test.db"
    engine = sqlalchemy.create_engine(db_url)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def git_repos_dir(tmp_path: Path, monkeypatch):
    """Redirect git_store to a tmp_path subdirectory."""
    repos = tmp_path / "git_repos"
    repos.mkdir()
    monkeypatch.setenv("GIT_REPOS_DIR", str(repos))
    return repos


@pytest.fixture
def repo(sqlite_engine, git_repos_dir):
    """SqlProjectRepository wired to the per-test engine + git dir."""
    return SqlProjectRepository(engine=sqlite_engine)


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------


def test_create_inserts_project_row(repo, sqlite_engine, git_repos_dir):
    project = repo.create(
        user_id=1,
        name="My Project",
        slug="my-project",
        git_repo_path=str(git_repos_dir / "1"),
    )
    assert project.id is not None, "create() must return a row with id assigned"
    assert project.name == "My Project"
    assert project.slug == "my-project"
    assert project.user_id == 1
    # Verify it really hit the DB.
    with Session(sqlite_engine) as s:
        rows = s.exec(select(Project).where(Project.slug == "my-project")).all()
        assert len(rows) == 1, "Project row must be persisted after create()"


def test_create_initialises_git_repo(repo, git_repos_dir):
    project = repo.create(
        user_id=1,
        name="Git-init test",
        slug="git-init-test",
        git_repo_path=str(git_repos_dir / "x"),
    )
    # init_repo writes the per-project repo at GIT_REPOS_DIR/<project_id>/
    assert (git_repos_dir / str(project.id) / ".git").is_dir(), (
        "create() must call git_store.init_repo so a .git directory exists"
    )


def test_create_stores_initial_commit_sha(repo, git_repos_dir):
    project = repo.create(
        user_id=1,
        name="SHA test",
        slug="sha-test",
        git_repo_path=str(git_repos_dir / "y"),
    )
    assert project.latest_commit_sha is not None, (
        "create() must populate latest_commit_sha from init_repo"
    )
    assert len(project.latest_commit_sha) == 40, (
        f"latest_commit_sha must be a 40-char SHA, got {project.latest_commit_sha!r}"
    )


def test_create_rolls_back_db_on_git_failure(
    sqlite_engine, git_repos_dir, monkeypatch
):
    """If git_store.init_repo raises, the DB insert must be rolled back."""
    repo = SqlProjectRepository(engine=sqlite_engine)

    # Patch init_repo at the import site used by repository.py
    with patch(
        "modules.data.projects.repository.init_repo",
        side_effect=RuntimeError("simulated git failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated git failure"):
            repo.create(
                user_id=1,
                name="Doomed",
                slug="doomed",
                git_repo_path=str(git_repos_dir / "z"),
            )

    # No orphan row must remain.
    with Session(sqlite_engine) as s:
        rows = s.exec(select(Project).where(Project.slug == "doomed")).all()
        assert rows == [], (
            "DB insert must roll back when git init fails — found orphan rows: "
            f"{rows}"
        )


# ---------------------------------------------------------------------------
# get_by_slug()
# ---------------------------------------------------------------------------


def test_get_by_slug_returns_project(repo, git_repos_dir):
    repo.create(
        user_id=1, name="Findable", slug="findable",
        git_repo_path=str(git_repos_dir / "f"),
    )
    found = repo.get_by_slug("findable")
    assert found is not None, "get_by_slug must return the inserted project"
    assert found.slug == "findable"


def test_get_by_slug_returns_none_when_missing(repo):
    assert repo.get_by_slug("does-not-exist") is None, (
        "get_by_slug must return None for unknown slugs"
    )


# ---------------------------------------------------------------------------
# list_for_user()
# ---------------------------------------------------------------------------


def test_list_for_user_returns_only_owned_projects(repo, git_repos_dir):
    repo.create(
        user_id=1, name="A", slug="user-1-a",
        git_repo_path=str(git_repos_dir / "a"),
    )
    repo.create(
        user_id=1, name="B", slug="user-1-b",
        git_repo_path=str(git_repos_dir / "b"),
    )
    repo.create(
        user_id=2, name="C", slug="user-2-c",
        git_repo_path=str(git_repos_dir / "c"),
    )
    user1_slugs = {p.slug for p in repo.list_for_user(1)}
    assert user1_slugs == {"user-1-a", "user-1-b"}, (
        f"list_for_user(1) must return only user 1's rows; got {user1_slugs}"
    )


def test_list_for_user_empty_when_none_owned(repo):
    assert repo.list_for_user(99) == [], (
        "list_for_user must return [] when the user owns nothing"
    )


# ---------------------------------------------------------------------------
# touch()
# ---------------------------------------------------------------------------


def test_touch_updates_sha_and_file_count(repo, git_repos_dir):
    project = repo.create(
        user_id=1, name="Touchable", slug="touchable",
        git_repo_path=str(git_repos_dir / "t"),
    )
    new_sha = "0" * 40
    repo.touch(project.id, sha=new_sha, file_count=3)
    refreshed = repo.get_by_slug("touchable")
    assert refreshed.latest_commit_sha == new_sha
    assert refreshed.file_count == 3


def test_touch_advances_updated_at(repo, git_repos_dir):
    project = repo.create(
        user_id=1, name="Time", slug="time-test",
        git_repo_path=str(git_repos_dir / "tt"),
    )
    original_updated = project.updated_at
    repo.touch(project.id, sha="a" * 40, file_count=1)
    refreshed = repo.get_by_slug("time-test")
    assert refreshed.updated_at >= original_updated, (
        "touch() must advance updated_at"
    )


def test_touch_raises_for_unknown_project(repo):
    with pytest.raises(LookupError, match="touch"):
        repo.touch(project_id=9999, sha="b" * 40, file_count=0)


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


def test_delete_removes_project_row(repo, git_repos_dir):
    project = repo.create(
        user_id=1, name="ToDelete", slug="to-delete",
        git_repo_path=str(git_repos_dir / "d"),
    )
    repo.delete(project.id)
    assert repo.get_by_slug("to-delete") is None, (
        "delete() must remove the row from the DB"
    )


def test_delete_silent_for_unknown_project(repo):
    """Idempotent: deleting an absent row is a no-op, not an error."""
    repo.delete(project_id=9999)  # must not raise


# ---------------------------------------------------------------------------
# Integration / wiring sanity
# ---------------------------------------------------------------------------


def test_repository_does_not_import_git_store_service_directly():
    """Structural guard: repository.py must import git_store from the
    package root, never from .service."""
    from pathlib import Path
    repo_path = (
        Path(__file__).resolve().parents[1] / "repository.py"
    )
    text = repo_path.read_text(encoding="utf-8")
    assert "from modules.data.git_store.service" not in text, (
        "repository.py must import git_store via the package root, not .service"
    )
    assert "modules.data.git_store" in text, (
        "repository.py must import from modules.data.git_store"
    )


def test_repository_satisfies_protocol_shape():
    """SqlProjectRepository exposes all five protocol methods."""
    required = {"create", "get_by_slug", "list_for_user", "touch", "delete"}
    for method in required:
        assert hasattr(SqlProjectRepository, method), (
            f"SqlProjectRepository is missing protocol method: {method}"
        )


# ---------------------------------------------------------------------------
# create_anonymous()
# ---------------------------------------------------------------------------


def test_create_anonymous_sets_null_user_id(sqlite_engine, git_repos_dir):
    """create_anonymous() must store user_id=None on the Project row."""
    repo = SqlProjectRepository(engine=sqlite_engine)
    project = repo.create_anonymous(name="Anon Project", slug="anon-null-user")
    assert project.id is not None, "create_anonymous() must return a row with id assigned"
    assert project.user_id is None, (
        "create_anonymous() must set user_id=None; got %r" % project.user_id
    )


def test_create_anonymous_sets_anonymous_flag(sqlite_engine, git_repos_dir):
    """create_anonymous() must set anonymous=True on the Project row."""
    repo = SqlProjectRepository(engine=sqlite_engine)
    project = repo.create_anonymous(name="Anon Flag Test", slug="anon-flag-test")
    assert project.anonymous is True, (
        "create_anonymous() must set anonymous=True; got %r" % project.anonymous
    )


# ---------------------------------------------------------------------------
# list_anonymous_older_than()
# ---------------------------------------------------------------------------


def test_list_anonymous_older_than_returns_expired(sqlite_engine, git_repos_dir):
    """list_anonymous_older_than() returns anonymous projects whose created_at
    is before the cutoff datetime."""
    from datetime import datetime, timedelta

    repo = SqlProjectRepository(engine=sqlite_engine)
    project = repo.create_anonymous(name="Old Anon", slug="old-anon-project")

    # Back-date the row's created_at so it appears expired.
    from sqlmodel import Session
    with Session(sqlite_engine) as session:
        row = session.get(Project, project.id)
        row.created_at = datetime.utcnow() - timedelta(hours=72)
        session.add(row)
        session.commit()

    cutoff = datetime.utcnow() - timedelta(hours=48)
    results = repo.list_anonymous_older_than(cutoff)
    slugs = {p.slug for p in results}
    assert "old-anon-project" in slugs, (
        "list_anonymous_older_than() must return projects older than the cutoff"
    )


def test_list_anonymous_older_than_excludes_recent(sqlite_engine, git_repos_dir):
    """list_anonymous_older_than() must NOT return anonymous projects whose
    created_at is after the cutoff."""
    from datetime import datetime, timedelta

    repo = SqlProjectRepository(engine=sqlite_engine)
    repo.create_anonymous(name="Recent Anon", slug="recent-anon-project")

    # cutoff is 48 hours ago; the freshly-created row should be excluded.
    cutoff = datetime.utcnow() - timedelta(hours=48)
    results = repo.list_anonymous_older_than(cutoff)
    slugs = {p.slug for p in results}
    assert "recent-anon-project" not in slugs, (
        "list_anonymous_older_than() must not return projects newer than the cutoff"
    )


# ---------------------------------------------------------------------------
# claim()
# ---------------------------------------------------------------------------


def test_claim_anonymous_project_succeeds(sqlite_engine, git_repos_dir):
    """claim() sets user_id and clears the anonymous flag on a matching row."""
    repo = SqlProjectRepository(engine=sqlite_engine)
    repo.create_anonymous(name="Claimable", slug="claim-me")

    result = repo.claim("claim-me", user_id=7)

    assert result is not None, "claim() must return the Project on success"
    assert result.user_id == 7, (
        f"claim() must set user_id; got {result.user_id!r}"
    )
    assert result.anonymous is False, (
        "claim() must clear the anonymous flag"
    )


def test_claim_persists_ownership_in_db(sqlite_engine, git_repos_dir):
    """A subsequent get_by_slug must reflect the claimed user_id."""
    repo = SqlProjectRepository(engine=sqlite_engine)
    repo.create_anonymous(name="Persist Test", slug="claim-persist")

    repo.claim("claim-persist", user_id=5)

    refreshed = repo.get_by_slug("claim-persist")
    assert refreshed is not None
    assert refreshed.user_id == 5, (
        "claim() must commit the user_id change to the database"
    )
    assert refreshed.anonymous is False


def test_claim_already_owned_returns_none(sqlite_engine, git_repos_dir):
    """claim() returns None when the project already has an owner."""
    repo = SqlProjectRepository(engine=sqlite_engine)
    repo.create(
        user_id=1,
        name="Already Owned",
        slug="already-owned",
        git_repo_path=str((git_repos_dir / "ao")),
    )

    result = repo.claim("already-owned", user_id=2)

    assert result is None, (
        "claim() must return None for a project that already has user_id set"
    )


def test_claim_nonexistent_slug_returns_none(sqlite_engine, git_repos_dir):
    """claim() returns None when no project matches the given slug."""
    repo = SqlProjectRepository(engine=sqlite_engine)

    result = repo.claim("does-not-exist", user_id=1)

    assert result is None, (
        "claim() must return None when no project exists for the slug"
    )


def test_claim_idempotent_second_claim_returns_none(sqlite_engine, git_repos_dir):
    """Calling claim() twice on the same slug returns None the second time."""
    repo = SqlProjectRepository(engine=sqlite_engine)
    repo.create_anonymous(name="Idempotent", slug="claim-twice")

    first = repo.claim("claim-twice", user_id=3)
    second = repo.claim("claim-twice", user_id=4)

    assert first is not None, "first claim must succeed"
    assert second is None, "second claim must return None (already owned)"
