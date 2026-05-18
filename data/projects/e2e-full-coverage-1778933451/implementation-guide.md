# Implementation Guide: E2E Full Coverage — PD + SA (Runs 2-3)

## Overview
This epic delivers full E2E test coverage for the Project Detail (PD-01 through PD-16) and SaaS (SA-01 through SA-13, SA-20, SA-21) domains, building on the 43 Overview scenarios completed in Run 1. Work sequences in two parallel tracks: Tasks 1 and 2 cover Project Detail (Docker-passable gate scenarios first, then mock-dependent AI and pipeline scenarios), while Tasks 3 and 4 cover SaaS (auth and isolation first, then billing and upgrade flows). Task 5 is a final coverage audit that depends on both tracks completing, wiring the full suite into CI as a deploy gate.

## Shared Pre-flight
- Confirm Run 1 infrastructure is intact: e2e/conftest.py session fixtures, e2e/pages/overview_page.py page object, e2e/steps/overview_preconditions.py login/logout steps, and e2e/helpers/seed_projects.py seeding helpers all import without error
- Verify pytest-playwright and pytest-bdd are installed in the dev environment per requirements-dev.txt
- Start the Docker dev server and confirm both Flask (port 8095) and Angular (port 4201) health endpoints respond
- Review e2e/docs/conventions.md to confirm tagging rules, step style, and naming conventions before writing any new files
- Review e2e/pages/overview_page.py to internalize the page object class structure, constructor pattern, and data-test selector convention that all new page objects must follow
- Confirm the Angular detail, auth, and billing component templates are accessible for adding data-test attributes
- Verify pytest --collect-only -m e2e shows the existing 43 Overview scenarios as a baseline
- Decide the plan state injection mechanism (direct DB insert via the test session) before starting Task 3 or Task 4

---

## Task 1: PD Gate Scenarios (PD-02, PD-03, PD-04, PD-15, PD-16)  [Effort: 2 days]

### What
Creates the Project Detail page object, precondition steps, and the Docker-passable scenarios that must pass before any mock-dependent PD work begins. These cover the reader panel, sidebar navigation, status row, file ordering, and XSS sanitization — the structural foundation all other PD features depend on.

### Files
- **Create**: e2e/pages/detail_page.py — Page object with data-test selectors for the reader panel, sidebar file list, status row, and markdown content area
- **Create**: e2e/steps/detail_preconditions.py — Given steps for seeding a project with a braindump and full spec file set
- **Create**: e2e/steps/detail_steps.py — When/Then steps for sidebar clicks, reader content checks, file ordering, and XSS assertions
- **Create**: e2e/features/detail-reader.feature — Gherkin scenarios for PD-02, PD-15, PD-16
- **Create**: e2e/features/detail-sidebar.feature — Gherkin scenarios for PD-03, PD-04
- **Create**: e2e/test_detail.py — pytest-bdd scenarios() registration for all PD feature files
- **Modify**: Angular detail component templates — Add data-test attributes for panel container, sidebar items, status row, and markdown content area

### Steps
1. Create detail_page.py following the same class structure as overview_page.py. Define an __init__ that accepts a Playwright page, then add methods for opening the reader panel, clicking sidebar file entries, reading the file list in display order, inspecting rendered markdown content, and checking the status row text. Use data-test attribute selectors exclusively.
2. Create detail_preconditions.py with Given steps that seed a project containing a braindump and a complete spec file set (analysis, epic, architecture, timeline, implementation guide) using the POST /api/projects endpoint and file upload helpers from seed_projects.py. Include a Given step for navigating to the detail view of the seeded project.
3. Write detail-reader.feature with scenarios tagged @PD-02, @PD-15, and @PD-16. The PD-02 scenario verifies the expanded reader panel opens when a project is selected. The PD-15 scenario checks that files appear in canonical order: braindump, analysis, epic, architecture, timeline, implementation guide. The PD-16 scenario confirms markdown renders with formatting and that embedded script tags are stripped.
4. Write detail-sidebar.feature with scenarios tagged @PD-03 and @PD-04. The PD-03 scenario verifies that clicking a filename in the sidebar loads that file in the reader panel. The PD-04 scenario checks the sidebar status row displays the current connection state.
5. Implement detail_steps.py with When/Then step definitions that call detail_page.py methods. No step definition may contain a raw selector string — all element access goes through the page object.
6. Create test_detail.py and register both detail-reader.feature and detail-sidebar.feature using pytest-bdd's scenarios() function.
7. Add data-test attributes to the Angular detail component templates for every element the page object needs: reader panel container, sidebar file list items, individual file entries, status row element, and markdown content wrapper.

### Verify
- All scenarios tagged @PD-02, @PD-03, @PD-04, @PD-15, and @PD-16 pass against the Docker dev server with zero failures
- detail_page.py is the sole location of selectors — grep detail_steps.py and detail_preconditions.py for data-test and confirm zero matches
- pytest --collect-only -k detail shows both feature files registered and approximately 10 scenarios collected
- ng build --configuration production passes with no template errors from added data-test attributes

---

## Task 2: PD Mock Scenarios (PD-01, PD-05 through PD-14)  [Effort: 2 days]

### What
Adds the mock-dependent Project Detail scenarios covering the spec-generation pipeline, AI text operations, result panels, toolbar actions, undo/redo, and brainstorm flows. Every scenario is tagged @SKIP_MOCK and will skip cleanly when run against Docker without mock services.

### Files
- **Create**: e2e/features/detail-specgen.feature — Scenarios for PD-01, PD-06, PD-07 covering the spec-gen pipeline and generate buttons
- **Create**: e2e/features/detail-ai-ops.feature — Scenarios for PD-08, PD-09 covering AI text operation chips and style presets
- **Create**: e2e/features/detail-results.feature — Scenarios for PD-10, PD-11, PD-12 covering the result panel, toolbar, and undo/redo
- **Create**: e2e/features/detail-brainstorm.feature — Scenarios for PD-13, PD-14 covering brainstorm follow-up and spec generation from brainstorm
- **Modify**: e2e/pages/detail_page.py — Add methods for spec-gen buttons, AI chips, result panel diff view, Apply/Copy/Dismiss toolbar, undo/redo triggers, brainstorm input, and dot indicators
- **Modify**: e2e/steps/detail_preconditions.py — Add Given steps for mock-dependent states such as pipeline in-progress, AI result available, and undo stack populated
- **Modify**: e2e/steps/detail_steps.py — Add When/Then steps for pipeline triggers, chip toggles, toolbar actions, and brainstorm interactions
- **Modify**: e2e/features/detail-sidebar.feature — Add a PD-05 scenario for per-file dot tracking
- **Modify**: e2e/test_detail.py — Register the four new feature files
- **Modify**: Angular detail component templates — Add data-test attributes for spec-gen buttons, AI chips, result panel, toolbar buttons, brainstorm input, and dot indicators

### Steps
1. Extend detail_page.py with methods for clicking the Generate Specs button, clicking the Generate Guide button, toggling AI operation chips, selecting style preset chips, reading the result panel diff view content, clicking Apply/Copy/Dismiss toolbar buttons, triggering undo and redo actions, entering text in the brainstorm follow-up input, and checking per-file dot indicator states in the sidebar.
2. Write detail-specgen.feature with scenarios tagged @PD-01 @SKIP_MOCK, @PD-06 @SKIP_MOCK, and @PD-07 @SKIP_MOCK. PD-01 covers the full spec-gen pipeline lifecycle: start, poll, and complete with incremental file saves. PD-06 tests the Generate Specs button trigger and loading state. PD-07 tests the Generate Guide button trigger.
3. Add a PD-05 scenario tagged @PD-05 @SKIP_MOCK to detail-sidebar.feature for per-file dot tracking that shows generation status indicators next to each file in the sidebar.
4. Write detail-ai-ops.feature with scenarios tagged @PD-08 @SKIP_MOCK and @PD-09 @SKIP_MOCK. PD-08 tests that AI text operation chips are visible and toggleable when a spec file is open. PD-09 tests that style preset chips render and can be selected.
5. Write detail-results.feature with scenarios tagged @PD-10 @SKIP_MOCK, @PD-11 @SKIP_MOCK, and @PD-12 @SKIP_MOCK. PD-10 verifies the AI result panel displays a diff view. PD-11 tests the Apply, Copy, and Dismiss toolbar actions. PD-12 tests the undo/redo stack after applying a result.
6. Write detail-brainstorm.feature with scenarios tagged @PD-13 @SKIP_MOCK and @PD-14 @SKIP_MOCK. PD-13 tests the brainstorm follow-up input accepts text and submits. PD-14 tests that Generate Specs can be triggered from brainstorm output.
7. Extend detail_preconditions.py with Given steps for mock-dependent preconditions: a pipeline already in progress, an AI result already available in the result panel, and an undo stack with at least one applied change.
8. Extend detail_steps.py with the corresponding When/Then steps for all new scenarios, routing every element interaction through detail_page.py methods.
9. Register all four new feature files in test_detail.py using scenarios() calls.
10. Add data-test attributes to Angular templates for spec-gen buttons, AI operation chips, style preset chips, result panel container, diff view, toolbar buttons, undo/redo controls, brainstorm input field, and sidebar dot indicators.

### Verify
- All @SKIP_MOCK-tagged scenarios skip cleanly when run against Docker — zero false failures in the test output
- Every PD feature ID from PD-01 through PD-16 appears as a tag on at least one scenario across all detail feature files
- pytest --collect-only -k detail shows approximately 35 total PD scenarios
- ng build --configuration production passes with no template errors

---

## Task 3: SA Auth and Isolation (SA-01, SA-02, SA-04, SA-06, SA-13)  [Effort: 2 days]

### What
Creates the SaaS page object, multi-user precondition infrastructure, and the authentication and isolation scenarios that gate all other SaaS work. These prove login, signup, token expiry redirect, project ownership 403 enforcement, and full-page route rendering — the scenarios every billing and upgrade test depends on.

### Files
- **Create**: e2e/pages/saas_page.py — Page object with data-test selectors for login form, signup form, error messages, 403 page, and full-page route containers
- **Create**: e2e/steps/saas_preconditions.py — Given steps for multi-user setup (user A and user B), JWT generation per user, and expired-token injection
- **Create**: e2e/steps/saas_steps.py — When/Then steps for form submissions, redirect assertions, 403 UI checks, and route rendering verification
- **Create**: e2e/features/saas-auth.feature — Scenarios for SA-01, SA-02, SA-04, SA-13
- **Create**: e2e/features/saas-isolation.feature — Scenarios for SA-06
- **Create**: e2e/test_saas.py — pytest-bdd scenarios() registration for all SA feature files
- **Modify**: Angular login, signup, error, and layout component templates — Add data-test attributes for form fields, buttons, error containers, and route wrappers

### Steps
1. Create saas_page.py following the overview_page.py class pattern. Define methods for filling the login email and password fields and clicking submit, filling the signup form fields and clicking register, reading displayed error messages, checking the current URL for redirect verification, inspecting the 403 error page message and back button, and verifying that a route renders without the app shell wrapper.
2. Create saas_preconditions.py with Given steps that create user A via the API with known credentials, create user B via the API with separate credentials, generate distinct JWT tokens for each user, and provide a step that injects an expired JWT into the browser session to simulate token expiry.
3. Write saas-auth.feature with scenarios tagged @SA-01, @SA-02, @SA-04, and @SA-13. SA-01 tests that a user can log in with valid credentials and lands on the overview page. SA-02 tests the signup flow from form submission through to successful account creation. SA-04 tests that an expired JWT causes a redirect to the login page. SA-13 verifies that the /signup and /upgrade routes render as full-page layouts without the app shell.
4. Write saas-isolation.feature with scenarios tagged @SA-06. Include at least three scenarios: user B navigating to user A's project URL receives a 403 response, the 403 page displays an ownership error message, and the back button on the 403 page navigates the user away.
5. Implement saas_steps.py with When/Then steps that call saas_page.py methods for every form interaction, redirect check, and content assertion. No raw selectors in step code.
6. Create test_saas.py and register saas-auth.feature and saas-isolation.feature using pytest-bdd's scenarios() function.
7. Add data-test attributes to Angular templates for login form email input, password input, submit button, signup form fields, register button, error message container, 403 page message, 403 back button, and the full-page route layout wrapper.

### Verify
- Scenarios tagged @SA-01, @SA-02, @SA-04, and @SA-13 pass against Docker
- Scenarios tagged @SA-06 pass with two distinct users seeded in the database, confirming user B receives 403 on user A's project
- saas_page.py uses only data-test selectors — grep saas_steps.py and saas_preconditions.py for data-test confirms zero matches
- ng build --configuration production passes

---

## Task 4: SA Billing and Upgrade (SA-08 through SA-12, SA-20, SA-21)  [Effort: 2 days]

### What
Adds plan state injection infrastructure and the billing and upgrade scenarios covering the 429 rate-limit redirect, usage metering, upgrade button visibility, upgrade page states per plan, lapsed plan handling, and Stripe checkout redirect. Docker-passable scenarios use direct database plan state injection; mock-dependent scenarios are tagged @SKIP_MOCK.

### Files
- **Create**: e2e/features/saas-billing.feature — Scenarios for SA-08, SA-09, SA-10, SA-11
- **Create**: e2e/features/saas-upgrade.feature — Scenarios for SA-12, SA-20, SA-21
- **Modify**: e2e/pages/saas_page.py — Add methods for reading the usage meter, checking upgrade button visibility, inspecting upgrade page content per plan state, and verifying checkout redirect
- **Modify**: e2e/steps/saas_preconditions.py — Add Given steps for injecting plan state (free, pro, lapsed) via direct database insert and configuring a mock 429 response
- **Modify**: e2e/steps/saas_steps.py — Add When/Then steps for billing UI assertions, upgrade page state checks, and checkout redirect verification
- **Modify**: e2e/test_saas.py — Register the two new feature files
- **Modify**: Angular masthead, usage meter, upgrade page, and billing error component templates — Add data-test attributes

### Steps
1. Extend saas_preconditions.py with Given steps that set a user's plan to "free", "pro", or "lapsed" by inserting or updating the plan field directly in the database via the test session. This is the mechanism that unblocks SA-10, SA-11, SA-12, and SA-20.
2. Add a Given step to saas_preconditions.py that configures a mock 429 response from the billing HTTP interceptor. Tag scenarios using this step with @SKIP_MOCK since the mock cannot run against plain Docker.
3. Extend saas_page.py with methods for reading the usage meter numeric value, checking whether the usage meter component is visible or hidden, checking whether the upgrade button in the masthead is visible, reading upgrade page content to distinguish free CTA from lapsed CTA from pro manage-subscription view, and verifying that clicking the checkout button navigates to the expected redirect URL.
4. Write saas-billing.feature with four scenarios. SA-08 tagged @SKIP_MOCK tests that a 429 response redirects the user to the upgrade page. SA-09 tests that the usage remaining count displays in the header. SA-10 tests that the usage meter is visible for a free-plan user and hidden for a pro-plan user. SA-11 tests that the upgrade button appears in the masthead for non-pro users.
5. Write saas-upgrade.feature with three scenarios. SA-12 tests that the upgrade page renders the correct content based on the user's current plan state. SA-20 tagged @SKIP_MOCK tests that a lapsed plan shows a different call-to-action than a free plan. SA-21 tagged @SKIP_MOCK tests that the checkout button triggers a redirect to the Stripe checkout URL.
6. Extend saas_steps.py with When/Then steps for all billing and upgrade assertions, routing through saas_page.py for every element interaction.
7. Register saas-billing.feature and saas-upgrade.feature in test_saas.py using scenarios() calls.
8. Add data-test attributes to Angular templates for the usage meter component, usage count display, upgrade button in masthead, upgrade page content sections, plan-specific CTA elements, and checkout trigger button.

### Verify
- Docker-passable scenarios (@SA-09, @SA-10, @SA-11, @SA-12) pass against Docker with plan state injected via the database
- Mock-dependent scenarios (@SA-08, @SA-20, @SA-21) skip cleanly with @SKIP_MOCK tag and produce no false failures
- Every SA feature ID from SA-01 through SA-13 plus SA-20 and SA-21 appears as a tag on at least one scenario
- ng build --configuration production passes

---

## Task 5: Coverage Audit and CI Gate Wiring  [Effort: 0.5 days]

### What
Validates that every PD and SA feature ID has at least one tagged E2E scenario, confirms pass/skip counts hit the epic's success criteria, and wires the E2E suite into CI as a required check. This task converts the test suite from a safety net into a deploy gate.

### Files
- **Modify**: e2e/docs/conventions.md — Append Run 2 and Run 3 scenario inventory tables with feature ID, scenario name, feature file, and Docker pass/skip classification
- **Modify**: CI pipeline configuration — Add the E2E suite as a required status check with tolerance for @SKIP_MOCK skips

### Steps
1. Run pytest --collect-only -m e2e and capture the full scenario list. Cross-reference every feature ID from PD-01 through PD-16 and SA-01 through SA-13 plus SA-20 and SA-21 against the collected tags. Document any feature ID that lacks a corresponding scenario and create the missing scenario before proceeding.
2. Run the full E2E suite against Docker and record pass, skip, and fail counts. Verify the Docker-passable pass count reaches at least 30 combined across PD and SA (target is 15 or more from each domain). Verify every @SKIP_MOCK scenario skips without producing a failure exit code.
3. Update e2e/docs/conventions.md with a Run 2 inventory table and a Run 3 inventory table. Each row should list the feature ID, scenario name, source feature file path, and whether it passes on Docker or skips as mock-dependent.
4. Add an E2E job to the CI pipeline configuration that runs pytest -m e2e against the Docker environment. Configure the job so that skipped tests (from @SKIP_MOCK) do not cause a non-zero exit code, but any unexpected failure does fail the build.
5. Run ng build --configuration production and the full Karma unit test suite to confirm that data-test attribute additions across Tasks 1 through 4 introduced no regressions in the frontend build or existing tests.

### Verify
- Every feature ID from PD-01 through PD-16 and SA-01 through SA-13 plus SA-20 and SA-21 has at least one tagged scenario — 48 feature IDs with zero gaps
- Combined Runs 2 and 3 scenario count is approximately 60 (approximately 35 PD plus approximately 25 SA)
- Docker-passable pass count is 30 or higher with zero unexpected failures
- CI pipeline executes the E2E job and reports correct pass/skip/fail status on a test push