# Final Cleanup — Delete 7,456 Lines

## KPI: lines deleted

Target: 7,456 lines of dead, duplicate, or replaceable code removed from the codebase.

## Current decomposition status

The app has been decomposed across 3 versions over this session:

### V1: app.component (1,774 lines) — the monolith
- app.component.ts: 1,189 lines — ALL signals, methods, effects, polling, AI ops
- app.component.html: 585 lines — inline masthead, nav, status bar, search, grid, expanded panel, modal
- Status: LIVE at `/`, fully working, newspaper design
- Problem: monolithic, untestable in isolation, all logic in one file

### V2: app-v2.component (1,341 lines) — decomposed but duplicate
- app-v2.component.ts: 1,089 lines — 90% copy-paste from V1
- app-v2.component.html: 243 lines — delegates to 5 sub-components
- 5 sub-components: project-grid (120), reader-panel (201), sidebar-v2 (209), status-bar (89), section-nav (53) = 672 lines total
- Status: LIVE at `/v2`, working, same newspaper design after CSS fix
- Problem: app-v2.component.ts is 1,089 lines of DUPLICATED logic from V1

### Live Playground (1,173 lines) — demo composition
- live-playground.component: 181 + 196 + 112 = 489 lines
- playground-demo-data.ts: 169 lines
- Status: LIVE at `/playground`, works without auth
- Problem: none — this is the target architecture

## What to delete

| File | Lines | Why deletable |
|------|-------|---------------|
| app.component.ts | 1,189 | V2 replaces it after route cutover |
| app.component.html | 585 | V2 sub-components replace it |
| app-v2.component.ts | 1,089 | Extract shared state to service, shell drops to ~150 lines |
| app-v2.component.css | 9 | Duplicates global styles |
| design-playground.component.ts | 34 | Replaced by live-playground |
| landing-pitch.component.css | 401 | Can use global styles instead of scoped --lp-* tokens |
| web/style.css | 621 | Dead — never referenced anywhere |
| public/assets/playground.html | 2,304 | Static copy of landing/playground.html, replaced by live playground |
| public/assets/landing-style.css | 1,224 | Static copy of landing/style.css, only used by dead design-playground |
| **TOTAL** | **7,456** | |

## The plan

### Phase 1: Kill dead code (instant, zero risk)
Delete files that nothing references:
- `web/style.css` (621 lines)
- `web-ng/public/assets/playground.html` (2,304 lines)
- `web-ng/public/assets/landing-style.css` (1,224 lines)
- `design-playground.component.ts` (34 lines)
- Remove `DesignPlaygroundComponent` import from `app-v2.component.ts`
- Remove `<app-design-playground />` from `app-v2.component.html`
**Subtotal: 4,183 lines deleted**

### Phase 2: Promote V2 sub-components to main app
The live playground proves the sub-components work. Now make them the production app:
1. Extract shared state from app-v2.component.ts → `app-state.service.ts` (~400 lines)
2. app-v2.component.ts becomes a thin shell injecting the state service (~150 lines)
3. That's a net reduction of 939 lines (1,089 → 150)
**Subtotal: 939 lines deleted**

### Phase 3: Route cutover + V1 deletion
1. `/` → AppV2Component (thin shell + sub-components)
2. `/v1` → escape hatch for 1 week
3. After soak: delete app.component.ts (1,189) + app.component.html (585)
**Subtotal: 1,774 lines deleted**

### Phase 4: CSS consolidation
1. landing-pitch.component.css (401 lines) → use global classes, delete scoped CSS
2. app-v2.component.css (9 lines) → merge into global or delete
3. Audit styles.css for V1-only classes → delete unused (~200 lines estimated)
**Subtotal: ~610 lines deleted**

## Future: Port /playground to standalone HTML
After cleanup, export the live playground as a standalone HTML file:
- Extract the rendered HTML + demo data into a single self-contained file
- Reference landing/style.css for design tokens
- Use same mock data as playground-demo-data.ts but as inline JSON
- Serve from landing container at `/playground.html`
- This becomes the new design reference AND the product demo page
- The Angular live-playground stays as the development version

## Score card

| Phase | Lines deleted | Running total |
|-------|-------------|---------------|
| Phase 1: Dead code | 4,183 | 4,183 |
| Phase 2: TS dedup | 939 | 5,122 |
| Phase 3: V1 retirement | 1,774 | 6,896 |
| Phase 4: CSS consolidation | ~610 | ~7,506 |
| **Total** | **~7,506** | Exceeds 7,456 target |

## What survives (the final architecture)

```
web-ng/src/app/
├── app-v2.component.ts          (~150 lines — thin shell)
├── app-v2.component.html        (243 lines — delegates to sub-components)
├── services/
│   ├── app-state.service.ts     (~400 lines — all shared signals + methods)
│   ├── projects.service.ts      (157 lines)
│   ├── auth.service.ts          (37 lines)
│   ├── ai.service.ts            (63 lines)
│   └── ...
├── project-grid.component.*     (120 lines)
├── reader-panel.component.*     (201 lines)
├── sidebar-v2.component.*       (209 lines)
├── status-bar.component.*       (89 lines)
├── section-nav.component.*      (53 lines)
├── landing-pitch.component.*    (~80 lines, no scoped CSS)
├── live-playground.component.*  (489 lines)
└── playground-demo-data.ts      (169 lines)
```

Total app: ~2,260 lines (down from ~4,900 before cleanup)
CSS: ~1,600 lines (down from ~3,600)
