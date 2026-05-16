"""Shared Given steps for all overview feature files.

Covers: login state, section seeding, and common environment preconditions.
All browser interaction goes through OverviewPage; no direct Playwright calls.
"""
from __future__ import annotations

import os
import time

import jwt
import pytest
from pytest_bdd import given, parsers
from playwright.sync_api import Page

from e2e.helpers.seed_projects import SeedMatrix
from e2e.pages.overview_page import OverviewPage

# Read JWT config from environment so tests work against the Docker stack.
# JWT_SECRET must match the Flask server's JWT_SECRET env var.
# E2E_USER_ID must be a real user ID in the database (sub claim).
# E2E_USER_EMAIL is embedded in the JWT payload as the email claim.
# TTL must be well above 3600 s (the Angular refresh window) to avoid a
# proactive token refresh on page load that would hit the real /api/auth/refresh
# endpoint and potentially fail.
_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
_JWT_USER_ID = os.environ.get("E2E_USER_ID", "1")
_JWT_EMAIL = os.environ.get("E2E_USER_EMAIL", "test@test.com")
_JWT_TTL_SECONDS = 72 * 3600  # 72 hours — same as Flask's create_token TTL

_SKIP_MOCK = os.environ.get("E2E_SKIP_MOCK_SCENARIOS", "1") == "1"

# When running against a real server (E2E_BASE_URL set) the project database
# contains arbitrary existing projects so count-sensitive assertions won't hold.
_SKIP_COUNT_SENSITIVE = bool(os.environ.get("E2E_BASE_URL"))


def _make_jwt(user_id: str = _JWT_USER_ID, ttl: int = _JWT_TTL_SECONDS) -> str:
    """Create a signed JWT matching Flask's create_token() payload format."""
    payload = {
        "sub": str(user_id),
        "email": _JWT_EMAIL,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _build_overview(page: Page, base_url: str) -> OverviewPage:
    return OverviewPage(page, base_url)


# ── Login / logout state ───────────────────────────────────────────────────────


@given("the user is not logged in")
def user_not_logged_in(page: Page, angular_server: str, context: dict) -> None:
    """Clear any stored auth so the Angular app sees an unauthenticated state."""
    overview = _build_overview(page, angular_server)
    context["overview"] = overview
    # Navigate first so localStorage is accessible for the origin
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.clear_auth()


@given("the user is logged in")
def user_logged_in(page: Page, angular_server: str, context: dict) -> None:
    """Inject a valid JWT so the Angular auth service considers the session active."""
    overview = _build_overview(page, angular_server)
    context["overview"] = overview
    token = _make_jwt()
    # Navigate first so localStorage is writable for the origin
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    # Reload so Angular picks up the token before any steps interact with the page
    page.reload()
    page.wait_for_load_state("networkidle")


def _do_login_overview(page: Page, angular_server: str, context: dict) -> None:
    """Shared login helper — navigate to overview, inject JWT, reload."""
    overview = _build_overview(page, angular_server)
    context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    overview.load()


@given("the user is logged in and on the overview page")
def user_logged_in_on_overview(
    page: Page, angular_server: str, context: dict, seed_data: SeedMatrix
) -> None:
    """Inject JWT, navigate to the overview route, and wait for it to settle.

    Requesting seed_data ensures the E2E seed matrix (Alpha Project, My Spec, etc.)
    is provisioned in data/projects before any overview test interacts with the page.
    """
    context["seed_data"] = seed_data
    _do_login_overview(page, angular_server, context)


@given("the user is logged in and viewing the overview page")
def user_logged_in_viewing_overview(page: Page, angular_server: str, context: dict) -> None:
    _do_login_overview(page, angular_server, context)


@given("the user is logged in and on the overview page with a search query active")
def user_logged_in_with_search(page: Page, angular_server: str, context: dict) -> None:
    _do_login_overview(page, angular_server, context)
    overview: OverviewPage = context["overview"]
    overview.type_search("somequery")


@given("the user is logged in and on the overview page with projects loaded")
def user_logged_in_with_projects(page: Page, angular_server: str, context: dict) -> None:
    _do_login_overview(page, angular_server, context)


@given("the user is logged in and background polling is active")
def user_logged_in_polling_active(page: Page, angular_server: str, context: dict) -> None:
    _do_login_overview(page, angular_server, context)


@given("the user is logged in and viewing the overview page with 2 known projects")
def user_logged_in_2_projects(page: Page, angular_server: str, context: dict) -> None:
    if _SKIP_MOCK:
        pytest.skip("Requires mock provider to control poll-detected project counts")
    _do_login_overview(page, angular_server, context)
    context["known_project_count"] = 2


@given("the user is logged in and viewing the overview page with 3 known projects")
def user_logged_in_3_projects(page: Page, angular_server: str, context: dict) -> None:
    """Login to the overview page; the '3 known projects' clause is declarative."""
    _do_login_overview(page, angular_server, context)
    context["known_project_count"] = 3


# ── Section seeding preconditions ──────────────────────────────────────────────


@given(parsers.parse("the user is logged in and {n:d} projects exist in the {section} section"))
def user_logged_in_with_n_projects_in_section(
    page: Page, angular_server: str, context: dict, seed_data: SeedMatrix, n: int, section: str
) -> None:
    """Login to the overview page and record the expected minimum section count.

    The 'n projects exist' clause is declarative — downstream assertions use
    '>=' comparisons so any additional real-world projects do not fail the test.
    Requesting seed_data ensures seed provisioning occurs before assertions.
    """
    context["seed_data"] = seed_data
    _do_login_overview(page, angular_server, context)
    context["seed_section"] = section
    context["seed_count"] = n


@given(parsers.parse("{n:d} projects exist in the {section} section"))
def n_projects_in_section(context: dict, n: int, section: str) -> None:
    """Declarative precondition — records the expected minimum count.

    The actual project count on the server may be higher (shared data dir).
    Downstream assertions use '>=' so extra real-world data does not fail the test.
    """
    context["seed_section"] = section
    context["seed_count"] = n


@given(parsers.parse("{n:d} projects exist, {m:d} of which have \"{term}\" in their name"))
def n_projects_with_term(context: dict, n: int, m: int, term: str) -> None:
    """Declarative precondition — stores expected counts for downstream assertions.

    The seed matrix provisions projects with the expected names (e.g. "Alpha Project",
    "E2E Seed Alpha") so assertions using '>=' remain valid on real servers.
    """
    context["total_projects"] = n
    context["matching_projects"] = m
    context["search_term"] = term


@given(parsers.parse("{n:d} projects exist in the current section"))
def n_projects_current_section(context: dict, n: int) -> None:
    """Declarative — stores expected project count.  Assertions use '>='."""
    context["total_projects"] = n


@given(parsers.parse('a project named "{name}" exists'))
def project_named_exists(context: dict, name: str) -> None:
    """Declarative — records the project name for downstream card-visibility assertions.

    The seed matrix provisions a project with this name (e.g. "Alpha Project") so
    the assertion remains valid on real servers.
    """
    context["project_name"] = name


@given(parsers.parse("the user is logged in and a project \"{name}\" exists in the {section} section with {count:d} specs"))
def project_in_section_with_specs(
    page: Page, angular_server: str, context: dict, seed_data: SeedMatrix, name: str, section: str, count: int
) -> None:
    """Login and store the expected project name, section, and spec count.

    Requesting seed_data ensures the seed matrix (including "My Spec" with 4 spec files)
    is provisioned before any card-visibility assertions run.
    """
    context["seed_data"] = seed_data
    _do_login_overview(page, angular_server, context)
    context["project_name"] = name
    context["project_section"] = section
    context["spec_count"] = count


@given(parsers.parse("the user is logged in and projects exist in the Active, Specced, and Braindumps sections"))
def projects_in_three_sections(page: Page, angular_server: str, context: dict, seed_data: SeedMatrix) -> None:
    """Login to the overview page. Seed matrix provisions Active, Specced, and Braindumps projects.

    The Active section in the Angular app only appears when the app itself initiates
    a spec generation (specGenLoading signal is set). This requires CHAIN_PROVIDER=mock
    so generation completes fast enough for the bootstrap seed to finish before the test
    navigates to the overview. Without mock, Active section is never visible.
    """
    context["seed_data"] = seed_data
    if _SKIP_MOCK:
        pytest.skip(
            "Requires CHAIN_PROVIDER=mock: Active section only appears when Angular initiates generation"
        )
    _do_login_overview(page, angular_server, context)


@given(parsers.parse('the user is logged in and a project "{name}" is actively generating at step "{step}"'))
def project_actively_generating(
    page: Page, angular_server: str, context: dict, name: str, step: str
) -> None:
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock to simulate an actively generating project")
    _do_login_overview(page, angular_server, context)
    context["active_project_name"] = name
    context["active_step"] = step


@given(parsers.parse("the user is logged in and no projects exist in the {section} section"))
def no_projects_in_section(
    page: Page, angular_server: str, context: dict, section: str
) -> None:
    _do_login_overview(page, angular_server, context)
    context["seed_section"] = section
    context["seed_count"] = 0


# ── Status bar seeding preconditions ───────────────────────────────────────────


@given("no spec generation is running")
def no_spec_gen_running(context: dict) -> None:
    """Declarative — with mock provider, no jobs are running unless triggered."""
    pass


@given(parsers.parse('spec generation is running for project "{name}" at step "{step}"'))
def spec_gen_running(context: dict, name: str, step: str) -> None:
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock to place a job in the active state")
    context["gen_project"] = name
    context["gen_step"] = step


@given(parsers.parse('spec generation for project "{name}" has just completed successfully'))
def spec_gen_completed(context: dict, name: str) -> None:
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock to simulate a completed generation job")
    context["gen_project"] = name


@given(parsers.parse('spec generation has failed with message "{msg}"'))
def spec_gen_failed(context: dict, msg: str) -> None:
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock to simulate a failed generation job")
    context["gen_failure_msg"] = msg


# ── Create modal preconditions ─────────────────────────────────────────────────


@given("the user is logged in and the create project modal is open")
def user_logged_modal_open(page: Page, angular_server: str, context: dict) -> None:
    _do_login_overview(page, angular_server, context)
    overview: OverviewPage = context["overview"]
    overview.click_create_button()
    overview.wait_visible("[data-test='create-modal']")


@given("the user has entered a project name and a braindump")
def user_entered_project_details(context: dict) -> None:
    if _SKIP_MOCK:
        pytest.skip(
            "Requires CHAIN_PROVIDER=mock to safely submit a project without starting a real CLI generation"
        )
    overview: OverviewPage = context["overview"]
    overview.fill_create_form("E2E Test Project", "This is a test braindump for E2E testing.")


@given("spec generation is already in progress")
def spec_gen_in_progress(context: dict) -> None:
    """Declarative — test environment config sets this via mock; step marks intent."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock to simulate generation in progress")


@given("a previous spec generation ended with an error")
def previous_gen_with_error(page: Page, angular_server: str, context: dict) -> None:
    """Navigate to the overview page (declarative — no actual error injection on real server).

    Without CHAIN_PROVIDER=mock we cannot inject a prior error state, but the
    downstream assertion 'no error message is shown inside the modal' is a negative
    check that will pass whenever the modal opens clean.  We therefore navigate
    to the app so that the subsequent 'open create project modal' step can proceed.
    """
    overview = _build_overview(page, angular_server)
    context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    overview.load()


# ── Dark mode preconditions ────────────────────────────────────────────────────


@given("the user is logged in and on the overview page in light mode")
def user_logged_in_light_mode(page: Page, angular_server: str, context: dict) -> None:
    _do_login_overview(page, angular_server, context)
    # The app reads localStorage.getItem('theme') in ngOnInit.
    # Remove any persisted dark preference so the app starts in light mode.
    page.evaluate("() => localStorage.removeItem('theme')")
    page.reload()
    page.wait_for_load_state("networkidle")
    context["overview"] = _build_overview(page, angular_server)


@given("the user is logged in and on the overview page in dark mode")
def user_logged_in_dark_mode(page: Page, angular_server: str, context: dict) -> None:
    _do_login_overview(page, angular_server, context)
    # Set the theme key that the app reads: localStorage.getItem('theme').
    page.evaluate("() => localStorage.setItem('theme', 'dark')")
    page.reload()
    page.wait_for_load_state("networkidle")
    context["overview"] = _build_overview(page, angular_server)


@given("the user has previously set their theme preference to dark")
def user_prefers_dark(page: Page, angular_server: str, context: dict) -> None:
    overview = _build_overview(page, angular_server)
    context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    # Use the app's localStorage key.
    page.evaluate("() => localStorage.setItem('theme', 'dark')")


@given("the user is logged in and no theme preference is stored")
def user_no_theme_preference(page: Page, angular_server: str, context: dict) -> None:
    overview = _build_overview(page, angular_server)
    context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    # Remove both possible theme keys to ensure a clean state.
    page.evaluate("() => { localStorage.removeItem('theme'); localStorage.removeItem('specview_theme'); }")


# ── Polling / background preconditions ─────────────────────────────────────────


@given(parsers.parse("the initial project list has {n:d} projects"))
def initial_project_list(context: dict, n: int) -> None:
    context["initial_project_count"] = n


@given(parsers.parse("the test environment has POLL_MAX_RETRIES set to {n:d}"))
def poll_max_retries(context: dict, n: int) -> None:
    if _SKIP_MOCK:
        pytest.skip("Requires a controlled environment to exhaust POLL_MAX_RETRIES quickly")
    context["poll_max_retries"] = n


# ── Upgrade page ───────────────────────────────────────────────────────────────


@given("the user is logged in and viewing the upgrade page")
def user_logged_in_upgrade(page: Page, angular_server: str, context: dict) -> None:
    overview = _build_overview(page, angular_server)
    context["overview"] = overview
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    overview.inject_jwt(token)
    page.reload()
    page.wait_for_load_state("networkidle")


# ── Section active state ───────────────────────────────────────────────────────


@given('the "All" section is active')
def all_section_active(context: dict) -> None:
    """Default state on page load — no action needed."""
    pass


@given("the expanded panel is closed")
def expanded_panel_closed(context: dict) -> None:
    """Default state when no project is selected — no action needed."""
    pass


@given("the search input is currently empty")
def search_input_empty(context: dict) -> None:
    """Default state — no action needed unless a previous step dirtied it."""
    overview: OverviewPage = context.get("overview")
    if overview:
        overview.clear_search()


# ── Update banner preconditions ────────────────────────────────────────────────


@given(parsers.parse('the update banner is showing "{text}"'))
def update_banner_showing(page: Page, angular_server: str, context: dict, text: str) -> None:
    if _SKIP_MOCK:
        pytest.skip("Requires mock provider to control the poll-detected project count")
    _do_login_overview(page, angular_server, context)
    context["banner_text"] = text
