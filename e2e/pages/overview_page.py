"""Page object for the Specview overview (home) page."""
from __future__ import annotations

import time
from playwright.sync_api import Page

from e2e.pages.app_page import AppPage

_OVERVIEW_ROUTE = "/"


class OverviewPage(AppPage):
    """Page object for the main overview grid and masthead."""

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url + _OVERVIEW_ROUTE)

    # ── Section tab navigation ─────────────────────────────────────────────

    def click_section_tab(self, name: str) -> None:
        """Click the section tab whose visible label matches *name* exactly."""
        self.page.locator(
            "[data-test='section-tab']",
            has_text=name,
        ).click()

    def get_active_tab(self) -> str:
        """Return the label text of the currently active section tab."""
        return (
            self.page.locator("[data-test='section-tab'].active")
            .first.inner_text()
            .strip()
        )

    def count_section_tabs(self) -> int:
        """Return the total number of section tab buttons."""
        return self.page.locator("[data-test='section-tab']").count()

    def is_tab_active(self, name: str) -> bool:
        """Return True if the tab labelled *name* carries the active CSS class."""
        loc = self.page.locator("[data-test='section-tab']", has_text=name)
        classes = loc.get_attribute("class") or ""
        return "active" in classes.split()

    def get_section_count_badge(self, section_name: str) -> int:
        """Return the integer shown in the count badge for the named section tab."""
        badge_text = (
            self.page.locator("[data-test='section-tab']", has_text=section_name)
            .locator("[data-test='section-tab-count']")
            .inner_text()
            .strip()
        )
        return int(badge_text)

    # ── Status bar ────────────────────────────────────────────────────────

    def get_status_bar_text(self) -> str:
        """Return the concatenated visible text of the status bar, normalized.

        Collapses all whitespace (including newlines from inline span elements)
        into single spaces and lowercases for consistent comparisons.
        """
        raw = self.page.locator("[data-test='status-bar']").inner_text().strip()
        import re
        return re.sub(r"\s+", " ", raw).lower()

    def get_status_bar_state(self) -> str:
        """Return the modifier class active on the status bar element.

        Returns one of: 'idle', 'active', 'success', 'failure'.
        """
        classes = self.page.locator("[data-test='status-bar']").get_attribute("class") or ""
        for state in ("active", "success", "failure", "idle"):
            modifier = f"gen-status-bar--{state}"
            if modifier in classes:
                return state
        return "idle"

    def is_status_bar_active(self, timeout_ms: int = 10_000) -> bool:
        """Return True if the status bar has the active modifier within *timeout_ms*."""
        return self.is_visible(".gen-status-bar--active", timeout_ms=timeout_ms)

    def is_cancel_button_visible(self) -> bool:
        return self.is_visible("[data-test='cancel-generation-global']")

    def is_retry_button_visible(self) -> bool:
        return self.is_visible(".gen-status-retry")

    # ── Search bar ────────────────────────────────────────────────────────

    def type_search(self, query: str) -> None:
        """Type *query* into the search input."""
        self.enter_text("[data-test='search-input']", query)

    def clear_search(self) -> None:
        """Clear the search input field."""
        self.enter_text("[data-test='search-input']", "")

    def get_search_count_text(self) -> str:
        """Return the text of the search count / project count element."""
        return self.page.locator("[data-test='search-count']").inner_text().strip()

    def is_search_visible(self) -> bool:
        return self.is_visible("[data-test='search-input']", timeout_ms=3_000)

    def is_search_hidden(self) -> bool:
        """Return True when the search input is absent from the DOM or hidden."""
        try:
            self.page.wait_for_selector(
                "[data-test='search-input']", timeout=3_000, state="hidden"
            )
            return True
        except Exception:
            return False

    # ── Project grid ──────────────────────────────────────────────────────

    def get_visible_card_count(self) -> int:
        """Return the number of visible project cards."""
        return self.page.locator("[data-test='project-card']").count()

    def get_cards_in_section(self, section_name: str) -> int:
        """Return the number of project cards inside the section group labelled *section_name*."""
        group = self.page.locator(
            f"[data-test='section-group'][data-section='{section_name}']"
        )
        return group.locator("[data-test='project-card']").count()

    def is_card_visible(self, project_name: str) -> bool:
        """Return True if a project card whose title contains *project_name* is visible."""
        loc = self.page.locator("[data-test='project-card']", has_text=project_name)
        try:
            loc.wait_for(state="visible", timeout=5_000)
            return True
        except Exception:
            return False

    def get_section_group_order(self) -> list[str]:
        """Return section group titles in DOM order, title-cased for comparison."""
        locators = self.page.locator("[data-test='section-group']").all()
        titles = []
        for loc in locators:
            title = loc.locator(".section-group-title").inner_text().strip().title()
            titles.append(title)
        return titles

    def is_empty_state_visible(self) -> bool:
        return self.is_visible(".empty-state", timeout_ms=3_000)

    def is_column_layout_visible(self) -> bool:
        """Return True if file-column elements are present (non-grouped layout)."""
        return self.is_visible(".file-column", timeout_ms=3_000)

    def section_group_headers_visible(self) -> bool:
        return self.is_visible("[data-test='section-group']", timeout_ms=2_000)

    # ── Masthead ──────────────────────────────────────────────────────────

    def is_masthead_visible(self) -> bool:
        return self.is_visible("[data-test='masthead-title']", timeout_ms=5_000)

    def get_masthead_title(self) -> str:
        return self.page.locator("[data-test='masthead-title']").inner_text().strip()

    def is_page_shell_visible(self) -> bool:
        """Return True if the outer .page div is present."""
        return self.is_visible(".page", timeout_ms=5_000)

    def is_router_outlet_only(self) -> bool:
        """Return True when the page shell is absent (unauthenticated path)."""
        return not self.is_visible(".page", timeout_ms=2_000)

    # ── Update banner ─────────────────────────────────────────────────────

    def is_update_banner_visible(self) -> bool:
        return self.is_visible("[data-test='update-banner']", timeout_ms=5_000)

    def click_dismiss_banner(self) -> None:
        self.page.locator("[data-test='update-banner'] button").click()

    # ── Create modal ──────────────────────────────────────────────────────

    def click_create_button(self) -> None:
        self.click("[data-test='create-button']")

    def is_create_modal_visible(self) -> bool:
        return self.is_visible("[data-test='create-modal']", timeout_ms=5_000)

    def is_create_modal_hidden(self) -> bool:
        """Return True when the create-modal element is absent or hidden."""
        try:
            self.page.wait_for_selector(
                "[data-test='create-modal']", timeout=5_000, state="hidden"
            )
            return True
        except Exception:
            return False

    def click_modal_backdrop(self) -> None:
        """Click the backdrop area outside the modal dialog to dismiss it."""
        backdrop = self.page.locator(".modal-backdrop")
        # Click the top-left corner of the backdrop, which is outside the centered modal.
        backdrop.click(position={"x": 10, "y": 10})

    def fill_create_form(self, name: str, braindump: str) -> None:
        """Fill the create-project form fields using Playwright's reliable fill method."""
        name_input = self.page.locator("#projectName")
        name_input.wait_for(state="visible", timeout=5_000)
        name_input.fill(name)
        braindump_input = self.page.locator("[data-test='braindump-input']")
        braindump_input.wait_for(state="visible", timeout=5_000)
        braindump_input.fill(braindump)

    def click_generate_button(self) -> None:
        """Click the Generate Specs button in the create-project modal."""
        btn = self.page.locator(".modal-generate")
        btn.wait_for(state="visible", timeout=5_000)
        btn.click()

    def is_generate_button_disabled(self) -> bool:
        attr = self.page.locator(".modal-generate").get_attribute("disabled")
        return attr is not None

    def is_modal_error_visible(self) -> bool:
        return self.is_visible(".modal .text-ops-error", timeout_ms=2_000)

    # ── Dark mode ─────────────────────────────────────────────────────────

    def toggle_dark_mode(self) -> None:
        self.click("[data-test='dark-mode-toggle']")

    def is_dark_mode_active(self) -> bool:
        """Return True when the document root carries a dark theme attribute."""
        attr = self.page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        )
        return attr == "dark"

    def get_theme_preference_from_storage(self) -> str | None:
        """Return the theme string stored in localStorage under the app's key."""
        return self.page.evaluate(
            "() => localStorage.getItem('theme')"
        )

    # ── Auth helpers ──────────────────────────────────────────────────────

    def inject_jwt(self, token: str) -> None:
        """Write a JWT into localStorage so the Angular auth service picks it up."""
        self.page.evaluate(
            f"() => localStorage.setItem('specview_jwt', {token!r})"
        )

    def clear_auth(self) -> None:
        """Remove all auth tokens from localStorage."""
        self.page.evaluate("() => localStorage.removeItem('specview_jwt')")

    def expire_jwt(self) -> None:
        """Replace the stored JWT with one that has already expired."""
        import time as _time
        import jwt as _jwt

        expired_token = _jwt.encode(
            {"sub": "test@test.com", "exp": int(_time.time()) - 1},
            "dev-secret-change-in-prod",
            algorithm="HS256",
        )
        self.inject_jwt(expired_token)
        # Reload so the Angular app re-reads localStorage
        self.page.reload()
        self.page.wait_for_load_state("networkidle")
