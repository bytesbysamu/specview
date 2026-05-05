# Task 3: Wire Operations to Stage Instead of Replace

**Purpose**: Refactor `AppComponent.applyResult()` to write AI results to `stagedOutput` (the staging panel from Tasks 1–2) instead of calling `editor.replaceSelection()`, so users can review output before promoting it.

**Effort**: 1h

**Dependencies**: Task 1 (staging state properties) and Task 2 (TextOutputComponent) must be completed first

**Parallel With**: —

**Blocks**: Task 4 (Apply action — wires the button that promotes staged output into the editor)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task is the pivot point of the Apply Button capability. Today, all five single-shot AI operations (rewrite, expand, compress, clarify, generate) call `applyResult()` which immediately replaces the editor selection via `this.editor.replaceSelection(newText)`. After this task, those same five operations call `stageResult()` which writes to `this.stagedOutput` — a property that Task 1 added and that Task 2's `TextOutputComponent` is already bound to via `[output]="stagedOutput"`. The result: AI output appears in a read-only staging panel instead of overwriting the editor in-place, letting the user review before applying. Iterate, GenerateSpec, and Revert bypass the staging flow entirely — they set `this.content` directly as they do today.

**Trade-offs considered**:
- **New method alongside `applyResult`** — rejected because both methods would exist in the codebase with near-identical call sites, inviting confusion about which to use. A rename makes the intent unambiguous.
- **Clear staged output only on dismiss** — rejected because the architecture's state table specifies "New AI operation starts → stagedOutput cleared." Leaving stale output visible alongside a new loading spinner would confuse users.
- **Rename + body change on `applyResult`** — preferred because all five call sites reference the same method; renaming it once redirects everything with zero risk of a missed call site.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                          # Flag any unrelated M/?? entries
git diff HEAD -- src/app/app.component.ts           # Confirm Tasks 1+2 changes are committed
git diff HEAD -- src/app/app.component.spec.ts      # Confirm Task 1 test file is committed
npx ng build --configuration development 2>&1 | tail -5   # Confirm clean compile after Tasks 1+2
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: build succeeds; note Karma test count from Task 1 (expect ≥2 passing from Task 1's spec file).

---

## 3. Files

### To Create (new)
None.

### To Modify (cite CODEBASE CONTEXT)
- `src/app/app.component.ts` — rename `applyResult()` → `stageResult()`, change body from `this.editor.replaceSelection(newText)` to `this.stagedOutput = newText`, add `this.stagedOutput = ''` at top of `onOperate()` to clear previous staged output when a new operation starts
- `src/app/app.component.spec.ts` — add 4 tests covering: staging behavior for single-shot ops, non-call of `replaceSelection`, clearing on new operation, iterate/revert bypassing staging (file created by Task 1)

### To Leave Alone
- `src/app/components/text-output/text-output.component.ts` — Task 2's component; already bound to `stagedOutput` via `[output]` input; no changes needed
- `src/app/components/text-output/text-output.component.spec.ts` — Task 2's tests; cover component inputs/outputs, not staging wiring
- `src/app/components/operation-bar/operation-bar.component.ts` — Task 5 adds Undo Apply button here; not this task's scope
- `src/app/services/ai.service.ts` — backend calls unchanged; the service returns the same `TextOperationResponse`
- `src/app/components/editor/editor.component.ts` — `replaceSelection()` at line 129 remains available but is no longer called by single-shot operations
- `server.js` — backend unchanged

---

## 4. Implementation Steps

### Step 1: Rename `applyResult` → `stageResult` and change body

**Action**: Find the `applyResult` method (currently line 837 pre-Tasks-1/2; search by name after prior tasks shift line numbers). Rename to `stageResult`. Replace the body: instead of `this.editor.replaceSelection(newText)`, set `this.stagedOutput = newText`.

**File**: `src/app/app.component.ts`

**Pattern**:
```typescript
// BEFORE (current shape)
private applyResult(newText: string): void {
  this.loading = false;
  this.editor.replaceSelection(newText);
}

// AFTER
private stageResult(newText: string): void {
  this.loading = false;
  this.stagedOutput = newText;
}
```

All five `subscribe.next` callbacks in `onOperate()` call `this.applyResult(response.text)`. Because the method is renamed, update each call site from `this.applyResult(response.text)` to `this.stageResult(response.text)`. There are exactly five occurrences — one each for rewrite, expand, compress, clarify, generate.

**Verify**: `grep -n 'applyResult\|stageResult' src/app/app.component.ts` — expect 6 hits for `stageResult` (1 definition + 5 call sites), 0 hits for `applyResult`.

### Step 2: Clear `stagedOutput` when a new operation starts

**Action**: At the top of `onOperate()`, immediately after `this.loading = true`, add `this.stagedOutput = '';`. This ensures that starting any operation (including iterate/revert) discards stale staged output from a previous operation.

**File**: `src/app/app.component.ts`

**Pattern**:
```typescript
onOperate(event: OperationEvent): void {
  this.loading = true;
  this.stagedOutput = '';    // ← add this line

  switch (event.operation) {
    // ... existing cases unchanged
  }
}
```

**Verify**: `npx ng build --configuration development 2>&1 | tail -5` — expect clean compile, zero errors.

### Step 3: Add tests for staging behavior

**Action**: Open `src/app/app.component.spec.ts` (created by Task 1) and add a `describe('stageResult wiring')` block with 4 test cases.

**File**: `src/app/app.component.spec.ts`

**Pattern**: See Section 5 (Tests) below for complete assertion bodies.

**Verify**: `npx ng test --no-watch --browsers=ChromeHeadless 2>&1 | tail -20` — expect all tests passing including the 4 new ones.

---

## 5. Tests

Add the following `describe` block to `src/app/app.component.spec.ts`. This block sits after Task 1's existing `describe('staging state')` block. Tests are Karma + Jasmine, matching the project's `angular.json` test builder (`@angular-devkit/build-angular:karma`).

The tests assume the TestBed configured by Task 1 is available (with `AiService`, `HttpClient`, `ProjectsService`, `ImplementationService`, and `TimelineParserService` mocked). Adjust the reference to the mocked `AiService` instance if Task 1 used a different variable name — the shape is the same.

```typescript
describe('stageResult wiring', () => {
  it('rewriteOperation_setsStagedOutputInsteadOfReplacingSelection', () => {
    // Arrange
    const mockResponse = { text: 'rewritten text', latencyMs: 42 };
    aiService.rewrite = jasmine.createSpy('rewrite').and.returnValue(of(mockResponse));
    component.selectedText = 'original selection';
    component.hasSelection = true;
    // Spy on editor.replaceSelection (ViewChild set by fixture)
    const editorEl = fixture.debugElement.query(By.directive(EditorComponent));
    const editorInstance = editorEl?.componentInstance as EditorComponent;
    const replaceSpy = spyOn(editorInstance, 'replaceSelection');

    // Act
    component.onOperate({ operation: 'rewrite', instruction: 'improve this' });

    // Assert
    expect(component.stagedOutput).toBe('rewritten text');
    expect(component.loading).toBeFalse();
    expect(replaceSpy).not.toHaveBeenCalled();
  });

  it('allFiveSingleShotOps_flowThroughStageResult', () => {
    // Verify each of the 5 operations sets stagedOutput
    const ops: Array<{ op: string; spy: string; args?: any }> = [
      { op: 'rewrite', spy: 'rewrite' },
      { op: 'expand', spy: 'expand' },
      { op: 'compress', spy: 'compress' },
      { op: 'clarify', spy: 'clarify' },
      { op: 'generate', spy: 'generate' },
    ];

    ops.forEach(({ op, spy: spyName }) => {
      const mockResp = { text: `${op}-result`, latencyMs: 10 };
      (aiService as any)[spyName] = jasmine.createSpy(spyName).and.returnValue(of(mockResp));
      component.selectedText = 'some text';
      component.hasSelection = true;

      component.onOperate({ operation: op as any, instruction: 'test' });

      expect(component.stagedOutput).toBe(`${op}-result`,
        `Expected stagedOutput to be set for operation '${op}'`);
      expect(component.loading).toBeFalse();
    });
  });

  it('newOperation_clearsPreviousStagedOutput', () => {
    // Arrange — simulate leftover staged output from a prior operation
    component.stagedOutput = 'stale result from previous op';
    const mockResponse = { text: 'fresh result', latencyMs: 10 };
    aiService.expand = jasmine.createSpy('expand').and.returnValue(of(mockResponse));
    component.selectedText = 'text';
    component.hasSelection = true;

    // Act
    component.onOperate({ operation: 'expand' });

    // Assert — stagedOutput is the new result (was cleared then set)
    expect(component.stagedOutput).toBe('fresh result');
  });

  it('iterateOperation_doesNotSetStagedOutput', () => {
    // Arrange
    component.stagedOutput = 'leftover';
    component.baseSpecContent = 'base';
    component.content = 'current';
    const mockResponse = { text: 'iterated content', latencyMs: 10 };
    aiService.iterate = jasmine.createSpy('iterate').and.returnValue(of(mockResponse));

    // Act
    component.onOperate({ operation: 'iterate' });

    // Assert — stagedOutput was cleared at top of onOperate, NOT set to iterate result
    expect(component.stagedOutput).toBe('');
    // iterate sets this.content directly
    expect(component.content).toBe('iterated content');
  });
});
```

**Import requirements** (add at top of spec file if not already present from Task 1):
```typescript
import { of } from 'rxjs';
import { By } from '@angular/platform-browser';
import { EditorComponent } from './components/editor/editor.component';
```

---

## 6. Commit Plan

One commit — this is a single logical unit (rename + body change + clearing + tests):

1. `feat(editor): wire single-shot operations to stage instead of replace` — `src/app/app.component.ts`, `src/app/app.component.spec.ts`: rename `applyResult` → `stageResult`, change body to set `stagedOutput`, add clearing at top of `onOperate`, add 4 tests

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npx ng build --configuration development 2>&1 | tail -5
npx ng test --no-watch --browsers=ChromeHeadless 2>&1 | tail -20
```

**Expected delta**: Task 1+2 baseline test count → +4 passing. Zero pre-existing tests broken. Build compiles cleanly.

**Manual smoke check** (if dev server is running): trigger a Rewrite operation → confirm the result appears in the staging panel below the editor (not in the editor itself). Confirm the editor content is unchanged until Apply is wired (Task 4).

---

## 8. Rollback

- **Per-step**: single commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.

---

## 9. Deviations Allowed

- **Task 1 used a different property name than `stagedOutput`** → use whatever name Task 1 introduced; update all references in this guide accordingly; log in commit body.
- **Task 1's spec file uses a different variable name for the mocked `AiService`** → match the existing convention (e.g., `mockAiService` vs `aiService`); translate silently but note in commit body.
- **`applyResult` was already renamed by a prior task** → find the current method name that calls `this.editor.replaceSelection(newText)`; rename that; log deviation.
- **EditorComponent not renderable in TestBed** (Monaco dependency issue) → use `component.editor = { replaceSelection: jasmine.createSpy('replaceSelection') } as any` to stub the ViewChild directly; log deviation.
- **Line numbers shifted due to Tasks 1+2** → find targets by method name (`applyResult`, `onOperate`), not line number.
- **Side-effect required** (push, publish, schema change) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task redirects AI results to the staging panel but does NOT implement the mechanism to promote staged output into the editor. That is Task 4's job. After this task, clicking a single-shot operation will populate `stagedOutput` (visible in the staging panel), but the Apply button has no handler yet — the `(apply)` binding is wired by Task 4.

- **`applyToEditor()` method** — deferred to Task 4; that task adds the method and the `(apply)` template binding
- **`undoApply()` method and Undo Apply button** — deferred to Task 5; depends on Task 4
- **Dismiss handler on TextOutputComponent** — already wired by Task 2 to `clearStagedOutput()` from Task 1; no changes needed here
- **Error staging** — `handleError()` still shows an `alert()`; staging errors in the output panel is a potential follow-up but not in the epic
- **Streaming operations** — Iterate, GenerateSpec, and Revert set `this.content` directly; converting them to staging would change their UX semantics and is explicitly out of scope per the architecture

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, state transition table
- [Epic](./epic.md) – Task scope and dependencies
- [Timeline](./timeline.md) – Status tracking (update after done)