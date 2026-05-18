# 🔍 E2E Full Coverage — PD + SA (Runs 2-3) — Analysis

## The Problem
Run 1 covered 17/54 features with 43 E2E scenarios. 37 features across Project Detail and SaaS domains have zero E2E coverage. The goal is full traceability — every feature ID maps to at least one Gherkin scenario — split into Docker-runnable and mock-skipped buckets.

## Hard Constraints
- Existing pipeline pattern (Run 1) must be followed — no new test framework
- Docker-only pass target: ~62/103 scenarios; remainder tagged `_SKIP_MOCK`
- Page object pattern already established in `overview_page.py`
- `e2e/docs/conventions.md` governs tags, step style, naming — non-negotiable
- No Redis, no Postgres queue — in-process state only

## Open Questions
- **SA-14–SA-19 vs. success criteria**: Six features are "Backend only — pytest" but success criteria demands every feature has an E2E scenario. Which wins — drop them from E2E count, or add thin smoke scenarios that hit the endpoint via browser?
- **Plan state injection**: How does a test set a user to free/pro/lapsed? Direct DB seed? Admin API endpoint? Test-only Flask route? (Decision affects `saas_preconditions.py` design entirely)
- **detail_page.py "extends" OverviewPage**: Inheritance or composition? Inheritance couples domains; composition via shared selectors module is cleaner but needs deciding now.
- **SA-08 (429 redirect)**: Force a real rate-limit hit (fragile, slow) or mock the 429 response? If mock, it's skip-tagged and Docker-pass count drops.
- **Scenario counts don't add up**: PD files sum to 30 (not ~35), SA files sum to 20 (not ~25). Are there unlisted scenarios or are the targets wrong?

## Dependencies & Sequencing
- Run 2 before Run 3 — `detail_preconditions.py` reuses `overview_preconditions.py` login steps; SA tests need the same pattern stable first
- Multi-user auth (SA-06) blocks all isolation tests — user-creation API or seed script must exist before SA scenarios can be written
- Seed data for Run 2 (project with full spec set) must be built before any PD scenario runs — blocks the entire run
- Mock infrastructure is a separate workstream — ~41 skip-tagged scenarios stay dead until it ships

## Explicitly Out of Scope
- **SA-14–SA-19 as E2E scenarios** — backend-only; pytest covers them; adding browser tests adds cost with zero UI signal. Re-scope if someone requests UI smoke for security headers.
- **Mock infrastructure build-out** — this epic writes the scenarios and skip-tags them; building the mock server is a different epic. Re-scope when mock epic lands.
- **Stripe live-mode testing** — SA-21 tests redirect only; verifying actual payment flow belongs to a Stripe integration epic. Re-scope if checkout breaks in prod.
- **Karma unit test changes** — success criteria mentions "no Karma regressions" but this epic writes E2E only; unit tests are not touched. Re-scope if E2E seed data somehow conflicts.