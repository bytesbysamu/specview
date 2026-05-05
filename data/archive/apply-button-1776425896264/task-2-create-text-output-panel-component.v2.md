Good. Karma + Jasmine, no existing spec files. Now I have everything to write the guide.

# Task 2: Create Text Output Panel Component

**Purpose**: Build a standalone Angular component that displays staged AI results as read-only text, with Apply and Dismiss actions, so that Task 3 can wire AI operations to stage results instead of replacing content in-place.

**Effort**: 3h

**Dependencies**: None — this component is self-contained (pure inputs/outputs, no service injection).

**Parallel With**: Task 1 (result staging state on AppComponent)

**Blocks**: Task 3 (wire operations to staging), Task 4 (apply action), Task 5 (undo apply)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task creates `TextOutputComponent`, a standalone Angular component that renders AI-generated text in a staging panel between the editor/preview area and the operation bar. The component is display-only: it receives `output` and `loading` as inputs, emits `apply` and `dismiss` as outputs, and injects no services. It follows the same inline-template/inline-styles standalone pattern used by every other component in `src/app/components/`. The architecture decision (see `architecture.md` Task 2) calls for a separate component from `OutputPanelComponent` — that component is wired to SSE streaming for implementation tasks and has `running`, `success`, `files`, `taskName` inputs plus `accept`/`retry` outputs. Text output needs none of that; two small components beats one overloaded component.

**Trade-offs considered**:
- **Reuse `OutputPanelComponent`** — rejected because it carries streaming/SSE semantics (`running`, `success`, `files`, `taskName`, `accept`, `retry`) that don't apply. Overloading it would add `*ngIf` branches in the template and mixed concerns.
- **Rendered markdown (`marked`) in the output** — rejected because the output is working text, not a finished document. Plain `<pre>` lets the user see exactly what they're applying. Preview pane exists for rendered markdown after Apply.
- **Create as a feature-module with its own service** — rejected because this is a pure display component with zero data-fetching. Inputs/outputs only, matching the codebase pattern for `OperationBarComponent`.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                         # Flag any unrelated M/?? entries
git diff HEAD -- src/app/app.component.ts          # Confirm target file is clean
npm run build 2>&1 | tail -5                       # Confirm build passes; record baseline
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: 0 spec files exist. Build succeeds (0 test suites — Karma configured but no `.spec.ts` files yet).

---

## 3. Files

### To Create (new)
- `src/app/components/text-output/text-output.component.ts` **(new)** — standalone component; inputs `output`/`loading`, outputs `apply`/`dismiss`
- `src/app/components/text-output/text-output.component.spec.ts` **(new)** — Karma + Jasmine tests for the component

### To Modify (cite CODEBASE CONTEXT)
- `src/app/app.component.ts` — add import of `TextOutputComponent` to the `imports` array (line 23) and add `<app-text-output>` to the template between `</main>` (line 110) and `<app-output-panel>` (line 112)

### To Leave Alone
- `src/app/components/output-panel/output-panel.component.ts` — similar visual pattern but different purpose (SSE streaming for implementation tasks); do not reuse or modify
- `src/app/components/operation-bar/operation-bar.component.ts` — the operation bar sits below the new component; no changes needed in this task
- `src/app/services/ai.service.ts` — AI operations wiring is Task 3, not this task

---

## 4. Implementation Steps

### Step 1: Create TextOutputComponent

**Action**: Create the standalone component with inline template and inline styles. Follow the exact pattern from `src/app/components/output-panel/output-panel.component.ts` (standalone, CommonModule import, inline template/styles, OnPush). Use the color palette from the architecture doc: `#252526` background, `#238636` apply button, `#3c3c3c` dismiss button. Every interactive element gets a `data-test` attribute.

**File**: `src/app/components/text-output/text-output.component.ts` **(new)**

**Pattern**:
```typescript
import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-text-output',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="text-output-panel" data-test="text-output-panel"
         *ngIf="output || loading">
      <div class="panel-header">
        <span class="panel-title">AI Output</span>
        <div class="panel-actions">
          <span class="spinner" *ngIf="loading"></span>
          <button
            class="apply-btn"
            data-test="apply-output"
            (click)="apply.emit()"
            [disabled]="loading || !output">
            ✓ Apply
          </button>
          <button
            class="dismiss-btn"
            data-test="dismiss-output"
            (click)="dismiss.emit()"
            [disabled]="loading">
            ✕
          </button>
        </div>
      </div>
      <div class="panel-content" data-test="staged-output-content">
        <pre>{{ output }}</pre>
      </div>
    </div>
  `,
  styles: [`
    .text-output-panel {
      background: #252526;
      border-top: 1px solid #3c3c3c;
      display: flex;
      flex-direction: column;
      max-height: 40vh;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 12px;
      border-bottom: 1px solid #3c3c3c;
      flex-shrink: 0;
    }

    .panel-title {
      font-size: 12px;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .panel-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .apply-btn {
      background: #238636;
      color: #fff;
      border: none;
      padding: 4px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      transition: background 0.15s ease;
    }

    .apply-btn:hover:not(:disabled) {
      background: #2ea043;
    }

    .apply-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    .dismiss-btn {
      background: #3c3c3c;
      color: #d4d4d4;
      border: none;
      padding: 4px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      transition: background 0.15s ease;
    }

    .dismiss-btn:hover:not(:disabled) {
      background: #4c4c4c;
    }

    .dismiss-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    .panel-content {
      overflow-y: auto;
      padding: 12px;
      flex: 1;
      min-height: 0;
    }

    .panel-content pre {
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
      font-size: 13px;
      color: #d4d4d4;
      line-height: 1.5;
    }

    .spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid #3c3c3c;
      border-top-color: #007acc;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class TextOutputComponent {
  @Input() output: string = '';
  @Input() loading: boolean = false;
  @Output() apply = new EventEmitter<void>();
  @Output() dismiss = new EventEmitter<void>();
}
```

**Verify**: `npx ng build --configuration=development 2>&1 | tail -3` — expect build success (component is created but not yet imported anywhere; Angular tree-shakes unused standalone components, so build should pass regardless).

---

### Step 2: Register in AppComponent imports and template

**Action**: Import `TextOutputComponent` in `src/app/app.component.ts` and add it to the `imports` array. Insert `<app-text-output>` into the template between the closing `</main>` tag (line 110) and the `<!-- Implementation output panel -->` comment (line 112). Bind placeholder properties for now — Task 1 adds the real `stagedOutput` property; this task wires to temporary empty strings so the component compiles.

**File**: `src/app/app.component.ts` (lines 0, 23, 110-112)

**Pattern — import statement** (after line 14):
```typescript
import { TextOutputComponent } from './components/text-output/text-output.component';
```

**Pattern — imports array** (line 23, add `TextOutputComponent`):
```typescript
imports: [CommonModule, EditorComponent, PreviewComponent, OperationBarComponent, SidebarComponent, NewProjectComponent, BuilderProfileComponent, PrinciplesEditorComponent, CodebaseEditorComponent, TimelineViewComponent, OutputPanelComponent, TextOutputComponent],
```

**Pattern — template** (between line 110 `</main>` and line 112 `<!-- Implementation output panel -->`):
```html
        <!-- AI result staging panel -->
        <app-text-output
          [output]="stagedOutput"
          [loading]="loading"
          (apply)="applyToEditor()"
          (dismiss)="dismissOutput()">
        </app-text-output>
```

**Action — add stub properties and methods** (after `historyStack` declaration, line 264):
```typescript
// Staging: holds AI result until user applies (Task 1 will formalize)
stagedOutput = '';
preApplyContent = '';
```

**Action — add stub methods** (after `handleError`, before the closing `}`):
```typescript
applyToEditor(): void {
  // Task 4 will implement
}

dismissOutput(): void {
  this.stagedOutput = '';
}
```

**Verify**: `npx ng build --configuration=development 2>&1 | tail -3` — expect build success. Then `npm start` and visually confirm the panel does NOT appear (because `stagedOutput` is empty and `loading` starts `false`).

---

### Step 3: Write component tests

**Action**: Create a Karma + Jasmine spec file for `TextOutputComponent`. Test four behaviors: hidden when no output and not loading, visible when output is set, apply button emits, dismiss button emits. Use `data-test` selectors only.

**File**: `src/app/components/text-output/text-output.component.spec.ts` **(new)**

**Pattern**: See Section 5 (Tests) below for the full test body.

**Verify**: `npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -10` — expect 4 passing tests.

---

## 5. Tests

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TextOutputComponent } from './text-output.component';

describe('TextOutputComponent', () => {
  let component: TextOutputComponent;
  let fixture: ComponentFixture<TextOutputComponent>;

  function query<T extends HTMLElement>(selector: string): T | null {
    return fixture.nativeElement.querySelector(selector);
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TextOutputComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(TextOutputComponent);
    component = fixture.componentInstance;
  });

  it('noOutputNotLoading_panelHidden', () => {
    component.output = '';
    component.loading = false;
    fixture.detectChanges();

    const panel = query('[data-test="text-output-panel"]');
    expect(panel).toBeNull();
  });

  it('outputSet_panelVisible_contentRendered', () => {
    component.output = 'Rewritten text here';
    component.loading = false;
    fixture.detectChanges();

    const panel = query('[data-test="text-output-panel"]');
    expect(panel).not.toBeNull();

    const content = query<HTMLPreElement>('[data-test="staged-output-content"] pre');
    expect(content).not.toBeNull();
    expect(content!.textContent).toContain('Rewritten text here');
  });

  it('applyClicked_emitsApplyEvent', () => {
    component.output = 'Some output';
    component.loading = false;
    fixture.detectChanges();

    const applySpy = spyOn(component.apply, 'emit');
    const applyBtn = query<HTMLButtonElement>('[data-test="apply-output"]');
    expect(applyBtn).not.toBeNull();

    applyBtn!.click();
    expect(applySpy).toHaveBeenCalledTimes(1);
  });

  it('dismissClicked_emitsDismissEvent', () => {
    component.output = 'Some output';
    component.loading = false;
    fixture.detectChanges();

    const dismissSpy = spyOn(component.dismiss, 'emit');
    const dismissBtn = query<HTMLButtonElement>('[data-test="dismiss-output"]');
    expect(dismissBtn).not.toBeNull();

    dismissBtn!.click();
    expect(dismissSpy).toHaveBeenCalledTimes(1);
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. **`feat(text-output): create TextOutputComponent with Apply/Dismiss actions`** — `src/app/components/text-output/text-output.component.ts`: standalone component with OnPush, inputs (`output`, `loading`), outputs (`apply`, `dismiss`), dark-theme styling, `data-test` selectors
2. **`feat(app): register TextOutputComponent in shell template`** — `src/app/app.component.ts`: import, add to `imports` array, insert `<app-text-output>` in template between editor area and output panel, add `stagedOutput`/`preApplyContent` stub properties and `applyToEditor()`/`dismissOutput()` stub methods
3. **`test(text-output): add component tests — hidden/visible/apply/dismiss`** — `src/app/components/text-output/text-output.component.spec.ts`: 4 Jasmine tests using `data-test` selectors

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npx ng build --configuration=development 2>&1 | tail -5
npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -10
```

**Expected delta**: 0 → 4 passing tests. Build succeeds. Zero pre-existing tests broken (there are none to break).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`. Commit 2 depends on commit 1 (imports the component), so revert in reverse order if rolling back both.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` to return to the starting state. No external state (DB, API, deployed service) is affected — this is purely frontend.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist**: verify against the actual file tree; if `src/app/components/` doesn't exist, flag and stop.
- **Test framework mismatch**: the guide assumes Karma + Jasmine per `angular.json:91` config. If the repo has migrated to Jest or another runner, translate the test shape silently but note in commit body.
- **`loading` input collision**: AppComponent already has a `loading` property used by the operation bar. The template binding `[loading]="loading"` reuses it. If Task 1 introduces a separate `stagingLoading` property, adapt the binding name — log deviation.
- **ChromeHeadless not available**: if `npx ng test --browsers=ChromeHeadless` fails due to missing Chrome, try `--browsers=ChromeHeadlessNoSandbox` or `--no-watch` only. Log the environment deviation.
- **Step N unlocks an obvious simplification for Step N+1**: take it, log deviation in the commit.

---

## 10. Out of Scope

This task creates the component shell and registers it in the template. It does NOT wire AI operations to populate `stagedOutput`, implement the Apply action logic, or add Undo Apply. Those are separate tasks that depend on this component existing.

- **Wiring AI operations to staging** — Task 3; requires renaming `applyResult()` to `stageResult()` and changing its body. Deferred because it changes behavior for all five single-shot operations and should be verified independently.
- **Apply action logic** — Task 4; the `applyToEditor()` method is a stub in this task. Deferred because it requires `preApplyContent` state management and `onContentChange()` integration that should be its own verifiable commit.
- **Undo Apply button in operation bar** — Task 5; requires modifying `OperationBarComponent` with new input/output. Deferred because it depends on Task 4's state management.
- **Markdown rendering in the output panel** — architecture decision chose plain `<pre>` over rendered markdown. If this is revisited later, it would be a separate task.
- **Keyboard shortcut for Apply** (e.g., Cmd+Enter) — not in the epic scope. Could be added later as a polish task.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale (Task 2 section)
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)