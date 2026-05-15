# V1 Retirement & Full Migration Plan

### Phase 1: Visual parity (do first)
1. Empty all 5 V2 component CSS files — let global styles.css render everything
2. Screenshot compare V1 vs V2 — must be pixel-identical on grid, cards, spacing
3. Fix any remaining visual diffs (card title font-size: 17px not 18px, etc.)
4. Add panel slide animation to V2 expanded panel (@panelEnter from V1)
5. Add WordCountPipe to V2 reader panel

### Phase 2: Test migration
1. Run all 155 Karma unit tests — they test V1 components, need to verify V2 doesn't break them
2. Run E2E tests against /v2 route — fix any selector/DOM mismatches
3. Add unit tests for the 5 V2 sub-components (project-grid, reader-panel, sidebar-v2, status-bar, section-nav)
4. Verify V2's AppV2Component has equivalent test coverage to V1's AppComponent

### Phase 3: Route cutover
1. Add /v2 route as an alias — keep / pointing to V1
2. Manual QA on /v2 — full user flow: login, browse, search, create project, generate specs, AI ops, upgrade
3. Swap routes: / points to AppV2Component, /v1 points to old AppComponent (escape hatch)
4. Monitor for issues — if something breaks, /v1 is still live

### Phase 4: Dead code cleanup
1. Delete V1 files after 1 week with no rollback needed:
   - app.component.html (585 lines — replaced by V2 sub-components)
   - app.component.css if V2 doesn't reference it (check first)
   - app.component.ts stays — V2 still uses the same TS or a copy of it
2. Remove /v1 escape hatch route
3. Remove any V1-only CSS classes from styles.css that V2 components don't use
4. Remove duplicate imports/exports
5. Update CLAUDE.md to reflect new component structure

### What NOT to delete
- styles.css — this IS the design system, used by V2
- All services (auth, projects, ai, subscription, token-lifecycle) — shared
- app.config.ts — shared bootstrap config
- app.routes.ts — updated but not deleted
- Landing pitch component, design playground component — V2-only additions, keep

### Risk mitigation
- Keep V1 as /v1 escape hatch for at least 1 week after cutover
- Run full E2E suite against both / and /v1 during transition
- If any E2E test fails on / that passes on /v1, the V2 component has a bug — fix before proceeding
- Never delete app.component.ts until all signals/methods are confirmed working in V2

### Timeline
- Phase 1: 1 day (CSS only)
- Phase 2: 2 days (test migration)
- Phase 3: 0.5 day (route swap)
- Phase 4: 0.5 day (cleanup, 1 week after Phase 3)
- Total: 4 days + 1 week buffer
