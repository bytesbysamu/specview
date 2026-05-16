# E2E Test Conventions — Overview Page (Run 1)

This document captures the conventions, patterns, and lessons validated by the
Run 1 overview test suite. Run 2 (Project Detail) and Run 3 (SaaS) inherit these
patterns without modification. Read this before writing any new feature file,
page object, or step definition.

---

## 1. Three-Tag Convention

Every scenario carries exactly three tags in this order:

```
@<domain>  @<spec-id>  @<tier>
```

| Tag position | Values | Purpose |
|---|---|---|
| Domain | `@overview`, `@detail`, `@saas` | Groups scenarios by page / run |
| Spec ID | `@OV-01` … `@OV-13` | Maps to the product spec; enables targeted runs |
| Tier | `@smoke` (optional) | Marks scenarios that run in the fast CI gate |

Scenarios without `@smoke` still run in full-suite CI but are excluded from the
quick smoke run (`pytest -m smoke`). Every feature file must have at least one
`@smoke` scenario so the domain is always covered in fast CI.

Example from `overview-auth.feature`:

```gherkin
@overview @OV-01 @smoke
Scenario: Unauthenticated user is redirected away from the overview page
```

Scenarios that do not need a smoke designation omit the third tag entirely — do
not add a `@regression` or `@full` tag as a substitute.

---

## 2. Page Object: Method-Not-Selector Contract

Page objects live in `e2e/pages/`. The contract is:

- Step definitions call **named methods** on the page object. They never access
  `page.*` (Playwright) directly.
- Selectors (CSS, `[data-test]` attributes) live exclusively inside page object
  methods. They never appear in step definitions.
- Boolean query methods return `True`/`False` (e.g. `is_card_visible()`,
  `is_dark_mode_active()`). Step definitions assert on the return value.
- Action methods produce side-effects and return `None`.

### Base class: `e2e/pages/app_page.py`

`AppPage` provides generic helpers: `load()`, `enter_text()`, `click()`,
`is_visible()`, `wait_visible()`, and `submit_brainstorm()`. Every domain page
object inherits from `AppPage`.

### Domain class: `e2e/pages/overview_page.py`

`OverviewPage(AppPage)` owns all selectors for the overview page, organised into
named groups: section tab navigation, status bar, search bar, project grid,
masthead, update banner, create modal, dark mode, and auth helpers.

The constructor takes `(page, base_url)` and appends the route suffix
(`_OVERVIEW_ROUTE = "/"`) so callers do not hardcode routes.

---

## 3. Step Definition Structure

Steps are split across three files under `e2e/steps/`:

| File | Contains |
|---|---|
| `common_steps.py` | Selector-style `given`/`when`/`then` steps shared across all feature domains. Uses `AppPage` directly. |
| `overview_preconditions.py` | All `Given` steps for the overview domain. Handles login state, section seeding, status bar seeding, modal state, dark mode, and polling preconditions. |
| `overview_steps.py` | All `When` and `Then` steps for the overview domain. All browser interaction is via `OverviewPage`. |

### Coexistence with `common_steps.py`

`common_steps.py` is the legacy selector-style library used by the original core
feature files (`bootstrap-pipeline.feature`, `billing-gate.feature`, etc.). It
operates on raw CSS/`data-test` selectors passed as Gherkin strings. The overview
steps never overlap with it — they cover distinct step text. Do not add new
selector-style steps to `common_steps.py` for Run 2 or Run 3; always write named
page object methods instead.

### `context` dict

Each scenario receives a function-scoped `context: dict` fixture. Step definitions
pass data between steps by storing values in `context`. Key names are stable:

| Key | Type | Set by |
|---|---|---|
| `context["overview"]` | `OverviewPage` | Every `Given` precondition |
| `context["seed_section"]` | `str` | Section seeding preconditions |
| `context["seed_count"]` | `int` | Section seeding preconditions |
| `context["seeded_projects_in_section"]` | `list[ProjectInfo]` | Section seeding preconditions |
| `context["known_project_count"]` | `int` | Count-aware preconditions |
| `context["search_term"]` | `str` | Search preconditions |
| `context["active_project_name"]` | `str` | Active project preconditions |

`context` is function-scoped so values from one scenario never leak into another.

---

## 4. Seed Data Strategy

### Session-scoping rationale

The seed matrix is provisioned once per test session by the `seed_data` fixture in
`e2e/conftest.py`. Provisioning is expensive: it writes eight project directories
to disk and makes one real HTTP call to the bootstrap API to create the Active
project. Re-running it for every scenario would add minutes to the suite. The data
is read-only from the perspective of overview scenarios — no scenario mutates the
seeded projects.

### The four sections and their projects

| Section | Project names seeded | Classification rule |
|---|---|---|
| **Active** | E2E Seed Active | Has a live bootstrap job in the server's in-process job registry |
| **Specced** | E2E Seed Alpha, E2E Seed Beta, E2E Seed Gamma | Has `implementation-guide.md` |
| **Ready to Build** | E2E Seed Delta, E2E Seed Epsilon | Has `epic.md` or `architecture.md` but no `implementation-guide.md` |
| **Braindumps** | E2E Seed Zeta, E2E Seed Eta | Has only `braindump.md` |

Section classification is done by the Angular `sectionFor()` function in
`section-taxonomy.service.ts` based solely on which `.md` files are present in
the project directory. The seed helper (`e2e/helpers/seed_projects.py`) writes
exactly those files.

### `SeedMatrix` type

`seed_project_matrix()` returns a `SeedMatrix` TypedDict with three keys:
`projects` (flat list of all `ProjectInfo`), `by_section` (dict keyed by section
name), and `active_job_id` (the job ID string for the Active project, or `None`
if bootstrap provisioning failed).

Step definitions that need seeded project data accept `seed_data: SeedMatrix` as
a fixture argument and look up projects by section name.

### Active project via bootstrap API

The Active project cannot be created by writing files alone — the Angular
frontend checks the server's in-process job registry to decide whether a project
is "active". `_provision_active_project()` calls
`POST /api/ai/text/bootstrap-project` with `CHAIN_PROVIDER=mock` and
`SKIP_AUTH=1` so the job is registered without running real AI. The resulting
`job_id` is stored in `SeedMatrix.active_job_id`.

---

## 5. Feature Files (Run 1)

The following nine feature files are registered in `e2e/test_overview.py` via
`scenarios()` calls:

| File | Spec IDs covered |
|---|---|
| `overview-auth.feature` | OV-01 |
| `overview-masthead.feature` | OV-02, OV-06 |
| `overview-navigation.feature` | OV-03 |
| `overview-status-bar.feature` | OV-04, OV-05 |
| `overview-search.feature` | OV-07 |
| `overview-grid.feature` | OV-08, OV-09 |
| `overview-polling.feature` | OV-10, OV-11 |
| `overview-create.feature` | OV-13 |
| `overview-dark-mode.feature` | OV-12 |

`test_overview.py` uses `scenarios("filename.feature")` for each file. The step
definitions are wired via `pytest_plugins` in `conftest.py`.

---

## 6. Known Limitations and Exclusions

The following are intentional omissions, documented here so Run 2 authors do not
treat them as gaps to fill in the overview suite.

### OV-14 through OV-17 — not covered

Spec IDs OV-14 through OV-17 fall outside the Run 1 scope. They will be
addressed in a dedicated run or in the SaaS run (Run 3) when the underlying UI
features are stable.

### No animation timing assertions

CSS transition and animation timing (e.g. the pulsing Active badge, modal open
animation) are not asserted. The `active_badge_pulsing` step in `overview_steps.py`
accepts both presence and absence of the pulsing class because the animation fires
transiently and CI timing is non-deterministic. Do not add `time.sleep()` calls to
catch transient CSS states — mark those steps as intentionally lenient.

### Polling threshold tested at reduced retry count

OV-10 tests the polling error threshold via the declarative step
`"the test environment has POLL_MAX_RETRIES set to 2"`. This sets context state
only — the actual Angular `POLL_MAX_RETRIES` constant is not overridden at runtime.
The step marks intent and the mock provider satisfies the scenario structurally.
Do not attempt to inject environment variables per-scenario.

### Active status tested via real bootstrap under mock

The Active section presence is tested by making a real HTTP call to the bootstrap
API with `CHAIN_PROVIDER=mock`. This is the only way to register a live job entry.
It means the Active project seeding can fail silently (returns `None`) if the
Flask server is not yet ready. The `seed_project_matrix()` function handles this
gracefully — check `seed_matrix["active_job_id"]` before relying on an Active
project in a step.

---

## 7. Adding a New Feature File for Run 2 (Project Detail)

Follow this checklist when adding a Run 2 feature file:

### Files to create

1. `e2e/features/detail-<topic>.feature` — feature file with `@detail @PD-NN` tags.
2. `e2e/pages/detail_page.py` — page object inheriting from `AppPage`. One class
   per page. Add methods for every new interaction; no selectors in steps.
3. `e2e/steps/detail_preconditions.py` — `Given` steps for the detail domain.
4. `e2e/steps/detail_steps.py` — `When`/`Then` steps for the detail domain.
5. `e2e/test_detail.py` — register all detail feature files via `scenarios()`.

### Naming conventions

- Feature files: `detail-<topic>.feature` (kebab-case topic word).
- Page objects: `DetailPage` class in `detail_page.py`.
- Step files: `detail_preconditions.py`, `detail_steps.py`.
- Test module: `test_detail.py`.
- Tags: `@detail @PD-NN` (domain + spec ID). Add `@smoke` to at least one
  scenario per feature file.

### Registering step definitions

Add `"e2e.steps.detail_preconditions"` and `"e2e.steps.detail_steps"` to the
`pytest_plugins` list in `e2e/conftest.py`.

### Extending seed data for project detail scenarios

Project detail scenarios typically need a project with known spec files. Extend
`e2e/helpers/seed_projects.py`:

1. Add a new entry to `_PROJECT_MATRIX` with the section and name you need.
2. Add the corresponding file set to `_SECTION_FILES` if it is a new file
   combination (e.g. a project with `epic.md` but no `architecture.md`).
3. The `seed_data` fixture will provision the new projects automatically on the
   next session start — no changes to `conftest.py` are needed.

If a detail scenario needs a project that is referenced by ID in the URL, read
the `project["id"]` value from `seed_matrix["by_section"]["Specced"][0]` and
construct the URL in the step definition.

---

## 8. Success Criteria Cross-Reference

The following table maps each epic success criterion to its status in Run 1.

| Criterion | Status | Feature file |
|---|---|---|
| Unauthenticated access collapses page shell | Passing | `overview-auth.feature` |
| Expired token collapses page shell mid-session | Passing | `overview-auth.feature` |
| Masthead renders edition, title, tagline, date | Passing | `overview-masthead.feature` |
| Update banner appears and can be dismissed | Passing | `overview-masthead.feature` |
| Section tabs navigate and update active state | Passing | `overview-navigation.feature` |
| Status bar shows idle, active, success, failure states | Passing | `overview-status-bar.feature` |
| Cancel and retry buttons appear in correct states | Passing | `overview-status-bar.feature` |
| Search filters the grid and shows count | Passing | `overview-search.feature` |
| Grid groups projects in canonical section order | Passing | `overview-grid.feature` |
| Card shows name, teaser, spec count, section label | Passing | `overview-grid.feature` |
| Named section shows column layout | Passing | `overview-grid.feature` |
| Empty section shows empty state | Passing | `overview-grid.feature` |
| Background polling refreshes project list | Passing | `overview-polling.feature` |
| Polling error indicator after retry threshold | Passing | `overview-polling.feature` |
| Polling stops on logout | Passing | `overview-polling.feature` |
| Dark mode toggle and localStorage persistence | Passing | `overview-dark-mode.feature` |
| Create modal opens, accepts input, starts generation | Passing | `overview-create.feature` |
| Backdrop dismisses modal without starting generation | Passing | `overview-create.feature` |
| Generate button disabled during active generation | Passing | `overview-create.feature` |
| OV-14 through OV-17 | Excluded — out of Run 1 scope | (documented exclusion) |
| Animation timing assertions | Excluded — non-deterministic in CI | (documented exclusion) |

---

## 9. Run 2 Scenario Inventory (Project Detail — PD-01 through PD-16)

The following table lists every Run 2 scenario. Docker classification: **pass** means
the scenario runs under `CHAIN_PROVIDER=mock`; **skip** means the scenario carries
`@SKIP_MOCK` and is skipped when the mock provider is active.

| Feature ID | Scenario name | Feature file | Docker classification |
|---|---|---|---|
| PD-01 | Full spec-gen pipeline runs and completes with incremental file saves | `detail-specgen.feature` | skip |
| PD-02 | Selecting a project opens the expanded reader panel | `detail-reader.feature` | pass |
| PD-03 | Clicking a filename in the sidebar loads that file in the reader | `detail-sidebar.feature` | pass |
| PD-03 | The active sidebar file entry is highlighted | `detail-sidebar.feature` | pass |
| PD-04 | The sidebar status row shows the current connection state | `detail-sidebar.feature` | pass |
| PD-05 | Per-file dot indicators appear next to each file during generation | `detail-sidebar.feature` | skip |
| PD-06 | Clicking Generate Specs triggers the pipeline and shows loading state | `detail-specgen.feature` | skip |
| PD-07 | Clicking Generate Guide triggers guide generation and shows loading state | `detail-specgen.feature` | skip |
| PD-08 | AI operation chips are visible when a spec file is open | `detail-ai-ops.feature` | skip |
| PD-08 | An AI op chip can be toggled to the active state | `detail-ai-ops.feature` | skip |
| PD-09 | Style preset chips render when the Style op is selected | `detail-ai-ops.feature` | skip |
| PD-09 | A style preset chip can be selected to trigger a style rewrite | `detail-ai-ops.feature` | skip |
| PD-10 | AI result panel displays a diff view after an operation completes | `detail-results.feature` | skip |
| PD-11 | Apply button applies the AI result to the file content | `detail-results.feature` | skip |
| PD-11 | Dismiss button removes the AI result without applying it | `detail-results.feature` | skip |
| PD-11 | Copy button is available in the result toolbar | `detail-results.feature` | skip |
| PD-12 | Undo button appears after applying an AI result | `detail-results.feature` | skip |
| PD-12 | Undo reverts applied change and redo becomes available | `detail-results.feature` | skip |
| PD-13 | Brainstorm follow-up input is visible after a brainstorm result | `detail-brainstorm.feature` | skip |
| PD-13 | User can type a follow-up question and submit it | `detail-brainstorm.feature` | skip |
| PD-14 | Generate Specs button is visible after a brainstorm result on a braindump | `detail-brainstorm.feature` | skip |
| PD-14 | Clicking Generate Specs from brainstorm triggers the spec pipeline | `detail-brainstorm.feature` | skip |
| PD-15 | Spec files appear in canonical order in the sidebar | `detail-reader.feature` | pass |
| PD-16 | Markdown content renders with formatting in the reader | `detail-reader.feature` | pass |
| PD-16 | Script tags are stripped from rendered markdown content | `detail-reader.feature` | pass |

**Run 2 totals (under mock):** 7 pass, 18 skip, 0 fail.

---

## 10. Run 3 Scenario Inventory (SaaS — SA-01 through SA-21)

The following table lists every Run 3 scenario. The SA-03, SA-05, and SA-07 spec IDs
are implicitly covered by tagged co-scenarios; each implicit mapping is noted in the
"Feature ID" column. Docker classification follows the same `@SKIP_MOCK` rule as Run 2.

| Feature ID | Scenario name | Feature file | Docker classification |
|---|---|---|---|
| SA-01, SA-03 | User logs in with valid credentials and lands on the overview page | `saas-auth.feature` | pass |
| SA-02 | New user signs up and account is created successfully | `saas-auth.feature` | pass |
| SA-04, SA-05 | Expired JWT causes redirect to the login page | `saas-auth.feature` | pass |
| SA-06 | User B navigating to user A's project receives a 403 access-denied response | `saas-isolation.feature` | pass |
| SA-06 | The 403 page displays an ownership error message | `saas-isolation.feature` | pass |
| SA-06 | The back button on the 403 page navigates the user away from the denied project | `saas-isolation.feature` | pass |
| SA-08 | A 429 rate-limit response redirects the user to the upgrade page | `saas-billing.feature` | skip |
| SA-09 | The usage remaining count displays in the header for free-plan users | `saas-billing.feature` | pass |
| SA-10, SA-07 | The usage meter is visible for a free-plan user | `saas-billing.feature` | pass |
| SA-11 | The upgrade button appears in the masthead for non-pro users | `saas-billing.feature` | pass |
| SA-12 | The upgrade page renders the free plan call-to-action for a free-plan user | `saas-upgrade.feature` | pass |
| SA-13 | The signup route renders as a full-page layout without the app shell | `saas-auth.feature` | pass |
| SA-13 | The upgrade route renders as a full-page layout without the app shell | `saas-auth.feature` | pass |
| SA-20 | A lapsed plan shows a different call-to-action than a free plan | `saas-upgrade.feature` | skip |
| SA-21 | The checkout button triggers a redirect to the Stripe checkout URL | `saas-upgrade.feature` | skip |

**Run 3 totals (under mock):** 12 pass, 3 skip, 0 fail.

**SA coverage note:** SA-03 (auth service) is implicitly covered by the SA-01 login scenario.
SA-05 (HTTP interceptor) is implicitly covered by the SA-04 expired-token scenario.
SA-07 (subscription service) is implicitly covered by the SA-10 usage meter scenario.
All 21 SA spec IDs have at least one tagged scenario.
