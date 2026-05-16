# V3 + Cleanup — State Extraction, Tests, Deletion

Meta-braindump merging three overlapping plans into one sequenced execution. Source braindumps preserved as historical reference: "App V3 — State Extraction," "Final Cleanup — Delete 7,456 Lines," "Frontend Cleanup & CSS Unification."

## Fact-checked current state (2026-05-16)

### Already done this session
- web/ directory DELETED (style.css 621 + app.js 323 + index.html 70 = 1,014 lines)
- design-playground.component.ts DELETED (34 lines)
- public/assets/playground.html DELETED (2,304 lines)
- public/assets/landing-style.css DELETED (1,224 lines)
- V2 is production at `/`, V1 escape hatch at `/v1`
- Live playground at `/playground` with design system sections
- 441 Karma tests passing, 43 E2E scenarios (34 pass, 9 skip)
- **Total already deleted: 4,576 lines**

### What remains (verified line counts)
- app.component.ts: 1,189 lines (V1 monolith, live at /v1)
- app.component.html: 585 lines (V1 template)
- app-v2.component.ts: 1,087 lines (90% duplicate of V1, production at /)
- app-v2.component.html: 240 lines (delegates to sub-components)
- app-v2.component.css: 9 lines (duplicates global)
- landing-pitch.component.css: 401 lines (scoped --lp-* tokens duplicating globals)
- styles.css: 1,769 lines (127 classes unused by V2 = ~700 lines of dead CSS)
- **Total remaining deletable: ~4,211 lines**

### What survives untouched
- 5 V2 sub-components (672 lines total): project-grid, reader-panel, sidebar-v2, status-bar, section-nav
- 8 playground components (pg-tokens, pg-borders, pg-animations, pg-state-matrix, pg-components-app, pg-components-ui, live-playground, playground-demo-data)
- 7 services (568 lines total): projects, auth, ai, subscription, token-lifecycle, section-taxonomy, project-teaser
- Other components: login, signup, upgrade, usage-meter, public-spec, word-count.pipe
- landing-pitch.component.ts + .html (80 lines — just the CSS gets killed)
- Global styles.css (trimmed, not deleted)
- landing/style.css (unchanged)

---

## Phase 1: State Extraction (~3 hours)

### Goal
Extract V2's 1,087-line god component into a testable service + thin shell. V2 keeps working throughout — this is a refactor, not a rewrite.

### Step 1: Create app-state.service.ts (~400 lines)
Move from app-v2.component.ts:

**Signals (~40):** projects, activeProject, activeFile, activeSection, searchQuery, isDark, updateBanner, knownCount, aiLoading, aiResult, aiLatencyMs, aiError, activeOp, copied, contextContent, contextTitle, showCreateModal, specGenLoading, specGenError, specGenStep, specGenProjectName, specGenJobId, specGenFailedStep, cancelling, accessDenied, epicGuideLoading, epicGuideError, shareUrl, shareCopied, shareLoading, polling, pollingError, billingError, lastSyncAt, specGenStartTime, specGenElapsed, activeOpFile, fileOpState, pulsingSections, undoStack, redoStack, brainstormQuestion

**Computed (~15):** sectionCounts, filteredProjects, projectsBySection, columns, showGrid, showExpanded, mode, currentSpec, parsedContent, parsedAiResult, diffHtmlUnified, expandedTitle, expandedProject, activeFileType, isAdditiveOp, isBraindump, canGenerateSpecs, canGenerateEpicGuide, canRevert, canRedo, sectionLabel, activeStepLabel

**Methods (~30):** loadProjects, checkForUpdates, selectProject, selectFile, closeExpanded, openContext, selectSection, onSearch, toggleTheme, openCreateModal, closeCreateModal, createProject, generateFromBraindump, generateEpicGuide, generateFromBrainstormResult, _runBootstrap, onCancel, onRetry, retryLastOp, toggleOp, runOp, runStyle, applyResult, copyResult, dismissResult, undoVersion, redoVersion, followupBrainstorm, shareProject, logout, navigateToUpgrade

**Effects (3):** auth watcher, spec gen elapsed timer, section count pulse

### Step 2: Extract utilities
- computeParagraphDiff() → utils/paragraph-diff.ts (~30 lines)
- NAV_SECTIONS, CONTEXT_FILES → constants/nav-sections.ts (~20 lines)

### Step 3: Build V3 shell (~30 lines TS, ~250 lines HTML)
```typescript
export class AppV3Component {
  state = inject(AppStateService);
  auth = inject(AuthService);
  subscription = inject(SubscriptionService);
  readonly sections = NAV_SECTIONS;
  readonly contextFiles = CONTEXT_FILES;
  readonly STYLE_PRESETS = ['Concise', 'Technical', 'Executive', 'Narrative', 'Punchy'];
}
```
Template = V2 template with `state.x()` bindings. Same sub-components, same CSS.

### Step 4: Route V3 at /v3
Add route, add to FULL_PAGE_ROUTES. V1 and V2 stay live.

### Phase 1 line impact
- Deleted: 0 (refactor only, V2 still exists)
- Added: ~480 (service + shell + utils + constants)
- V2 app-v2.component.ts: 1,087 → ~30 (inject service, wire template)
- Net: -577 lines (V2 shrinks, new files added)

---

## Phase 2: All Tests Green on V3 (~2 hours)

### Goal
Prove V3 works identically to V2 before any deletion. Every test — unit and E2E — passes against V3.

### Step 1: Migrate pre-V3 tests
The 48 app-v2 regression tests (signals, computed, methods, polling, bootstrap) were written against `component.x()`. Copy to `app-state.service.spec.ts` and change to `service.x()`. Mechanical find-replace.

### Step 2: Run Karma against V3
All 441 tests must pass. The V2 sub-component tests don't change (they test @Input/@Output, not the shell). The app-v2 tests get split: 48 pre-V3 tests move to service spec, 15 basic behavior tests stay on V3 shell.

### Step 3: Run E2E against /v3
```bash
E2E_BASE_URL=http://localhost:8095 python -m pytest e2e/test_overview.py -v
```
The 43 E2E scenarios target DOM selectors (`[data-test]`) that are the same in V2 and V3 (same template, same sub-components). Should pass without changes. Fix any selector mismatches.

### Step 4: Screenshot comparison
Playwright screenshot of / (V2) vs /v3 — overlay at 50% opacity. Must be pixel-identical.

### Phase 2 gate
- 441+ Karma tests pass
- 34+ E2E tests pass (9 skip for mock-dependent)
- Screenshot match confirms visual parity
- Only proceed to Phase 3 after this gate passes

---

## Phase 3: Delete V1 + V2 + CSS Cleanup (~2 hours + 1-week soak)

### Step 1: Route cutover
- `/` → AppV3Component
- `/v1` → AppComponent (escape hatch)
- `/v2` → redirect to `/`

### Step 2: 1-week soak
Monitor for rollbacks. If any issue, /v1 is live.

### Step 3: Delete V1 (after soak)
- app.component.ts (1,189 lines)
- app.component.html (585 lines)
- app.component.spec.ts (existing 5 tests — superseded by service spec)
- Remove /v1 route
**Subtotal: -1,774 lines**

### Step 4: Delete V2 shell (after soak)
- app-v2.component.ts (now ~30 lines, but V3 replaces it)
- app-v2.component.html (240 lines)
- app-v2.component.css (9 lines)
- Remove /v2 redirect
**Subtotal: -279 lines**

### Step 5: CSS consolidation
- landing-pitch.component.css (401 lines) → switch to ViewEncapsulation.None, use global classes, delete scoped CSS
- Audit styles.css: grep every class against V3 template + sub-component templates. Remove classes with zero references (~200 lines estimated)
- Extract shared tokens (--ink, --bg, --serif etc.) into shared/tokens.css (~50 lines), imported by both styles.css and landing/style.css
**Subtotal: ~-601 lines + 50 added = -551 net**

### Phase 3 line impact
- Deleted: 2,604 lines
- Added: ~50 lines (tokens.css)
- Net: -2,554 lines

---

## KPI Scorecard

| Phase | Lines deleted | Lines added | Net | Running total |
|-------|-------------|-------------|-----|---------------|
| Already done (this session) | 4,576 | 0 | -4,576 | -4,576 |
| Phase 1: State extraction | 1,057 (V2 shrink) | 480 | -577 | -5,153 |
| Phase 2: Tests green | 0 | ~50 (service spec) | +50 | -5,103 |
| Phase 3: Delete V1+V2+CSS | 2,604 | 50 | -2,554 | -7,657 |
| **Total** | **8,237** | **580** | **-7,657** | |

## Final architecture (after all 3 phases)

```
web-ng/src/app/
├── app-v3.component.ts           (~30 lines — thin shell)
├── app-v3.component.html         (~250 lines — same as V2 template)
├── app.routes.ts                 (routes: /, /playground, /signup, /upgrade, /s/:slug)
├── services/
│   ├── app-state.service.ts      (~400 lines — all shared state + logic)
│   ├── app-state.service.spec.ts (~200 lines — migrated from V2 pre-tests)
│   ├── projects.service.ts       (157 lines)
│   ├── auth.service.ts           (37 lines)
│   ├── ai.service.ts             (63 lines)
│   ├── subscription.service.ts   (55 lines)
│   ├── token-lifecycle.service.ts (103 lines)
│   ├── section-taxonomy.service.ts (46 lines)
│   └── project-teaser.ts         (107 lines)
├── utils/paragraph-diff.ts       (~30 lines)
├── constants/nav-sections.ts     (~20 lines)
├── 5 sub-components              (672 lines — unchanged)
├── 8 playground components       (~2,400 lines — unchanged)
├── landing-pitch.component.*     (~80 lines — no scoped CSS)
├── other pages                   (login, signup, upgrade, public-spec)
└── styles.css                    (~1,100 lines — trimmed)

shared/tokens.css                  (~50 lines — imported by both styles.css and landing/style.css)
```

Total app code: ~4,600 lines (down from ~11,750 before this session)
Total CSS: ~2,400 lines (down from ~3,600)

## Playground connection (future)
After V3, the live playground can inject AppStateService for "real data mode" — toggle between demo signals and real service. Same state service, no duplication.

## Success criteria
- AppStateService injectable, testable, owns all state
- V3 shell under 50 lines of TS
- V3 visually identical to V2 (screenshot match)
- 441+ Karma tests pass on V3
- 34+ E2E tests pass on V3
- V1 and V2 fully deleted after soak (zero references remaining)
- styles.css has no classes unused by any active component
- One shared tokens.css imported by both app and landing
- `ng build` passes at every phase boundary
