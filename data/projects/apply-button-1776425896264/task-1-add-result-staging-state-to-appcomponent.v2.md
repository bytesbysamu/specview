Now I have the full codebase picture. Here's the implementation guide:

# Task 1: Add result staging state to AppComponent

**Purpose**: Introduce two component-level properties (`stagedOutput`, `preApplyContent`) and a reset method that later tasks will wire into the AI operation flow and Apply/Undo cycle.

**Effort**: 2h

**Dependencies**: None

**Parallel With**: Task 2 (TextOutputComponent)

**Blocks**: Task 3 (wire operations to staging), Task 4 (apply action), Task 5 (undo apply)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task lays the state foundation for the Apply Button capability. Today, `AppComponent.applyResult()` (line 837) immediately pushes AI output into the editor via `replaceSelection()`. The Apply Button epic splits this into two steps: stage the result, then let the user explicitly apply it. Task 1 adds the two properties that hold that staged state — `stagedOutput` (the AI result waiting for the user to tap Apply) and `preApplyContent` (a snapshot of editor content before Apply, enabling undo). It also adds `clearStagedOutput()`, which resets both when the user switches files, matching the existing `historyStack = []` reset in `onSpecSelect()`. No behavior changes — this is pure state scaffolding that Tasks 3–5 will consume.

**Trade-offs considered**:
- **Signals instead of plain properties** — rejected because every other piece of component state in `AppComponent` (`content`, `selectedText`, `loading`, `historyStack`, `baseSpecContent`) uses plain properties. Introducing signals for two strings would break the consistency pattern and add noise for zero current benefit.
- **Dedicated service / store** — rejected because the architecture doc explicitly calls out "No service, no signal, just properties matching the existing pattern." Two strings don't warrant a service.
- **Chosen: plain properties + reset method** — preferred because it matches the existing property pattern verbatim, is trivially testable, and keeps the diff minimal for later tasks to build on.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                          # Flag any unrelated M/?? entries
git diff HEAD -- src/app/app.component.ts           # Confirm target file is clean
npm run build 2>&1 | tail -5                        # Confirm project compiles; record result
node --test server.test.js 2>&1 | tail -3           # Record server test baseline
```

**If working tree is dirty on `src/app/app.component.ts`**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: build succeeds; server tests N/N passing. (No Angular component tests exist yet — `src/**/*.spec.ts` is empty.)

---

## 3. Files

### To Create (new)
- `src/app/app.component.spec.ts` **(new)** — first Angular component test; covers staging state initialization and `clearStagedOutput()` behavior. Requires `karma.conf.js` **(new)** at project root if `ng test` fails without it.

### To Modify (cite CODEBASE CONTEXT)
- `src/app/app.component.ts` — add `stagedOutput` + `preApplyContent` properties after `historyStack` (line 264); add `clearStagedOutput()` method; call it in `onSpecSelect()` (line 369)

### To Leave Alone
- `src/app/components/operation-bar/operation-bar.component.ts` — Task 5 modifies this; not touched here
- `src/app/components/output-panel/output-panel.component.ts` — unrelated SSE streaming panel; the new TextOutputComponent (Task 2) is separate
- `src/app/services/ai.service.ts` — no service changes for state scaffolding
- `server.js` — backend unchanged

---

## 4. Implementation Steps

### Step 1: Add staging properties to AppComponent

**Action**: Add `stagedOutput` and `preApplyContent` as empty-string properties after the existing `historyStack` declaration.

**File**: `src/app/app.component.ts` (line 264, after `historyStack: string[] = [];`)

**Pattern**:
```typescript
  // Undo history stack for iterate
  historyStack: string[] = [];

  // Result staging: holds AI output until user taps Apply
  stagedOutput = '';
  // Pre-apply snapshot: editor content before last Apply, for undo
  preApplyContent = '';
```

**Verify**: `npm run build 2>&1 | tail -5` — expect clean compilation, zero errors.

### Step 2: Add `clearStagedOutput()` method

**Action**: Add a method that resets both staging properties. Place it near the existing state-management methods (after `getActiveProjectName()` around line 574, before the getter `isTimelineFile`).

**File**: `src/app/app.component.ts`

**Pattern**:
```typescript
  clearStagedOutput(): void {
    this.stagedOutput = '';
    this.preApplyContent = '';
  }
```

**Verify**: `npm run build 2>&1 | tail -5` — expect clean compilation.

### Step 3: Call `clearStagedOutput()` in `onSpecSelect()`

**Action**: Add `this.clearStagedOutput();` on the line after `this.historyStack = [];` (line 369) inside `onSpecSelect()`.

**File**: `src/app/app.component.ts` (line 369)

**Pattern**:
```typescript
  onSpecSelect(event: { project: Project; spec: SpecFile }): void {
    this.activeProjectId = event.project.id;
    this.currentFile = event.spec.filename;
    // Clear history stack when switching files
    this.historyStack = [];
    this.clearStagedOutput();
    // ... rest of method unchanged
```

**Verify**: `npm run build 2>&1 | tail -5` — expect clean compilation. Then manually confirm `onSpecSelect` logic is intact: `grep -n 'clearStagedOutput' src/app/app.component.ts` should show exactly two hits (the definition and the call).

### Step 4: Create `karma.conf.js` (if needed)

**Action**: Run `npx ng test --no-watch` to see if Angular's Karma runner works without a root `karma.conf.js`. If it fails with a "missing config" error, generate the default:

```bash
npx ng generate config karma
```

If `ng generate config karma` is not available in Angular 19, create `karma.conf.js` at the project root manually.

**File**: `karma.conf.js` **(new, only if needed)**

**Pattern**:
```javascript
module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('karma-coverage'),
      require('@angular-devkit/build-angular/plugins/karma')
    ],
    client: {
      jasmine: {},
      clearContext: false
    },
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/spec-doc'),
      subdir: '.',
      reporters: [{ type: 'text-summary' }]
    },
    reporters: ['progress', 'kjhtml'],
    browsers: ['ChromeHeadless'],
    restartOnFileChange: true
  });
};
```

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless 2>&1 | tail -10` — expect Karma to start (may show 0 specs if no test file yet, or succeed with the test from Step 5).

### Step 5: Add component test for staging state

**Action**: Create the first Angular component test file for `AppComponent`. Use TestBed with mocked services. Test the three state behaviors: initialization, `clearStagedOutput()`, and `onSpecSelect()` clearing staged output.

**File**: `src/app/app.component.spec.ts` **(new)**

**Pattern**: See Section 5 (Tests) below for the complete file.

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless 2>&1 | tail -10` — expect 3/3 passing.

---

## 5. Tests

Framework: Jasmine + Karma (configured in `angular.json` test target + `tsconfig.spec.json`). No existing `.spec.ts` files — this is the first.

```typescript
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { AppComponent } from './app.component';
import { AiService } from './services/ai.service';
import { ProjectsService } from './services/projects.service';
import { ImplementationService } from './services/implementation.service';
import { TimelineParserService } from './services/timeline-parser.service';
import { of } from 'rxjs';

describe('AppComponent — staging state', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent, HttpClientTestingModule],
      providers: [
        { provide: AiService, useValue: {} },
        {
          provide: ProjectsService,
          useValue: { list: () => of([]) }
        },
        { provide: ImplementationService, useValue: {} },
        { provide: TimelineParserService, useValue: {} }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
  });

  it('initialProperties_stagedOutputAndPreApplyContentAreEmptyStrings', () => {
    expect(component.stagedOutput).toBe('');
    expect(component.preApplyContent).toBe('');
  });

  it('clearStagedOutput_resetsBothProperties', () => {
    component.stagedOutput = 'some AI result';
    component.preApplyContent = 'previous editor content';

    component.clearStagedOutput();

    expect(component.stagedOutput).toBe('');
    expect(component.preApplyContent).toBe('');
  });

  it('onSpecSelect_clearsStagedOutput', () => {
    component.stagedOutput = 'stale result';
    component.preApplyContent = 'stale snapshot';
    component.historyStack = ['old content'];

    const mockProject = { id: 'test', name: 'Test', expanded: false, specs: [] };
    const mockSpec = { id: 'spec-1', label: 'Test', filename: 'test.md', content: '# Test' };

    component.onSpecSelect({ project: mockProject, spec: mockSpec });

    expect(component.stagedOutput).toBe('');
    expect(component.preApplyContent).toBe('');
    expect(component.historyStack).toEqual([]);
  });
});
```

---

## 6. Commit Plan

One commit — this is a single logical unit (state scaffolding):

1. `feat(app): add result staging state to AppComponent` — `src/app/app.component.ts`, `src/app/app.component.spec.ts`, optionally `karma.conf.js`: adds `stagedOutput`, `preApplyContent` properties, `clearStagedOutput()` method, clears on file switch, first component test

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npm run build 2>&1 | tail -5                                          # Compiles clean
npx ng test --no-watch --browsers=ChromeHeadless 2>&1 | tail -10      # 3/3 passing
node --test server.test.js 2>&1 | tail -3                             # Server tests unchanged
```

**Expected delta**: 0 → 3 Angular component tests passing. Zero server tests broken. Build still clean.

---

## 8. Rollback

- **Per-step**: each step is additive (new properties, new method, new call, new file). Reverting the single commit undoes all: `git revert <sha>`.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch, or delete the branch entirely.

---

## 9. Deviations Allowed

- **`karma.conf.js` not needed** → if `npx ng test` works without it (Angular 19 may use defaults), skip Step 4 entirely. Note in commit body.
- **`HttpClientTestingModule` import path differs** → Angular 19 may use `provideHttpClientTesting()` instead. Match whatever the installed Angular version exports. Translate silently but note in commit body.
- **TestBed compilation errors from child component imports** → `AppComponent` imports many child components inline. If TestBed balks at unresolved dependencies in those children, add `schemas: [CUSTOM_ELEMENTS_SCHEMA]` to the TestBed config to shallow-render them for this test file only. Log as deviation.
- **`ProjectsService.list()` signature mismatch** → the mock returns `of([])`. If the real service has a different shape, match it. Log as deviation.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task adds state scaffolding only. It does NOT change any user-visible behavior — `applyResult()` still calls `replaceSelection()` directly, no output panel appears, no Apply button exists. Those are Tasks 2–5.

- **Wiring `stagedOutput` into `onOperate()` / `applyResult()`** — Task 3 handles this; do not rename or modify `applyResult()` here.
- **TextOutputComponent** — Task 2; do not create it here even though the properties it will bind to now exist.
- **`applyToEditor()` and `undoApply()` methods** — Tasks 4 and 5; do not add them here.
- **Comprehensive test suite with data-test selectors** — Task 6; this task creates the first test file and proves the Karma pipeline works, but full DOM interaction tests are deferred.
- **Template changes** — no `<app-text-output>` element in the template yet; that's Task 3 or 4.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale (Task 1 section, state transitions table)
- [Epic](./epic.md) — Task scope
- [Timeline](./timeline.md) — Status tracking (update after done)