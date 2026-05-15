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
