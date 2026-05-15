# 🎯 Epic: Test Phase 2: E2E — Overview Page

## Business Value

spec-doc is a documentation-first development tool where the overview page is the single entry point for every user session. It displays every project across four lifecycle sections, handles search and filtering, shows real-time generation status, and gates access behind authentication. A bug in this surface — a broken tab filter, a stale status bar, a login redirect that doesn't fire — is immediately visible and immediately blocks the user. Today there are zero automated checks on any of this behavior. The 13 feature specs (OV-01 through OV-13) describe what the page should do, but nothing verifies that it actually does it after a code change.

Beyond the overview page itself, this epic establishes the E2E foundation — step definition library, page object patterns, seed data strategy, and Gherkin conventions — that every future test run inherits. Run 2 (Project Detail) and Run 3 (SaaS) will add scenarios on top of whatever patterns ship here. Getting those patterns wrong doesn't just cost rework on overview tests; it multiplies into every domain that follows. The investment is front-loaded by design: build the scaffold once, reuse it across three feature sets totaling 40+ specs.

For a solo founder shipping across multiple projects, automated E2E coverage on the primary navigation surface replaces manual smoke-testing before every deploy. Each passing run is 30 scenarios that don't need a human clicking through tabs, checking status bars, and verifying auth redirects — time reclaimed directly into feature work on spec-doc and other active projects.

## Scope

### What This Epic Covers

- **Gherkin scenario derivation (OV-01 – OV-13)** — translate State Matrix rows and Edge Cases from the frozen feature specs into ~30 tagged scenarios across 9 `.feature` files, grouped by functional area (auth, masthead, navigation, status bar, search, grid, polling, create, dark mode)
- **Step definition library for overview** — new semantic steps (logged-in state, section seeding, tab assertions, status bar checks, search validation, card counting) that complement the existing `common_steps.py` without refactoring it
- **Overview page object** — `overview_page.py` encapsulating all overview-specific selectors and interactions, extending the existing `AppPage` base
- **Test data seeding strategy** — an 8-project matrix across 4 sections (Active, Ready to Build, Specced, Braindumps) provisioned via API in Given steps under `CHAIN_PROVIDER=mock`
- **Green run of all overview scenarios** — every new scenario passing against the existing session-scoped Flask (port 5001) + Angular dev (port 4201) infrastructure

### What This Epic Does NOT Cover

- ❌ **OV-14 – OV-17 (pure-function services)** — unit test territory; no user-visible behavior to drive through a browser
- ❌ **Animation timing assertions (OV-04 pulse, OV-06 auto-dismiss)** — flake magnets in CI; only re-scope if a timing bug ships to production
- ❌ **Refactoring existing step library** — selector-style steps and new semantic steps coexist; cleanup deferred to Run 3 when the library is large enough to justify it
- ❌ **Run 2 (Project Detail) and Run 3 (SaaS)** — future runs that consume the patterns built here but define no feature files, steps, or page objects now
- ❌ **CSS-only assertions without user interaction** — brittle and low signal; not E2E-testable
- ❌ **New E2E infrastructure** — reuse existing `conftest.py`, `common_steps.py`, and `app_page.py` as-is; no rebuilds

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Derive Gherkin scenarios from frozen feature specs** | Feature specs OV-01–OV-13 frozen; existing 5 `.feature` files passing green | — | 1 day | High |
| 2 | **Build overview page object and step definitions** | Task 1 (scenario list determines required steps and selectors) | — | 2 days | High |
| 3 | **Implement seed data provisioning for the 8-project matrix** | Task 2 (Given steps call seed helpers); `POST /api/projects` endpoint available | Task 2 ‖ partial | 1 day | High |
| 4 | **Wire scenarios end-to-end and achieve green run** | Tasks 1–3 complete | — | 1.5 days | High |
| 5 | **Document conventions and patterns for Run 2 inheritance** | Task 4 (patterns validated by green run) | — | 0.5 day | Low |

## Success Criteria

- ✅ 9 `.feature` files committed under `e2e/features/overview-*.feature` covering OV-01 through OV-13
- ✅ ~30 scenarios passing green in a single `pytest` run against `CHAIN_PROVIDER=mock`
- ✅ Zero Playwright calls in step definition files — all browser interaction routed through page objects
- ✅ Existing 5 `.feature` files remain green and unmodified
- ✅ Every scenario tagged with its source spec ID (`@OV-xx`) and domain tag (`@overview`)
- ✅ Seed data provisions 8 projects across 4 sections without real AI calls
- ✅ Gherkin conventions (semantic Given/When/Then, no selector language in scenario text) followed consistently across all new files

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — E2E scaffold design, page object patterns, and seed data strategy
- [Timeline](./timeline.md) — Task status and milestone tracking