# 🎯 Epic: E2E2 — Behavioural Test Coverage for Retrofitted Components

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Spec Doc's four core UI components — editor, preview, operation-bar, and sidebar — were retrofitted without any behavioural test coverage. Every AI operation or editor refactor currently ships on manual confidence alone. A single selector rename or response-shape change can silently break the bootstrap flow, the rewrite operation, or the context-editor, and nothing in CI catches it. This epic adds the first automated regression net.

The shared fixture contract established in Task 2 is the multiplier. Once `conftest.py` encodes the server-strategy decision, every future feature's step definitions can be authored in parallel against a stable contract — the cost of adding the sixth, seventh, and eighth E2E scenario approaches zero. Without that contract locked in first, each new feature file becomes a bespoke integration that compounds drift rather than inheriting consistency.

For a solo founder, the business case is straightforward: behavioural tests are the prerequisite for confident velocity. The five covered workflows — bootstrap happy-path, bootstrap fail-fast, edit-spec, context-editor, and rewrite-operation — are exactly the paths a new user walks on first contact. Catching regressions there before they reach production protects conversion, not just correctness.

**Value Proposition**: A locked-in E2E fixture contract and five green feature files make every subsequent spec-doc UI change shippable with automated confidence instead of manual hope.

---

## Scope

### What This Epic Covers

- **E2E strategy decision** — driver choice (Playwright/Selenium/requests-only) and server pattern (real Express + Angular dev servers vs. filesystem-only), recorded as the `conftest.py` fixture strategy before any page object is written
- **Page object layer** — four classes (`new-project`, `operation-bar`, `sidebar`, `output-panel` — the components that received `[data-test]` retrofits in E2E-foundation Task 2; editor/preview were NOT retrofitted), each exposing named methods backed exclusively by `[data-test]` selectors, co-located in `e2e/pages/`
- **Shared fixture** — a single `e2e/conftest.py` encoding the chosen server strategy; the one import contract all five step-definition modules will use
- **Gherkin scenarios** — five `.feature` files covering bootstrap-happy, bootstrap-fail-fast, edit-spec, context-editor, and rewrite-operation, each with complete, reviewable scenario steps
- **Step implementations** — five pytest-bdd step-definition modules wired to page objects and the shared fixture; every scenario reaches green or carries a documented skip with an explicit reason

### What This Epic Does NOT Cover

- ❌ **New Angular components or component behaviour changes** — all `[data-test]` attributes are assumed present; missing selectors are pre-existing bugs, not E2E2 scope
- ❌ **A fifth page object** — if `new-project` surfaces as needed mid-Task 3, re-scope at the task boundary, not before
- ❌ **Retry/backoff, flakiness budgets, test-reporting dashboards** — no reliability infrastructure until a second consumer exists to calibrate the shape
- ❌ **Server orchestration abstractions** — if the real-server pattern is chosen, the fixture does minimum: start, yield, teardown; no wrapper layer above that

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Resolve E2E driver and server strategy** | None | — | 0.5 days | High |
| 2 | **Page objects + shared fixture** | 1 | — | 1 day | High |
| 3 | **Gherkin scenarios + step implementations** | 2 | — | 2 days | High |

### Task 1: Resolve E2E Driver and Server Strategy

The analysis identifies two explicit blockers before a single line of conftest can be written: which browser automation driver (Playwright Python, Selenium, or requests-only) and whether feature steps spin up real Express + Angular dev servers or interact with the filesystem directly. This task resolves both, records the decision with its rationale, and validates the chosen approach can run headless in CI without introducing a display dependency. No code ships from this task — only a locked decision that unblocks Task 2.

**Port budget**: One ADR-style decision record (≤30 lines); zero code files; CI environment probe if the real-server path is chosen — no fixture scaffolding, no page object skeletons, nothing that pre-empts Task 2's shape.

### Task 2: Page Objects + Shared Fixture

Write four page object classes in `e2e/pages/` — one per retrofitted component (editor, preview, operation-bar, sidebar) — each exposing named, intention-revealing methods backed exclusively by `[data-test]` selectors. Simultaneously encode the Task 1 decision into `e2e/conftest.py` as a pytest fixture that all five step-definition modules will import; this is the single shared contract and must be stable before Task 3 begins. No step definitions, no `.feature` files, and no server orchestration beyond what the chosen fixture strategy minimally requires.

**Port budget**: 4 page object files + 1 conftest fixture (~150–200 lines total); CI server-startup wiring deferred to Task 3 if the real-server pattern demands it; no base-class hierarchy, no retry logic, no fixture parameterisation — those abstractions have no second consumer yet.

### Task 3: Gherkin Scenarios + Step Implementations

Write five `.feature` files (bootstrap-happy, bootstrap-fail-fast, edit-spec, context-editor, rewrite-operation) with complete, human-readable Gherkin scenarios, then implement the corresponding pytest-bdd step-definition modules using the page objects and shared fixture from Task 2. Page object methods may be extended only if a selector gap surfaces during step authoring — no new page objects, no new components. Every scenario must reach green or carry a documented skip with an explicit reason and a linked issue before this task closes.

**Port budget**: 5 `.feature` files + 5 step-definition modules (~10–15 step functions total, ~200–250 lines); CI server-startup wiring included here only if the real-server pattern was chosen in Task 1 and was deferred from Task 2 — nothing beyond what reaching green requires.

---

## Success Criteria

This epic is complete when:

- ✅ The driver and server-strategy decision is recorded and agreed before any fixture code is written
- ✅ Four page object classes exist in `e2e/pages/`, each method backed by a `[data-test]` selector — zero class-name or text selectors present
- ✅ `e2e/conftest.py` is the single server-strategy fixture; no step-definition module imports any other setup code
- ✅ Five `.feature` files cover all named workflows with complete Gherkin scenarios (no scenario stubs)
- ✅ `pytest e2e/` runs to completion in CI with every scenario green or carrying a documented skip with an explicit reason
- ✅ A selector change in one component breaks exactly the page object methods for that component and no others — isolation is verifiable

---

## Non-Goals

- ❌ **Visual regression testing** — pixel-diff tools are a separate concern; correctness of behaviour is the only signal here
- ❌ **Performance or load testing** — out of scope until behavioural coverage is stable
- ❌ **Coverage of features outside the four retrofitted components** — scope is bounded to editor, preview, operation-bar, and sidebar workflows; new-project modal only if it replaces a named component and the task boundary is re-scoped explicitly
- ❌ **Pre-emptive structural test library** — any structural tests added must be triggered by a real violation encountered during this epic, not by theory

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview