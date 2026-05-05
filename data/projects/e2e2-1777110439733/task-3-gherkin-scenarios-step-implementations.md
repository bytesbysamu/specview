# Task 3: Gherkin Scenarios + Step Implementations — Implementation Guide

## 1. Context

Task 3 closes the E2E2 epic by writing 5 `.feature` files and the matching pytest-bdd step definitions, executed against the page objects + shared fixture from Task 2. Every scenario covers a real user-visible workflow that today relies on manual browser smoke. The five flows are: bootstrap-happy (full capability generation), bootstrap-fail-fast (the error panel that ships per commit `220d9e5`), edit-spec (Monaco auto-save), context-editor (parametrized across 4 context keys), rewrite-operation (selection → instruction → result). Backend is Flask `:3101`; Express was retired in commits `7a9c53e` + `536ae1d`. AI provider is `mock` for all scenarios (deterministic output, zero API cost).

**Trade-offs considered:**

- **One `.feature` per workflow vs. one combined `.feature`** — separate files chosen; each maps to one user story, runs independently, fails in isolation. Combined would tangle scenarios and obscure failure attribution.
- **API-based setup vs. UI-based setup** — API for prerequisites (seed projects via `POST /api/projects`), UI for the actual assertions (click bootstrap, watch progress). Faster + less brittle than clicking through bootstrap to seed every test.
- **Real Claude SDK vs. `CHAIN_PROVIDER=mock`** — mock chosen; real Claude is per-run cost + non-deterministic + test-flake source. Real-claude smoke is a separate `@pytest.mark.real_claude` track (registered, no bodies).

---

## 2. Pre-flight

Run **before editing any file**:

```bash
cd {WORKSPACE}
git status                                      # clean working tree
git log --oneline -1                            # confirm Task 2 merged

# Confirm Task 2 deliverables exist
ls e2e/pages/{new_project,operation_bar,sidebar,output_panel}_page.py
ls e2e/conftest.py
ls e2e/pytest.ini

# Confirm Flask + Angular runnable (Task 2's fixture starts them)
curl -sS -o /dev/null -w "Flask :3101 → %{http_code}\n" http://localhost:3101/health
curl -sS -o /dev/null -w "Angular :4201 → %{http_code}\n" http://localhost:4201/

# Baseline backend pytest count
cd flask && python -m pytest --tb=no -q 2>&1 | tail -1   # Record N

# Baseline e2e pytest count (smoke from Task 2)
cd .. && python -m pytest e2e/ -q 2>&1 | tail -1         # Record M
```

**If `e2e/pages/*.py` files are missing**: Task 2 didn't land — stop, run Task 2 first.

---

## 3. Files

### To Create (new)

- `e2e/features/bootstrap_happy.feature` — Gherkin: open modal → fill name + braindump → click Generate → assert all 5 steps green → assert ≥6 docs in file list
- `e2e/features/bootstrap_fail_fast.feature` — Gherkin: bootstrap with Flask returning provider error → assert step fails → assert error panel visible → assert no template docs generated
- `e2e/features/edit_spec.feature` — Gherkin: open existing project → type in editor → wait 1.5s → assert PUT fires → reload → assert change persists
- `e2e/features/context_editor.feature` — Gherkin (parametrized over 4 keys): open builder/principles/codebase/references editor → edit → save → reload → assert persistence
- `e2e/features/rewrite_operation.feature` — Gherkin: open project with text → select content → click Rewrite → enter instruction → assert response shows in output panel
- `e2e/steps/test_bootstrap_happy.py` — pytest-bdd step bindings for bootstrap_happy.feature
- `e2e/steps/test_bootstrap_fail_fast.py` — same for fail-fast
- `e2e/steps/test_edit_spec.py` — same for edit-spec
- `e2e/steps/test_context_editor.py` — same for context-editor (parametrize fixture over 4 keys)
- `e2e/steps/test_rewrite_operation.py` — same for rewrite-operation
- `e2e/steps/__init__.py` — empty package marker

### To Modify

- `e2e/conftest.py` — add `seed_project(name, files)` API-based setup helper that POSTs to Flask `:3101/api/projects` (used as a Gherkin `Given` background); add `flask_provider_error(should_fail: bool)` fixture that flips the chain provider to a stub that raises `ProviderError` (used by fail-fast scenario)

### To Leave Alone

- `e2e/pages/*.py` — page objects from Task 2; extend a method ONLY if a selector gap surfaces during step authoring (and only methods, never new selectors — those are E2E-foundation territory)
- `flask/` — backend code; do not modify routes, prompts, or providers; Task 3 only consumes the existing API surface
- `src/app/components/*` — Angular templates; `[data-test]` attributes are already retrofitted

---

## 4. Implementation Steps

### Step 1: Write `bootstrap_happy.feature`

**Action**: Cover the happy-path bootstrap. Five Gherkin steps; assertion is "5 progress steps go green AND file list shows ≥6 docs."

**File**: `e2e/features/bootstrap_happy.feature` (new)

```gherkin
Feature: Bootstrap a new capability — happy path
  As a builder
  I want to generate a complete capability spec from a brain dump
  So that I have analysis, epic, architecture, and task guides ready for execution

  Background:
    Given Flask is running with CHAIN_PROVIDER=mock
    And Angular is running on port 4201
    And no project named "Test Capability" exists

  Scenario: Generate a complete capability folder
    When the user opens the New Project modal
    And the user enters "Test Capability" as the project name
    And the user pastes a valid brain dump
    And the user clicks Generate
    Then the bootstrap completes within 60 seconds
    And all 5 progress steps are green
    And the generated file list contains at least 6 documents
    And the file list includes "analysis.md", "epic.md", "architecture.md"
    And no progress step shows the failed marker
```

**Verify**: `cat e2e/features/bootstrap_happy.feature` reads cleanly. Gherkin parser will load it in Step 6.

---

### Step 2: Write `bootstrap_fail_fast.feature`

**Action**: Cover the regression that the silent-template-fallback fix (`220d9e5`) closed. When Flask errors mid-bootstrap, UI must show the error panel — never fake docs.

**File**: `e2e/features/bootstrap_fail_fast.feature` (new)

```gherkin
Feature: Bootstrap fails fast on AI provider error
  As a builder
  I want to see a clear error when bootstrap fails
  So that I never receive misleading template-only docs

  Background:
    Given Flask is running with CHAIN_PROVIDER=mock
    And Angular is running on port 4201
    And the chain provider is stubbed to raise ProviderError on the third call

  Scenario: Bootstrap fails on architecture generation
    When the user opens the New Project modal
    And the user enters "Failing Capability" as the project name
    And the user pastes a valid brain dump
    And the user clicks Generate
    Then steps 1 and 2 complete successfully
    And step 3 shows the failed marker with HTTP 502
    And the error panel is visible with text "Bootstrap Failed"
    And no template docs (spec-index.md, timeline.md, README.md) are generated
    And the "Try Again" button is visible
```

---

### Step 3: Write `edit_spec.feature`

**Action**: Cover Monaco editor + auto-save against existing project. Use API-based setup to seed the project.

**File**: `e2e/features/edit_spec.feature` (new)

```gherkin
Feature: Edit and auto-save a spec file
  As a builder
  I want my edits to persist without explicit save action
  So that I can iterate freely without losing work

  Background:
    Given Flask is running with CHAIN_PROVIDER=mock
    And Angular is running on port 4201
    And a project "Edit Test" exists with file "epic.md" containing "# Original"

  Scenario: Auto-save persists edits across reload
    When the user opens project "Edit Test" from the sidebar
    And the user clicks file "epic.md" in the project tree
    And the user types " — edited" at the end of the editor content
    And the user waits 1500 milliseconds for auto-save debounce
    Then a PUT request to "/api/projects/{id}/files/epic.md" was sent
    When the user reloads the browser
    And the user reopens project "Edit Test"
    And the user clicks file "epic.md"
    Then the editor content ends with " — edited"
```

---

### Step 4: Write `context_editor.feature`

**Action**: Parametrize over the 4 context keys (builder, principles, codebase, references). One Scenario Outline, one Examples table.

**File**: `e2e/features/context_editor.feature` (new)

```gherkin
Feature: Edit and persist context files
  As a builder
  I want to edit each of the 4 context keys
  So that AI generations include my project-specific context

  Background:
    Given Flask is running with CHAIN_PROVIDER=mock
    And Angular is running on port 4201

  Scenario Outline: Edit and reload <key>
    When the user clicks the "<button_label>" sidebar action
    And the user types "<sample_content>" into the context editor
    And the user clicks Save
    And the user reloads the browser
    And the user clicks the "<button_label>" sidebar action again
    Then the context editor content equals "<sample_content>"

    Examples:
      | key        | button_label      | sample_content                    |
      | builder    | Builder Profile   | # Builder — solo founder         |
      | principles | Principles        | # Principles — ship fast         |
      | codebase   | Codebase          | # Codebase — Flask + Angular     |
      | references | References        | # References — humanize-me port  |
```

---

### Step 5: Write `rewrite_operation.feature`

**Action**: Cover the rewrite operation end-to-end via the operation bar.

**File**: `e2e/features/rewrite_operation.feature` (new)

```gherkin
Feature: Rewrite text via AI operation
  As a builder
  I want to transform selected text via AI instruction
  So that I can quickly iterate on spec content

  Background:
    Given Flask is running with CHAIN_PROVIDER=mock
    And Angular is running on port 4201
    And a project "Rewrite Test" exists with file "epic.md" containing "Original sentence."

  Scenario: Rewrite selected text with an instruction
    When the user opens project "Rewrite Test"
    And the user clicks file "epic.md"
    And the user clicks the Rewrite button in the operation bar
    Then a POST request to "/api/ai/text/rewrite" is sent
    And the response status is 200
    And the output panel shows the mock provider response
```

---

### Step 6: Write step-definition modules

**Action**: One `test_*.py` per `.feature` file. Each module uses `pytest_bdd.scenarios("../features/<file>.feature")` to auto-bind. Step bodies use page objects from `e2e.pages` and the conftest fixtures.

**File**: `e2e/steps/test_bootstrap_happy.py` (new)

**Pattern**:

```python
"""Step definitions for bootstrap_happy.feature."""
from pytest_bdd import scenarios, given, when, then, parsers
from e2e.pages import NewProjectPage, SidebarPage

scenarios("../features/bootstrap_happy.feature")


@given('Flask is running with CHAIN_PROVIDER=mock')
def flask_running(flask_server):  # fixture from conftest.py
    assert flask_server.is_alive()


@given('Angular is running on port 4201')
def angular_running(angular_server):
    assert angular_server.responds_at("/")


@given(parsers.parse('no project named "{name}" exists'))
def no_project(api_client, name):
    api_client.delete_project_if_exists(name)


@when('the user opens the New Project modal')
def open_modal(page):
    SidebarPage(page).click_new_project_toggle()


@when(parsers.parse('the user enters "{name}" as the project name'))
def enter_name(page, name):
    NewProjectPage(page).fill_project_name(name)


@when('the user pastes a valid brain dump')
def paste_braindump(page):
    NewProjectPage(page).fill_braindump(
        "Build a tool that does X. Users want Y. Charge $5/mo."
    )


@when('the user clicks Generate')
def click_generate(page):
    NewProjectPage(page).click_bootstrap_trigger()


@then(parsers.parse('the bootstrap completes within {seconds:d} seconds'))
def wait_bootstrap(page, seconds):
    NewProjectPage(page).wait_for_completion(timeout_seconds=seconds)


@then('all 5 progress steps are green')
def assert_all_steps_green(page):
    states = NewProjectPage(page).get_step_states()
    assert all(s == "done" for s in states), f"steps not all green: {states}"


@then(parsers.parse('the generated file list contains at least {count:d} documents'))
def assert_file_count(page, count):
    files = NewProjectPage(page).get_generated_filenames()
    assert len(files) >= count, f"expected ≥{count}, got {len(files)}: {files}"


@then(parsers.parse('the file list includes {filenames}'))
def assert_files_include(page, filenames):
    expected = [f.strip().strip('"') for f in filenames.split(",")]
    actual = NewProjectPage(page).get_generated_filenames()
    for fname in expected:
        assert fname in actual, f"missing {fname} in {actual}"


@then('no progress step shows the failed marker')
def assert_no_failure(page):
    states = NewProjectPage(page).get_step_states()
    assert "failed" not in states, f"unexpected failure marker: {states}"
```

**Verify**: `pytest e2e/steps/test_bootstrap_happy.py --collect-only -q` shows 1 scenario.

---

### Step 7: Write remaining 4 step modules following the same pattern

**Action**: Create `test_bootstrap_fail_fast.py`, `test_edit_spec.py`, `test_context_editor.py`, `test_rewrite_operation.py`. Each follows the Step 6 shape: import scenarios, bind Given/When/Then, delegate DOM work to page objects, use API-fixtures for setup.

**Common pattern for API-based setup** (in `conftest.py` per Section 3):

```python
@pytest.fixture
def seed_project(api_client):
    """Helper to seed a project via API before UI scenarios."""
    created = []
    def _seed(name, files):
        proj_id = api_client.create_project(name, files)
        created.append(proj_id)
        return proj_id
    yield _seed
    for pid in created:
        api_client.delete_project_if_exists(pid)
```

**Verify**: `pytest e2e/ --collect-only -q` shows 5 feature files × scenarios = 8+ collected (4 from context_editor outline).

---

### Step 8: Run the full E2E suite

**Action**: Execute every scenario. Each must reach green or carry a documented `@pytest.mark.skip("reason: <issue link>")` marker.

**File**: n/a — runtime verification.

**Verify**:

```bash
cd {WORKSPACE}
python -m pytest e2e/ -m e2e -v --tb=short 2>&1 | tail -30
```

Expect: 5 feature files load, 8+ scenarios run, all green OR skipped with explicit reason.

---

## 5. Tests

The features themselves ARE the tests. Each scenario's `Then` clauses are executable assertions via pytest-bdd. No additional unit tests needed in this task — the smoke tests from Task 2 already cover fixture and page-object contracts.

**Negative-path coverage**:
- bootstrap_fail_fast covers Flask provider error → fail-fast UI (closes the regression `220d9e5` fixed)
- All other scenarios cover happy paths

**Out-of-scope test types**:
- Performance / load — defer until N>100 user reports
- Cross-browser — defer until Safari user reports a layout bug
- Accessibility — defer until external user demand

---

## 6. Commit Plan

One commit per logical unit. Run `pytest e2e/` after each commit to confirm zero regressions.

1. `feat(e2e): add bootstrap_happy + bootstrap_fail_fast feature files` — `e2e/features/bootstrap_*.feature`: 2 Gherkin files
2. `feat(e2e): add edit_spec + context_editor + rewrite_operation feature files` — `e2e/features/{edit_spec,context_editor,rewrite_operation}.feature`: 3 Gherkin files
3. `feat(e2e): add seed_project + flask_provider_error fixtures to conftest` — `e2e/conftest.py`: API-based setup helpers
4. `test(e2e): add step definitions for bootstrap scenarios` — `e2e/steps/test_bootstrap_{happy,fail_fast}.py`
5. `test(e2e): add step definitions for edit_spec + context_editor + rewrite_operation` — `e2e/steps/test_{edit_spec,context_editor,rewrite_operation}.py`
6. `test(e2e): add steps __init__.py and verify full e2e suite` — `e2e/steps/__init__.py`; full-suite green confirmation in commit body

**Deviation logging**: any selector gap surfaced during step authoring → log in commit body as `Deviations: page object {ClassName}.{method} returns None due to missing [data-test='{selector}'] attribute on {component}.`

---

## 7. Verification

```bash
cd {WORKSPACE}
# Compile check
pytest e2e/ --collect-only -q 2>&1 | tail -5

# Full E2E suite
pytest e2e/ -m e2e -v --tb=short 2>&1 | tail -50

# Backend regression check (must stay at baseline N)
cd flask && python -m pytest --tb=no -q 2>&1 | tail -3
```

**Expected delta**:
- pytest e2e collected: previous M → M + 8+ (5 features, context_editor parametrizes ×4, others 1 each)
- pytest e2e passing: 5 features green OR carry explicit skip with linked issue
- Backend pytest: unchanged N (Task 3 doesn't touch backend)

**Acceptance criteria**:
- Every `Then` clause executes
- No `@pytest.mark.skip` without an explicit `reason=` argument
- Page object methods are stable (no new ones added — only extensions if a selector gap forced it)

---

## 8. Rollback

- **Per-step**: each commit is independently revertible with `git revert <sha>`. Feature files don't depend on each other; step modules import from `e2e.pages` and `e2e.conftest`, both stable from Task 2.
- **Per-branch**: if E2E suite reveals systemic gaps, `git reset --hard <pre-Task-3-sha>` returns to Task 2 state. Re-attempt with smaller feature files if scope was too large.

---

## 9. Deviations Allowed

- **Selector mismatch surfaces during step authoring** → page object method returns None or raises `NotImplementedError("[data-test='X'] absent from <component>")`. Log in commit body. Do NOT add the missing attribute (E2E-foundation Task scope).
- **Mock provider returns non-JSON for some endpoints** (lint-braindump, review) — those routes return 502 in mock mode, which is correct test behavior. If a scenario depends on JSON-shaped output from those routes, mark scenario with `@skip("requires real Claude; tracked in <issue>")`.
- **Angular dev server takes longer than expected to start** → conftest's `angular_server` fixture timeout may need bumping past 90s on slower hosts. Adjust in conftest, log as deviation.
- **`pytest-bdd` version differences in step parser syntax** → use `parsers.parse` for typed args, `parsers.cfparse` if cardinality matters. Pick one consistently per file.
- **Side-effect required** (push, drop, rm -rf outside e2e/) → STOP, mark `[REQUIRES APPROVAL]`, surface to requester.

---

## 10. Out of Scope

This task closes the E2E2 epic with 5 working scenarios. The following are explicitly deferred:

- **6th+ feature files** — when a 6th workflow needs E2E coverage, scope a new task; do not pre-emptively add scenarios that aren't user-flow-driven
- **Visual regression / pixel diff** — defer until a real layout regression triggers it
- **Cross-browser (Firefox, Safari)** — Chrome only; trigger: confirmed bug report on a non-Chrome browser
- **Mobile viewport scenarios** — desktop only; trigger: mobile UX becomes a product priority
- **Real Claude SDK in CI** — `@pytest.mark.real_claude` is registered (Task 4 of test-enhancement) with zero bodies; trigger: paying user justifies per-run cost
- **Accessibility scans** (axe-core) — defer until external user demand or compliance requirement
- **Performance / load testing** — defer until N>100 users
- **CI parallel matrix sharding** — premature; trigger: full suite > 10 min wall-clock
- **Component test authoring** — explicitly the "follow-on epic" per Test Enhancement Task 2's deferral; not in scope here

**Rule for the executor**: if a change appears useful but matches one of these deferrals, STOP and flag it as out-of-scope rather than absorbing it.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic (component list resolved post-analysis: new-project, operation-bar, sidebar, output-panel)
- [Epic](./epic.md) – Scope and tasks
- [Task 1](./task-1-resolve-e2e-driver-and-server-strategy.md) – Driver + server strategy decision (must land before Task 2)
- [Task 2](./task-2-page-objects-shared-fixture.md) – Page objects + conftest (must land before this task)
