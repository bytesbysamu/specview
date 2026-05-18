# Test Phase 2: Gherkin Scenarios & E2E Tests

## What this is

Write Gherkin `.feature` files for the overview page and implement them as Playwright E2E tests. Gherkin is the stable behavioral contract — it describes what users see and do, not how the code works. E2E tests execute these scenarios against a running app (docker compose, `CHAIN_PROVIDER=mock`).

These tests should rarely change. Layout tweaks, refactors, and signal renames don't break them. Only feature additions or removals require updates.

**Depends on:** Phase 1 feature specs (the scenarios are derived from F1-F17).

---

## Existing E2E Infrastructure

Already built and working:

- **5 feature files** in `e2e/features/` covering backend AI flows (brainstorm, bootstrap-pipeline, epic-guide, billing-gate, pro-check)
- **Step definitions** in `e2e/steps/common_steps.py` — 193 lines, covers: app loading, project seeding, text entry, button clicks, visibility assertions with configurable timeouts, polling status checks
- **Page object** in `e2e/pages/app_page.py` — load(), enter_text(), click(), is_visible(), wait_visible(), submit_brainstorm()
- **Test fixtures** in `e2e/conftest.py` — session-scoped Flask (port 5001, CHAIN_PROVIDER=mock) + Angular dev server (port 4201)
- **Product behavior contract** in `product-behavior.md` — 5 flows mirrored 1:1 by features

None of the existing features test the overview page layout, navigation, or grid. They test AI operation flows (submit → poll → result). The new features below fill the overview page gap.

---

## New Gherkin Feature Files

Six new `.feature` files, one per functional area of the overview page. Each scenario maps back to one or more feature specs from Phase 1 (F1-F17).

### overview-auth.feature (F1)

```gherkin
Feature: Overview — Authentication Gate

  Scenario: Unauthenticated user sees login form
    Given the app is loaded
    And the user is not logged in
    Then the login form is visible
    And the project grid is not visible

  Scenario: Authenticated user sees the overview page
    Given the app is loaded
    And the user is logged in
    Then the masthead title "Specview" is visible
    And the section navigation is visible
    And the project grid is visible

  Scenario: Sign out returns to login
    Given the user is logged in
    When the user clicks "Sign out"
    Then the login form is visible
    And the project grid is not visible
```

### overview-navigation.feature (F3, F6, F12)

```gherkin
Feature: Overview — Section Navigation

  Scenario: Default view shows all sections grouped
    Given the user is logged in
    And projects exist in multiple sections
    When the app loads
    Then the "All" tab is active
    And projects are grouped under section headers

  Scenario: Clicking a section tab filters to that section
    Given the user is logged in
    And projects exist in "Specced" section
    When the user clicks the "Specced" tab
    Then only specced projects are visible
    And the view uses a column layout

  Scenario: Section count badges reflect project counts
    Given the user is logged in
    And 3 projects are in "Braindumps"
    And 5 projects are in "Specced"
    Then the "Braindumps" badge shows "3"
    And the "Specced" badge shows "5"

  Scenario: Clicking "All" returns to grouped view
    Given the user is on the "Specced" tab
    When the user clicks the "All" tab
    Then projects are grouped under section headers

  Scenario: Context tab shows configuration cards
    Given the user is logged in
    When the user clicks the "Context" tab
    Then 6 context cards are visible
    And the search bar is hidden
```

### overview-status-bar.feature (F4)

```gherkin
Feature: Overview — Status Bar

  Scenario: Idle state shows ready message
    Given the user is logged in
    And no generation is running
    Then the status bar shows "idle — ready"

  Scenario: Active generation shows project and step
    Given the user is logged in
    And a spec generation is running for "My Project" at step "architecture"
    Then the status bar shows "My Project"
    And the status bar shows "architecture"
    And the status bar has a shimmer animation

  Scenario: Generation success shows done
    Given the user is logged in
    And a generation has just completed for "My Project"
    Then the status bar shows "done"

  Scenario: Generation failure shows error with retry
    Given the user is logged in
    And a generation has failed with "AI provider error"
    Then the status bar shows "error"
    And a retry button is visible in the status bar
```

### overview-search.feature (F5)

```gherkin
Feature: Overview — Search & Filter

  Scenario: Search filters projects by name
    Given the user is logged in
    And 10 projects are loaded
    When the user types "auth" in the search bar
    Then only projects with "auth" in the name are visible
    And the count label shows the number of matches

  Scenario: Clearing search shows all projects
    Given the user is logged in
    And the search bar contains "auth"
    When the user clears the search bar
    Then all projects are visible
    And the count label shows the total project count

  Scenario: Search with no matches shows empty state
    Given the user is logged in
    When the user types "zzz-nonexistent" in the search bar
    Then an empty state message is visible
```

### overview-grid.feature (F6, F7, F8, F9)

```gherkin
Feature: Overview — Project Grid

  Scenario: Active section uses hero grid layout
    Given the user is logged in
    And 3 projects are in the "Active" section
    Then the Active section uses a wider first column

  Scenario: First card in each section has enhanced styling
    Given the user is logged in
    And projects exist in "Specced" section
    Then the first card in "Specced" has a larger title

  Scenario: Project cards display name, teaser, and file count
    Given the user is logged in
    And a project "Auth Reliability" exists with 8 files
    Then the card shows "Auth Reliability"
    And the card shows a teaser
    And the card shows "8" as the file count

  Scenario: Clicking a project card opens the project
    Given the user is logged in
    And a project "Auth Reliability" exists
    When the user clicks the "Auth Reliability" card
    Then the project detail view opens

  Scenario: Braindump cards show real content teasers
    Given the user is logged in
    And a braindump project has content starting with "Claude CLI OAuth credentials expire regularly"
    Then the card teaser shows "Claude CLI OAuth credentials expire regularly."
```

### overview-polling.feature (F13, F14)

```gherkin
Feature: Overview — Polling & Error Recovery

  Scenario: Polling error displayed after max retries
    Given the user is logged in
    And the API is unreachable
    When polling exceeds the maximum retry count
    Then the polling error message is visible

  Scenario: Update banner can be dismissed
    Given the user is logged in
    And an update banner is showing
    When the user clicks dismiss
    Then the update banner is hidden
```

---

## E2E Implementation Notes

### Step definitions to add

The existing `common_steps.py` handles generic steps (app loading, clicking, visibility). New steps needed for overview-specific assertions:

- "projects are grouped under section headers" — assert `.section-group` elements exist with `.section-group-title`
- "the view uses a column layout" — assert `.file-column` elements exist
- "the status bar shows {text}" — assert `.gen-status-content` contains text
- "the status bar has a shimmer animation" — assert `.gen-status-track` element exists
- "the count label shows the number of matches" — assert `.search-count` text matches
- "the first card in {section} has a larger title" — assert `.featured` class on first `.file-item`
- "6 context cards are visible" — assert `.context-card` count
- "the search bar is hidden" — assert `.search-bar` not visible

### Page object extensions

Extend `app_page.py` with overview-specific selectors:

```python
SECTION_TAB = '.section-link'
SECTION_GROUP = '.section-group'
STATUS_BAR = '.gen-status-bar'
SEARCH_INPUT = '.search-bar input'
SEARCH_COUNT = '.search-count'
FILE_ITEM = '.file-item'
CONTEXT_CARD = '.context-card'
POLLING_ERROR = '[data-test="polling-error"]'
```

### Test data seeding

E2E tests run against `CHAIN_PROVIDER=mock`. Need seed projects that cover all sections:
- 1-2 projects with active jobs (Active)
- 1-2 projects with architecture.md + epic.md (Ready to build)
- 3-4 projects with implementation-guide.md (Specced)
- 2-3 projects with braindump.md only (Braindumps)

Seed via the API or by pre-populating `data/projects/` in the test fixture.

---

## Relationship to Existing Features

The 5 existing `.feature` files stay unchanged. They test backend AI flows (brainstorm → result, pipeline → files, billing gate → 429). The 6 new files test the overview page chrome that wraps those flows.

Together they cover:

| Layer | Existing features | New features |
|-------|------------------|--------------|
| Auth | — | overview-auth |
| Navigation | — | overview-navigation |
| Status bar | — | overview-status-bar |
| Search | — | overview-search |
| Grid/cards | — | overview-grid |
| Polling | bootstrap-pipeline (partial) | overview-polling |
| Brainstorm | brainstorm | — |
| Pipeline | bootstrap-pipeline | — |
| Epic guide | epic-guide | — |
| Billing | billing-gate, pro-check | — |
