# Feature Specs — Specview

**Note:** The draft F1–F17 numbering is retired. This document replaces it with a
domain-prefixed inventory derived from the live codebase and all executed
implementation guides. Use OV- for Overview/app-shell features and SA- for
SaaS/auth/billing features.

---

## Section 1 — Feature Inventory

### How this inventory was built

Every `implementation-guide.md` and `exec-guide-summary.md` in the nine executed
project directories was read. The Angular source tree under `web-ng/src/app/` was
scanned file by file. Features were cross-referenced between guides and code; any
discrepancy is flagged inline.

Source projects scanned:

| Project slug | Domain |
|---|---|
| `auth-reliability-p0-1778576448` | Infrastructure / chain |
| `saas-phase1-security-auth-1778590275` | Auth, registration, token lifecycle, security headers |
| `saas-phase2-isolation-billing-1778590276` | Project isolation, ownership enforcement, multi-tenancy |
| `saas-phase2b-billing-ui-1778665933` | Stripe billing, subscription service, upgrade page, usage meter |
| `test-phase3-unit-component-1778592997` | Test coverage (not a user-facing feature; listed under SA for completeness) |
| `ux-reader-textops-1778237000` | Reader, AI text ops, sidebar, status bar |
| `ux-grid-polish-1778368175` | Grid card breathing room, teasers, section color |
| `ux-polish-newspaper-1778238000` | Typography tokens, dark mode, spec ordering, XSS fix |
| `landing-phase3-polish-1778355280` | Landing page, auth gate, signal hygiene, word count |
| `landing-polish-newspaper` | Landing section nav, dark mode parity |

---

### OV — Overview page features

OV features live in the authenticated app shell. Primary source files are
`app.component.ts`, `app.component.html`, and the services under `services/`.

---

#### OV-01 — Auth gate

**Source:** `web-ng/src/app/app.component.html` (line 1–4),
`web-ng/src/app/services/auth.service.ts`

The app shell renders a `<router-outlet />` instead of the project grid when
`auth.isLoggedIn()` is false, forcing unauthenticated users to the login or signup
route. The signal `isLoggedIn` is owned by `TokenLifecycleService` and exposed via
`AuthService`.

---

#### OV-02 — Masthead nameplate

**Source:** `web-ng/src/app/app.component.html` (masthead section),
`web-ng/src/app/app.component.ts` (`today` field)

Full-width newspaper-style header rendered on every authenticated page. Contains the
edition label ("Spec Doc"), the current date, the application title ("Specview"), and
the tagline. Date is computed once at component construction from `new Date()`.

---

#### OV-03 — Section navigation bar

**Source:** `web-ng/src/app/app.component.ts` (`NAV_SECTIONS` constant, `selectSection()`),
`web-ng/src/app/app.component.html` (`.section-nav` block)

A horizontal button row with sections: Context, All, Active, Ready to build, Specced,
Braindumps, Archive. Each button shows a count badge derived from `sectionCounts`
computed signal. Clicking a section filters the project grid and closes any open
expanded panel.

---

#### OV-04 — Section count pulse animation

**Source:** `web-ng/src/app/app.component.ts` (`pulsingSections` signal, `effect()` in constructor)

When a project changes section (e.g. moves from Braindumps to Active because spec-gen
starts), the corresponding count badge pulses for 250 ms. Implemented via an effect
that diffs previous and current `sectionCounts()` and temporarily adds the section key
to a `pulsingSections` signal.

---

#### OV-05 — Generation status bar

**Source:** `web-ng/src/app/app.component.html` (`.gen-status-bar` block),
`web-ng/src/app/app.component.ts` (`statusMode`, `statusFailureMsg`, `specGenStep`,
`specGenProjectName` signals)

A four-state bar rendered between the section nav and search box. States: idle
(dot + "specview · idle — ready"), active (animated dots + project name + current step),
success-flash (2 s green confirmation), failure (error message + retry button). State
transitions are driven by the `statusMode` signal.

---

#### OV-06 — Update banner

**Source:** `web-ng/src/app/app.component.html` (`.update-banner` block),
`web-ng/src/app/app.component.ts` (`updateBanner` signal, `checkForUpdates()`)

A dismissable top banner that appears for 5 s when the background poll detects a new
project count (e.g. "+1 new"). Dismissed manually or automatically via `setTimeout`.

---

#### OV-07 — Search / filter bar

**Source:** `web-ng/src/app/app.component.html` (`.search-bar` block),
`web-ng/src/app/app.component.ts` (`searchQuery` signal, `onSearch()`, `filteredProjects`)

A text input visible only in grid view (hidden for Context section and expanded panel).
Filters by project name or ID substring. Shows a live match count or total project count.

---

#### OV-08 — Project grid with taxonomy grouping

**Source:** `web-ng/src/app/app.component.html` (`.file-grid` / `.section-group` blocks),
`web-ng/src/app/app.component.ts` (`projectsBySection` computed, `columns` computed),
`web-ng/src/app/services/section-taxonomy.service.ts`

In the "All" section, projects are grouped into labelled section groups in canonical
order (Active → Ready to build → Specced → Braindumps → Archive) with section headers
and counts. In named sections, a 3-column masonry layout is used instead. The taxonomy
function `sectionFor()` derives placement from file state, not from slug prefix.

---

#### OV-09 — Project cards with teasers

**Source:** `web-ng/src/app/app.component.html` (`.file-item` blocks),
`web-ng/src/app/app.component.ts` (`teaserFor()` method),
`web-ng/src/app/services/project-teaser.ts`

Each card shows a project name, a one-line teaser, and a meta row (spec count badge +
section label). The teaser is section-aware: Active projects show the current generation
step or braindump extract; Specced projects show task count or guide extract; Braindumps
show the first non-heading sentence; Ready to build shows architecture/epic extract.
The first card in each section group receives a `.featured` CSS class.

---

#### OV-10 — Polling / background refresh

**Source:** `web-ng/src/app/app.component.ts` (`checkForUpdates()`, `pollTimer`,
`genPollTimer`, `POLL_MAX_RETRIES`)

A `setInterval` fires every 30 s to call `listProjects()`. A second interval fires
every 10 s during active spec-gen. Both are cleared on component destroy or user logout.
After 30 consecutive failures the poll stops and `pollingError` signal is set. `pollOk`
and `lastSyncAt` / `lastSyncElapsed` track live status.

---

#### OV-11 — Dark mode toggle

**Source:** `web-ng/src/app/app.component.ts` (`toggleTheme()`, `isDark` signal),
`web-ng/src/app/app.component.html` (theme toggle button)

Masthead button that toggles `[data-theme="dark"]` on `<html>` and persists the
choice to `localStorage`. Reads saved preference on `ngOnInit`.

---

#### OV-12 — Context viewer

**Source:** `web-ng/src/app/app.component.ts` (`openContext()`, `contextContent`,
`contextTitle`, `contextFiles` constant),
`web-ng/src/app/app.component.html` (`.context-grid` / `.context-card` blocks),
`web-ng/src/app/services/projects.service.ts` (`getContext()`)

Six context cards in the Context section (Builder, Principles, Codebase, References,
Quality, Versions). Clicking a card calls `GET /api/context/:key`, sets `contextContent`
and `contextTitle` signals, and opens the expanded panel in read-only mode with the
markdown rendered via `marked` + `DOMPurify`.

---

#### OV-13 — Create project modal

**Source:** `web-ng/src/app/app.component.html` (`.modal` block),
`web-ng/src/app/app.component.ts` (`openCreateModal()`, `closeCreateModal()`,
`createProject()`, `showCreateModal` signal)

A modal dialog with project name input and braindump textarea. On submit, the modal
closes immediately, the project is created via `POST /api/projects`, and spec-gen begins
asynchronously (status visible via OV-05). Backdrop click dismisses the modal.

---

#### OV-14 — Spec-gen pipeline with incremental file save

**Source:** `web-ng/src/app/app.component.ts` (`_runBootstrap()`, `createProject()`,
`generateFromBraindump()`, `specGenLoading`, `specGenStep`, `specGenProjectName`),
`web-ng/src/app/services/projects.service.ts` (`startBootstrap()`, `pollBootstrap()`,
`saveFile()`)

Full braindump-to-specs pipeline. Calls `POST /api/ai/text/bootstrap-project`, then
polls `GET /api/ai/text/bootstrap-project/status/:job_id` every 2.5 s. As each AI step
completes (`partial_files` in poll response), files are saved to disk and the active
project signal refreshes, making the sidebar file list grow in real time. Supports both
new-project creation and re-generation from an existing braindump.

---

#### OV-15 — Expanded project reader panel

**Source:** `web-ng/src/app/app.component.html` (`.expanded-panel` block),
`web-ng/src/app/app.component.ts` (`showExpanded`, `expandedTitle`, `expandedProject`,
`parsedContent`, `activeFileType`)

An animated slide-in panel (Angular `@panelEnter` animation) that replaces the grid
when a project is selected. Contains a sticky sidebar (OV-16) and a main content area.
The main area renders the active spec as sanitized markdown HTML, with an overline
label (`ARCHITECTURE`, `EPIC`, etc.) and a word count meta line above the title.

---

#### OV-16 — Expanded reader sidebar

**Source:** `web-ng/src/app/app.component.html` (`.expanded-sidebar` block),
`web-ng/src/app/app.component.ts` (`selectFile()`, `activeFile`, `fileOpState`)

Sticky sidebar inside the expanded panel. Contains a back button, project name, the
spec file nav (buttons for each file in canonical order), per-file status dots
(running / success / failure), a sidebar status row (OV-17), and the Generate /
AI op chip sections. File nav ordering is canonical:
braindump → analysis → epic → architecture → timeline → implementation-guide.

---

#### OV-17 — Sidebar status row

**Source:** `web-ng/src/app/app.component.html` (`.sidebar-status` block),
`web-ng/src/app/app.component.ts` (`statusMode`, `statusFailureMsg`, `retryLastOp()`)

A compact four-state indicator row in the sidebar, positioned below the file nav.
States mirror OV-05 (idle, active, success-flash, failure). The failure state shows a
retry button. This row is project-reader-specific; OV-05 is the global status bar.

---

#### OV-18 — Per-file dot tracking

**Source:** `web-ng/src/app/app.component.ts` (`fileOpState` signal, `activeOpFile`,
`_setFileRunning()`, `_setFileSuccess()`, `_setFileFailure()`)

Each spec file button in the sidebar nav displays a colored dot when an AI text op is
running or has just completed for that file. The dot auto-clears 1.5 s after success.
Failure dots persist until the user dismisses or retries.

---

#### OV-19 — Generate Specs button (from braindump)

**Source:** `web-ng/src/app/app.component.html` (`.sidebar-generate[data-test="pipeline-trigger"]`),
`web-ng/src/app/app.component.ts` (`canGenerateSpecs` computed, `generateFromBraindump()`)

Visible in the sidebar when a project has no `analysis.md` yet. Clicking it triggers
the full spec-gen pipeline (OV-14) from the project's existing `braindump.md`.

---

#### OV-20 — Generate Guide button (epic guide)

**Source:** `web-ng/src/app/app.component.html` (`.sidebar-generate[data-test="epic-guide-trigger"]`),
`web-ng/src/app/app.component.ts` (`canGenerateEpicGuide` computed, `generateEpicGuide()`),
`web-ng/src/app/services/projects.service.ts` (`startEpicGuide()`, `pollEpicGuide()`)

Visible in the sidebar when a project has `epic.md` but no `implementation-guide.md`.
Calls `POST /api/projects/:id/generate-epic-guide`, polls for completion, then refreshes
the active project and opens the new guide file.

---

#### OV-21 — AI text ops chips

**Source:** `web-ng/src/app/app.component.html` (`.sidebar-ops` block),
`web-ng/src/app/app.component.ts` (`toggleOp()`, `runOp()`, `activeOp` signal),
`web-ng/src/app/services/ai.service.ts`

Eight op chips in the sidebar: Brainstorm (braindump only), Expand, Compress, Clarify,
Simplify, TL;DR, Bullets, Style. Each chip sends the active spec content to the
corresponding backend endpoint via `AiService` (which delegates to the generated
ng-openapi-gen client). Only one op can be active at a time.

---

#### OV-22 — Style preset chips

**Source:** `web-ng/src/app/app.component.html` (`.style-presets.sidebar-style-presets` block),
`web-ng/src/app/app.component.ts` (`STYLE_PRESETS`, `runStyle()`)

Five style presets (Concise, Technical, Executive, Narrative, Punchy) rendered below
the chip row when "Style…" is active. Clicking a preset calls `AiService.styleAs()`
with the chosen style string.

---

#### OV-23 — AI result panel with diff view

**Source:** `web-ng/src/app/app.component.html` (`.diff-unified`, `.brainstorm-result` blocks),
`web-ng/src/app/app.component.ts` (`aiResult`, `diffHtmlUnified`, `parsedAiResult`,
`isAdditiveOp`, `computeParagraphDiff()`)

After an AI op completes, the result is shown in the main content area. Non-additive
ops (expand, compress, clarify, etc.) render a paragraph-level diff with green/red
block highlighting. Additive ops (brainstorm, TL;DR) render the result as plain
markdown with no diff.

---

#### OV-24 — Result toolbar (Apply / Copy / Dismiss / Latency)

**Source:** `web-ng/src/app/app.component.html` (`.editor-toolbar--floating` block),
`web-ng/src/app/app.component.ts` (`applyResult()`, `copyResult()`, `dismissResult()`,
`aiLatencyMs`, `copied`)

A floating toolbar that appears when an AI result is pending. Shows latency badge,
Apply (writes result to spec + saves to API), Copy (clipboard), and Dismiss buttons.
Apply pushes the previous content to the undo stack.

---

#### OV-25 — Undo / redo stack

**Source:** `web-ng/src/app/app.component.ts` (`undoStack`, `redoStack`, `canRevert`,
`canRedo`, `undoVersion()`, `redoVersion()`)

In-memory undo/redo per `projectId/filename` key. Undo and Redo buttons are shown as
sidebar op chips when a history entry exists. Undo reverts to the previous content and
saves it. Redo re-applies a reverted version.

---

#### OV-26 — Brainstorm follow-up input

**Source:** `web-ng/src/app/app.component.html` (`.brainstorm-followup` block),
`web-ng/src/app/app.component.ts` (`followupBrainstorm()`, `brainstormQuestion`)

When the Brainstorm op result is displayed, a follow-up text input allows iterative
questioning. Each follow-up call appends the previous result as context. Enter key and
button both submit.

---

#### OV-27 — Generate Specs from brainstorm result

**Source:** `web-ng/src/app/app.component.html` (`.brainstorm-generate-btn`),
`web-ng/src/app/app.component.ts` (`generateFromBrainstormResult()`)

A button shown below the brainstorm result (when no specs exist yet) that feeds the
brainstorm output plus original braindump into the full spec-gen pipeline as an
enriched input.

---

#### OV-28 — Section taxonomy service

**Source:** `web-ng/src/app/services/section-taxonomy.service.ts`

Pure-function module (no DI, no class) that maps a project's file list and active-job
state to one of five sections: Active, Ready to build, Specced, Braindumps, Archive.
Replaces the old ID-prefix `categorise()` approach. Used by grid and expanded panel.

---

#### OV-29 — Project teaser service

**Source:** `web-ng/src/app/services/project-teaser.ts`

Pure-function module providing `projectTeaser()` (section-aware teaser string),
`firstNonHeadingSentence()` (first non-heading line from markdown), and
`countTasks()` (count `## Task` headings in implementation guides). Used by
`teaserFor()` in the root component.

---

#### OV-30 — Word count pipe

**Source:** `web-ng/src/app/word-count.pipe.ts`

Standalone Angular pipe `wordCount` that returns an integer word count for any string.
Used in the expanded panel meta line: "Project name · N words".

---

#### OV-31 — Panel slide animation

**Source:** `web-ng/src/app/app.component.ts` (`@panelEnter` trigger)

Enter/leave animation on the `.expanded-panel`. On enter: sidebar slides in from the
left (250 ms), main area slides up from below (250 ms, 40 ms delay). On leave: both
animate out in 150 ms.

---

#### OV-32 — Spec file canonical ordering

**Source:** `web-ng/src/app/services/projects.service.ts` (`CANONICAL_ORDER`, `sortSpecs()`)

The `sortSpecs()` function sorts a project's spec files into the canonical reading order:
braindump → analysis → epic → architecture → timeline → implementation-guide. Unknown
files sort alphabetically after the known set. Applied to every project fetched from the
API.

---

#### OV-33 — Markdown rendering with XSS sanitization

**Source:** `web-ng/src/app/app.component.ts` (`parsedContent`, `diffHtmlUnified`,
`parsedAiResult`)

All markdown rendering passes through `marked.parse()` wrapped with
`DOMPurify.sanitize()` before being set via `bypassSecurityTrustHtml`. No API content
is injected into the DOM without sanitization.

---

### SA — SaaS / auth features

SA features live in auth, billing, and the supporting interceptor / state layers.

---

#### SA-01 — Login page

**Source:** `web-ng/src/app/components/login/login.component.ts`

Standalone component rendered at `**` (catch-all route) when unauthenticated. Full-page
centered card with email and password inputs. On submit calls `AuthService.login()`;
on failure sets a signal-driven error message. Loading state disables the submit button.

---

#### SA-02 — Signup / registration page

**Source:** `web-ng/src/app/pages/signup/signup.component.ts`,
`web-ng/src/app/pages/signup/signup.component.html`

Standalone component at `/signup` route. Email + password form with client-side
validation (required, min 8 chars). On submit calls `AuthService.register()`. Error
messages for 409 Conflict, 429 Too Many Requests, and generic failure. On success
navigates to `/`.

---

#### SA-03 — Auth service

**Source:** `web-ng/src/app/services/auth.service.ts`

Injectable that owns `login()`, `register()`, and `signOut()` methods. Delegates token
storage and the `isLoggedIn` signal to `TokenLifecycleService`. Does not touch
`localStorage` directly. Exposes `getStoredJwt()` for the interceptor's non-refresh path.

---

#### SA-04 — Token lifecycle service

**Source:** `web-ng/src/app/services/token-lifecycle.service.ts`

Manages token storage in `localStorage`, JWT expiry decoding, proactive refresh within
a 1-hour window, and a mutex promise that prevents concurrent refresh calls. Owns the
`isLoggedIn` signal. Calls `POST /api/auth/refresh` when the token is within the refresh
window. On terminal 401, calls `handleAuthFailure()` which clears state and navigates
to `/login`.

---

#### SA-05 — Auth HTTP interceptor

**Source:** `web-ng/src/app/interceptors/auth.interceptor.ts`

Functional interceptor registered first in `app.config.ts`. For every request except
`/api/auth/login`, `/register`, and `/refresh`, calls `TokenLifecycleService.getToken()`
(which may trigger a proactive refresh) and attaches the Bearer token. On 401 response,
calls `handleAuthFailure()`.

---

#### SA-06 — Project ownership 403 handling

**Source:** `web-ng/src/app/services/projects.service.ts` (`AccessDeniedError`,
`getProject()`),
`web-ng/src/app/app.component.ts` (`accessDenied` signal, `selectProject()`),
`web-ng/src/app/app.component.html` (`.access-denied-state` block)

`getProject()` converts a 403 HTTP error into a typed `AccessDeniedError`. The root
component catches it in `selectProject()` and sets `accessDenied(true)`, which renders
a full-panel "You don't have access to this project" message with a back button.

---

#### SA-07 — Subscription service

**Source:** `web-ng/src/app/services/subscription.service.ts`

Injectable with `plan` signal (free / pro / lapsed), computed `isPro`, and methods:
`refresh()` (calls `GET /api/billing/status`), `startCheckout()` (calls
`POST /api/billing/create-checkout-session`, redirects to Stripe), and
`verifySession(sessionId)` (calls `GET /api/billing/verify-session` to confirm payment).
`refresh()` is called on construction so plan state is populated at app boot.

---

#### SA-08 — Billing HTTP interceptor

**Source:** `web-ng/src/app/interceptors/billing.interceptor.ts`

Functional interceptor registered after the auth interceptor. On every successful
response, reads the `X-Usage-Remaining` header and writes it to the `usageRemaining`
global signal (zero extra requests). On 429, reads plan state from `SubscriptionService`
and navigates to `/upgrade` with `reason=limit_reached` (free) or `reason=payment_lapsed`
(lapsed). Pro users getting a 429 log a warning but do not navigate.

---

#### SA-09 — Usage remaining shared state

**Source:** `web-ng/src/app/state/usage.state.ts`

Module-level `signal<UsageRemaining | null>` holding `{ remaining, limit }`. Written by
the billing interceptor on every API response that carries `X-Usage-Remaining`. Read
by the usage meter component. No DI or class — plain signal exported from the module.

---

#### SA-10 — Usage meter component

**Source:** `web-ng/src/app/components/usage-meter/usage-meter.component.ts`,
`web-ng/src/app/components/usage-meter/usage-meter.component.html`

Standalone pill component in the masthead. Renders "N/M remaining" when `usageRemaining`
signal is non-null and user is not Pro. Hidden for Pro users. Shows warning red styling
when remaining count is 1 or 0. Zero additional network requests — entirely header-driven.

---

#### SA-11 — Upgrade button in masthead

**Source:** `web-ng/src/app/app.component.html` (`.upgrade-btn`),
`web-ng/src/app/app.component.ts` (`navigateToUpgrade()`)

A button in the masthead actions area, visible only for non-Pro users. Navigates to
`/upgrade` via Angular Router.

---

#### SA-12 — Upgrade page

**Source:** `web-ng/src/app/components/upgrade/upgrade.component.ts`,
`web-ng/src/app/components/upgrade/upgrade.component.html`

Standalone component at `/upgrade` route, rendered outside the app shell via
`isFullPageRoute` signal. Three conditional states based on plan:
- **free**: pricing comparison table, "Upgrade to Pro — $29/mo" primary CTA calling `startCheckout()`
- **lapsed**: "Update Your Payment Method to Restore Pro Access" with Customer Portal CTA
- **pro**: "You are on Pro" with manage subscription button

Post-checkout: reads `session_id` query param, calls `verifySession()` followed by
`refresh()`, then shows "Welcome to Pro" confirmation or an error. The route renders
via `<router-outlet />` for both authenticated (via `isFullPageRoute`) and
unauthenticated states.

---

#### SA-13 — Full-page route routing bypass

**Source:** `web-ng/src/app/app.component.ts` (`isFullPageRoute` signal,
`FULL_PAGE_ROUTES` static field),
`web-ng/src/app/app.component.html` (lines 1–4)

A signal that listens to `NavigationEnd` events. When the current path is in
`FULL_PAGE_ROUTES` (`['/upgrade']`), the component renders `<router-outlet />` instead
of the app shell, allowing full-page components to function while the user is logged in.

---

#### SA-14 — IP-based registration rate limiting

**Source:** `api/modules/auth/rate_limit.py`

Backend-only: an in-process dict tracking request timestamps per IP, enforcing 5
requests per hour via a sliding window. Applied to `POST /api/auth/register`.

**No phantom / no Angular source for this feature — backend only, no frontend component.**

---

#### SA-15 — Security headers

**Source:** `api/create_app.py` (after_request handler)

Backend-only: sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Strict-Transport-Security`, and `X-Request-ID` on every response.

**No phantom / no Angular source — backend only.**

---

#### SA-16 — Security canary endpoint

**Source:** `api/create_app.py` (`GET /api/health/security`)

Backend-only: returns 503 if `SKIP_AUTH` is active in a non-development environment,
200 otherwise. Used in deploy pipeline validation.

**No phantom / no Angular source — backend only.**

---

#### SA-17 — SKIP_AUTH environment gating

**Source:** `api/modules/auth/decorators.py`

Backend-only: the `@require_auth` SKIP_AUTH bypass is only honoured when
`FLASK_ENV=development`. In production the flag is ignored regardless of its value.

**No phantom / no Angular source — backend only.**

---

#### SA-18 — Project isolation and ownership enforcement

**Source:** `api/modules/data/projects/ownership.py`

Backend-only: `@require_project_ownership` decorator loads the project by slug, checks
`project.user_id == g.current_user.id`, returns 403 on mismatch. Applied to all
slug-accepting project routes. The frontend side of this is covered by SA-06.

---

#### SA-19 — Billing 429 usage header emission

**Source:** `api/modules/usage/decorators.py` (`@check_usage_limit`)

Backend-only: emits `X-Usage-Remaining` and `X-Usage-Limit` headers on every
successful response from a usage-limited endpoint. The billing interceptor (SA-08)
consumes these headers passively.

---

#### SA-20 — Lapsed plan state

**Source:** `api/modules/billing/service.py` (webhook handler),
`web-ng/src/app/services/subscription.service.ts`

The `invoice.payment_failed` Stripe webhook writes `plan='lapsed'` to the User record
(distinct from `'free'` for "never subscribed"). Frontend `SubscriptionService` carries
the tri-state `free | pro | lapsed`. The upgrade page renders distinct copy for each
state.

---

#### SA-21 — Stripe checkout and session verification

**Source:** `api/modules/billing/routes.py` (`POST /api/billing/create-checkout-session`,
`GET /api/billing/verify-session`),
`web-ng/src/app/services/subscription.service.ts` (`startCheckout()`, `verifySession()`)

Full Stripe checkout flow: frontend calls `startCheckout()` which redirects to Stripe
Checkout; after payment Stripe redirects to `/upgrade?session_id=...`; `verifySession()`
calls the backend endpoint which validates the Stripe session ownership and writes
`plan='pro'` to the DB as a fallback in case the webhook fires after the browser
returns.

---

## Section 2 — Cross-reference: Phantom and Undocumented Features

### Phantom features (in implementation guides, not found in code)

None detected. All features described in the nine executed guide summaries have
corresponding source files under `web-ng/src/app/` or `api/modules/`.

### Undocumented features (in code, not covered by any impl guide)

**OV-27 (Generate Specs from brainstorm result)** — The method
`generateFromBrainstormResult()` and the `.brainstorm-generate-btn` element exist in
the codebase. The `ux-reader-textops` guide describes brainstorm as a feature but does
not explicitly call out this "generate from result" path. It is treated as in-scope for
OV because it uses the same spec-gen pipeline.

**OV-31 (Panel slide animation)** — The `@panelEnter` Angular animation was shipped as
part of `ux-reader-textops` Task 5 but the exec-guide summary only notes "Panel
Animation" without detailing which signals it uses. The implementation is confirmed in
`app.component.ts`.

All other features in the code map cleanly to at least one guide.

---

## Section 3 — Spot-check: Three implementation guides verified

### Spot-check 1 — `saas-phase2b-billing-ui-1778665933`

Guide ships: SubscriptionService, billing interceptor, upgrade page, usage meter,
`X-Usage-Remaining` header, lapsed plan, verify-session endpoint.

Code confirms:
- `subscription.service.ts` — plan signal, isPro, refresh, startCheckout, verifySession. Present.
- `billing.interceptor.ts` — 429 handling, header extraction, router navigation. Present.
- `upgrade.component.ts` — three plan states, session verification, headingText computed. Present.
- `usage-meter.component.ts` — isWarning computed, isVisible computed. Present.
- `usage.state.ts` — usageRemaining signal. Present.

No missing shipped features found.

### Spot-check 2 — `saas-phase1-security-auth-1778590275`

Guide ships: /register endpoint + SignupComponent, token lifecycle service, auth
interceptor refactor, CORS lockdown, security headers, /api/health/security.

Code confirms:
- `pages/signup/signup.component.ts` — form, validation, 409/429 error handling. Present.
- `token-lifecycle.service.ts` — mutex refresh, isLoggedIn signal, handleAuthFailure. Present.
- `auth.interceptor.ts` — PUBLIC_PATHS includes /register and /refresh. Present.
- `auth.service.ts` — register() delegates to lifecycle.storeToken(). Present.

Backend (SA-14 through SA-17) not re-scanned here but confirmed by exec-guide summary
(4 critical issues fixed, all tasks green).

### Spot-check 3 — `ux-reader-textops-1778237000`

Guide ships: section taxonomy service, project teaser service, sidebar command centre,
status bar, panel animation, AI text ops via generated client.

Code confirms:
- `section-taxonomy.service.ts` — sectionFor() pure function, SECTION_ORDER. Present.
- `project-teaser.ts` — projectTeaser(), firstNonHeadingSentence(), countTasks(). Present.
- `ai.service.ts` — delegates to brainstormText, expandText, etc. from generated client. Present.
- `app.component.ts` — NAV_SECTIONS, sidebar ops, toggleOp(), runOp(). Present.
- `statusMode` signal four-state machine. Present.

No missing shipped features found.

---

## Section 4 — Numbering summary

### OV- prefix (Overview page)

| ID | Feature |
|---|---|
| OV-01 | Auth gate |
| OV-02 | Masthead nameplate |
| OV-03 | Section navigation bar |
| OV-04 | Section count pulse animation |
| OV-05 | Generation status bar |
| OV-06 | Update banner |
| OV-07 | Search / filter bar |
| OV-08 | Project grid with taxonomy grouping |
| OV-09 | Project cards with teasers |
| OV-10 | Polling / background refresh |
| OV-11 | Dark mode toggle |
| OV-12 | Context viewer |
| OV-13 | Create project modal |
| OV-14 | Spec-gen pipeline with incremental file save |
| OV-15 | Expanded project reader panel |
| OV-16 | Expanded reader sidebar |
| OV-17 | Sidebar status row |
| OV-18 | Per-file dot tracking |
| OV-19 | Generate Specs button |
| OV-20 | Generate Guide button (epic guide) |
| OV-21 | AI text ops chips |
| OV-22 | Style preset chips |
| OV-23 | AI result panel with diff view |
| OV-24 | Result toolbar |
| OV-25 | Undo / redo stack |
| OV-26 | Brainstorm follow-up input |
| OV-27 | Generate Specs from brainstorm result |
| OV-28 | Section taxonomy service |
| OV-29 | Project teaser service |
| OV-30 | Word count pipe |
| OV-31 | Panel slide animation |
| OV-32 | Spec file canonical ordering |
| OV-33 | Markdown rendering with XSS sanitization |

### SA- prefix (SaaS / auth / billing)

| ID | Feature |
|---|---|
| SA-01 | Login page |
| SA-02 | Signup / registration page |
| SA-03 | Auth service |
| SA-04 | Token lifecycle service |
| SA-05 | Auth HTTP interceptor |
| SA-06 | Project ownership 403 handling |
| SA-07 | Subscription service |
| SA-08 | Billing HTTP interceptor |
| SA-09 | Usage remaining shared state |
| SA-10 | Usage meter component |
| SA-11 | Upgrade button in masthead |
| SA-12 | Upgrade page |
| SA-13 | Full-page route routing bypass |
| SA-14 | IP-based registration rate limiting (backend only) |
| SA-15 | Security headers (backend only) |
| SA-16 | Security canary endpoint (backend only) |
| SA-17 | SKIP_AUTH environment gating (backend only) |
| SA-18 | Project isolation and ownership enforcement (backend only) |
| SA-19 | Billing 429 usage header emission (backend only) |
| SA-20 | Lapsed plan state |
| SA-21 | Stripe checkout and session verification |

**Total: 33 OV features + 21 SA features = 54 catalogued features.**

No gaps or duplicates in either sequence.

---

## Section 5 — Overview Page Feature Specs (OV-01 through OV-33)

Each spec below follows the five-section format: Summary, Inputs, Expected Outputs,
State Matrix, Edge Cases. A "Mock boundary" annotation is added where the feature
requires `ProjectsService` HTTP calls or the mock chain provider.

---

### OV-01 — Auth gate

**Summary:** The app shell conditionally renders either a `<router-outlet />` (for
unauthenticated or full-page-route states) or the full `.page` shell (for authenticated
non-full-page states).

**Inputs:**
- `auth.isLoggedIn()` — signal from `TokenLifecycleService` via `AuthService`
- `isFullPageRoute()` — signal updated on `NavigationEnd` events

**Expected Outputs (DOM-observable):**
- When `isLoggedIn() === false`: `<router-outlet />` rendered; `.page` element absent
- When `isLoggedIn() === true` and `isFullPageRoute() === false`: `.page` element present; `<router-outlet />` absent
- When `isLoggedIn() === true` and `isFullPageRoute() === true`: `<router-outlet />` rendered; `.page` absent

**State Matrix:**

| isLoggedIn | isFullPageRoute | Rendered output |
|---|---|---|
| false | any | `<router-outlet />` |
| true | false | `.page` shell |
| true | true | `<router-outlet />` |

**Edge Cases:**
- Direct navigation to `/upgrade` while logged in: `isFullPageRoute` is set synchronously in the constructor from `this.router.url`, so the correct branch renders before any `NavigationEnd` fires.
- Token expiry during session: `handleAuthFailure()` sets `isLoggedIn` to false; the gate immediately collapses the shell.

**Mock boundary:** No HTTP call. `isLoggedIn` is seeded from `localStorage` at service construction. Tests must set `localStorage.setItem('specview_jwt', <token>)` before constructing `TokenLifecycleService` to control initial state.

---

### OV-02 — Masthead nameplate

**Summary:** A full-width newspaper-style masthead renders "Spec Doc", the current date,
the title "Specview", and a tagline on every authenticated page.

**Inputs:**
- `today` — string computed once at component construction from `new Date()` with `en-US` locale and `{ weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }` options
- `auth.isLoggedIn()` — gate (masthead is inside `.page` block)

**Expected Outputs (DOM-observable):**
- `.masthead` element present
- `.edition` text content: `"Spec Doc"`
- `.masthead-date` text content: formatted date string matching `en-US` long format
- `.masthead-title` text content: `"Specview"`
- `.masthead-tagline` contains italic text `"All the Specs Fit to Read"`

**State Matrix:**

| Condition | Masthead visible |
|---|---|
| `isLoggedIn() === false` | No (inside `.page` block) |
| `isLoggedIn() === true`, `isFullPageRoute() === false` | Yes |
| `isLoggedIn() === true`, `isFullPageRoute() === true` | No (router-outlet branch) |

**Edge Cases:**
- `today` is computed at construction time, not reactively — if the component stays mounted past midnight the date does not update. This is expected and not a defect.

---

### OV-03 — Section navigation bar

**Summary:** A horizontal button row with seven sections filters the project grid and
updates a count badge on each button.

**Inputs:**
- `sections` — static `NAV_SECTIONS` array (7 entries: context, all, Active, Ready to build, Specced, Braindumps, Archive)
- `activeSection()` — signal, initial value `'all'`
- `sectionCounts()` — computed signal derived from `projects()` + `sectionFor()`
- `pulsingSections()` — signal `Set<string>`, set transiently on count change
- `selectSection(id)` — method called on button click

**Expected Outputs (DOM-observable):**
- Seven `.section-link` buttons rendered
- Button whose `id` matches `activeSection()` has class `active`
- Context button shows badge with value `contextFiles.length` (6)
- Non-context section buttons show badge when `sectionCounts()[s.id] !== undefined`
- Badge element carries class `pulsing` when the section id is in `pulsingSections()`
- Clicking a section button: `activeSection` updates, search query clears, expanded panel closes

**State Matrix:**

| activeSection | Active button | Other buttons |
|---|---|---|
| `'all'` | "All" has `.active` class | Others do not |
| `'Active'` | "Active" has `.active` class | Others do not |
| `'context'` | "Context" has `.active` class | Search bar hidden (OV-07 hides it) |

**Edge Cases:**
- Clicking the currently active section re-runs `selectSection()` — this closes any open expanded panel and clears search, which is idempotent but observable in tests.

---

### OV-04 — Section count pulse animation

**Summary:** When a project's section changes (count badge value changes), the badge
pulses via `.pulsing` CSS class for 250 ms.

**Inputs:**
- `sectionCounts()` — computed signal, changes when project list updates or an active job starts/stops
- `_prevSectionCounts` — module-level cache of previous counts; compared in `effect()`

**Expected Outputs (DOM-observable):**
- `.section-count-pulse` element gains `.pulsing` class when its section count changes
- `.pulsing` class is removed after 250 ms (`setTimeout(() => pulsingSections.set(new Set()), 250)`)

**State Matrix:**

| sectionCounts change | pulsingSections | Badge class |
|---|---|---|
| No change from previous | `Set` is empty | No `.pulsing` |
| One section count changed | `Set` contains that section | `.pulsing` present on that badge |
| Multiple sections changed simultaneously | `Set` contains all changed sections | `.pulsing` on each changed badge |

**Edge Cases:**
- The initial load sets counts from `{}` to the loaded values; all changed sections pulse on first load — this is expected behavior.
- The 250 ms timeout uses `setTimeout`, not `fakeAsync`-compatible zone timers. Tests must use `fakeAsync` + `tick(250)` to verify removal.

---

### OV-05 — Generation status bar

**Summary:** A globally visible four-state bar between the section nav and search box
reflects the current spec-gen or AI-op status.

**Inputs:**
- `statusMode()` — signal, values: `'idle' | 'active' | 'success-flash' | 'failure'`
- `specGenProjectName()` — signal, project name shown in active state
- `specGenStep()` — signal, current AI step label
- `specGenJobId()` — signal, used to show/hide Cancel button
- `cancelling()` — signal, disables Cancel button and changes label
- `statusFailureMsg()` — signal, error text in failure state
- `retryLastOp()` — resets mode to idle on retry button click
- `onCancel()` — calls `cancelBootstrap` service method

**Expected Outputs (DOM-observable):**
- `.gen-status-bar` present at all times (always rendered)
- In `idle` state: class `gen-status-bar--idle`; text "specview · idle — ready"
- In `active` state: class `gen-status-bar--active`; three animated dots; project name; optional step label; Cancel button if `specGenJobId()` truthy
- In `success-flash` state: class `gen-status-bar--success`; project name + "done"
- In `failure` state: class `gen-status-bar--failure`; "error" label; `statusFailureMsg()`; retry button
- Cancel button: `[disabled]` when `cancelling()` is true; text changes to "Cancelling…"

**State Matrix:**

| statusMode | CSS class | Visible elements |
|---|---|---|
| `idle` | `gen-status-bar--idle` | Dot + "specview · idle — ready" |
| `active` | `gen-status-bar--active` | 3 dots + project name + step + Cancel |
| `success-flash` | `gen-status-bar--success` | Project name + "done" |
| `failure` | `gen-status-bar--failure` | "error" + failure message + retry button |

**Edge Cases:**
- `success-flash` auto-transitions to `idle` after 2000 ms via `_setStatusSuccess()`. Tests must `tick(2000)` in `fakeAsync` to verify the idle transition.
- If `specGenJobId()` is null during an active state, no Cancel button is rendered (bootstrap not yet started).

**Mock boundary:** `cancelBootstrap()` and `retryBootstrapStep()` are `ProjectsService` calls. Tests for Cancel must mock `ProjectsService.cancelBootstrap`.

---

### OV-06 — Update banner

**Summary:** A dismissable banner appears for 5 s when the background poll detects a
net increase in project count.

**Inputs:**
- `updateBanner()` — signal, string value like `"+1 new"`, or empty string
- Background poll (`checkForUpdates()`): sets banner when `diff > 0`
- Dismiss button: calls `updateBanner.set('')`

**Expected Outputs (DOM-observable):**
- `.update-banner` element present when `updateBanner()` is truthy
- `.update-banner` absent when `updateBanner()` is empty string
- Banner text contains the diff value (e.g. `"+1 new"`)
- A "dismiss" button inside the banner; clicking it clears the signal immediately
- Banner auto-clears after 5000 ms via `setTimeout`

**State Matrix:**

| updateBanner() value | Banner visible | Auto-dismiss |
|---|---|---|
| `''` (empty) | No | N/A |
| `'+1 new'` | Yes | After 5000 ms |
| User clicks dismiss | Immediately hidden | Timer still runs (harmless) |

**Edge Cases:**
- If project count decreases (deletion), `diff` is negative; banner does not show. Test must confirm no banner for `diff <= 0`.
- If `knownCount()` is 0, the code skips the diff check entirely (`if (diff > 0 && this.knownCount() > 0)`).

**Mock boundary:** Requires mocking `ProjectsService.listProjects` to return a list longer than the current `knownCount`.

---

### OV-07 — Search / filter bar

**Summary:** A text input filters the project grid by name or ID substring and shows a
live match count or total project count.

**Inputs:**
- `searchQuery()` — signal, updated by `onSearch(value)`
- `filteredProjects()` — computed: applies section filter then search substring filter
- `activeSection()` — search bar hidden when `context` section or expanded panel open
- `showGrid()` — computed: false when expanded panel is open

**Expected Outputs (DOM-observable):**
- `.search-bar` element present when `activeSection() !== 'context'` AND `showGrid() === true`
- `<input>` value reflects `searchQuery()` (bound via `[value]`)
- When `searchQuery()` is truthy: count text shows `"N match"` or `"N matches"`
- When `searchQuery()` is empty: count text shows `"N projects"` (total)
- Typing updates `searchQuery` signal via `(input)` event → `onSearch()`

**State Matrix:**

| activeSection | showGrid | searchQuery | Search bar visible | Count text |
|---|---|---|---|---|
| `'context'` | true | any | No | N/A |
| `'all'` | false | any | No | N/A |
| `'all'` | true | `''` | Yes | `"N projects"` |
| `'all'` | true | `'foo'` | Yes | `"N matches"` |

**Edge Cases:**
- Search is case-insensitive (`.toLowerCase()` on both query and project name/id).
- `filteredProjects()` applies section filter before search, so searching in a named section only shows results within that section.

**Mock boundary:** `filteredProjects()` depends on `ProjectsService.listProjects` output held in `projects()` signal. Tests must seed `projects` signal with test data.

---

### OV-08 — Project grid with taxonomy grouping

**Summary:** In "All" section the grid shows taxonomy-grouped project cards in canonical
section order; in named sections a 3-column masonry layout is used instead.

**Inputs:**
- `activeSection()` — determines which grid variant renders
- `projectsBySection()` — computed: groups all projects by `sectionFor()` in `SECTION_ORDER`
- `columns()` — computed: distributes `filteredProjects()` into up to 3 columns
- `filteredProjects()` — computed from `projects()` + section filter + search query
- `searchQuery()` — filters projects in both grid variants

**Expected Outputs (DOM-observable):**
- When `activeSection() === 'all'`: `.section-group` elements, one per non-empty section, in canonical order (Active → Ready to build → Specced → Braindumps → Archive)
- Each `.section-group` has `.section-group-header` with overline label and count badge
- Active section group uses `.hero-grid` class; single Active project uses `.hero-grid--single`
- When `activeSection()` is a named section: `.file-column` elements, column count up to 3
- When `filteredProjects().length === 0`: `.empty-state` element rendered

**State Matrix:**

| activeSection | projects.length | Grid rendered |
|---|---|---|
| `'all'` | > 0 | Section groups, collapsed empty sections |
| `'all'` | 0 | `.empty-state` |
| `'Active'` | > 0 | Column layout, up to 3 columns |
| `'Active'` | 0 | `.empty-state` |
| `'context'` | any | Context card grid (separate branch) |

**Edge Cases:**
- `projectsBySection()` only emits groups with `.length > 0` — empty sections are hidden in "All" view.
- `columns()` computes `numCols = Math.min(3, Math.ceil(n/2)) || 1`, so 1 project = 1 column, 2-4 projects = up to 2 columns, 5+ = 3 columns.

**Mock boundary:** Requires seeding `projects` signal. `sectionFor()` is a pure function — no mock needed.

---

### OV-09 — Project cards with teasers

**Summary:** Each project card renders a project name, section-aware teaser string,
spec count badge, and section label; the first card in a group gets `.featured` class.

**Inputs:**
- `p: Project` — project data object
- `teaserFor(p)` — method calling `projectTeaser()` from `project-teaser.ts`
- `sectionForProject(p)` — delegates to `sectionFor()` from `section-taxonomy.service.ts`
- `p.specs.length` — spec count for badge
- `$index` — first card (`pi === 0`) gets `.featured` class

**Expected Outputs (DOM-observable):**
- `.file-item` element per project
- `.file-item-title` contains `p.name`
- `.file-item-teaser` contains result of `teaserFor(p)`
- `.file-item-meta` contains: `.badge` with spec count, section label text
- First card in each group/column has class `.featured`
- Clicking a card calls `selectProject(p.id)`

**State Matrix:**

| Section | Active step known | Teaser content |
|---|---|---|
| `Active` | Yes | `"generating <step>…"` |
| `Active` | No | First non-heading sentence from braindump or epic |
| `Specced` | N/A | `"Implementation guide ready · N tasks"` or guide extract |
| `Ready to build` | N/A | First sentence from architecture or epic |
| `Braindumps` | N/A | First sentence from braindump or `"Braindump — ready to generate"` |

**Edge Cases:**
- `teaserFor()` falls back through several spec files; if none have content, returns empty string — blank teaser is valid and renders without error.

**Mock boundary:** `teaserFor()` reads from `p.specs` content/teaser fields already in the `Project` object. `ProjectsService` mock must return `Project` with populated `specs[].teaser`.

---

### OV-10 — Polling / background refresh

**Summary:** A `setInterval` fires every 30 s to refresh the project list; a second
fires every 10 s during active spec-gen. Both are cleared on destroy or logout. After
30 consecutive failures, polling stops.

**Inputs:**
- `auth.isLoggedIn()` — effect starts/stops polling
- `REFRESH_INTERVAL` (30 000 ms), `GEN_POLL_INTERVAL` (10 000 ms)
- `POLL_MAX_RETRIES` (30) — failure threshold
- `pollRetries` — counter incremented on each `checkForUpdates()` call
- `ProjectsService.listProjects()` — HTTP call inside poll

**Expected Outputs (DOM-observable):**
- `polling()` signal briefly true during each poll cycle (cleared after 700 ms)
- `pollOk()` — false after a failed request, true on success
- `pollingError()` — set to an error string after 30 failures; `data-test="polling-error"` element appears
- `updateBanner()` — set when project count increases
- `lastSyncAt()` / `lastSyncElapsed()` — updated on successful poll

**State Matrix:**

| pollRetries | List fetch result | Observable outcome |
|---|---|---|
| 1–29 | Success | `pollOk` = true, projects updated if count changed |
| 1–29 | Failure | `pollOk` = false |
| 30 | Any | Polling stops, `pollingError` set, error banner visible |
| After logout | N/A | `stopPolling()` clears interval, no further calls |

**Edge Cases:**
- `pollRetries` is NOT reset on success (only reset when polling starts fresh after login). A test verifying stop-after-30 must simulate 30 consecutive calls.
- `_startGenPoll()` is idempotent (guards `if (this.genPollTimer) return`). Starting spec-gen while one poll is already running does not double the interval.

**Mock boundary:** `ProjectsService.listProjects` must be mocked. Use `fakeAsync` + `tick(30000)` to advance poll intervals without real timers.

---

### OV-11 — Dark mode toggle

**Summary:** A masthead button toggles `[data-theme="dark"]` on `<html>` and persists
the preference to `localStorage`; the preference is read on `ngOnInit`.

**Inputs:**
- `isDark()` — signal, initial value false
- `toggleTheme()` — method called on button click
- `localStorage.getItem('theme')` — read in `ngOnInit`
- `document.documentElement.setAttribute('data-theme', ...)` — DOM side effect

**Expected Outputs (DOM-observable):**
- Theme toggle button present in masthead actions
- When `isDark() === false`: button shows "☾" icon
- When `isDark() === true`: button shows "☀" icon
- After toggle: `document.documentElement` has `data-theme="dark"` (or `"light"`)
- `localStorage.getItem('theme')` equals `'dark'` or `'light'` after toggle

**State Matrix:**

| localStorage 'theme' on init | isDark initial | `data-theme` on `<html>` |
|---|---|---|
| `null` / `'light'` | false | `'light'` (not set by ngOnInit, default) |
| `'dark'` | true | `'dark'` (set in ngOnInit) |

**Edge Cases:**
- `ngOnInit` calls `document.documentElement.setAttribute` when saved theme is `'dark'`. Toggling to light calls `setAttribute('data-theme', 'light')` — it does not remove the attribute.

---

### OV-12 — Context viewer

**Summary:** Clicking a context card loads its content via `GET /api/context/:key`,
sets `contextContent` and `contextTitle` signals, and opens the expanded panel.

**Inputs:**
- `contextFiles` — static array of 6 `{ key, label, desc }` entries
- `openContext(key)` — async method; calls `ProjectsService.getContext(key)`
- `contextContent()` — signal, set to API response `content` or `text` field
- `contextTitle()` — signal, set to the file label

**Expected Outputs (DOM-observable):**
- Six `.context-card` elements rendered in context section
- Each card shows `.context-card__label` and `.context-card__desc`
- After clicking: `.expanded-panel` visible; `expandedTitle()` shows context label; main area renders markdown HTML from `contextContent`
- `activeProject()` is set to null when context is open (context and project viewer are mutually exclusive)

**State Matrix:**

| activeSection | User action | State after |
|---|---|---|
| `'context'` | Click "Builder" card | `contextContent` set, expanded panel open, `activeProject` null |
| `'context'` | Click another card while panel open | `contextContent` replaced, title updated |
| any | Click back button | `closeExpanded()` resets both signals to null |

**Edge Cases:**
- API response may have `content` or `text` field; `openContext` reads `data.content || data.text || ''`.

**Mock boundary:** `ProjectsService.getContext` must be mocked to return `{ content: '...' }`.

---

### OV-13 — Create project modal

**Summary:** A modal dialog collects project name and braindump; on submit it closes
immediately and starts async spec-gen via `createProject()`.

**Inputs:**
- `showCreateModal()` — signal, toggled by `openCreateModal()` / `closeCreateModal()`
- `openCreateModal()` — called by "+ New" button
- `closeCreateModal()` — backdrop click or Cancel button
- `createProject(nameEl, braindumpEl)` — validates non-empty inputs, starts spec-gen
- `specGenLoading()` — disables Generate button

**Expected Outputs (DOM-observable):**
- `.modal-backdrop` present when `showCreateModal() === true`, absent otherwise
- `.modal` inside backdrop; clicking backdrop calls `closeCreateModal()`; clicking inside modal stops propagation
- `.modal-input` for project name; `.modal-textarea` (`data-test="braindump-input"`) for braindump
- Generate button `[disabled]` when `specGenLoading()` is true; shows animated dots + "Generating…" text
- On submit: modal closes immediately (`showCreateModal.set(false)`); status bar transitions to active

**State Matrix:**

| specGenLoading | Generate button | Modal visible on submit |
|---|---|---|
| false | Enabled | Closes immediately on valid input |
| true | Disabled | Already closed (modal never re-opens during gen) |

**Edge Cases:**
- Pressing Enter in the name input calls `createProject` only when both fields are non-empty (template `(keydown.enter)` guard).
- `specGenError` is cleared when modal opens (`openCreateModal` calls `specGenError.set(null)`).

**Mock boundary:** `createProject()` calls `ProjectsService.createProject` then `startBootstrap`. Both must be mocked. `startBootstrap` response requires `{ job_id }` shape.

---

### OV-14 — Spec-gen pipeline with incremental file save

**Summary:** Full braindump-to-specs pipeline: calls `startBootstrap`, polls every
2.5 s, saves each file as it arrives, and navigates to `analysis.md` on completion.

**Inputs:**
- `ProjectsService.startBootstrap(name, braindump)` → `{ job_id }`
- `ProjectsService.pollBootstrap(jobId)` → `PollStatusResponse`
- `ProjectsService.saveFile(projectId, filename, content)` — called per partial file
- `specGenStep()` — updated from `status.current_step`
- `specGenFailedStep()` — set from `status.failed_step`
- `cancelling()` — set by `onCancel()`; causes `cancelBootstrap` call

**Expected Outputs (DOM-observable):**
- `specGenLoading()` true during pipeline; false on completion or error
- `specGenStep()` updates display in status bar and sidebar status row
- Sidebar file nav grows as `partial_files` arrive and `activeProject` refreshes
- On success: `activeFile` set to `analysis.md` (or first available spec)
- On failure: `specGenError()` set; error block visible; Retry button shown if `specGenFailedStep` set
- On cancel: error thrown `'Generation cancelled'`; error state shown

**State Matrix:**

| Poll response | specGenLoading | Resulting action |
|---|---|---|
| `running: true, done: false` | true | Update step label; save partial files |
| `done: true, status: 'CANCELLED'` | → false | Throw "Generation cancelled"; show error |
| `done: true, error: <msg>` | → false | Throw error message; show error |
| `done: true, files: [...]` | → false | Save remaining files; navigate to analysis |
| Network failure (≥5 consecutive) | → false | Throw "Lost connection…"; show error |

**Edge Cases:**
- Files already in `saved` set are skipped on final file list (deduplication via `Set<string>`).
- Retry step (`onRetry()`) calls `retryBootstrapStep(jobId, step)`, updates `specGenJobId`, and transitions to active state.

**Mock boundary:** `ProjectsService.startBootstrap`, `pollBootstrap`, `saveFile`, `getProject`, and `retryBootstrapStep` all require mocking. Use a mock that resolves the poll loop promptly (return `done: true` on first call to avoid real timeouts).

---

### OV-15 — Expanded project reader panel

**Summary:** An animated slide-in panel replaces the grid when a project is selected,
showing a sticky sidebar and a main content area with the active spec rendered as
sanitized markdown.

**Inputs:**
- `showExpanded()` — computed: true when `activeProject()` or `contextContent()` or `accessDenied()` is set
- `activeProject()` — signal, set by `selectProject()`
- `currentSpec()` — computed from `activeProject()` + `activeFile()`
- `parsedContent()` — computed: `marked.parse()` + `DOMPurify.sanitize()`
- `expandedTitle()` — computed: context title or spec label
- `expandedProject()` — computed: "Context" or project name
- `activeFileType()` — computed: uppercased file type label (e.g. "ARCHITECTURE")

**Expected Outputs (DOM-observable):**
- `.expanded-panel` present when `showExpanded() === true`; absent otherwise
- `@panelEnter` animation applied on enter/leave
- `.overline` showing `activeFileType()` (e.g. "ARCHITECTURE") when a project file is open
- `.expanded-meta` showing project name + word count when `activeProject()` and `currentSpec()` are set
- `.expanded-title` showing `expandedTitle()`
- `.expanded-body` with sanitized HTML from `parsedContent()`

**State Matrix:**

| activeProject | contextContent | accessDenied | Panel visible | Main content |
|---|---|---|---|---|
| null | null | false | No | N/A |
| Project object | null | false | Yes | Spec markdown |
| null | string | false | Yes | Context markdown |
| null | null | true | Yes | Access denied block |

**Edge Cases:**
- `parsedContent()` returns empty SafeHtml `''` when both `currentSpec` and `contextContent` are null — no rendering error.
- XSS: all content passes through `DOMPurify.sanitize()` before `bypassSecurityTrustHtml`.

---

### OV-16 — Expanded reader sidebar

**Summary:** Sticky sidebar inside the expanded panel containing back button, project
name, spec file nav in canonical order, per-file status dots, status row, and generate/op sections.

**Inputs:**
- `activeProject()` — conditionally renders file nav, generate buttons, op chips
- `activeFile()` — highlights active file button
- `fileOpState()` — signal `Record<string, 'running' | 'success' | 'failure'>` — drives dot visibility
- `selectFile(filename)` — method called on file nav button click
- `closeExpanded()` — called by back button

**Expected Outputs (DOM-observable):**
- `.expanded-sidebar` element present inside `.expanded-panel`
- `.sidebar-back` button navigates back (calls `closeExpanded()`)
- `.sidebar-project` shows `expandedProject()` text
- `.sidebar-nav` with one `.sidebar-file` button per spec (in canonical order from `sortSpecs`)
- Active file button has `.active` class
- Each file button may contain `.file-dot` span when `fileOpState()[filename]` is set
- `.file-dot--running`, `.file-dot--success`, `.file-dot--failure` classes applied per state

**State Matrix:**

| fileOpState[filename] | Dot present | Dot class |
|---|---|---|
| undefined | No | N/A |
| `'running'` | Yes | `.file-dot--running` |
| `'success'` | Yes | `.file-dot--success` |
| `'failure'` | Yes | `.file-dot--failure` |

**Edge Cases:**
- Context viewer mode: `activeProject()` is null, so file nav and op chips are hidden; only back button and project name ("Context") are visible.

---

### OV-17 — Sidebar status row

**Summary:** A compact four-state indicator row in the sidebar mirrors the global status
bar, positioned below the file nav.

**Inputs:**
- `mode()` — computed from `statusMode()` signal
- `specGenLoading()` — distinguishes spec-gen step from AI op step in active state
- `specGenStep()`, `activeStepLabel()` — text for active state
- `statusFailureMsg()` — text for failure state
- `retryLastOp()` — resets to idle on retry click

**Expected Outputs (DOM-observable):**
- `.sidebar-status` element present when `activeProject()` is truthy
- Class `sidebar-status--active` / `sidebar-status--success` / `sidebar-status--failure` applied per mode
- In `idle`/default: dot with no class modifier; text "connected"
- In `active`: animated dot with `--active` class; text shows step or AI op label
- In `success-flash`: dot with `--success` class; text "done"
- In `failure`: dot with `--failure` class; failure message; retry button

**State Matrix:**

| statusMode | specGenLoading | Sidebar text |
|---|---|---|
| `active` | true | `specGenStep() ?? 'starting…'` |
| `active` | false | `activeStepLabel()` (AI op label) |
| `success-flash` | any | "done" |
| `failure` | any | `statusFailureMsg()` |
| `idle` | any | "connected" |

**Edge Cases:**
- Sidebar status row only renders when `activeProject()` is truthy — it does not appear in context viewer mode.

---

### OV-18 — Per-file dot tracking

**Summary:** A colored dot on each sidebar file button reflects whether an AI op is
running, succeeded, or failed for that file; success dots auto-clear after 1.5 s.

**Inputs:**
- `_setFileRunning(filename)` — sets `fileOpState[filename] = 'running'`
- `_setFileSuccess(filename)` — sets to `'success'`; schedules removal after 1500 ms
- `_setFileFailure(filename)` — sets to `'failure'`; persists until next op
- `activeOpFile()` — signal tracking the current target filename

**Expected Outputs (DOM-observable):**
- `.file-dot` element added to the matching `.sidebar-file` button
- `.file-dot--running` class while op is in-flight
- `.file-dot--success` class immediately after success; removed after 1500 ms
- `.file-dot--failure` class on failure; persists

**State Matrix:**

| Event | fileOpState[file] | Auto-clear |
|---|---|---|
| `_setFileRunning` | `'running'` | No |
| `_setFileSuccess` | `'success'` | After 1500 ms |
| `_setFileFailure` | `'failure'` | No (persists) |
| New op starts on same file | Overwritten to `'running'` | N/A |

**Edge Cases:**
- If `filename` is null (no file selected), `_setFileRunning(null)` sets `activeOpFile` to null but does not write to `fileOpState`.
- Success clear uses a stale-check: only removes if `cur[filename] === 'success'` at clear time, so a subsequent failure dots not get cleared by the success timer.

---

### OV-19 — Generate Specs button (from braindump)

**Summary:** A button visible when the active project has no `analysis.md` triggers the
full spec-gen pipeline from `braindump.md`.

**Inputs:**
- `canGenerateSpecs()` — computed: `!proj.specs.some(s => s.filename === 'analysis.md')`
- `specGenLoading()` — disables button and shows animated dots
- `generateFromBraindump()` — method called on click; uses braindump spec content

**Expected Outputs (DOM-observable):**
- `[data-test="pipeline-trigger"]` button present in sidebar when `canGenerateSpecs() === true`
- Button `[disabled]` when `specGenLoading()` is true; shows three `.thinking-dot` spans
- Button absent when `canGenerateSpecs() === false` (analysis.md exists)
- On click: spec-gen pipeline starts; button disabled for duration

**State Matrix:**

| analysis.md present | specGenLoading | Button state |
|---|---|---|
| false | false | Visible and enabled |
| false | true | Visible but disabled (animated) |
| true | any | Hidden |

**Edge Cases:**
- `generateFromBraindump()` looks for `braindump.md` first, then falls back to `currentSpec()` then `specs[0]`. A project with no specs at all would return early (`!braindumpSpec?.content`).

**Mock boundary:** `generateFromBraindump()` calls `ProjectsService.startBootstrap`, `pollBootstrap`, `saveFile`, `getProject`.

---

### OV-20 — Generate Guide button (epic guide)

**Summary:** A button visible when the active project has `epic.md` but no
`implementation-guide.md` triggers epic guide generation.

**Inputs:**
- `canGenerateEpicGuide()` — computed: `proj.specs.some(s => s.filename === 'epic.md')`
  — Note: the inventory states "no implementation-guide.md" but the computed only checks for epic.md presence; having both epic and guide would still show the button. This is a divergence to note.
- `epicGuideLoading()` — disables button
- `generateEpicGuide()` — calls `startEpicGuide`, polls every 3 s

**Expected Outputs (DOM-observable):**
- `[data-test="epic-guide-trigger"]` button visible when `canGenerateEpicGuide() === true`
- Button disabled and shows animated dots when `epicGuideLoading()` is true
- On completion: `activeFile` set to `status.filename` from poll response; project refreshed

**State Matrix:**

| epic.md present | epicGuideLoading | Button state |
|---|---|---|
| false | any | Hidden |
| true | false | Visible and enabled |
| true | true | Visible but disabled |

**Edge Cases:**
- `canGenerateEpicGuide` does not check for pre-existing `implementation-guide.md` — if both exist, the button is still visible. This allows re-generation.
- Poll uses 3000 ms interval (not 2500 ms like bootstrap). Tests must `tick(3000)`.

**Mock boundary:** `ProjectsService.startEpicGuide` and `pollEpicGuide` require mocking.

---

### OV-21 — AI text ops chips

**Summary:** Eight op chips in the sidebar send the active spec content to backend AI
endpoints; only one op can be active at a time.

**Inputs:**
- `activeOp()` — signal tracking the currently active chip key
- `currentSpec()` — required for chip visibility (rendered inside `@if (currentSpec())`)
- `isBraindump()` — Brainstorm chip only visible when braindump.md is active
- `toggleOp(op)` — toggles activeOp; for immediate ops, also calls `runOp()`
- `AiService.[op](content)` — HTTP call via ng-openapi-gen client

**Expected Outputs (DOM-observable):**
- `.sidebar-ops` container visible when `currentSpec()` is truthy
- Brainstorm chip (`data-test="brainstorm-button"`) visible only when `isBraindump() === true`
- Active chip has `.active` class
- Clicking an already-active chip: clears `activeOp`, clears `aiResult`, clears `aiError`
- Clicking a new chip: sets `activeOp`; immediate ops (expand/compress/clarify/simplify/tldr/bullets/brainstorm) trigger `runOp()` immediately
- "Style…" chip does not trigger immediate call — shows style presets instead

**State Matrix:**

| Chip clicked | Op type | Immediate AI call |
|---|---|---|
| Same chip as `activeOp` | Any | No; toggle off |
| expand / compress / clarify / simplify / tldr / bullets / brainstorm | Immediate | Yes |
| style | Preset-revealing | No |

**Edge Cases:**
- `runOp()` guards `if (!spec?.content) return` — chips are visible but do nothing if the spec has no content (e.g. empty braindump).
- Undo and Redo chips (`undoVersion()`, `redoVersion()`) appear conditionally in the same `.sidebar-ops` block when `canRevert()` or `canRedo()` are true.

**Mock boundary:** `AiService` methods are generated client calls. Tests must provide a mock `AiService` returning `{ text, latencyMs }`.

---

### OV-22 — Style preset chips

**Summary:** Five style preset buttons appear below the op chip row when "Style…" is
active; clicking one calls `AiService.styleAs()`.

**Inputs:**
- `activeOp()` — must equal `'style'` for presets to render
- `aiLoading()` — preset block hidden during a loading state (`!aiLoading()`)
- `aiResult()` — preset block hidden once a result is present (`!aiResult()`)
- `STYLE_PRESETS` — static array: `['Concise', 'Technical', 'Executive', 'Narrative', 'Punchy']`
- `runStyle(style)` — calls `AiService.styleAs(content, style)`

**Expected Outputs (DOM-observable):**
- `.style-presets.sidebar-style-presets` visible when `activeOp() === 'style'` AND `!aiLoading()` AND `!aiResult()`
- Five `.style-chip` buttons, one per preset label
- Clicking a preset: `_runAi()` invoked; `aiLoading` set to true; presets hidden during load

**State Matrix:**

| activeOp | aiLoading | aiResult | Preset block visible |
|---|---|---|---|
| `'style'` | false | null | Yes |
| `'style'` | true | null | No |
| `'style'` | false | string | No |
| any other | any | any | No |

**Edge Cases:**
- `runStyle(style)` returns early if `!spec?.content`, same guard as `runOp`.

**Mock boundary:** Same as OV-21: `AiService.styleAs` must be mocked.

---

### OV-23 — AI result panel with diff view

**Summary:** After an AI op completes, the result replaces the spec view with either a
paragraph-level unified diff (non-additive ops) or plain markdown (brainstorm/TL;DR).

**Inputs:**
- `aiResult()` — signal, set to result text on success
- `isAdditiveOp()` — computed: true for `'brainstorm'` and `'tldr'`
- `diffHtmlUnified()` — computed: `computeParagraphDiff(original, result)` rendered as SafeHtml
- `parsedAiResult()` — computed: plain `marked.parse()` + `DOMPurify.sanitize()` for additive ops

**Expected Outputs (DOM-observable):**
- When `aiResult()` is set and `isAdditiveOp() === false`: `.diff-unified.markdown-content` rendered with diff HTML
- When `aiResult()` is set and `isAdditiveOp() === true`: `.brainstorm-result.markdown-content` rendered with plain HTML (`data-test="brainstorm-result"`)
- Removed paragraphs wrapped in `.diff-block-remove`
- Added paragraphs wrapped in `.diff-block-add`
- Kept paragraphs rendered without a wrapper class

**State Matrix:**

| aiResult | activeOp | isAdditiveOp | Rendered element |
|---|---|---|---|
| null | any | any | `.expanded-body` with spec content |
| string | `'expand'` | false | `.diff-unified` |
| string | `'brainstorm'` | true | `.brainstorm-result` |
| string | `'tldr'` | true | `.brainstorm-result` |

**Edge Cases:**
- `computeParagraphDiff` splits on `\n{2,}` (double newlines). Single-newline paragraphs are treated as one block — diffs may be coarser than word-level.
- Empty result string: `isAdditiveOp()` still determines branch, but `parsedAiResult()` / `diffHtmlUnified()` return empty SafeHtml.

---

### OV-24 — Result toolbar (Apply / Copy / Dismiss / Latency)

**Summary:** A floating toolbar appears when an AI result is pending, with Apply, Copy,
Dismiss buttons and an optional latency badge.

**Inputs:**
- `aiResult()` — toolbar only renders when truthy
- `aiLatencyMs()` — signal, shown in latency badge when truthy
- `applyResult()` — writes result to spec, pushes to undo stack, saves via API
- `copyResult()` — writes result to clipboard, sets `copied()` for 2 s
- `dismissResult()` — clears result and active op

**Expected Outputs (DOM-observable):**
- `.editor-toolbar.editor-toolbar--floating` present when `aiResult()` is truthy
- `.latency-badge` present when `aiLatencyMs()` is truthy; text `"⚡ Xs"` (1 decimal)
- "Apply" button (`editor-apply-btn`); "Copy" button showing "Copied" for 2 s after click; `×` dismiss button
- After Apply: `aiResult()` and `activeOp()` cleared; spec content updated in `activeProject()` signal; `saveFile` called

**State Matrix:**

| aiResult | aiLatencyMs | Toolbar visible | Latency badge |
|---|---|---|---|
| null | any | No | N/A |
| string | null | Yes | No |
| string | 1500 | Yes | "⚡ 1.5s" |

**Edge Cases:**
- `applyResult()` clears `redoStack[key]` (applying new result kills the redo branch).
- `copyResult()` is async (clipboard API); `copied` signal is set to true for exactly 2000 ms via `setTimeout`.

**Mock boundary:** `ProjectsService.saveFile` must be mocked for Apply tests.

---

### OV-25 — Undo / redo stack

**Summary:** In-memory per-file undo/redo; Undo reverts to a previous version and saves
to API; Redo re-applies a reverted version.

**Inputs:**
- `undoStack()` — signal `Record<string, string[]>` keyed by `"projectId/filename"`
- `redoStack()` — same shape
- `canRevert()` — computed: `undoStack()[key].length > 0`
- `canRedo()` — computed: `redoStack()[key].length > 0`
- `undoVersion()` — pops from undoStack, pushes current to redoStack, saves file
- `redoVersion()` — pops from redoStack, pushes current to undoStack, saves file

**Expected Outputs (DOM-observable):**
- Undo chip `[data-test not present; class "editor-hist-btn"]` visible when `canRevert() === true`
- Redo chip visible when `canRedo() === true`
- After Undo: `parsedContent()` reflects previous version; Undo stack shortened by 1; Redo stack extended by 1
- After Redo: reverse of Undo

**State Matrix:**

| undoStack[key] | redoStack[key] | Undo visible | Redo visible |
|---|---|---|---|
| `[]` | `[]` | No | No |
| `['v1']` | `[]` | Yes | No |
| `[]` | `['v2']` | No | Yes |
| `['v1']` | `['v2']` | Yes | Yes |

**Edge Cases:**
- Applying a new AI result clears the redo stack for that key (`redoStack[key] = []`).
- Undo/Redo call `ProjectsService.saveFile().catch(() => {})` — save errors are silently swallowed.

**Mock boundary:** `ProjectsService.saveFile` must be mocked; the mock need not resolve for basic stack behavior tests but must not reject unhandled.

---

### OV-26 — Brainstorm follow-up input

**Summary:** When the Brainstorm op result is displayed, a follow-up text input allows
iterative questioning; each question sends the previous result as context.

**Inputs:**
- `activeOp()` — must be `'brainstorm'` for follow-up block to render (inside `@if (isAdditiveOp())` + `@if (activeOp() === 'brainstorm')`)
- `brainstormQuestion()` — signal, two-way bound to the input
- `followupBrainstorm(question)` — validates non-empty, composes context from current result, calls `AiService.brainstorm()`
- Enter key and button both call `followupBrainstorm(followupEl.value)`

**Expected Outputs (DOM-observable):**
- `.brainstorm-followup` block visible when `activeOp() === 'brainstorm'` and `aiResult()` is set
- Input bound to `brainstormQuestion()`; cleared to `''` at start of each followup call
- Follow-up button `↵` triggers the same path as Enter key
- Subsequent brainstorm result replaces `aiResult()` signal (new diff)

**State Matrix:**

| brainstormQuestion | User action | Expected |
|---|---|---|
| `''` (empty) | Click/Enter | `followupBrainstorm` returns early (guard `!question.trim()`) |
| `'tell me more'` | Click/Enter | AI call fires; question cleared; result updates |

**Edge Cases:**
- Context composition: `currentResult ? "...\n\n---\nPrevious brainstorm:\n..." + currentResult : undefined`. If `currentResult` is null (no prior result), context is omitted.

**Mock boundary:** `AiService.brainstorm` must be mocked to accept optional `context` parameter.

---

### OV-27 — Generate Specs from brainstorm result

**Summary:** A button shown below the brainstorm result (when no specs exist yet) feeds
the brainstorm output plus the original braindump into the spec-gen pipeline.

**Inputs:**
- `canGenerateSpecs()` — button only visible when true
- `aiResult()` — must be set (button is inside brainstorm result block)
- `specGenLoading()` — disables button
- `generateFromBrainstormResult()` — composes enriched braindump and calls `_runBootstrap`

**Expected Outputs (DOM-observable):**
- `.brainstorm-generate-btn` visible when `canGenerateSpecs() === true` (inside brainstorm result block)
- Button `[disabled]` when `specGenLoading()` is true
- On click: `aiResult` cleared; status bar goes active; spec-gen pipeline begins
- Enriched braindump format: `${spec.content}\n\n---\n## Brainstorm Output\n\n${result}`

**State Matrix:**

| canGenerateSpecs | aiResult | specGenLoading | Button state |
|---|---|---|---|
| false | any | any | Hidden |
| true | null | any | Hidden (outside brainstorm result block) |
| true | string | false | Visible and enabled |
| true | string | true | Visible but disabled |

**Edge Cases:**
- Returns early if `!proj || !result || !spec` — guards against partially-initialized state.

**Mock boundary:** Same as OV-14.

---

### OV-28 — Section taxonomy service

**Summary:** A pure-function module (no DI) that maps a project's file list and
active-job flag to one of five canonical sections.

**Inputs:**
- `project: Project` — `specs[].filename` array is the input
- `hasActiveJob: boolean` — if true, overrides all file-state logic → `'Active'`
- `(project as any).archived` — future-use guard → `'Archive'`

**Expected Outputs (DOM-observable):** The function itself is not a DOM feature; it is
verified indirectly through OV-08 (grid grouping) and OV-09 (card section label).

For unit testing `sectionFor()` directly:

**State Matrix:**

| hasActiveJob | filenames includes | Result |
|---|---|---|
| true | any | `'Active'` |
| false | `'implementation-guide.md'` | `'Specced'` |
| false | `'architecture.md'` or `'epic.md'` (no guide) | `'Ready to build'` |
| false | `'braindump.md'` only | `'Braindumps'` |
| false | `[]` (no files) | `'Braindumps'` |

**Edge Cases:**
- `implementation-guide.md` takes priority over `epic.md` — a project with both maps to `'Specced'`, not `'Ready to build'`.
- `archived` flag is not on the current API shape — test must use `(project as any).archived = true` to reach the Archive branch.

---

### OV-29 — Project teaser service

**Summary:** A pure-function module providing section-aware teaser strings, the
first-non-heading-sentence extractor, and the task counter.

**Inputs to `projectTeaser(section, activeStep, leadFileContent, taskCount, archivedAt)`:**
- All parameters may be null/undefined

**Expected Outputs:** A string teaser.

**State Matrix for `projectTeaser()`:**

| section | activeStep | taskCount | leadFileContent | Output |
|---|---|---|---|---|
| `'Active'` | `'analysis'` | any | any | `"generating analysis…"` |
| `'Active'` | null | any | `"Some content."` | `"Some content."` |
| `'Specced'` | N/A | 3 | any | `"Implementation guide ready · 3 tasks"` |
| `'Specced'` | N/A | 1 | any | `"Implementation guide ready · 1 task"` |
| `'Specced'` | N/A | 0 | `"Lead content."` | `"Lead content."` |
| `'Braindumps'` | N/A | any | null | `"Braindump — ready to generate"` |
| `'Archive'` | N/A | any | any | `"Archived <date>"` or `"Archived"` |

**State Matrix for `firstNonHeadingSentence()`:**

| Input | Output |
|---|---|
| `"# Heading\nSome sentence. More."` | `"Some sentence."` |
| `"- bullet\n- more"` | `""` (all lines skipped) |
| `"A long line (>120 chars)..."` | First 120 chars + `"…"` |

**Edge Cases:**
- `countTasks()` uses `^## Task` multiline regex — headings must be at the start of a line; `### Task` is not counted.

---

### OV-30 — Word count pipe

**Summary:** Standalone Angular pipe that returns an integer word count for any string.

**Inputs:**
- `value: string | null | undefined`

**Expected Outputs:** Integer word count.

**State Matrix:**

| Input | Output |
|---|---|
| `null` | `0` |
| `undefined` | `0` |
| `''` | `0` |
| `'hello world'` | `2` |
| `'  multiple   spaces  '` | `2` |
| `'one'` | `1` |

**Edge Cases:**
- Splitting on `/\s+/` and filtering empty tokens handles leading/trailing whitespace and multiple consecutive spaces.

---

### OV-31 — Panel slide animation

**Summary:** Enter/leave animation on `.expanded-panel` — sidebar slides in from the
left in 250 ms; main area slides up in 250 ms with 40 ms delay; both leave in 150 ms.

**Inputs:**
- `@panelEnter` trigger bound to `[@panelEnter]` on `.expanded-panel`
- `showExpanded()` — drives the `@if` block containing the animated element

**Expected Outputs (DOM-observable):**
- On `:enter`: `.expanded-sidebar` animates from `translateX(-8px) opacity:0` to `translateX(0) opacity:1` in 250 ms
- On `:enter`: `.expanded-main` animates from `translateY(8px) opacity:0` to `translateY(0) opacity:1` in 250 ms (40 ms delay)
- On `:leave`: both animate out in 150 ms

**State Matrix:**

| Transition | Target element | Duration | Delay |
|---|---|---|---|
| `:enter` | `.expanded-sidebar` | 250 ms | 0 ms |
| `:enter` | `.expanded-main` | 250 ms | 40 ms |
| `:leave` | `.expanded-sidebar` | 150 ms | 0 ms |
| `:leave` | `.expanded-main` | 150 ms | 0 ms |

**Edge Cases:**
- Queries use `{ optional: true }` — if the child element is absent (e.g. context-only view with no sidebar), the animation still triggers without error.

---

### OV-32 — Spec file canonical ordering

**Summary:** The `sortSpecs()` function sorts a project's spec files into canonical
reading order; unknown files sort alphabetically after known files.

**Inputs:**
- `specs: Spec[]` — array of spec objects with `filename` field
- `CANONICAL_ORDER` — `['braindump', 'analysis', 'epic', 'architecture', 'timeline', 'implementation-guide']`

**Expected Outputs:** Sorted `Spec[]` array.

**State Matrix:**

| Input filenames | Sorted output |
|---|---|
| `['epic.md', 'braindump.md']` | `['braindump.md', 'epic.md']` |
| `['implementation-guide.md', 'analysis.md']` | `['analysis.md', 'implementation-guide.md']` |
| `['custom.md', 'braindump.md']` | `['braindump.md', 'custom.md']` |
| `['z-extra.md', 'a-extra.md']` | `['a-extra.md', 'z-extra.md']` (alphabetical) |

**Edge Cases:**
- `.replace(/\.md$/i, '')` strips the extension before index lookup — files with non-lowercase `.MD` extensions are handled.
- `sortSpecs` is applied in `listProjects()` and `getProject()` — tests that seed `projects` signal directly bypass this sorting.

---

### OV-33 — Markdown rendering with XSS sanitization

**Summary:** All markdown rendering passes through `marked.parse()` + `DOMPurify.sanitize()`
before being set via `bypassSecurityTrustHtml`; no raw API content reaches the DOM.

**Inputs:**
- `currentSpec()?.content` — spec markdown string
- `contextContent()` — context markdown string
- `aiResult()` — AI-generated markdown string
- `DOMPurify.sanitize()` — strips `<script>`, `onerror`, etc.

**Expected Outputs (DOM-observable):**
- `.expanded-body`, `.brainstorm-result`, `.diff-unified` all inject HTML via `[innerHTML]`
- Content that would result in `<script>alert(1)</script>` must be stripped — confirm via `DOMPurify.sanitize('<script>alert(1)</script>')` returning empty string

**State Matrix:**

| Input content | DOMPurify strips | Rendered output |
|---|---|---|
| `"# Hello\n\nWorld"` | Nothing | `<h1>Hello</h1><p>World</p>` |
| `'<script>alert(1)</script>'` | `<script>` tag | Empty string |
| `'<img onerror="x">'` | `onerror` attribute | `<img>` with no event handler |

**Edge Cases:**
- `bypassSecurityTrustHtml` disables Angular's own sanitization — `DOMPurify` is the sole XSS defense. Tests must verify DOMPurify is called before `bypassSecurityTrustHtml`.

---

## Section 6 — SaaS & Auth Feature Specs (SA-01 through SA-21)

UI testable truth is the **tri-state plan**: `free | pro | lapsed`.

Divergence note — billing_status lapsed→free mapping: The backend Stripe webhook sets
`plan='lapsed'` on `invoice.payment_failed`. The frontend `SubscriptionService` receives
this value verbatim from `GET /api/billing/status`. The frontend tri-state maps directly:
`'free'` = never subscribed, `'pro'` = active subscription, `'lapsed'` = previously pro,
payment failed. Tests must not assume lapsed is treated as free — the upgrade page renders
distinct copy for lapsed vs free. Any test that collapses lapsed→free will produce false
positives on the plan-state branching logic.

---

### SA-01 — Login page

**Summary:** A standalone full-page centered card collects email and password; on submit
calls `AuthService.login()`; on failure shows an inline error; loading state disables
the submit button.

**Inputs:**
- `loading()` — signal, set true during `login()` call
- `error()` — signal, set to error string on failure
- `submit(event)` — form submit handler; reads `form.elements[0]` (email) and `form.elements[1]` (password)

**Expected Outputs (DOM-observable):**
- `.login-wrap` renders a centered `.login-card`
- Submit button shows `"Signing in…"` and `[disabled]` when `loading() === true`
- `.login-error` element visible when `error()` is truthy; contains error text
- On success: `AuthService.login()` stores token → `isLoggedIn` signal becomes true → app shell renders

**State Matrix:**

| loading | error | Button text | Error block |
|---|---|---|---|
| false | `''` | "Sign in" | Hidden |
| true | `''` | "Signing in…" | Hidden |
| false | `'Invalid email or password.'` | "Sign in" | Visible |

**Edge Cases:**
- The form uses `form.elements[0]` and `form.elements[1]` index access (not named fields) — tests must construct a real `FormEvent` or mock element access.
- Any error (network or 401) maps to the same `'Invalid email or password.'` message — no status-specific branching in `LoginComponent`.

**Mock boundary (Tier 3 — auth):** `AuthService.login` must be mocked. Do not call real `POST /api/auth/login` in unit tests.

---

### SA-02 — Signup / registration page

**Summary:** A standalone component at `/signup` with email + password form, client-side
validation, and error messages for 409, 429, and generic failures.

**Inputs:**
- `loading()` — signal
- `error()` — signal
- `submit(event)` — validates required fields, min 8-char password, then calls `AuthService.register()`

**Expected Outputs (DOM-observable):**
- Email and password inputs; submit button
- Client-side validation errors (shown via `error()` signal before any HTTP call):
  - Empty email or password: `"Email and password are required."`
  - Password < 8 chars: `"Password must be at least 8 characters."`
- HTTP error mapping:
  - 409: `"An account with this email already exists."`
  - 429: `"Too many attempts — please wait before trying again."`
  - Other: `"Registration failed. Please try again."`
- On success: navigates to `'/'`

**State Matrix:**

| password.length | HTTP response | Error shown |
|---|---|---|
| 0 (empty) | N/A (guard) | "Email and password are required." |
| 5 | N/A (guard) | "Password must be at least 8 characters." |
| 10 | 409 | "An account with this email already exists." |
| 10 | 429 | "Too many attempts — please wait before trying again." |
| 10 | 500 | "Registration failed. Please try again." |
| 10 | 201 success | Router navigates to "/" |

**Edge Cases:**
- Both client-side guards run before any HTTP call — `loading` is never set for guard failures.
- Email is `.trim()`-ed before validation but password is not — a password of `"       x"` (7 spaces + 1 char) has length 8 and passes the guard.

**Mock boundary (Tier 3 — auth):** `AuthService.register` and `Router.navigate` must be mocked.

---

### SA-03 — Auth service

**Summary:** Injectable wrapping `TokenLifecycleService`: owns `login()`, `register()`,
`signOut()`, and exposes `isLoggedIn` and `getStoredJwt()`.

**Inputs:**
- `HttpClient.post('/api/auth/login', { email, password })` → `AuthResponse`
- `HttpClient.post('/api/auth/register', { email, password })` → `AuthResponse`
- `TokenLifecycleService.storeToken(token)` — called after successful login/register
- `TokenLifecycleService.handleAuthFailure()` — called by `signOut()`

**Expected Outputs:**
- `login()` resolves with void on success; rejects on HTTP error
- `register()` same behavior
- `signOut()` calls `handleAuthFailure()` which clears storage + navigates to `/login`
- `isLoggedIn` — same signal reference as `TokenLifecycleService.isLoggedIn`
- `getStoredJwt()` — returns `localStorage.getItem('specview_jwt')` via `getRawToken()`

**State Matrix:**

| Method | HTTP outcome | isLoggedIn after | Side effect |
|---|---|---|---|
| `login()` | 200 with token | true | Token in localStorage |
| `login()` | 401 | unchanged | No token stored |
| `register()` | 201 with token | true | Token in localStorage |
| `signOut()` | N/A | false | Token removed; navigate to /login |

**Edge Cases:**
- `AuthService` does not touch `localStorage` directly — all persistence goes through `TokenLifecycleService`.

**Mock boundary (Tier 3 — auth):** HTTP calls require `HttpClientTestingModule`. `TokenLifecycleService` should be provided as a spy in isolation tests.

---

### SA-04 — Token lifecycle service

**Summary:** Manages token storage, JWT expiry decoding, proactive refresh within a
1-hour window, a mutex preventing concurrent refresh calls, and terminal 401 handling.

**Inputs:**
- `localStorage.getItem('specview_jwt')` — read on construction for initial `isLoggedIn` state
- `getToken()` — async; returns token or triggers refresh or calls `handleAuthFailure()`
- `REFRESH_WINDOW_SECONDS = 3600` — if `secondsUntilExpiry <= 3600`, refresh fires
- `HttpClient.post('/api/auth/refresh', {})` → `RefreshResponse`

**Expected Outputs:**
- `isLoggedIn` signal reflects current storage state
- `getToken()` returns: valid token (no op), refreshed token (within window), or null (expired/failure)
- `handleAuthFailure()`: removes token from localStorage, sets `isLoggedIn(false)`, navigates to `/login`
- Concurrent `getToken()` calls within refresh window share a single in-flight refresh promise

**State Matrix:**

| Token state | secondsUntilExpiry | getToken() result |
|---|---|---|
| No token | N/A | null |
| Valid, > 3600 s remaining | > 3600 | token (no refresh) |
| Valid, ≤ 3600 s remaining | ≤ 3600 | refreshed token (or null on failure) |
| Expired (≤ 0) | ≤ 0 | null (handleAuthFailure called) |
| Malformed JWT (no exp) | N/A (null) | token (returned as-is) |

**Edge Cases:**
- Mutex: two concurrent `getToken()` calls when within refresh window both receive the same `_refreshPromise`. The second call does not make a second HTTP request.
- `_decodeExp()` does not verify the JWT signature — malformed payloads return null (no exp), which is treated as a valid token.

**Mock boundary (Tier 3 — auth):** `HttpClient` must be mocked via `HttpClientTestingModule`. `Router.navigate` must be stubbed to avoid real navigation.

---

### SA-05 — Auth HTTP interceptor

**Summary:** Functional interceptor that attaches Bearer tokens to all non-public
requests and calls `handleAuthFailure()` on 401 responses.

**Inputs:**
- `PUBLIC_PATHS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh']`
- `TokenLifecycleService.getToken()` — async call per request
- `req.url` — checked against `PUBLIC_PATHS`
- 401 HTTP error response — triggers `handleAuthFailure()`

**Expected Outputs:**
- Public path requests: passed through with no `Authorization` header modification
- Non-public requests with token: `Authorization: Bearer <token>` header attached
- Non-public requests without token (null from `getToken()`): request passed through without header
- 401 response: `handleAuthFailure()` called; error re-thrown

**State Matrix:**

| Request URL | getToken() result | 401 response | Authorization header |
|---|---|---|---|
| `/api/auth/login` | any | any | Untouched |
| `/api/auth/refresh` | any | any | Untouched |
| `/api/projects` | `'token123'` | No | `Bearer token123` |
| `/api/projects` | null | No | Untouched |
| `/api/projects` | `'token123'` | Yes | Added then `handleAuthFailure()` called |

**Edge Cases:**
- The interceptor uses `from(lifecycle.getToken()).pipe(switchMap(...))` — the token is fetched asynchronously even for non-public paths.
- `startsWith` matching: a URL like `/api/auth/login/extra` is treated as public.

**Mock boundary (Tier 3 — auth):** `TokenLifecycleService` must be mocked. Use Angular `HttpClientTestingModule` with `provideInterceptors` configuration.

---

### SA-06 — Project ownership 403 handling

**Summary:** `ProjectsService.getProject()` converts a 403 HTTP error to
`AccessDeniedError`; the root component catches it and shows a full-panel access-denied message.

**Inputs:**
- `ProjectsService.getProject(id)` — throws `AccessDeniedError` on HTTP 403
- `selectProject(id)` — catches `AccessDeniedError` in root component
- `accessDenied()` — signal set to true on 403
- `[data-test="access-denied-message"]` — the access denied DOM block

**Expected Outputs (DOM-observable):**
- On 403: `accessDenied()` set to true; expanded panel visible; `.access-denied-state` block shown
- `.access-denied-heading`: `"You don't have access to this project."`
- `"Back to projects"` button calls `closeExpanded()`; resets `accessDenied` to false
- `activeProject()` is null during access-denied state (panel open but no project loaded)

**State Matrix:**

| HTTP response | accessDenied | Panel content |
|---|---|---|
| 200 with project | false | Spec reader |
| 403 | true | Access denied block |
| Other HTTP error | Re-thrown | No access-denied block (error propagates) |

**Edge Cases:**
- `AccessDeniedError` is a typed subclass of `Error` with `status = 403` and `type = 'access_denied'`. Tests must `instanceof AccessDeniedError` to confirm the conversion.

**Mock boundary:** `ProjectsService.getProject` must be mocked to reject with HTTP 403 error.

---

### SA-07 — Subscription service

**Summary:** Injectable with `plan` signal (tri-state), `isPro` computed, and methods
for `refresh()`, `startCheckout()`, and `verifySession()`. `refresh()` is called on
construction.

**Inputs:**
- `HttpClient.get('/api/billing/status')` → `{ plan: 'free' | 'pro' | 'lapsed' }`
- `HttpClient.post('/api/billing/create-checkout-session', {})` → `{ url: string }`
- `HttpClient.get('/api/billing/verify-session', { params: { session_id } })` → `{ plan }`

**Expected Outputs:**
- `plan()` signal: one of `'free' | 'pro' | 'lapsed'`; initial value `'free'`; updated by `refresh()`
- `isPro()`: computed `true` only when `plan() === 'pro'`
- `startCheckout()`: calls `redirect(url)` — protected method, overridable in tests
- `verifySession(sessionId)`: sets `plan` to the verified plan value

**State Matrix (plan signal):**

| API response plan | plan() after refresh | isPro() |
|---|---|---|
| `'free'` | `'free'` | false |
| `'pro'` | `'pro'` | true |
| `'lapsed'` | `'lapsed'` | false |

**Edge Cases:**
- `startCheckout()` calls `this.redirect(res.url)` — this is `window.location.href = url` in production. Tests must subclass or spy on `redirect()` to prevent navigation.
- `refresh()` is called in the constructor — DI must be set up before construction, or tests must stub HTTP before the service is instantiated.

**Mock boundary (Tier 3 — billing, Stripe):** All three HTTP endpoints require mocking. `redirect()` must be overridden to prevent `window.location` assignment in test environments.

---

### SA-08 — Billing HTTP interceptor

**Summary:** Reads `X-Usage-Remaining` / `X-Usage-Limit` headers from every successful
response; on 429, navigates to `/upgrade` with plan-appropriate reason; Pro users
on 429 only log a warning.

**Inputs:**
- Every `HttpResponse` carrying `X-Usage-Remaining` header
- `SubscriptionService.plan()` — read on 429 to determine reason
- `Router.navigate(['/upgrade'], { queryParams: { reason, feature } })`
- `err.error.feature` — from `LimitErrorBody`

**Expected Outputs (DOM-observable / state-observable):**
- On any response with `X-Usage-Remaining` header: `usageRemaining` signal updated with `{ remaining, limit }`
- On 429 with `plan === 'free'`: navigate to `/upgrade?reason=limit_reached&feature=<feature>`
- On 429 with `plan === 'lapsed'`: navigate to `/upgrade?reason=payment_lapsed&feature=<feature>`
- On 429 with `plan === 'pro'`: `console.warn` called; error re-thrown; NO navigation

**429 × Plan × Feature combinations (exhaustive):**

| Plan | 429 received | feature in body | reason in navigation |
|---|---|---|---|
| `free` | Yes | `'spec_gen'` | `/upgrade?reason=limit_reached&feature=spec_gen` |
| `free` | Yes | `'text_ops'` | `/upgrade?reason=limit_reached&feature=text_ops` |
| `free` | Yes | absent/null | `/upgrade?reason=limit_reached&feature=unknown` |
| `lapsed` | Yes | `'spec_gen'` | `/upgrade?reason=payment_lapsed&feature=spec_gen` |
| `lapsed` | Yes | absent/null | `/upgrade?reason=payment_lapsed&feature=unknown` |
| `pro` | Yes | any | No navigation; `console.warn`; error propagates |

**State Matrix (header parsing):**

| X-Usage-Remaining | X-Usage-Limit | usageRemaining signal |
|---|---|---|
| absent | absent | Signal not updated |
| `'5'` | `'10'` | `{ remaining: 5, limit: 10 }` |
| `'0'` | `'10'` | `{ remaining: 0, limit: 10 }` |
| `'5'` | absent | `{ remaining: 5, limit: 0 }` |

**Edge Cases:**
- The `tap` handler checks `'headers' in event` — `HttpSentEvent` and other non-response events pass through without header reading.
- `parseInt(remaining, 10)` — malformed header values (non-numeric) produce `NaN`; no guard exists.

**Mock boundary (Tier 3 — billing):** `SubscriptionService` and `Router` must be mocked. Use `HttpClientTestingModule` with the interceptor registered.

---

### SA-09 — Usage remaining shared state

**Summary:** A module-level `signal<UsageRemaining | null>` exported from
`usage.state.ts`; written by the billing interceptor; read by the usage meter component.

**Inputs:**
- `usageRemaining.set({ remaining, limit })` — called by billing interceptor
- No DI, no class — plain signal

**Expected Outputs (state-observable):**
- Initial value: `null`
- After interceptor writes: `{ remaining: number, limit: number }`
- `usageRemaining()` readable from any component importing the module

**State Matrix:**

| usageRemaining() | isWarning (in UsageMeter) | isVisible (in UsageMeter) |
|---|---|---|
| null | false | false (isVisible = !isPro && usage !== null) |
| `{ remaining: 5, limit: 10 }` | false (`remaining > 1`) | true (if not Pro) |
| `{ remaining: 1, limit: 10 }` | true | true |
| `{ remaining: 0, limit: 10 }` | true (`remaining <= 1`) | true |

**Edge Cases:**
- The signal is module-level — it persists across test runs unless explicitly reset between tests. Tests must call `usageRemaining.set(null)` in `afterEach`.

---

### SA-10 — Usage meter component

**Summary:** Standalone pill in the masthead showing `"N/M remaining"` for non-Pro
users when `usageRemaining` is non-null; warning style when remaining ≤ 1.

**Inputs:**
- `usageRemaining` — module-level signal from `usage.state.ts`
- `isPro` — computed from `SubscriptionService.isPro()`
- `isWarning` — computed: `usage !== null && usage.remaining <= 1`
- `isVisible` — computed: `!isPro() && usage() !== null`

**Expected Outputs (DOM-observable):**
- `[data-test="usage-meter"]` element present when `isVisible() === true`; absent otherwise
- Element text: `"N/M remaining"` where N = `remaining`, M = `limit`
- Element has class `usage-meter--warning` when `isWarning() === true`
- Zero additional HTTP requests — entirely driven by header state

**State Matrix:**

| isPro | usageRemaining | isVisible | isWarning | DOM |
|---|---|---|---|---|
| true | any | false | N/A | Meter hidden |
| false | null | false | N/A | Meter hidden |
| false | `{ remaining: 5, limit: 10 }` | true | false | `"5/10 remaining"`, no warning |
| false | `{ remaining: 1, limit: 10 }` | true | true | `"1/10 remaining"`, warning style |
| false | `{ remaining: 0, limit: 10 }` | true | true | `"0/10 remaining"`, warning style |

**Edge Cases:**
- `isWarning` threshold is `<= 1` (not `=== 0`) — both 0 and 1 remaining show warning style.

**Mock boundary (Tier 3 — billing):** `SubscriptionService` must be mocked to control `isPro()`. `usageRemaining` signal must be set directly in tests.

---

### SA-11 — Upgrade button in masthead

**Summary:** A button in masthead actions area, visible only for non-Pro users, that
navigates to `/upgrade`.

**Inputs:**
- `subscription.isPro()` — button hidden when true
- `navigateToUpgrade()` — calls `router.navigate(['/upgrade'])`

**Expected Outputs (DOM-observable):**
- `.upgrade-btn` present in masthead when `isPro() === false`
- `.upgrade-btn` absent when `isPro() === true`
- Clicking calls `navigateToUpgrade()` → `Router.navigate(['/upgrade'])`

**State Matrix:**

| plan | isPro | Button visible |
|---|---|---|
| `'free'` | false | Yes |
| `'lapsed'` | false | Yes |
| `'pro'` | true | No |

**Edge Cases:**
- Both `'free'` and `'lapsed'` show the upgrade button — their plan-specific copy is handled on the upgrade page, not here.

---

### SA-12 — Upgrade page

**Summary:** Standalone component at `/upgrade` with three plan-state views (free,
lapsed, pro), session verification flow, and a `headingText` computed that adapts to
plan + verification state.

**Inputs:**
- `ActivatedRoute.snapshot.queryParamMap` — reads `reason`, `feature`, `session_id`
- `SubscriptionService.plan()`, `.isPro()`
- `sessionId()` — if set, triggers `handleVerifySession()` in `ngOnInit`
- `loading()`, `verified()`, `error()` — signals managing async state
- `upgrade()` — calls `startCheckout()`

**Expected Outputs (DOM-observable):**
- When `loading() === true`: `"Confirming your subscription…"` loading block; all other content hidden
- When `verified() === true`: `[data-test="upgrade-confirmed"]` block; heading `"Welcome to Pro"`; "Go to Specview" link
- When `isPro() === true` (not via session): `[data-test="upgrade-pro-view"]`; heading `"You are on Pro"`; "Manage Subscription" link
- When `plan() === 'lapsed'`: `[data-test="upgrade-lapsed-view"]`; heading `"Update Your Payment Method"`; "Update Payment Method" link to `/api/billing/portal`
- Default (free): `[data-test="upgrade-free-view"]`; heading from `reason` signal; checkout button `[data-test="upgrade-checkout-btn"]`
- Error: `[data-test="upgrade-error"]` block visible when `error()` is set

**headingText computed:**

| verified | isPro | reason | headingText |
|---|---|---|---|
| true | any | any | "Welcome to Pro" |
| false | true | any | "You are on Pro" |
| false | false | `'payment_lapsed'` | "Update Your Payment Method" |
| false | false | `'limit_reached'` | "Usage Limit Reached" |
| false | false | `'direct'` | "Upgrade to Pro" |

**State Matrix (session_id presence × plan):**

| session_id | plan after verify | verified | error | Displayed block |
|---|---|---|---|---|
| absent | any | false | null | Plan-appropriate view (free/pro/lapsed) |
| present | `'pro'` | true | null | `upgrade-confirmed` |
| present | `'free'` / `'lapsed'` | false | error string | Error block + plan view |
| present | verify call throws | false | error string | Error block (refresh fallback tried) |

**Free-plan limit_reached view:**
- When `reason() === 'limit_reached'` AND `feature()` is non-empty: `[data-test="upgrade-limit-notice"]` shown with feature name
- When `feature()` is empty: notice hidden

**Edge Cases:**
- `handleVerifySession` first calls `verifySession()` (may throw — caught silently), then always calls `refresh()` (may also throw — caught silently). The plan is checked via `subscription.isPro()` after both.
- `upgrade()` does not call `loading.set(false)` on success — the redirect happens via `window.location.href`, so the component is destroyed before the finally block would run. On error, `loading.set(false)` runs in the catch block.

**Mock boundary (Tier 3 — auth, billing, Stripe):**
- `SubscriptionService`: mock all three methods (`verifySession`, `refresh`, `startCheckout`).
- `ActivatedRoute`: provide with `queryParamMap` snapshot containing test params.
- `redirect()`: override in test subclass to prevent `window.location.href` assignment.

---

### SA-13 — Full-page route routing bypass

**Summary:** `isFullPageRoute` signal listens to `NavigationEnd` events; when the
current path is in `FULL_PAGE_ROUTES` (`['/upgrade']`), the root component renders
`<router-outlet />` instead of the app shell.

**Inputs:**
- `FULL_PAGE_ROUTES = ['/upgrade']` — static array
- `Router.events` pipe filtered to `NavigationEnd`
- `e.urlAfterRedirects.split('?')[0]` — strips query string before comparison

**Expected Outputs (DOM-observable):**
- On navigation to `/upgrade`: `isFullPageRoute()` becomes true; app shell hidden; `<router-outlet />` shown
- On navigation away from `/upgrade` (e.g. to `/`): `isFullPageRoute()` becomes false; app shell shown
- Initial render at `/upgrade` (direct URL): constructor sets `isFullPageRoute` synchronously from `this.router.url`

**State Matrix:**

| Current route | isLoggedIn | isFullPageRoute | Rendered |
|---|---|---|---|
| `/` | true | false | App shell |
| `/upgrade` | true | true | Router outlet |
| `/upgrade?session_id=x` | true | true | Router outlet (query stripped) |
| `/upgrade` | false | true | First branch router-outlet (not logged in) |

**Edge Cases:**
- Query string stripping: `/upgrade?session_id=abc` → `urlAfterRedirects.split('?')[0]` → `/upgrade` — correctly matches.
- New full-page routes require adding to `FULL_PAGE_ROUTES` only; no template change needed.

---

### SA-14 — IP-based registration rate limiting (backend only)

**Summary:** In-process sliding window rate limiter on `POST /api/auth/register`:
5 requests per IP per hour.

**Inputs:** IP address from `request.remote_addr`.

**Expected Outputs:** HTTP 429 response with `error` message when limit exceeded.

**State Matrix:**

| Requests in past hour | Response |
|---|---|
| ≤ 5 | 201 or pass-through |
| > 5 | 429 |

**Edge Cases:**
- In-process dict is not shared across worker processes — load-balanced deployments may not enforce limits correctly.
- No Angular source; frontend SA-02 handles the 429 response by showing `"Too many attempts…"`.

---

### SA-15 — Security headers (backend only)

**Summary:** `after_request` handler sets four security headers on every response.

**Expected Outputs:** Every HTTP response includes:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Request-ID: <uuid>` (unique per request)

**State Matrix:**

| Route | Headers present |
|---|---|
| Any route (authenticated or not) | All four headers |

**Edge Cases:**
- `X-Request-ID` is generated per-request — tests must assert presence and UUID format, not exact value.

---

### SA-16 — Security canary endpoint (backend only)

**Summary:** `GET /api/health/security` returns 503 if `SKIP_AUTH` is active in a
non-development environment, 200 otherwise.

**State Matrix:**

| FLASK_ENV | SKIP_AUTH | Response |
|---|---|---|
| `development` | true | 200 |
| `production` | false | 200 |
| `production` | true | 503 |

**Edge Cases:**
- Used in deploy pipeline validation — a 503 here blocks deployment.

---

### SA-17 — SKIP_AUTH environment gating (backend only)

**Summary:** The `@require_auth` SKIP_AUTH bypass is only honoured when
`FLASK_ENV=development`; in production the flag is ignored.

**State Matrix:**

| FLASK_ENV | SKIP_AUTH env | Auth enforced |
|---|---|---|
| `development` | true | No (bypass active) |
| `development` | false | Yes |
| `production` | true | Yes (bypass ignored) |
| `production` | false | Yes |

**Edge Cases:**
- Tests that use `SKIP_AUTH=true` must also set `FLASK_ENV=development` or the bypass will not activate.

---

### SA-18 — Project isolation and ownership enforcement (backend only)

**Summary:** `@require_project_ownership` decorator loads the project by slug, checks
`project.user_id == g.current_user.id`, returns 403 on mismatch.

**State Matrix:**

| project.user_id matches g.current_user.id | Response |
|---|---|
| Yes | Pass through to route handler |
| No | 403 `{"error": "Access denied"}` |
| Project not found | 404 |

**Edge Cases:**
- The 403 from this decorator is what `ProjectsService.getProject()` in the frontend converts to `AccessDeniedError` (SA-06).

---

### SA-19 — Billing 429 usage header emission (backend only)

**Summary:** `@check_usage_limit` emits `X-Usage-Remaining` and `X-Usage-Limit` headers
on every successful response; returns 429 with `LimitErrorBody` on limit exceeded.

**Expected Outputs:**
- Every successful response from a usage-limited endpoint: headers `X-Usage-Remaining: N` and `X-Usage-Limit: M`
- When limit exceeded: 429 with `{ error, feature, limit, reset_at, upgrade_url }`

**State Matrix:**

| Usage count vs limit | Response | Headers emitted |
|---|---|---|
| Below limit | 200 | `X-Usage-Remaining`, `X-Usage-Limit` |
| At/above limit | 429 | No `X-Usage-Remaining` (429 is an error response) |

**Edge Cases:**
- The frontend billing interceptor (SA-08) reads these headers from success responses only. The 429 error body `feature` field drives the `feature` query param on the upgrade redirect.

---

### SA-20 — Lapsed plan state

**Summary:** The `invoice.payment_failed` Stripe webhook writes `plan='lapsed'` to the
User record; the frontend tri-state carries this verbatim.

**Divergence note (lapsed→free):** The backend stores and returns `'lapsed'` as a
distinct value — it must never be mapped to `'free'` in frontend tests. The upgrade
page (`[data-test="upgrade-lapsed-view"]`) renders only when `plan() === 'lapsed'`
exactly. Any test that substitutes `'free'` for `'lapsed'` will not exercise the lapsed
payment-method restore flow.

**State Matrix:**

| Stripe event | DB plan | Frontend plan() | Upgrade page view |
|---|---|---|---|
| `checkout.session.completed` | `'pro'` | `'pro'` | Pro view |
| `invoice.payment_failed` | `'lapsed'` | `'lapsed'` | Lapsed view |
| No subscription | `'free'` | `'free'` | Free view |

**Edge Cases:**
- `SubscriptionService.refresh()` is the only frontend path that updates `plan()` from the API — there is no WebSocket or push update. A user whose webhook fires while they are on the upgrade page will see stale state until the next `refresh()` call.

**Mock boundary (Tier 3 — billing):** Tests for the lapsed flow must set `plan` signal to `'lapsed'` directly (not `'free'`) and confirm `[data-test="upgrade-lapsed-view"]` is rendered.

---

### SA-21 — Stripe checkout and session verification

**Summary:** Full Stripe checkout flow: `startCheckout()` redirects to Stripe; after
payment Stripe redirects to `/upgrade?session_id=...`; `verifySession()` confirms
payment and writes `plan='pro'` as a fallback.

**Inputs:**
- `startCheckout()` → `POST /api/billing/create-checkout-session` → `{ url }` → `redirect(url)`
- `verifySession(sessionId)` → `GET /api/billing/verify-session?session_id=<id>` → `{ plan }`
- Query param `session_id` on `/upgrade` route — detected in `ngOnInit`

**Expected Outputs:**
- `startCheckout()`: `redirect()` called with Stripe Checkout URL; no return value
- `verifySession()`: `plan` signal updated to verified plan
- After `ngOnInit` with `session_id`: `handleVerifySession()` calls `verifySession()` then `refresh()`; if `isPro()` is true → `verified.set(true)`; else → `error.set('<message>')`

**State Matrix:**

| session_id present | verifySession outcome | refresh outcome | isPro after | verified | error |
|---|---|---|---|---|---|
| No | N/A | N/A | (pre-existing) | false | null |
| Yes | resolves (pro) | resolves (pro) | true | true | null |
| Yes | throws | resolves (pro) | true | true | null |
| Yes | throws | resolves (free) | false | false | error string |
| Yes | resolves (lapsed) | resolves (lapsed) | false | false | error string |

**Edge Cases:**
- Webhook may fire before browser returns from Stripe — in this case `refresh()` alone (without `verifySession`) is sufficient to confirm Pro. `verifySession` is a belt-and-suspenders check.
- `verifySession` failure is silently swallowed (`catch { }`) — the `refresh()` call always runs.

**Mock boundary (Tier 3 — auth, billing, Stripe):** `verifySession`, `refresh`, and `startCheckout` on `SubscriptionService` must be mocked. `redirect()` must be overridden. `ActivatedRoute` must be provided with a snapshot containing `session_id`.

---

## Section 7 — Testing Architecture & Coverage Gap Map (Task 4)

### 7.1 Four-layer test pyramid

The specview test suite is organized into four distinct layers, each building on the one below:

```
Layer 4: Feature Specs (this document)
         54 features with state matrices and edge cases.
         Source of truth for expected behavior. Everything below
         must trace back to a row in a state matrix here.

Layer 3: Gherkin scenarios (e2e/features/*.feature)
         Human-readable scenario files per product-behavior.md flow.
         pytest-bdd converts each scenario into a runnable test.
         These are the integration acceptance tests.

Layer 2: Playwright E2E tests (e2e/ with pytest-playwright)
         Scenarios drive a real browser against the full stack
         (Flask mock provider + Angular dev server). Fixtures in
         e2e/conftest.py start both servers session-scoped.

Layer 1: Karma / Jasmine unit tests (web-ng/src/app/**/*.spec.ts)
         Fast, no browser, no server. Cover service methods, signal
         state machines, pure functions, and pipe transforms.
         Backend unit tests (pytest) cover routes, services, chain
         adapter, workflows, and structural rules.
```

The pyramid flows upward: unit tests prove atomic behavior; E2E tests prove
product flows end-to-end. Feature specs (this document) sit above the pyramid
as the specification layer — not a test file, but the contract all three layers
must satisfy.

### 7.2 Existing infrastructure catalog

#### Karma (Angular unit tests)

File: `web-ng/karma.conf.js`

- Framework: Jasmine + `@angular-devkit/build-angular`
- Browsers: Chrome (local), ChromeHeadlessCI (CI via `KARMA_BROWSERS` env var)
- Coverage reporters: HTML, text-summary, json-summary → `coverage/web-ng/`
- Plugins: `karma-jasmine`, `karma-chrome-launcher`, `karma-jasmine-html-reporter`,
  `karma-coverage`

#### E2E fixtures

File: `e2e/conftest.py`

- `flask_server` (session-scoped): starts `python -m flask run --port 5001` with
  `CHAIN_PROVIDER=mock`. Waits for port 5001 within 30 s.
- `angular_server` (session-scoped): starts `npx ng serve --port 4201`. Waits
  up to 120 s.
- `context` (function-scoped): mutable dict shared across Gherkin steps in a
  single scenario.
- Step definitions discovered from `e2e/steps/common_steps`.

#### Existing Gherkin feature files (`e2e/features/`)

| File | Product-behavior flow | Scenarios |
|---|---|---|
| `brainstorm.feature` | Flow 1 — Brainstorm | 2: happy path + 500 failure |
| `bootstrap-pipeline.feature` | Flow 2 — Brainstorm → Pipeline | 2: happy path + poll error |
| `epic-guide.feature` | Flow 3 — Epic-Guide Generation | 2: happy path + timeout |
| `billing-gate.feature` | Flow 4 — Billing Gate (free tier) | 2: blocked free user + allowed pro user |
| `pro-check.feature` | Flow 5 — Pro Subscription Check | 2: pro bypasses limit + DB failure fail-safe |

All five product-behavior flows from `product-behavior.md` have a corresponding
feature file. Each file covers happy path and primary failure shape.

#### Existing mock files (`web-ng/src/app/services/`)

| File | Service mocked |
|---|---|
| `projects.service.mock.ts` | `ProjectsService` — all HTTP methods |
| `ai.service.mock.ts` | `AiService` — all AI text op methods |
| `subscription.service.mock.ts` | `SubscriptionService` — plan signal + billing methods |
| `token-lifecycle.service.mock.ts` | `TokenLifecycleService` — token storage + lifecycle |

All four core services have mock factories. Each exports
`createMock{Name}Service()` returning a typed Jasmine spy object.

### 7.3 Coverage matrix

States: **covered** = test(s) directly exercise this feature; **partial** = some
states covered but not all matrix rows; **gap** = no test at any layer; **N/A** =
feature is backend-only or infrastructure, no frontend unit test applicable.

Columns:
- **Spec** = feature spec exists in this document (Section 5 or 6)
- **Gherkin** = scenario in `e2e/features/*.feature`
- **E2E** = Playwright scenario wired and runnable (Gherkin must exist first)
- **Unit** = `*.spec.ts` test covering the feature

| Feature | Spec | Gherkin | E2E | Unit |
|---|---|---|---|---|
| OV-01 Auth gate | covered | gap | gap | partial |
| OV-02 Masthead nameplate | covered | gap | gap | gap |
| OV-03 Section navigation bar | covered | gap | gap | gap |
| OV-04 Section count pulse animation | covered | gap | gap | gap |
| OV-05 Generation status bar | covered | gap | gap | gap |
| OV-06 Update banner | covered | gap | gap | gap |
| OV-07 Search / filter bar | covered | gap | gap | gap |
| OV-08 Project grid with taxonomy grouping | covered | gap | gap | partial |
| OV-09 Project cards with teasers | covered | gap | gap | covered |
| OV-10 Polling / background refresh | covered | gap | gap | partial |
| OV-11 Dark mode toggle | covered | gap | gap | gap |
| OV-12 Context viewer | covered | gap | gap | partial |
| OV-13 Create project modal | covered | gap | gap | gap |
| OV-14 Spec-gen pipeline with incremental file save | covered | covered | gap | partial |
| OV-15 Expanded project reader panel | covered | gap | gap | gap |
| OV-16 Expanded reader sidebar | covered | gap | gap | gap |
| OV-17 Sidebar status row | covered | gap | gap | gap |
| OV-18 Per-file dot tracking | covered | gap | gap | gap |
| OV-19 Generate Specs button | covered | gap | gap | gap |
| OV-20 Generate Guide button (epic guide) | covered | covered | gap | partial |
| OV-21 AI text ops chips | covered | covered | gap | covered |
| OV-22 Style preset chips | covered | gap | gap | covered |
| OV-23 AI result panel with diff view | covered | gap | gap | gap |
| OV-24 Result toolbar | covered | gap | gap | gap |
| OV-25 Undo / redo stack | covered | gap | gap | gap |
| OV-26 Brainstorm follow-up input | covered | gap | gap | gap |
| OV-27 Generate Specs from brainstorm result | covered | gap | gap | gap |
| OV-28 Section taxonomy service | covered | gap | gap | covered |
| OV-29 Project teaser service | covered | gap | gap | covered |
| OV-30 Word count pipe | covered | gap | gap | covered |
| OV-31 Panel slide animation | covered | gap | gap | N/A |
| OV-32 Spec file canonical ordering | covered | gap | gap | covered |
| OV-33 Markdown rendering with XSS sanitization | covered | gap | gap | gap |
| SA-01 Login page | covered | gap | gap | gap |
| SA-02 Signup / registration page | covered | gap | gap | gap |
| SA-03 Auth service | covered | gap | gap | covered |
| SA-04 Token lifecycle service | covered | gap | gap | covered |
| SA-05 Auth HTTP interceptor | covered | gap | gap | gap |
| SA-06 Project ownership 403 handling | covered | gap | gap | partial |
| SA-07 Subscription service | covered | gap | gap | covered |
| SA-08 Billing HTTP interceptor | covered | covered | gap | gap |
| SA-09 Usage remaining shared state | covered | gap | gap | gap |
| SA-10 Usage meter component | covered | covered | gap | gap |
| SA-11 Upgrade button in masthead | covered | gap | gap | gap |
| SA-12 Upgrade page | covered | covered | gap | gap |
| SA-13 Full-page route routing bypass | covered | gap | gap | gap |
| SA-14 IP-based registration rate limiting | covered | gap | gap | N/A |
| SA-15 Security headers | covered | gap | gap | N/A |
| SA-16 Security canary endpoint | covered | gap | gap | N/A |
| SA-17 SKIP_AUTH environment gating | covered | gap | gap | N/A |
| SA-18 Project isolation and ownership enforcement | covered | gap | gap | N/A |
| SA-19 Billing 429 usage header emission | covered | gap | gap | N/A |
| SA-20 Lapsed plan state | covered | gap | gap | partial |
| SA-21 Stripe checkout and session verification | covered | covered | gap | partial |

### 7.4 Gap summary by scope

#### Phase 2 scope — Gherkin + Playwright E2E gaps

The E2E gap column is 100% gap across all 54 features. This is because
the Playwright step implementations in `e2e/steps/common_steps.py` have not
been confirmed runnable against the full stack — the feature files exist but
step bindings need validation. Phase 2 work is:

1. Write missing Gherkin scenarios for every feature without a `covered` entry:
   - All OV features except OV-14 (bootstrap pipeline), OV-20 (epic guide),
     OV-21 (brainstorm chip covered by `brainstorm.feature`), OV-22 (style presets —
     no standalone scenario, exercises same route as OV-21)
   - SA-01, SA-02, SA-05, SA-06, SA-08, SA-09, SA-10, SA-11, SA-12, SA-13, SA-20, SA-21
     all lack Gherkin scenarios. SA-04 (billing gate + pro check) has feature files but
     no auth-flow scenario.
2. Wire Playwright step definitions for all five existing feature files.
3. Validate the `flask_server` + `angular_server` fixture chain runs end-to-end in CI.

Priority order for Gherkin authoring (by product-behavior.md flow coverage risk):
- High: SA-01 (login), SA-02 (signup), OV-13 (create project modal), OV-14 poll
  path with `partial_files`
- Medium: SA-08 (billing interceptor 429 navigation), SA-12 (upgrade page states),
  OV-10 (poll error state)
- Low: OV-02 through OV-07 (visual/layout features — hard to E2E test reliably)

#### Phase 3 scope — unit test gaps and partials

Frontend unit test gaps (no `*.spec.ts` coverage):

- OV-02, OV-03, OV-04, OV-05, OV-06, OV-07, OV-11, OV-13, OV-15, OV-16, OV-17,
  OV-18, OV-19, OV-23, OV-24, OV-25, OV-26, OV-27, OV-31 (N/A), OV-33
- SA-01, SA-02, SA-05, SA-08, SA-09, SA-10, SA-11, SA-12, SA-13

Frontend unit test partials (exist but incomplete state matrix coverage):

- OV-01: `AppComponent` spec only tests create + polling lifecycle; auth gate
  branch (logged-in vs logged-out template toggle) is not directly asserted.
- OV-08: `sectionFor` is covered by `section-taxonomy.service.spec.ts` but the
  grid grouping computed signal and `projectsBySection` rendering are not tested.
- OV-10: Poll timer management tested via fakeAsync; `lastSyncAt`,
  `lastSyncElapsed`, `pollOk`, and `updateBanner` signals are not tested.
- OV-12: `getContext` HTTP method covered in `projects.service.spec.ts`; the
  component-level `openContext()` → `contextContent` signal flow is not tested.
- OV-14: `startBootstrap` and `pollBootstrap` covered; `_runBootstrap()` 
  component orchestration (file-save loop, status transitions) not tested.
- OV-20: `startEpicGuide` and `pollEpicGuide` covered; component `generateEpicGuide()`
  orchestration not tested.
- SA-06: `getProject` HTTP method covered; `AccessDeniedError` conversion and
  `accessDenied` signal in component not tested.
- SA-20: `plan` signal and `isPro` computed covered; lapsed-specific upgrade page
  copy and CTA distinction from free not unit tested.
- SA-21: `verifySession` and `startCheckout` covered in `subscription.service.spec.ts`;
  `UpgradeComponent.handleVerifySession()` orchestration not tested.

### 7.5 Overlap with product-behavior.md

`product-behavior.md` defines five core flows. Mapping to this matrix:

| Product-behavior flow | Feature IDs covered | Gherkin file | E2E gap |
|---|---|---|---|
| Flow 1 — Brainstorm | OV-21, OV-26, OV-27 | `brainstorm.feature` (2 scenarios) | Step impl needed |
| Flow 2 — Brainstorm → Pipeline | OV-14, OV-19, OV-27 | `bootstrap-pipeline.feature` (2 scenarios) | Step impl needed |
| Flow 3 — Epic-Guide Generation | OV-20 | `epic-guide.feature` (2 scenarios) | Step impl needed |
| Flow 4 — Billing Gate | SA-08, SA-09, SA-10, SA-19 | `billing-gate.feature` (2 scenarios) | Step impl needed |
| Flow 5 — Pro Subscription Check | SA-07, SA-19, SA-20 | `pro-check.feature` (2 scenarios) | Step impl needed |

The five feature files cover all five product-behavior flows at the scenario
title level. The E2E gap across all flows is identical: step implementations
in `e2e/steps/common_steps.py` need to be completed and the full-stack fixture
chain validated. This is the entirety of Phase 2 E2E work.

---

## Section 8 — Phase 3 Unit Test Audit (Task 5)

### 8.1 Summary counts

| Metric | Count |
|---|---|
| Frontend `*.spec.ts` files | 9 |
| Frontend describe blocks (total) | 28 |
| Frontend it() tests (total) | 146 |
| Backend pytest test files | 56 |
| Backend pytest tests (total) | 830 |
| Frontend tests: aligned | 121 |
| Frontend tests: misaligned | 0 |
| Frontend tests: orphaned | 25 |
| Backend tests: directly map to frontend features | ~120 (ai + auth + billing + data/projects routes) |
| Backend tests: infrastructure / no frontend feature | ~710 (chain, runtime, quality, observability, data/git) |

### 8.2 Frontend spec.ts inventory

Each file is listed with its describe blocks and all test titles. Classification
(aligned / misaligned / orphaned) follows the state matrix rows in Sections 5 and 6.

---

#### `web-ng/src/app/app.component.spec.ts`

**Describe blocks:**
- `AppComponent`
- `AppComponent — polling lifecycle`

**Tests:**

| Test title | Classification |
|---|---|
| should create the app | aligned → OV-01 (component instantiation) |
| stops polling (pollTimer becomes null) when listProjects returns successfully on first call | aligned → OV-10 (poll stop on max retries) |
| sets pollingError signal after POLL_MAX_RETRIES retries | aligned → OV-10 (pollingError signal) |
| clears pollTimer on ngOnDestroy | aligned → OV-10 (clearInterval on destroy) |
| renders [data-test="polling-error"] when pollingError signal is set | aligned → OV-10 (DOM state) |

All 5 tests: aligned.

---

#### `web-ng/src/app/services/ai.service.spec.ts`

**Describe blocks:**
- `AiService` (root)
- `AiService > brainstorm`
- `AiService > expand`
- `AiService > compress`
- `AiService > clarify`
- `AiService > simplify`
- `AiService > tldr`
- `AiService > bullets`
- `AiService > styleAs`

**Tests:**

| Test title | Classification |
|---|---|
| POSTs to /api/brainstorm with text only when optional fields are absent | aligned → OV-21 (brainstorm HTTP contract) |
| includes question in POST body when provided | aligned → OV-21 |
| includes context in POST body when provided | aligned → OV-21 |
| includes both question and context when both are provided | aligned → OV-21 |
| resolves with the body of the HTTP response | aligned → OV-21 |
| omits question from body when question is empty string (falsy) | aligned → OV-21 edge case |
| omits context from body when context is empty string (falsy) | aligned → OV-21 edge case |
| POSTs to /api/expand with text | aligned → OV-21 (expand chip) |
| resolves with the response body (expand) | aligned → OV-21 |
| POSTs to /api/compress with text | aligned → OV-21 (compress chip) |
| resolves with the response body (compress) | aligned → OV-21 |
| POSTs to /api/clarify with text | aligned → OV-21 (clarify chip) |
| resolves with the response body (clarify) | aligned → OV-21 |
| POSTs to /api/simplify with text | aligned → OV-21 (simplify chip) |
| resolves with the response body (simplify) | aligned → OV-21 |
| POSTs to /api/tldr with text | aligned → OV-21 (TL;DR chip) |
| resolves with the response body (tldr) | aligned → OV-21 |
| POSTs to /api/bullets with text | aligned → OV-21 (bullets chip) |
| resolves with the response body (bullets) | aligned → OV-21 |
| POSTs to /api/rewrite with text and style | aligned → OV-22 (style presets → styleAs) |
| passes style value as-is to the request body | aligned → OV-22 |
| resolves with the response body (styleAs) | aligned → OV-22 |

All 21 tests: aligned.

---

#### `web-ng/src/app/services/auth.service.spec.ts`

**Describe blocks:**
- `AuthService`
- `AuthService > isLoggedIn`
- `AuthService > login`
- `AuthService > register`
- `AuthService > signOut`
- `AuthService > getStoredJwt`

**Tests:**

| Test title | Classification |
|---|---|
| returns false when lifecycle signal is false | aligned → SA-03 (isLoggedIn delegation) |
| returns true when lifecycle signal is true | aligned → SA-03 |
| POSTs to /api/auth/login with email and password | aligned → SA-03 (login method) |
| calls storeToken with the token from the response | aligned → SA-03 |
| propagates HTTP errors to the caller (login) | aligned → SA-03 edge case |
| POSTs to /api/auth/register with email and password | aligned → SA-03 (register method) |
| calls storeToken with the token from the registration response | aligned → SA-03 |
| propagates HTTP errors to the caller (register) | aligned → SA-03 edge case |
| delegates to lifecycle.handleAuthFailure | aligned → SA-03 (signOut) |
| returns null when lifecycle.getRawToken returns null | aligned → SA-03 (getStoredJwt) / SA-05 |
| returns the token when lifecycle.getRawToken returns a string | aligned → SA-03 / SA-05 |

All 11 tests: aligned.

---

#### `web-ng/src/app/services/project-teaser.spec.ts`

**Describe blocks:**
- `firstNonHeadingSentence`
- `countTasks`
- `projectTeaser`
- `projectTeaser > Active section`
- `projectTeaser > Specced section`
- `projectTeaser > Ready to build section`
- `projectTeaser > Braindumps section`
- `projectTeaser > Archive section`
- `projectTeaser > unknown section fallback`

**Tests (33 total):**

`firstNonHeadingSentence` (13 tests): all aligned → OV-29 (pure function behavior).
`countTasks` (6 tests): all aligned → OV-29.
`projectTeaser` by section (14 tests): all aligned → OV-09 (teaser display) and OV-29
(pure function contract for each section branch).

All 33 tests: aligned.

---

#### `web-ng/src/app/services/projects.service.spec.ts`

**Describe blocks:**
- `sortSpecs (via listProjects)`
- `ProjectsService`
- `ProjectsService > listProjects`
- `ProjectsService > getProject`
- `ProjectsService > getContext`
- `ProjectsService > startBootstrap`
- `ProjectsService > pollBootstrap`
- `ProjectsService > createProject`
- `ProjectsService > saveFile`
- `ProjectsService > startEpicGuide`
- `ProjectsService > pollEpicGuide`

**Tests:**

| Test title | Classification |
|---|---|
| orders specs in canonical sequence regardless of API response order | aligned → OV-32 |
| places unknown filenames after all canonical entries | aligned → OV-32 |
| sorts multiple unknown filenames alphabetically among themselves | aligned → OV-32 |
| handles a project with no specs | aligned → OV-32 edge case |
| GETs /api/projects and returns sorted project list | aligned → OV-10 (listProjects poll) / OV-32 |
| GETs /api/projects/:id | aligned → OV-15 (getProject for reader panel) |
| sorts specs returned from the API (getProject) | aligned → OV-32 |
| GETs /api/context/:key | aligned → OV-12 (context viewer) |
| resolves with content and optional text field | aligned → OV-12 |
| POSTs to /api/ai/text/bootstrap-project with project_name and braindump | aligned → OV-14 |
| GETs /api/ai/text/bootstrap-project/status/:jobId | aligned → OV-14 (poll) |
| resolves with done=true and files when job completes | aligned → OV-14 |
| POSTs to /api/projects with name and files | aligned → OV-13 / OV-14 (createProject) |
| PUTs to /api/projects/:id/files/:filename with content | aligned → OV-14 (saveFile) / OV-24 (apply result) |
| resolves without error on success (saveFile) | aligned → OV-14 |
| POSTs to /api/projects/:id/generate-epic-guide | aligned → OV-20 |
| resolves with alreadyRunning flag when job is already in progress | aligned → OV-20 edge case |
| GETs /api/projects/:id/generate-epic-guide/status | aligned → OV-20 (poll) |
| resolves with filename when job completes | aligned → OV-20 |
| resolves with error field when job fails | aligned → OV-20 edge case |

All 20 tests: aligned.

Note: `AccessDeniedError` conversion for 403 responses (SA-06) is not tested here —
this is a gap in `projects.service.spec.ts`.

---

#### `web-ng/src/app/services/section-taxonomy.service.spec.ts`

**Describe blocks:**
- `SECTION_ORDER`
- `sectionFor`
- `sectionFor > active-state precedence — hasActiveJob overrides file state`
- `sectionFor > file-based classification — hasActiveJob is false`
- `sectionFor > archive override — archived flag wins over all file states`

**Tests (18 total):**

`SECTION_ORDER` (2 tests): aligned → OV-03 (section nav order) / OV-28 (taxonomy service).
`sectionFor active-state` (4 parameterized cases): aligned → OV-28 state matrix.
`sectionFor file-based` (8 parameterized cases): aligned → OV-28 state matrix.
`sectionFor archive override` (4 cases): aligned → OV-28 edge cases.

All 18 tests: aligned.

---

#### `web-ng/src/app/services/subscription.service.spec.ts`

**Describe blocks:**
- `SubscriptionService`
- `SubscriptionService > isPro`
- `SubscriptionService > refresh()`
- `SubscriptionService > verifySession()`
- `SubscriptionService > startCheckout()`

**Tests:**

| Test title | Classification |
|---|---|
| should have initial plan state of "free" | aligned → SA-07 (initial plan signal) |
| returns false when plan is "free" (isPro) | aligned → SA-07 |
| returns false when plan is "lapsed" (isPro) | aligned → SA-07 / SA-20 (lapsed state) |
| returns true when plan is "pro" (isPro) | aligned → SA-07 |
| updates plan signal from API response (refresh) | aligned → SA-07 |
| sets plan to "lapsed" when API returns lapsed | aligned → SA-07 / SA-20 |
| updates plan state on success (verifySession) | aligned → SA-21 |
| keeps plan at current value if verify returns free | aligned → SA-21 edge case |
| calls POST /api/billing/create-checkout-session | aligned → SA-21 (startCheckout) |

All 9 tests: aligned.

---

#### `web-ng/src/app/services/token-lifecycle.service.spec.ts`

**Describe blocks:**
- `TokenLifecycleService`
- `TokenLifecycleService — _decodeExp (via getToken)`
- `TokenLifecycleService — getToken fresh path`
- `TokenLifecycleService — getToken expired path`
- `TokenLifecycleService — getToken refresh path`
- `TokenLifecycleService — handleAuthFailure`

**Tests:**

| Test title | Classification |
|---|---|
| creates successfully | aligned → SA-04 |
| isLoggedIn is false when localStorage has no token | aligned → SA-04 |
| storeToken sets isLoggedIn to true | aligned → SA-04 |
| getRawToken returns null when no token stored | aligned → SA-04 |
| getRawToken returns stored token after storeToken | aligned → SA-04 |
| getToken returns the raw token when it has no exp claim | aligned → SA-04 (non-expiring path) |
| getToken returns null when no token in localStorage | aligned → SA-04 |
| getToken returns the raw token when exp is malformed | aligned → SA-04 edge case |
| getToken returns the raw token when JWT has wrong segment count | aligned → SA-04 edge case |
| getToken returns the raw token when JWT payload is not valid JSON | aligned → SA-04 edge case |
| returns the token directly when expiry is well beyond the refresh window | aligned → SA-04 (fresh path) |
| returns null and calls handleAuthFailure when token is expired | aligned → SA-04 (expired path) |
| calls /api/auth/refresh and stores the new token when within refresh window | aligned → SA-04 (refresh path) |
| concurrent getToken calls share one in-flight refresh (mutex) | aligned → SA-04 (mutex) |
| returns null and calls handleAuthFailure when refresh HTTP call fails | aligned → SA-04 edge case |
| removes token from localStorage (handleAuthFailure) | aligned → SA-04 / SA-05 |
| sets isLoggedIn to false (handleAuthFailure) | aligned → SA-04 |
| navigates to /login (handleAuthFailure) | aligned → SA-04 |

All 18 tests: aligned.

---

#### `web-ng/src/app/word-count.pipe.spec.ts`

**Describe blocks:**
- `WordCountPipe`

**Tests:**

| Test title | Classification |
|---|---|
| returns 0 for null | aligned → OV-30 |
| returns 0 for undefined | aligned → OV-30 |
| returns 0 for empty string | aligned → OV-30 |
| returns 0 for whitespace-only string | aligned → OV-30 |
| counts a single word | aligned → OV-30 |
| counts two space-separated words | aligned → OV-30 |
| counts words separated by multiple spaces | aligned → OV-30 |
| counts words separated by tabs | aligned → OV-30 |
| counts words separated by newlines | aligned → OV-30 |
| counts words in a typical markdown sentence | aligned → OV-30 |
| ignores leading and trailing whitespace | aligned → OV-30 |

All 11 tests: aligned.

---

### 8.3 Frontend classification summary

**Total: 146 tests across 9 files.**

- Aligned: 146 (100%) — every existing test maps to at least one spec state matrix row.
- Misaligned: 0 — no test contradicts a spec.
- Orphaned: 0 — no test covers an implementation detail that has no spec counterpart.

The 25 "orphaned" count in the summary table is a **revised downward to 0** after
detailed review. What initially appeared as potential orphans (e.g., internal token
decode branches, empty-string falsy guard in AiService) are in fact edge cases
documented in the state matrices of SA-04 and OV-21. All 146 tests are traceable
to feature spec rows.

### 8.4 Backend pytest audit (830 tests across 56 files)

Grouped by module with frontend feature overlap noted.

#### `modules/ai/routes/tests/` — AI HTTP routes

| File | Tests | Frontend features covered |
|---|---|---|
| `test_actions.py` | ~35 | OV-21 (brainstorm/expand/compress/clarify/simplify/tldr/bullets), OV-22 (rewrite/styleAs) |
| `test_generic_skill_route.py` | ~10 | OV-21 (route contract) |
| `test_skill_integration.py` | ~12 | OV-21 (skill execution integration) |
| `test_spec_gen_routes.py` | ~20 | OV-14 (bootstrap), OV-19 (trigger) |
| `test_text_bootstrap.py` | ~25 | OV-14 (bootstrap pipeline HTTP) |
| `test_task_gen_routes.py` | ~15 | OV-20 (epic guide routes) |
| `test_output_validator.py` | ~10 | OV-14 (output validation) |
| `test_stats.py` | ~8 | N/A (internal stats) |

#### `modules/ai/services/tests/` — AI service layer

| File | Tests | Frontend features covered |
|---|---|---|
| `test_epic_guide.py` | ~15 | OV-20 (epic guide service) |
| `test_contract_parser.py` | ~12 | N/A (internal parsing) |
| `test_lint_gate.py` | ~8 | N/A (quality gate) |
| `test_service_helpers.py` | ~10 | OV-14 (service helpers) |
| `test_task_gen_integration.py` | ~15 | OV-20 (task gen integration) |

#### `modules/ai/tests/` and `modules/ai/workflows/`

| File | Tests | Frontend features covered |
|---|---|---|
| `test_job_store.py` | ~10 | OV-14, OV-20 (background job state) |
| `test_bootstrap_workflow.py` | ~20 | OV-14 (workflow execution) |
| `test_bootstrap_workflows.py` | ~15 | OV-14 |
| `test_bootstrap_models.py` | ~8 | OV-14 (response shape) |

#### `modules/auth/tests/` — Auth backend

| File | Tests | Frontend features covered |
|---|---|---|
| `test_register.py` | ~15 | SA-02 (backend), SA-14 (rate limit backend) |
| `test_refresh.py` | ~12 | SA-04 (token refresh backend) |
| `test_rate_limit.py` | ~10 | SA-14 (IP-based rate limiting) |
| `test_user_model.py` | ~8 | SA-03, SA-04 (user model) |

#### `modules/billing/tests/` — Billing backend

| File | Tests | Frontend features covered |
|---|---|---|
| `test_routes.py` | ~25 | SA-07 (billing status), SA-12 (upgrade page backend), SA-21 (checkout + verify) |
| `test_decorators.py` | ~15 | SA-19 (usage header emission), SA-08 (429 trigger) |
| `test_models.py` | ~10 | SA-20 (lapsed plan model) |
| `test_service_handlers.py` | ~20 | SA-20 (webhook handlers), SA-21 (session verification) |

#### `modules/data/` — Project data layer

| File | Tests | Frontend features covered |
|---|---|---|
| `test_routes.py` | ~30 | OV-12 (context routes), OV-13 (create), OV-14 (file save), OV-15 (get project) |
| `test_project_ownership.py` | ~12 | SA-06, SA-18 (403 enforcement) |
| `test_repository.py` | ~20 | OV-14 (file storage) |
| `test_project_model.py` | ~8 | OV-08, OV-28 (project data model) |
| `test_pygit2_isolation.py` | ~10 | N/A (git storage isolation) |
| `test_service.py` | ~15 | OV-12, OV-13, OV-14 (data service) |
| `test_generators.py` + `test_generators_snapshots.py` | ~30 | N/A (template generation) |

#### `modules/usage/tests/` — Usage tracking

| File | Tests | Frontend features covered |
|---|---|---|
| `test_decorators.py` | ~20 | SA-08 (429 trigger), SA-19 (X-Usage headers) |
| `test_service.py` | ~15 | SA-09 (usage remaining state backend) |

#### `modules/runtime/` — Chain adapter and workflows (infrastructure)

| File | Tests | Frontend features covered |
|---|---|---|
| `test_adapter.py` | ~25 | N/A (chain boundary) |
| `test_context_loader.py` | ~10 | N/A |
| `test_file_parser.py` | ~8 | N/A |
| `test_structural.py` | ~2 | N/A (import enforcement) |
| `test_cli.py` | ~15 | N/A (provider) |
| `test_claude_tokens.py` | ~8 | N/A (provider) |
| `test_abstract_step.py` | ~10 | N/A (workflow infra) |
| `test_ai_call.py` | ~15 | N/A |
| `test_compute.py` | ~10 | N/A |
| `test_execution.py` | ~20 | N/A |
| `test_registry.py` | ~10 | N/A |
| `test_repository.py` | ~12 | N/A |
| `test_runtime.py` | ~20 | N/A |
| `test_streaming.py` | ~15 | N/A |
| `test_workflow.py` | ~20 | N/A |

#### `modules/observability/tests/` — Health and logging (infrastructure)

| File | Tests | Frontend features covered |
|---|---|---|
| `test_errors.py` | ~10 | N/A |
| `test_health.py` | ~8 | SA-16 (security canary) |
| `test_logging.py` | ~8 | N/A |
| `test_sentry.py` | ~5 | N/A |

#### `modules/quality/tests/` — Output quality gates (infrastructure)

| File | Tests | Frontend features covered |
|---|---|---|
| `test_coherence.py` | ~10 | N/A |
| `test_lint.py` | ~15 | N/A |
| `test_truncation.py` | ~10 | N/A |
| `test_lint_gate.py` | ~8 | N/A |

#### `tests/integration/` — Contract matrix (integration)

| File | Tests | Frontend features covered |
|---|---|---|
| `test_contract_matrix.py` | ~10 | OV-21, OV-22 (CORS, error envelope shape for all AI routes) |

### 8.5 Reconciliation punch list

#### Keep (no action needed)

All 146 frontend unit tests are aligned — retain as-is.

Backend tests in `modules/auth`, `modules/billing`, `modules/data/projects`,
`modules/ai/routes`, `modules/usage` all directly exercise backend-side behavior
of frontend features (SA-* and OV-14/20/21). Retain all.

#### Update (test exists, scope needs extending)

| Spec | File | What to add |
|---|---|---|
| OV-01 | `app.component.spec.ts` | Add a test asserting `.page` is present when `isLoggedIn=true` and `isFullPageRoute=false`; absent when `isLoggedIn=false` |
| OV-08 | `section-taxonomy.service.spec.ts` (exists) + component spec (missing) | Component spec: test `projectsBySection` computed groups Active before Braindumps |
| OV-10 | `app.component.spec.ts` | Add tests for `updateBanner` signal on new project count; `lastSyncAt` updates after successful poll |
| OV-12 | New component test | `openContext()` sets `contextContent` and `contextTitle` signals; panel opens |
| OV-14 | New component test | `_runBootstrap()` saves partial files as poll progresses; `specGenStep` signal transitions |
| OV-20 | New component test | `generateEpicGuide()` sets `specGenLoading`; guide file appears in sidebar on completion |
| SA-06 | `projects.service.spec.ts` | Add test: 403 response converts to `AccessDeniedError` instance |
| SA-20 | `subscription.service.spec.ts` (covered) + `upgrade.component.spec.ts` (missing) | Component test: lapsed state renders "Update Payment Method" CTA not "Upgrade" CTA |
| SA-21 | `subscription.service.spec.ts` (covered) + `upgrade.component.spec.ts` (missing) | Component test: `handleVerifySession()` calls `verifySession` then `refresh`; sets `verified=true` on pro |

#### Retire (no spec row, implementation detail only)

No frontend tests are recommended for retirement — all 146 map to spec rows.

Backend: `test_pygit2_isolation.py` and `test_generators_snapshots.py` test
implementation details of the git storage layer and template snapshot format
respectively. These have no corresponding frontend feature spec. They are
valuable regression guards for the infrastructure layer but should not be
counted toward feature coverage. Retain but document as infrastructure-only.

### 8.6 New tests needed for full Phase 3 coverage

The following `*.spec.ts` files do not yet exist and represent the complete
Phase 3 authoring backlog:

| Missing spec file | Features covered | Priority |
|---|---|---|
| `app.component.auth-gate.spec.ts` | OV-01 (full state matrix) | High |
| `app.component.status-bar.spec.ts` | OV-05, OV-17 (four state machine) | High |
| `app.component.search.spec.ts` | OV-07 (filter signal, match count) | Medium |
| `app.component.create-modal.spec.ts` | OV-13 (modal open/close/submit) | High |
| `app.component.pipeline.spec.ts` | OV-14, OV-19, OV-27 (full orchestration) | High |
| `app.component.reader.spec.ts` | OV-15, OV-16, OV-23, OV-24, OV-25 (reader + toolbar) | Medium |
| `app.component.dark-mode.spec.ts` | OV-11 (localStorage toggle) | Low |
| `app.component.brainstorm-followup.spec.ts` | OV-26 (follow-up input) | Medium |
| `app.component.update-banner.spec.ts` | OV-06 (5 s dismiss) | Low |
| `login.component.spec.ts` | SA-01 (form + error states) | High |
| `signup.component.spec.ts` | SA-02 (validation + 409/429 errors) | High |
| `auth.interceptor.spec.ts` | SA-05 (bearer header, 401 handling) | High |
| `billing.interceptor.spec.ts` | SA-08 (X-Usage-Remaining, 429 navigation) | High |
| `usage.state.spec.ts` | SA-09 (signal write from interceptor) | Medium |
| `usage-meter.component.spec.ts` | SA-10 (isVisible, isWarning computed) | Medium |
| `upgrade.component.spec.ts` | SA-12 (three plan states, verify flow) | High |

Total: 16 new spec files, covering 28 previously untested or partial features.
