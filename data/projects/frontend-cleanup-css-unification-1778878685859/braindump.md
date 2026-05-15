# Frontend Cleanup & CSS Unification

## Current state (audited 2026-05-15)

### 3 style files, all with same tokens, not shared
- `landing/style.css` (1,224 lines) — landing page + design playground
- `web-ng/src/styles.css` (1,769 lines) — app (V1 + V2)
- `web/style.css` (621 lines) — DEAD, never referenced anywhere

### Massive TS duplication
- `app.component.ts` (V1): 1,189 lines
- `app-v2.component.ts` (V2): 1,089 lines
- 90% signal/computed overlap — copy-pasted, not shared
- `computeParagraphDiff()` utility duplicated verbatim in both
- `NAV_SECTIONS`, `CONTEXT_FILES` constants duplicated

### CSS waste
- styles.css has 149 classes, only 84 used by V2 (127 unused = 60% waste)
- landing/style.css has 91 classes, 23 shared with styles.css
- `landing-pitch.component.css` (401 lines) redefines design tokens locally with `--lp-*` prefix — could use globals
- 5 V2 sub-component CSS files are effectively empty (3 lines each, just a comment)

### Dead code
- `web/style.css` — 621 lines, pure dead code, never imported
- V1's inline editor toolbar HTML (150+ lines) + related CSS (200+ lines) — replaced by V2 sub-components
- V1 animation triggers (25+ lines) — V2 uses simpler state transitions
- `/v2` route redirects to `/` — dead but intentional backward compat

### Design playground file copies
- `landing/playground.html` manually copied to `web-ng/public/assets/playground.html`
- `landing/style.css` manually copied to `web-ng/public/assets/landing-style.css`
- No sync mechanism — updates to landing/ won't reach the app build

## The cleanup plan

### Phase 1: Dead code removal (30 min)
1. Delete `web/style.css` (621 lines, never referenced)
2. Delete `web/` directory if nothing else references it
3. Remove unused CSS classes from `styles.css` that only V1's template uses (after V1 retirement)

### Phase 2: One shared token file (1 hour)
1. Extract shared design tokens (--ink, --bg, --serif, --sans, --border, --accent, --red + dark mode overrides) into `shared/tokens.css` (~50 lines)
2. `landing/style.css` imports `shared/tokens.css` + adds landing-only classes
3. `web-ng/src/styles.css` imports `shared/tokens.css` + adds app-only classes
4. Delete duplicate token declarations from both files
5. Result: tokens defined once, used everywhere

### Phase 3: Kill landing-pitch component CSS (1 hour)
1. The 401-line `landing-pitch.component.css` redefines everything with `--lp-*` prefixed tokens
2. Switch to ViewEncapsulation.None or use global classes from landing/style.css
3. Remove all `--lp-*` token definitions — use `var(--ink)`, `var(--bg)` etc. directly
4. Target: landing-pitch.component.css → 0 lines (all styles from global)

### Phase 4: TS deduplication (2 hours)
1. Extract shared signals + computed + methods into `app-state.service.ts`:
   - All 40+ signals (projects, activeProject, activeFile, statusMode, etc.)
   - All computed values (sectionCounts, filteredProjects, projectsBySection, etc.)
   - All methods (loadProjects, selectProject, createProject, _runBootstrap, etc.)
   - `computeParagraphDiff()` utility → standalone file
   - `NAV_SECTIONS`, `CONTEXT_FILES` → standalone constants file
2. Both `app.component.ts` and `app-v2.component.ts` inject the service
3. Templates bind to `state.projects()` instead of `this.projects()`
4. Target: app.component.ts drops from 1,189 → ~200 lines (template bindings only)
5. Target: app-v2.component.ts drops from 1,089 → ~150 lines

### Phase 5: Playground sync (30 min)
1. Stop copying playground.html to assets — instead, serve from landing container or use a build script
2. Option A: `DesignPlaygroundComponent` fetches from the landing container URL directly (cross-origin)
3. Option B: Build step that copies `landing/playground.html` → `web-ng/public/assets/` (npm script)
4. Option C: Symlink `web-ng/public/assets/playground.html` → `../../landing/playground.html`
5. Recommended: Option B (npm script in build pipeline)

### Phase 6: V1 retirement (after soak)
1. Route cutover: `/` → V2, `/v1` → V1
2. 1-week soak with zero rollbacks
3. Delete: app.component.html, app.component.ts, app.component.spec.ts
4. Remove /v1 route
5. Remove V1-only CSS classes from styles.css
6. Final target: one app component, one global stylesheet, zero duplication

## Size targets after cleanup

| File | Before | After |
|------|--------|-------|
| styles.css | 1,769 lines | ~1,000 lines (remove V1-only classes) |
| landing/style.css | 1,224 lines | ~800 lines (tokens extracted) |
| app-v2.component.ts | 1,089 lines | ~150 lines (state in service) |
| app.component.ts | 1,189 lines | DELETED |
| landing-pitch.component.css | 401 lines | 0 lines (use global) |
| web/style.css | 621 lines | DELETED |
| Total CSS | 3,614 lines | ~1,850 lines (-49%) |
| Total app TS | 2,278 lines | ~150 lines (-93%) |

## Success criteria
- One set of design tokens defined in one place
- Zero duplicate signal/computed/method definitions
- styles.css has no classes unused by any active component
- `ng build` passes, 155 unit tests pass, E2E passes
- Landing page, design playground, and app all render from the same token source
