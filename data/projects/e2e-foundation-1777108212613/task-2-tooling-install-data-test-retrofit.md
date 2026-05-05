# Task 2: Tooling install + `[data-test]` retrofit

## 1. Context

This task installs the Python-based E2E test infrastructure (Playwright + pytest-bdd) and retrofits four Angular component templates with `[data-test]` selector attributes. Together these two deliverables form the prerequisite surface for Task 3's page objects: Playwright cannot run without a Chromium installation, and page objects written before selectors exist bind to visual implementation details — class names, tag structures — that change when the product is redesigned. Bundling the tooling install with the selector retrofit ensures Task 3 receives a stable, complete contract in a single dependency rather than two partial deliverables that could arrive out of order.

**Trade-offs considered**:
- **Behave over pytest-bdd** — rejected; a second runner requires its own conftest, its own fixture chain, and a separate CI step — three new seams for zero additional coverage. pytest-bdd keeps marker registration, session fixtures, and conftest inheritance from the existing pytest ecosystem intact.
- **JavaScript/TypeScript Playwright** — rejected; the E2E layer authored in Python shares fixture scoping, marker registration, and conftest conventions with the backend test suite. A TS runner splits the ecosystem and produces two parallel conftest hierarchies.
- **CSS class or `id` selectors instead of `[data-test]`** — rejected; class names and ids are visual implementation details that change on redesign. `[data-test]` is the established convention in the architecture doc and is the exact name Task 3's page objects will reference — any other attribute name produces a naming conflict.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Working tree state
git status
git diff HEAD -- \
  src/app/components/new-project/new-project.component.html \
  src/app/components/operation-bar/operation-bar.component.html \
  src/app/components/sidebar/sidebar.component.html

# Identify component directories — determines Step 6 target path
ls src/app/components/

# Identify existing CI workflow files — determines Step 2 action
ls .github/workflows/ 2>/dev/null || echo "NO CI workflows found — will create"

# Check for existing Python artefacts
ls requirements*.txt pytest.ini pyproject.toml 2>/dev/null || echo "no Python config found"

# Baseline Angular test count — record before any edits
npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -10
```

**If working tree is dirty on target files**: stash unrelated changes before starting.

**Critical pre-flight decision**: if `ls src/app/components/` shows an `output-panel/` directory, that is the Step 6 target. If it shows only `preview/`, use `src/app/components/preview/preview.component.html` as the Step 6 target and log the substitution as a deviation in every commit that references it.

**Baseline recorded**: ___ / ___ Angular tests passing (executor fills in after running the baseline command above).

---

## 3. Files

### To Create (new)
- `requirements-dev.txt` — Python E2E deps: playwright, pytest-playwright, pytest-bdd, pytest. No `-r requirements.txt` prefix — spec-doc has no production Python code to extend.
- `pytest.ini` — registers the `e2e` pytest marker used by `pytest -m e2e`. Lives at repo root; required before any E2E test invocation in Tasks 3–4.
- `e2e/__init__.py` — empty; makes `e2e/` a Python package so pytest collects it without path manipulation.
- `e2e/test_tooling_smoke.py` — import verification tests (Playwright, pytest-bdd) and parametrised structural tests asserting every required `[data-test]` attribute is present in the four templates.
- `.github/workflows/ci.yml` — **only if no workflow file exists**. If a workflow already exists, modify it in place per Step 2.

### To Modify (cite CODEBASE CONTEXT)
- `src/app/components/new-project/new-project.component.html` — attribute additions only: modal container, project-name input, template selector, bootstrap trigger button. (spec-doc CLAUDE.md: `components/new-project/` — Bootstrap modal)
- `src/app/components/operation-bar/operation-bar.component.html` — attribute additions only: one `data-test` per AI operation button (rewrite, expand, compress, clarify, generate). (spec-doc CLAUDE.md: `components/operation-bar/` — AI operation buttons)
- `src/app/components/sidebar/sidebar.component.html` — attribute additions only: new-project toggle, project-list container, `[attr.data-test]` dynamic binding on project list items. (spec-doc CLAUDE.md: `components/sidebar/` — Project tree)
- `src/app/components/output-panel/output-panel.component.html` **or** `src/app/components/preview/preview.component.html` — attribute additions only: output container and output content area. Which file applies is determined by the pre-flight `ls src/app/components/` result.
- `.github/workflows/ci.yml` — **only if a workflow already exists**: append a new `e2e-setup` job for Python + Playwright Chromium installation and verification.

### To Leave Alone
- `src/app/components/editor/` — Monaco editor; its internal DOM is managed by the Monaco runtime and is not addressable via static HTML attributes.
- `src/app/services/` — Angular services; the selector contract lives in templates only.
- `server.js` — Express API; no changes in this task.
- `e2e/conftest.py` — not yet created; Task 3 owns this file.
- `e2e/pages/` — not yet created; Task 3 owns this directory.

---

## 4. Implementation Steps

### Step 1: Create `requirements-dev.txt` and `pytest.ini`

**Action**: Create `requirements-dev.txt` at the repo root with floor-pinned package versions. Create `pytest.ini` at the repo root registering the `e2e` marker and scoping test discovery to `e2e/`.

**File**: `requirements-dev.txt` (new), `pytest.ini` (new)

**Pattern**:
```text
# requirements-dev.txt
playwright>=1.50.0
pytest-playwright>=0.6.0
pytest-bdd>=8.0.0
pytest>=8.3.0
```

```ini
# pytest.ini
[pytest]
markers =
    e2e: browser-driven Playwright end-to-end tests (require running Angular + Express servers)
testpaths = e2e
```

**Verify**:
```bash
pip install -r requirements-dev.txt
playwright --version
playwright install chromium
python -c "from playwright.sync_api import sync_playwright; print('playwright ok')"
python -c "import pytest_bdd; print('pytest-bdd ok')"
```
Expect: both `ok` lines printed, no import errors.

---

### Step 2: Add Playwright Chromium install to CI workflow

**Action**: If no workflow exists at `.github/workflows/`, create `ci.yml` with the `e2e-setup` job block below. If a workflow already exists, append the `e2e-setup` job to the existing `jobs:` block without modifying other jobs.

**File**: `.github/workflows/ci.yml` (new if absent; modify if present)

**Pattern — new file**:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e-setup:
    name: E2E tooling verify
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install E2E Python dependencies
        run: pip install -r requirements-dev.txt

      - name: Install Playwright Chromium
        run: playwright install --with-deps chromium

      - name: Verify Playwright operational
        run: python -c "from playwright.sync_api import sync_playwright; print('chromium ok')"
```

**Pattern — appending to existing file** (add inside the existing `jobs:` block):
```yaml
  e2e-setup:
    name: E2E tooling verify
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install E2E Python dependencies
        run: pip install -r requirements-dev.txt
      - name: Install Playwright Chromium
        run: playwright install --with-deps chromium
      - name: Verify Playwright operational
        run: python -c "from playwright.sync_api import sync_playwright; print('chromium ok')"
```

**Verify**:
```bash
grep -A 2 'playwright install' .github/workflows/ci.yml
```
Expect: `playwright install --with-deps chromium` is present.

---

### Step 3: Retrofit `new-project.component.html`

**Action**: Open `src/app/components/new-project/new-project.component.html`. Add `data-test` attributes to four elements: the modal root container, the project-name input or textarea, the template selector, and the bootstrap trigger button. Attribute additions only — no logic changes, no class changes, no structural rewrites.

**File**: `src/app/components/new-project/new-project.component.html` (CODEBASE CONTEXT: `components/new-project/` — Bootstrap modal)

**Pattern** (add the attribute to the existing element; do not change surrounding markup):
```html
<!-- Modal root container — add to the outermost wrapper element -->
<div ... data-test="new-project-modal">

  <!-- Project name / brain dump — input or textarea; attribute name is the same either way -->
  <input ... data-test="project-name-input" />
  <!-- OR if a textarea: -->
  <textarea ... data-test="project-name-input"></textarea>

  <!-- Template selector — <select>, radio group, or ion-select -->
  <select ... data-test="template-selector">...</select>

  <!-- Bootstrap trigger — the submit / generate button -->
  <button ... data-test="bootstrap-trigger">Bootstrap</button>

</div>
```

**Verify**:
```bash
grep -c 'data-test=' src/app/components/new-project/new-project.component.html
```
Expect: `4`.

---

### Step 4: Retrofit `operation-bar.component.html`

**Action**: Open `src/app/components/operation-bar/operation-bar.component.html`. Add one `data-test` attribute to each of the five AI operation buttons. Each attribute name is the operation name suffixed with `-btn`.

**File**: `src/app/components/operation-bar/operation-bar.component.html` (CODEBASE CONTEXT: `components/operation-bar/` — AI operation buttons)

**Pattern**:
```html
<button ... data-test="rewrite-btn">Rewrite</button>
<button ... data-test="expand-btn">Expand</button>
<button ... data-test="compress-btn">Compress</button>
<button ... data-test="clarify-btn">Clarify</button>
<button ... data-test="generate-btn">Generate</button>
```

**Verify**:
```bash
grep -c 'data-test=' src/app/components/operation-bar/operation-bar.component.html
```
Expect: `5`.

---

### Step 5: Retrofit `sidebar.component.html`

**Action**: Open `src/app/components/sidebar/sidebar.component.html`. Add `data-test` to the new-project toggle button and the project list container. On the repeating project item element (rendered with `*ngFor` or `@for`), add a dynamic `[attr.data-test]` binding — this produces a unique selector per project that page objects can address by name.

**File**: `src/app/components/sidebar/sidebar.component.html` (CODEBASE CONTEXT: `components/sidebar/` — Project tree)

**Pattern — `*ngFor` syntax**:
```html
<!-- Button that opens the new-project modal -->
<button ... data-test="new-project-toggle">+ New Project</button>

<!-- Project list container -->
<ul ... data-test="project-list">

  <!-- Dynamic binding — renders as data-test="project-item-{name}" in the DOM -->
  <li *ngFor="let project of projects"
      [attr.data-test]="'project-item-' + project.name"
      ...>
    {{ project.name }}
  </li>

</ul>
```

**Pattern — `@for` control flow syntax** (Angular 17+ alternative):
```html
<button ... data-test="new-project-toggle">+ New Project</button>
<ul ... data-test="project-list">
  @for (project of projects; track project.name) {
    <li [attr.data-test]="'project-item-' + project.name" ...>{{ project.name }}</li>
  }
</ul>
```

**Verify**:
```bash
grep -c 'data-test' src/app/components/sidebar/sidebar.component.html
```
Expect: `3` (new-project-toggle, project-list, and the `[attr.data-test]` binding — three occurrences of the string `data-test`).

---

### Step 6: Retrofit output-panel (or preview) component

**Action**: Using the pre-flight `ls src/app/components/` result, identify the correct target: `output-panel/output-panel.component.html` if the directory exists, otherwise `preview/preview.component.html`. Add `data-test` to the output container and the content area. Add `data-test="copy-btn"` only if a copy button already exists in the template — do not add elements that are not present.

**File**: `src/app/components/output-panel/output-panel.component.html` if it exists, otherwise `src/app/components/preview/preview.component.html` (CODEBASE CONTEXT: `components/preview/` — marked.js preview)

**Pattern**:
```html
<!-- Output root container -->
<div ... data-test="output-panel">

  <!-- Content area where AI output or rendered markdown appears -->
  <div ... data-test="output-content">
    <!-- existing content unchanged -->
  </div>

  <!-- Copy button — add ONLY if the element already exists in the template -->
  <button ... data-test="copy-btn">Copy</button>

</div>
```

**Verify**:
```bash
# Run whichever path exists
grep -c 'data-test=' src/app/components/output-panel/output-panel.component.html 2>/dev/null \
  || grep -c 'data-test=' src/app/components/preview/preview.component.html
```
Expect: `2` minimum (output-panel, output-content); `3` if a copy button exists in the template.

---

### Step 7: Create `e2e/` package and tooling smoke tests

**Action**: Create `e2e/__init__.py` (empty file) to make `e2e/` a Python package. Create `e2e/test_tooling_smoke.py` with the complete test content from § 5. Run the suite immediately after creation to confirm all 16 tests pass before committing.

**File**: `e2e/__init__.py` (new), `e2e/test_tooling_smoke.py` (new)

**Pattern**: copy § 5 verbatim.

**Verify**:
```bash
pytest e2e/test_tooling_smoke.py -v
```
Expect: **16 passed**, 0 failed, 0 errors. If any selector test fails, the corresponding template step (3–6) has a missing or misspelled attribute — fix the template and re-verify before committing.

---

## 5. Tests

Framework: pytest 8.x with `parametrize`. The Angular Karma suite is unchanged by this task — no Jasmine additions required.

```python
# e2e/test_tooling_smoke.py
import pathlib
import pytest

# Repo root is one directory above e2e/
WORKSPACE = pathlib.Path(__file__).parent.parent


class TestToolingInstall:
    """Playwright and pytest-bdd are importable from the installed requirements."""

    def test_playwright_importable_returnsChromiumDriver(self):
        """playwright installed → sync_playwright().chromium is not None"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            assert p.chromium is not None, (
                "Chromium driver not found. "
                "Run: playwright install chromium"
            )

    def test_pytest_bdd_importable_hasScenariosHelper(self):
        """pytest_bdd installed → pytest_bdd.scenarios is callable"""
        import pytest_bdd

        assert callable(getattr(pytest_bdd, "scenarios", None)), (
            "pytest_bdd.scenarios not callable. "
            "Check: pip install -r requirements-dev.txt"
        )


class TestSelectorContract:
    """Structural: every required [data-test] attribute is present in each template.
    One grep per assertion. Failure message names the rule and the fix."""

    @pytest.mark.parametrize(
        "selector",
        [
            "new-project-modal",
            "project-name-input",
            "template-selector",
            "bootstrap-trigger",
        ],
    )
    def test_newProjectTemplate_hasDataTestSelector(self, selector):
        """new-project.component.html has all required [data-test] attributes"""
        template = (
            WORKSPACE
            / "src/app/components/new-project/new-project.component.html"
        )
        content = template.read_text(encoding="utf-8")
        assert f'data-test="{selector}"' in content, (
            f'Missing [data-test="{selector}"] in new-project.component.html. '
            f"Add the attribute to the corresponding element (Step 3)."
        )

    @pytest.mark.parametrize(
        "selector",
        [
            "rewrite-btn",
            "expand-btn",
            "compress-btn",
            "clarify-btn",
            "generate-btn",
        ],
    )
    def test_operationBarTemplate_hasDataTestSelector(self, selector):
        """operation-bar.component.html has all required [data-test] attributes"""
        template = (
            WORKSPACE
            / "src/app/components/operation-bar/operation-bar.component.html"
        )
        content = template.read_text(encoding="utf-8")
        assert f'data-test="{selector}"' in content, (
            f'Missing [data-test="{selector}"] in operation-bar.component.html. '
            f"Add the attribute to the corresponding button (Step 4)."
        )

    @pytest.mark.parametrize(
        "selector",
        [
            "new-project-toggle",
            "project-list",
        ],
    )
    def test_sidebarTemplate_hasStaticDataTestSelector(self, selector):
        """sidebar.component.html has required static [data-test] attributes"""
        template = (
            WORKSPACE / "src/app/components/sidebar/sidebar.component.html"
        )
        content = template.read_text(encoding="utf-8")
        assert f'data-test="{selector}"' in content, (
            f'Missing [data-test="{selector}"] in sidebar.component.html. '
            f"Add the attribute to the corresponding element (Step 5)."
        )

    def test_sidebarTemplate_hasDynamicProjectItemBinding(self):
        """sidebar.component.html has [attr.data-test] binding on project list items"""
        template = (
            WORKSPACE / "src/app/components/sidebar/sidebar.component.html"
        )
        content = template.read_text(encoding="utf-8")
        assert "attr.data-test" in content, (
            "Missing [attr.data-test] binding on project list items in sidebar.component.html. "
            "Add [attr.data-test]=\"'project-item-' + project.name\" to the *ngFor element (Step 5)."
        )

    @pytest.mark.parametrize(
        "selector",
        [
            "output-panel",
            "output-content",
        ],
    )
    def test_outputPanelTemplate_hasDataTestSelector(self, selector):
        """output-panel or preview component has required [data-test] attributes"""
        output_panel_path = (
            WORKSPACE
            / "src/app/components/output-panel/output-panel.component.html"
        )
        preview_path = (
            WORKSPACE / "src/app/components/preview/preview.component.html"
        )
        template = output_panel_path if output_panel_path.exists() else preview_path
        assert template.exists(), (
            "Neither output-panel.component.html nor preview.component.html found. "
            "Run: ls src/app/components/ and update Step 6 with the correct path."
        )
        content = template.read_text(encoding="utf-8")
        assert f'data-test="{selector}"' in content, (
            f'Missing [data-test="{selector}"] in {template.name}. '
            f"Add the attribute to the corresponding element (Step 6)."
        )
```

**Test count**: 2 (tooling) + 4 (new-project) + 5 (operation-bar) + 2 (sidebar static) + 1 (sidebar dynamic) + 2 (output-panel) = **16 tests**.

---

## 6. Commit Plan

**Executor instruction**: run `git commit` after completing each step below — not once at the end. The step must verify cleanly before you move to the next step. Each commit is independently revertible; batch commits at the end destroy that granularity.

1. `feat(e2e): add requirements-dev.txt and pytest.ini` — after Step 1 — files: `requirements-dev.txt`, `pytest.ini`
2. `ci(e2e): add playwright chromium install job` — after Step 2 — files: `.github/workflows/ci.yml`
3. `feat(templates): [data-test] retrofit — new-project component` — after Step 3 — files: `src/app/components/new-project/new-project.component.html`
4. `feat(templates): [data-test] retrofit — operation-bar component` — after Step 4 — files: `src/app/components/operation-bar/operation-bar.component.html`
5. `feat(templates): [data-test] retrofit — sidebar component` — after Step 5 — files: `src/app/components/sidebar/sidebar.component.html`
6. `feat(templates): [data-test] retrofit — output-panel component` — after Step 6 — files: `src/app/components/output-panel/output-panel.component.html` or `src/app/components/preview/preview.component.html`
7. `test(e2e): selector contract and tooling smoke tests` — after Step 7 and `pytest e2e/test_tooling_smoke.py -v` shows 16 passed — files: `e2e/__init__.py`, `e2e/test_tooling_smoke.py`

**Deviation logging**: if any step deviates from this guide (e.g., `preview/` used in place of `output-panel/`; a button element name differs from the pattern), prefix the commit body with `Deviations:` and one line per deviation. Example: `Deviations: used preview.component.html — output-panel/ directory not found`.

---

## 7. Verification

```bash
# Python E2E smoke suite — must show 16 passed
pytest e2e/test_tooling_smoke.py -v

# Angular unit suite — must be unchanged from baseline
npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -10
```

**Expected delta**:
- Python: 0 → **16 passing** (new file; no prior Python suite)
- Angular Karma: N → N (unchanged; `data-test` attribute additions do not affect component logic or existing specs)

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. Reverting commit 3 removes the new-project selector attributes without touching tooling, CI, or the other three templates.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` returns all four templates and all new files to their pre-task state. Delete the feature branch if applicable.

---

## 9. Deviations Allowed

- **`output-panel/` directory does not exist** → use `src/app/components/preview/preview.component.html` as the Step 6 target. The `test_outputPanelTemplate_hasDataTestSelector` test already handles this via an `exists()` check. Log in commit 6's body: `Deviations: used preview.component.html — output-panel/ not found`.
- **`new-project.component.html` uses a `<textarea>` instead of `<input>`** → apply `data-test="project-name-input"` to the `<textarea>`. Page object authors (Task 3) depend on the attribute name, not the element type.
- **Sidebar uses `@for` control flow instead of `*ngFor`** → apply `[attr.data-test]` inside the `@for` block. The rendered DOM attribute is identical; Playwright finds it the same way.
- **`template-selector` element is absent from new-project template** → skip that attribute; remove `"template-selector"` from the `TestSelectorContract.test_newProjectTemplate_hasDataTestSelector` parametrize list in `e2e/test_tooling_smoke.py`. Log in commit 7's body: `Deviations: template-selector omitted — element not present in template`.
- **A CI workflow already exists and appending `e2e-setup` creates a YAML conflict** → if the conflict cannot be resolved by simple append, STOP and flag [REQUIRES APPROVAL] before modifying the workflow.
- **Any push, publish, or `rm -rf` command is needed** → STOP, mark [REQUIRES APPROVAL], and ask.

---

## 10. Out of Scope

This task delivers tooling installation and the selector contract. It does not deliver any runnable end-to-end test that exercises a live browser — that requires page objects (Task 3) and Gherkin feature files (Task 4). The `e2e/test_tooling_smoke.py` file created here reads template files from disk; it does not start a browser, navigate to a URL, or interact with the running application. The executor must stop and flag any of the following if the temptation to add them arises.

- **`e2e/conftest.py`** — the session-scoped server lifecycle fixture belongs to Task 3. If startup/teardown logic appears necessary during this task, STOP and flag it rather than absorbing Task 3 scope.
- **`e2e/pages/` directory and page object classes** — Task 3 owns these. The selector names established in this task are the input to Task 3, not a reason to build page objects early.
- **`.feature` files and step definitions** — Task 4 owns these. Any Gherkin file created in Task 2 is a scope violation.
- **Karma test alignment or fixes** — Task 1 owns any Karma-specific verification. If the Angular test baseline is broken before this task begins, STOP and flag rather than absorbing Task 1 scope.
- **Angular component logic changes** — the retrofit is attribute additions only. If adding an attribute exposes a structural problem in the template (a missing container element, a missing button), STOP and flag rather than refactoring the component in this task.

**Rule for the executor**: if a change appears helpful but appears in this list, log it as a deviation note and continue with this task's scope only.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale and phase execution diagram
- [Epic](./epic.md) — Task scope and success criteria
- [Timeline](./timeline.md) — Update task status from "in progress" to "done" after § 7 Verification passes