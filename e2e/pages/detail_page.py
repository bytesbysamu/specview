"""Page object for the Specview project detail (expanded reader) view."""
from __future__ import annotations

import re
from playwright.sync_api import Page

from e2e.pages.app_page import AppPage

# The detail view is not a separate route — it is the overview page with the
# expanded panel open.  We reuse the overview route and open a project card.
_OVERVIEW_ROUTE = "/"

# Canonical file label order as rendered in the sidebar file list.
CANONICAL_FILE_ORDER = [
    "braindump",
    "analysis",
    "epic",
    "architecture",
    "timeline",
    "implementation guide",
]


class DetailPage(AppPage):
    """Page object for the expanded project reader panel and sidebar."""

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url + _OVERVIEW_ROUTE)

    # ── Panel visibility ──────────────────────────────────────────────────────

    def is_reader_panel_visible(self, timeout_ms: int = 10_000) -> bool:
        """Return True if the expanded reader panel container is visible."""
        return self.is_visible("[data-test='reader-panel']", timeout_ms=timeout_ms)

    def wait_reader_panel_visible(self, timeout_ms: int = 10_000) -> None:
        """Wait until the reader panel is visible."""
        self.wait_visible("[data-test='reader-panel']", timeout_ms=timeout_ms)

    # ── Project card selection ────────────────────────────────────────────────

    def click_project_card(self, project_name: str) -> None:
        """Click the project card whose title contains *project_name*.

        Waits for the sidebar nav to become visible, confirming the expanded
        panel opened before returning.
        """
        self.page.locator("[data-test='project-card']", has_text=project_name).first.click()
        self.wait_visible("[data-test='sidebar-nav']", timeout_ms=30_000)

    # ── Sidebar file list ─────────────────────────────────────────────────────

    def is_sidebar_nav_visible(self, timeout_ms: int = 5_000) -> bool:
        """Return True if the sidebar file navigation element is visible."""
        return self.is_visible("[data-test='sidebar-nav']", timeout_ms=timeout_ms)

    def get_sidebar_file_labels(self) -> list[str]:
        """Return the label text of every sidebar file entry in DOM order.

        Returns lower-case stripped strings so callers can compare without
        worrying about capitalisation.
        """
        buttons = self.page.locator("[data-test='sidebar-file']").all()
        return [b.inner_text().strip().lower() for b in buttons]

    def click_sidebar_file(self, label: str) -> None:
        """Click the sidebar file entry whose label contains *label*.

        Matches case-insensitively so callers can pass partial labels such as
        "analysis" without knowing the exact capitalisation the UI uses.
        After clicking, waits for the clicked button to have the 'active' CSS
        class so callers can immediately assert on the active state.
        """
        import re as _re
        from playwright.sync_api import expect as _expect

        buttons = self.page.locator("[data-test='sidebar-file']").all()
        for btn in buttons:
            if label.lower() in btn.inner_text().strip().lower():
                btn.click()
                # Wait for Angular to apply the .active class to this button.
                # The class attribute is e.g. "sidebar-file active" or just
                # "sidebar-file" when not active.
                _expect(btn).to_have_class(_re.compile(r"\bactive\b"), timeout=5_000)
                return
        raise ValueError(f"No sidebar file entry found containing label {label!r}")

    def get_active_sidebar_file(self, timeout_ms: int = 5_000) -> str:
        """Return the label of the currently active (selected) sidebar file.

        Waits up to *timeout_ms* for at least one sidebar file to carry the
        active CSS class before reading its label.
        """
        active = self.page.locator("[data-test='sidebar-file'].active")
        active.first.wait_for(state="visible", timeout=timeout_ms)
        return active.first.inner_text().strip().lower()

    def count_sidebar_files(self) -> int:
        """Return the total number of file entries in the sidebar nav."""
        return self.page.locator("[data-test='sidebar-file']").count()

    # ── Reader content area ───────────────────────────────────────────────────

    def get_reader_title(self) -> str:
        """Return the text of the expanded panel title heading."""
        return self.page.locator("[data-test='reader-title']").inner_text().strip()

    def get_reader_content_html(self) -> str:
        """Return the raw inner HTML of the markdown content area."""
        return self.page.locator("[data-test='reader-content']").inner_html()

    def get_reader_content_text(self) -> str:
        """Return the visible text of the markdown content area."""
        return self.page.locator("[data-test='reader-content']").inner_text().strip()

    def is_reader_content_visible(self, timeout_ms: int = 10_000) -> bool:
        """Return True if the markdown content div is visible."""
        return self.is_visible("[data-test='reader-content']", timeout_ms=timeout_ms)

    def wait_reader_content_visible(self, timeout_ms: int = 10_000) -> None:
        """Wait until the reader content area is visible."""
        self.wait_visible("[data-test='reader-content']", timeout_ms=timeout_ms)

    def reader_content_contains(self, text: str) -> bool:
        """Return True if the reader content area contains *text* (case-insensitive)."""
        content = self.get_reader_content_text()
        return text.lower() in content.lower()

    def reader_content_has_heading(self) -> bool:
        """Return True if the reader content contains at least one HTML heading tag."""
        html = self.get_reader_content_html()
        return bool(re.search(r"<h[1-6]", html, re.IGNORECASE))

    def reader_content_has_no_script_tags(self) -> bool:
        """Return True if the reader content HTML contains no <script> tags.

        DOMPurify strips <script> tags from the innerHTML — this method asserts
        that the sanitisation worked.
        """
        html = self.get_reader_content_html()
        return "<script" not in html.lower()

    # ── Sidebar status row ────────────────────────────────────────────────────

    def get_sidebar_status_text(self) -> str:
        """Return the visible text of the sidebar status row.

        Normalises whitespace so assertions are layout-independent.
        """
        raw = self.page.locator("[data-test='sidebar-status']").inner_text()
        return re.sub(r"\s+", " ", raw).strip()

    def is_sidebar_status_visible(self, timeout_ms: int = 5_000) -> bool:
        """Return True if the sidebar status element is visible."""
        return self.is_visible("[data-test='sidebar-status']", timeout_ms=timeout_ms)

    def get_sidebar_status_mode(self) -> str:
        """Return the active CSS modifier on the sidebar status element.

        Returns one of: 'active', 'success-flash', 'failure', or 'default'.
        """
        classes = (
            self.page.locator("[data-test='sidebar-status']").get_attribute("class") or ""
        )
        if "sidebar-status--active" in classes:
            return "active"
        if "sidebar-status--success" in classes:
            return "success-flash"
        if "sidebar-status--failure" in classes:
            return "failure"
        return "default"

    # ── Spec-gen pipeline triggers ────────────────────────────────────────────

    def click_generate_specs(self, timeout_ms: int = 5_000) -> None:
        """Click the Generate Specs button in the sidebar.

        Waits for the button to be visible before clicking.  The button is
        only rendered when canGenerateSpecs is true (braindump-only project).
        """
        self.wait_visible("[data-test='pipeline-trigger']", timeout_ms=timeout_ms)
        self.page.locator("[data-test='pipeline-trigger']").click()

    def click_generate_guide(self, timeout_ms: int = 5_000) -> None:
        """Click the Generate Guide button in the sidebar.

        Only rendered when canGenerateEpicGuide is true (full-spec project).
        """
        self.wait_visible("[data-test='epic-guide-trigger']", timeout_ms=timeout_ms)
        self.page.locator("[data-test='epic-guide-trigger']").click()

    def is_generate_specs_loading(self) -> bool:
        """Return True if the Generate Specs button is in a loading/disabled state."""
        btn = self.page.locator("[data-test='pipeline-trigger']")
        return btn.is_disabled()

    def is_generate_guide_loading(self) -> bool:
        """Return True if the Generate Guide button is in a loading/disabled state."""
        btn = self.page.locator("[data-test='epic-guide-trigger']")
        return btn.is_disabled()

    # ── AI operation chips ────────────────────────────────────────────────────

    def is_sidebar_ops_visible(self, timeout_ms: int = 5_000) -> bool:
        """Return True if the AI op chips section is visible."""
        return self.is_visible("[data-test='sidebar-ops']", timeout_ms=timeout_ms)

    def get_ai_op_chip_labels(self) -> list[str]:
        """Return the label text of all AI op chip buttons."""
        chips = self.page.locator("[data-test='ai-op-chip']").all()
        return [c.inner_text().strip() for c in chips]

    def click_ai_op_chip(self, label: str) -> None:
        """Click the AI op chip whose label contains *label* (case-insensitive)."""
        chips = self.page.locator("[data-test='ai-op-chip']").all()
        for chip in chips:
            if label.lower() in chip.inner_text().strip().lower():
                chip.click()
                return
        raise ValueError(f"No AI op chip found containing label {label!r}")

    def is_ai_op_chip_active(self, label: str) -> bool:
        """Return True if the AI op chip for *label* has the active CSS class."""
        chips = self.page.locator("[data-test='ai-op-chip']").all()
        for chip in chips:
            if label.lower() in chip.inner_text().strip().lower():
                classes = chip.get_attribute("class") or ""
                return "active" in classes
        return False

    # ── Style preset chips ────────────────────────────────────────────────────

    def is_style_presets_visible(self, timeout_ms: int = 5_000) -> bool:
        """Return True if the style preset chip panel is visible."""
        return self.is_visible("[data-test='style-presets']", timeout_ms=timeout_ms)

    def get_style_chip_labels(self) -> list[str]:
        """Return the label text of all style preset chips."""
        chips = self.page.locator("[data-test='style-chip']").all()
        return [c.inner_text().strip() for c in chips]

    def click_style_chip(self, label: str) -> None:
        """Click the style chip whose label contains *label*."""
        chips = self.page.locator("[data-test='style-chip']").all()
        for chip in chips:
            if label.lower() in chip.inner_text().strip().lower():
                chip.click()
                return
        raise ValueError(f"No style chip found containing label {label!r}")

    # ── Result panel / diff view ──────────────────────────────────────────────

    def is_result_toolbar_visible(self, timeout_ms: int = 10_000) -> bool:
        """Return True if the floating result toolbar is visible."""
        return self.is_visible("[data-test='result-toolbar']", timeout_ms=timeout_ms)

    def is_diff_view_visible(self, timeout_ms: int = 10_000) -> bool:
        """Return True if the unified diff view panel is visible."""
        return self.is_visible("[data-test='diff-view']", timeout_ms=timeout_ms)

    def get_diff_view_text(self) -> str:
        """Return the visible text of the diff view panel."""
        return self.page.locator("[data-test='diff-view']").inner_text().strip()

    def click_apply_result(self) -> None:
        """Click the Apply button in the floating result toolbar."""
        self.page.locator("[data-test='apply-button']").click()

    def click_copy_result(self) -> None:
        """Click the Copy button in the floating result toolbar."""
        self.page.locator("[data-test='copy-button']").click()

    def click_dismiss_result(self) -> None:
        """Click the Dismiss (×) button in the floating result toolbar."""
        self.page.locator("[data-test='dismiss-button']").click()

    # ── Undo / redo ───────────────────────────────────────────────────────────

    def is_undo_button_visible(self, timeout_ms: int = 5_000) -> bool:
        """Return True if the Undo chip is visible in the sidebar."""
        return self.is_visible("[data-test='undo-button']", timeout_ms=timeout_ms)

    def is_redo_button_visible(self, timeout_ms: int = 5_000) -> bool:
        """Return True if the Redo chip is visible in the sidebar."""
        return self.is_visible("[data-test='redo-button']", timeout_ms=timeout_ms)

    def click_undo(self) -> None:
        """Click the Undo chip in the sidebar."""
        self.page.locator("[data-test='undo-button']").click()

    def click_redo(self) -> None:
        """Click the Redo chip in the sidebar."""
        self.page.locator("[data-test='redo-button']").click()

    # ── Brainstorm follow-up input ────────────────────────────────────────────

    def is_brainstorm_followup_visible(self, timeout_ms: int = 10_000) -> bool:
        """Return True if the brainstorm follow-up input row is visible."""
        return self.is_visible("[data-test='brainstorm-followup-input']", timeout_ms=timeout_ms)

    def type_brainstorm_followup(self, text: str) -> None:
        """Type *text* into the brainstorm follow-up input field."""
        self.wait_visible("[data-test='brainstorm-followup-input']", timeout_ms=10_000)
        self.page.locator("[data-test='brainstorm-followup-input']").fill(text)

    def click_brainstorm_followup_submit(self) -> None:
        """Click the follow-up submit (↵) button."""
        self.page.locator("[data-test='brainstorm-followup-btn']").click()

    def is_brainstorm_result_visible(self, timeout_ms: int = 15_000) -> bool:
        """Return True if the brainstorm result panel is visible."""
        return self.is_visible("[data-test='brainstorm-result']", timeout_ms=timeout_ms)

    def is_brainstorm_generate_btn_visible(self, timeout_ms: int = 5_000) -> bool:
        """Return True if the 'Generate Specs from this brainstorm' button is visible."""
        return self.is_visible("[data-test='brainstorm-generate-btn']", timeout_ms=timeout_ms)

    def click_brainstorm_generate(self) -> None:
        """Click 'Generate Specs from this brainstorm' button."""
        self.wait_visible("[data-test='brainstorm-generate-btn']", timeout_ms=10_000)
        self.page.locator("[data-test='brainstorm-generate-btn']").click()

    # ── Per-file dot indicators ───────────────────────────────────────────────

    def get_file_dot_state(self, filename_label: str) -> str | None:
        """Return the state of the dot indicator for the sidebar file whose label
        contains *filename_label*, or None if no dot indicator is visible.

        States: 'running', 'success', 'failure'.
        The dot indicator carries a data-state attribute set by the Angular template.
        """
        buttons = self.page.locator("[data-test='sidebar-file']").all()
        for btn in buttons:
            if filename_label.lower() in btn.inner_text().strip().lower():
                dot = btn.locator("[data-test='file-dot']")
                if dot.count() == 0:
                    return None
                return dot.first.get_attribute("data-state")
        raise ValueError(f"No sidebar file entry found containing label {filename_label!r}")

    def has_file_dot(self, filename_label: str) -> bool:
        """Return True if the sidebar file entry for *filename_label* has a dot indicator."""
        return self.get_file_dot_state(filename_label) is not None

    # ── Auth helpers (shared with overview) ───────────────────────────────────

    def inject_jwt(self, token: str) -> None:
        """Write a JWT into localStorage so the Angular auth service picks it up."""
        self.page.evaluate(
            f"() => localStorage.setItem('specview_jwt', {token!r})"
        )

    def clear_auth(self) -> None:
        """Remove all auth tokens from localStorage."""
        self.page.evaluate("() => localStorage.removeItem('specview_jwt')")
