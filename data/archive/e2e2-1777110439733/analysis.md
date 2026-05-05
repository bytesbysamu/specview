# 🔍 E2E2 — Analysis

## The Problem
The four retrofitted spec-doc components have no behavioral test coverage. Without a shared fixture contract established first, Task 4 step definitions will be written inconsistently and break when selectors change. Tasks 3 and 4 together build the E2E layer from zero — page objects and conftest in Task 3, running scenarios in Task 4.

## Hard Constraints
- All selectors must use `[data-test]` attributes exclusively — no class names, no text, no ARIA roles
- pytest-bdd is the runner; browser automation driver is unspecified (see Open Questions — this is a blocker)
- `conftest.py` is the single shared contract; all five step-definition modules import from it, nothing else
- Task 3 port budget is hard: 4 page object files + 1 conftest; zero step definitions, zero `.feature` files
- Task 4 cannot add new page objects or new components — only extend existing page object methods if a selector gap surfaces

## Open Questions
- **Server strategy**: Real Express + Angular dev servers, or filesystem-only for teardown? — `subprocess.Popen` pair vs. direct filesystem reads/writes with no HTTP; this choice locks CI into an approach that's expensive to reverse
- **Browser automation driver**: Playwright (Python), Selenium, or `requests`-only? — determines the page object base class and whether "reach green" requires a headless display in CI
- **Resolved — 4 components are**: `new-project`, `operation-bar`, `sidebar`, `output-panel` — the components retrofitted with `[data-test]` attrs in the prior E2E-foundation Task 2 (commits `3832187`, `de75cf6`, `6926af1`, `7eb7b12`). Page objects must target ONLY these — editor and preview were never retrofitted, so any `[data-test]` selector lookup against them returns null.
- **Filesystem teardown scope**: Does "interact with filesystem directly" mean (a) cleanup-only after real-server tests, or (b) the entire test interaction bypasses HTTP?

## Dependencies & Sequencing
- Server strategy decision blocks conftest authoring — this is the Task 3 gate, nothing else can start
- Settled conftest blocks all 5 step-definition modules in Task 4 — parallel authoring is fine once it's done
- `[data-test]` attributes must already exist on all four components entering Task 3 — attribute gaps are retrofit bugs, not Task 3 scope
- CI server-startup wiring is a Task 4 concern only if real-server pattern is chosen; filesystem-only eliminates it entirely

## Explicitly Out of Scope
- New Angular components or component behavior changes — no component work in either task
- Retry/backoff, flakiness budgets, test reporting dashboards — no reliability infrastructure until a second consumer exists to calibrate it
- A 5th page object — if `new-project` surfaces as needed mid-Task 4, re-scope at the task boundary, not before
- Server orchestration abstractions (process managers, health-check polling) — if real-server pattern is chosen, the fixture does minimum: start, yield, teardown; no wrapper layer
- Any `[data-test]` attribute additions — retrofit is assumed complete; missing selectors are pre-existing bugs