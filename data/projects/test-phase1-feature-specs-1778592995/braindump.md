# Test Phase 1: Feature Specs & Testing Architecture

## What this is

Document every user-facing feature of the Specview overview page as a testable specification. These feature specs become the source of truth — Gherkin scenarios (Phase 2) and unit tests (Phase 3) are derived from them. When features change, specs get updated first, then tests follow.

This phase also establishes the testing architecture: what tools exist, what's missing, and how the layers fit together.

---

## Current Testing Infrastructure (fact-checked 2026-05-12)

### What already exists

**Angular unit tests (Karma + Jasmine):**
- `web-ng/src/app/app.component.spec.ts` — 4 test cases: component creation, polling lifecycle (timer stops after max retries), polling error signal rendering, cleanup on destroy
- `web-ng/src/app/services/projects.service.mock.ts` — spy-based mock for ProjectsService
- `web-ng/src/app/services/ai.service.mock.ts` — spy-based mock for AiService
- `web-ng/karma.conf.js` — Chrome + ChromeHeadlessCI, coverage reporter to `./coverage/web-ng`
- Dependencies: karma 6.4.0, jasmine-core 5.4.0, @types/jasmine 5.1.0

**E2E tests (pytest-bdd + Playwright):**
- `e2e/features/` — 5 Gherkin feature files, 10 scenarios covering backend flows:
  - `brainstorm.feature` — text submission, error handling
  - `bootstrap-pipeline.feature` — async spec generation, failure polling
  - `epic-guide.feature` — guide generation, timeout error
  - `billing-gate.feature` — free tier limit, pro tier bypass
  - `pro-check.feature` — pro plan routing, lookup failure
- `e2e/steps/common_steps.py` — 193 lines of Given/When/Then step definitions
- `e2e/pages/app_page.py` — page object (load, enter_text, click, is_visible, wait_visible)
- `e2e/conftest.py` — session fixtures spinning up Flask (port 5001, CHAIN_PROVIDER=mock) + Angular dev server (port 4201)
- Dependencies: pytest-bdd >= 7.0, pytest-playwright >= 0.5, playwright >= 1.44

**Product behavior contract:**
- `product-behavior.md` — 5 core flows mirrored 1:1 by `e2e/features/`. Per CLAUDE.md: any flow change must be reflected in both.

### What's missing

- No service unit tests (section-taxonomy, project-teaser, projects.service)
- No template/component tests beyond the smoke test
- No tests for any UX feature delivered across 5+ epic branches
- No CI pipeline for frontend tests
- Existing E2E features cover backend flows but not overview page layout/navigation
- No visual regression tests

---

## Testing Architecture

Four layers, each derived from the one above:

```
Feature Specs (this document)
  ↓ generates
Gherkin Scenarios (Phase 2) — stable behavioral contract, rarely change
  ↓ implements
E2E Tests (Phase 2) — Playwright against docker compose, verify user-visible behavior
  ↓ complements
Unit & Component Tests (Phase 3) — Karma/Jasmine, test internal logic + DOM, change more often
```

**Why this order:**
- Feature specs are the requirements — they must exist before any test is written
- Gherkin + E2E test user-facing behavior and are stable (layout changes don't break them)
- Unit tests verify implementation details and catch regressions faster but need updating when code changes
- E2E tests run against `CHAIN_PROVIDER=mock` in docker compose — no real AI calls

---

## Overview Page — Feature Specifications

Features documented from actual code: `app.component.html` (505 lines), `app.component.ts` (~700 lines), `styles.css` (1,581 lines), `section-taxonomy.service.ts`, `project-teaser.ts`. Cross-referenced against UX epics: `ux-grid-polish`, `ux-landing-grid-polish`, `ux-polish-newspaper`, `app-ui-mockups`, `ux-reader-textops`.

### F1 — Auth Gate

The entire page is behind an auth check. Unauthenticated users see `<app-login />`, authenticated users see the overview.

- Source: `app.component.html` line 1 — `@if (!auth.isLoggedIn())`
- `auth.isLoggedIn()` is a signal from `AuthService` (JWT in localStorage as `specview_jwt`)
- `LoginComponent` is a standalone component imported by AppComponent

### F2 — Masthead

Editorial newspaper header with three regions:

| Element | Content | Typography |
|---------|---------|------------|
| Edition | "Spec Doc" | Sans, small |
| Date | Today's date (e.g. "Tuesday, May 12, 2026") | Sans, muted |
| Title | "Specview" | 64px Playfair Display |
| Tagline | "All the Specs Fit to Read" | Source Serif 4, italic |
| Actions | "+ New" button, theme toggle (☀/☾), "Sign out" | Sans |

- `today` property formats current date
- `openCreateModal()` opens project creation
- `toggleTheme()` / `isDark()` signal controls dark mode
- `logout()` clears JWT and resets `isLoggedIn`

### F3 — Section Navigation

Sticky horizontal nav bar with 7 tabs:

| Tab | ID | Filters to |
|-----|-----|------------|
| Context | `context` | 6 config files (builder, principles, codebase, references, quality, versions) |
| All | `all` | All projects grouped by section |
| Active | `Active` | Projects with running AI jobs |
| Ready to build | `Ready to build` | Projects with architecture.md or epic.md but no impl guide |
| Specced | `Specced` | Projects with implementation-guide.md |
| Braindumps | `Braindumps` | Projects with braindump.md only |
| Archive | `Archive` | Archived projects |

- `activeSection()` signal tracks selected tab
- Count badges: grey pills with `section-count` class, dynamic from `sectionCounts()` computed signal
- Badges pulse on change: `pulsingSections()` signal + `section-count-pulse` CSS class
- 3px ink top border above nav (nameplate rule from ux-polish-newspaper)
- Source: `app.component.html` lines 30-46, `app.component.ts` `NAV_SECTIONS` constant

### F4 — Status Bar

Always-visible inline bar between nav and search. Four mutually exclusive states driven by `mode()` signal:

| State | `mode()` value | Visual |
|-------|---------------|--------|
| Idle | `idle` | Green dot · "specview · idle — ready" |
| Active | `active` | Amber shimmer + thinking dots · project name · step name |
| Success | `success-flash` | Green · project name · "done" |
| Failure | `failure` | Red · "error" · message · retry button |

- Source: `app.component.html` lines 49-92
- Active state shows `specGenProjectName()` and `specGenStep()` signals
- Failure state shows `statusFailureMsg()` signal and `retryLastOp()` button
- Shimmer animation via `.gen-status-track` CSS
- Colors from playground 5.7: idle=#1a6b30, active=#7a5800, failure=#C41E3A

### F5 — Search & Filter

Full-width search input with count label, hidden when viewing a project or context section:

- `searchQuery()` signal bound to input via `onSearch(value)`
- `filteredProjects()` computed signal filters projects by name match
- Count label: "N projects" (no query) or "N matches" (with query)
- Source: `app.component.html` lines 109-126

### F6 — All-Sections Grid (default view)

When `activeSection() === 'all'`, projects grouped by taxonomy section in canonical order:

- `projectsBySection()` computed signal returns `{ section, projects }[]`
- Each section group has: colored overline title, count pill badge, card grid
- Overline color via `[data-section]` CSS attribute selector: Active=green, Specced=blue, Braindumps=muted
- Grid: `auto-fill minmax(280px, 1fr)` with vertical-only separators
- Source: `app.component.html` lines 146-173

### F7 — Hero Grid (Active section only)

Special layout for the Active section group:

- CSS class `hero-grid` applied when `group.section === 'Active'`
- Layout: `2fr 1fr 1fr` (lead story + two secondaries)
- First card: `.hero-main` — 28px title, 4-line teaser clamp
- Remaining: `.hero-secondary` — 16px title, 3-line clamp
- Single-project fallback: `hero-grid--single` class
- Source: `app.component.html` lines 153-155

### F8 — Featured First Card

Every section's first card gets enhanced styling:

- `.featured` class on first card (`let pi = $index`, `[class.featured]="pi === 0"`)
- 17px title (vs 15px regular), 3-line clamp (vs 2-line)
- Source: `app.component.html` line 159

### F9 — Project Cards

Each card displays:

- Title: `p.name`
- Teaser: `teaserFor(p)` — delegates to `projectTeaser()` from `project-teaser.ts`
- Meta: file count badge (`p.specs.length`) + section label (`sectionForProject(p)`)
- Click handler: `selectProject(p.id)` opens project detail view
- Styling: 20px 24px padding, vertical-only separators (border-left), hover tint `rgba(0,0,0,0.025)`

### F10 — Section Taxonomy (Pure Logic)

`section-taxonomy.service.ts` — pure function `sectionFor(project, hasActiveJob)`:

```
archived → Archive
hasActiveJob → Active
has implementation-guide.md → Specced
has architecture.md or epic.md → Ready to build
default → Braindumps
```

Five sections in display order: Active, Ready to build, Specced, Braindumps, Archive. Exported as `SECTION_ORDER`.

### F11 — Project Teasers (Pure Logic)

`project-teaser.ts` — pure functions:

**`firstNonHeadingSentence(content)`:** Skips lines starting with `# - * > |`, returns first sentence (up to `.!?` + whitespace/EOL), truncates at 120 chars with `…`.

**`countTasks(content)`:** Counts `## Task` headings in implementation guide.

**`projectTeaser(section, activeStep, leadFileContent, taskCount, archivedAt)`:**

| Condition | Output |
|-----------|--------|
| Active + step known | "generating {step}…" |
| Active + content | First non-heading sentence |
| Specced + taskCount > 0 | "Implementation guide ready · N tasks" |
| Specced + content | First non-heading sentence |
| Ready to build + content | First non-heading sentence |
| Ready to build (no content) | "Ready to build" |
| Braindumps + content | First non-heading sentence |
| Braindumps (no content) | "Braindump — ready to generate" |
| Archive + date | "Archived {formatted date}" |
| Archive (no date) | "Archived" |
| Fallback | "" |

### F12 — Single-Section View

When a specific section tab is clicked (not "All" or "Context"):

- 3-column newspaper layout via `columns()` computed signal
- `.file-column` with `border-right` dividers
- Column header with section label + count badge (first column only)
- Same card structure as all-sections view
- Source: `app.component.html` lines 174-198

### F13 — Polling & Error Recovery

Background polling for project updates:

- `REFRESH_INTERVAL = 30_000` (30s) for project list refresh
- `POLL_MAX_RETRIES = 30` — after 30 consecutive failures, polling stops
- `pollingError()` signal set with error message
- `[data-test="polling-error"]` div renders when signal is truthy
- Source: `app.component.spec.ts` already tests this (4 cases)

### F14 — Update Banner

Dismissible notification:

- `updateBanner()` signal contains message text
- Dismiss button: `updateBanner.set('')`
- Source: `app.component.html` lines 95-99

### F15 — Create Project Modal

- `+ New` button in masthead calls `openCreateModal()`
- Collects project name + initial braindump content
- Creates project via ProjectsService

### F16 — Dark Mode

- `isDark()` signal, `toggleTheme()` method
- Icon toggle: ☀ (in dark mode) / ☾ (in light mode)
- CSS custom properties switch between light (cream #FFFEF9 / ink #121212) and dark equivalents

### F17 — Context Section

Non-project section for 6 configuration files:

- Builder, Principles, Codebase, References, Quality, Versions
- `CONTEXT_FILES` constant with key, label, desc
- Rendered as `.context-grid` with `.context-card` elements
- Click handler: `openContext(f.key)`

---

## UX Decisions That Must Be Tested

Decisions encoded in CSS/template across 5+ UX epic branches. None currently have test coverage.

| Decision | Source | Affects |
|----------|--------|---------|
| 280px min card width + vertical-only separators | ux-grid-polish | F9 card layout |
| Section color via `[data-section]` attribute | ux-grid-polish | F6 section headers |
| Real braindump teasers (first prose sentence) | ux-grid-polish | F11 teaser logic |
| Hero grid `2fr 1fr 1fr` for Active only | app-ui-mockups | F7 hero grid |
| Featured first card (17px title) | app-ui-mockups | F8 featured card |
| Status bar 4 states with specific colors | app-ui-mockups | F4 status bar |
| Grey pill count badges | ux-landing-grid-polish | F3 nav badges |
| Badge pulse on count change | ux-grid-polish | F3 nav badges |
| 3px ink nameplate rule above nav | ux-polish-newspaper | F3 nav styling |
| Source Serif 4 teasers at 14px | app-ui-mockups | F9 card typography |
| Section taxonomy: file-state logic | ux-reader-textops | F10 taxonomy |
| Teaser: section-aware state-aware copy | ux-reader-textops | F11 teaser logic |
| Canonical section order in "All" view | ux-reader-textops | F6 section grouping |
| 3-column layout in single-section view | ux-polish-newspaper | F12 column layout |
