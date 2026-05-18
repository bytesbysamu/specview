# Frontend Test Coverage — Overview Page (Superseded)

> **This braindump has been split into 3 phase-specific projects.** Use those instead.

## Phase Projects

| Phase | Project | What it covers |
|-------|---------|---------------|
| **Phase 1** | `test-phase1-feature-specs-1778592995` | Document all 17 overview page features (F1-F17), testing infrastructure audit, UX epic decisions that need coverage |
| **Phase 2** | `test-phase2-gherkin-e2e-1778592996` | 6 new Gherkin feature files (auth, navigation, status bar, search, grid, polling), Playwright E2E implementation, step definitions |
| **Phase 3** | `test-phase3-unit-component-1778592997` | Pure function tests (section-taxonomy, project-teaser), component/template tests (masthead, nav, status bar, search, grid, auth gate), CI integration |

## Original content below (reference only)

**Scope: Overview page only.** The expanded project page (editor, text ops, diff view) is a future phase.

---

## Current Testing Infrastructure (fact-checked 2026-05-12)

### What already exists

**Angular unit tests (Karma + Jasmine):**
- `web-ng/src/app/app.component.spec.ts` — 4 test cases: component creation, polling lifecycle (timer stops after max retries), polling error signal rendering, cleanup on destroy
- `web-ng/src/app/services/projects.service.mock.ts` — spy-based mock
- `web-ng/src/app/services/ai.service.mock.ts` — spy-based mock
- `web-ng/karma.conf.js` — Chrome + ChromeHeadlessCI, coverage reporter
- Dependencies: karma 6.4.0, jasmine-core 5.4.0, @types/jasmine 5.1.0

**E2E tests (pytest-bdd + Playwright):**
- `e2e/features/` — 5 Gherkin feature files, 10 scenarios total:
  - `brainstorm.feature` — text submission, error handling
  - `bootstrap-pipeline.feature` — async spec generation, failure polling
  - `epic-guide.feature` — guide generation, timeout error
  - `billing-gate.feature` — free tier limit, pro tier bypass
  - `pro-check.feature` — pro plan routing, lookup failure
- `e2e/steps/common_steps.py` — 193 lines, Given/When/Then step definitions
- `e2e/pages/app_page.py` — page object (load, enter_text, click, is_visible, wait_visible)
- `e2e/conftest.py` — session fixtures spinning up Flask (port 5001, CHAIN_PROVIDER=mock) + Angular dev server (port 4201)
- Dependencies: pytest-bdd >= 7.0, pytest-playwright >= 0.5, playwright >= 1.44

**Product behavior contract:**
- `product-behavior.md` — 5 core flows mirrored 1:1 by `e2e/features/`. Any flow change must be reflected in both.

### What's missing

- No service unit tests (section-taxonomy, project-teaser, projects.service)
- No template/component tests beyond the smoke test
- No tests for any UX feature delivered across 5+ UX epic branches
- No CI pipeline for frontend tests (`ng test` not in any GitHub Actions workflow)
- Existing E2E features cover backend flows (brainstorm, pipeline, billing) but not overview page layout/navigation
- No visual regression tests

---

## Overview Page — Feature Inventory

Features documented from the actual template (`app.component.html`), component (`app.component.ts`), styles (`styles.css`), and service files. Cross-referenced against UX epics: `ux-grid-polish`, `ux-landing-grid-polish`, `ux-polish-newspaper`, `app-ui-mockups`, `ux-reader-textops`.

### F1 — Auth Gate

The entire page is behind an auth check. Unauthenticated users see `<app-login />`.

```html
@if (!auth.isLoggedIn()) {
  <app-login />
} @else {
  <div class="page">...</div>
}
```

- `auth.isLoggedIn()` is a signal from `AuthService`
- JWT stored in localStorage as `specview_jwt`
- Login component is a standalone component imported by AppComponent

### F2 — Masthead

Editorial newspaper header with three regions:

| Element | Content | Typography |
|---------|---------|------------|
| Edition | "Spec Doc" | Sans, small |
| Date | Today's date (e.g. "Tuesday, May 12, 2026") | Sans, muted |
| Title | "Specview" | 64px Playfair Display |
| Tagline | "All the Specs Fit to Read" | Source Serif 4, italic |
| Actions | "+ New" button, theme toggle (☀/☾), "Sign out" | Sans |

- Dark mode toggle via `toggleTheme()` / `isDark()` signal
- New project button opens create modal

### F3 — Section Navigation

Sticky horizontal nav bar with section tabs:

| Section | Content filter | Count badge |
|---------|---------------|-------------|
| Context | Context files (builder, principles, codebase, references, quality, versions) | Static count (6) |
| All | All projects grouped by section | — |
| Active | Projects with running AI jobs | Dynamic |
| Ready to build | Projects with architecture.md or epic.md but no impl guide | Dynamic |
| Specced | Projects with implementation-guide.md | Dynamic |
| Braindumps | Projects with braindump.md only | Dynamic |
| Archive | Archived projects | Dynamic |

- `activeSection()` signal tracks which tab is selected
- Count badges are grey pills with `section-count` class
- Badges pulse on count change via `pulsingSections()` signal + `section-count-pulse` class
- 3px ink top border (nameplate rule) above the nav bar
- Clicking a tab calls `selectSection(s.id)`

### F4 — Status Bar

Always-visible inline bar between nav and search, four states:

| State | Visual | Content |
|-------|--------|---------|
| Idle | Green dot + "specview · idle — ready" | Default |
| Active | Amber shimmer + thinking dots + project name + step | During generation |
| Success | Green + project name + "done" | After completion |
| Failure | Red + "error" + message + retry button | On error |

- `mode()` signal: `'idle' | 'active' | 'success-flash' | 'failure'`
- `specGenProjectName()` and `specGenStep()` signals for active generation
- `statusFailureMsg()` for error text
- Retry button calls `retryLastOp()`
- Shimmer animation on `.gen-status-track` during active state

### F5 — Search & Filter

Full-width search input with count label:

- `searchQuery()` signal bound to input value
- `filteredProjects()` computed signal filters by query
- Count label: "N projects" when no query, "N matches" when filtering
- Hidden when viewing a single project or the context section
- `onSearch(value)` updates the signal

### F6 — All-Sections Grid (default view)

When `activeSection() === 'all'`, projects are grouped by taxonomy section in canonical order (Active → Ready to build → Specced → Braindumps → Archive):

Each section group has:
- Colored overline title via `[data-section]` attribute (Active=green, Specced=blue, Braindumps=muted)
- Section count pill badge
- Card grid using `auto-fill minmax(280px, 1fr)`

### F7 — Hero Grid (Active section)

The Active section uses a special `2fr 1fr 1fr` layout:
- First card (`hero-main`): 28px title, 4-line teaser clamp
- Remaining cards (`hero-secondary`): 16px title, 3-line clamp
- Only applies when `group.section === 'Active'`
- Falls back to single-card layout when only 1 active project

### F8 — Featured First Card

In every section, the first card gets enhanced styling:
- `.featured` class: 17px title (vs 15px regular)
- 3-line teaser clamp (vs 2-line regular)

### F9 — Project Cards

Each card in the grid:
- Title: `p.name`
- Teaser: `teaserFor(p)` — state-aware text from `project-teaser.ts`
- Meta: file count badge + section label
- Click: `selectProject(p.id)` opens the project
- Vertical-only separators (border-left, no horizontal borders)
- 20px 24px padding
- Hover: subtle background tint (`rgba(0,0,0,0.025)`)

### F10 — Section Taxonomy (Pure Logic)

`section-taxonomy.service.ts` classifies projects into sections based on file state:

```
archived flag → Archive
hasActiveJob → Active
has implementation-guide.md → Specced
has architecture.md or epic.md → Ready to build
default → Braindumps
```

Five canonical sections in display order: Active, Ready to build, Specced, Braindumps, Archive.

### F11 — Project Teasers (Pure Logic)

`project-teaser.ts` produces one-line teaser strings:

| Section | Teaser |
|---------|--------|
| Active + step known | "generating {step}..." |
| Specced + task count | "Implementation guide ready · N tasks" |
| Specced/Ready/Braindumps + content | First non-heading sentence from lead file |
| Braindumps (no content) | "Braindump — ready to generate" |
| Archive + date | "Archived {date}" |

`firstNonHeadingSentence(content)` skips `# - * > |` lines, returns first sentence (up to `.!?`), truncates at 120 chars.

### F12 — Single-Section View

When a specific section tab is clicked (not "All"):
- 3-column newspaper layout: `.file-column` with `border-right` dividers
- Column header: section label + count badge (first column only)
- Projects distributed across columns via `columns()` computed signal
- Same card structure as all-sections view

### F13 — Polling Error State

When project polling fails repeatedly:
- `pollingError()` signal set after `POLL_MAX_RETRIES` (30) retries
- Renders `[data-test="polling-error"]` div with error message
- "Error" overline label

### F14 — Update Banner

Dismissible notification banner:
- `updateBanner()` signal contains message text
- Dismiss button clears the signal

### F15 — Create Project Modal

`+ New` button in masthead opens a modal for creating a new project.
- `openCreateModal()` triggers the modal
- Form collects project name + initial braindump content

### F16 — Dark Mode

Toggle between light and dark themes:
- `isDark()` signal tracks state
- `toggleTheme()` switches
- Icon: ☀ (dark mode active, click for light) / ☾ (light mode active, click for dark)
- CSS custom properties switch between cream/ink and dark equivalents

### F17 — Context Section

Special non-project section for configuration files:
- 6 context cards: Builder, Principles, Codebase, References, Quality, Versions
- Grid layout distinct from project cards
- Click opens context editor
- Static count (not derived from projects)

---

## Testing Architecture

### Layer 1 — Feature Specifications (this document)

Features F1-F17 above. Updated when UX changes. Source of truth for what the overview page does.

### Layer 2 — Gherkin Scenarios (generated from features)

One `.feature` file per functional area. Gherkin describes user-facing behavior in Given/When/Then. These change rarely — only when features fundamentally change.

**New feature files needed for the overview page:**

```
e2e/features/overview-auth.feature          ← F1
e2e/features/overview-navigation.feature    ← F3, F12
e2e/features/overview-status-bar.feature    ← F4
e2e/features/overview-search.feature        ← F5
e2e/features/overview-grid.feature          ← F6, F7, F8, F9
e2e/features/overview-polling.feature       ← F13
```

Existing features stay (brainstorm, bootstrap-pipeline, epic-guide, billing-gate, pro-check). They test backend flows; the new files test frontend layout/interaction.

### Layer 3 — E2E Tests (generated from Gherkin)

Playwright step definitions executing against docker compose (CHAIN_PROVIDER=mock). These are the most stable tests — they verify user-visible behavior through a real browser. They should rarely change.

One step file per feature file, sharing common steps from `e2e/steps/common_steps.py`.

### Layer 4 — Unit + Component Tests (Angular Karma/Jasmine)

These test internal logic and DOM rendering. They change more often as implementation evolves.

**Pure function tests (highest value, cheapest to write):**

```
web-ng/src/app/services/section-taxonomy.service.spec.ts
  - archived project → Archive
  - active job → Active
  - has implementation-guide.md → Specced
  - has architecture.md → Ready to build
  - has epic.md → Ready to build
  - braindump.md only → Braindumps
  - empty specs array → Braindumps

web-ng/src/app/services/project-teaser.spec.ts
  - firstNonHeadingSentence: empty → ''
  - firstNonHeadingSentence: headers only → ''
  - firstNonHeadingSentence: sentence after header → returns sentence
  - firstNonHeadingSentence: multi-sentence → first only
  - firstNonHeadingSentence: long line → truncated at 120 + '…'
  - firstNonHeadingSentence: skips bullets, quotes, tables
  - projectTeaser: Active + step → "generating {step}…"
  - projectTeaser: Specced + taskCount → "Implementation guide ready · N tasks"
  - projectTeaser: Braindumps + content → first sentence
  - projectTeaser: Braindumps + empty → "Braindump — ready to generate"
  - projectTeaser: Archive + date → "Archived {date}"
  - countTasks: counts ## Task headings
```

**Component/template tests (verify DOM rendering + signal reactivity):**

```
web-ng/src/app/app.component.spec.ts (extend existing)
  - masthead renders title, date, tagline
  - section nav renders all 7 tabs
  - clicking a tab updates activeSection signal
  - section count badges show correct numbers
  - search input filters projects
  - search count label updates
  - all-sections view groups projects by section
  - hero grid applies to Active section only
  - featured class on first card per section
  - status bar shows correct state (idle/active/success/failure)
  - dark mode toggle switches icon
  - create modal opens on "+ New" click
  - login component shown when not authenticated
  - polling error renders data-test attribute
```

### Layer 5 — Visual Regression (stretch goal, not now)

Playwright screenshot comparison for key states. Catches CSS regressions in the newspaper aesthetic. Defer until E2E is stable.

---

## Gherkin Scenarios for Overview Page

### overview-auth.feature

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
```

### overview-navigation.feature

```gherkin
Feature: Overview — Section Navigation

  Scenario: Default view shows all sections grouped
    Given the user is logged in
    And projects exist in multiple sections
    When the app loads
    Then the "All" tab is active
    And projects are grouped by section with headers

  Scenario: Clicking a section tab filters to that section
    Given the user is logged in
    And projects exist in "Specced" section
    When the user clicks the "Specced" tab
    Then only specced projects are visible
    And the view switches to 3-column layout

  Scenario: Section count badges reflect project counts
    Given the user is logged in
    And 3 projects are in "Braindumps"
    And 5 projects are in "Specced"
    Then the "Braindumps" badge shows "3"
    And the "Specced" badge shows "5"

  Scenario: Clicking "All" returns to grouped view
    Given the user is on the "Specced" tab
    When the user clicks the "All" tab
    Then projects are grouped by section with headers
```

### overview-status-bar.feature

```gherkin
Feature: Overview — Status Bar

  Scenario: Idle state shows ready message
    Given the user is logged in
    And no generation is running
    Then the status bar shows "specview · idle — ready"
    And the status bar has the idle style

  Scenario: Active generation shows project and step
    Given the user is logged in
    And a spec generation is running for "My Project" at step "architecture"
    Then the status bar shows "My Project · architecture"
    And the status bar has the active style with shimmer

  Scenario: Generation failure shows error with retry
    Given the user is logged in
    And a generation has failed with "AI provider error"
    Then the status bar shows "error · AI provider error"
    And a retry button is visible
```

### overview-search.feature

```gherkin
Feature: Overview — Search & Filter

  Scenario: Search filters projects by name
    Given the user is logged in
    And 10 projects are loaded
    When the user types "auth" in the search bar
    Then only projects with "auth" in the name are visible
    And the count label shows the number of matches

  Scenario: Empty search shows all projects
    Given the user is logged in
    And the search bar contains "auth"
    When the user clears the search bar
    Then all projects are visible
    And the count label shows total project count

  Scenario: Search with no matches shows empty state
    Given the user is logged in
    When the user types "zzz-nonexistent" in the search bar
    Then the empty state message is visible
```

### overview-grid.feature

```gherkin
Feature: Overview — Project Grid

  Scenario: Active section uses hero grid layout
    Given the user is logged in
    And 3 projects are in the "Active" section
    Then the Active section uses the hero grid layout
    And the first card has the hero-main style

  Scenario: First card in each section is featured
    Given the user is logged in
    And projects exist in "Specced" section
    Then the first card in "Specced" has the featured style

  Scenario: Project cards show name, teaser, and file count
    Given the user is logged in
    And a project "Auth Reliability" exists with 8 files
    Then the card for "Auth Reliability" shows the project name
    And the card shows a teaser from the braindump
    And the card shows a badge with "8"

  Scenario: Clicking a project card opens it
    Given the user is logged in
    And a project "Auth Reliability" exists
    When the user clicks the "Auth Reliability" card
    Then the project detail view is visible

  Scenario: Cards have vertical-only separators
    Given the user is logged in
    And projects are visible in the grid
    Then cards have left borders but no top or bottom borders
```

### overview-polling.feature

```gherkin
Feature: Overview — Polling & Error Recovery

  Scenario: Polling error displayed after max retries
    Given the user is logged in
    And the API is unreachable
    When polling exceeds the maximum retry count
    Then the polling error message is visible
    And it contains "Refresh to resume"

  Scenario: Successful load clears any previous error
    Given the user is logged in
    And a polling error was previously shown
    When the API becomes reachable again
    Then the polling error message is not visible
```

---

## What the UX Epics Encoded (must be tested)

These UX decisions were made across 5+ epic branches and are now baked into CSS/template. They are not currently tested by anything. The Gherkin scenarios above cover the behavioral aspects; the component/unit tests cover the implementation details.

| UX Decision | Source Epic | Test Coverage |
|-------------|------------|---------------|
| 280px min card width, vertical-only separators | ux-grid-polish | overview-grid E2E + visual |
| Section color via `[data-section]` attribute | ux-grid-polish | component test: data-section present |
| Real braindump teasers (first prose sentence) | ux-grid-polish | project-teaser.spec.ts unit tests |
| Hero grid `2fr 1fr 1fr` for Active | app-ui-mockups | overview-grid E2E |
| Featured first card per section | app-ui-mockups | component test: `.featured` class |
| Status bar 4 states (idle/active/success/failure) | app-ui-mockups | overview-status-bar E2E |
| Grey pill count badges | ux-landing-grid-polish | component test: `.section-count` rendered |
| 3px ink nameplate rule | ux-polish-newspaper | visual regression (stretch) |
| Source Serif 4 teasers at 14px | app-ui-mockups | visual regression (stretch) |
| Taxonomy: file-state logic replaces ID-prefix | ux-reader-textops | section-taxonomy.spec.ts unit tests |
| Teaser: section-aware, state-aware copy | ux-reader-textops | project-teaser.spec.ts unit tests |
| Polling error after 30 retries | app.component.spec.ts | Already tested (extend) |
| Section count badge pulse on change | ux-grid-polish | component test: pulsing class |

---

## Execution Order

1. **Pure function unit tests first** — `section-taxonomy.service.spec.ts` and `project-teaser.spec.ts`. Highest value per effort. No DOM, no async, no mocks. Just inputs and outputs.

2. **Extend `app.component.spec.ts`** — Add template tests for masthead, nav, search, grid rendering, status bar states. Uses existing mock infrastructure.

3. **Gherkin feature files** — Write the 6 new `.feature` files above. These are the stable contract.

4. **E2E step definitions** — Implement Playwright steps for the new Gherkin scenarios. Run against `docker compose` with `CHAIN_PROVIDER=mock`.

5. **CI integration** — Add `ng test --watch=false --browsers=ChromeHeadless` to the GitHub Actions pipeline. Fail the build on test failure.

6. **Visual regression** (stretch) — Playwright screenshots for overview page states. Baseline + diff on PR.
