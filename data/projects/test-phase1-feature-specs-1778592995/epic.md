# 🎯 Epic: Test Phase 1: Feature Specs & Testing Architecture

## Business Value

The overview page has shipped 17+ user-facing features across 10 epic branches with zero feature-level specifications. Every test written so far — 155 frontend unit tests in Phase 3, 819 backend pytest tests, 10 E2E scenarios — was authored against implementation details rather than a requirements contract. When a feature changes, there is no single document that says what the correct behavior *should* be, only scattered code that shows what it *happens* to do. This makes regression detection a coin flip: tests pass because they mirror code, not because they verify intent.

A testable feature spec layer converts tribal knowledge into a durable contract. Gherkin scenarios (Phase 2) and unit tests (Phase 3 reconciliation) derive from these specs, not from reading source code. When a feature changes, the spec updates first and broken tests become intentional signals rather than noise. For a solo founder shipping across five active projects, this is the difference between "I think the overview still works" and "the spec says it works and the tests prove it."

The secondary deliverable — the testing architecture map — gives a single-page answer to "what is tested, what is not, and where does a new test go?" Without this, every future test phase starts with re-discovery. The map also surfaces the gap between existing E2E coverage (backend flows only) and the untested frontend surface, making Phase 2 scoping mechanical rather than exploratory.

## Scope

### What This Epic Covers

- **Complete feature inventory** — Scan all 10 epic branch impl guides and the live codebase to discover every user-facing feature, replacing the draft F1–F17 list with a verified, numbered catalog
- **Testable feature specs for the overview page** — Auth gate, masthead, section navigation, status bar, search, grid layouts, cards, taxonomy logic, teaser logic, polling, dark mode, context section, and create modal — each with defined inputs, outputs, and edge cases
- **Testable feature specs for SaaS features** — Project isolation (ownership, 403 UI, dual-write), billing (upgrade page tri-state, usage meter, billing interceptor, lapsed handling, post-checkout verification), and login/register flows
- **Testing architecture map** — Document the four-layer test pyramid (specs → Gherkin → E2E → unit), existing infrastructure per layer, and coverage gaps that Phase 2 and Phase 3 must fill
- **Phase 3 unit test audit** — Cross-reference the 155 existing frontend unit tests (+ 819 backend) against the new specs to produce a gap list for future reconciliation

### What This Epic Does NOT Cover

- ❌ **Writing or modifying any tests** — This phase produces the specification document; Phases 2 and 3 produce tests
- ❌ **CI pipeline setup** — No frontend test pipeline exists, but building one is infrastructure work triggered by Phase 2 E2E execution
- ❌ **Visual regression testing** — Different toolchain entirely; deferred until design system stabilization
- ❌ **Backend API specifications** — The 5 existing E2E features already cover backend flows; this phase is frontend-facing only
- ❌ **Automated codebase scanner tooling** — Feature discovery is a manual inventory task, not a reusable tool project
- ❌ **Gherkin scenario authoring** — That is Phase 2's deliverable, derived from this phase's specs
- ❌ **Test execution or coverage measurement** — No tests are run; the deliverable is a document

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Feature Discovery & Complete Inventory** — Read impl guides and exec summaries from all 10 epic branches, scan live codebase files (template, component, routes, services, interceptors, state), produce a verified numbered feature list replacing the draft F1–F17 | None | — | 1 day | High |
| 2 | **Overview Page Feature Specs** — Write testable specifications for all overview page features (auth gate, masthead, nav + badges, status bar states, search/filter, all-sections grid, hero grid, featured card, project cards, section taxonomy, project teasers, single-section view, polling/error recovery, update banner, create modal, dark mode, context section) with inputs, expected outputs, and edge cases | Task 1 | — | 2 days | High |
| 3 | **SaaS & Auth Feature Specs** — Write testable specifications for project isolation (user-scoped listing, 403 access denied UI, dual-write creation, auto-migration), billing (upgrade page free/pro/lapsed states, post-checkout verification, SubscriptionService signals), usage meter, billing interceptor (header reading, 429 routing), and login/register flows | Task 1, Phase 2b branch merged | Task 2 | 1.5 days | High |
| 4 | **Testing Architecture & Coverage Gap Map** — Document the four-layer pyramid, catalog existing infra per layer (Karma config, E2E conftest, page objects, mocks), map each feature spec to its current coverage state (none / unit-only / E2E-only / both), and list gaps that Phase 2 and Phase 3 must close | Tasks 2–3 | — | 1 day | High |
| 5 | **Phase 3 Unit Test Audit** — Cross-reference 155 existing frontend unit tests (+ 819 backend) against the new feature specs, classify each test as aligned / misaligned / orphaned, produce a reconciliation punch list for Phase 3 rework | Tasks 2–3 | Task 4 | 0.5 day | Low |

## Success Criteria

- ✅ Every user-facing feature on the overview page and SaaS flows has a numbered spec entry with defined inputs, expected outputs, and at least one edge case
- ✅ Feature inventory is verified against actual codebase files — no spec references a feature that doesn't exist in code, no shipped feature is missing from the inventory
- ✅ Each spec is testable against `CHAIN_PROVIDER=mock` — no spec requires live AI calls or real Stripe sessions to verify
- ✅ Testing architecture map covers all four layers and identifies every coverage gap by feature number
- ✅ Feature numbering is final and stable — Phase 2 Gherkin scenarios and Phase 3 reconciliation can reference spec numbers without ambiguity
- ✅ The `billing_status()` lapsed→free mapping is resolved: spec uses the UI tri-state (`free | pro | lapsed`) as the testable contract, with a note on the OpenAPI divergence

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – Testing layer design and infrastructure decisions
- [Timeline](./timeline.md) – Status tracking