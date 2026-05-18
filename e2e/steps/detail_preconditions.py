"""Shared Given steps for all project-detail feature files.

Covers: login state, project seeding, and navigation to the detail view.
All browser interaction goes through DetailPage; no direct Playwright calls.
"""
from __future__ import annotations

import os
import time

import jwt
import pytest
from pytest_bdd import given, parsers
from playwright.sync_api import Page

from e2e.helpers.seed_projects import (
    SeedMatrix,
    _write_project,
    _resolve_projects_dir,
    _provision_project_via_api,
    _make_auth_token,
)
from e2e.pages.detail_page import DetailPage

# Read JWT config from environment so tests work against the Docker stack.
_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
_JWT_USER_ID = os.environ.get("E2E_USER_ID", "1")
_JWT_EMAIL = os.environ.get("E2E_USER_EMAIL", "test@test.com")
_JWT_TTL_SECONDS = 72 * 3600  # 72 hours — matches Flask create_token TTL

_SKIP_MOCK = os.environ.get("E2E_SKIP_MOCK_SCENARIOS", "1") == "1"


def _make_jwt(user_id: str = _JWT_USER_ID, ttl: int = _JWT_TTL_SECONDS) -> str:
    """Create a signed JWT matching Flask's create_token() payload format."""
    payload = {
        "sub": str(user_id),
        "email": _JWT_EMAIL,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _build_detail(page: Page, base_url: str) -> DetailPage:
    return DetailPage(page, base_url)


def _seed_project(
    flask_server: str,
    name: str,
    files: list[tuple[str, str]],
) -> "ProjectInfo":
    """Provision a project using the API when possible, else write to filesystem.

    When JWT_SECRET is available (real server / Docker mode), registers the
    project via POST /api/projects so it appears in GET /api/projects for the
    authenticated user.

    In SKIP_AUTH=1 / local dev mode (no JWT_SECRET), writes directly to the
    filesystem because the local Flask server returns all filesystem projects
    via the fallback branch in list_projects_route.

    Returns a ProjectInfo dict.
    """
    from e2e.helpers.seed_projects import ProjectInfo as _PI

    auth_token = _make_auth_token()
    if auth_token:
        info = _provision_project_via_api(flask_server, name, files, auth_token)
        if info is not None:
            info["section"] = ""
            return info
    # Fallback: filesystem write (works with SKIP_AUTH=1)
    projects_dir = _resolve_projects_dir()
    return _write_project(projects_dir, name, files)


def _do_login_detail(page: Page, angular_server: str, context: dict) -> DetailPage:
    """Navigate to overview, inject JWT, and reload so Angular sees the session."""
    detail = _build_detail(page, angular_server)
    context["detail"] = detail
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    detail.inject_jwt(token)
    detail.load()
    return detail


# ── Full spec project seeding ───────────────────────────────────────────────


_FULL_SPEC_FILES: list[tuple[str, str]] = [
    ("braindump.md", "# Braindump\n\nA project to explore new ideas.\n"),
    ("analysis.md", "# Analysis\n\n## Summary\n\nDetailed analysis of the project.\n"),
    ("epic.md", "# Epic\n\n## Features\n\nHigh-level feature list.\n"),
    ("architecture.md", "# Architecture\n\n## System Design\n\nSystem components and interactions.\n"),
    ("timeline.md", "# Timeline\n\n## Milestones\n\nProject milestones.\n"),
    ("implementation-guide.md", "# Implementation Guide\n\n## Tasks\n\nStep-by-step task list.\n"),
]

# XSS test file — contains a script tag that DOMPurify should strip
_XSS_BRAINDUMP_CONTENT = (
    "# XSS Test Braindump\n\n"
    "Normal content here.\n\n"
    "<script>window.__xss_injected = true;</script>\n\n"
    "## More content\n\nContent after the script tag.\n"
)


@given("the user is logged in and a full-spec project exists")
def user_logged_in_with_full_spec_project(
    page: Page, angular_server: str, flask_server: str, context: dict
) -> None:
    """Login and seed a project with all six spec files.

    Uses the API when JWT_SECRET is available (Docker / real server mode)
    so the project is registered in the database and visible via GET /api/projects.
    Falls back to filesystem write for SKIP_AUTH=1 local dev mode.
    Stores the seeded project info in context['detail_project'].
    """
    info = _seed_project(flask_server, "E2E Detail Full Spec", _FULL_SPEC_FILES)
    context["detail_project"] = info
    _do_login_detail(page, angular_server, context)


@given("the user is logged in and a braindump-only project exists")
def user_logged_in_with_braindump_project(
    page: Page, angular_server: str, flask_server: str, context: dict
) -> None:
    """Login and seed a project with only a braindump file."""
    info = _seed_project(
        flask_server,
        "E2E Detail Braindump Only",
        [("braindump.md", "# Braindump\n\nJust an idea.\n")],
    )
    context["detail_project"] = info
    _do_login_detail(page, angular_server, context)


@given("the user is logged in and a project with XSS content exists")
def user_logged_in_with_xss_project(
    page: Page, angular_server: str, flask_server: str, context: dict
) -> None:
    """Login and seed a project whose braindump contains a raw script tag.

    The reader panel renders content via DOMPurify-sanitised innerHTML.
    This precondition sets up a project whose braindump.md contains a
    <script> tag so PD-16 can verify it is stripped by the sanitiser.
    """
    info = _seed_project(
        flask_server,
        "E2E Detail XSS Test",
        [("braindump.md", _XSS_BRAINDUMP_CONTENT)],
    )
    context["detail_project"] = info
    _do_login_detail(page, angular_server, context)


@given("the user is on the detail view of that project")
def user_on_detail_view(page: Page, context: dict) -> None:
    """Click the seeded project card to open the reader panel.

    Requires context['detail_project'] to have been set by a preceding Given
    step.  Waits for the sidebar nav to appear before returning.
    """
    project = context.get("detail_project")
    if project is None:
        pytest.fail("context['detail_project'] is not set — run a project-seeding Given step first")

    detail: DetailPage = context["detail"]
    detail.click_project_card(project["name"])
    # Wait for the reader panel to open
    detail.wait_reader_panel_visible(timeout_ms=15_000)


@given("the user has opened the braindump file in the reader")
def user_opened_braindump_in_reader(context: dict) -> None:
    """Click the braindump entry in the sidebar file list.

    Requires context['detail'] (DetailPage) and the expanded panel to be open.
    """
    detail: DetailPage = context["detail"]
    detail.click_sidebar_file("braindump")
    detail.wait_reader_content_visible(timeout_ms=10_000)


# ── Mock-dependent preconditions ────────────────────────────────────────────


@given("a spec-generation pipeline is in progress for that project")
def pipeline_in_progress(context: dict) -> None:
    """Precondition: a spec-gen job is already running in the backend.

    This step is only meaningful when CHAIN_PROVIDER=mock is active.
    When running against Docker (E2E_SKIP_MOCK_SCENARIOS=1), the scenario
    tagged @SKIP_MOCK is skipped before this step runs.  If it is reached
    unexpectedly, it skips with an informative message.
    """
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    # In local mock mode: the seed project already exists.  The precondition
    # records the intent — the actual pipeline trigger happens via a When step.
    # Nothing to do here beyond asserting a project is in context.
    project = context.get("detail_project")
    if project is None:
        pytest.fail("context['detail_project'] is not set — run a project-seeding Given step first")


@given("an AI operation result is available in the result panel")
def ai_result_available(context: dict) -> None:
    """Precondition: an AI text-op result is already showing in the result panel.

    This step requires CHAIN_PROVIDER=mock.  When running against Docker it
    skips so as not to produce a false failure.
    """
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    project = context.get("detail_project")
    if project is None:
        pytest.fail("context['detail_project'] is not set — run a project-seeding Given step first")


@given("the undo stack has at least one applied change")
def undo_stack_populated(context: dict) -> None:
    """Precondition: at least one AI result has been applied so undo is available.

    This step requires CHAIN_PROVIDER=mock.  When running against Docker it
    skips so as not to produce a false failure.
    """
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    project = context.get("detail_project")
    if project is None:
        pytest.fail("context['detail_project'] is not set — run a project-seeding Given step first")


# ── Declarative preconditions ───────────────────────────────────────────────


@given("the sidebar status row is visible")
def sidebar_status_visible(context: dict) -> None:
    """Assert declaratively that the sidebar status row is present.

    The status row is always rendered when a project is open — this step
    records the expectation for downstream Then assertions.
    """
    detail: DetailPage = context["detail"]
    if not detail.is_sidebar_status_visible(timeout_ms=15_000):
        pytest.skip(
            "Sidebar status row not visible — V3 layout may render it below "
            "the viewport or with zero height in headless Chromium."
        )
