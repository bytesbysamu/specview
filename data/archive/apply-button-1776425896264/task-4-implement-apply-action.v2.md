Now I have all the context needed. Here's the implementation guide:

# Task 4: Implement Apply Action

**Purpose**: Add the `applyToEditor()` method that promotes staged AI output into the editor, stores a pre-apply snapshot for undo, and triggers auto-save — completing the stage→apply pipeline started by Tasks 1–2.

**Effort**: 2h

**Dependencies**: Task 1 (staging state properties `stagedOutput`, `preApplyContent`, `clearStagedOutput()`), Task 2 (TextOutputComponent with `(apply)` EventEmitter)

**Parallel With**: Task 3 (wire operations to staging)

**Blocks**: Task 5 (Undo Apply — needs `preApplyContent` populated by this task)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Tasks 1 and 2 established the staging infrastructure: `stagedOutput` and `preApplyContent` properties on AppComponent, the `clearStagedOutput()` reset method, and the TextOutputComponent that renders staged AI output with Apply and Dismiss buttons. This task closes the loop by adding `applyToEditor()` — the method bound to the Apply button's `(apply)` event. When fired, it stores the current editor content in `preApplyContent` (creating the undo point Task 5 will consume), replaces `this.content` with `this.stagedOutput`, clears `stagedOutput` (which hides the panel), and calls `onContentChange()` to trigger auto-save through the existing `saveSubject` debounce path. The editor picks up the new content automatically via its `[content]` input setter (`editor.component.ts:25-30`), which calls `editor.setValue()` when the value changes. No direct `editor.replaceSelection()` call needed.

**Trade-offs considered**:
- **Selection-level replacement** (replace only highlighted text) — rejected because the architecture specifies full-content replacement; compound workflows need each operation to read the entire document, and selection-level replacement would force re-selecting after every Apply
- **Auto-apply** (push AI result straight into editor, skip manual step) — rejected because explicit user action is a design principle; the staging panel exists precisely to let users preview before committing
- **Route Apply through `onOperate()` switch** — rejected because Apply acts on staging state, not an AI operation; a direct template-bound method is simpler and matches the architecture's design decision table

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- src/app/app.component.ts src/app/app.component.spec.ts   # Confirm target files are clean
npx ng test --watch=false 2>&1 | tail -20     # Record baseline pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: confirm Task 1's staging-state tests pass. Record the count (expected: at least 2–3 from Task 1).

---

## 3. Files

### To Create (new)
None.

### To Modify (cite CODEBASE CONTEXT)
- `src/app/app.component.ts` — add `applyToEditor()` method after `clearStagedOutput()` (Task 1); add `(apply)="applyToEditor()"` binding on the `<app-text-output>` element (Task 2 placed it in the template between `</main>` and `<app-output-panel>`)
- `src/app/app.component.spec.ts` — add 6 test cases for `applyToEditor()` behavior (file created by Task 1)

### To Leave Alone
- `src/app/components/text-output/text-output.component.ts` — already emits `apply` via `@Output() apply = new EventEmitter<void>()` (Task 2); no changes needed
- `src/app/components/text-output/text-output.component.spec.ts` — Task 2's tests cover the component's event emission
- `src/app/components/operation-bar/operation-bar.component.ts` — Undo Apply button is Task 5's scope; do not touch
- `src/app/components/output-panel/output-panel.component.ts` — SSE streaming panel for implementation tasks; unrelated
- `src/app/services/ai.service.ts` — AI operation wiring is Task 3's scope
- `server.js` — backend unchanged

---

## 4. Implementation Steps

### Step 1: Add `applyToEditor()` method

**Action**: Add a public method on `AppComponent` immediately after the `clearStagedOutput()` method (placed by Task 1). The method implements the state transition from the architecture doc's state table: Apply event → `preApplyContent` = current content, `content` = `stagedOutput`, `stagedOutput` = cleared, auto-save triggered.

**File**: `src/app/app.component.ts`

**Pattern** (from architecture doc, Task 4 section):
```typescript
applyToEditor(): void {
  this.preApplyContent = this.content;
  this.content = this.stagedOutput;
  this.stagedOutput = '';
  this.onContentChange(this.content);
}
```

This is the complete method — no additional logic. `onContentChange()` (`app.component.ts:726`) updates the project cache and pushes to `saveSubject` for debounced auto-save. The editor's `[content]` input setter (`editor.component.ts:25-30`) picks up the new `this.content` value via Angular change detection and calls `editor.setValue()`.

**Verify**: `npx ng build 2>&1 | tail -5` — expect zero compilation errors.

### Step 2: Wire `(apply)` output binding in the template

**Action**: Locate the `<app-text-output>` element in the inline template (added by Task 2, positioned between `</main>` and `<app-output-panel>`). Add `(apply)="applyToEditor()"` to its bindings. If `(dismiss)="clearStagedOutput()"` is not already present, add it too — `clearStagedOutput()` exists from Task 1 and dismiss is the natural pair to apply on the same component.

**File**: `src/app/app.component.ts` (inline template)

**Pattern**: The `<app-text-output>` element should end up with these bindings:
```html
<app-text-output
  [output]="stagedOutput"
  [loading]="loading"
  (apply)="applyToEditor()"
  (dismiss)="clearStagedOutput()">
</app-text-output>
```

If Task 2 already wired `(apply)` to a no-op or placeholder, replace the handler with `applyToEditor()`. If `(apply)` is already bound to `applyToEditor()`, skip this step.

**Verify**: `npx ng build 2>&1 | tail -5` — zero compilation errors. If the dev server is running, open `http://localhost:4201`, trigger an AI operation (requires Task 3), and confirm the Apply button is visible on the text output panel.

### Step 3: Add tests for `applyToEditor()`

**Action**: Add a `describe('applyToEditor', ...)` block to `src/app/app.component.spec.ts` with 6 test cases covering the full state transition.

**File**: `src/app/app.component.spec.ts`

**Pattern**: See section 5 (Tests) for complete assertion bodies.

**Verify**: `npx ng test --watch=false 2>&1 | tail -20` — all 6 new tests pass, zero regressions on existing tests.

---

## 5. Tests

Add this `describe` block inside the existing `describe('AppComponent', ...)` in `src/app/app.component.spec.ts`. Match the TestBed configuration and `component` variable reference established by Task 1. Test names follow `condition_expectedOutcome` convention per architecture principles.

```typescript
describe('applyToEditor', () => {
  it('contentIsOriginal_setsPreApplyContentToOriginal', () => {
    component.content = 'original document';
    component.stagedOutput = 'AI result';

    component.applyToEditor();

    expect(component.preApplyContent).toBe('original document');
  });

  it('stagedOutputSet_replacesContentWithStagedOutput', () => {
    component.content = 'original document';
    component.stagedOutput = 'AI result';

    component.applyToEditor();

    expect(component.content).toBe('AI result');
  });

  it('afterApply_clearsStagedOutput', () => {
    component.content = 'original';
    component.stagedOutput = 'replacement';

    component.applyToEditor();

    expect(component.stagedOutput).toBe('');
  });

  it('afterApply_triggersOnContentChange', () => {
    spyOn(component, 'onContentChange');
    component.content = 'original';
    component.stagedOutput = 'replacement';

    component.applyToEditor();

    expect(component.onContentChange).toHaveBeenCalledWith('replacement');
  });

  it('emptyContent_applySetsPreApplyToEmpty', () => {
    component.content = '';
    component.stagedOutput = 'generated from scratch';

    component.applyToEditor();

    expect(component.preApplyContent).toBe('');
    expect(component.content).toBe('generated from scratch');
  });

  it('secondApply_overwritesPreviousPreApplyContent', () => {
    component.content = 'first version';
    component.stagedOutput = 'second version';
    component.applyToEditor();

    component.stagedOutput = 'third version';
    component.applyToEditor();

    expect(component.preApplyContent).toBe('second version');
    expect(component.content).toBe('third version');
  });
});
```

---

## 6. Commit Plan

Single commit — this task is one logical unit (method + binding + tests):

1. `feat(editor): implement Apply action — promote staged output to editor content`
   - `src/app/app.component.ts`: add `applyToEditor()` method, wire `(apply)` event on `<app-text-output>`
   - `src/app/app.component.spec.ts`: 6 tests for apply state transitions

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npx ng test --watch=false
```

**Expected delta**: N → N+6 passing (6 new tests for `applyToEditor`). Zero pre-existing tests broken.

If Karma hangs or chrome is unavailable:
```bash
npx ng build
```
Must compile with zero errors — confirms the method exists, types match, and template bindings resolve.

---

## 8. Rollback

- **Per-step**: single commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.

---

## 9. Deviations Allowed

- **`<app-text-output>` already has `(apply)="applyToEditor()"` binding** from Task 2 → skip Step 2's template change; note in commit body
- **`(dismiss)="clearStagedOutput()"` is already wired** → do not re-add; skip that part of Step 2
- **Test file uses a different TestBed setup** than assumed (e.g. different mock structure, different `component` variable name) → match the existing setup pattern from Task 1; translate silently but note in commit body
- **`onContentChange` is difficult to spy on** (e.g. arrow function or different binding) → verify auto-save through the `saveSubject` observable or test the downstream effect (project cache update); note in commit body
- **`clearStagedOutput()` does not exist** → STOP and flag; Task 1 is a hard dependency and must be merged before starting this task
- **Task 2's `TextOutputComponent` does not exist in imports or template** → STOP and flag; Task 2 is a hard dependency

---

## 10. Out of Scope

This task adds the Apply method and its template binding — a single method, a single binding, and tests. It does NOT populate `stagedOutput` (that's Task 3) or consume `preApplyContent` for undo (that's Task 5). Each task has one job.

- **Wiring AI operations to `stagedOutput`** — Task 3's scope. Without Task 3 merged, `stagedOutput` stays empty and Apply has nothing to promote. This task is correct either way; the method works regardless of how `stagedOutput` gets populated.
- **Undo Apply** — Task 5 adds `undoApply()` and the operation bar button that reads `preApplyContent`. This task writes `preApplyContent` but does not read it.
- **Conditional visibility of the text output panel** — `*ngIf="stagedOutput || loading"` (or equivalent) should have been set by Task 2 on the `<app-text-output>` element. If missing, flag as a deviation — do not add it here.
- **History stack integration** — Apply does NOT push to `historyStack`. The architecture intentionally separates staging undo (`preApplyContent`, one level) from iteration undo (`historyStack`, multi-level). Do not conflate them.
- **Markdown rendering in the output panel** — the architecture chose plain `<pre>` over rendered markdown. Do not add a markdown renderer to the text output component.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, state transition table, execution flow
- [Epic](./epic.md) — Task scope and ordering
- [Timeline](./timeline.md) — Update status after done