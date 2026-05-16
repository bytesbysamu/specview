"""Given steps for SaaS auth and isolation feature files.

Covers: multi-user setup (user A / user B), JWT generation per user,
expired-token injection, and common SaaS navigation preconditions.
All browser interaction goes through SaasPage; no direct Playwright calls.
"""
from __future__ import annotations

import os
import time
import uuid

import jwt
import pytest
import requests
from pytest_bdd import given, parsers
from playwright.sync_api import Page

from e2e.pages.saas_page import SaasPage

# ── JWT configuration ─────────────────────────────────────────────────────────
# Matches the values used in overview_preconditions.py for consistency.

_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
_JWT_USER_ID = os.environ.get("E2E_USER_ID", "1")
_JWT_EMAIL = os.environ.get("E2E_USER_EMAIL", "test@test.com")
_JWT_TTL_SECONDS = 72 * 3600

# Two secondary users for isolation testing.
_USER_B_EMAIL = os.environ.get("E2E_USER_B_EMAIL", "user-b@e2e.test")
_USER_B_PASSWORD = os.environ.get("E2E_USER_B_PASSWORD", "e2e-user-b-pw-1234")

_SKIP_MOCK = os.environ.get("E2E_SKIP_MOCK_SCENARIOS", "1") == "1"


def _make_jwt(
    user_id: str = _JWT_USER_ID,
    email: str = _JWT_EMAIL,
    ttl: int = _JWT_TTL_SECONDS,
) -> str:
    """Create a signed JWT matching Flask's create_token() payload format."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _make_expired_jwt(user_id: str = _JWT_USER_ID) -> str:
    """Create a JWT that has already expired (exp = now - 1s)."""
    payload = {
        "sub": str(user_id),
        "email": _JWT_EMAIL,
        "iat": int(time.time()) - 10,
        "exp": int(time.time()) - 1,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _build_saas(page: Page, base_url: str) -> SaasPage:
    return SaasPage(page, base_url)


def _register_user(api_base_url: str, email: str, password: str) -> dict | None:
    """Register a new user via POST /api/auth/register.

    Returns the response JSON dict (containing 'token' and 'email') on
    success, or None if the request fails or the email is already taken.
    Silently swallows 409 Conflict (already registered) and returns None.
    """
    try:
        resp = requests.post(
            f"{api_base_url}/api/auth/register",
            json={"email": email, "password": password},
            timeout=10,
        )
    except requests.RequestException:
        return None

    if resp.status_code in (200, 201):
        return resp.json()

    # 409 means already registered — not a failure for our purposes.
    return None


# ── Plan state helpers ────────────────────────────────────────────────────────

def _inject_plan_via_api(flask_server: str, token: str, plan: str) -> bool:
    """Attempt to set the user's plan via PUT /api/billing/test-plan.

    Returns True if successful, False otherwise. This endpoint only exists
    in SKIP_AUTH / test mode and is not available in production Docker.
    """
    try:
        resp = requests.put(
            f"{flask_server}/api/billing/test-plan",
            json={"plan": plan},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except requests.RequestException:
        return False


# ── Login / overview navigation preconditions ─────────────────────────────────


@given("the user is not logged in and is on the login page")
def user_not_logged_in_on_login_page(
    page: Page, angular_server: str, context: dict
) -> None:
    """Clear any stored auth and navigate to the login page."""
    saas = _build_saas(page, angular_server)
    context["saas"] = saas
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    saas.clear_auth()
    saas.go_to_login()


@given("the user navigates to the login page")
def user_navigates_to_login(page: Page, angular_server: str, context: dict) -> None:
    """Navigate to the /login route."""
    saas: SaasPage = context.get("saas")
    if saas is None:
        saas = _build_saas(page, angular_server)
        context["saas"] = saas
    saas.go_to_login()


@given("the user is not logged in and is on the signup page")
def user_not_logged_in_on_signup_page(
    page: Page, angular_server: str, context: dict
) -> None:
    """Clear any stored auth and navigate to the signup page."""
    saas = _build_saas(page, angular_server)
    context["saas"] = saas
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    saas.clear_auth()
    saas.go_to_signup()


@given("the user is logged in via JWT injection")
def user_logged_in_via_jwt(page: Page, angular_server: str, context: dict) -> None:
    """Inject a valid JWT so the Angular auth service sees an active session."""
    saas = _build_saas(page, angular_server)
    context["saas"] = saas
    token = _make_jwt()
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    saas.inject_jwt(token)
    page.reload()
    page.wait_for_load_state("networkidle")


@given("the user's session token has expired")
def user_session_token_expired(page: Page, angular_server: str, context: dict) -> None:
    """Replace the current JWT with an already-expired token and reload.

    Requires 'saas' to be in context — call after a login-precondition step.
    """
    saas: SaasPage = context.get("saas")
    if saas is None:
        saas = _build_saas(page, angular_server)
        context["saas"] = saas
    saas.expire_jwt()


# ── Multi-user isolation preconditions ────────────────────────────────────────


@given("user A is registered and has a project")
def user_a_registered_with_project(
    page: Page, angular_server: str, flask_server: str, context: dict
) -> None:
    """Register user A via the API and seed a project for them.

    Creates user A using the E2E credentials, seeds a project file
    directly to the filesystem, and stores the project ID in context so
    user B can attempt to access it later.

    When running against SKIP_AUTH mode (local dev), ownership enforcement
    is bypassed — the isolation scenario will be skipped in that mode.
    """
    if not os.environ.get("JWT_SECRET"):
        pytest.skip(
            "SA-06 requires real JWT_SECRET and user-owned projects. "
            "Run against the Docker stack with E2E_BASE_URL set."
        )

    # Register user A using the primary E2E credentials.
    user_a_email = _JWT_EMAIL
    user_a_password = os.environ.get("E2E_USER_PASSWORD", "e2e-user-a-pw-5678")

    result = _register_user(flask_server, user_a_email, user_a_password)
    # If registration failed, try to log in (user may already exist from a prior run).
    if result is None:
        try:
            resp = requests.post(
                f"{flask_server}/api/auth/login",
                json={"email": user_a_email, "password": user_a_password},
                timeout=10,
            )
            if resp.status_code == 200:
                result = resp.json()
        except requests.RequestException:
            pass

    if result is None:
        pytest.skip("Could not authenticate user A — skipping isolation scenario")

    user_a_token = result["token"]
    context["user_a_token"] = user_a_token

    # Seed a project for user A via the API so it is registered in the DB.
    from e2e.helpers.seed_projects import _provision_project_via_api
    project_name = f"E2E SA06 UserA Project {int(time.time())}"
    project_info = _provision_project_via_api(
        flask_server,
        project_name,
        [("braindump.md", "# User A Project\n\nThis belongs to user A.\n")],
        user_a_token,
    )

    if project_info is None:
        pytest.skip("Could not seed user A's project — skipping isolation scenario")

    context["user_a_project"] = project_info
    context["flask_server"] = flask_server

    # Build the SaasPage and put it in context for downstream steps.
    saas = _build_saas(page, angular_server)
    context["saas"] = saas


@given("user B is logged in")
def user_b_logged_in(
    page: Page, angular_server: str, flask_server: str, context: dict
) -> None:
    """Register user B (if needed) and inject their JWT into the browser.

    User B is a separate account with no ownership of user A's projects.
    This step injects user B's JWT so the Angular app sends their token
    on subsequent API requests.
    """
    if not os.environ.get("JWT_SECRET"):
        pytest.skip(
            "SA-06 requires real JWT_SECRET. Run against the Docker stack."
        )

    # Generate a unique email for user B so parallel runs don't collide.
    user_b_email = f"user-b-{int(time.time())}@e2e.test"
    user_b_password = _USER_B_PASSWORD

    result = _register_user(flask_server, user_b_email, user_b_password)
    if result is None:
        pytest.skip("Could not register user B — skipping isolation scenario")

    user_b_token = result["token"]
    context["user_b_token"] = user_b_token
    context["user_b_email"] = user_b_email

    # Build the saas page and inject user B's JWT.
    saas: SaasPage = context.get("saas")
    if saas is None:
        saas = _build_saas(page, angular_server)
        context["saas"] = saas

    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    saas.inject_jwt(user_b_token)
    page.reload()
    page.wait_for_load_state("networkidle")


# ── Billing / plan state preconditions ────────────────────────────────────────


@given("the user is logged in as a free-plan user")
def user_logged_in_free_plan(
    page: Page, angular_server: str, flask_server: str, context: dict
) -> None:
    """Inject a valid JWT and ensure the user has free-plan state.

    In SKIP_AUTH mode the billing/status endpoint returns 'free' by default,
    so no additional plan injection is needed. In Docker mode the user's plan
    is already set when they register (defaults to free).
    """
    saas = _build_saas(page, angular_server)
    context["saas"] = saas
    token = _make_jwt()
    context["jwt_token"] = token
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    saas.inject_jwt(token)
    page.reload()
    page.wait_for_load_state("networkidle")


@given("the user is logged in as a pro-plan user")
def user_logged_in_pro_plan(
    page: Page, angular_server: str, flask_server: str, context: dict
) -> None:
    """Inject a JWT and attempt to set the user's plan to 'pro'.

    This step requires the billing test endpoint or Docker plan injection.
    If neither is available the scenario is skipped.
    """
    if _SKIP_MOCK:
        pytest.skip(
            "SA-10 pro-plan variant requires plan injection. "
            "Tag: @SKIP_MOCK — skip in Docker-only mode."
        )
    saas = _build_saas(page, angular_server)
    context["saas"] = saas
    token = _make_jwt()
    context["jwt_token"] = token
    page.goto(angular_server)
    page.wait_for_load_state("networkidle")
    saas.inject_jwt(token)
    page.reload()
    page.wait_for_load_state("networkidle")


@given("a 429 rate-limit response is configured")
def configure_mock_429(
    page: Page, angular_server: str, context: dict
) -> None:
    """Configure a mock 429 response — requires mock infrastructure.

    This step is always skipped when E2E_SKIP_MOCK_SCENARIOS=1 (default).
    It exists to document SA-08 and serve as the hook for mock-enabled runs.
    """
    pytest.skip(
        "SA-08 requires intercepting a 429 from a mock billing HTTP layer. "
        "Tag: @SKIP_MOCK — not runnable against plain Docker."
    )
