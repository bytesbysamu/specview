# 🎯 Epic: E2E Full Coverage — PD + SA (Runs 2-3)

## Business Value

spec-doc's documentation-first methodology only works if the tool itself ships with confidence. Run 1 proved the E2E pipeline works — 43 scenarios across 17 features, 32 passing against Docker. But 37 features across Project Detail and SaaS domains remain uncovered. Every uncovered feature is a regression blind spot — a place where a refactor or new capability can silently break user-facing behavior with zero automated signal.

Full traceability (every feature ID → at least one Gherkin scenario) eliminates the "works on my machine" gap for a solo dev shipping across multiple projects. When Sam touches the detail reader or billing flow in a sprint focused on something else, the E2E suite either passes or flags the break immediately. The alternative — manual smoke testing across 54 features before each deploy — is a 2+ hour tax that compounds with every release.

The Docker-pass target (~62/103 scenarios) also establishes a CI gate that runs without external dependencies. The remaining ~41 mock-tagged scenarios document expected behavior precisely, so when the mock infrastructure epic lands, those scenarios activate without rewriting a single line.

## Scope

### What This Epic Covers
- **Run 2 (Project Detail)** — 16 features (PD-01 to PD-16) across 6 feature files with ~30 Gherkin scenarios covering the reader panel, sidebar, spec-gen pipeline, AI ops, results, and brainstorm flows
- **Run 3 (SaaS)** — 15 E2E-testable features (SA-01 to SA-13, SA-20, SA-21) across 4 feature files with ~20 Gherkin scenarios covering auth, project isolation, billing, and upgrade flows
- **Test infrastructure** — page objects (`detail_page.py`, `saas_page.py`), precondition steps, seed data, and multi-user auth setup required to execute both runs
- **Skip classification** — every mock-dependent scenario tagged `_SKIP_MOCK` per conventions; Docker-pass scenarios verified green
- **Traceability** — every feature ID from PD-01 to SA-21 maps to at least one scenario

### What This Epic Does NOT Cover
- ❌ **SA-14 to SA-19 (backend-only features)** — IP rate limiting, security headers, canary endpoint, SKIP_AUTH gating, project isolation enforcement, billing 429 header are pytest-only; no browser signal to test
- ❌ **Mock infrastructure build-out** — this epic writes and skip-tags scenarios; building the mock server is a separate epic
- ❌ **Stripe live-mode verification** — SA-21 tests the checkout redirect only; actual payment flow belongs to a Stripe integration epic
- ❌ **Karma unit test changes** — E2E-only scope; unit tests are not touched
- ❌ **Run 1 modifications** — existing 43 OV scenarios are stable and not revisited

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **PD Infrastructure & Seed Data** — `detail_page.py` (composition over inheritance, shared selectors module), `detail_preconditions.py`, seed script for project with full spec set (braindump + analysis + epic + architecture + timeline + impl-guide) | None | — | 2 days | High |
| 2 | **Run 2 Scenario Authoring** — 6 feature files (`detail-reader`, `detail-sidebar`, `detail-specgen`, `detail-ai-ops`, `detail-results`, `detail-brainstorm`), ~30 scenarios, `detail_steps.py`, `test_detail.py` registration | Task 1 | — | 3 days | High |
| 3 | **SA Infrastructure & Multi-User Auth** — `saas_page.py`, `saas_preconditions.py` with plan-state injection (test-only Flask route for setting free/pro/lapsed), user-creation API for user B, separate JWT generation | Task 2 | — | 2 days | High |
| 4 | **Run 3 Scenario Authoring** — 4 feature files (`saas-auth`, `saas-isolation`, `saas-billing`, `saas-upgrade`), ~20 scenarios, `saas_steps.py`, `test_saas.py` registration | Task 3 | — | 2 days | High |
| 5 | **Traceability Validation & Docker Pass** — verify every PD/SA feature ID appears in at least one scenario tag, confirm ~15 PD + ~15 SA scenarios pass against Docker, remaining correctly skip-tagged, `ng build` clean | Tasks 2, 4 | — | 1 day | High |

## Success Criteria

- ✅ Every feature from PD-01 to PD-16 and SA-01 to SA-21 (excluding SA-14–SA-19) has at least one E2E scenario tagged with its feature ID
- ✅ ~62 total scenarios (across all 3 runs) pass against Docker Compose with no external mocks
- ✅ ~41 mock-dependent scenarios tagged `_SKIP_MOCK` and skip cleanly without failure noise
- ✅ Page objects for all 3 domains (`overview_page.py`, `detail_page.py`, `saas_page.py`) follow identical structural pattern
- ✅ `ng build --configuration production` passes with zero errors
- ✅ No Karma unit test regressions introduced
- ✅ All conventions from `e2e/docs/conventions.md` followed — tags, step style, naming verified in Task 5
- ✅ Multi-user isolation proven: user B receives 403 on user A's project in Docker pass

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — Page object design, seed strategy, plan-state injection mechanism
- [Timeline](./timeline.md) — Execution status and completion tracking