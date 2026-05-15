"""Shared Given steps for all overview feature files.

Covers: login state, section seeding, and common environment preconditions.
All browser interaction goes through OverviewPage; no direct Playwright calls.
"""
from __future__ import annotations

import time

import jwt
import pytest
from pytest_bdd import given, parsers
from playwright.sync_api import Page

from e2e.helpers.seed_projects import SeedMatrix
from e2e.pages.overview_page import OverviewPage

import os

_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
_JWT_USER_ID = os.environ.get("E2E_USER_ID", "1")
_JWT_USER_EMAIL = os.environ.get("E2E_USER_EMAIL", "test@test.com")
_JWT_TTL_SECONDS = 86400  # 24h — must exceed REFRESH_WINDOW_SECONDS (3600) to avoid refresh attempt


def _make_jwt(user_id: str = _JWT_USER_ID, email: str = _JWT_USER_EMAIL, ttl: int = _JWT_TTL_SECONDS) -> str:
    payload = {"sub": user_id, "email": email, "exp": int(time.time()) + ttl}
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _build_overview(page: Page, base_url: str) -> OverviewPage:
    return OverviewPage(page, base_url)


# ── Login / logout state ───────────────────────────────────────────────────────


@given("the user is not logged in")
def user_not_logged_in(page: Page, angular_server: str, step_context: dict) -> None:
    """Clear any stored auth so the Angular app sees an unauthenticated state."""
    overview = _build_overview(page, angular_server)
    step_context["overview"] = overview
    # Navigate first so localStorage is accessible for the origin
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.clear_auth()


@given("the user is logged in")
def user_logged_in(page: Page, angular_server: str, step_context: dict) -> None:
    """Inject a valid JWT then navigate to root so Angular boots authenticated."""
    overview = _build_overview(page, angular_server)
    step_context["overview"] = overview
    token = _make_jwt()
    # Navigate to establish the origin so localStorage is accessible
    page.goto(angular_server + "/login")
    page.wait_for_load_state("domcontentloaded")
    # Inject token into localStorage
    page.evaluate(f"() => localStorage.setItem('specview_jwt', '{token}')")
    # Navigate to root (not reload) so Angular reboots with token and lands on overview
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")


@given("the user is logged in and on the overview page")
def user_logged_in_on_overview(page: Page, angular_server: str, step_context: dict) -> None:
    """Inject JWT, navigate to the overview route, and wait for it to settle."""
    overview = _build_overview(page, angular_server)
    step_context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    overview.load()


@given("the user is logged in and viewing the overview page")
def user_logged_in_viewing_overview(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)


@given("the user is logged in and on the overview page with a search query active")
def user_logged_in_with_search(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    overview: OverviewPage = step_context["overview"]
    overview.type_search("somequery")


@given("the user is logged in and on the overview page with projects loaded")
def user_logged_in_with_projects(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)


@given("the user is logged in and background polling is active")
def user_logged_in_polling_active(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)


@given("the user is logged in and viewing the overview page with 2 known projects")
def user_logged_in_2_projects(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    step_context["known_project_count"] = 2


@given("the user is logged in and viewing the overview page with 3 known projects")
def user_logged_in_3_projects(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    step_context["known_project_count"] = 3


# ── Section seeding preconditions ──────────────────────────────────────────────


@given(parsers.parse("the user is logged in and {n:d} projects exist in the {section} section"))
def user_logged_in_with_n_projects_in_section(
    page: Page, angular_server: str, step_context: dict, seed_data: SeedMatrix, n: int, section: str
) -> None:
    """Login and verify the seed matrix contains the expected count for the section."""
    user_logged_in_on_overview(page, angular_server, step_context)
    step_context["seed_section"] = section
    step_context["seed_count"] = n
    # Verify seed data matches the expected count so the test fails fast if the
    # matrix was not provisioned correctly.
    seeded = seed_data["by_section"].get(section, [])
    assert len(seeded) >= n, (
        f"Expected at least {n} seeded project(s) in section '{section}', "
        f"but only {len(seeded)} were provisioned. "
        f"Sections available: {list(seed_data['by_section'].keys())}"
    )
    step_context["seeded_projects_in_section"] = seeded[:n]


@given(parsers.parse("{n:d} projects exist in the {section} section"))
def n_projects_in_section(step_context: dict, seed_data: SeedMatrix, n: int, section: str) -> None:
    """Verify the session seed data contains the expected count for the named section."""
    step_context["seed_section"] = section
    step_context["seed_count"] = n
    seeded = seed_data["by_section"].get(section, [])
    assert len(seeded) >= n, (
        f"Expected at least {n} seeded project(s) in section '{section}', "
        f"but only {len(seeded)} were provisioned. "
        f"Sections available: {list(seed_data['by_section'].keys())}"
    )
    step_context["seeded_projects_in_section"] = seeded[:n]


@given(parsers.parse("{n:d} projects exist, {m:d} of which have \"{term}\" in their name"))
def n_projects_with_term(step_context: dict, n: int, m: int, term: str) -> None:
    step_context["total_projects"] = n
    step_context["matching_projects"] = m
    step_context["search_term"] = term


@given(parsers.parse("{n:d} projects exist in the current section"))
def n_projects_current_section(step_context: dict, n: int) -> None:
    step_context["total_projects"] = n


@given(parsers.parse('a project named "{name}" exists'))
def project_named_exists(step_context: dict, name: str) -> None:
    step_context["project_name"] = name


@given(parsers.parse("the user is logged in and a project \"{name}\" exists in the {section} section with {count:d} specs"))
def project_in_section_with_specs(
    page: Page, angular_server: str, step_context: dict, name: str, section: str, count: int
) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    step_context["project_name"] = name
    step_context["project_section"] = section
    step_context["spec_count"] = count


@given(parsers.parse("the user is logged in and projects exist in the Active, Specced, and Braindumps sections"))
def projects_in_three_sections(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)


@given(parsers.parse('the user is logged in and a project "{name}" is actively generating at step "{step}"'))
def project_actively_generating(
    page: Page, angular_server: str, step_context: dict, name: str, step: str
) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    step_context["active_project_name"] = name
    step_context["active_step"] = step


@given(parsers.parse("the user is logged in and no projects exist in the {section} section"))
def no_projects_in_section(
    page: Page, angular_server: str, step_context: dict, section: str
) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    step_context["seed_section"] = section
    step_context["seed_count"] = 0


# ── Status bar seeding preconditions ───────────────────────────────────────────


@given("no spec generation is running")
def no_spec_gen_running(step_context: dict) -> None:
    """Declarative — with mock provider, no jobs are running unless triggered."""
    pass


@given(parsers.parse('spec generation is running for project "{name}" at step "{step}"'))
def spec_gen_running(step_context: dict, name: str, step: str) -> None:
    step_context["gen_project"] = name
    step_context["gen_step"] = step


@given(parsers.parse('spec generation for project "{name}" has just completed successfully'))
def spec_gen_completed(step_context: dict, name: str) -> None:
    step_context["gen_project"] = name


@given(parsers.parse('spec generation has failed with message "{msg}"'))
def spec_gen_failed(step_context: dict, msg: str) -> None:
    step_context["gen_failure_msg"] = msg


# ── Create modal preconditions ─────────────────────────────────────────────────


@given("the user is logged in and the create project modal is open")
def user_logged_modal_open(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    overview: OverviewPage = step_context["overview"]
    overview.click_create_button()
    overview.wait_visible("[data-test='create-modal']")


@given("the user has entered a project name and a braindump")
def user_entered_project_details(step_context: dict) -> None:
    overview: OverviewPage = step_context["overview"]
    overview.fill_create_form("E2E Test Project", "This is a test braindump for E2E testing.")


@given("spec generation is already in progress")
def spec_gen_in_progress(step_context: dict) -> None:
    """Declarative — test environment config sets this via mock; step marks intent."""
    pass


@given("a previous spec generation ended with an error")
def previous_gen_with_error(step_context: dict) -> None:
    """Declarative — error state injection handled via mock in conftest."""
    pass


# ── Dark mode preconditions ────────────────────────────────────────────────────


@given("the user is logged in and on the overview page in light mode")
def user_logged_in_light_mode(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    # Ensure light mode by clearing any dark preference
    page.evaluate("() => localStorage.removeItem('specview_theme')")
    page.reload()
    page.wait_for_load_state("networkidle")
    step_context["overview"] = _build_overview(page, angular_server)


@given("the user is logged in and on the overview page in dark mode")
def user_logged_in_dark_mode(page: Page, angular_server: str, step_context: dict) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    page.evaluate("() => localStorage.setItem('specview_theme', 'dark')")
    page.reload()
    page.wait_for_load_state("networkidle")
    step_context["overview"] = _build_overview(page, angular_server)


@given("the user has previously set their theme preference to dark")
def user_prefers_dark(page: Page, angular_server: str, step_context: dict) -> None:
    overview = _build_overview(page, angular_server)
    step_context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    page.evaluate("() => localStorage.setItem('specview_theme', 'dark')")


@given("the user is logged in and no theme preference is stored")
def user_no_theme_preference(page: Page, angular_server: str, step_context: dict) -> None:
    overview = _build_overview(page, angular_server)
    step_context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    page.evaluate("() => localStorage.removeItem('specview_theme')")


# ── Polling / background preconditions ─────────────────────────────────────────


@given(parsers.parse("the initial project list has {n:d} projects"))
def initial_project_list(step_context: dict, n: int) -> None:
    step_context["initial_project_count"] = n


@given(parsers.parse("the test environment has POLL_MAX_RETRIES set to {n:d}"))
def poll_max_retries(step_context: dict, n: int) -> None:
    step_context["poll_max_retries"] = n


# ── Upgrade page ───────────────────────────────────────────────────────────────


@given("the user is logged in and viewing the upgrade page")
def user_logged_in_upgrade(page: Page, angular_server: str, step_context: dict) -> None:
    overview = _build_overview(page, angular_server)
    step_context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    page.reload()
    page.wait_for_load_state("networkidle")


# ── Section active state ───────────────────────────────────────────────────────


@given('the "All" section is active')
def all_section_active(step_context: dict) -> None:
    """Default state on page load — no action needed."""
    pass


@given("the expanded panel is closed")
def expanded_panel_closed(step_context: dict) -> None:
    """Default state when no project is selected — no action needed."""
    pass


@given("the search input is currently empty")
def search_input_empty(step_context: dict) -> None:
    """Default state — no action needed unless a previous step dirtied it."""
    overview: OverviewPage = step_context.get("overview")
    if overview:
        overview.clear_search()


# ── Update banner preconditions ────────────────────────────────────────────────


@given(parsers.parse('the update banner is showing "{text}"'))
def update_banner_showing(page: Page, angular_server: str, step_context: dict, text: str) -> None:
    user_logged_in_on_overview(page, angular_server, step_context)
    step_context["banner_text"] = text
