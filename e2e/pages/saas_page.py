"""Page object for SaaS auth and isolation flows.

Covers: login form, signup form, error messages, 403 page,
and full-page route container detection.
All selectors use data-test attributes exclusively.
"""
from __future__ import annotations

from playwright.sync_api import Page

from e2e.pages.app_page import AppPage

_LOGIN_ROUTE = "/login"
_SIGNUP_ROUTE = "/signup"
_UPGRADE_ROUTE = "/upgrade"


class SaasPage(AppPage):
    """Page object for SaaS auth forms, 403 denial page, and full-page routes."""

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)

    # ── Login form ────────────────────────────────────────────────────────────

    def go_to_login(self) -> None:
        """Navigate to the /login route and wait for network idle."""
        self.page.goto(self.base_url + _LOGIN_ROUTE)
        self.page.wait_for_load_state("networkidle")

    def fill_login_email(self, email: str) -> None:
        """Enter *email* into the login email field."""
        self.enter_text("[data-test='login-email']", email)

    def fill_login_password(self, password: str) -> None:
        """Enter *password* into the login password field."""
        self.enter_text("[data-test='login-password']", password)

    def click_login_submit(self) -> None:
        """Click the login submit button."""
        self.click("[data-test='login-submit']")

    def submit_login(self, email: str, password: str) -> None:
        """Fill and submit the login form in one call."""
        self.fill_login_email(email)
        self.fill_login_password(password)
        self.click_login_submit()

    # ── Signup form ───────────────────────────────────────────────────────────

    def go_to_signup(self) -> None:
        """Navigate to the /signup route and wait for network idle."""
        self.page.goto(self.base_url + _SIGNUP_ROUTE)
        self.page.wait_for_load_state("networkidle")

    def fill_signup_email(self, email: str) -> None:
        """Enter *email* into the signup email field."""
        self.enter_text("[data-test='signup-email']", email)

    def fill_signup_password(self, password: str) -> None:
        """Enter *password* into the signup password field."""
        self.enter_text("[data-test='signup-password']", password)

    def click_signup_submit(self) -> None:
        """Click the signup register button."""
        self.click("[data-test='signup-submit']")

    def submit_signup(self, email: str, password: str) -> None:
        """Fill and submit the signup form in one call."""
        self.fill_signup_email(email)
        self.fill_signup_password(password)
        self.click_signup_submit()

    # ── Error messages ────────────────────────────────────────────────────────

    def get_login_error(self) -> str:
        """Return the text of the login error message container, or '' if absent."""
        loc = self.page.locator("[data-test='login-error']")
        try:
            loc.wait_for(state="visible", timeout=5_000)
            return loc.inner_text().strip()
        except Exception:
            return ""

    def get_signup_error(self) -> str:
        """Return the text of the signup error message container, or '' if absent."""
        loc = self.page.locator("[data-test='signup-error']")
        try:
            loc.wait_for(state="visible", timeout=5_000)
            return loc.inner_text().strip()
        except Exception:
            return ""

    def is_login_error_visible(self) -> bool:
        """Return True if a login error message is displayed."""
        return self.is_visible("[data-test='login-error']", timeout_ms=5_000)

    def is_signup_error_visible(self) -> bool:
        """Return True if a signup error message is displayed."""
        return self.is_visible("[data-test='signup-error']", timeout_ms=5_000)

    def is_signup_form_visible(self) -> bool:
        """Return True if the signup email input field is visible."""
        return self.is_visible("[data-test='signup-email']", timeout_ms=5_000)

    # ── URL / redirect helpers ────────────────────────────────────────────────

    def get_current_path(self) -> str:
        """Return the current URL pathname (e.g. '/', '/login', '/signup')."""
        return self.page.url.replace(self.base_url, "").split("?")[0] or "/"

    def is_on_login_page(self) -> bool:
        """Return True when the login form is visible on the current page."""
        return self.is_visible("[data-test='login-email']", timeout_ms=5_000)

    def is_on_overview_page(self) -> bool:
        """Return True when the authenticated page shell is visible."""
        return self.is_visible(".page", timeout_ms=10_000)

    def wait_for_redirect_to_login(self, timeout_ms: int = 10_000) -> None:
        """Wait until the login form appears (used to verify redirect after expiry)."""
        self.wait_visible("[data-test='login-email']", timeout_ms=timeout_ms)

    def wait_for_redirect_to_overview(self, timeout_ms: int = 10_000) -> None:
        """Wait until the page shell appears (used to verify successful login)."""
        self.wait_visible(".page", timeout_ms=timeout_ms)

    # ── 403 / access-denied page ──────────────────────────────────────────────

    def is_access_denied_visible(self) -> bool:
        """Return True if the access-denied (403) message block is visible."""
        return self.is_visible("[data-test='access-denied-message']", timeout_ms=10_000)

    def get_access_denied_text(self) -> str:
        """Return the combined text of the access-denied message block."""
        loc = self.page.locator("[data-test='access-denied-message']")
        try:
            loc.wait_for(state="visible", timeout=10_000)
            return loc.inner_text().strip()
        except Exception:
            return ""

    def click_access_denied_back(self) -> None:
        """Click the 'Back to projects' button on the 403 page."""
        self.click("[data-test='access-denied-back']")

    def is_access_denied_back_visible(self) -> bool:
        """Return True if the back button on the 403 page is visible."""
        return self.is_visible("[data-test='access-denied-back']", timeout_ms=5_000)

    def wait_access_denied_hidden(self, timeout_ms: int = 5_000) -> None:
        """Wait until the access-denied panel disappears from the DOM."""
        from playwright.sync_api import expect
        expect(
            self.page.locator("[data-test='access-denied-message']")
        ).to_be_hidden(timeout=timeout_ms)

    # ── Project card navigation ───────────────────────────────────────────────

    def click_project_card_by_name(self, project_name: str) -> None:
        """Click the project card whose title contains *project_name*."""
        self.page.locator(
            "[data-test='project-card']", has_text=project_name
        ).first.click()

    # ── Full-page route detection ─────────────────────────────────────────────

    def is_page_shell_visible(self) -> bool:
        """Return True if the outer .page div (app shell) is present."""
        return self.is_visible(".page", timeout_ms=5_000)

    def is_full_page_route(self) -> bool:
        """Return True when the page shell is absent — indicates a full-page route."""
        return not self.is_visible(".page", timeout_ms=2_000)

    def go_to_upgrade(self) -> None:
        """Navigate to /upgrade and wait for network idle."""
        self.page.goto(self.base_url + _UPGRADE_ROUTE)
        self.page.wait_for_load_state("networkidle")

    def is_upgrade_page_visible(self) -> bool:
        """Return True if the upgrade page container is rendered."""
        return self.is_visible("[data-test='upgrade-free-view'], [data-test='upgrade-pro-view'], [data-test='upgrade-lapsed-view']", timeout_ms=10_000)

    # ── Usage meter ───────────────────────────────────────────────────────────

    def is_usage_meter_visible(self) -> bool:
        """Return True if the usage-meter component is rendered in the DOM."""
        return self.is_visible("[data-test='usage-meter']", timeout_ms=5_000)

    def get_usage_count_text(self) -> str:
        """Return the text inside the usage count span (e.g. '3/5 remaining')."""
        loc = self.page.locator("[data-test='usage-count']")
        try:
            loc.wait_for(state="visible", timeout=5_000)
            return loc.inner_text().strip()
        except Exception:
            return ""

    def get_usage_remaining(self) -> int | None:
        """Parse and return the remaining count from the usage meter text.

        Returns the integer remaining value, or None if the meter is absent.
        The meter text format is '<remaining>/<limit> remaining'.
        """
        text = self.get_usage_count_text()
        if not text:
            return None
        try:
            return int(text.split("/")[0].strip())
        except (ValueError, IndexError):
            return None

    # ── Masthead upgrade button ───────────────────────────────────────────────

    def is_upgrade_masthead_btn_visible(self) -> bool:
        """Return True if the Upgrade button in the masthead is visible."""
        return self.is_visible("[data-test='upgrade-masthead-btn']", timeout_ms=15_000)

    # ── Upgrade page content inspection ──────────────────────────────────────

    def is_upgrade_free_view_visible(self) -> bool:
        """Return True if the free-plan upgrade CTA is rendered."""
        return self.is_visible("[data-test='upgrade-free-view']", timeout_ms=10_000)

    def is_upgrade_pro_view_visible(self) -> bool:
        """Return True if the pro-plan manage-subscription view is rendered."""
        return self.is_visible("[data-test='upgrade-pro-view']", timeout_ms=10_000)

    def is_upgrade_lapsed_view_visible(self) -> bool:
        """Return True if the lapsed-plan payment-update view is rendered."""
        return self.is_visible("[data-test='upgrade-lapsed-view']", timeout_ms=10_000)

    def is_upgrade_checkout_btn_visible(self) -> bool:
        """Return True if the checkout CTA button is visible on the upgrade page."""
        return self.is_visible("[data-test='upgrade-checkout-btn']", timeout_ms=5_000)

    def is_upgrade_limit_notice_visible(self) -> bool:
        """Return True if the limit-reached notice is shown on the upgrade page."""
        return self.is_visible("[data-test='upgrade-limit-notice']", timeout_ms=5_000)

    def click_upgrade_checkout_btn(self) -> None:
        """Click the 'Upgrade to Pro' checkout button."""
        self.click("[data-test='upgrade-checkout-btn']")

    def get_upgrade_view_name(self) -> str:
        """Return which upgrade view is currently rendered: 'free', 'pro', or 'lapsed'."""
        if self.is_upgrade_pro_view_visible():
            return "pro"
        if self.is_upgrade_lapsed_view_visible():
            return "lapsed"
        if self.is_upgrade_free_view_visible():
            return "free"
        return "unknown"

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def inject_jwt(self, token: str) -> None:
        """Write a JWT into localStorage so the Angular auth service picks it up."""
        self.page.evaluate(
            f"() => localStorage.setItem('specview_jwt', {token!r})"
        )

    def clear_auth(self) -> None:
        """Remove all auth tokens from localStorage."""
        self.page.evaluate("() => localStorage.removeItem('specview_jwt')")

    def expire_jwt(self) -> None:
        """Replace the stored JWT with one that has already expired and reload."""
        import os as _os
        import time as _time
        import jwt as _jwt

        secret = _os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
        expired_token = _jwt.encode(
            {"sub": "1", "email": "test@test.com", "exp": int(_time.time()) - 1},
            secret,
            algorithm="HS256",
        )
        self.inject_jwt(expired_token)
        self.page.reload()
        self.page.wait_for_load_state("networkidle")
