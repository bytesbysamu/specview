"""When/Then step definitions for all project-detail feature files.

All browser interaction is routed through DetailPage — no direct Playwright
or raw selector strings appear in this file.
"""
from __future__ import annotations

import os

import pytest
from pytest_bdd import when, then, parsers
from playwright.sync_api import Page

from e2e.pages.detail_page import DetailPage, CANONICAL_FILE_ORDER

_SKIP_MOCK = os.environ.get("E2E_SKIP_MOCK_SCENARIOS", "1") == "1"


# ── Navigation / panel opening ─────────────────────────────────────────────────


@when("the user clicks on the project card")
def click_project_card(page: Page, angular_server: str, context: dict) -> None:
    """Click the seeded project card to open the expanded reader panel."""
    project = context.get("detail_project")
    if project is None:
        pytest.fail("context['detail_project'] not set — run a seeding Given step first")

    detail: DetailPage = context["detail"]
    detail.click_project_card(project["name"])


# ── Reader panel assertions ────────────────────────────────────────────────────


@then("the expanded reader panel is visible")
def reader_panel_visible(context: dict) -> None:
    """Assert that the expanded reader panel container is visible."""
    detail: DetailPage = context["detail"]
    assert detail.is_reader_panel_visible(timeout_ms=15_000), (
        "Expected the expanded reader panel to be visible after clicking a project card"
    )


@then("the reader content area renders formatted markdown")
def reader_content_renders_markdown(context: dict) -> None:
    """Assert that the reader content area has rendered at least one HTML heading.

    The Angular app passes spec file markdown through the `marked` library and
    injects it as sanitised innerHTML.  A heading in the rendered HTML is the
    simplest indicator that markdown rendering ran successfully.
    """
    detail: DetailPage = context["detail"]
    detail.wait_reader_content_visible(timeout_ms=10_000)
    assert detail.reader_content_has_heading(), (
        "Expected the reader content to contain at least one HTML heading tag "
        "— markdown does not appear to have been rendered"
    )


@then("the reader content contains no script tags")
def reader_content_no_script_tags(context: dict) -> None:
    """Assert that DOMPurify stripped any <script> tags from the rendered HTML."""
    detail: DetailPage = context["detail"]
    detail.wait_reader_content_visible(timeout_ms=10_000)
    assert detail.reader_content_has_no_script_tags(), (
        "Expected <script> tags to be stripped from reader content by DOMPurify, "
        "but a <script> tag was found in the rendered HTML"
    )


@then("the reader panel displays the analysis file content")
def reader_displays_analysis(context: dict) -> None:
    """Assert that the reader content area shows content from the analysis file.

    The analysis seed file starts with '# Analysis' so we verify the word
    'Analysis' appears in the rendered text.
    """
    detail: DetailPage = context["detail"]
    detail.wait_reader_content_visible(timeout_ms=10_000)
    assert detail.reader_content_contains("analysis"), (
        "Expected the reader content to include 'analysis' after clicking the "
        "analysis sidebar entry"
    )


# ── Sidebar file list assertions ───────────────────────────────────────────────


@then("the sidebar file list shows files in canonical order")
def sidebar_files_canonical_order(context: dict) -> None:
    """Assert that sidebar file labels appear in the canonical spec order.

    Canonical order: braindump, analysis, epic, architecture, timeline,
    implementation guide.  The check is positional — earlier canonical items
    must appear before later ones.  Extra files or label abbreviations are
    tolerated as long as the relative order is preserved.
    """
    detail: DetailPage = context["detail"]
    labels = detail.get_sidebar_file_labels()
    assert len(labels) > 0, "Expected at least one sidebar file entry, got none"

    # Build a filtered list of canonical names that appear in the sidebar labels
    present = [
        name for name in CANONICAL_FILE_ORDER
        if any(name in label for label in labels)
    ]

    # Verify position in labels list preserves canonical order
    for i, name_a in enumerate(present):
        for name_b in present[i + 1:]:
            pos_a = next(idx for idx, lbl in enumerate(labels) if name_a in lbl)
            pos_b = next(idx for idx, lbl in enumerate(labels) if name_b in lbl)
            assert pos_a < pos_b, (
                f"Expected '{name_a}' to appear before '{name_b}' in the sidebar, "
                f"but got order: {labels}"
            )


@when(parsers.parse('the user clicks the "{label}" sidebar file'))
def click_sidebar_file(context: dict, label: str) -> None:
    """Click the sidebar file entry whose label contains *label*."""
    detail: DetailPage = context["detail"]
    detail.click_sidebar_file(label)


@then(parsers.parse('the "{label}" sidebar file entry is marked as active'))
def sidebar_file_active(context: dict, label: str) -> None:
    """Assert that the sidebar file entry for *label* carries the active CSS class."""
    detail: DetailPage = context["detail"]
    active = detail.get_active_sidebar_file()
    assert label.lower() in active.lower(), (
        f"Expected '{label}' to be the active sidebar file, but active was: {active!r}"
    )


# ── Spec-gen pipeline steps ────────────────────────────────────────────────────


@when("the user clicks the Generate Specs button")
def click_generate_specs(context: dict) -> None:
    """Click the Generate Specs pipeline trigger button."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_generate_specs()


@when("the user clicks the Generate Guide button")
def click_generate_guide(context: dict) -> None:
    """Click the Generate Guide (epic guide) button."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_generate_guide()


@then("the Generate Specs button enters a loading state")
def generate_specs_loading_state(context: dict) -> None:
    """Assert that the Generate Specs button becomes disabled after clicking."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_generate_specs_loading(), (
        "Expected the Generate Specs button to be disabled after triggering pipeline"
    )


@then("the Generate Guide button enters a loading state")
def generate_guide_loading_state(context: dict) -> None:
    """Assert that the Generate Guide button becomes disabled after clicking."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_generate_guide_loading(), (
        "Expected the Generate Guide button to be disabled after triggering guide generation"
    )


@then("the sidebar status row transitions to active mode")
def sidebar_status_active_mode(context: dict) -> None:
    """Assert that the sidebar status row enters the 'active' (running) mode."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    # Poll briefly for the active mode — the mock provider responds quickly
    import time as _time
    deadline = _time.monotonic() + 10
    while _time.monotonic() < deadline:
        mode = detail.get_sidebar_status_mode()
        if mode == "active":
            return
        _time.sleep(0.3)
    mode = detail.get_sidebar_status_mode()
    assert mode == "active", (
        f"Expected sidebar status to enter 'active' mode after triggering pipeline, "
        f"but mode is: {mode!r}"
    )


@then("the spec generation pipeline completes successfully")
def pipeline_completes(context: dict) -> None:
    """Assert that the pipeline eventually reaches the success-flash state."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    import time as _time
    deadline = _time.monotonic() + 60
    while _time.monotonic() < deadline:
        mode = detail.get_sidebar_status_mode()
        if mode == "success-flash":
            return
        if mode == "failure":
            msg = detail.get_sidebar_status_text()
            pytest.fail(f"Pipeline failed during E2E test: {msg!r}")
        _time.sleep(0.5)
    pytest.fail("Pipeline did not complete within 60 seconds")


@then("the sidebar file list is updated with generated files")
def sidebar_files_updated(context: dict) -> None:
    """Assert that the sidebar file list contains more than just the braindump."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    labels = detail.get_sidebar_file_labels()
    assert len(labels) > 1, (
        f"Expected more than one sidebar file after pipeline completion, got: {labels!r}"
    )


# ── Per-file dot indicator steps ───────────────────────────────────────────────


@then(parsers.parse('the "{filename}" file has a dot indicator'))
def file_has_dot(context: dict, filename: str) -> None:
    """Assert that the sidebar entry for *filename* has a dot state indicator."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.has_file_dot(filename), (
        f"Expected sidebar file '{filename}' to have a dot indicator, but none was present"
    )


@then("each generated file shows a dot indicator during generation")
def generated_files_show_dots(context: dict) -> None:
    """Assert that at least one sidebar file has an active dot indicator."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    labels = detail.get_sidebar_file_labels()
    found = any(detail.has_file_dot(label) for label in labels)
    assert found, (
        "Expected at least one sidebar file to show a dot indicator during generation, "
        f"but none found. Labels: {labels!r}"
    )


# ── AI op chip steps ───────────────────────────────────────────────────────────


@then("the AI operation chips are visible in the sidebar")
def ai_op_chips_visible(context: dict) -> None:
    """Assert that the AI op chips section is rendered."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_sidebar_ops_visible(timeout_ms=10_000), (
        "Expected the AI operation chips panel to be visible when a spec file is open"
    )


@then("the AI operation chips panel contains multiple chips")
def ai_op_chips_multiple(context: dict) -> None:
    """Assert that more than one AI op chip is rendered."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    labels = detail.get_ai_op_chip_labels()
    assert len(labels) > 1, (
        f"Expected multiple AI op chips, but got: {labels!r}"
    )


@when(parsers.parse('the user toggles the "{chip}" AI op chip'))
def toggle_ai_op_chip(context: dict, chip: str) -> None:
    """Click an AI op chip to toggle it on."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_ai_op_chip(chip)


@then(parsers.parse('the "{chip}" AI op chip is active'))
def ai_op_chip_active(context: dict, chip: str) -> None:
    """Assert that the named AI op chip has the active CSS class."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_ai_op_chip_active(chip), (
        f"Expected AI op chip '{chip}' to be active after toggling"
    )


# ── Style preset chip steps ────────────────────────────────────────────────────


@then("the style preset chips are visible")
def style_chips_visible(context: dict) -> None:
    """Assert that the style preset chip panel is rendered."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_style_presets_visible(timeout_ms=10_000), (
        "Expected the style preset chips to be visible after selecting Style op"
    )


@then("the style preset chips panel contains multiple presets")
def style_chips_multiple(context: dict) -> None:
    """Assert that multiple style preset chips are rendered."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    labels = detail.get_style_chip_labels()
    assert len(labels) > 1, (
        f"Expected multiple style preset chips, but got: {labels!r}"
    )


@when(parsers.parse('the user selects the "{preset}" style preset'))
def select_style_preset(context: dict, preset: str) -> None:
    """Click a style preset chip."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_style_chip(preset)


# ── Result panel / toolbar steps ───────────────────────────────────────────────


@then("the result panel shows a diff view")
def result_panel_shows_diff(context: dict) -> None:
    """Assert that the diff view panel is visible in the result panel."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_diff_view_visible(timeout_ms=15_000), (
        "Expected the diff view to be visible in the result panel"
    )


@then("the floating result toolbar is visible")
def result_toolbar_visible(context: dict) -> None:
    """Assert that the floating Apply/Copy/Dismiss toolbar is visible."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_result_toolbar_visible(timeout_ms=15_000), (
        "Expected the floating result toolbar to be visible when an AI result is active"
    )


@when("the user clicks the Apply button in the result toolbar")
def click_apply_button(context: dict) -> None:
    """Click the Apply button to accept the AI result."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_apply_result()


@when("the user clicks the Copy button in the result toolbar")
def click_copy_button(context: dict) -> None:
    """Click the Copy button in the floating toolbar."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_copy_result()


@when("the user clicks the Dismiss button in the result toolbar")
def click_dismiss_button(context: dict) -> None:
    """Click the Dismiss (×) button in the floating toolbar."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_dismiss_result()


@then("the result toolbar disappears")
def result_toolbar_gone(context: dict) -> None:
    """Assert that the floating result toolbar is no longer visible."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert not detail.is_result_toolbar_visible(timeout_ms=5_000), (
        "Expected the result toolbar to disappear after dismissing the result"
    )


@then("the reader content is updated with the applied result")
def reader_content_updated(context: dict) -> None:
    """Assert that the reader content area was updated after applying a result."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.wait_reader_content_visible(timeout_ms=10_000)
    assert detail.reader_content_has_heading(), (
        "Expected reader content to show updated content with headings after applying result"
    )


# ── Undo / redo steps ──────────────────────────────────────────────────────────


@then("the undo button is visible in the sidebar")
def undo_button_visible(context: dict) -> None:
    """Assert that the Undo chip is visible in the sidebar op chips."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_undo_button_visible(timeout_ms=10_000), (
        "Expected the Undo button to be visible after applying an AI result"
    )


@when("the user clicks the Undo button")
def click_undo_button(context: dict) -> None:
    """Click the Undo chip in the sidebar."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_undo()


@then("the redo button becomes visible in the sidebar")
def redo_button_visible(context: dict) -> None:
    """Assert that the Redo chip appears after an undo action."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_redo_button_visible(timeout_ms=10_000), (
        "Expected the Redo button to appear after performing an Undo action"
    )


@then("the reader content reverts to its previous state")
def reader_content_reverted(context: dict) -> None:
    """Assert that the reader content area contains content (after undo)."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.wait_reader_content_visible(timeout_ms=10_000)
    assert detail.reader_content_has_heading(), (
        "Expected reader content to show heading text after reverting to previous state"
    )


# ── Brainstorm follow-up steps ─────────────────────────────────────────────────


@then("the brainstorm follow-up input is visible")
def brainstorm_followup_input_visible(context: dict) -> None:
    """Assert that the brainstorm follow-up input field is visible."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_brainstorm_followup_visible(timeout_ms=15_000), (
        "Expected the brainstorm follow-up input to be visible after a brainstorm result"
    )


@when(parsers.parse('the user types "{text}" in the brainstorm follow-up input'))
def type_brainstorm_followup(context: dict, text: str) -> None:
    """Type a follow-up question into the brainstorm follow-up input."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.type_brainstorm_followup(text)


@when("the user submits the brainstorm follow-up")
def submit_brainstorm_followup(context: dict) -> None:
    """Click the follow-up submit button."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_brainstorm_followup_submit()


@then("the brainstorm result panel updates with the follow-up answer")
def brainstorm_result_updated(context: dict) -> None:
    """Assert that the brainstorm result area is visible and has content."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_brainstorm_result_visible(timeout_ms=15_000), (
        "Expected the brainstorm result panel to be visible after follow-up submission"
    )


@then("the Generate Specs from brainstorm button is visible")
def brainstorm_generate_btn_visible(context: dict) -> None:
    """Assert the 'Generate Specs from this brainstorm' button is visible."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    assert detail.is_brainstorm_generate_btn_visible(timeout_ms=10_000), (
        "Expected 'Generate Specs from this brainstorm' button to be visible after brainstorm result"
    )


@when("the user clicks Generate Specs from the brainstorm result")
def click_brainstorm_generate_specs(context: dict) -> None:
    """Click the 'Generate Specs from this brainstorm' button."""
    if _SKIP_MOCK:
        pytest.skip("Requires CHAIN_PROVIDER=mock — skipping against Docker stack")
    detail: DetailPage = context["detail"]
    detail.click_brainstorm_generate()


# ── Sidebar status row assertions ──────────────────────────────────────────────


@then("the sidebar status row displays a connection state")
def sidebar_status_shows_connection(context: dict) -> None:
    """Assert that the sidebar status row displays any recognisable connection state.

    In the default (idle) state the sidebar status shows 'connected'. This step
    does not assert the specific mode because the test server may or may not be
    actively generating — it simply checks that the status row is rendered and
    contains visible text.
    """
    detail: DetailPage = context["detail"]
    assert detail.is_sidebar_status_visible(timeout_ms=5_000), (
        "Expected sidebar status row to be visible"
    )
    status_text = detail.get_sidebar_status_text()
    # Any non-empty text counts — the row shows 'connected', a step name, or 'done'
    assert len(status_text) > 0, (
        f"Expected sidebar status row to contain visible text, got empty string"
    )
