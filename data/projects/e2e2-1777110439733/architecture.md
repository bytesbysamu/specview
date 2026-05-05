# 🏗️ Solution Architecture: E2E2 — Behavioural Test Coverage for Retrofitted Components

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The E2E layer for Spec Doc sits above a full Angular + Express stack. Because the application is a JavaScript-rendered SPA with Monaco Editor, filesystem-driven project persistence, and real server-side AI operations, the only test strategy that exercises actual behaviour is one that drives a real browser against real servers. A requests-only or filesystem-only approach would bypass the Angular rendering layer entirely and produce tests that verify nothing a user would encounter.

The architectural pivot of this system is `e2e/conftest.py`. Every downstream decision — how servers start, how AI responses are controlled, how page objects reach the DOM — flows from the single fixture encoded there. Locking that contract before any feature file is written is not bureaucracy; it is the difference between five step-definition modules that share a stable foundation and five modules that each embed bespoke setup logic that compounds drift.

Page objects occupy the anti-corruption layer between test intent and DOM structure. A step definition that reads `sidebar.select_project("my-project")` survives a CSS refactor, a class rename, or an Ionic layout change. The same step definition reaching directly into the DOM does not. The selector boundary — `[data-test]` only, never class or tag — is the invariant that makes component isolation verifiable: a selector change in the editor component breaks exactly `EditorPage` methods and nothing else.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| `[data-test]` selectors only | Page object methods never reference CSS classes, element tags, or text content; structural refactors cannot silently break selectors |
| Fixture as contract | `e2e/conftest.py` is the single point encoding the server strategy; no step-definition module imports any other setup code |
| Concrete before abstract | No base page object class; each of the four classes has exactly one named consumer in this epic; extraction happens only when a second consumer surfaces |
| Deferred server wiring | The conftest fixture encodes strategy; CI orchestration is deferred to Task 3 if the real-server path was chosen in Task 1 and requires additional wiring |
| AI mocked at the boundary | Claude responses are intercepted at the Express middleware level, not in the Angular layer; CI runs without API credentials and at deterministic speed |
| Component isolation is verifiable | Each page object owns its selectors exclusively; the success criterion `selector change → exactly that PO breaks` is testable by inspection, not by convention |

---

## System Boundaries

### What This System Includes

- A recorded driver and server-strategy decision (Task 1), consumed by every subsequent task
- Four page object classes in `e2e/pages/`, one per retrofitted component, each exposing named methods backed exclusively by `[data-test]` selectors
- A single `e2e/conftest.py` fixture encoding the chosen server strategy, shared by all five step-definition modules
- Five `.feature` files covering bootstrap-happy, bootstrap-fail-fast, edit-spec, context-editor, and rewrite-operation, each with complete Gherkin scenarios
- Five pytest-bdd step-definition modules wired to page objects and the shared fixture, every scenario reaching green or carrying a documented skip with an explicit reason

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| New Angular components or `[data-test]` attribute additions | Missing selectors are pre-existing bugs; this epic adds the test layer over what already exists |
| A fifth page object for the new-project modal | No named Epic task requires it; re-scope at the Task 3 boundary if a selector gap surfaces |
| Retry, backoff, or flakiness budgets | No second consumer calibrates the shape; add if CI failure rates surface a real pattern |
| Test-reporting dashboards | No signal yet that standard pytest output is insufficient |
| Server orchestration abstraction above the fixture | The fixture does minimum: start, yield, teardown; no wrapper layer is added until a second fixture consumer exists |
| Visual regression testing | Pixel-diff correctness is a separate concern; behaviour is the only signal here |

---

## Component Design

### Driver: Playwright Python

**Purpose**: Exercises the full Angular + Express stack through a real browser, replacing manual click-through confidence with automated regression coverage.

**Consumer**: All five step-definition modules (Tasks 2 and 3).

**Key parts**:
- `playwright.sync_api.Browser` — launched headless in CI, headed locally for authoring
- `playwright.sync_api.Page` — the Playwright page object injected into each step definition via the conftest fixture

**Why Playwright over Selenium**: Playwright's auto-wait semantics match Angular's async rendering cycle. It waits for elements to be actionable before interacting, which eliminates the explicit `sleep` and polling waits that make Selenium suites brittle in SPA contexts. Single-process, no WebDriver protocol overhead, and no display server dependency in CI are the practical gains. Selenium is the correct choice only for legacy browser-compatibility requirements this project has none of.

**Why Playwright over requests-only**: Angular 19 renders in the browser. Monaco Editor initialises a full CodeMirror instance. The bootstrap flow triggers Angular component state changes. None of these are reachable by HTTP requests to the Express API alone — only a real browser executes them.

### Server Strategy: Real Express + Angular, AI Mocked at Express Middleware

**Purpose**: Preserves behavioural fidelity for filesystem-backed flows while keeping CI fast and API-credential-free.

**Consumer**: `e2e/conftest.py` (Task 2), CI pipeline (Task 3 if real-server wiring is needed).

**Key parts**:
- Express dev server (port 3100) — runs the projects API, which writes and reads project files to the local filesystem
- Angular dev server (port 4201) — serves the compiled Angular application the browser navigates to
- AI response intercept — Express middleware in the test environment returns deterministic, fixture-controlled responses for `/api/ai/text` instead of forwarding to Claude CLI or the remote API

**Why real servers**: The bootstrap-happy and bootstrap-fail-fast scenarios test actual project directory creation and markdown file persistence. A mocked Express would test the mock. A filesystem-only approach would never invoke Angular. The edit-spec scenario depends on the real auto-save debounce path — 1 second write to Express, confirmed by a subsequent load. Only a real server round-trip validates that path.

**Why mock AI at the middleware layer, not the Angular service layer**: Intercepting at Express keeps the Angular `ai.service.ts` path unaltered and tests the full call chain, including serialisation and response-shape handling. Mocking at the Angular service layer would skip HTTP encoding and response mapping — exactly the paths most likely to break when the AI response envelope changes.

**Why session-scoped, not function-scoped**: Server startup is expensive. Amortising it across the full test session means five feature files share one startup cost. Test data isolation is achieved through per-scenario project directory creation and teardown, not server restarts.

### Page Object Layer: Four Classes in `e2e/pages/`

**Purpose**: Interposes an anti-corruption layer between step-definition intent and DOM structure, so that component refactors require changes in exactly one class rather than across every step file that touches that component.

**Key parts**:
- `EditorPage` — named methods for loading content, reading current value, triggering edits; consumer: edit-spec and rewrite-operation step definitions
- `PreviewPage` — named methods for reading rendered HTML, checking sync state; consumer: edit-spec and context-editor step definitions
- `OperationBarPage` — named methods for invoking rewrite, expand, compress, clarify; consumer: rewrite-operation and context-editor step definitions
- `SidebarPage` — named methods for selecting projects, verifying project list state; consumer: bootstrap and edit-spec step definitions

**Why no base class**: Each of the four classes has exactly one task-named consumer in this epic. A shared base class that no second class currently needs introduces a shape that the first real shared-method pull will likely invalidate. The extraction is cheap when it's pulled by two real consumers; it is not cheap to unwind when the abstraction turns out to be wrong.

**Why `[data-test]` exclusively**: Class selectors break on Ionic layout updates. Text selectors break on copy changes. Tag selectors break on semantic HTML corrections. The `[data-test]` attribute is the only selector category that survives all three refactor types without touching the test layer.

### Shared Fixture: `e2e/conftest.py`

**Purpose**: Encodes the Task 1 decision once and exposes it as the single import contract for all five step-definition modules.

**Consumer**: All five step-definition modules (Task 3).

**Key parts**:
- Session-scoped server fixture — starts Express and Angular dev servers, yields a base URL, tears down after session
- Playwright `page` fixture — creates a browser page pre-navigated to the Angular app, scoped per scenario
- AI mock fixture — registers the deterministic response handler on the Express AI endpoint before the session begins

**Why one conftest, not per-feature setup**: If each feature file embeds its own server-start logic, the server-strategy decision is encoded N times. The first time someone changes the port or the mock response shape, they change it in one place or they introduce drift. A single conftest is the only structure that prevents that drift by construction.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Test runner | pytest + pytest-bdd | Matches existing backend test conventions; Gherkin scenarios are human-readable by non-developers and serve as living documentation |
| Browser driver | Playwright Python | Auto-wait semantics for Angular async rendering; headless CI without display server; modern API over WebDriver |
| Servers under test | Real Angular 19 + Express | Behavioural fidelity; filesystem-backed project flows require real server round-trips |
| AI responses in CI | Mocked at Express middleware | Deterministic outputs; no API key dependency; controls response shape independently of Claude API changes |
| Selector convention | `[data-test]` attributes | Established in architecture principles; already the standard for Ionic/Angular projects in this builder's stack |
| Gherkin framework | pytest-bdd | Python-native; step definitions live alongside backend tests; no separate process, no separate runner |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Playwright over Selenium | Auto-wait eliminates SPA polling boilerplate; single-process model; headless without Xvfb | Smaller community history than Selenium; requires `playwright install` in CI |
| Real servers over filesystem-only | Bootstrap and edit-spec flows require real file writes and real server state; anything less tests a simulation | Server startup adds ~5–10s to CI run; addressed by session scope |
| AI mocked at Express, not Angular service | Tests the full HTTP + response-mapping chain; does not alter Angular code under test | Requires an Express test-mode switch; one additional env-flag to document |
| Session-scoped servers, function-scoped test data | Startup cost amortised; isolation achieved by scenario-level project directory creation | Scenarios must not share project names; naming convention enforced by fixture, not by CI |
| No base page object class | Four consumers, all unique; premature extraction constrains the shape before the second consumer calibrates it | If two classes do share a method, extraction requires an extra commit; acceptable cost |
| Documented skip over forced green | A scenario that cannot reach green due to a missing `[data-test]` attribute surfaces a pre-existing gap, not an E2E2 defect | Skipped scenarios are visible debt; each must carry a linked issue to prevent permanent deferral |

---

## Patterns

### Page Object as Anti-Corruption Layer

**When to use**: Any time a step definition needs to interact with a rendered component.

**How it works**: The page object class owns the selector knowledge for one component. Step definitions call named methods that express intent. The DOM mapping lives exclusively in the page object. When the component's structure changes, one class changes, not every step file that touches it.

**Example in this system**: `OperationBarPage` knows which `[data-test]` attribute triggers the rewrite operation. The rewrite-operation step definition calls the named method. When the operation-bar is restyled or its HTML structure changes, the `OperationBarPage` is the only file that needs updating.

### Session Fixture as Contract

**When to use**: When multiple test modules share expensive setup that should not be repeated per scenario.

**How it works**: `e2e/conftest.py` declares the fixture at session scope. All five step-definition modules import it. The fixture starts servers once, yields a stable base URL, and tears down after the last scenario. Per-scenario isolation is achieved through test data, not server restarts.

**Example in this system**: The bootstrap-happy and edit-spec feature files both need the Express API and Angular dev server. Neither encodes how those servers start. Both import the same fixture and inherit the same base URL, regardless of whether the server strategy ever changes.

### Selector Uniqueness Invariant

**When to use**: As a validation criterion for each new `[data-test]` attribute assigned to a page object method.

**How it works**: Each `[data-test]` value appears in exactly one page object method. Cross-component selectors are a violation. The invariant makes the success criterion from the epic mechanically verifiable: change a `[data-test]` attribute, and exactly one page object method fails.

**Example in this system**: If the editor component uses `[data-test="editor-content"]` and the preview component uses `[data-test="preview-content"]`, changing the editor's attribute breaks only `EditorPage`. If both components shared a `[data-test="content"]` attribute, the invariant would be violated and isolation would be lost.

---

## Execution Flow

```
[Task 1 — Decision]
  Driver choice ──→ Server strategy
                       │
[Task 2 — Foundation]  ▼
  4 Page objects ──→ conftest.py fixture
                       │
[Task 3 — Coverage]    ▼
  5 Feature files ──→ 5 Step-definition modules ──→ green or documented skip
```

Task 1 is a prerequisite to Task 2 because the server strategy determines what the conftest fixture encodes; writing page objects against an undecided fixture is writing against an unstable contract. Task 2 is a prerequisite to Task 3 because step definitions import page objects and the conftest fixture; authoring Gherkin scenarios before those imports are stable produces step files that drift before they are ever run. There is no parallel opportunity across the three tasks; each delivers the foundation the next task builds on.

Within Task 3, the five feature files can be authored in parallel once the shared fixture is stable, because each imports the same conftest and its own named page objects. The fixture contract from Task 2 is the multiplier the epic identifies: with it locked in, the sixth and seventh feature files are incremental; without it, each is a bespoke integration.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview