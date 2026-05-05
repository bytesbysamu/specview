"""HTTP-level tests for the file-history endpoints (Pers-T4).

Three new routes on the projects blueprint:
  GET  /api/projects/<id>/files/<filename>/history
  GET  /api/projects/<id>/files/<filename>/diff
  POST /api/projects/<id>/files/<filename>/revert

The handlers resolve the project via `current_app.project_repository`
(Pers-T3 seam) and delegate every git op to `modules.data.git_store`
(Pers-T2 adapter wall). These tests stub both to avoid standing up a real
DB or a real git repository — the integration concerns of those two
modules are owned by their own test suites.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from create_app import create_app as createApp


# ---------------------------------------------------------------------------
# Local app/client fixtures
#
# The global app/client live in api/tests/conftest.py — that conftest is
# not in our parent chain (we live under api/modules/...), so we declare
# our own here rather than widening conftest scope.
#
# `create_app` is imported under a camelCase alias because pytest's
# `python_functions = ["test_*", "*_*"]` glob would otherwise collect
# the imported snake_case function itself as a test case (matches the
# existing pattern in modules/ai/routes/tests/test_spec_gen_routes.py).
# ---------------------------------------------------------------------------
@pytest.fixture()
def app():
    return createApp({"TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------
class _StubProject:
    """Mimics modules.data.projects.models.Project enough for the routes."""

    id = 42
    slug = "my-project"
    file_count = 3


_HISTORY_ROW_UNIX = {
    "sha": "deadbeef" * 5,  # 40 chars
    "message": "Update brain-dump.md",
    "timestamp": 1714128000,  # 2024-04-26T12:00:00 UTC, unix int (matches
                              # what git_store.get_history actually returns)
}


# ---------------------------------------------------------------------------
# Fixtures (local — do not widen the global conftest)
# ---------------------------------------------------------------------------
@pytest.fixture()
def project_repo_stub(app):
    """Override app.project_repository with a MagicMock returning _StubProject."""
    stub = MagicMock()
    stub.get_by_slug.return_value = _StubProject()
    app.project_repository = stub
    return stub


@pytest.fixture()
def git_patch():
    """Patch the git_store module imported into modules.data.projects.routes."""
    with patch("modules.data.projects.routes.git_store") as mock_gs:
        yield mock_gs


# ---------------------------------------------------------------------------
# GET /history
# ---------------------------------------------------------------------------
class TestGetFileHistory:
    def test_returns_history_list(self, client, project_repo_stub, git_patch):
        git_patch.get_history.return_value = [_HISTORY_ROW_UNIX]
        r = client.get(
            "/api/projects/my-project/files/brain-dump.md/history"
        )
        assert r.status_code == 200, r.data
        body = json.loads(r.data)
        assert "history" in body
        assert len(body["history"]) == 1
        entry = body["history"][0]
        assert entry["sha"] == _HISTORY_ROW_UNIX["sha"]
        assert entry["message"] == "Update brain-dump.md"
        assert entry["author"], "author must be populated (defaulted from git_store author signature)"
        assert "timestamp" in entry, "timestamp must be present"
        # Timestamp must be ISO-8601, not a unix int — schema says date-time.
        assert "T" in entry["timestamp"], (
            f"timestamp must be ISO-8601, got {entry['timestamp']!r}"
        )

    def test_default_limit_is_20(self, client, project_repo_stub, git_patch):
        git_patch.get_history.return_value = []
        client.get("/api/projects/my-project/files/brain-dump.md/history")
        git_patch.get_history.assert_called_once_with("42", "brain-dump.md", 20)

    def test_custom_limit_forwarded(self, client, project_repo_stub, git_patch):
        git_patch.get_history.return_value = []
        client.get(
            "/api/projects/my-project/files/brain-dump.md/history?limit=5"
        )
        git_patch.get_history.assert_called_once_with("42", "brain-dump.md", 5)

    def test_404_unknown_project(self, client, project_repo_stub, git_patch):
        project_repo_stub.get_by_slug.return_value = None
        r = client.get(
            "/api/projects/no-such/files/brain-dump.md/history"
        )
        assert r.status_code == 404
        assert "error" in json.loads(r.data)


# ---------------------------------------------------------------------------
# GET /diff
# ---------------------------------------------------------------------------
class TestGetFileDiff:
    def test_returns_diff_string(self, client, project_repo_stub, git_patch):
        git_patch.get_diff.return_value = (
            "--- a/brain-dump.md\n"
            "+++ b/brain-dump.md\n"
            "@@ -1 +1 @@\n"
            "-old\n+new\n"
        )
        r = client.get(
            "/api/projects/my-project/files/brain-dump.md/diff"
            "?from_sha=aaa111&to_sha=bbb222"
        )
        assert r.status_code == 200, r.data
        body = json.loads(r.data)
        assert "diff" in body
        assert "@@" in body["diff"]

    def test_forwards_shas_to_git_store(
        self, client, project_repo_stub, git_patch
    ):
        git_patch.get_diff.return_value = ""
        client.get(
            "/api/projects/my-project/files/brain-dump.md/diff"
            "?from_sha=aaa111&to_sha=bbb222"
        )
        git_patch.get_diff.assert_called_once_with(
            "42", "brain-dump.md", "aaa111", "bbb222"
        )

    def test_400_missing_from_sha(self, client, project_repo_stub, git_patch):
        r = client.get(
            "/api/projects/my-project/files/brain-dump.md/diff?to_sha=bbb222"
        )
        assert r.status_code == 400
        assert "error" in json.loads(r.data)

    def test_400_missing_to_sha(self, client, project_repo_stub, git_patch):
        r = client.get(
            "/api/projects/my-project/files/brain-dump.md/diff?from_sha=aaa111"
        )
        assert r.status_code == 400
        assert "error" in json.loads(r.data)

    def test_404_unknown_project(self, client, project_repo_stub, git_patch):
        project_repo_stub.get_by_slug.return_value = None
        r = client.get(
            "/api/projects/no-such/files/brain-dump.md/diff"
            "?from_sha=aaa111&to_sha=bbb222"
        )
        assert r.status_code == 404
        assert "error" in json.loads(r.data)


# ---------------------------------------------------------------------------
# POST /revert
# ---------------------------------------------------------------------------
class TestRevertFile:
    def test_returns_new_sha_and_message(
        self, client, project_repo_stub, git_patch
    ):
        git_patch.revert_file.return_value = "newsha9999" + "0" * 30
        r = client.post(
            "/api/projects/my-project/files/brain-dump.md/revert",
            json={"to_sha": "deadbeef" * 5},
        )
        assert r.status_code == 200, r.data
        body = json.loads(r.data)
        assert body["sha"].startswith("newsha9999")
        assert "message" in body
        assert "revert" in body["message"].lower()

    def test_forwards_args_to_git_store(
        self, client, project_repo_stub, git_patch
    ):
        git_patch.revert_file.return_value = "x" * 40
        client.post(
            "/api/projects/my-project/files/brain-dump.md/revert",
            json={"to_sha": "deadbeef" * 5},
        )
        git_patch.revert_file.assert_called_once_with(
            "42", "brain-dump.md", "deadbeef" * 5
        )

    def test_calls_repository_touch_after_revert(
        self, client, project_repo_stub, git_patch
    ):
        """latest_commit_sha must be advanced after a successful revert."""
        new_sha = "f" * 40
        git_patch.revert_file.return_value = new_sha
        client.post(
            "/api/projects/my-project/files/brain-dump.md/revert",
            json={"to_sha": "deadbeef" * 5},
        )
        project_repo_stub.touch.assert_called_once_with(42, new_sha, 3)

    def test_404_unknown_project(self, client, project_repo_stub, git_patch):
        project_repo_stub.get_by_slug.return_value = None
        r = client.post(
            "/api/projects/no-such/files/brain-dump.md/revert",
            json={"to_sha": "deadbeef" * 5},
        )
        assert r.status_code == 404
        assert "error" in json.loads(r.data)

    def test_400_missing_to_sha(self, client, project_repo_stub, git_patch):
        r = client.post(
            "/api/projects/my-project/files/brain-dump.md/revert",
            json={},
        )
        assert r.status_code == 400
        assert "error" in json.loads(r.data)


# ---------------------------------------------------------------------------
# Structural: route module imports git_store via the public package only
# ---------------------------------------------------------------------------
class TestGitStoreAdapterBoundary:
    def test_routes_import_git_store_via_package_root(self):
        """routes.py must consume the git layer via modules.data.git_store
        (the public adapter wall), never via .service or by reaching for
        the underlying library directly. The library-level guard is owned
        by modules/data/git_store/tests/test_pygit2_isolation.py — this
        test focuses on the seam owned by Pers-T4."""
        routes_path = Path(__file__).resolve().parents[1] / "routes.py"
        text = routes_path.read_text(encoding="utf-8")
        assert "modules.data.git_store" in text, (
            "routes.py must import git_store from modules.data.git_store"
        )
        assert "modules.data.git_store.service" not in text, (
            "routes.py must use the package-root import, not .service"
        )
