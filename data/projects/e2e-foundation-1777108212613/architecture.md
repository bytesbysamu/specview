# 🏗️ Solution Architecture: E2E Foundation

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The E2E foundation closes the last structural gap in the test pyramid by adding two previously absent layers: a verified Karma baseline at the unit level, and Playwright-driven browser tests at the workflow level. Both layers address the same root cause — assertions written without a live runner are claims, not measurements. The architecture treats the Karma job and the Playwright job as structurally independent concerns that share nothing but the Angular codebase they exercise.

The central insight is that browser-level tests are only as stable as the selectors they depend on. Class names, element IDs, and tag structures change when the product is redesigned; they are visual implementation details, not behavioral contracts. The `[data-test]` selector retrofit on four Angular templates is therefore not merely a convenience — it establishes a stable semantic contract between the product's component layer and the test layer, insulating page objects from redesigns that have no bearing on workflow behavior.

The architecture's three layers — selector contract, page objects, and Gherkin feature files — are deliberately thin. The selector contract lives in Angular templates. Page objects translate selectors into named, reusable actions. Feature files compose those actions into workflow assertions readable by anyone familiar with the product. The shared `e2e/conftest.py` fixture is the only place server lifecycle appears; it is a single seam, not a per-test concern. This structure mirrors the bounded-context principle already applied in the feature folders: each layer has one job, and no layer reaches past its neighbor.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| `[data-test]` as the only selector contract | Page objects reference no class, id, or tag selectors; the retrofit on 4 component templates is the surface area that fulfills this invariant |
| One shared fixture, not per-test setup | `e2e/conftest.py` holds the single server-lifecycle fixture all five feature files import; duplication in teardown logic compounds across files and drifts silently |
| Real servers for browser tests | Playwright exercises the full Angular + Express stack because the regressions it catches — route renames, template changes, broken API contracts — are by definition integration failures that a mocked layer would not surface |
| Concrete page objects, not a hierarchy | Four page objects for four components; no base class, no inheritance chain — each is a named adapter around one component's `[data-test]` surface |
| pytest-bdd stays within the existing pytest ecosystem | Markers, fixtures, and conftest conventions already established by the 302-test backend suite carry forward unmodified; adding a second test runner (Behave) would split the ecosystem without adding coverage |

---

## System Boundaries

### What This System Includes

- Karma runtime verification — executing the 16 existing frontend service specs against a live Chrome-equipped host and aligning any assertions written without a runner
- Playwright + pytest-bdd package installation and Chromium CI configuration — wired to the existing `pytest -m e2e` marker registered in Task 1
- `[data-test]` selector retrofit on four Angular component templates: `new-project`, `operation-bar`, `sidebar`, and `output-panel`
- Four page object classes in `e2e/pages/` — one per retrofitted component, exposing named methods backed exclusively by `[data-test]` selectors
- One shared pytest fixture in `e2e/conftest.py` encoding the server setup and teardown strategy for all five feature files
- Five Gherkin `.feature` files and their pytest-bdd step definition modules: `bootstrap-happy`, `bootstrap-fail-fast`, `edit-spec`, `context-editor`, `rewrite-operation`
- CI integration — two independent jobs (Karma, Playwright) both passing on main

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Component tests for 15 Angular components | Explicitly deferred in the prior epic as a follow-on; the trigger condition is component coverage becoming the named gap blocking a release |
| Retroactive `@pytest.mark.*` sweep on ~250 pre-existing tests | Markers affect CI filtering, not pass/fail; mechanical edit with no correctness value until the pipeline is sharded — re-scope when sharding is the named problem |
| `real_claude` test bodies | Registered and empty by design per Task 4 of the prior epic; the trigger condition is a live API smoke requirement with a stub baseline to compare against |
| CI pipeline optimization (parallel matrix, test splitting) | Premature until five feature files have run through production CI for at least one sprint and actual timing data motivates the split |
| Worktree branch cleanup | Cosmetic; handled outside epic scope |

---

## Component Design

### Selector Contract Layer

**Purpose**: Provides a rename-proof, semantic surface that page objects can address without coupling to visual structure. Without this layer, any CSS refactor silently breaks E2E selectors.

**Key Parts**:
- `new-project.component.html` — receives `[data-test]` attributes on the project name input, the template selector, and the bootstrap trigger; consumer is `NewProjectPage` in `e2e/pages/`
- `operation-bar.component.html` — receives attributes on each AI operation button (rewrite, expand, compress, clarify, generate); consumer is `OperationBarPage`
- `sidebar.component.html` — receives attributes on the project list items and the new-project toggle; consumer is `SidebarPage`
- `output-panel.component.html` — receives attributes on the output container and any copy or accept controls; consumer is `OutputPanelPage`

**Patterns**: Anti-corruption layer — the `[data-test]` attribute decouples the test layer from the rendering layer the same way an ACL decouples a domain from an external API's response format.

---

### Page Object Layer

**Purpose**: Translates `[data-test]` selectors into named, reusable actions so step definitions express intent ("click the bootstrap button") rather than mechanics ("find `[data-test='bootstrap-trigger']` and click it"). Encapsulating this translation in one class per component means a selector change repairs one file, not five step definition modules.

**Key Parts**:
- `NewProjectPage` — actions for entering a project name, selecting a template, and triggering bootstrap; consumer: `bootstrap-happy` and `bootstrap-fail-fast` step definitions
- `OperationBarPage` — actions for triggering each of the five AI operations; consumer: `rewrite-operation` step definitions
- `SidebarPage` — actions for navigating between projects and opening the new-project modal; consumer: `edit-spec` and `context-editor` step definitions
- `OutputPanelPage` — assertions on content presence, load state, and output content; consumer: all five step definition modules

**Patterns**: Page Object — isolates selector knowledge; each object is the single place to update when a `[data-test]` name changes.

---

### Shared Server Fixture

**Purpose**: Manages the Angular dev server and Express API server lifecycle once, for all five feature files. Without a shared fixture, each feature file either duplicates startup/teardown or trusts that another test left the server running — both patterns have broken CI unpredictably in other projects.

**Key Parts**:
- Session-scoped fixture in `e2e/conftest.py` — starts Express (port 3100) and Angular dev server (port 4201) before the E2E suite runs; shuts them down after; consumer: all five feature file step definition modules
- Health-check gate — the fixture polls both server health endpoints before yielding to step definitions; this eliminates race conditions between server startup and the first Playwright navigation that caused intermittent failures in comparable setups

**Patterns**: Fixture-as-contract — the fixture is the seam. Step definitions import it by name; they carry no knowledge of how servers start or what ports they use.

---

### Gherkin Feature Layer

**Purpose**: Expresses the five product workflows in business-readable form so regressions are identified at the workflow level, not the assertion level. A failing `bootstrap-happy` scenario names a broken user path, not a broken line of JavaScript.

**Key Parts**:
- `bootstrap-happy.feature` + step module — the primary new-project workflow from brain-dump input to generated spec files appearing in the sidebar; consumer: CI `pytest -m e2e`
- `bootstrap-fail-fast.feature` + step module — validates that an empty or invalid project name surfaces an error state before any AI call is made
- `edit-spec.feature` + step module — opening an existing spec, making a change, and confirming auto-save persists
- `context-editor.feature` + step module — interacting with the principles/codebase/references context panels
- `rewrite-operation.feature` + step module — triggering a rewrite AI operation and verifying output appears in the output panel

**Patterns**: Given/When/Then maps directly to Arrange/Act/Assert — each Gherkin scenario is a test with a product-legible name, consistent with the `condition_expectedOutcome` naming convention already established in the backend suite.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Browser automation | Playwright (Python) | Native pytest integration preserves the existing conftest/marker/fixture conventions; Chromium bundles with `playwright install` removing the Chrome-version drift problem that plagues Selenium setups |
| BDD framework | pytest-bdd | Stays within the existing pytest ecosystem — markers, session fixtures, and conftest inheritance all carry over unchanged; Behave would require a separate runner and duplicate conftest patterns |
| Frontend unit runner | Karma + Jasmine | Already installed and configured; verification is a host requirement (Chrome), not a configuration change |
| Selector protocol | `[data-test]` HTML attributes | Semantic, not structural — survive CSS refactors, class renames, and tag changes; no runtime cost |
| Server orchestration | Real Angular dev server + real Express | The regressions E2E tests are designed to catch exist precisely in the rendering and routing layers; mocking either layer would make the tests blind to the failures they are intended to detect |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Real Express + Angular servers over filesystem mocking | Route renames and template errors are the stated failure modes; they do not appear under filesystem interaction. A stub that bypasses HTTP is testing the step definitions, not the product. | Slower suite startup; CI must manage two server processes. Mitigated by session-scoped fixture starting servers once per run. |
| pytest-bdd over Behave | The backend's 302-test suite is already on pytest. A second runner (Behave) would require its own conftest, its own fixture chain, and its own CI step — three new seams for zero coverage gain. | pytest-bdd's Gherkin parser is less feature-rich than Behave's. Acceptable: the five scenarios don't require advanced Gherkin constructs. |
| Session-scoped server fixture, not function-scoped | Playwright tests are slow to start servers. Function-scoped setup makes a 5-feature suite 5× slower for no isolation benefit, since the product's state is reset by API calls inside the tests, not by server restarts. | A crashing server mid-suite leaves subsequent tests in an undefined state. The fixture's health-check gate detects this and fails fast rather than producing phantom assertion errors. |
| Four independent page objects, no shared base class | The prior engineering scar from MapStruct applies in reverse: a base class built before two page objects share behavior is speculative abstraction. The four components have distinct surfaces; any shared helper should emerge from a real overlap, not be pre-emptively designed. | If a fifth page object emerges with identical patterns, extraction is a one-refactor operation — cheap once the shape is clear, expensive to un-abstract if the assumption was wrong. |
| `[data-test]` retrofit as a prerequisite to page objects | Page objects written against class selectors would require rewriting when the retrofit lands. Retrofit first, then build page objects once, against the stable interface. | Task 2 and Task 3 are sequential on the page-object side. This is the correct dependency order: contracts before consumers. |

---

## Patterns

### Page Object

**When to use**: Any time a step definition needs to interact with a rendered Angular component.

**How it works**: A class wraps one component's `[data-test]` selectors and exposes named methods. Step definitions call methods, not selectors. When a selector changes, one file changes.

**Example in this system**: `OperationBarPage.triggerRewrite()` is the single place that knows `[data-test='rewrite-btn']`. The five feature files that need rewrite behavior call the method — they do not re-derive the selector.

---

### Fixture-as-Contract

**When to use**: When multiple test files need identical setup and teardown — particularly expensive setup like server startup.

**How it works**: A session-scoped pytest fixture handles startup once per test session and teardown once at the end. Test files declare a dependency on the fixture name; they receive the running application context without knowing how it was started.

**Example in this system**: All five step definition modules import the session fixture from `e2e/conftest.py`. The fixture starts Express on 3100 and Angular on 4201, polls their health endpoints, and yields. Neither port nor startup logic appears anywhere else.

---

### Gherkin as Workflow Specification

**When to use**: When a regression's business meaning matters as much as its technical cause.

**How it works**: Gherkin scenarios are the test names made executable. A failing scenario reports a broken user path in product language, not a broken assertion in test language. pytest-bdd maps each Gherkin step to a Python function; the Python function calls a page object method.

**Example in this system**: `bootstrap-happy` describes the core value loop — user provides a brain dump, product generates structured specs — in terms a product owner can read. If it fails in CI, the failure message names the broken workflow, not the broken selector.

---

## Execution Flow

```
[Phase 1 — Parallel]
  Task 1: Karma verification ──────────────────────────────────────────▶ Karma green on CI
  Task 2: Tooling install + [data-test] retrofit ──────────────────────▶ Playwright installed
                                                                           4 components retrofitted

[Phase 2 — Sequential on Task 2]
                                   Task 3: Page objects + conftest ──▶ 4 page object classes
                                                                        shared fixture in conftest

[Phase 3 — Sequential on Task 3]
                                                   Task 4: Feature files ──▶ 5 .feature files
                                                                              5 step modules
                                                                              pytest -m e2e green
```

Tasks 1 and 2 share no dependencies and can run in parallel. Task 3 cannot begin until Task 2 delivers the `[data-test]` retrofit — page objects written before selectors exist are bound to stale assumptions. Task 4 is gated on Task 3 because step definitions call page object methods, and step stubs written before page objects exist embed the coupling problem the page object pattern was designed to prevent. Task 1 delivers the Karma job independently; it has no input into the Playwright layer and no dependency on it.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview