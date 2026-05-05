"""Project SQLModel entity + ProjectRepository Protocol.

Coexists alongside the active filesystem implementation in modules/projects/.
Task 3 introduces the SQL implementation that consumes these models.
"""
from datetime import datetime
from typing import List, Optional, Protocol

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str
    slug: str = Field(unique=True, index=True)
    git_repo_path: str
    latest_commit_sha: Optional[str] = Field(default=None)
    file_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectRepository(Protocol):
    def create(
        self, user_id: int, name: str, slug: str, git_repo_path: str
    ) -> Project: ...

    def get_by_slug(self, slug: str) -> Optional[Project]: ...

    def list_for_user(self, user_id: int) -> List[Project]: ...

    def touch(self, project_id: int, sha: str, file_count: int) -> None: ...

    def delete(self, project_id: int) -> None: ...
