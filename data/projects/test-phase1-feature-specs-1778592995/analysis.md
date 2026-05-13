# 🔍 Test Phase 1: Feature Specs & Testing Architecture — Analysis

## The Problem
The overview page has 17+ features shipped across 10 epic branches with zero feature-level specifications. Unit tests (Phase 3) shipped *before* specs existed, meaning 146 tests were written against implementation, not requirements. This phase creates the spec layer that should have come first, retroactively establishing the contract that Gherkin and unit tests derive from.

## Hard Constraints
- Spec-doc stack: Flask + Angular, Docker Compose deploy — specs must be testable against `CHAIN_PROVIDER=mock`
- Existing E2E infra (pytest-bdd + Playwright) and unit infra (Karma + Jasmine) are locked in
- Solo dev — the spec file must be a single self-contained document, not a distributed spec system
- No CI pipeline exists for frontend tests; this phase is **documentation only**, not pipeline work

## Open Questions
- **Scope boundary:** The brain dump says "overview page" but includes login, `/upgrade` route, billing interceptor, and Stripe checkout — are these one spec or separate specs per route? → (a) single spec file, (b) one spec per route/page, (c) overview-only, others deferred
- **Phase 3 reconciliation:** 146 unit tests already shipped. Does this phase audit them against the new specs, or ignore them? → (a) audit + gap list, (b) specs only, reconcile in a future phase
- **"Spec pipeline" automation:** The dump says "explore the actual codebase" to discover features. Is the deliverable a *script* that inventories features, or a *manually written* spec doc? → Manual doc; a discovery script is a separate tool project
- **Lapsed→free mapping:** `billing_status()` maps `lapsed→free` for OpenAPI but UI distinguishes them. Which is the spec-level truth? → UI tri-state (`free|pro|lapsed`) is the testable contract

## Dependencies & Sequencing
- SaaS Phase 2a/2b shipped and merged (PRs #49, #50, 2026-05-13) — billing/upgrade features are stable and ready for spec writing
- Feature discovery requires reading impl guides from all 10 projects — this blocks writing the spec, not just numbering it
- Phase 2 (Gherkin) and Phase 3 reconciliation both depend on this phase's feature numbering being final

## Explicitly Out of Scope
- **CI pipeline setup** — mentioned as missing, but is infrastructure work, not spec work. Trigger: Phase 2 E2E execution
- **Visual regression tests** — listed as missing, entirely different toolchain. Trigger: design system stabilization
- **Backend API specs** — 5 E2E features already cover backend flows; this phase is frontend-facing only
- **Writing or modifying tests** — this phase produces the *document*; Phases 2 and 3 produce tests
- **Automated codebase scanner** — "spec pipeline should explore the codebase" implies tooling; defer to a separate task. This phase: manual inventory + spec writing