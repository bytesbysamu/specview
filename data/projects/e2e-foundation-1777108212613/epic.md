# 🎯 Epic: E2E foundation

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The test-coverage epic shipped 4 of 5 tasks, leaving the E2E layer entirely absent. Every user-facing workflow — bootstrap, edit, context, rewrite — has zero browser-level regression coverage. A single route rename in Express or an accidental template change in Angular can silently break the product with no automated signal until a user reports it. The five workflow names are already product-legible (`bootstrap-happy`, `edit-spec`, `rewrite-operation`); they belong in CI, not just in a planning table.

A verified Karma runtime is an unresolved prerequisite the prior epic flagged as High severity. The 16 frontend service specs were written without a live Karma runner confirming them. Until a Chrome-equipped host executes those specs green, the frontend baseline is an assertion, not a measurement. Establishing that baseline is as much a confidence item as a CI requirement — and it has to land before browser-level tests layer on top of the same component code.

Together, Karma verification and the Playwright/pytest-bdd layer close the last structural gap in the test foundation. The result is a CI pipeline that signals regressions at the unit, integration, and workflow level before they reach users.

**Value Proposition**: Verify the Karma frontend baseline and ship 5 browser-level feature file tests so every merge to main is protected against workflow regressions in the product's most-used paths.

---

## Scope

### What This Epic Covers

- **Karma runtime verification** — confirm all 16 frontend service specs execute and pass on a Chrome-equipped host; align any assertions that were written without a live runner
- **Playwright + pytest-bdd tooling install** — add both packages, configure the Chromium install in CI, and wire the `e2e` pytest marker to the new suite
- **`[data-test]` retrofit on 4 Angular components** — add selector attributes to `new-project`, `operation-bar`, `sidebar`, and `output-panel` as a stable, rename-proof contract for page objects
- **Page objects + API test setup pattern** — write `e2e/pages/` classes for the 4 retrofitted components and encode the teardown strategy as a shared pytest fixture in `e2e/conftest.py`
- **5 Gherkin feature files with step definitions** — `bootstrap-happy`, `bootstrap-fail-fast`, `edit-spec`, `context-editor`, `rewrite-operation`; each mapped to pytest-bdd step implementations exercising the app through Playwright

### What This Epic Does NOT Cover

- ❌ Retroactive `@pytest.mark.*` sweep across ~250 pre-existing tests — markers help CI filtering but don't affect pass/fail; no E2E dependency
- ❌ Component tests for 15 Angular components — explicitly deferred per the prior epic's Task 2 "follow-on" decision
- ❌ `real_claude` test bodies — empty by design per Task 4 spec; no trigger condition met yet
- ❌ Worktree branch cleanup and `=4.0.0` stray file — cosmetic, handled in a one-line cleanup PR outside this epic

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Karma runtime verification** | None | 2 | 0.5 days | High |
| 2 | **Tooling install + `[data-test]` retrofit** | None | 1 | 1 day | High |
| 3 | **Page objects + API setup pattern** | 2 | — | 1 day | High |
| 4 | **5 Gherkin feature files** | 3 | — | 2 days | High |

### Task 1: Karma runtime verification

Execute the 16 existing frontend service specs on a Chrome-equipped host and confirm they pass end-to-end. If any spec is red, audit the assertion against actual service behavior and fix — these specs were written without a live Karma runner, so a small alignment pass may be necessary. This task delivers a confirmed frontend-unit baseline before the E2E layer depends on the same component code.

**Port budget**: 0–5 spec file assertion corrections; no new specs written, no new services covered, no mock factory additions — scope limited to making what already exists provably green on a real runner.

### Task 2: Tooling install + `[data-test]` retrofit

Add `playwright` and `pytest-bdd` to `requirements-dev.txt`, configure the Playwright Chromium install in the CI workflow, and add `[data-test]` selector attributes to the four Angular component templates (`new-project`, `operation-bar`, `sidebar`, `output-panel`). The selector retrofit co-locates with the tooling install because page objects cannot be written until both the framework exists and the selectors are in the templates.

**Port budget**: ~4 Angular template edits (attribute additions only, no logic changes), one `requirements-dev.txt` diff, one CI workflow step — no page object classes, no feature files, no step definitions in this task.

### Task 3: Page objects + API setup pattern

Write `e2e/pages/` classes for the four retrofitted components, each exposing named methods backed exclusively by `[data-test]` selectors. Simultaneously, decide and encode the API test setup pattern — whether feature file steps spin up real Express + Angular dev servers or interact with the filesystem directly for teardown — as a shared pytest fixture in `e2e/conftest.py`. This fixture is the one contract all five feature files will import.

**Port budget**: 4 page object files + 1 conftest fixture; no step definitions, no `.feature` files, no server orchestration beyond what the shared fixture requires — CI server-startup wiring deferred to Task 4 if the chosen pattern requires it.

### Task 4: 5 Gherkin feature files

Write `.feature` files for `bootstrap-happy`, `bootstrap-fail-fast`, `edit-spec`, `context-editor`, and `rewrite-operation`, each with complete Gherkin scenarios. Implement the corresponding pytest-bdd step functions using the page objects and shared fixture from Task 3. Each feature file must reach green (or carry a documented skip with an explicit reason) before this task closes.

**Port budget**: 5 `.feature` files + 5 step-definition modules (~10–15 step functions total); page object methods may be extended only if a selector gap surfaces during step authoring — no new page objects, no new components.

---

## Success Criteria

This epic is complete when:

- ✅ All 16 frontend service specs pass under a live Karma runner on a Chrome-equipped host
- ✅ `pytest -m e2e` executes all 5 feature files with zero unimplemented steps and zero failures in the project's CI environment
- ✅ Page objects for all 4 components reference only `[data-test]` selectors — no class, id, or tag selectors anywhere in `e2e/pages/`
- ✅ A single shared pytest fixture in `e2e/conftest.py` handles test setup and teardown for all 5 feature files — no per-file setup duplication
- ✅ Both the Karma job and the Playwright job pass on main in CI

---

## Non-Goals

- ❌ Retroactive marker sweep on ~250 pre-existing tests — re-scope when CI needs marker-based test sharding in a split pipeline
- ❌ Component tests for 15 Angular components — re-scope when component coverage is the named gap blocking a release, not before
- ❌ `real_claude` live API smoke tests — re-scope when live API smoke becomes an explicit CI requirement with a passing stub-server baseline to compare against
- ❌ CI pipeline optimization (parallel matrix, test splitting) — premature until the 5 initial feature files have run in production CI at least one full sprint

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview