# 🔍 V3 + Cleanup — State Extraction, Tests, Deletion — Analysis

## The Problem
`spec-doc` frontend has two near-identical god components (V1: 1,774 lines, V2: 1,336 lines) serving the same app at different routes. State logic is trapped inside component classes, untestable in isolation. 4,576 lines already deleted this session; ~4,211 remain but require a safe extraction-first approach before removal.

## Hard Constraints
- V2 must stay visually and functionally identical throughout Phase 1-2 — refactor, not rewrite
- 1-week soak with `/v1` escape hatch before any deletion
- `ng build` must pass at every phase boundary
- 441 Karma + 34 E2E tests must stay green continuously
- Solo dev — no staged rollout audience, just Sam watching logs

## Open Questions
- **400-line AppStateService** — this is a new god service replacing a god component. Split boundary? (a) ship as-is, split later when pain emerges (b) split now into state + operations (c) group by domain: project-state, ai-state, ui-state
- **"~700 lines dead CSS" vs "~200 removed"** — Phase 3 Step 5 only commits to ~200. Is the remaining ~500 deferred, or was the 700 estimate wrong? Needs a real grep before scoping.
- **shared/tokens.css location** — lives outside `app/` but must be importable by both `styles.css` and `landing/style.css`. Where in the build? `src/shared/`? `src/styles/`? Angular's `styles[]` array?
- **ViewEncapsulation.None on landing-pitch** — leaks all class names globally. Acceptable risk for a scoped-token component, or does it need a class prefix convention?
- **Soak monitoring** — what's the trigger for rollback? Error rate? Manual check? No alerting infra mentioned.

## Dependencies & Sequencing
- Phase 1 → Phase 2 → Phase 3 is strictly serial (stated gate between 2→3)
- Phase 3 has internal 1-week hard delay (soak) between Step 2 and Step 3
- E2E tests assume route `/` — route cutover in Phase 3 Step 1 means E2E base URL changes; tests must not hardcode `/v2` or `/v3`
- `shared/tokens.css` extraction depends on knowing final surviving classes — can't finalize until after CSS audit in the same step

## Explicitly Out of Scope
- **Playground "real data mode"** — brain dump labels it "future"; keep it there. Trigger: after V3 ships and stabilizes for 2+ weeks.
- **Fixing the 9 skipped E2E tests** — they're mock-dependent and orthogonal to this refactor. Trigger: when mock infra gets addressed separately.
- **Further splitting AppStateService** — ship the 400-line version; split only if testing or reasoning about it becomes painful.
- **Landing page redesign** — `landing-pitch` keeps its TS/HTML; only CSS changes. No content or layout work.
- **Any new features on V3** — this is a zero-behavior-change refactor. Feature work waits until deletion is complete.