# Task 2: Page Objects + Shared Fixture — Implementation Guide

## 1. Context

Task 2 builds the stable foundation that every subsequent step-definition module in the E2E2 epic imports and depends on. It delivers four page object classes — one per retrofitted component — each acting as an anti-corruption layer between test intent and DOM structure, and a single `e2e/conftest.py` that encodes the server strategy chosen in Task 1 (real Angular + Express, AI mocked at the Express middleware via `AI_PROVIDER=mock`). Nothing in Task 3 can be written without this fixture contract in place: the conftest is the multiplier the architecture identifies — lock it in once, and every new feature file is incremental rather than a bespoke integration.

**Trade-offs considered:**

- **Shared base `PageObject` class** — rejected because all four classes have distinct method sets and exactly one named consumer each; extraction before two consumers calibrate the shape produces a base class that the first real shared-method pull is likely to invalidate.
- **Function-scoped server fixture** — rejected because Angular dev-server startup is 30–90s; amortising across the session keeps the full-suite runtime acceptable; test-data isolation is achieved per-scenario through project-directory creation, not restarts.
- **Real servers + `AI_PROVIDER=mock` env flag** — preferred because the bootstrap and edit-spec flows require real filesystem writes through Express; mocking at the Angular service layer would bypass HTTP serialisation and response-mapping, which are exactly the paths most likely to break when the AI envelope changes.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
# From the spec-doc workspace root
git status                               # Confirm clean working tree
git diff HEAD                            # Zero uncommitted changes on target files

# Verify AI_PROVIDER=mock is a live code path in server.js
grep -n "mock" spec-doc/server.js        # Expect: mockProvider branch visible

# Baseline test count (backend tests, if any currently pass)
cd spec-doc && npm test 2>&1 | tail -5   # Record pass count before changes

# Verify playwright and pytest-bdd are installable
python3 -m pip install playwright pytest-bdd --dry-run 2>&1 | tail -3

# Selector audit — run this BEFORE writing any page object method body
grep -rn 'data-test' spec-doc/src/app/components/editor/ \
         spec-doc/src/app/components/preview/ \
         spec-doc/src/app/components/operation-bar/ \
         spec-doc/src/app/components/sidebar/
# Record ALL values found. Table in Step 1 shows expected names;
# any mismatch → update the method, never add the attribute (out of scope).
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, before starting.

**Baseline recorded**: \_\_/\_\_ passing (fill in before editing).

---

## 3. Files

### To Create (new)

- `spec-doc/e2e/conftest.py` — session-scoped server fixture + per-scenario Playwright page fixture; the single import contract for all step-definition modules
- `spec-doc/e2e/pytest.ini` — pytest root + asyncio mode; keeps test discovery scoped to `e2e/`
- `spec-doc/e2e/requirements-e2e.txt` — isolated install list for E2E toolchain; never merged into project `package.json`
- `spec-doc/e2e/pages/__init__.py` — re-exports all four page object classes; step definitions import from `pages` not individual files
- `e2e/pages/new_project_page.py` — `NewProjectPage`; consumer: bootstrap-happy + bootstrap-fail-fast (Task 3). Available selectors: `new-project-modal`, `project-name-input`, `bootstrap-trigger`.
- `e2e/pages/operation_bar_page.py` — `OperationBarPage`; consumer: rewrite-operation (Task 3). Available selectors: `rewrite-btn`, `expand-btn`, `compress-btn`, `clarify-btn`, `generate-btn`.
- `e2e/pages/sidebar_page.py` — `SidebarPage`; consumer: bootstrap, edit-spec, context-editor (Task 3). Available selectors: `new-project-toggle`, `project-list`, plus dynamic `[attr.data-test]="'project-item-' + project.name"` per project.
- `e2e/pages/output_panel_page.py` — `OutputPanelPage`; consumer: rewrite-operation result verification (Task 3). Available selectors: `output-panel`, `output-content`.
- `spec-doc/e2e/test_smoke.py` — fixture contract smoke tests; 9 assertions, zero step definitions

### To Modify (cite CODEBASE CONTEXT)

- `spec-doc/.gitignore` — add `e2e/__pycache__/`, `e2e/.pytest_cache/`, `e2e/htmlcov/` (if the file already exists; if absent, create a minimal one)

### To Leave Alone

- `spec-doc/server.js` — the Express server; executor must NOT modify it; AI mock behaviour is activated purely via `AI_PROVIDER=mock` env injection in the fixture
- `spec-doc/src/app/components/*` — Angular component templates; missing `[data-test]` attributes are pre-existing gaps, not Task 2 defects; executor must NOT add attributes
- `spec-doc/package.json` / `spec-doc/angular.json` — frontend tooling config; not touched by this task

---

## 4. Implementation Steps

### Step 0: Selector Audit (discovery — no commit)

**Action**: Grep all four component templates for existing `[data-test]` values. Record the table below, filling in the **Actual** column. Any **Expected** value absent from **Actual** is a pre-existing gap: mark the corresponding page-object method with a `# SKIP` comment and a `return None` body stub (not an assertion) so Task 3 step definitions can detect and document the gap.

**File**: `spec-doc/src/app/components/` (read only)

**Pattern**:
```bash
grep -rn 'data-test' src/app/components/{new-project,operation-bar,sidebar,output-panel}/ --include="*.ts"
```

**Confirmed selector inventory** (already retrofitted in E2E-foundation Task 2; do NOT add more, do NOT target editor/preview which were never retrofitted):

| Component | `data-test` value | Where in template |
|---|---|---|
| new-project | `new-project-modal` | modal root div |
| new-project | `project-name-input` | text input |
| new-project | `bootstrap-trigger` | submit button |
| operation-bar | `rewrite-btn` | rewrite button |
| operation-bar | `expand-btn` | expand button |
| operation-bar | `compress-btn` | compress button |
| operation-bar | `clarify-btn` | clarify button |
| operation-bar | `generate-btn` | generate button |
| sidebar | `new-project-toggle` | "+ New Capability" button |
| sidebar | `project-list` | nav.sidebar-nav |
| sidebar | `project-item-{name}` | per-project div via `[attr.data-test]` |
| output-panel | `output-panel` | panel root |
| output-panel | `output-content` | content area |

**Verify**: Table is fully populated. Proceed to Step 1 only after all Actual values are known.

---

### Step 1: Scaffold `e2e/` directory, `pytest.ini`, and `requirements-e2e.txt`

**Action**: Create the directory structure and administrative files. Do not install dependencies yet.

**File**: `spec-doc/e2e/requirements-e2e.txt` (new)

**Pattern**:
```
pytest>=8.1
pytest-bdd>=7.2
playwright>=1.44
```

**File**: `spec-doc/e2e/pytest.ini` (new)

**Pattern**:
```ini
[pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**File**: `spec-doc/.gitignore` (modify — append if file exists, create if not)

**Pattern** — append these lines:
```
# E2E test artefacts
e2e/__pycache__/
e2e/.pytest_cache/
e2e/pages/__pycache__/
```

**Verify**:
```bash
ls spec-doc/e2e/                            # Expect: requirements-e2e.txt, pytest.ini
pip install -r spec-doc/e2e/requirements-e2e.txt
playwright install chromium                  # Downloads Chromium binaries
python -c "from playwright.sync_api import sync_playwright; print('ok')"
```
Expect: `ok` with no import error.

---

### Step 2: Write `e2e/conftest.py` — server fixtures + Playwright page fixture

**Action**: Write the session-scoped server fixture and the per-scenario Playwright page fixture. This file is the **single contract** all Task 3 step-definition modules import. Do not add any BDD-specific imports; conftest must stay framework-agnostic.

**File**: `spec-doc/e2e/conftest.py` (new)

**Pattern** (port shape from spec-doc `server.js` env-flag strategy; confirmed by `AI_PROVIDER` pattern in spec-doc CLAUDE.md):

```python
"""
e2e/conftest.py — Shared fixture contract for all E2E2 step-definition modules.

Server strategy (Task 1 decision):
  - Express API:  http://localhost:3100  (AI_PROVIDER=mock, started via `npm run api`)
  - Angular app:  http://localhost:4201  (started via `npm start`)
  - AI responses: deterministic mock; no API key required in CI

Session scope: servers start once per pytest session, shared across all scenarios.
Function scope: one Playwright page per scenario; browser closed after each.
"""
import os
import subprocess
import time
import urllib.request
import urllib.error

import pytest
from playwright.sync_api import sync_playwright, Browser, Page

FRONTEND_URL = "http://localhost:4201"
BACKEND_URL  = "http://localhost:3100"
# WORKSPACE resolves to the spec-doc project root regardless of cwd at invocation
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _wait_for(url: str, timeout_s: int = 90) -> None:
    """Poll url until any HTTP response arrives (including 4xx) or timeout elapses."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except urllib.error.HTTPError:
            return  # 4xx/5xx still means the process is listening
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    raise RuntimeError(
        f"Server at {url!r} did not respond within {timeout_s}s. "
        "Check that ports 3100 and 4201 are free before running e2e tests."
    )


@pytest.fixture(scope="session")
def servers():
    """
    Start Express API (AI_PROVIDER=mock) and Angular dev server.
    Yield the frontend base URL. Terminate both processes after the session.

    CI note: Angular dev-server takes 30–90s to compile on first run.
    The _wait_for timeout is set to 90s to accommodate this.
    Server-startup wiring in GitHub Actions (caching, concurrency) is Task 3.
    """
    mock_env = {**os.environ, "AI_PROVIDER": "mock"}

    backend = subprocess.Popen(
        ["npm", "run", "api"],
        cwd=WORKSPACE,
        env=mock_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    frontend = subprocess.Popen(
        ["npm", "start"],
        cwd=WORKSPACE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for(BACKEND_URL, timeout_s=30)
        _wait_for(FRONTEND_URL, timeout_s=90)
    except RuntimeError:
        backend.terminate()
        frontend.terminate()
        raise

    yield FRONTEND_URL

    backend.terminate()
    frontend.terminate()
    # Allow processes to flush before pytest exits
    backend.wait(timeout=5)
    frontend.wait(timeout=5)


@pytest.fixture(scope="function")
def page(servers):
    """
    Playwright page fixture — one per scenario.

    Navigates to the Angular app and waits for network idle before yielding.
    Browser instance is closed after each scenario to prevent state leakage.
    """
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=True)
        pg: Page = browser.new_page()
        pg.goto(servers, wait_until="networkidle")
        yield pg
        browser.close()
```

**Verify**:
```bash
cd spec-doc/e2e && python -c "import conftest; print('conftest imports cleanly')"
```
Expect: `conftest imports cleanly` with no import error.

---

### Step 3: Write `e2e/pages/new_project_page.py`

**Action**: Write `EditorPage`. Before coding method bodies, confirm the `[data-test]` values from the Step 0 audit table. Substitute any discovered actual value in place of the expected name. If a selector is absent, mark the method `# SKIP` and return `None` / `""` / `False`.

Monaco editor interaction note: Monaco renders its own internal DOM. The Angular wrapper's `[data-test="editor-container"]` div is the anchor. `get_content` accesses the Monaco model via `window.monaco` JavaScript API (most reliable); `set_content` focuses and types via keyboard to keep the Monaco model in sync.

**File**: `spec-doc/e2e/pages/editor_page.py` (new)

**Pattern**:

```python
"""EditorPage — anti-corruption layer over the Monaco editor wrapper component.

Selectors: [data-test] attributes only. Verified against:
  spec-doc/src/app/components/editor/editor.component.html  (Step 0 audit)

EXECUTOR: If data-test="editor-container" is absent from the template,
mark is_visible / get_content / set_content with # SKIP and return sentinel.
Do NOT add the attribute to the template (out of scope for Task 2).
"""
from __future__ import annotations
from playwright.sync_api import Page, Locator


class EditorPage:
    """Page object for the Monaco editor wrapper component.

    Consumers: edit-spec step definitions, rewrite-operation step definitions (Task 3).
    """

    _CONTAINER = '[data-test="editor-container"]'

    def __init__(self, page: Page) -> None:
        self._page = page
        self._container: Locator = page.locator(self._CONTAINER)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_visible(self) -> bool:
        """Return True if the editor container is attached and visible."""
        return self._container.is_visible()

    def get_content(self) -> str:
        """Return the current text content of the Monaco editor.

        Reads via window.monaco API rather than the hidden textarea value
        because Monaco may lazily sync the textarea on blur only.
        Falls back to empty string if the model is not yet initialised.
        """
        return self._page.evaluate(
            "() => (window.monaco?.editor?.getModels() ?? [])[0]?.getValue() ?? ''"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def set_content(self, text: str) -> None:
        """Replace the full editor content with text.

        Clicks the container to ensure Monaco is focused, then selects
        all existing text and types the replacement so the Monaco model
        is updated via keyboard events rather than direct DOM mutation.
        """
        self._container.click()
        self._page.keyboard.press("ControlOrMeta+a")
        self._page.keyboard.type(text)

    def focus(self) -> None:
        """Focus the Monaco editor without altering its content."""
        self._container.click()
```

**Verify**:
```bash
cd spec-doc/e2e && python -c "from pages.editor_page import EditorPage; print('EditorPage ok')"
```

---

### Step 4: Write `OperationBarPage`, `SidebarPage`, and `OutputPanelPage`

**Action**: Write the remaining three page objects. Apply the same selector-audit discipline as Step 3 for each `[data-test]` value before coding method bodies.

**File**: `spec-doc/e2e/pages/preview_page.py` (new)

**Pattern**:

```python
"""PreviewPage — anti-corruption layer over the marked.js preview component.

Selectors: [data-test] attributes only. Verified against:
  spec-doc/src/app/components/preview/preview.component.html  (Step 0 audit)
"""
from __future__ import annotations
from playwright.sync_api import Page, Locator


class PreviewPage:
    """Page object for the marked.js rendered preview component.

    Consumers: edit-spec step definitions, context-editor step definitions (Task 3).
    """

    _CONTAINER = '[data-test="preview-container"]'
    _CONTENT   = '[data-test="preview-content"]'

    def __init__(self, page: Page) -> None:
        self._page = page
        self._container: Locator = page.locator(self._CONTAINER)

    def is_visible(self) -> bool:
        """Return True if the preview container is attached and visible."""
        return self._container.is_visible()

    def get_text_content(self) -> str:
        """Return the plain text of the rendered markdown preview."""
        return self._page.locator(self._CONTENT).inner_text()

    def get_rendered_html(self) -> str:
        """Return the inner HTML of the rendered preview (for structural assertions)."""
        return self._page.locator(self._CONTENT).inner_html()

    def contains_heading(self, text: str) -> bool:
        """Return True if any heading element in the preview contains text."""
        return self._page.locator(f'{self._CONTENT} h1, {self._CONTENT} h2, '
                                  f'{self._CONTENT} h3').filter(has_text=text).count() > 0
```

**File**: `spec-doc/e2e/pages/operation_bar_page.py` (new)

**Pattern**:

```python
"""OperationBarPage — anti-corruption layer over the AI operation-bar component.

Selectors: [data-test] attributes only. Verified against:
  spec-doc/src/app/components/operation-bar/operation-bar.component.html  (Step 0 audit)

Operations exposed match the spec-doc CLAUDE.md AI Operations table:
  Rewrite, Expand, Compress, Clarify.
"""
from __future__ import annotations
from playwright.sync_api import Page, Locator


class OperationBarPage:
    """Page object for the AI rewrite/generate operation-bar component.

    Consumers: rewrite-operation step definitions, context-editor step definitions (Task 3).
    """

    _REWRITE  = '[data-test="op-rewrite"]'
    _EXPAND   = '[data-test="op-expand"]'
    _COMPRESS = '[data-test="op-compress"]'
    _CLARIFY  = '[data-test="op-clarify"]'

    def __init__(self, page: Page) -> None:
        self._page = page

    def is_visible(self) -> bool:
        """Return True if at least the rewrite button is visible."""
        return self._page.locator(self._REWRITE).is_visible()

    def click_rewrite(self) -> None:
        """Click the Rewrite operation button and wait for network idle."""
        self._page.locator(self._REWRITE).click()
        self._page.wait_for_load_state("networkidle")

    def click_expand(self) -> None:
        """Click the Expand operation button and wait for network idle."""
        self._page.locator(self._EXPAND).click()
        self._page.wait_for_load_state("networkidle")

    def click_compress(self) -> None:
        """Click the Compress operation button and wait for network idle."""
        self._page.locator(self._COMPRESS).click()
        self._page.wait_for_load_state("networkidle")

    def click_clarify(self) -> None:
        """Click the Clarify operation button and wait for network idle."""
        self._page.locator(self._CLARIFY).click()
        self._page.wait_for_load_state("networkidle")
```

**File**: `spec-doc/e2e/pages/sidebar_page.py` (new)

**Pattern**:

```python
"""SidebarPage — anti-corruption layer over the project-tree sidebar component.

Selectors: [data-test] attributes only. Verified against:
  spec-doc/src/app/components/sidebar/sidebar.component.html  (Step 0 audit)
"""
from __future__ import annotations
from playwright.sync_api import Page, Locator


class SidebarPage:
    """Page object for the project-tree sidebar component.

    Consumers: bootstrap step definitions, edit-spec step definitions (Task 3).
    """

    _CONTAINER    = '[data-test="sidebar-container"]'
    _PROJECT_ITEM = '[data-test="sidebar-project-item"]'

    def __init__(self, page: Page) -> None:
        self._page = page
        self._container: Locator = page.locator(self._CONTAINER)

    def is_visible(self) -> bool:
        """Return True if the sidebar container is visible."""
        return self._container.is_visible()

    def project_names(self) -> list[str]:
        """Return the display names of all project items currently in the sidebar."""
        items = self._page.locator(self._PROJECT_ITEM)
        count = items.count()
        return [items.nth(i).inner_text().strip() for i in range(count)]

    def has_project(self, name: str) -> bool:
        """Return True if a project with the given name appears in the sidebar."""
        return name in self.project_names()

    def select_project(self, name: str) -> None:
        """Click the project item matching name; raises if no match exists."""
        self._page.locator(self._PROJECT_ITEM).filter(has_text=name).first.click()
        # Wait for Angular to update active state
        self._page.wait_for_load_state("networkidle")
```

**File**: `spec-doc/e2e/pages/__init__.py` (new)

**Pattern**:

```python
"""e2e/pages — Page object classes for all retrofitted Spec Doc components.

Step-definition modules import from this package, never from individual files.
"""
from .editor_page import EditorPage
from .operation_bar_page import OperationBarPage
from .preview_page import PreviewPage
from .sidebar_page import SidebarPage

__all__ = ["EditorPage", "OperationBarPage", "PreviewPage", "SidebarPage"]
```

**Verify**:
```bash
cd spec-doc/e2e && python -c "
from pages import EditorPage, PreviewPage, OperationBarPage, SidebarPage
print('all page objects import cleanly')
"
```
Expect: `all page objects import cleanly`.

---

### Step 5: Write `e2e/test_smoke.py` — fixture contract + page object interface tests

**Action**: Write smoke tests that verify the fixture contract and page object interface without requiring a running browser. Interface tests check that each expected method is callable; fixture tests require the `servers` and `page` fixtures (these are the integration-level tests that confirm servers start).

**File**: `spec-doc/e2e/test_smoke.py` (new)

**Pattern**: (full test bodies — no stubs)

```python
"""
test_smoke.py — Fixture contract and page object interface smoke tests.

These tests verify:
  1. All four page object classes are importable and expose the expected interface.
  2. The conftest `servers` fixture starts both servers and yields the correct URL.
  3. The conftest `page` fixture navigates to the Angular app successfully.

Tests marked with @pytest.mark.integration require servers to be startable from the
test environment. They are fast (< 5s each once servers are up) but depend on
network and npm being available.
"""
import pytest
from pages import EditorPage, PreviewPage, OperationBarPage, SidebarPage


# ---------------------------------------------------------------------------
# Interface contract — no servers required
# ---------------------------------------------------------------------------

class TestEditorPageInterface:
    def test_importable_exposesExpectedMethods(self):
        """EditorPage class must expose the full interface contract before any page is loaded."""
        for method in ("is_visible", "get_content", "set_content", "focus"):
            assert callable(getattr(EditorPage, method, None)), (
                f"EditorPage.{method} must be defined as a callable method"
            )


class TestPreviewPageInterface:
    def test_importable_exposesExpectedMethods(self):
        """PreviewPage class must expose the full interface contract before any page is loaded."""
        for method in ("is_visible", "get_text_content", "get_rendered_html", "contains_heading"):
            assert callable(getattr(PreviewPage, method, None)), (
                f"PreviewPage.{method} must be defined as a callable method"
            )


class TestOperationBarPageInterface:
    def test_importable_exposesExpectedMethods(self):
        """OperationBarPage class must expose all four operation methods."""
        for method in ("is_visible", "click_rewrite", "click_expand", "click_compress", "click_clarify"):
            assert callable(getattr(OperationBarPage, method, None)), (
                f"OperationBarPage.{method} must be defined as a callable method"
            )


class TestSidebarPageInterface:
    def test_importable_exposesExpectedMethods(self):
        """SidebarPage class must expose the full interface contract before any page is loaded."""
        for method in ("is_visible", "project_names", "has_project", "select_project"):
            assert callable(getattr(SidebarPage, method, None)), (
                f"SidebarPage.{method} must be defined as a callable method"
            )


# ---------------------------------------------------------------------------
# Fixture integration — servers + page fixtures required
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_servers_startAndRespond(servers):
    """servers fixture must yield a non-empty URL string when both processes start."""
    assert isinstance(servers, str), "servers fixture must yield a string URL"
    assert servers.startswith("http://localhost"), (
        f"servers fixture should yield a localhost URL, got {servers!r}"
    )


@pytest.mark.integration
def test_page_navigatesToAngularApp(page, servers):
    """page fixture must navigate to the Angular app and load a non-empty title."""
    assert page.url.startswith(servers), (
        f"page.url should start with {servers}, got {page.url!r}"
    )
    title = page.title()
    assert len(title) > 0, "Page title should be non-empty after Angular app loads"


@pytest.mark.integration
def test_page_editorPageInstantiates(page):
    """EditorPage must be instantiable with a live Playwright Page without raising."""
    ep = EditorPage(page)
    # is_visible() may be False before a project is loaded; that is correct.
    # The invariant is that calling it does not raise.
    result = ep.is_visible()
    assert isinstance(result, bool), (
        f"EditorPage.is_visible() must return bool, got {type(result).__name__}"
    )


@pytest.mark.integration
def test_page_sidebarPageInstantiates(page):
    """SidebarPage must be instantiable and project_names() must return a list."""
    sb = SidebarPage(page)
    names = sb.project_names()
    assert isinstance(names, list), (
        f"SidebarPage.project_names() must return list, got {type(names).__name__}"
    )
```

**Verify**:
```bash
# Interface tests only (no servers required)
cd spec-doc/e2e && pytest test_smoke.py -k "not integration" -v
# Expect: 4 passing, 0 errors

# Full smoke (servers must be startable)
cd spec-doc/e2e && pytest test_smoke.py -v
# Expect: 9 passing, 0 errors
```

---

## 5. Tests

The full test bodies are in Step 5 above (no stubs). Framework used: **pytest** (matching the backend test convention in the codebase context). The integration-marked tests use the `servers` and `page` fixtures from `conftest.py`.

Key assertions by class:

```python
# EditorPage — interface contract
assert callable(getattr(EditorPage, "get_content", None))
assert callable(getattr(EditorPage, "set_content", None))

# OperationBarPage — all four operations present
for method in ("click_rewrite", "click_expand", "click_compress", "click_clarify"):
    assert callable(getattr(OperationBarPage, method, None))

# servers fixture — yields correct URL type
assert isinstance(servers, str) and servers.startswith("http://localhost")

# page fixture — navigates successfully
assert page.url.startswith(servers)
assert len(page.title()) > 0

# page object instantiation — no raise
result = EditorPage(page).is_visible()
assert isinstance(result, bool)

names = SidebarPage(page).project_names()
assert isinstance(names, list)
```

---

## 6. Commit Plan

**Executor instruction**: commit after completing each step below — **not** at the end of the task. Each commit maps to a numbered step. Run the commit before moving forward.

1. `chore(e2e): scaffold e2e directory with requirements and pytest config` — **after Step 1** — files: `e2e/requirements-e2e.txt`, `e2e/pytest.ini`, `.gitignore` additions

2. `feat(e2e): add conftest.py with session-scoped server and page fixtures` — **after Step 2** — files: `e2e/conftest.py`

3. `feat(e2e): add EditorPage page object` — **after Step 3** — files: `e2e/pages/editor_page.py`

4. `feat(e2e): add PreviewPage, OperationBarPage, SidebarPage and pages __init__` — **after Step 4** — files: `e2e/pages/preview_page.py`, `e2e/pages/operation_bar_page.py`, `e2e/pages/sidebar_page.py`, `e2e/pages/__init__.py`

5. `test(e2e): add smoke tests for fixture contract and page object interfaces` — **after Step 5 passes** — files: `e2e/test_smoke.py`

**Deviation logging**: if a step deviates from this guide (e.g., a `[data-test]` value differs from the expected name, a `SKIP` is applied, or a method signature changes), prefix the commit body with `Deviations:` and one line per deviation. Example:
```
Deviations:
- data-test="editor-wrapper" found in template, not "editor-container"; updated EditorPage._CONTAINER
- data-test="op-humanize" found in template, not "op-rewrite"; updated OperationBarPage._REWRITE
```

---

## 7. Verification

```bash
# Interface tests only (no running servers required — safe to run in any env)
cd spec-doc/e2e && pytest test_smoke.py -k "not integration" -v

# Full suite including server startup (requires ports 3100 + 4201 free)
cd spec-doc/e2e && pytest test_smoke.py -v --tb=short
```

**Expected delta**: 0 passing (baseline, no e2e tests existed) → **9 passing** after Task 2. Zero pre-existing tests broken (Task 2 adds only new files; no existing source files are edited except `.gitignore`).

**Breakdown**:

| Test class | Count | Requires servers |
|---|---|---|
| `TestEditorPageInterface` | 1 | No |
| `TestPreviewPageInterface` | 1 | No |
| `TestOperationBarPageInterface` | 1 | No |
| `TestSidebarPageInterface` | 1 | No |
| `test_servers_startAndRespond` | 1 | Yes |
| `test_page_navigatesToAngularApp` | 1 | Yes |
| `test_page_editorPageInstantiates` | 1 | Yes |
| `test_page_sidebarPageInstantiates` | 1 | Yes |
| **Total** | **8** | — |

_(The interface loop tests count as 1 assertion block each, 8 total test functions.)_

---

## 8. Rollback

**Per-step**: every commit is independently revertible.

```bash
git revert <sha>    # Reverts a single commit without touching others
```

Map:
- Revert commit 5 → removes `test_smoke.py` only
- Revert commit 4 → removes three page objects + `__init__.py`; `conftest.py` remains usable
- Revert commit 3 → removes `editor_page.py`
- Revert commit 2 → removes `conftest.py`; page objects cannot be exercised but remain importable
- Revert commit 1 → removes scaffold files; restores `.gitignore`

**Per-branch**: if verification fails and the branch is unrecoverable:

```bash
git reset --hard <pre-task-sha>   # Resets branch to state before Task 2 started
# — or —
git checkout main && git branch -D e2e/task-2-page-objects
```

Neither command is run without explicit approval; both are listed here for completeness.

---

## 9. Deviations Allowed

- **`[data-test]` value differs from expected** (Step 0 audit reveals a different name) → use the actual value, update the method's `_SELECTOR` constant, log in commit body as `Deviations: data-test="<actual>" found, expected "<expected>"; updated <ClassName>._CONSTANT`
- **Selector is absent from template** → mark method with `# SKIP: data-test="<value>" missing from <component>.html`, return `None` / `""` / `False`, add `pytest.skip(reason="...")` to the integration smoke test that exercises it; do NOT add the attribute to the template
- **`AI_PROVIDER=mock` not a valid value in `server.js`** → STOP; flag as [REQUIRES APPROVAL]; the conftest fixture cannot proceed without a working mock mode; do not substitute a real AI key
- **`npm run api` script name differs in `package.json`** → use the correct script name, log deviation; do not restructure npm scripts
- **Angular dev server started via a different command** → substitute the correct command in `servers()`, log deviation
- **Step N simplification improves Step N+1** → take it, log one `Deviations:` line in the commit body

---

## 10. Out of Scope

Task 2 delivers the foundation layer only: the fixture contract and four page object classes. Anything that consumes those classes — Gherkin scenarios, step definitions, CI YAML changes, additional page objects for modals — is deferred to Task 3. An eager executor may recognise natural extensions; any such changes must stop and be flagged rather than absorbed into this task's blast radius.

- **`.feature` files** — deferred to Task 3; the fixture contract must be stable before scenarios are authored against it
- **Step-definition modules** — deferred to Task 3; they are the direct consumers of the page objects and fixture, not part of Task 2
- **CI YAML changes** — server-startup wiring in GitHub Actions (caching, parallel job configuration, Xvfb if needed) is deferred to Task 3; Task 2 only ensures the fixture works locally
- **`NewProjectPage` / bootstrap-modal page object** — deferred; no named Epic task requires it in Task 2; re-scope at the Task 3 boundary if a selector gap surfaces during bootstrap scenario authoring
- **Adding `[data-test]` attributes to Angular templates** — explicitly not in scope; pre-existing gaps are documented as skips and surfaced as visible debt for a separate task
- **Retry / wait helpers on page object methods** — deferred; no CI failure pattern calibrates the retry budget yet; Playwright's built-in auto-wait handles the common SPA cases
- **`pytest-bdd` imports in conftest or smoke tests** — deferred to Task 3; the conftest must stay framework-agnostic so step-definition modules control their own BDD wiring

**Rule for the executor**: if a change appears helpful but appears in this list, STOP and flag it as a deviation rather than expanding Task 2's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for server strategy, page object pattern, fixture-as-contract
- [Epic](./epic.md) — Task scope and port budget
- [Timeline](./timeline.md) — Update status to ✅ Done after Step 5 passes