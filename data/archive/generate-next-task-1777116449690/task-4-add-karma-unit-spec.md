# Task 4: Add Karma Unit Spec

## 1. Context

Task 4 closes the automated verification loop for the two behaviors introduced by Tasks 1–3: action emission on click and disabled-state rendering when generation is in flight. Without this spec, the sidebar's new `canGenerateTask` / `generatingTask` inputs and the `'generate-task'` emission are covered only by manual smoke testing. The spec mounts `SidebarComponent` in isolation using Angular's `TestBed`, sets inputs directly (no `AppComponent` host required), and makes concrete assertions against the `(action)` output EventEmitter and the button's `disabled` attribute — the same seam that `AppComponent` drives at runtime. This gives CI a fast, headless regression guard that is structurally coupled to the component contract, not to the host integration.

**Trade-offs considered:**
- **E2E extension (Playwright/Cypress)** — rejected because the E2E2 epic is in flight; extending page objects mid-cycle introduces merge risk with no proportionate benefit over a unit spec for this thin surface.
- **Angular Testing Library (`@testing-library/angular`)** — considered as a higher-level query API; rejected in favor of standard Angular `TestBed` + `By.css` because no other spec in this project imports `@testing-library/angular`, so adding a new dependency here would be an out-of-scope infrastructure change.
- **`TestBed` + Jasmine (chosen)** — the default Angular 19 test stack; already configured by the project's `karma.conf.js` and `angular.json`; no new dependencies; matches the framework any future contributor will expect to find in a `.spec.ts` file.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# 1. Confirm working tree is clean on targets
git -C {WORKSPACE} status
git -C {WORKSPACE} diff HEAD -- web/src/app/components/sidebar/sidebar.component.ts

# 2. Confirm Tasks 1–3 are merged (inputs and union must exist before writing the spec)
grep -n "canGenerateTask\|generatingTask\|generate-task" \
  {WORKSPACE}/web/src/app/components/sidebar/sidebar.component.ts

# 3. Confirm spec file does not already exist
ls {WORKSPACE}/web/src/app/components/sidebar/sidebar.component.spec.ts 2>&1

# 4. Record baseline test count
cd {WORKSPACE}/web && npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -5
```

**If working tree is dirty on `sidebar.component.ts`**: stash or commit unrelated changes before proceeding. Tasks 1–3 must be fully merged; if the `grep` in step 2 returns no matches, stop and do not proceed — the component contract this spec tests does not yet exist.

**Baseline recorded**: N / N passing (executor fills in from step 4 output).

---

## 3. Files

### To Create (new)
- `web/src/app/components/sidebar/sidebar.component.spec.ts` — Karma/Jasmine spec for `SidebarComponent`; covers the two behaviors introduced by Tasks 1–3; depends on `SidebarComponent`'s `@Input() canGenerateTask`, `@Input() generatingTask`, and `@Output() action` as established by Task 2.

### To Modify
*(none — this task adds one file only)*

### To Leave Alone
- `web/src/app/components/sidebar/sidebar.component.ts` — component under test; must not be modified during this task; its contract is the input to the spec.
- `web/src/app/app.component.ts` — the host; AppComponent handler tests are explicitly out of scope (see §10).
- `web/karma.conf.js` — test runner config; no changes needed.
- `web/angular.json` — build/test config; no changes needed.
- `{WORKSPACE}/spec-doc/api/` — Flask backend; entirely unrelated.

---

## 4. Implementation Steps

### Step 1: Read the component contract

**Action**: Before writing a single line of the spec, read the post-Tasks-1-3 sidebar component in full. Confirm the exact names of the two new `@Input()` properties, the `@Output()` property name, the busy-state button label text, and which existing `@Input()` properties (e.g. `projects`, `selectedProjectId`, `selectedFile`) have no default and must be supplied in `beforeEach` to avoid `undefined` errors at `fixture.detectChanges()`.

**File**: `web/src/app/components/sidebar/sidebar.component.ts` (cite Tasks 1–3 result)

**Pattern** — look for these shapes:
```typescript
// Task 1 result — union includes 'generate-task'
export type SidebarAction = 'implement' | 'copy' | ... | 'generate-task';

// Task 2 result — two new inputs, one existing output
@Input() canGenerateTask: boolean = false;
@Input() generatingTask:  boolean = false;
@Output() action = new EventEmitter<SidebarAction>();

// Task 2 result — button in sidebar-actions block (lines ~73–92 area)
// [disabled]="!canGenerateTask || generatingTask"
// (click)="action.emit('generate-task')"
// label: generatingTask ? '<busy-text>' : 'Generate Next Task'
```

**Verify**: The `grep` from Pre-flight step 2 already confirmed these names exist. If the output property is named anything other than `action`, note it as a deviation and update all references in the spec.

---

### Step 2: Create the spec file

**Action**: Create `web/src/app/components/sidebar/sidebar.component.spec.ts` with the complete spec below. Before writing, replace any `<fill-from-step-1>` tokens with values confirmed in Step 1.

**File**: `web/src/app/components/sidebar/sidebar.component.spec.ts` **(new)**

**Pattern / complete implementation**:

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { SidebarComponent } from './sidebar.component';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns the "Generate Next Task" button from the fixture, or undefined if
 * it is not in the DOM.  Matches on stable text so the spec does not couple
 * to CSS selectors or element order.
 */
function getGenerateBtn(
  fixture: ComponentFixture<SidebarComponent>
): HTMLButtonElement | undefined {
  return (fixture.debugElement.queryAll(By.css('button'))
    .map(de => de.nativeElement as HTMLButtonElement)
    .find(el => el.textContent?.includes('Generate Next Task') ||
                el.textContent?.includes('Generating')));  // covers busy label too
}

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

describe('SidebarComponent — generate-task action', () => {
  let fixture: ComponentFixture<SidebarComponent>;
  let component: SidebarComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent],   // standalone component — import directly
    }).compileComponents();

    fixture   = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;

    // Satisfy any required @Inputs that the component reads on init.
    // Executor: adjust this block if the component has additional required
    // inputs without defaults (confirmed in Step 1).
    component.projects          = [];
    component.selectedProjectId = null;
    component.selectedFile      = null;
    component.canGenerateTask   = false;
    component.generatingTask    = false;

    fixture.detectChanges();
  });

  // -------------------------------------------------------------------------
  // Behavior A: clicking the button emits 'generate-task' from (action)
  // -------------------------------------------------------------------------

  it('emits "generate-task" when the Generate Next Task button is clicked', () => {
    // Arrange
    const emitted: string[] = [];
    component.action.subscribe((a: string) => emitted.push(a));

    component.canGenerateTask = true;
    component.generatingTask  = false;
    fixture.detectChanges();

    // Act
    const btn = getGenerateBtn(fixture);
    expect(btn).toBeDefined('Generate Next Task button must be present in the template');
    btn!.click();
    fixture.detectChanges();

    // Assert
    expect(emitted).toContain(
      'generate-task',
      'clicking the button must emit the "generate-task" action string'
    );
  });

  // -------------------------------------------------------------------------
  // Behavior B: generatingTask = true disables the button and updates label
  // -------------------------------------------------------------------------

  it('disables the button and changes its label when generatingTask is true', () => {
    // Arrange
    component.canGenerateTask = true;
    component.generatingTask  = true;
    fixture.detectChanges();

    // Act
    const btn = getGenerateBtn(fixture);
    expect(btn).toBeDefined('Generate Next Task button must be present when generatingTask is true');

    // Assert — disabled
    expect(btn!.disabled).toBeTrue(
      'button must be disabled when generatingTask is true'
    );

    // Assert — label has changed from the idle text
    // The busy label is implementation-defined (e.g. "Generating…"); we only
    // assert it is NOT the idle label, so the spec survives minor copy changes.
    expect(btn!.textContent?.trim()).not.toBe(
      'Generate Next Task',
      'button label must change from "Generate Next Task" when busy'
    );
  });

  // -------------------------------------------------------------------------
  // Boundary: button stays disabled when canGenerateTask is false
  // -------------------------------------------------------------------------

  it('keeps the button disabled when canGenerateTask is false regardless of generatingTask', () => {
    component.canGenerateTask = false;
    component.generatingTask  = false;
    fixture.detectChanges();

    const btn = getGenerateBtn(fixture);
    if (!btn) {
      // If the button is conditionally rendered (*ngIf) instead of [disabled],
      // the button may be absent when canGenerateTask is false — both are valid
      // implementations; this test handles both.
      expect(btn).toBeUndefined(
        'button may be absent when canGenerateTask is false (*ngIf implementation)'
      );
      return;
    }

    expect(btn.disabled).toBeTrue(
      'button must be disabled when canGenerateTask is false'
    );
  });
});
```

**Verify**:
```bash
cd {WORKSPACE}/web && npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | grep -E "SUMMARY|FAILED|ERROR|Executed"
```
Expect: 3 new tests passing; 0 pre-existing failures.

---

## 5. Tests

The complete test bodies appear in Step 2 above. Summarized for review:

| # | Description | Assertion |
|---|---|---|
| 1 | Emits `'generate-task'` on click | `expect(emitted).toContain('generate-task')` |
| 2 | Disables button when `generatingTask` is true | `expect(btn.disabled).toBeTrue()` + `expect(btn.textContent?.trim()).not.toBe('Generate Next Task')` |
| 3 | Button disabled / absent when `canGenerateTask` is false | `expect(btn.disabled).toBeTrue()` *or* `expect(btn).toBeUndefined()` depending on `*ngIf` vs `[disabled]` implementation |

**Framework**: Karma + Jasmine (Angular 19 default). Uses `TestBed.configureTestingModule`, `ComponentFixture`, `By.css`, and `debugElement`. No additional dependencies required.

---

## 6. Commit Plan

**Executor instruction**: commit immediately after Step 2's verify command passes — not at the end of any larger batch.

1. `test(sidebar): add Karma spec for generate-task action and disabled state` — after Step 2 verify passes — files: `web/src/app/components/sidebar/sidebar.component.spec.ts` — what: 3 tests covering Behavior A (action emission), Behavior B (disabled state + label), and boundary case (canGenerateTask=false)

**Deviation logging**: if the spec required structural changes to accommodate the actual component shape (e.g. different required inputs, different output name, conditional rendering), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/web && npm test -- --watch=false --browsers=ChromeHeadless
```

**Expected delta**: baseline N → N+3 passing. Zero pre-existing tests broken. The three new tests map 1:1 to the three `it(...)` blocks in `sidebar.component.spec.ts`.

If `npm test` is not configured to run `ng test`, fall back to:
```bash
cd {WORKSPACE}/web && npx ng test --watch=false --browsers=ChromeHeadless
```

---

## 8. Rollback

- **Per-step**: there is one commit. Revert it with `git revert <sha>` — this deletes the spec file from history with no side effects on the component or the app.
- **Per-branch**: if the spec causes cascading failures (e.g. Angular compiler errors from a missing import), `git reset --hard <pre-task-sha>` on the feature branch. The only file introduced is the spec; no production code was changed.

---

## 9. Deviations Allowed

- **`@Output()` is not named `action`** — read the actual component, rename every `component.action` reference in the spec to match. Note in commit body.
- **Required `@Input()` properties differ from assumed** — the `beforeEach` block lists the ones the architecture implies; if `fixture.detectChanges()` throws `TypeError: Cannot read properties of undefined`, inspect the component's `ngOnInit` for the missing input and add it to the `beforeEach` block. Note in commit body.
- **Button uses `*ngIf` instead of `[disabled]`** — test 3 already handles this with the `if (!btn)` branch. No change needed unless the other two tests also encounter absent buttons (which would indicate `canGenerateTask = true` is not enabling the button — a Task 2 defect to fix separately).
- **Busy label is absent / empty rather than changed text** — if the button has no text at all when `generatingTask = true` (e.g. replaced by a spinner icon only), change the label assertion to `expect(btn!.textContent?.trim()).not.toBe('Generate Next Task')` — which is already written that way in the spec above. No change needed.
- **`projects`, `selectedProjectId`, `selectedFile` not valid `@Input()` names** — inspect the component for its actual input property names and update the `beforeEach` accordingly. Note in commit body.
- **Test framework mismatch** (e.g. project has migrated to Jest) — translate the spec to Jest (`describe`/`it`/`expect` APIs are identical; replace `fixture.debugElement.queryAll(By.css(...))` with `screen.queryAllByRole('button')`). Note in commit body.
- **Side-effect required** (e.g. `npm install` for a missing test dependency) → STOP, mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

Task 4 is narrowly scoped to the two behaviors called out in the epic: click emission and disabled-state rendering. Any work that extends beyond the `SidebarComponent` test boundary, modifies existing tests, or sets up new infrastructure is out of scope for this task. The following items are explicitly deferred:

- **`AppComponent` handler tests** — the `case 'generate-task'` branch, `canGenerateTask` predicate logic, and the three outcome paths (success / null / error) in `app.component.ts` are not covered here. They are the integration of Tasks 2 and 3 at runtime; a future task should add a focused `app.component.spec.ts` block once the feature ships and the handler contract is stable.
- **E2E coverage** — the E2E2 epic is in flight; extending page objects or Playwright/Cypress specs to cover the generate-task button mid-cycle carries merge risk. Revisit after E2E2 closes.
- **Streaming / progress-granularity tests** — the architecture defers SSE streaming to a follow-up; there is nothing to test here.
- **`ImplementationGuideService` unit tests** — the service already exists and owns the prompt-build / file-write logic; any gaps in its coverage are a separate task.
- **Bootstrap loop behavioral tests** — the loop already calls `generateNextTask()` correctly; modifying its test coverage is unrelated to this epic and should not be bundled here.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale; component graph and Input-Driven Disabled State pattern
- [Epic](./epic.md) — Task scope and port budget
- [Timeline](./timeline.md) — Status tracking (mark Task 4 complete after verification passes)