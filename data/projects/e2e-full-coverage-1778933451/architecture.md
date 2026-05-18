Here is the complete Solution Architecture document:

---

# 🏗️ Solution Architecture: E2E Full Coverage — PD + SA (Runs 2-3)

## Architecture Overview

The E2E suite expansion from 43 scenarios (Run 1) to approximately 103 scenarios requires a page object architecture that scales without becoming a maintenance liability. The key insight is that Project Detail and SaaS test distinct application domains — one exercises a deeply nested UI state (project open, spec file selected, AI operation running) while the other exercises lateral flows (auth boundaries, billing gates, multi-user isolation). These domains share login preconditions but nothing else structurally, so the page object layer must compose horizontally rather than inherit vertically.

Run 1 established the pattern: Gherkin feature files describe product workflows, pytest-bdd wires them to Playwright interactions, page objects own all selectors, and API-based setup skips irrelevant click-through. Runs 2 and 3 extend this pattern without modifying it. The challenge is not inventing new infrastructure — it is managing the three new concerns that Run 1 did not face: deeply nested UI preconditions (a project must be open with spec files loaded before any PD scenario begins), multi-user isolation (SA-06 requires two authenticated sessions in the same test), and plan-state injection (billing scenarios require a user to be in a specific subscription state before the browser step starts).

The architecture addresses all three through API-first setup. No scenario navigates through UI flows to reach its precondition state. Every Given step calls Flask endpoints to seed the exact database and file state required, then hands the browser a fully-prepared context. This keeps scenarios focused on the assertion-relevant behavior and prevents cascading failures when an upstream UI change breaks an unrelated precondition flow.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | Plan-state injection goes through a dedicated test-only Flask route, not direct DB writes from the test harness. The route is the adapter between test setup and subscription state. |
| P4 — No Speculative Abstractions | No shared base page class. `detail_page.py` and `saas_page.py` are independent modules that import a shared selectors dictionary if they happen to need overlapping selectors. No class hierarchy. |
| P7 — File Size & Structure | Each page object stays under 200 lines. Each step file stays under 200 lines. Feature files split by behavioral domain, not by feature count — a file with 4 scenarios is fine. |
| Composition over Inheritance | Page objects compose Playwright page handles and a shared selectors module. No `BasePage` class. No `super().__init__()`. A page object is a plain class that receives a Playwright `Page` in its constructor. |
| API-first Setup | Every Given step that establishes precondition state does so via HTTP calls to Flask, never by clicking through the UI. UI navigation is reserved for When/Then steps only. |
| Selector Contract | All E2E selectors use `[data-test]` attributes exclusively. Selectors are retrofitted to Angular templates as feature files demand them — never speculatively, never inline in step definitions. |

## Component Design

### Shared Selectors Module

**Purpose**: Single source of truth for `[data-test]` attribute strings across all page objects.

A flat Python module (`e2e/pages/selectors.py`) exports named string constants grouped by component domain. Page objects import the constants they need. When a selector changes in the Angular template, one constant update propagates to every page object and step that references it. This eliminates the failure mode where two page objects reference the same element with slightly different selector strings that drift apart.

The module is not a class and carries no behavior — it is a namespace of string constants organized by Angular component boundary. Constants follow the naming pattern `COMPONENT_ELEMENT` (e.g., `SIDEBAR_FILE_NAV`, `READER_MARKDOWN_BODY`, `BILLING_USAGE_METER`).

### Detail Page Object (`e2e/pages/detail_page.py`)

**Purpose**: Encapsulates all Playwright interactions for the Project Detail domain (PD-01 through PD-16).

Composed of focused method groups: sidebar navigation (click file, check dot states, verify ordering), reader panel (verify markdown render, check XSS sanitization, confirm panel open state), spec-gen controls (trigger generation, poll status, verify completion), and AI operations (toggle chips, submit operations, verify result panel). Each method group corresponds to one feature file's worth of scenarios.

Does not extend `overview_page.py`. Instead, scenarios that need a project open import both `overview_page` (to navigate to the project) and `detail_page` (to interact with the expanded detail view). This is composition through imports, not inheritance through class hierarchy.

### SaaS Page Object (`e2e/pages/saas_page.py`)

**Purpose**: Encapsulates auth forms, billing UI, and upgrade page interactions for SA-01 through SA-21.

Covers four UI surfaces: login form (email/password inputs, submit, error display), signup form (same structure, different route), upgrade page (plan cards, checkout trigger, manage link), and billing indicators (usage meter, upgrade button in masthead, 429 redirect handling). Each surface maps to one feature file.

Multi-user scenarios use two instances of this page object — one per browser context. The page object itself is stateless; it does not store which user is logged in. The test fixture manages browser context separation.

### Detail Preconditions (`e2e/steps/detail_preconditions.py`)

**Purpose**: Given-step implementations that establish a project-open-with-specs state via API calls.

The fundamental precondition for all PD scenarios is "a project exists with a full spec set." This step calls `POST /api/projects` to create the project, then calls `PUT /api/projects/{id}/files/{filename}` for each spec file (braindump, analysis, epic, architecture, timeline, implementation-guide) using fixture content from `e2e/fixtures/`. The browser then navigates to the project — the detail view opens with all files already present.

This API-first approach means PD scenarios never depend on the spec-gen pipeline working correctly. If the pipeline breaks, PD-01/PD-06/PD-07 scenarios (which test the pipeline itself) fail, but PD-02/PD-03/PD-15/PD-16 scenarios (which test the reader and sidebar) continue passing because their precondition state was set via direct API writes.

### SaaS Preconditions (`e2e/steps/saas_preconditions.py`)

**Purpose**: Multi-user setup, JWT generation, and plan-state injection for billing scenarios.

Three precondition capabilities: create a second user (call `POST /api/auth/register` with unique credentials and store the returned JWT), inject plan state (call the test-only plan-state endpoint), and establish browser auth context (inject the JWT into browser storage so subsequent page loads are authenticated).

### Plan-State Injection Route

**Purpose**: Allow E2E tests to set a user's subscription plan to any state (free, pro, lapsed) without requiring Stripe webhooks or actual payment flows.

This is a test-only Flask route (`POST /api/test/set-plan`) that accepts a user identifier and a target plan state, then writes directly to the Subscription table. The route is guarded by an environment variable (`E2E_TEST_MODE=1`) and returns 404 in production. This follows the adapter boundary principle — the test harness never imports SQLAlchemy models or writes to the database directly. It calls an HTTP endpoint, which owns the write.

The alternative — mocking Stripe webhooks to trigger state transitions — would couple billing scenarios to webhook parsing logic. A billing scenario that tests "usage meter shows remaining count for free user" should not fail because the webhook parser changed. Direct state injection isolates the UI assertion from the billing implementation.

### Multi-User Browser Context

**Purpose**: Enable SA-06 (project isolation) scenarios where two users interact with the same application instance.

Playwright's browser context API provides isolated cookie/storage jars within a single browser instance. Each user gets their own context — User A's JWT lives in context A, User B's JWT lives in context B. The test creates both contexts in the Given step, authenticates each via their respective JWTs, then switches between contexts in When steps.

This avoids the overhead of launching two full browser instances. It also avoids the race conditions of trying to log in and out within a single context during a scenario. Each context is a clean, isolated session.

### Seed Data Fixtures (`e2e/fixtures/`)

**Purpose**: Static markdown content for spec files used in project seeding.

A directory of minimal but structurally valid spec files: `braindump.md`, `analysis.md`, `epic.md`, `architecture.md`, `timeline.md`, `implementation-guide.md`. Each file is short (under 50 lines) but contains the structural markers that the reader panel and sidebar expect — headings, lists, cross-references. The XSS sanitization scenario uses a dedicated fixture with embedded script tags.

Fixtures are static files, not generated. They change only when the spec format itself changes. This makes seed data deterministic — no flaky tests from randomized content.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Test Runner | pytest with pytest-bdd | Already established in Run 1; Gherkin feature files map directly to product requirements; pytest-bdd integrates with existing pytest fixtures and markers |
| Browser Automation | Playwright (Python) | Multi-context support for multi-user scenarios; auto-wait eliminates manual sleep; trace capture for debugging failures; headless by default for Docker |
| Selector Strategy | `[data-test]` attributes | Resilient to CSS and structural changes; explicit contract between Angular templates and E2E tests; retrofitted incrementally per feature file |
| Test Data | API-seeded via Flask endpoints | No direct DB access from test harness; respects adapter boundary; same endpoints work locally and in Docker |
| Plan-State Control | Test-only Flask route behind env guard | Decouples billing UI tests from Stripe integration; fast setup; no webhook simulation required for plan states |
| Skip Mechanism | pytest-bdd tags + `_SKIP_MOCK` convention | Clean separation between Docker-passable and mock-dependent scenarios; tagged scenarios produce no failure noise when skipped |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Composition over inheritance for page objects | Run 1's `overview_page.py` is self-contained; adding a base class now would require refactoring working code for no behavioral gain. Composition via imports means each page object can evolve independently. | Page objects may duplicate 2-3 helper methods (e.g., `wait_for_navigation`). Acceptable — three duplicated lines are better than a premature abstraction. |
| Test-only Flask route for plan injection rather than direct DB writes | Keeps the E2E harness ignorant of database schema. If the Subscription model changes columns, only the Flask route updates — not every billing test. Follows P1 adapter boundary. | Adds one route to the Flask app that exists only for testing. Guarded by `E2E_TEST_MODE` env var; returns 404 without it. |
| Two separate browser contexts for multi-user rather than login/logout cycling | Contexts are isolated by Playwright's design. No risk of leaked cookies or storage between users. Faster than full login/logout UI flows. | Slightly more complex fixture setup — must create and manage two contexts. Worth it for isolation guarantee. |
| API-first precondition setup rather than UI navigation | A Given step that clicks through 4 screens to reach the test state introduces 4 points of failure unrelated to the scenario's purpose. API setup is fast, deterministic, and decoupled from UI changes. | Tests do not exercise the navigation path they skip. Acceptable — navigation is covered by its own dedicated scenarios (PD-02, SA-01, SA-02). |
| Separate step files per domain rather than one monolithic steps file | `detail_steps.py` and `saas_steps.py` stay under 200 lines each. Step definitions are scoped to their domain — no accidental coupling. A developer working on billing tests never scrolls past sidebar assertions. | Step reuse across domains requires explicit imports from precondition files. No implicit sharing. |
| Static seed fixtures rather than generated content | Deterministic tests. No flakiness from randomized markdown. Fixtures only change when the spec format changes — not on every test run. | Fixtures may drift from real spec content over time. Acceptable — E2E tests verify structural rendering, not content accuracy. |
| One feature file per behavioral cluster rather than one per feature ID | `detail-reader.feature` covers PD-02, PD-15, PD-16 because they all test the reader panel. Grouping by behavior means a reader regression shows up as one failed file with a coherent name, not three scattered failures. | Traceability requires scenario-level tags (e.g., `@PD-02`) rather than file-level mapping. The traceability validation in Task 5 verifies tag coverage. |
| Skip-tagging mock-dependent scenarios rather than conditionally running them | A skipped scenario produces a clean "skipped" status in pytest output. A conditionally-run scenario that encounters missing infrastructure produces cryptic errors. Skip-tagging is explicit documentation of what needs mock support. | Skipped scenarios are invisible in green-path CI. Acceptable — the traceability check in Task 5 verifies they exist and are tagged correctly. |

## Integration Points

### Flask API Surface Used by E2E

The E2E harness interacts with Flask through five endpoint groups: auth (`/api/auth/register`, `/api/auth/login`) for user creation and JWT acquisition, projects (`/api/projects`, `/api/projects/{id}/files/{filename}`) for seed data injection, billing status (`/api/billing/status`) for assertion verification, the test-only plan-state endpoint (`/api/test/set-plan`) for subscription manipulation, and the billing checkout (`/api/billing/create-checkout-session`) for redirect verification.

No other Flask endpoints are called from Given steps. When and Then steps interact exclusively through the browser — Playwright drives the Angular app, which calls Flask through its normal `HttpClient` service layer.

### Angular Template Contract

Each feature file implies a set of `[data-test]` attributes that must exist in the Angular templates. The implementation guide for each task will enumerate the exact attributes needed. The architectural rule is: attributes are added to templates when the feature file that needs them is written, not before and not after. This prevents speculative attribute pollution and ensures every `[data-test]` attribute has exactly one consumer.

### Docker Compose Compatibility

All Docker-pass scenarios must work against the existing `docker-compose.yml` configuration with `CHAIN_PROVIDER=mock`. The plan-state injection route requires `E2E_TEST_MODE=1` in the Docker Compose environment for the Flask service. No other infrastructure changes are needed — the existing single-worker gunicorn with gthread supports concurrent test requests and the in-process state dict required by background job polling.

## Skip Classification Strategy

Scenarios divide into two categories based on a single criterion: does the scenario require AI-generated output to exist in the response?

Docker-pass scenarios test UI structure, navigation, rendering, and state that can be established through API-seeded data. They never trigger the spec-gen pipeline or AI text operations — their preconditions inject results directly via file writes.

Mock-dependent scenarios (`_SKIP_MOCK` tagged) test workflows where the AI response content affects the UI behavior — diff views, undo/redo stacks, result toolbars, brainstorm follow-ups. These scenarios require a mock provider that returns deterministic AI-shaped responses. They are authored now (documenting the expected behavior precisely) and activated when the mock infrastructure epic delivers `CHAIN_PROVIDER=mock` with scenario-specific response fixtures.

The boundary is not "does this feature involve AI" but "does this scenario's assertion depend on AI output content." PD-06 (Generate Specs button) has a Docker-pass scenario (button appears, click triggers 202 response) and a mock-dependent scenario (pipeline completes, files appear in sidebar).

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design: coverage gaps, regression blind spots, multi-user test complexity
- [Epic](./epic.md) — Scope, task breakdown, success criteria, and effort estimates
- [Timeline](./timeline.md) — Execution sequencing and dependency tracking