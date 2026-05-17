# exec-guide summary — Playground 2.0 — Specview Case Study + UX Audit

**Date:** 2026-05-16
**Tasks run:** 5
**Tasks passed:** 5 / 5
**Tests:** passed (frontend: 72/72 specs, backend: 4/4 structural)
**Review:** 3 critical (all fixed), 5 warnings
**PR:** https://github.com/bytesbysamu/specview/pull/70

## Tasks

| Task | Status | Files changed |
|------|--------|---------------|
| Task 1: Narrative Shell + Route Architecture | ✓ complete | pg-case-study.component.ts, app.routes.ts |
| Task 2: Hero + Problem Section | ✓ complete | pg-hero.component.ts, pg-case-study.component.ts |
| Task 3: Pipeline Visualization | ✓ complete | pg-pipeline.component.ts, playground-demo-data.ts, pg-case-study.component.ts |
| Task 4: Narrative Wrappers for Phase 1/2 | ✓ complete | pg-narrative-design.component.ts, pg-narrative-screens.component.ts, pg-narrative-patterns.component.ts, pg-narrative-dark.component.ts, pg-case-study.component.ts |
| Task 5: Journey Map | ✓ complete | pg-journey.component.ts, pg-case-study.component.ts |

## Test results

- Frontend production build: passed (zero errors, 3 pre-existing budget warnings)
- Playground spec tests: 72/72 passed (pg-animations, pg-borders, pg-components-app, pg-components-ui, pg-state-matrix, pg-tokens)
- Backend structural tests: 4/4 passed (no import violations)

## Review findings

### Fixed (critical)
1. **Wrong CSS custom property names in pg-case-study.component.ts** — nav bar used `--color-bg`, `--color-border`, `--color-text-muted`, `--color-text`, `--color-accent` instead of `--bg`, `--border`, `--ink-muted`, `--ink`, `--accent`. Dark mode was completely broken for the nav bar. Fixed by replacing all occurrences.
2. **Missing ChangeDetectionStrategy.OnPush on pg-case-study.component.ts** — all other new components used OnPush but the shell did not. Fixed by adding OnPush.
3. **Duplicate theme toggle state (split-brain)** — pg-case-study and pg-narrative-dark both maintained independent isDark signals. Fixed by adding MutationObserver on data-theme attribute in the dark component to stay in sync with the shell's toggle.

### Acknowledged (warnings)
1. Hardcoded `#fff` in pg-hero.component.ts status bar (intentional contrast color)
2. Hardcoded `rgba(0,0,0,0.02)` hover in pg-narrative-dark.component.ts
3. Undefined `--surface-raised` token in pg-pipeline.component.ts (fallback always used)
4. Fallback hex values use Tailwind palette instead of project tokens in pg-journey.component.ts
5. Narrative wrapper styles duplicated across 3 components (~75 lines each)

## Next steps

- Review and merge PR: https://github.com/bytesbysamu/specview/pull/70
- Manual: verify `/playground` renders narrative arc end-to-end
- Manual: verify dark-mode toggle flips all sections including nav bar
- Manual: verify responsive layout at 375px viewport
- Consider extracting shared narrative wrapper styles to reduce duplication
