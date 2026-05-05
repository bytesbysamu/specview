"""Tests for the Project SQLModel entity + ProjectRepository Protocol."""
from datetime import datetime

from modules.data.projects.models import Project, ProjectRepository


def test_project_defaults():
    project = Project(
        user_id=1,
        name="My Project",
        slug="my-project",
        git_repo_path="/data/projects/1",
    )
    assert project.id is None, "Project.id must be None before insertion"
    assert project.file_count == 0, "Project.file_count must default to 0"
    assert project.latest_commit_sha is None, \
        "Project.latest_commit_sha must default to None"


def test_project_timestamps_set_on_instantiation():
    project = Project(
        user_id=1,
        name="Timestamp Test",
        slug="ts-test",
        git_repo_path="/data/projects/2",
    )
    assert isinstance(project.created_at, datetime), \
        "Project.created_at must be a datetime"
    assert isinstance(project.updated_at, datetime), \
        "Project.updated_at must be a datetime"


def test_project_table_registered_in_sqlmodel_metadata():
    from sqlmodel import SQLModel
    tables = SQLModel.metadata.tables
    assert "project" in tables, \
        f"'project' table must be in SQLModel.metadata; found: {list(tables)}"


def test_project_slug_has_index():
    from sqlmodel import SQLModel
    table = SQLModel.metadata.tables["project"]
    index_cols = {
        col.name
        for idx in table.indexes
        for col in idx.columns
    }
    assert "slug" in index_cols, \
        "Project.slug must be covered by a database index"


def test_project_repository_protocol_has_required_methods():
    required = {"create", "get_by_slug", "list_for_user", "touch", "delete"}
    for method_name in required:
        assert hasattr(ProjectRepository, method_name), \
            f"ProjectRepository Protocol is missing method: {method_name}"


def test_stub_satisfies_project_repository_protocol():
    class StubRepo:
        def create(self, user_id, name, slug, git_repo_path):
            return Project(
                user_id=user_id, name=name, slug=slug, git_repo_path=git_repo_path
            )

        def get_by_slug(self, slug):
            return None

        def list_for_user(self, user_id):
            return []

        def touch(self, project_id, sha, file_count):
            pass

        def delete(self, project_id):
            pass

    stub = StubRepo()
    for method_name in ("create", "get_by_slug", "list_for_user", "touch", "delete"):
        assert callable(getattr(stub, method_name)), \
            f"StubRepo.{method_name} must be callable"


def test_metadata_create_all_emits_user_and_project_tables(tmp_path):
    """Smoke test: SQLModel metadata produces the expected tables in SQLite."""
    from sqlalchemy import create_engine, inspect
    from sqlmodel import SQLModel
    import modules.auth.models  # noqa: F401 — registers User in metadata
    import modules.data.projects.models  # noqa: F401 — registers Project in metadata

    engine = create_engine(f"sqlite:///{tmp_path}/schema_smoke.db")
    SQLModel.metadata.create_all(engine)
    found = set(inspect(engine).get_table_names())
    assert "user" in found, \
        f"'user' table missing after create_all; found: {found}"
    assert "project" in found, \
        f"'project' table missing after create_all; found: {found}"
