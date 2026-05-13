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

**Important: this list is a starting point, not the source of truth.** It was manually inventoried from the codebase at a point in time and is likely incomplete — Phase 2a/2b shipped new features (isolation, billing, upgrade page) that are appended at the bottom but not numbered. The spec pipeline should **explore the actual codebase** to discover all user-facing features rather than trust this list:

Scan these files for the complete feature surface:
- `web-ng/src/app/app.component.html` — root template, all UI sections
- `web-ng/src/app/app.component.ts` — all signals, computed values, methods
- `web-ng/src/app/app.routes.ts` — registered routes (upgrade, signup, etc.)
- `web-ng/src/app/components/` — standalone components (login, upgrade, usage-meter)
- `web-ng/src/app/services/` — all services (projects, auth, ai, subscription, token-lifecycle)
- `web-ng/src/app/interceptors/` — HTTP interceptors (auth, billing)
- `web-ng/src/app/state/` — shared state (usage)
- `web-ng/src/styles.css` — all CSS classes and dark-mode rules

The list below is the known inventory. Features may have been added, changed, or removed since this was written. Number them during spec generation, not before.

Additionally, review the `implementation-guide.md` and `exec-guide-summary.md` from every executed project to verify what was actually shipped. These are the projects with confirmed implementations (as of 2026-05-13):

| Project | What it shipped |
|---------|----------------|
| `auth-reliability-p0-1778576448` | JWT auth, credential persistence, @require_auth |
| `saas-phase1-security-auth-1778590275` | Login/register, token lifecycle, auth interceptor, security headers |
| `saas-phase2-isolation-billing-1778590276` | Project isolation, ownership decorator, 403 access denied UI, auto-migration |
| `saas-phase2b-billing-ui-1778665933` | SubscriptionService, upgrade page, billing interceptor, usage meter, lapsed state |
| `test-phase3-unit-component-1778592997` | 146 unit tests, section-taxonomy + project-teaser coverage |
| `ux-reader-textops-1778237000` | Reader view, text operations, navigation |
| `ux-grid-polish-1778368175` | Card grid layout, vertical separators, section colors |
| `ux-polish-newspaper-1778238000` | Newspaper typography, nameplate rule, column layout |
| `landing-phase3-polish-1778355280` | Landing page polish |
| `landing-polish-newspaper` | Landing newspaper feel |

Each of these may have introduced features not captured in the F1-F17 list below. The spec pipeline should read their impl guides to build the complete feature inventory.

Previously documented from: `app.component.html`, `app.component.ts`, `styles.css`, `section-taxonomy.service.ts`, `project-teaser.ts`. Cross-referenced against UX epics.

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

---

## SaaS Features (from Phase 2a/2b, shipped 2026-05-13)

These features were added after the original F1-F17 inventory. They need to be documented as testable specs alongside the overview page features. The spec pipeline should assign feature numbers and integrate them into the full feature inventory.

### Project Isolation (Phase 2a)

**User-scoped project listing:**
`GET /api/projects` returns only projects owned by the authenticated user. The `@require_project_ownership` decorator is on all 9 project routes. The listing uses `repository.list_for_user(g.current_user.id)` instead of a global filesystem scan.

**Ownership enforcement (403):**
Any authenticated user trying to access, edit, or delete a project they don't own receives a 403 "access denied" response. This applies to GET, PUT, DELETE, repair, coherence, and all 3 file-history routes.

**Access denied UI:**
When the frontend receives a 403 from the projects API, it shows a "You don't have access to this project" message with a "Back to projects" button, via the `accessDenied` signal on `AppComponent`. This is an `AccessDeniedError` subclass thrown by `ProjectsService.getProject()`.

**Dual-write project creation:**
`POST /api/projects` creates both a DB row (with `user_id`) via `SqlProjectRepository.create()` and a filesystem directory. If the DB write fails, nothing is created. If the filesystem fails, the DB row is rolled back.

**Auto-migration on startup:**
`create_app.py` checks if the `project` table is empty on startup. If so, it migrates all filesystem projects to DB rows assigned to `sam@specview.app` (overridable via `MIGRATION_OWNER_EMAIL`). Idempotent — skips if rows exist.

### Billing & Upgrade (Phase 2b)

**Upgrade button in masthead:**
Free users see an "Upgrade" button in `.masthead-actions` next to the "+ New" button. Hidden for Pro users via `@if (!subscription.isPro())`. Uses router navigation to `/upgrade`.

**Upgrade page (`/upgrade`):**
Standalone component rendered via `<router-outlet />` when `isFullPageRoute()` is true. Three states based on `subscription.plan()`:
- `free`: Pricing comparison (Free vs Pro), "Upgrade to Pro — $29/mo" button → `startCheckout()`
- `lapsed`: "Update your payment method" messaging, CTA → Stripe Customer Portal
- `pro`: "You're on Pro" confirmation, "Manage subscription" → Customer Portal

**Post-checkout verification:**
When the URL contains `?session_id=...` (Stripe redirects here after payment), the component calls `subscription.verifySession(sessionId)` which hits `GET /api/billing/verify-session`. This endpoint retrieves the session from Stripe, validates ownership via `metadata.user_id`, and writes `plan='pro'` to the DB if paid. Then calls `subscription.refresh()` to update the plan signal. Shows "Welcome to Pro" on success.

**SubscriptionService (signal-based):**
`plan = signal<Plan>('free')` where `Plan = 'free' | 'pro' | 'lapsed'`. `isPro = computed(() => this.plan() === 'pro')`. Methods: `refresh()` (GET /api/billing/status), `startCheckout()` (POST → Stripe redirect), `verifySession(sessionId)`. Constructor calls `refresh()` on injection.

**Usage meter pill:**
`<app-usage-meter />` in `.masthead-actions`. Reads from `usageRemaining` signal (populated by billing interceptor from `X-Usage-Remaining` response header). Shows "N/M remaining". Hidden when `isPro()` or when signal is null. Warning styling (red) at remaining ≤ 1.

**Billing interceptor:**
Dedicated `billingInterceptor` (separate from auth). Registered after `authInterceptor` in `app.config.ts`. Two responsibilities:
1. Reads `X-Usage-Remaining` header from every response → updates `usageRemaining` signal
2. Catches 429 responses → reads plan from `SubscriptionService` → navigates to `/upgrade?reason=limit_reached&feature=...` (free) or `/upgrade?reason=payment_lapsed` (lapsed). Pro users getting 429 logs a warning but doesn't navigate.

**Lapsed plan state:**
`invoice.payment_failed` webhook writes `plan='lapsed'` (not 'free') to `User.plan`. This distinguishes "never paid" from "payment failed". The upgrade page shows different messaging and CTA for lapsed vs free. The `billing_status()` route maps `lapsed` → `free` for the OpenAPI Plan enum while the internal DB carries the tri-state.

**Usage limits:**
`@check_usage_limit(feature)` decorator on AI routes. Daily caps: `bootstrap=30, task_gen=100, spec_gen=50, text=50, skill=20`. Pro users bypass entirely. Returns 429 with `{error, feature, limit, reset_at, upgrade_url}`. Emits `X-Usage-Remaining: {remaining}/{limit}` header on successful responses.
