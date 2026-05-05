Now I have the full picture. Let me generate the implementation guide.

# Task 5: Implement Single-Level Undo

**Purpose**: Add an "Undo Apply" button to the operation bar that restores editor content to its pre-Apply state, giving users a single-level safety net when reviewing staged AI results.

**Effort**: 1h

**Dependencies**: Tasks 1–4 must be complete (result staging state, TextOutputComponent, staging wiring, Apply action)

**Parallel With**: —

**Blocks**: Task 6 (tests + data-test audit)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Task 4 introduced `applyToEditor()`, which promotes staged AI output into the editor and snapshots the previous content into `preApplyContent`. This task closes the Apply loop by adding an "Undo Apply" button in the operation bar that restores that snapshot. The button is only visible when `preApplyContent` is non-empty (i.e., after the user has applied staged output and before they switch files or apply again). The undo slot is single-level — applying a second result overwrites the previous snapshot. File switch clears the slot via `clearStagedOutput()` (shipped in Task 1). The button lives in the operation bar rather than the text output panel because the panel is hidden after Apply — the user needs undo accessible while editing promoted content.

**Trade-offs considered**:
- **Dedicated `@Output() undoApply`** on OperationBarComponent — rejected because all other operations route through the unified `(operate)` EventEmitter. A side-channel for one operation breaks the pattern and adds a second wiring path.
- **Multi-level undo stack** — rejected because the architecture explicitly scopes this as single-level. Each Apply overwrites the slot. Multi-level undo is a separate design decision with undo-tree complexity that isn't warranted yet.
- **Route through `OperationEvent` with `'undoApply'` added to the `Operation` union** — preferred because it follows the established pattern (all buttons → `executeOp()` → `operate.emit()`), and the handler in `onOperate()` is a straightforward switch case matching the rest.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                              # Flag any unrelated M/?? entries
git diff HEAD -- src/app/app.component.ts \
                 src/app/components/operation-bar/operation-bar.component.ts
                                                        # Confirm target files are clean (or only have Task 1-4 changes)
npm test 2>&1 | tail -5                                 # Record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Pre-condition check**: Verify Tasks 1–4 are complete:
```bash
grep -q 'preApplyContent' src/app/app.component.ts     # Task 1 shipped
grep -q 'applyToEditor' src/app/app.component.ts       # Task 4 shipped
```
Both must succeed. If either fails, STOP — this task depends on them.

**Baseline recorded**: _____/_____ passing (fill in at execution time).

---

## 3. Files

### To Create (new)
- `src/app/components/operation-bar/operation-bar.component.spec.ts` **(new)** — Karma + Jasmine tests covering the Undo Apply button visibility and event emission

### To Modify (cite CODEBASE CONTEXT)
- `src/app/components/operation-bar/operation-bar.component.ts` — add `'undoApply'` to `Operation` union (line 5), add `@Input() canUndoApply` (after line 270), add Undo Apply button to template (after the Revert button, line 73), add button style (after `.revert` block, line 172)
- `src/app/app.component.ts` — add `undoApply()` method (after `applyToEditor()`, shipped by Task 4), add `case 'undoApply'` to `onOperate()` switch (after `case 'revert'`, line 819), add `[canUndoApply]` binding to `<app-operation-bar>` in template (after `[historyCount]`, line 132)
- `src/app/app.component.spec.ts` — add test for `undoApply()` behavior (this file was created by Task 1)

### To Leave Alone
- `src/app/components/text-output/text-output.component.ts` — the undo button lives in the operation bar, not the text output panel (architecture decision: panel is hidden after Apply)
- `src/app/components/output-panel/output-panel.component.ts` — SSE implementation streaming; unrelated to the Apply/Undo cycle
- `src/app/services/ai.service.ts` — no backend call for undo; it's a local state operation
- `server.js` — backend unchanged

---

## 4. Implementation Steps

### Step 1: Extend Operation type and add input

**Action**: Add `'undoApply'` to the `Operation` type union and add `@Input() canUndoApply` to the component class.

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Pattern**:
```typescript
// Line 5 — extend union
export type Operation = 'rewrite' | 'expand' | 'compress' | 'clarify' | 'generate' | 'iterate' | 'revert' | 'generateSpec' | 'undoApply';

// After @Input() historyCount (line 270) — add new input
@Input() canUndoApply = false;
```

**Verify**: `npx ng build --configuration development 2>&1 | tail -3` — expect clean build (unused input is fine)

---

### Step 2: Add Undo Apply button to operation bar template

**Action**: Insert the Undo Apply button in the template after the Revert button. Visible only when `canUndoApply` is true. Emits via `executeOp('undoApply')`.

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Pattern** (insert after the Revert `</button>` at line 73, before the Generate Spec button at line 74):
```html
<button
  *ngIf="canUndoApply"
  class="op-btn undo-apply"
  (click)="executeOp('undoApply')"
  [disabled]="loading"
  data-test="undo-apply"
  title="Undo last Apply — restore previous content">
  ↩ Undo Apply
</button>
```

**Verify**: `npx ng build --configuration development 2>&1 | tail -3` — clean build

---

### Step 3: Add Undo Apply button style

**Action**: Add `.undo-apply` style block to the component styles. Amber accent matching Revert, but slightly differentiated with a distinct background to avoid confusion with the existing Revert (which undoes iterate/generateSpec operations, not Apply).

**File**: `src/app/components/operation-bar/operation-bar.component.ts`

**Pattern** (insert after the `.revert` block ending at line 172):
```css
&.undo-apply {
  border-color: #e0904a;
  background: #3a2510;
  color: #e0904a;

  &:hover:not(:disabled) {
    background: #4a3520;
    border-color: #f0a05a;
  }
}
```

**Verify**: Visual — start dev server (`npm run dev`), apply a staged result, confirm button appears with amber styling.

---

### Step 4: Add undoApply() method to AppComponent

**Action**: Add the `undoApply()` method. It restores `content` from `preApplyContent`, clears the snapshot, and triggers `onContentChange()` to sync auto-save.

**File**: `src/app/app.component.ts`

**Pattern** (add after the `applyToEditor()` method shipped by Task 4):
```typescript
undoApply(): void {
  if (this.preApplyContent) {
    this.content = this.preApplyContent;
    this.preApplyContent = '';
    this.onContentChange(this.content);
  }
}
```

**Verify**: `npx ng build --configuration development 2>&1 | tail -3` — clean build

---

### Step 5: Wire undoApply in onOperate() switch

**Action**: Add a `case 'undoApply'` to the `onOperate()` switch block. Unlike AI operations, this is a synchronous local-state operation — set `loading = false` immediately.

**File**: `src/app/app.component.ts`

**Pattern** (insert after `case 'revert':` block, before `case 'generateSpec':` — currently around line 819):
```typescript
case 'undoApply':
  this.undoApply();
  this.loading = false;
  break;
```

**Verify**: `npx ng build --configuration development 2>&1 | tail -3` — clean build

---

### Step 6: Bind canUndoApply in template

**Action**: Add the `[canUndoApply]` input binding to the `<app-operation-bar>` element in the AppComponent template.

**File**: `src/app/app.component.ts`

**Pattern** (add after `[historyCount]="historyStack.length"` at line 132):
```html
[canUndoApply]="!!preApplyContent"
```

The full `<app-operation-bar>` block becomes:
```html
<app-operation-bar
  [hasSelection]="hasSelection"
  [selectionLength]="selectedText.length"
  [loading]="loading"
  [hasBaseSpec]="!!baseSpecContent"
  [baseSpecFile]="currentFile"
  [canRevert]="historyStack.length > 0"
  [historyCount]="historyStack.length"
  [canUndoApply]="!!preApplyContent"
  (operate)="onOperate($event)">
</app-operation-bar>
```

**Verify**: `npx ng build --configuration development 2>&1 | tail -3` — clean build. Full dev test: run `npm run dev`, perform an AI operation → Apply → confirm "Undo Apply" button appears → click it → confirm content restores and button disappears.

---

## 5. Tests

### OperationBarComponent tests (new file)

**File**: `src/app/components/operation-bar/operation-bar.component.spec.ts` **(new)**

**Framework**: Karma + Jasmine (matches `tsconfig.spec.json` and `angular.json` config)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { OperationBarComponent, OperationEvent } from './operation-bar.component';

describe('OperationBarComponent', () => {
  let component: OperationBarComponent;
  let fixture: ComponentFixture<OperationBarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OperationBarComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(OperationBarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('Undo Apply button', () => {
    it('canUndoApplyFalse_hidesUndoButton', () => {
      component.canUndoApply = false;
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('[data-test="undo-apply"]');
      expect(btn).toBeNull();
    });

    it('canUndoApplyTrue_showsUndoButton', () => {
      component.canUndoApply = true;
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('[data-test="undo-apply"]');
      expect(btn).not.toBeNull();
      expect(btn.textContent).toContain('Undo Apply');
    });

    it('undoApplyClicked_emitsUndoApplyOperation', () => {
      component.canUndoApply = true;
      fixture.detectChanges();

      let emitted: OperationEvent | null = null;
      component.operate.subscribe((event: OperationEvent) => emitted = event);

      const btn: HTMLButtonElement = fixture.nativeElement.querySelector('[data-test="undo-apply"]');
      btn.click();

      expect(emitted).not.toBeNull();
      expect(emitted!.operation).toBe('undoApply');
    });

    it('loadingTrue_disablesUndoButton', () => {
      component.canUndoApply = true;
      component.loading = true;
      fixture.detectChanges();

      const btn: HTMLButtonElement = fixture.nativeElement.querySelector('[data-test="undo-apply"]');
      expect(btn.disabled).toBeTrue();
    });
  });

  describe('Revert button', () => {
    it('canRevertFalse_hidesRevertButton', () => {
      component.canRevert = false;
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.revert');
      expect(btn).toBeNull();
    });

    it('canRevertTrue_showsRevertButton', () => {
      component.canRevert = true;
      component.historyCount = 2;
      fixture.detectChanges();

      const btn = fixture.nativeElement.querySelector('.revert');
      expect(btn).not.toBeNull();
      expect(btn.textContent).toContain('Revert (2)');
    });
  });
});
```

### AppComponent undoApply tests (add to existing spec)

**File**: `src/app/app.component.spec.ts` (created by Task 1 — append to existing `describe` block)

```typescript
describe('undoApply', () => {
  it('preApplyContentSet_restoresPreviousContent', () => {
    component.content = 'after-apply content';
    component.preApplyContent = 'before-apply content';

    component.undoApply();

    expect(component.content).toBe('before-apply content');
    expect(component.preApplyContent).toBe('');
  });

  it('preApplyContentEmpty_noChange', () => {
    component.content = 'current content';
    component.preApplyContent = '';

    component.undoApply();

    expect(component.content).toBe('current content');
  });

  it('undoApply_triggersOnContentChange', () => {
    component.preApplyContent = 'old content';
    component.content = 'new content';
    spyOn(component, 'onContentChange');

    component.undoApply();

    expect(component.onContentChange).toHaveBeenCalledWith('old content');
  });
});
```

**Note**: The AppComponent spec was scaffolded in Task 1. The executor should add this `describe('undoApply')` block inside the existing top-level `describe('AppComponent')`. If Task 1's spec mocks services or provides TestBed setup, reuse that setup — do not create a duplicate `beforeEach`.

---

## 6. Commit Plan

One commit per logical unit:

1. **`feat(operation-bar): add Undo Apply button with canUndoApply input`** — `operation-bar.component.ts`: extends `Operation` type, adds `@Input() canUndoApply`, button template, and `.undo-apply` style
2. **`feat(app): wire undoApply through onOperate and template`** — `app.component.ts`: adds `undoApply()` method, `case 'undoApply'` in switch, `[canUndoApply]` binding
3. **`test(undo-apply): operation bar + app component undo tests`** — `operation-bar.component.spec.ts` (new), `app.component.spec.ts` (append)

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npm test                    # Karma — all Angular specs
npm run test:server         # Node.js server tests (should be unaffected)
```

**Expected delta**: baseline → baseline + 9 passing (6 operation-bar specs + 3 app-component undo specs). Zero pre-existing tests broken.

**Manual smoke test** (recommended before marking complete):
1. `npm run dev` → open `http://localhost:4201`
2. Select text → Rewrite → AI returns staged output → click Apply → confirm content replaced
3. Confirm "Undo Apply" button appears in operation bar (amber styling)
4. Click "Undo Apply" → confirm content reverts to pre-Apply state
5. Confirm "Undo Apply" button disappears after undo
6. Switch files → confirm button stays hidden (cleared by `clearStagedOutput()`)

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` — commit 1 (button) can be reverted without touching commit 2 (wiring), though the feature will be inert.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.

---

## 9. Deviations Allowed

- **`preApplyContent` property doesn't exist yet** → Tasks 1–4 are not complete. STOP — do not implement Task 5 before its dependencies.
- **Task 1 spec file (`app.component.spec.ts`) uses a different TestBed setup than shown** → adapt the undo tests to match the existing `beforeEach` / mock setup. Log as deviation in commit body.
- **`onContentChange` is private** → if Task 4 didn't make it public, call it via bracket notation in tests (`(component as any).onContentChange`) or change the spy target. Log as deviation.
- **Operation bar template structure changed by another task** → insert the Undo Apply button after Revert and before Generate Spec, preserving relative order. Log as deviation if the anchor elements moved.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task adds a single-level undo for the Apply action only. It does not cover broader undo/redo functionality, nor does it extend the existing `historyStack` mechanism (which serves iterate/generateSpec/revert, a separate undo domain).

- **Multi-level undo** — deferred; requires an undo-tree or deeper stack design. Revisit if user feedback shows single-level is insufficient.
- **Redo after Undo Apply** — deferred; would need a `redoContent` slot or the undo tree. Not warranted until the single-level pattern proves limiting.
- **Keyboard shortcut (Cmd+Z) for Undo Apply** — deferred to avoid conflicting with Monaco editor's built-in undo. Needs design decision on keybinding scope (editor-focused vs. app-level).
- **Undo for iterate/revert/generateSpec** — already handled by the existing `historyStack` + Revert button. Do not merge the two undo mechanisms.
- **Comprehensive data-test audit** — Task 6 covers this. This task adds `data-test="undo-apply"` to the new button only.
- **Toast/notification on undo** — no toast needed; the content change is immediately visible in the editor.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale (Task 5 section)
- [Epic](./epic.md) — Task scope
- [Timeline](./timeline.md) — Status tracking (update after done)