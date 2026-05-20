"""SqlProjectRepository — concrete SQL implementation of ProjectRepository.

Wires the DB layer (modules.data.db) and the git_store layer
(modules.data.git_store) into one storage adapter. The Project SQL row
records ownership and the latest commit SHA; the per-project git
repository is the canonical store for markdown content.

Atomic-create contract
----------------------
`create()` performs the DB insert and `git_store.init_repo()` inside one
try/except. A git failure rolls back the DB insert so the system is never
left with an orphaned Project row pointing at a missing git repo.

Import discipline
-----------------
This module imports git_store ONLY from the package root
(`modules.data.git_store`). Direct imports of `.service` are forbidden by
the structural guard in `modules.data.git_store.tests.test_pygit2_isolation`.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from modules.data.db.session import get_session
from modules.data.git_store import init_repo

from .models import Project


class SqlProjectRepository:
    """SQL-backed ProjectRepository.

    Constructed without arguments uses the module-level engine via
    `get_session()`. An explicit `engine` argument is supported for test
    fixtures that bind to an in-memory SQLite without touching the
    process-wide singleton.
    """

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def _session(self) -> Session:
        """Return a fresh Session bound to either the injected engine or
        the module-level engine via get_session()."""
        if self._engine is not None:
            return Session(self._engine)
        # get_session is a @contextmanager; calling it returns a context
        # manager whose __enter__ yields the Session. We return the
        # context manager directly so callers use `with repo._session()`.
        return get_session()

    # ------------------------------------------------------------------
    # Public protocol surface
    # ------------------------------------------------------------------

    def create(
        self, user_id: int, name: str, slug: str, git_repo_path: str
    ) -> Project:
        """Insert a Project row and initialise its git repo atomically.

        On git_store.init_repo failure, the DB insert is rolled back so no
        orphaned row survives. The Project entity returned has its primary
        key populated and `latest_commit_sha` set to the initial commit
        SHA returned by init_repo.
        """
        now = datetime.utcnow()
        project = Project(
            user_id=user_id,
            name=name,
            slug=slug,
            git_repo_path=git_repo_path,
            latest_commit_sha=None,
            file_count=0,
            created_at=now,
            updated_at=now,
        )
        with self._session() as session:
            session.add(project)
            try:
                session.flush()  # assign project.id without committing
                # git seam — only public package import allowed.
                initial_sha = init_repo(str(project.id))
                project.latest_commit_sha = initial_sha
                session.add(project)
                session.commit()
                session.refresh(project)
                return project
            except Exception:
                session.rollback()
                raise

    def get_by_slug(self, slug: str) -> Optional[Project]:
        with self._session() as session:
            stmt = select(Project).where(Project.slug == slug)
            return session.exec(stmt).first()

    def list_for_user(self, user_id: int) -> List[Project]:
        with self._session() as session:
            stmt = (
                select(Project)
                .where(Project.user_id == user_id)
                .order_by(Project.created_at.desc())
            )
            return list(session.exec(stmt).all())

    def touch(self, project_id: int, sha: str, file_count: int) -> None:
        """Advance latest_commit_sha + file_count after a successful git
        write. Called from the routes layer (Pers-T4) every time a file
        is written, deleted, or reverted."""
        with self._session() as session:
            project = session.get(Project, project_id)
            if project is None:
                raise LookupError(
                    f"touch(): project_id={project_id} not found"
                )
            project.latest_commit_sha = sha
            project.file_count = file_count
            project.updated_at = datetime.utcnow()
            session.add(project)
            session.commit()

    def create_anonymous(self, name: str, slug: str) -> Project:
        """Insert an anonymous (no user) Project row.

        Does not initialise a git repo — the filesystem directory is the
        source of truth for anonymous projects. Logs and suppresses any DB
        error so callers can continue without the row.
        """
        now = datetime.utcnow()
        project = Project(
            user_id=None,
            name=name,
            slug=slug,
            git_repo_path="",
            latest_commit_sha=None,
            file_count=0,
            anonymous=True,
            created_at=now,
            updated_at=now,
        )
        with self._session() as session:
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def delete(self, project_id: int) -> None:
        """Hard-delete the DB row.

        Note: git_store.delete_repo does not yet exist (Task-2 follow-up);
        the on-disk repo is intentionally orphaned here rather than
        invented. The route layer logs a TODO when this is exposed.
        """
        with self._session() as session:
            project = session.get(Project, project_id)
            if project is None:
                return
            session.delete(project)
            session.commit()

    def list_anonymous_older_than(self, cutoff: datetime) -> List[Project]:
        """Return all anonymous projects whose created_at is before cutoff."""
        with self._session() as session:
            stmt = (
                select(Project)
                .where(Project.anonymous == True)  # noqa: E712
                .where(Project.created_at < cutoff)
            )
            return list(session.exec(stmt).all())

    def delete_by_id(self, project_id: int) -> None:
        """Hard-delete the DB row by primary key.

        Silently does nothing if the row is not found — safe to call when
        the row may have already been removed.
        """
        with self._session() as session:
            project = session.get(Project, project_id)
            if project is None:
                return
            session.delete(project)
            session.commit()
