# App V3 — State Extraction + Playground Shell

## The approach: Option A foundation + Option B shell

Extract V2's 1,089 lines of state logic into `app-state.service.ts` (Option A), then build a clean V3 shell component that uses the playground's proven composition pattern (Option B) but injects the real state service instead of demo signals. Best of both: zero re-implementation risk from Option A, cleanest possible shell from Option B.

## Why not pure Option A

Pure Option A splits V2 into service + shell but keeps V2's template and component structure. The shell is still `app-v2.component.ts` with all its baggage — the V2-specific CSS, the design-playground import, the landing-pitch conditional. You end up maintaining V2's decisions forever.

## Why not pure Option B

Pure Option B rewrites the 30 methods from scratch. The bootstrap polling loop, retry with failed-step tracking, AI text ops with undo/redo, cooperative cancellation — these took weeks to get right across multiple PRs. Rewriting them risks subtle regressions in edge cases that are hard to test.

## The hybrid

1. **Extract state service (Option A, zero risk):** Move all 40 signals, 15 computed values, 30 methods, 3 effects, and utility functions from `app-v2.component.ts` → `app-state.service.ts`. The service is injectable, testable in isolation, and owns all business logic. V2 keeps working during extraction (inject service, change `this.x` to `state.x`).

2. **Build V3 shell from playground pattern (Option B, clean):** Create `app-v3.component.ts` modeled after `live-playground.component.ts` (181 lines). Same template structure — delegates to sub-components via `@Input`/`@Output`. But instead of demo signals, inject `AppStateService` and bind to real signals. The template is essentially live-playground.component.html with real data bindings.

3. **V3 shell is ~150 lines** because it owns zero state — just injects the service and wires template bindings. The sub-components are already built and proven. The state service handles all logic.

## What goes into app-state.service.ts

### Signals (~40)
projects, activeProject, activeFile, activeSection, searchQuery, isDark, updateBanner, knownCount, aiLoading, aiResult, aiLatencyMs, aiError, activeOp, copied, contextContent, contextTitle, showCreateModal, specGenLoading, specGenError, specGenStep, specGenProjectName, specGenJobId, specGenFailedStep, cancelling, accessDenied, epicGuideLoading, epicGuideError, shareUrl, shareCopied, shareLoading, polling, pollingError, billingError, lastSyncAt, specGenStartTime, specGenElapsed, activeOpFile, fileOpState, pulsingSections, undoStack, redoStack, brainstormQuestion

### Computed (~15)
sectionCounts, filteredProjects, projectsBySection, columns, showGrid, showExpanded, mode, currentSpec, parsedContent, parsedAiResult, diffHtmlUnified, expandedTitle, expandedProject, activeFileType, isAdditiveOp, isBraindump, canGenerateSpecs, canGenerateEpicGuide, canRevert, canRedo, sectionLabel, activeStepLabel

### Methods (~30)
loadProjects, checkForUpdates, selectProject, selectFile, closeExpanded, openContext, selectSection, onSearch, toggleTheme, openCreateModal, closeCreateModal, createProject, generateFromBraindump, generateEpicGuide, generateFromBrainstormResult, _runBootstrap (polling loop), onCancel, onRetry, retryLastOp, toggleOp, runOp, runStyle, applyResult, copyResult, dismissResult, undoVersion, redoVersion, followupBrainstorm, shareProject, logout, navigateToUpgrade

### Effects (3)
- Auth watcher: starts/stops polling on login/logout
- Spec gen elapsed timer: 100ms interval during active generation
- Section count pulse: 250ms animation trigger on count change

### Utilities (extract to separate files)
- `computeParagraphDiff()` → `utils/paragraph-diff.ts`
- `NAV_SECTIONS`, `CONTEXT_FILES` → `constants/nav-sections.ts`

## What app-v3.component.ts looks like

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

  // Template delegates everything to state service:
  // [projects]="state.projects()"
  // [activeSection]="state.activeSection()"
  // (sectionSelected)="state.selectSection($event)"
  // etc.
}
```

~30 lines of component code. The template is ~250 lines (same as V2's, but binding to `state.x()` instead of `this.x()`).

## Migration sequence

### Step 1: Extract app-state.service.ts (2 hours)
- Create `web-ng/src/app/services/app-state.service.ts`
- Move all signals, computed, methods, effects from `app-v2.component.ts`
- Inject services (ProjectsService, AiService, AuthService, SubscriptionService, DomSanitizer, Router) in the state service constructor
- V2 component injects AppStateService, changes all `this.x` to `state.x` in template
- V2 keeps working — test by visiting `/v2`

### Step 2: Build V3 shell (1 hour)
- Create `app-v3.component.ts` (~30 lines)
- Copy `app-v2.component.html` → `app-v3.component.html`
- Replace all `this.x` with `state.x` bindings (or keep as-is if V2 template already uses service)
- Add route at `/v3`
- Verify same rendering as V2

### Step 3: Route cutover (30 min)
- `/` → AppV3Component
- `/v1` → AppComponent (V1 escape hatch)
- `/v2` → AppV2Component (V2 escape hatch, temporary)
- Test all three routes

### Step 4: Delete V1 + V2 after soak (30 min)
- Delete app.component.ts (1,189 lines)
- Delete app.component.html (585 lines)
- Delete app-v2.component.ts (1,089 lines — now just a thin shell, but V3 replaces it)
- Delete app-v2.component.html (243 lines)
- Delete app-v2.component.css (9 lines)
- Remove V1/V2 routes
- **Total deleted: 3,115 lines**

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
| **Net change** | **3,115** | **-2,435 lines** |

## Success criteria
- AppStateService is injectable, testable, owns all signals/methods
- V3 shell is under 50 lines of TypeScript
- V3 renders identically to V2 (screenshot overlay test)
- All 155+ Karma tests pass
- `ng build` passes
- V1 and V2 can be deleted after 1-week soak
- The live playground can optionally inject AppStateService for "real data mode" in the future
