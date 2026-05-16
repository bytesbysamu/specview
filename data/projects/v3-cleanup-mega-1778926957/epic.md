# 🎯 Epic: V3 + Cleanup — State Extraction, Tests, Deletion

## Business Value

spec-doc's frontend carries two near-identical god components (V1: 1,774 lines, V2: 1,087 lines) serving the same application at different routes. State logic is trapped inside component classes, making it untestable in isolation and impossible to extend without risk. Every bug fix or feature touches one of two 1,000+ line files where a single misplaced signal can cascade across the entire UI. For a solo founder shipping across five active projects, this tax compounds — each context switch back into spec-doc starts with re-learning which god component owns which behavior.

Extracting shared state into a standalone service and collapsing two components into one thin shell eliminates ~7,650 lines of duplication and dead code. The resulting architecture — a testable `AppStateService` plus a 30-line shell — means future features (real-data playground mode, new AI operations, additional file types) wire into one service with one test surface. Regressions get caught by service-level unit tests instead of fragile full-component renders.

This is a zero-behavior-change refactor. No user-facing feature ships. The payoff is developer velocity: faster iteration cycles, confident deploys, and a codebase that a single person can reason about in one sitting. Every week the god components survive is a week where spec-doc's feature roadmap moves slower than it should.

## Scope

### What This Epic Covers
- **State extraction** – Move ~40 signals, ~15 computed properties, ~30 methods, and 3 effects from `app-v2.component.ts` into a standalone `AppStateService`, plus extract utility functions and constants into dedicated files
- **V3 shell** – Build a thin component (~30 lines TS) that injects `AppStateService` and delegates all behavior, routed at `/v3` alongside existing V1/V2
- **Test parity** – Migrate the 48 pre-V3 regression tests to the service layer, confirm all 441+ Karma and 34+ E2E tests pass against V3, and verify pixel-identical rendering via screenshot comparison
- **Route cutover and soak** – Promote V3 to `/`, preserve `/v1` as a 1-week escape hatch, then delete V1 and V2 components entirely after soak
- **CSS consolidation** – Remove ~401 lines of duplicated scoped CSS from `landing-pitch`, audit and remove ~200 lines of dead classes from `styles.css`, and extract shared design tokens into a single `tokens.css`

### What This Epic Does NOT Cover
- ❌ **Playground real-data mode** — Future work; requires stable V3 for 2+ weeks before connecting `AppStateService` to playground components
- ❌ **Fixing the 9 skipped E2E tests** — Mock-infrastructure dependent and orthogonal to this refactor
- ❌ **Splitting AppStateService beyond ~400 lines** — Ship as-is; split only when testing or reasoning pain emerges
- ❌ **Landing page redesign** — `landing-pitch` keeps its TS and HTML; only scoped CSS is removed
- ❌ **New features on V3** — This is strictly a zero-behavior-change refactor; feature work waits until deletion is complete

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Extract AppStateService + V3 Shell** — Create `app-state.service.ts` (~400 lines) with all signals, computed, methods, and effects from V2; extract `paragraph-diff.ts` and `nav-sections.ts`; build V3 shell component; add `/v3` route | None | — | 3 hrs | High |
| 2 | **Migrate Tests & Prove Parity** — Move 48 pre-V3 tests to `app-state.service.spec.ts`; run full Karma suite (441+ pass); run E2E against `/v3` (34+ pass); screenshot-compare V2 vs V3 for pixel parity | Task 1 | — | 2 hrs | High |
| 3 | **Route Cutover + 1-Week Soak** — Promote V3 to `/`; redirect `/v2` → `/`; keep `/v1` escape hatch; monitor for regressions over 7 calendar days | Task 2 | — | 1 hr + 7-day wait | High |
| 4 | **Delete V1, V2, and Consolidate CSS** — Remove V1 files (1,774 lines), V2 shell files (279 lines), and routes; delete `landing-pitch` scoped CSS (401 lines) and switch to `ViewEncapsulation.None`; audit and remove dead `styles.css` classes (~200 lines); extract `shared/tokens.css` (~50 lines) | Task 3 | — | 2 hrs | High |

## Success Criteria

- ✅ `AppStateService` is independently injectable and testable — no state logic lives in any component class
- ✅ V3 shell component is under 50 lines of TypeScript
- ✅ V3 is visually identical to V2 — confirmed by screenshot overlay comparison
- ✅ 441+ Karma tests pass with V3 as the production component
- ✅ 34+ E2E scenarios pass against V3 (9 mock-dependent skips acceptable)
- ✅ Zero references to `AppComponent` (V1) or `AppV2Component` remain in the codebase after deletion
- ✅ `styles.css` contains no classes unused by any active component template
- ✅ One `shared/tokens.css` file is the single source for design tokens, imported by both `styles.css` and `landing/style.css`
- ✅ `ng build --configuration production` passes at every phase boundary
- ✅ Net line reduction of ~7,650 lines from pre-session baseline (~11,750 → ~4,600 app code)

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic: god components, untestable state, 4,211 lines of remaining duplication
- [Solution Architecture](./architecture.md) – System design for AppStateService, V3 shell, CSS token extraction
- [Timeline](./timeline.md) – Status tracking across all four tasks including soak period