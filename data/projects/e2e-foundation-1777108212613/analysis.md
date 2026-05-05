# 🔍 E2E foundation — Analysis

## The Problem
The test-coverage epic shipped 4 of 5 tasks. Task 5 (E2E) never executed because impl-guide generation hit the 600s Claude CLI timeout and produced no output. The `e2e` pytest marker is registered with zero consumers, leaving every user-facing workflow unverified at the browser level.

## Hard Constraints
- Angular component templates must carry `[data-test]` attributes before any Playwright selector can target them — frontend and Python work are coupled
- Spec Doc's backend is Express (Node), not Flask — "API-based test setup" means hitting Express endpoints or touching the filesystem directly, not Python fixtures calling Flask
- The 5 Gherkin feature names are already decided (`bootstrap-happy`, `bootstrap-fail-fast`, `edit-spec`, `context-editor`, `rewrite-operation`) — not up for re-scoping
- CI host needs Chromium installed; the sandbox demonstrated this gap is real

## Open Questions
- **E2E target**: does Playwright drive the Angular dev server + real Express API, or is the Express layer stubbed? → Real servers (closer to production) vs. mocked Express (faster, isolated)
- **pytest-bdd integration depth**: are `.feature` files pytest-bdd entry points (runner + step registry) or just living documentation alongside plain Playwright tests? → Full BDD runner vs. Playwright-only with feature files as spec artefacts
- **Karma unblocking**: is Karma verification a prerequisite before E2E ships, or a parallel track? → Sequential (confirm frontend unit baseline first) vs. parallel (browser-level E2E doesn't depend on Karma runtime)

## Dependencies & Sequencing
- `[data-test]` retrofit on 4 Angular components → must land before page objects are written (page objects lock in the selector contract)
- API test setup pattern decision → must be made before feature file step implementations begin (teardown strategy changes the step signatures)
- pytest-playwright + pytest-bdd install → prerequisite for any feature file execution; unblocks nothing else
- Karma host verification can run in parallel — different runtime, different machine requirement

## Explicitly Out of Scope
- Retroactive `@pytest.mark.*` sweep across ~250 pre-existing tests — no E2E dependency; re-scope when CI needs to filter by marker in a split pipeline
- Component tests for 15 Angular components — explicitly deferred per Task 2 "follow-on epic"; re-scope when component coverage is the named gap blocking a release
- `real_claude` test bodies — empty by design per Task 4; re-scope when live API smoke tests are a CI requirement
- Worktree branch cleanup + `=4.0.0` stray file — one-line cleanup PR, not E2E work