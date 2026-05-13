"""Tests for the @require_project_ownership decorator.

These tests exercise the four outcomes the decorator can produce:
  - 401  when g.current_user is None (no bearer token)
  - 404  when the project slug resolves to nothing
  - 403  when the authenticated user does not own the project
  - 200  when the authenticated user owns the project

A minimal Flask test app is constructed here with a single protected
route so that the decorator is exercised in isolation, independent of
the full projects blueprint. This avoids coupling the decorator tests
to filesystem behaviour or git_store internals.

Auth is driven by the suite-level autouse _auth_bypass fixture in
api/conftest.py, which patches modules.auth.decorators.verify_token and
modules.auth.decorators._load_user and auto-injects "Authorization:
Bearer test-token" on every client.open() call.  Tests that must
simulate "no authenticated user" pass headers={"Authorization": ""} to
opt out of the default injection so that @require_auth returns 401.

Do NOT set SKIP_AUTH=1 in these tests: that env flag sets
g.current_user = None in a way that skirts the real JWT flow, making
ownership assertions meaningless.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import modules.auth.decorators as _decorators
from modules.auth.models import User


# ---------------------------------------------------------------------------
# Stub helpers
#
# These are defined as a class with static methods to avoid the pytest
# collection glob python_functions = ["*_*"] incorrectly collecting module-level
# functions whose names contain underscores as test cases.
# ---------------------------------------------------------------------------

class Stubs:
    """Factory methods for in-test stubs; not collected by pytest."""

    @staticmethod
    def project(user_id: int, slug: str = "my-project"):
        """Return a minimal Project-like namespace sufficient for the decorator."""
        return SimpleNamespace(id=99, user_id=user_id, slug=slug, file_count=0)

    @staticmethod
    def load_user_fn(uid: int):
        """Return a _load_user replacement that resolves to the given user id."""
        def load(_uid: int) -> User:
            return User(
                id=uid,
                auth_user_id=f"user-{uid}",
                email=f"user{uid}@example.com",
                plan="pro",
            )
        return load


# ---------------------------------------------------------------------------
# Test app fixture
#
# We create a stripped-down Flask app that mounts a single route decorated
# with @require_auth + @require_project_ownership.  This isolates the
# decorator from all filesystem / git_store concerns.
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():
    """Minimal Flask app with one ownership-protected route."""
    from flask import Flask, jsonify
    from modules.auth.decorators import require_auth
    from modules.data.projects.ownership import require_project_ownership

    application = Flask(__name__)
    application.config["TESTING"] = True

    @application.get("/projects/<id>")
    @require_auth
    @require_project_ownership
    def protected(id: str):
        return jsonify({"ok": True, "project_id": id}), 200

    return application


@pytest.fixture()
def project_repo(app):
    """Attach a MagicMock project_repository to the test app."""
    stub = MagicMock()
    app.project_repository = stub
    return stub


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestOwnershipDecorator401:
    """401 is returned when there is no authenticated user."""

    def test_no_bearer_token_returns_401(self, client, project_repo):
        # Passing an empty Authorization header opts out of the autouse
        # _auth_bypass injection so @require_auth never sets g.current_user.
        r = client.get("/projects/my-project", headers={"Authorization": ""})
        assert r.status_code == 401
        body = json.loads(r.data)
        assert "error" in body


class TestOwnershipDecorator404:
    """404 is returned when the slug does not map to any project row."""

    def test_unknown_slug_returns_404(self, client, project_repo):
        project_repo.get_by_slug.return_value = None
        r = client.get("/projects/no-such-project")
        assert r.status_code == 404
        body = json.loads(r.data)
        assert body.get("error") == "Project not found"

    def test_get_by_slug_called_with_slug(self, client, project_repo):
        project_repo.get_by_slug.return_value = None
        client.get("/projects/target-slug")
        project_repo.get_by_slug.assert_called_once_with("target-slug")


class TestOwnershipDecorator403:
    """403 is returned when an authenticated user requests another user's project."""

    def test_wrong_owner_returns_403(self, client, project_repo):
        # The autouse _auth_bypass sets _FAKE_USER_ID=1.
        # The project belongs to user 2 — mismatch should produce 403.
        project_repo.get_by_slug.return_value = Stubs.project(user_id=2)
        r = client.get("/projects/my-project")
        assert r.status_code == 403
        body = json.loads(r.data)
        assert body.get("error") == "access denied"

    def test_different_authenticated_user_returns_403(
        self, client, project_repo, monkeypatch
    ):
        # Simulate a different authenticated user (id=5) whose id does not
        # match the project owner (id=99).
        monkeypatch.setattr(_decorators, "_load_user", Stubs.load_user_fn(5))
        project_repo.get_by_slug.return_value = Stubs.project(user_id=99)
        r = client.get("/projects/my-project")
        assert r.status_code == 403


class TestOwnershipDecorator200:
    """200 is returned when the authenticated user owns the requested project."""

    def test_owner_gets_200(self, client, project_repo):
        # _FAKE_USER_ID = 1, project.user_id = 1 → ownership passes.
        project_repo.get_by_slug.return_value = Stubs.project(user_id=1)
        r = client.get("/projects/my-project")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body.get("ok") is True

    def test_project_attached_to_g(self, client, project_repo, app):
        """g.project must be set on success so the handler can skip re-fetch."""
        stub_project = Stubs.project(user_id=1, slug="my-project")
        project_repo.get_by_slug.return_value = stub_project

        captured = {}

        @app.after_request
        def capture(response):
            from flask import g
            captured["project"] = g.get("project")
            return response

        client.get("/projects/my-project")
        assert captured.get("project") is stub_project, (
            "g.project must be the exact Project row returned by the repository"
        )


class TestOwnershipDecoratorMissingRepo:
    """404 is returned if project_repository is not configured on the app."""

    def test_missing_repository_returns_404(self, client, app):
        # Remove the repository attribute entirely (simulates unconfigured state).
        if hasattr(app, "project_repository"):
            del app.project_repository

        r = client.get("/projects/my-project")
        assert r.status_code == 404
        body = json.loads(r.data)
        assert body.get("error") == "Project not found"
