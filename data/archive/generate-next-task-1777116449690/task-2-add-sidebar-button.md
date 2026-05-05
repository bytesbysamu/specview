The frontend files are outside the permitted read scope for this session. I have sufficient context from the architecture document (which cites specific line numbers) to write the guide accurately. Proceeding now.

---

# Task 2: Add Sidebar Button — Implementation Guide

## 1. Context

Task 2 adds the visible entry point for "Generate Next Task": a button rendered inside `SidebarComponent`'s existing `sidebar-actions` block, governed by two new `@Input()` bindings (`canGenerateTask`, `generatingTask`) pushed down from the host. The component emits `'generate-task'` via its existing typed action output — the same dispatch path used by every existing action. Task 1 has already added `'generate-task'` to the `SidebarAction` union, so the TypeScript boundary is live; Task 2 completes the rendering half of the contract. Task 3 (AppComponent handler) and Task 4 (Karma spec) both depend on the shape this task establishes.

**Trade-offs considered (≤3 bullets)**:
- **Derive `canGenerateTask` inside `SidebarComponent` from a passed-in project object** — rejected because it couples the sidebar to the project model shape; the presentational-component pattern already established by existing action buttons requires state to arrive as scalar booleans.
- **Single combined `@Input() generateState: 'idle' | 'disabled' | 'busy'`** — rejected because it introduces a component-local enum that has no counterpart in the host, requiring translation on both sides with no simplification gain.
- **Two separate `@Input()` booleans `canGenerateTask` / `generatingTask`** — preferred because it matches the existing input pattern for other conditional sidebar controls, keeps the template binding readable, and lets the host change either flag independently.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
# From the Angular project root ({WORKSPACE} = /Users/sam/Projects/2026/spec-doc)
cd {WORKSPACE}

git status                                         # Assert: no untracked/modified entries on target files
git diff HEAD -- src/app/sidebar/sidebar.component.ts   # Confirm clean; also verify exact file path here
git diff HEAD -- src/app/sidebar/sidebar.component.spec.ts

# Confirm Task 1 pre-condition: 'generate-task' must already be in the SidebarAction union
grep "generate-task" src/app/sidebar/sidebar.component.ts
# Expected: at least one match showing 'generate-task' in the union string literal

# Record baseline test count
npm test -- --watch=false 2>&1 | tail -5
# Note the "X specs, 0 failures" line — record it as your baseline

# Confirm existing action button pattern (lines 73-92 per architecture doc)
sed -n '65,100p' src/app/sidebar/sidebar.component.ts
# Read the output carefully: confirm the emit method name, CSS class, disabled binding style
```

**If the exact path `src/app/sidebar/sidebar.component.ts` does not exist**: run `find . -name "sidebar.component.ts" -not -path "*/node_modules/*"` to locate it, then substitute throughout this guide.

**If working tree is dirty on target files**: stash or commit unrelated changes before proceeding.

**Baseline recorded**: _[executor fills in]_ / _[executor fills in]_ passing.

---

## 3. Files

### To Create (new)
_None._ Task 2 adds no new files; Task 4 creates the spec file.

### To Modify (cite architecture doc)
- `src/app/sidebar/sidebar.component.ts` — add `@Input() canGenerateTask: boolean` and `@Input() generatingTask: boolean` class members; add the "Generate Next Task" `<button>` inside the existing `<div class="sidebar-actions">` block (architecture doc: existing buttons at lines 73–92).

### To Leave Alone
- `src/app/app.component.ts` — the host handler and `canGenerateTask` predicate are Task 3's scope; touching this file here creates a merge conflict surface with Task 3.
- `src/app/sidebar/sidebar.component.spec.ts` — owned by Task 4; do not create or modify it in this task.
- All files in `{WORKSPACE}/api/` — backend is unaffected by a frontend-only change.

---

## 4. Implementation Steps

### Step 1: Confirm the emit method name and input pattern

**Action**: Read lines 1–100 of `sidebar.component.ts` to identify: (a) where `@Input()` bindings are declared, (b) the method or expression used to emit actions in existing buttons (e.g., `onAction('implement')` vs. `action.emit('implement')`), and (c) the CSS class applied to existing action buttons.

**File**: `src/app/sidebar/sidebar.component.ts` (existing)

**Pattern** — what you are reading for:
```typescript
// Somewhere in the class body — note the exact member name and call style
@Output() action = new EventEmitter<SidebarAction>();

// Inside template — note emit call style
<button class="<EXACT-CLASS>" (click)="<EXACT-EMIT-CALL>('implement')">…</button>
```

**Verify**: `grep -n "emit\|onAction\|\.action" src/app/sidebar/sidebar.component.ts | head -20` — record the exact call style; substitute it verbatim in Step 2.

---

### Step 2: Add the two @Input() bindings

**Action**: In `SidebarComponent`'s class body, add `canGenerateTask` and `generatingTask` alongside the existing `@Input()` declarations. Do not add defaults beyond `false`; do not add any derived logic.

**File**: `src/app/sidebar/sidebar.component.ts` (existing)

**Pattern** — insert after the last existing `@Input()` line:
```typescript
@Input() canGenerateTask: boolean = false;
@Input() generatingTask: boolean = false;
```

**Verify**:
```bash
grep -n "canGenerateTask\|generatingTask" src/app/sidebar/sidebar.component.ts
# Expected: two lines, both showing @Input() declarations, no other occurrences yet
```

---

### Step 3: Add the button to the template

**Action**: Inside the existing `<div class="sidebar-actions">` block (architecture doc: lines 73–92), append a `<button>` after the last existing action button. Use the **exact** emit call style confirmed in Step 1, the **exact** CSS class used by sibling buttons, and bind `[disabled]` and the label using the two new inputs.

**File**: `src/app/sidebar/sidebar.component.ts` (existing)

**Pattern** — adapt emit call style and CSS class from Step 1:
```html
<button
  class="<SAME-CLASS-AS-SIBLINGS>"
  [disabled]="!canGenerateTask || generatingTask"
  (click)="<EMIT-CALL-STYLE>('generate-task')"
>
  {{ generatingTask ? 'Generating…' : 'Generate Next Task' }}
</button>
```

> **Port note**: the `[disabled]` compound expression `!canGenerateTask || generatingTask` is the direct implementation of the architecture's "Input-Driven Disabled State" pattern (architecture.md §Patterns). Do not split into two separate `[disabled]` bindings.

**Verify**:
```bash
grep -A5 "Generate Next Task\|generate-task" src/app/sidebar/sidebar.component.ts
# Expected: the button element with [disabled] binding and (click) emitting 'generate-task'
```
Then serve the app locally and visually confirm the button appears in the sidebar when `canGenerateTask = true`:
```bash
npm start   # or ng serve --port=4201
# Open http://localhost:4201, inspect sidebar — button should render
```

---

## 5. Tests

> **Scope note**: Task 4 owns the canonical Karma spec file. The tests below are the complete behavioral assertions for the sidebar component's Task 2 surface. They MUST be written to pass before this task closes; Task 4 will incorporate them into the spec file without duplication.

The repo uses Karma + Angular `TestBed`. Match the existing sidebar spec pattern confirmed by pre-flight (inspect any `*.spec.ts` file under `src/app/sidebar/` for the `TestBed.configureTestingModule` shape used by existing sidebar specs).

```typescript
// src/app/sidebar/sidebar.component.spec.ts  — partial; Task 4 owns the full file
// Run these assertions against the component directly.

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { SidebarComponent } from './sidebar.component';

describe('SidebarComponent – Generate Next Task button (Task 2)', () => {

  let fixture: ComponentFixture<SidebarComponent>;
  let component: SidebarComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      // Use the same imports/declarations as existing sidebar specs in this file
      declarations: [SidebarComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
  });

  it('renders the Generate Next Task button when canGenerateTask is true', () => {
    component.canGenerateTask = true;
    component.generatingTask = false;
    fixture.detectChanges();

    const btn = fixture.debugElement.query(
      By.css('button[disabled]')
    );
    const allButtons: HTMLButtonElement[] = fixture.nativeElement.querySelectorAll('button');
    const generateBtn = Array.from(allButtons).find(
      (b) => b.textContent?.includes('Generate Next Task')
    );
    expect(generateBtn).toBeTruthy('Generate Next Task button must be present in DOM');
    expect(generateBtn!.disabled).toBe(
      false,
      'button must be enabled when canGenerateTask=true and generatingTask=false'
    );
  });

  it('disables the button when generatingTask is true', () => {
    component.canGenerateTask = true;
    component.generatingTask = true;
    fixture.detectChanges();

    const allButtons: HTMLButtonElement[] = fixture.nativeElement.querySelectorAll('button');
    const generateBtn = Array.from(allButtons).find(
      (b) => b.textContent?.includes('Generating') || b.textContent?.includes('Generate Next Task')
    );
    expect(generateBtn).toBeTruthy('button must be present regardless of generatingTask state');
    expect(generateBtn!.disabled).toBe(
      true,
      'button must be disabled when generatingTask=true'
    );
  });

  it('disables the button when canGenerateTask is false', () => {
    component.canGenerateTask = false;
    component.generatingTask = false;
    fixture.detectChanges();

    const allButtons: HTMLButtonElement[] = fixture.nativeElement.querySelectorAll('button');
    const generateBtn = Array.from(allButtons).find(
      (b) => b.textContent?.includes('Generate Next Task')
    );
    expect(generateBtn).toBeTruthy('button must render even when canGenerateTask=false');
    expect(generateBtn!.disabled).toBe(
      true,
      'button must be disabled when canGenerateTask=false'
    );
  });

  it('emits generate-task action when clicked while enabled', () => {
    component.canGenerateTask = true;
    component.generatingTask = false;
    fixture.detectChanges();

    const emitted: string[] = [];
    component.action.subscribe((a: string) => emitted.push(a));

    const allButtons: HTMLButtonElement[] = fixture.nativeElement.querySelectorAll('button');
    const generateBtn = Array.from(allButtons).find(
      (b) => b.textContent?.includes('Generate Next Task')
    );
    expect(generateBtn).toBeTruthy();
    generateBtn!.click();
    fixture.detectChanges();

    expect(emitted.length).toBe(1, 'action output must emit exactly once on click');
    expect(emitted[0]).toBe(
      'generate-task',
      'emitted value must be the string literal "generate-task"'
    );
  });

  it('shows Generating… label when generatingTask is true', () => {
    component.canGenerateTask = true;
    component.generatingTask = true;
    fixture.detectChanges();

    const allButtons: HTMLButtonElement[] = fixture.nativeElement.querySelectorAll('button');
    const generateBtn = Array.from(allButtons).find(
      (b) => b.textContent?.trim().startsWith('Generating')
    );
    expect(generateBtn).toBeTruthy(
      'button label must switch to Generating… when generatingTask=true'
    );
  });
});
```

**If the existing sidebar spec uses `imports: [SidebarComponent]` (standalone component) rather than `declarations`**: replace `declarations: [SidebarComponent]` with `imports: [SidebarComponent]` in `TestBed.configureTestingModule`. Inspect the nearest `*.spec.ts` in the same directory to confirm, and log the deviation in the commit.

---

## 6. Commit Plan

**Executor instruction**: run each commit immediately after completing the corresponding step. Do not batch commits at the end.

1. **`feat(sidebar): add canGenerateTask and generatingTask @Input bindings`** — after Step 2 — `src/app/sidebar/sidebar.component.ts`: adds the two `@Input()` property declarations.
2. **`feat(sidebar): render Generate Next Task button in sidebar-actions block`** — after Step 3 — `src/app/sidebar/sidebar.component.ts`: adds button template with `[disabled]` binding and `(click)` emit.
3. **`test(sidebar): add Task 2 behavioral assertions for generate-task button`** — after tests pass — `src/app/sidebar/sidebar.component.spec.ts`: five assertions covering enabled/disabled states, label switch, and action emission.

**Deviation logging**: if any step requires structural adaptation (e.g., standalone component, different emit style, different class name), prefix the commit body with `Deviations:` and one line per deviation. Example:
```
feat(sidebar): render Generate Next Task button in sidebar-actions block

Deviations: component is standalone; used imports: [SidebarComponent] in TestBed.
```

---

## 7. Verification

```bash
cd {WORKSPACE}
npm test -- --watch=false 2>&1 | tail -10
```

**Expected delta**: _[baseline N]_ → _[N + 5]_ passing. The five new assertions from Section 5 must all pass. Zero pre-existing tests broken.

Additionally, confirm TypeScript compilation is clean:
```bash
npx tsc --noEmit
# Expected: no errors
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>   # reverts the specific commit non-destructively
  ```
- **Per-branch**: if verification fails after all three commits and the failure cannot be isolated:
  ```bash
  git reset --hard <pre-task-sha>   # returns branch to state before Task 2 started
  ```
  Record `<pre-task-sha>` from `git log --oneline -5` during pre-flight.

---

## 9. Deviations Allowed

- **`sidebar.component.ts` path differs** — run `find . -name "sidebar.component.ts" -not -path "*/node_modules/*"` to locate it; substitute the correct path throughout and log it in commit 1's body.
- **Emit call style differs from pattern** (e.g., direct `this.action.emit()` inline vs. a method call) — match exactly what Step 1 reveals; do not introduce a new emit style.
- **Existing buttons use `[attr.disabled]` instead of `[disabled]`** — match the sibling pattern precisely; log in the commit body.
- **Component is standalone** (no `NgModule`) — adjust `TestBed.configureTestingModule` to use `imports: [SidebarComponent]`; log in test commit body.
- **Step N unlocks an obvious simplification for Step N+1** — take it; log one line in the commit body under `Deviations:`.
- **Side-effect required** (publish, push, schema migration) → **STOP**, mark **[REQUIRES APPROVAL]**, and surface to the task owner before proceeding.

---

## 10. Out of Scope

This task is responsible for the sidebar component's rendering surface and its two `@Input()` bindings only. It does not touch the host (`AppComponent`), the service, the backend, or the test infrastructure beyond the five baseline assertions. An executor who reads this task cleanly and finds an adjacent gap should stop at the boundary below rather than absorbing it.

- **`AppComponent` handler (`case 'generate-task'`)** — Task 3's scope; the two files are independent and can land in parallel. Editing `app.component.ts` here creates a merge risk.
- **`canGenerateTask` predicate logic** (requires active project + `epic.md` check) — computed in `AppComponent` per architecture; not sidebar business logic and must not be derived inside `SidebarComponent`.
- **Full Karma spec file** — Task 4 owns the canonical `sidebar.component.spec.ts`; the assertions in Section 5 are the seed that Task 4 will incorporate, not the final file.
- **Per-task targeting picker / `generateTaskByNum()`** — explicitly excluded from the architecture (architecture.md §What This System Does NOT Include); do not extend the service or add selection UI.
- **SSE / streaming progress indicator** — deferred until latency feedback confirms need; the spinner label (`Generating…`) is the v1 floor.
- **E2E coverage** — the E2E2 epic is in flight; extending page objects mid-cycle introduces merge risk with no proportionate benefit. Revisit after E2E2 closes.

**Rule for the executor**: if a change appears helpful but is listed here, stop and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Component graph, design decisions, patterns
- [Epic](./epic.md) – Full task scope and dependencies
- [Timeline](./timeline.md) – Update status to `in-progress` when Step 1 begins, `done` after Section 7 passes