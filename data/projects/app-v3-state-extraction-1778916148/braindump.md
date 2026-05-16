# App V3 — State Extraction + Playground Shell

## Prerequisites completed
- Phase 1: Live playground with 6 V2 sub-components + design tokens, borders, animations, state matrix
- Phase 2: 12 remaining component demos ported (masthead, op chips, modal, buttons, interactions, etc.)
- Static design playground DELETED (3,562 lines gone)
- `/playground` is the single source of truth for all UI work

## The approach: Option A foundation + Option B shell

Extract V2's 1,089 lines of state logic into `app-state.service.ts` (Option A), then build a clean V3 shell component that uses the playground's proven composition pattern (Option B) but injects the real state service instead of demo signals.

## Why this works now (it didn't before Phase 2)

Before Phase 2, the playground only composed 6 sub-components with demo data. Now it composes ~10 child components (pg-tokens, pg-borders, pg-animations, pg-state-matrix, pg-components-app, pg-components-ui, pg-landing, pg-interactions) plus the original 6 V2 sub-components. The composition pattern is battle-tested at scale.

The V3 shell follows the exact same pattern — but instead of demo signals, it injects `AppStateService` with real data from ProjectsService, AiService, etc.

## What V2 looks like today (the starting point)

```
app-v2.component.ts (1,089 lines)
├── 40 signals (all duplicated from V1)
├── 15 computed values
├── 30 methods (bootstrap, polling, AI ops, undo/redo)
├── 3 effects (auth watcher, timer, pulse)
└── imports 6 sub-components + landing-pitch + usage-meter
```

V2 template (243 lines) delegates to sub-components via @Input/@Output — this is already clean. The problem is the 1,089-line TS file owning ALL state.

## The extraction

### Step 1: Create app-state.service.ts (~400 lines)
Move from `app-v2.component.ts`:

**Signals (~40):** projects, activeProject, activeFile, activeSection, searchQuery, isDark, updateBanner, knownCount, aiLoading, aiResult, aiLatencyMs, aiError, activeOp, copied, contextContent, contextTitle, showCreateModal, specGenLoading, specGenError, specGenStep, specGenProjectName, specGenJobId, specGenFailedStep, cancelling, accessDenied, epicGuideLoading, epicGuideError, shareUrl, shareCopied, shareLoading, polling, pollingError, billingError, lastSyncAt, specGenStartTime, specGenElapsed, activeOpFile, fileOpState, pulsingSections, undoStack, redoStack, brainstormQuestion

**Computed (~15):** sectionCounts, filteredProjects, projectsBySection, columns, showGrid, showExpanded, mode, currentSpec, parsedContent, parsedAiResult, diffHtmlUnified, expandedTitle, expandedProject, activeFileType, isAdditiveOp, isBraindump, canGenerateSpecs, canGenerateEpicGuide, canRevert, canRedo, sectionLabel, activeStepLabel

**Methods (~30):** loadProjects, checkForUpdates, selectProject, selectFile, closeExpanded, openContext, selectSection, onSearch, toggleTheme, openCreateModal, closeCreateModal, createProject, generateFromBraindump, generateEpicGuide, generateFromBrainstormResult, _runBootstrap, onCancel, onRetry, retryLastOp, toggleOp, runOp, runStyle, applyResult, copyResult, dismissResult, undoVersion, redoVersion, followupBrainstorm, shareProject, logout, navigateToUpgrade

**Effects (3):** auth watcher (starts/stops polling on login/logout), spec gen elapsed timer (100ms), section count pulse (250ms)

**Utilities (extract to separate files):**
- `computeParagraphDiff()` → `utils/paragraph-diff.ts`
- `NAV_SECTIONS`, `CONTEXT_FILES` → `constants/nav-sections.ts`

### Step 2: Build V3 shell (~30 lines TS, ~250 lines HTML)
```typescript
@Component({
  selector: 'app-v3-root',
  standalone: true,
  imports: [
    SectionNavComponent, StatusBarComponent, ProjectGridComponent,
    SidebarV2Component, ReaderPanelComponent, LandingPitchComponent,
    UsageMeterComponent,
  ],
  templateUrl: './app-v3.component.html',
})
export class AppV3Component {
  state = inject(AppStateService);
  auth = inject(AuthService);
  subscription = inject(SubscriptionService);

  readonly sections = NAV_SECTIONS;
  readonly contextFiles = CONTEXT_FILES;
  readonly STYLE_PRESETS = ['Concise', 'Technical', 'Executive', 'Narrative', 'Punchy'];
}
```

Template copies V2's template but binds to `state.x()` instead of `this.x()`. Same sub-components, same layout, same CSS classes from global styles.css.

### Step 3: Route cutover
- `/` → AppV3Component
- `/v1` → AppComponent (escape hatch, 1 week)
- `/v2` → redirect to `/` (or delete)
- `/playground` → LivePlaygroundComponent (unchanged)

### Step 4: Delete V1 + V2 after soak
- Delete app.component.ts (1,189 lines)
- Delete app.component.html (585 lines)
- Delete app-v2.component.ts (1,089 lines)
- Delete app-v2.component.html (243 lines)
- Delete app-v2.component.css (9 lines)
- Remove V1/V2 routes
- **Total deleted: 3,115 lines**

## Connection to the live playground

After V3 ships, the live playground can optionally inject `AppStateService` for a "real data mode":
- Toggle between demo signals and real service
- Playground becomes both a design reference AND a functional test harness
- No code duplication — playground and app share the same state service

The playground's Phase 2 sub-components (pg-components-app, pg-components-ui) can also be imported by V3 if we want to show component demos inline in the app (e.g. a "design system" page for users). But that's V4, not V3.

## Line count impact

| File | Before | After |
|------|--------|-------|
| app.component.ts | 1,189 | DELETED |
| app.component.html | 585 | DELETED |
| app-v2.component.ts | 1,089 | DELETED |
| app-v2.component.html | 243 | DELETED |
| app-v2.component.css | 9 | DELETED |
| app-state.service.ts | 0 | ~400 (new) |
| app-v3.component.ts | 0 | ~30 (new) |
| app-v3.component.html | 0 | ~250 (new) |
| utils/paragraph-diff.ts | 0 | ~30 (new) |
| constants/nav-sections.ts | 0 | ~20 (new) |
| **Net** | **3,115 deleted** | **-2,385 lines** |

## Success criteria
- AppStateService is injectable, testable in isolation, owns all signals/methods
- V3 shell is under 50 lines of TypeScript
- V3 renders identically to V2 (screenshot overlay)
- All 257+ Karma tests pass (not 155 — Phase 1+2 added tests)
- E2E tests pass against V3 route
- `ng build` passes
- V1 and V2 deletable after 1-week soak
- Playground can inject AppStateService for real data mode (future)
