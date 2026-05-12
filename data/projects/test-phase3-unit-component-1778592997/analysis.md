# 🔍 Test Phase 3: Unit & Component Tests — Analysis

## The Problem
The Angular frontend has 4 unit tests covering one component. Backend has meaningful coverage; frontend has near-zero. Refactors and feature work can silently break pure logic (taxonomy classification, teaser generation, content parsing) with no safety net. This phase adds Karma/Jasmine tests for all non-DOM logic to close that gap.

## Hard Constraints
- Karma/Jasmine on Angular — already configured, `ChromeHeadlessCI` ready
- No DOM or template tests — UX is actively churning
- Solo dev — test suite must stay fast and low-maintenance or it gets abandoned
- CI must gate PRs — tests that don't block merges rot immediately

## Open Questions
- **What does "coverage parity with backend" mean concretely?** Line % target, no-untested-public-method rule, or branch coverage on pure logic? Pick one metric and a number before writing tests.
- **How is the "scan all services" scoped?** The brain dump specifies ~45 test cases for taxonomy + teaser, then adds an open-ended "also scan everything else." AiService parsing and AuthService token logic alone could double the phase. Run coverage on existing tests first to produce the gap report — that *is* the scan.
- **Does CI enforce a coverage ratchet or just upload artifacts?** The YAML uploads coverage but never fails on regression. Without a ratchet, Phase 4+ erodes what Phase 3 builds.
- **Signals: test the extracted function or the signal itself?** Computed signals that derive state are called out but no test cases are listed. Decide: extract computation into pure functions and test those, or test signals via `TestBed`/`createEnvironmentInjector`.

## Dependencies & Sequencing
- **Step 0 (missing):** The service scan must happen *before* test writing, not after. It's currently buried as "additional" but it determines the real scope of this phase. Promote it.
- **Mock factories → builder pattern:** At 2 mocks the current pattern is fine. The scan will likely surface 4-6 more services. Decide on centralized `testing/` directory vs. co-location *before* mock #3.
- **CI workflow:** Depends on repo having GitHub Actions enabled and `ChromeHeadless` available in the runner image. Verify before assuming the YAML just works.

## Explicitly Out of Scope
- **Template/component rendering tests** — UX churning; re-scope when component PRs drop below 2/week
- **Property-based testing (fast-check)** — interesting for `firstNonHeadingSentence` edge cases but adds a dependency and learning curve; re-scope after base suite exists
- **Refactoring `sectionFor` or `projectTeaser` before testing** — test current behavior first, refactor under coverage later
- **Integration, E2E, visual regression, feature docs** — later phases per the sequencing ladder

---
> **Cross-references:** [Solution Architecture](./architecture.md) · [Epic](./epic.md) · [Implementation Guide](./implementation-guide.md)