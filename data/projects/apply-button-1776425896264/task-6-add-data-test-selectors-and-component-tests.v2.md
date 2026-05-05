Now I have full context on the current codebase state and the test infrastructure. Let me generate the implementation guide.

# Task 6: Add data-test selectors and component tests

**Purpose**: Add `data-test` attributes to all interactive elements in `TextOutputComponent` and `OperationBarComponent`, then write comprehensive TestBed tests for the staging/apply/undo flow — both at the component level (TextOutputComponent) and the integration level (AppComponent).

**Effort**: 2h

**Dependencies**: Tasks 1–5 must be shipped (staging state, TextOutputComponent, wiring, apply, undo)

**Parallel With**: —

**Blocks**: —

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 6 caps the Apply Button capability by adding the `data-test` selectors required by the project's testing rules and writing the TestBed tests that prove the staging/apply/undo cycle works end-to-end through Angular's component tree. Tasks 1–5 shipped the behavior; this task makes it testable and regression-safe. The project currently has zero Angular spec files, so this task also bootstraps the Karma test runner (creating `karma.conf.js` if `ng test` doesn't work out of the box). All tests use TestBed with real child components rendered, mock services via providers, Page Object pattern with `data-test` selectors, and the `condition_expectedOutcome` naming convention — matching the architecture principles.

**Trade-offs considered**:
- **Add data-test selectors inside Tasks 2/5 when the components were first created** — rejected because separating selectors + tests into their own task keeps each prior task's blast radius small and lets the test author see all selectors in one pass, preventing mismatches
- **Jest instead of Karma** — rejected because `angular.json` already configures the `@angular-devkit/build-angular:karma` builder, `tsconfig.spec.json` targets Jasmine types, and Karma/Jasmine dependencies are already in `package.json`
- **Write tests in this task using `data-test` selectors (chosen)** — preferred because it combines the selector addition with immediate test consumption, guaranteeing no selector is orphaned or misspelled

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                    # Confirm Tasks 1-5 are committed; flag unrelated M/?? entries
git diff HEAD -- src/app/components/text-output/              # Confirm TextOutputComponent exists (Task 2)
git diff HEAD -- src/app/components/operation-bar/             # Confirm Undo Apply shipped (Task 5)
git log --oneline -10                                         # Confirm Task 1-5 commits present
ls src/app/app.component.spec.ts                              # Confirm Task 1 created it
ls src/app/components/text-output/text-output.component.ts    # Confirm Task 2 created it
npx ng test --no-watch --browsers=ChromeHeadless 2>&1 | tail -20   # Baseline test count; if it fails, Step 1 creates karma.conf.js
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: Record the passing test count from `ng test` output. If `ng test` fails entirely (missing `karma.conf.js`), baseline is 0 — Step 1 fixes it.

---

## 3. Files

### To Create (new)
- `karma.conf.js` **(new, conditional)** — only if `ng test` fails without it. Standard Angular Karma config pointing at `tsconfig.spec.json`

### To Modify (cite CODEBASE CONTEXT / PRIOR TASKS)
- `src/app/components/text-output/text-output.component.ts` — add `data-test` attributes to panel container, Apply button, Dismiss button, output content area, and spinner (shipped by Task 2)
- `src/app/components/text-output/text-output.component.spec.ts` — add TestBed tests for panel visibility, apply emits, dismiss emits, loading state (file created by Task 2; may have minimal tests)
- `src/app/components/operation-bar/operation-bar.component.ts` — add `data-test="undo-apply"` to the Undo Apply button (shipped by Task 5)
- `src/app/components/operation-bar/operation-bar.component.spec.ts` — add test verifying the Undo Apply button's `data-test` selector exists (file created by Task 5)
- `src/app/app.component.spec.ts` — add tests for: staged output flow, apply promotes content, undo restores content, file switch clears state (file created by Task 1; Task 4/5 added apply/undo tests)

### To Leave Alone
- `src/app/app.component.ts` — no logic changes; only spec files and component templates change in this task
- `src/app/components/output-panel/output-panel.component.ts` — SSE streaming panel; unrelated to staging flow
- `src/app/services/ai.service.ts` — service logic untouched; mocked in tests
- `server.js` — backend unchanged

---

## 4. Implementation Steps

### Step 1: Bootstrap Karma runner (conditional)

**Action**: Run `npx ng test --no-watch --browsers=ChromeHeadless`. If it fails with "Missing karma.conf.js" or similar config error, create the file. If tests already run, skip this step.

**File**: `karma.conf.js` (new, conditional)

**Pattern**:
```javascript
// Karma configuration file
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
    jasmineHtmlReporter: {
      suppressAll: true
    },
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/spec-doc'),
      subdir: '.',
      reporters: [{ type: 'html' }, { type: 'text-summary' }]
    },
    reporters: ['progress', 'kjhtml'],
    browsers: ['ChromeHeadless'],
    restartOnFileChange: true
  });
};
```

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless` — expect 0 failures (may be 0 specs if no `.spec.ts` files exist yet, or existing tests from Tasks 1-5 all pass)

---

### Step 2: Add data-test selectors to TextOutputComponent template

**Action**: Open `src/app/components/text-output/text-output.component.ts` and add `data-test` attributes to the five key elements. If Task 2 already added them (architecture said to), verify they match exactly and skip. The required selectors are:

| Element | Selector |
|---------|----------|
| Panel container div | `data-test="text-output-panel"` |
| Apply button | `data-test="apply-output"` |
| Dismiss button | `data-test="dismiss-output"` |
| Output content area | `data-test="staged-output-content"` |

**File**: `src/app/components/text-output/text-output.component.ts` (shipped by Task 2)

**Pattern** — the template section should contain these attributes (showing shape, not full template):
```html
<div class="text-output-panel" data-test="text-output-panel">
  <div class="panel-header">
    <span>AI Output</span>
    <button class="apply-btn" data-test="apply-output" (click)="apply.emit()" [disabled]="loading">✓ Apply</button>
    <button class="dismiss-btn" data-test="dismiss-output" (click)="dismiss.emit()">✕</button>
    <span class="spinner" *ngIf="loading"></span>
  </div>
  <div class="panel-content" data-test="staged-output-content">
    <pre>{{ output }}</pre>
  </div>
</div>
```

**Verify**: `grep -c 'data-test=' src/app/components/text-output/text-output.component.ts` — expect 4

---

### Step 3: Add data-test selector to Undo Apply button in OperationBarComponent

**Action**: Open `src/app/components/operation-bar/operation-bar.component.ts` and add `data-test="undo-apply"` to the Undo Apply button that Task 5 shipped.

**File**: `src/app/components/operation-bar/operation-bar.component.ts` (modified by Task 5)

**Pattern** — locate the Undo Apply button in the template and add the attribute:
```html
<button
  *ngIf="canUndoApply"
  class="op-btn undo-apply"
  data-test="undo-apply"
  (click)="executeOp('undoApply')"
  [disabled]="loading"
  title="Undo last apply">
  ↩ Undo Apply
</button>
```

**Verify**: `grep 'data-test="undo-apply"' src/app/components/operation-bar/operation-bar.component.ts` — expect 1 match

---

### Step 4: Write TextOutputComponent tests

**Action**: Open `src/app/components/text-output/text-output.component.spec.ts` (created by Task 2). Add comprehensive tests covering panel visibility, Apply event emission, Dismiss event emission, and loading state. Use Page Object pattern with `data-test` selectors.

**File**: `src/app/components/text-output/text-output.component.spec.ts` (created by Task 2)

**Pattern** — replace or extend the file with:
```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TextOutputComponent } from './text-output.component';

class TextOutputPage {
  constructor(private fixture: ComponentFixture<TextOutputComponent>) {}

  get panel(): HTMLElement | null {
    return this.query('[data-test="text-output-panel"]');
  }

  get applyButton(): HTMLButtonElement | null {
    return this.query<HTMLButtonElement>('[data-test="apply-output"]');
  }

  get dismissButton(): HTMLButtonElement | null {
    return this.query<HTMLButtonElement>('[data-test="dismiss-output"]');
  }

  get contentArea(): HTMLElement | null {
    return this.query('[data-test="staged-output-content"]');
  }

  get spinnerVisible(): boolean {
    return this.fixture.nativeElement.querySelector('.spinner') !== null;
  }

  private query<T extends HTMLElement>(selector: string): T | null {
    return this.fixture.nativeElement.querySelector(selector);
  }
}

describe('TextOutputComponent', () => {
  let component: TextOutputComponent;
  let fixture: ComponentFixture<TextOutputComponent>;
  let page: TextOutputPage;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TextOutputComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TextOutputComponent);
    component = fixture.componentInstance;
    page = new TextOutputPage(fixture);
  });

  describe('panel visibility', () => {
    it('emptyOutput_panelRendersWithEmptyContent', () => {
      component.output = '';
      fixture.detectChanges();
      // Panel element should exist in DOM (visibility controlled by parent *ngIf)
      expect(page.panel).toBeTruthy();
      expect(page.contentArea?.textContent?.trim()).toBe('');
    });

    it('nonEmptyOutput_displaysOutputText', () => {
      component.output = 'AI generated result here';
      fixture.detectChanges();
      expect(page.contentArea).toBeTruthy();
      expect(page.contentArea!.textContent).toContain('AI generated result here');
    });
  });

  describe('apply emission', () => {
    it('applyButtonClick_emitsApplyEvent', () => {
      component.output = 'some output';
      fixture.detectChanges();

      let emitted = false;
      component.apply.subscribe(() => emitted = true);

      page.applyButton!.click();
      expect(emitted).toBeTrue();
    });

    it('loadingTrue_applyButtonDisabled', () => {
      component.output = 'some output';
      component.loading = true;
      fixture.detectChanges();

      expect(page.applyButton!.disabled).toBeTrue();
    });
  });

  describe('dismiss emission', () => {
    it('dismissButtonClick_emitsDismissEvent', () => {
      component.output = 'some output';
      fixture.detectChanges();

      let emitted = false;
      component.dismiss.subscribe(() => emitted = true);

      page.dismissButton!.click();
      expect(emitted).toBeTrue();
    });
  });

  describe('loading state', () => {
    it('loadingFalse_spinnerHidden', () => {
      component.output = 'some output';
      component.loading = false;
      fixture.detectChanges();

      expect(page.spinnerVisible).toBeFalse();
    });

    it('loadingTrue_spinnerVisible', () => {
      component.output = 'some output';
      component.loading = true;
      fixture.detectChanges();

      expect(page.spinnerVisible).toBeTrue();
    });
  });

  describe('data-test selectors', () => {
    it('allRequiredSelectorsPresent', () => {
      component.output = 'test';
      fixture.detectChanges();

      expect(page.panel).toBeTruthy('missing data-test="text-output-panel"');
      expect(page.applyButton).toBeTruthy('missing data-test="apply-output"');
      expect(page.dismissButton).toBeTruthy('missing data-test="dismiss-output"');
      expect(page.contentArea).toBeTruthy('missing data-test="staged-output-content"');
    });
  });
});
```

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless --include='**/text-output.component.spec.ts'` — expect 7 passing, 0 failures

---

### Step 5: Write AppComponent staging flow tests

**Action**: Open `src/app/app.component.spec.ts` (created by Task 1, extended by Tasks 4 and 5). Add tests for: staged output flow (stageResult sets stagedOutput), apply promotes content, undo restores content, file switch clears state. AppComponent has heavy dependencies — mock `AiService`, `HttpClient`, `ProjectsService`, `ImplementationService`, `TimelineParserService`. The `EditorComponent` depends on Monaco — stub it to avoid loading the full editor.

**File**: `src/app/app.component.spec.ts` (created by Task 1)

**Pattern** — add these test blocks to the existing describe. The imports and TestBed setup may already exist from Task 1; extend rather than duplicate:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { AppComponent } from './app.component';
import { AiService } from './services/ai.service';
import { ProjectsService } from './services/projects.service';
import { ImplementationService } from './services/implementation.service';
import { TimelineParserService } from './services/timeline-parser.service';
import { of } from 'rxjs';

// Stub child components to avoid Monaco dependency and simplify test tree
@Component({ selector: 'app-editor', standalone: true, template: '' })
class MockEditorComponent {
  @Input() content = '';
  @Output() contentChange = new EventEmitter<string>();
  @Output() selectionChange = new EventEmitter<{ text: string; range: any }>();
  replaceSelection(_text: string): void {}
}

@Component({ selector: 'app-preview', standalone: true, template: '' })
class MockPreviewComponent {
  @Input() markdown = '';
}

@Component({ selector: 'app-sidebar', standalone: true, template: '' })
class MockSidebarComponent {
  @Input() projects: any[] = [];
  @Input() activeProjectId = '';
  @Input() activeFile = '';
  @Output() specSelect = new EventEmitter();
  @Output() action = new EventEmitter();
  @Output() deleteProject = new EventEmitter();
}

@Component({ selector: 'app-operation-bar', standalone: true, template: '' })
class MockOperationBarComponent {
  @Input() hasSelection = false;
  @Input() selectionLength = 0;
  @Input() loading = false;
  @Input() hasBaseSpec = false;
  @Input() baseSpecFile = '';
  @Input() canRevert = false;
  @Input() historyCount = 0;
  @Input() canUndoApply = false;
  @Output() operate = new EventEmitter();
}

@Component({ selector: 'app-new-project', standalone: true, template: '' })
class MockNewProjectComponent {
  @Output() close = new EventEmitter();
  @Output() projectCreated = new EventEmitter();
}

@Component({ selector: 'app-builder-profile', standalone: true, template: '' })
class MockBuilderProfileComponent {
  @Output() close = new EventEmitter();
}

@Component({ selector: 'app-principles-editor', standalone: true, template: '' })
class MockPrinciplesEditorComponent {
  @Output() close = new EventEmitter();
}

@Component({ selector: 'app-codebase-editor', standalone: true, template: '' })
class MockCodebaseEditorComponent {
  @Output() close = new EventEmitter();
}

@Component({ selector: 'app-timeline-view', standalone: true, template: '' })
class MockTimelineViewComponent {
  @Input() content = '';
  @Input() projectContext: any = null;
  @Output() implement = new EventEmitter();
  @Output() statusChange = new EventEmitter();
}

@Component({ selector: 'app-output-panel', standalone: true, template: '' })
class MockOutputPanelComponent {
  @Input() visible = false;
  @Input() output = '';
  @Input() running = false;
  @Input() success = false;
  @Input() files: string[] = [];
  @Input() taskName = '';
  @Output() close = new EventEmitter();
  @Output() accept = new EventEmitter();
  @Output() retry = new EventEmitter();
}

@Component({ selector: 'app-text-output', standalone: true, template: '' })
class MockTextOutputComponent {
  @Input() output = '';
  @Input() loading = false;
  @Output() apply = new EventEmitter<void>();
  @Output() dismiss = new EventEmitter<void>();
}

describe('AppComponent — staging flow', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;
  let mockAiService: jasmine.SpyObj<AiService>;
  let mockProjectsService: jasmine.SpyObj<ProjectsService>;

  beforeEach(async () => {
    mockAiService = jasmine.createSpyObj('AiService', [
      'rewrite', 'expand', 'compress', 'clarify', 'generate', 'iterate', 'generateSpec'
    ]);
    mockProjectsService = jasmine.createSpyObj('ProjectsService', ['list', 'get', 'updateFile', 'delete']);
    mockProjectsService.list.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
        AppComponent
      ],
      providers: [
        { provide: AiService, useValue: mockAiService },
        { provide: ProjectsService, useValue: mockProjectsService },
        { provide: ImplementationService, useValue: jasmine.createSpyObj('ImplementationService', ['implement']) },
        { provide: TimelineParserService, useValue: jasmine.createSpyObj('TimelineParserService', ['updateTaskStatus']) }
      ]
    })
    .overrideComponent(AppComponent, {
      remove: {
        imports: [
          // Remove real components that have heavy deps (Monaco, etc.)
        ]
      },
      add: {
        imports: [
          MockEditorComponent,
          MockPreviewComponent,
          MockSidebarComponent,
          MockOperationBarComponent,
          MockNewProjectComponent,
          MockBuilderProfileComponent,
          MockPrinciplesEditorComponent,
          MockCodebaseEditorComponent,
          MockTimelineViewComponent,
          MockOutputPanelComponent,
          MockTextOutputComponent
        ]
      }
    })
    .compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('stageResult', () => {
    it('stageResult_setsStagedOutputAndClearsLoading', () => {
      component.loading = true;
      (component as any).stageResult('AI generated text');

      expect(component.stagedOutput).toBe('AI generated text');
      expect(component.loading).toBeFalse();
    });

    it('stageResult_calledTwice_replacesFirstResult', () => {
      (component as any).stageResult('first result');
      (component as any).stageResult('second result');

      expect(component.stagedOutput).toBe('second result');
    });
  });

  describe('applyToEditor', () => {
    it('applyToEditor_promotesStagedOutputToContent', () => {
      component.content = 'original content';
      component.stagedOutput = 'new AI content';

      component.applyToEditor();

      expect(component.content).toBe('new AI content');
      expect(component.stagedOutput).toBe('');
    });

    it('applyToEditor_storesPreApplyContent', () => {
      component.content = 'original content';
      component.stagedOutput = 'new AI content';

      component.applyToEditor();

      expect(component.preApplyContent).toBe('original content');
    });
  });

  describe('undoApply', () => {
    it('undoApply_restoresPreApplyContent', () => {
      component.content = 'original';
      component.stagedOutput = 'replacement';
      component.applyToEditor();

      component.undoApply();

      expect(component.content).toBe('original');
      expect(component.preApplyContent).toBe('');
    });

    it('noPreApplyContent_undoApplyDoesNothing', () => {
      component.content = 'current content';
      component.preApplyContent = '';

      component.undoApply();

      expect(component.content).toBe('current content');
    });
  });

  describe('file switch clears state', () => {
    it('onSpecSelect_clearsStagedOutputAndPreApplyContent', () => {
      component.stagedOutput = 'pending result';
      component.preApplyContent = 'saved snapshot';

      const mockProject = { id: 'test', name: 'Test', expanded: true, specs: [] };
      const mockSpec = { id: 's1', label: 'Test', filename: 'test.md', content: 'file content' };

      component.onSpecSelect({ project: mockProject as any, spec: mockSpec });

      expect(component.stagedOutput).toBe('');
      expect(component.preApplyContent).toBe('');
    });
  });
});
```

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless` — expect all new tests pass. If `overrideComponent` doesn't work for removing specific imports (Angular's override API may differ), fall back to overriding the entire `imports` array. See Deviations Allowed.

---

### Step 6: Add Undo Apply data-test verification to OperationBarComponent tests

**Action**: Open `src/app/components/operation-bar/operation-bar.component.spec.ts` (created by Task 5). Add a test verifying the `data-test="undo-apply"` attribute exists when `canUndoApply` is true.

**File**: `src/app/components/operation-bar/operation-bar.component.spec.ts` (created by Task 5)

**Pattern** — add to existing describe block:
```typescript
describe('undo-apply data-test selector', () => {
  it('canUndoApplyTrue_undoButtonHasDataTestSelector', () => {
    component.canUndoApply = true;
    fixture.detectChanges();

    const undoBtn = fixture.nativeElement.querySelector('[data-test="undo-apply"]');
    expect(undoBtn).toBeTruthy('Undo Apply button must have data-test="undo-apply"');
  });

  it('canUndoApplyFalse_undoButtonNotRendered', () => {
    component.canUndoApply = false;
    fixture.detectChanges();

    const undoBtn = fixture.nativeElement.querySelector('[data-test="undo-apply"]');
    expect(undoBtn).toBeNull();
  });
});
```

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless --include='**/operation-bar.component.spec.ts'` — expect all pass

---

## 5. Tests

All tests are provided in Steps 4, 5, and 6 above with complete assertion bodies. Summary of test coverage:

**TextOutputComponent** (Step 4 — 7 tests):

| Test | What it asserts |
|------|-----------------|
| `emptyOutput_panelRendersWithEmptyContent` | Panel DOM element exists; content area is empty |
| `nonEmptyOutput_displaysOutputText` | Content area contains the provided output string |
| `applyButtonClick_emitsApplyEvent` | Clicking Apply button fires `apply` EventEmitter |
| `loadingTrue_applyButtonDisabled` | Apply button is `disabled` when `loading=true` |
| `dismissButtonClick_emitsDismissEvent` | Clicking Dismiss button fires `dismiss` EventEmitter |
| `loadingFalse_spinnerHidden` | No `.spinner` element when `loading=false` |
| `loadingTrue_spinnerVisible` | `.spinner` element present when `loading=true` |
| `allRequiredSelectorsPresent` | All 4 `data-test` selectors exist in rendered DOM |

**AppComponent staging flow** (Step 5 — 6 tests):

| Test | What it asserts |
|------|-----------------|
| `stageResult_setsStagedOutputAndClearsLoading` | `stagedOutput` set, `loading` false |
| `stageResult_calledTwice_replacesFirstResult` | Second call overwrites first |
| `applyToEditor_promotesStagedOutputToContent` | `content` = staged, `stagedOutput` cleared |
| `applyToEditor_storesPreApplyContent` | `preApplyContent` = previous content |
| `undoApply_restoresPreApplyContent` | `content` restored, `preApplyContent` cleared |
| `noPreApplyContent_undoApplyDoesNothing` | No-op when nothing to undo |
| `onSpecSelect_clearsStagedOutputAndPreApplyContent` | Both staging properties reset on file switch |

**OperationBarComponent** (Step 6 — 2 tests):

| Test | What it asserts |
|------|-----------------|
| `canUndoApplyTrue_undoButtonHasDataTestSelector` | `data-test="undo-apply"` present |
| `canUndoApplyFalse_undoButtonNotRendered` | Button not in DOM when `canUndoApply=false` |

---

## 6. Commit Plan

One commit per logical unit:

1. **`chore(test): bootstrap Karma runner`** — `karma.conf.js` (conditional; skip if not needed): Karma config for ChromeHeadless
2. **`feat(text-output): add data-test selectors`** — `text-output.component.ts`: add `data-test` attributes to panel, Apply, Dismiss, content area
3. **`feat(operation-bar): add data-test selector to Undo Apply`** — `operation-bar.component.ts`: add `data-test="undo-apply"`
4. **`test(text-output): TestBed tests for panel visibility, events, loading`** — `text-output.component.spec.ts`: 7 test cases with Page Object
5. **`test(app): staging flow integration tests`** — `app.component.spec.ts`: 7 test cases covering stage/apply/undo/file-switch
6. **`test(operation-bar): undo-apply data-test selector tests`** — `operation-bar.component.spec.ts`: 2 test cases

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npx ng test --no-watch --browsers=ChromeHeadless
```

**Expected delta**: Baseline (from Tasks 1–5) → Baseline + 16 passing. Zero pre-existing tests broken.

Cross-check data-test coverage:
```bash
grep -r 'data-test=' src/app/components/text-output/text-output.component.ts | wc -l   # expect 4
grep -r 'data-test="undo-apply"' src/app/components/operation-bar/operation-bar.component.ts | wc -l   # expect 1
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch [REQUIRES APPROVAL]
- **Karma config**: if `karma.conf.js` was created and causes issues, `git revert` the first commit. `ng test` will fall back to Angular CLI defaults.

---

## 9. Deviations Allowed

- **Task 2 already placed data-test attributes** → verify they match the required names exactly. If they do, skip Step 2 and note `Deviations: data-test selectors already present from Task 2` in the commit body.
- **Task 5's Undo button uses a different emission pattern** (e.g., dedicated `@Output()` instead of `executeOp('undoApply')`) → adapt the `data-test` placement to whichever element Task 5 actually created. Log the divergence.
- **`overrideComponent` remove/add doesn't work for swapping imports** → use a different mocking strategy: either override the entire `imports` array with all mock stubs, or use `TestBed.overrideComponent(AppComponent, { set: { imports: [...allMocks] } })`. Angular's override API varies across v19 minor versions — match what works.
- **`ng test` requires additional Chrome flags in CI/Docker** → add `--browsers=ChromeHeadlessNoSandbox` and define that custom launcher in `karma.conf.js`. This is a known container issue, not a test issue.
- **Existing tests from Tasks 1/4/5 already cover some behaviors listed here** (e.g., `applyToEditor` tests from Task 4) → do not duplicate. Only add tests for behaviors NOT already covered. Note in the commit body which tests were skipped as already covered.
- **`stageResult` is private** → access it via `(component as any).stageResult(...)` in tests, or test it indirectly through the AI operation subscribe callbacks by triggering `onOperate()` with a mocked `AiService` response.

---

## 10. Out of Scope

This task adds `data-test` selectors and tests for the staging/apply/undo flow only. It does not extend the flow, change behavior, or add new components. The following items are explicitly deferred:

- **E2E / Cypress / Playwright tests** — deferred until the project has a CI pipeline that runs the full app; unit/integration tests via TestBed are sufficient for now
- **data-test selectors on existing operation buttons** (Rewrite, Expand, Compress, Clarify, Generate, Iterate, Revert, Generate Spec) — these pre-date the Apply capability and should be added in a separate pass when those buttons get their own test coverage
- **Test coverage for AI service HTTP calls** (mocking HttpClient for AiService) — AiService tests are separate from the staging flow; they test the service, not the component
- **Code coverage thresholds** — no `coverageReporter` thresholds configured; premature until more of the app has tests
- **Performance / change detection tests** — verifying OnPush efficiency is an optimization concern, not a correctness concern

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale
- [Epic](./epic.md) — Task scope
- [Timeline](./timeline.md) — Status tracking (update after done)