"""Page object for the Specview Angular SPA."""
from __future__ import annotations

from playwright.sync_api import Page, expect


class AppPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

    def load(self) -> None:
        self.page.goto(self.base_url)
        self.page.wait_for_load_state("networkidle")

    def enter_text(self, selector: str, text: str) -> None:
        self.page.fill(selector, text)

    def click(self, selector: str) -> None:
        self.page.click(selector)

    def is_visible(self, selector: str, timeout_ms: int = 5_000) -> bool:
        try:
            self.page.wait_for_selector(selector, timeout=timeout_ms, state="visible")
            return True
        except Exception:
            return False

    def wait_visible(self, selector: str, timeout_ms: int = 30_000) -> None:
        self.page.wait_for_selector(selector, timeout=timeout_ms, state="visible")

    def submit_brainstorm(self, text: str = "test input for brainstorm") -> None:
        self.enter_text("[data-test='braindump-input']", text)
        self.click("[data-test='brainstorm-button']")
