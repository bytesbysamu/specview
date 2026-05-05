# 🔍 Gherkin Feature Files — Analysis

## The Problem
Task 3's page objects and shared fixture exist but have no executable test coverage. Five application flows (bootstrap-happy, bootstrap-fail-fast, edit-spec, context-editor, rewrite-operation) are untested. This task closes that gap by pairing each flow with a `.feature` file and a pytest-bdd step module.

## Hard Constraints
- Page objects and shared fixture come from Task 3 — they are the only allowed source; no new page objects.
- No new UI components may be added during step authoring.
- Page object methods may only be extended when a real selector gap surfaces — not preemptively.
- Port budget is fixed: 5 `.feature` files + 5 step modules, ~10–15 step functions total. Exceeding it is a scope violation.

## Open Questions
- **Is Task 3 stable?** Step authoring against a moving fixture risks churn. Options: treat Task 3 as locked before starting, or accept that step modules may need re-sync mid-task.
- **What counts as "green"?** Scenarios hitting a live backend, a mock, or a local test double? Options: all scenarios use a fixture-level mock; real backend required for at least happy-path; skips allowed on network-dependent scenarios with explicit reason strings.
- **Who owns the scenario content?** The five filenames are given but the actual scenarios are not. Options: scenarios are pre-specified elsewhere (link needed), or they must be authored here from scratch against existing UI behaviour.

## Dependencies & Sequencing
- Task 3 (page objects + shared fixture) must be complete and merged before step authoring begins — step functions cannot be written against an unstable selector API.
- The five feature files and five step modules are independent of each other and can be authored in parallel once Task 3 is locked.
- A selector gap in any step module may unblock a page object extension — that extension must be reviewed against the "no new page objects" constraint before merging.

## Explicitly Out of Scope
- **New page objects** — explicitly banned; re-scope only if a second feature group emerges with no existing object coverage.
- **New UI components** — any missing selector should be resolved by extending an existing page object method, not by building new UI.
- **Scenario discovery / behaviour specification** — if the five scenarios don't already exist written down, that is an analysis gap that must be resolved before implementation, not during it.
- **CI integration for the test suite** — running these tests in a pipeline is a separate concern; no GitHub Actions changes belong in this task's port budget.