"""Tests for modules/ai/services/anonymous_cleanup.py.

Covers:
- _delete_project_dir: normal removal, path-traversal rejection, missing dir
- _run_cleanup: expired projects are deleted, recent projects are skipped
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import modules.ai.services.anonymous_cleanup as cleanup


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_projects_dir(tmp_path, monkeypatch):
    """Redirect PROJECTS_DIR to a per-test tmp directory.

    Patches the reference inside anonymous_cleanup's already-imported
    namespace so all PROJECTS_DIR usage within the module sees the
    temporary path.
    """
    projects = tmp_path / "projects"
    projects.mkdir()
    import config
    monkeypatch.setattr(config, "PROJECTS_DIR", projects)
    monkeypatch.setattr(
        "modules.ai.services.anonymous_cleanup.PROJECTS_DIR", projects
    )
    return projects


# ---------------------------------------------------------------------------
# _delete_project_dir
# ---------------------------------------------------------------------------


def test_delete_project_dir_removes_directory(isolated_projects_dir):
    """_delete_project_dir must call shutil.rmtree and remove the directory."""
    slug = "my-project-slug"
    project_dir = isolated_projects_dir / slug
    project_dir.mkdir()
    (project_dir / "braindump.md").write_text("some content", encoding="utf-8")

    assert project_dir.exists(), "pre-condition: directory must exist before delete"
    cleanup._delete_project_dir(slug)
    assert not project_dir.exists(), (
        "_delete_project_dir must remove the project directory"
    )


def test_delete_project_dir_rejects_path_traversal(isolated_projects_dir):
    """Slugs containing '..' must be silently rejected — no filesystem access."""
    with patch("shutil.rmtree") as mock_rmtree:
        cleanup._delete_project_dir("../secret-slug")
        mock_rmtree.assert_not_called()

    # Also verify a slug with embedded traversal is rejected.
    with patch("shutil.rmtree") as mock_rmtree:
        cleanup._delete_project_dir("a/../../etc/passwd")
        mock_rmtree.assert_not_called()


def test_delete_project_dir_handles_missing_dir(isolated_projects_dir):
    """_delete_project_dir must not raise when the directory does not exist."""
    slug = "non-existent-project"
    assert not (isolated_projects_dir / slug).exists(), (
        "pre-condition: directory must not exist"
    )
    # Must complete without raising.
    cleanup._delete_project_dir(slug)


# ---------------------------------------------------------------------------
# _run_cleanup
# ---------------------------------------------------------------------------


def test_run_cleanup_deletes_expired_projects(isolated_projects_dir):
    """_run_cleanup must delete the directory and DB row for each expired project."""
    expired_slug = "old-project-abc"
    project_dir = isolated_projects_dir / expired_slug
    project_dir.mkdir()

    expired_project = MagicMock()
    expired_project.id = 42
    expired_project.slug = expired_slug

    # SqlProjectRepository is imported inside _run_cleanup, so we patch it at
    # the repository module level — the location it is actually imported from.
    with (
        patch(
            "modules.data.projects.repository.SqlProjectRepository"
        ) as MockRepo,
        patch(
            "modules.ai.services.anonymous_cleanup._delete_project_dir"
        ) as mock_delete_dir,
    ):
        repo_instance = MockRepo.return_value
        repo_instance.list_anonymous_older_than.return_value = [expired_project]

        cleanup._run_cleanup(ttl_hours=48)

        # The filesystem delete helper must have been called for the expired slug.
        mock_delete_dir.assert_called_once_with(expired_slug)
        # The DB row must have been removed.
        repo_instance.delete_by_id.assert_called_once_with(42)


def test_run_cleanup_skips_recent_projects(isolated_projects_dir):
    """_run_cleanup must NOT delete projects that are within the TTL window."""
    with (
        patch(
            "modules.data.projects.repository.SqlProjectRepository"
        ) as MockRepo,
        patch(
            "modules.ai.services.anonymous_cleanup._delete_project_dir"
        ) as mock_delete_dir,
    ):
        repo_instance = MockRepo.return_value
        # Repository returns empty list — no projects exceed the cutoff.
        repo_instance.list_anonymous_older_than.return_value = []

        cleanup._run_cleanup(ttl_hours=48)

        mock_delete_dir.assert_not_called()
        repo_instance.delete_by_id.assert_not_called()
