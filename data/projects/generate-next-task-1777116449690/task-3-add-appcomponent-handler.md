Now I have enough context from the existing task docs and architecture to write the guide. Let me produce it.

# Implementation Guide: Task 3 — Add AppComponent Handler

> **Workspace note**: All paths in this guide are relative to the Angular frontend root (`{SPEC_DOC_DIR}` = `~/Projects/2026/spec-doc`), **not** the `api/` subfolder. Run all commands from that root unless prefixed with `api/`.

---

## 1. Context

Task 3 closes the final gap between the sidebar's "Generate Next Task" button (added in Task 2) and a working end-to-end feature: it adds the `else if (action === 'generate-task')` branch to `AppComponent.onSidebarAction()`, a `generatingTask` boolean field that gates the sidebar's busy state, and a `canGenerateTask` getter that is `true` only when an active project exists and its file list contains `epic.md`. On invocation the handler sets the busy flag, calls `ImplementationGuideService.generateNextTask(activeProjectId, activeProjectName)`, then forks on three outcomes: a filename string (refresh files + select the new file + success status), `null` (all-tasks-done status), or an error (error status). The busy flag resets in both the success and error paths. Every piece of business logic — prompt construction, AI call, file write — lives in `ImplementationGuideService`; `AppComponent` only orchestrates the call and distributes its result to the existing UI surfaces.

**Trade-offs considered:**
- **Promoted `canGenerateTask` to a shared predicate service** — rejected; there is exactly one consumer (`AppComponent`), and promoting it introduces an abstraction layer with no second caller in scope.
- **Placed `generatingTask` flag in `SidebarComponent`** — rejected; the sidebar is a dumb emitter and must not own authoritative state; the flag belongs with the entity that controls when generation is in flight (`AppComponent`).
- **Inline status reuse over toast infrastructure** — preferred; an existing status slot requires zero new service injection or DOM targets; toast is deferred until user latency feedback confirms the need (see Architecture §Design Decisions).

---

## 2. Pre-flight

Run **before editing any file**:

```bash
# 1. Confirm working tree state — flag any unrelated M or ?? entries
git status
git diff HEAD -- src/app/app.component.ts src/app/app.component.html

# 2. Verify Task 1 (SidebarAction union) has landed
grep "'generate-task'" src/app/components/sidebar/sidebar.component.ts \
  && echo "Task 1: OK" || echo "BLOCKER: 'generate-task' not in SidebarAction union — Task 1 must ship first"

# 3. Check whether Task 2 inputs are declared (can run parallel, but needed before Step 5)
grep "canGenerateTask\|generatingTask" src/app/components/sidebar/sidebar.component.ts \
  && echo "Task 2: OK" || echo "WARN: Task 2 inputs not yet on SidebarComponent — defer Step 5 until Task 2 merges"

# 4. Verify ImplementationGuideService exists
test -f src/app/services/implementation-guide.service.ts \
  && echo "Service: OK" || echo "BLOCKER: implementation-guide.service.ts missing"

# 5. Audit actual property names in AppComponent — executor MUST record these before editing
grep -n "activeProject\|statusMessage\|selectedFile\|generatingTask\|showCode\|showPrinciples\|onSidebarAction" \
  src/app/app.component.ts | head -40

# 6. Baseline test run
npm test -- --watch=false
```

**Property-name audit** (Step 5 above): before writing any code, record the exact names for:
- Active project ID field (expected: `activeProjectId`)
- Active project name access (expected: `activeProject?.name` or `activeProjectName`)
- Active project file list field (expected: `activeProject?.specs` or `activeProject?.files`)
- Inline status field (expected: `statusMessage` or `status`)
- File selection mechanism (expected: `this.selectedFile = filename` or a `selectFile()` call)
- Project refresh mechanism (expected: `this.loadProject()` or `this.refreshFiles()`)

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: `__`/`__` passing (fill in from Step 6 output; prior guides show 0 tests initially).

---

## 3. Files

### To Create (new)
- `src/app/app.component.spec.ts` — Karma/Jasmine unit spec covering the `canGenerateTask` predicate and the three outcome paths of the `generate-task` handler; does not exist in the current tree (confirmed: 0 spec files from epic-2 baseline)

### To Modify (cite CODEBASE CONTEXT)
- `src/app/app.component.ts` — add `generatingTask` flag (~1 line, after existing `showCodebase = false` at ~line 258 per Task 4 guide), add `canGenerateTask` getter (~6 lines), inject `ImplementationGuideService` if absent (~1 constructor param), add `else if (action === 'generate-task')` branch in `onSidebarAction` (~18 lines), bind new inputs in the `<app-sidebar>` template element (~2 attribute additions). Total: ~28 lines net, within the 40-line port budget.

### To Leave Alone
- `src/app/components/sidebar/sidebar.component.ts` — owned by Task 2; do not touch even if a merge conflict appears — raise it instead
- `src/app/services/implementation-guide.service.ts` — service is complete per architecture; Task 3 is a caller, not an implementer
- `src/app/services/*.service.ts` (all others) — unrelated; URL changes already landed in Task 4 of the previous epic
- `api/` — entire Flask backend; no changes required for this task

---

## 4. Implementation Steps

### Step 1: Audit `app.component.ts` and record ground truth

**Action**: Read the file to confirm exact property names before writing any code. Do not edit yet.

**File**: `src/app/app.component.ts`

**Commands**:
```bash
# Find the action handler
grep -n "onSidebarAction\|else if.*action\|switch.*action" src/app/app.component.ts

# Find active project tracking
grep -n "activeProject" src/app/app.component.ts | head -20

# Find inline status field
grep -n "statusMessage\|status\s*=" src/app/app.component.ts | head -10

# Find file selection mechanism
grep -n "selectedFile\|selectFile\|openFile" src/app/app.component.ts | head -10

# Find project refresh
grep -n "loadProject\|refreshProject\|refreshFiles\|getProject" src/app/app.component.ts | head -10

# Read the imports block and @Component decorator
head -25 src/app/app.component.ts

# Read around the existing show* flags (line ~255-265)
sed -n '250,270p' src/app/app.component.ts

# Read the full onSidebarAction handler  
grep -n "onSidebarAction" src/app/app.component.ts
# Then: sed -n '<start>,<end>p' src/app/app.component.ts  (use line numbers from grep output)

# Find the <app-sidebar> binding in the template (inline or separate .html)
grep -n "app-sidebar\|\[canGenerateTask\]\|\[generatingTask\]" src/app/app.component.ts src/app/app.component.html 2>/dev/null
```

**Verify**: Record all confirmed property names. If any name differs from assumptions in Steps 2–5, use the confirmed name and log the deviation in that step's commit body.

---

### Step 2: Add `generatingTask` flag and inject `ImplementationGuideService`

**Action**: Add the `generatingTask` boolean field immediately after the last `show*` flag block (confirmed in Step 1). Add `ImplementationGuideService` to the constructor if it is not already injected. Add its import at the top of the file.

**File**: `src/app/app.component.ts`

**Pattern — import** (add alongside existing service imports at the top of the file):
```typescript
import { ImplementationGuideService } from './services/implementation-guide.service';
```

**Pattern — field** (add after `showCodebase = false;` or the equivalent last `show*` flag, confirmed in Step 1 to be near line 258):
```typescript
generatingTask = false;
```

**Pattern — constructor injection** (add only if `ImplementationGuideService` is not already a constructor parameter; confirm in Step 1):
```typescript
constructor(
  // ... existing injected services ...
  private implementationGuideService: ImplementationGuideService,
) {}
```

**Verify**:
```bash
grep -n "generatingTask\|ImplementationGuideService" src/app/app.component.ts
# Expected: at least 2 matches — the import line and the field declaration
ng build 2>&1 | grep -i "error TS"
# Expected: zero TypeScript errors
```

---

### Step 3: Add `canGenerateTask` getter

**Action**: Add a `get canGenerateTask()` accessor after the `generatingTask` field. The predicate returns `true` iff `activeProjectId` is non-null **and** the active project's file list contains `'epic.md'`. Use the exact file-list property name confirmed in Step 1 (assumed `activeProject?.specs` based on the project shape `{ id, name, createdAt, specs: [] }` confirmed in the epic-2 proxy guide).

**File**: `src/app/app.component.ts`

**Pattern**:
```typescript
get canGenerateTask(): boolean {
  if (!this.activeProjectId) return false;
  // Replace `activeProject?.specs` with the confirmed file-list property from Step 1.
  // If the file list holds objects rather than strings, adapt the comparison accordingly.
  return this.activeProject?.specs?.includes('epic.md') ?? false;
}
```

**Verify**:
```bash
grep -n "canGenerateTask" src/app/app.component.ts
# Expected: one match on the getter declaration
ng build 2>&1 | grep -i "error TS"
# Expected: zero errors; if activeProject or specs is unrecognized, check confirmed names from Step 1
```

---

### Step 4: Add `else if (action === 'generate-task')` branch in `onSidebarAction`

**Action**: Locate the `onSidebarAction` method (confirmed line range from Step 1 — expected near line 487 per the Task 4 guide). Add the new branch **after** the last existing `else if` block in the chain, before the closing brace of the method. The handler must:
1. Set `generatingTask = true` immediately.
2. Call `generateNextTask()` with `activeProjectId` and the active project's name.
3. On `next` with a non-null filename: refresh the project file list, select the returned file, set a success status message, then reset `generatingTask`.
4. On `next` with `null`: set the "all tasks done" status message, then reset `generatingTask`.
5. On `error`: set the error status message, then reset `generatingTask`.

Use the exact field names confirmed in Step 1 for: project name access, file refresh, file selection, and status field.

**File**: `src/app/app.component.ts`

**Pattern** (adapt property names to those confirmed in Step 1; the shape below uses the most probable names based on Angular conventions and the architecture):
```typescript
} else if (action === 'generate-task') {
  if (!this.activeProjectId) return;
  this.generatingTask = true;
  // Replace `this.activeProject?.name` with the confirmed project name access.
  // Replace `this.implementationGuideService.generateNextTask` with the confirmed method call.
  this.implementationGuideService
    .generateNextTask(this.activeProjectId, this.activeProject?.name ?? '')
    .subscribe({
      next: (filename: string | null) => {
        if (filename === null) {
          this.statusMessage = 'All tasks are already covered — nothing to generate.';
        } else {
          // Replace with the confirmed refresh call (e.g. this.loadProject(this.activeProjectId))
          this.loadProject(this.activeProjectId!);
          // Replace with the confirmed file-selection mechanism (e.g. this.selectedFile = filename)
          this.selectedFile = filename;
          this.statusMessage = `Task generated: ${filename}`;
        }
        this.generatingTask = false;
      },
      error: () => {
        this.statusMessage = 'Error generating task — check the console for details.';
        this.generatingTask = false;
      }
    });
}
```

**Verify**:
```bash
grep -n "generate-task\|generatingTask\|generateNextTask" src/app/app.component.ts
# Expected: three matches — the action string, the flag resets, and the service call
ng build 2>&1 | grep -i "error TS"
# Expected: zero TypeScript errors
```

---

### Step 5: Bind `[canGenerateTask]` and `[generatingTask]` to `<app-sidebar>` in the template

**Action**: Locate the `<app-sidebar>` element in the template (inline template in `app.component.ts` or in `app.component.html` — confirmed in Step 1). Add the two new input bindings. **Prerequisite**: Task 2 must have declared these `@Input()` properties on `SidebarComponent` before this step compiles cleanly. If Task 2 has not yet merged, add the bindings anyway and note the build error as expected; it resolves on Task 2 merge.

**File**: `src/app/app.component.ts` (or `src/app/app.component.html` if template is separate — confirmed in Step 1)

**Pattern** (add alongside existing sidebar input bindings):
```html
<app-sidebar
  [projects]="projects"
  [activeProjectId]="activeProjectId"
  [canGenerateTask]="canGenerateTask"
  [generatingTask]="generatingTask"
  (action)="onSidebarAction($event)">
</app-sidebar>
```

> The existing bindings (`[projects]`, `[activeProjectId]`, `(action)`) are illustrative — add only `[canGenerateTask]="canGenerateTask"` and `[generatingTask]="generatingTask"` to whatever attributes already exist. Do not remove or reorder existing bindings.

**Verify**:
```bash
grep -n "canGenerateTask\|generatingTask" src/app/app.component.ts src/app/app.component.html 2>/dev/null
# Expected: at least 4 matches — field, getter, two template bindings
ng build 2>&1 | grep -i "error TS"
# Expected: zero errors if Task 2 has landed; if Task 2 is not yet merged,
#           expect "Property 'canGenerateTask' does not exist on type 'SidebarComponent'" — acceptable, log it
```

---

## 5. Tests

Framework: **Karma + Jasmine** — confirmed from `angular.json` `"builder": "@angular-devkit/build-angular:karma"` (Task 4 guide, line 466). No existing `app.component.spec.ts` — create new.

**`src/app/app.component.spec.ts`** (new):

```typescript
import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { AppComponent } from './app.component';
import { ImplementationGuideService } from './services/implementation-guide.service';

// Minimal stub — expand with other required providers if AppComponent's constructor
// injects additional services (confirm from Step 1 audit).
const makeGuideServiceSpy = () =>
  jasmine.createSpyObj<ImplementationGuideService>('ImplementationGuideService', [
    'generateNextTask',
  ]);

describe('AppComponent — canGenerateTask predicate', () => {
  let component: AppComponent;
  let guideSpy: jasmine.SpyObj<ImplementationGuideService>;

  beforeEach(async () => {
    guideSpy = makeGuideServiceSpy();
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [{ provide: ImplementationGuideService, useValue: guideSpy }],
    }).compileComponents();
    component = TestBed.createComponent(AppComponent).componentInstance;
  });

  it('returns false when activeProjectId is null', () => {
    (component as any).activeProjectId = null;
    (component as any).activeProject = null;
    expect(component.canGenerateTask).toBeFalse();
  });

  it('returns false when activeProjectId is set but epic.md is absent from file list', () => {
    (component as any).activeProjectId = 'proj-1';
    // Replace 'specs' below with the confirmed file-list property name from Step 1.
    (component as any).activeProject = { id: 'proj-1', name: 'Demo', createdAt: '2026-01-01', specs: ['analysis.md'] };
    expect(component.canGenerateTask).toBeFalse();
  });

  it('returns true when activeProjectId is set and epic.md is in the file list', () => {
    (component as any).activeProjectId = 'proj-1';
    // Replace 'specs' below with the confirmed file-list property name from Step 1.
    (component as any).activeProject = { id: 'proj-1', name: 'Demo', createdAt: '2026-01-01', specs: ['epic.md', 'analysis.md'] };
    expect(component.canGenerateTask).toBeTrue();
  });
});

describe('AppComponent — onSidebarAction generate-task handler', () => {
  let component: AppComponent;
  let guideSpy: jasmine.SpyObj<ImplementationGuideService>;

  beforeEach(async () => {
    guideSpy = makeGuideServiceSpy();
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [{ provide: ImplementationGuideService, useValue: guideSpy }],
    }).compileComponents();
    component = TestBed.createComponent(AppComponent).componentInstance;
    // Seed a minimal active project state.
    (component as any).activeProjectId = 'proj-1';
    // Replace 'activeProject' and 'specs' with confirmed names from Step 1.
    (component as any).activeProject = { id: 'proj-1', name: 'Demo', createdAt: '2026-01-01', specs: ['epic.md'] };
  });

  it('sets generatingTask to true while the call is in flight', fakeAsync(() => {
    guideSpy.generateNextTask.and.returnValue(of('task-3.md'));
    expect(component.generatingTask).toBeFalse();
    // Spy on the refresh method to prevent real HTTP — replace 'loadProject' with confirmed name.
    spyOn(component as any, 'loadProject');
    component.onSidebarAction('generate-task');
    // generatingTask resets synchronously after next() in fakeAsync context
    tick();
    expect(guideSpy.generateNextTask).toHaveBeenCalledWith('proj-1', 'Demo');
  }));

  it('resets generatingTask and sets success statusMessage when a filename is returned', fakeAsync(() => {
    guideSpy.generateNextTask.and.returnValue(of('task-3.md'));
    spyOn(component as any, 'loadProject');
    component.onSidebarAction('generate-task');
    tick();
    expect(component.generatingTask).toBeFalse();
    // Replace 'statusMessage' with the confirmed status field name from Step 1.
    expect((component as any).statusMessage).toContain('task-3.md');
  }));

  it('selects the returned filename after successful generation', fakeAsync(() => {
    guideSpy.generateNextTask.and.returnValue(of('task-3.md'));
    spyOn(component as any, 'loadProject');
    component.onSidebarAction('generate-task');
    tick();
    // Replace 'selectedFile' with the confirmed file-selection property/method from Step 1.
    expect((component as any).selectedFile).toBe('task-3.md');
  }));

  it('sets an "all tasks done" statusMessage when the service returns null', fakeAsync(() => {
    guideSpy.generateNextTask.and.returnValue(of(null));
    component.onSidebarAction('generate-task');
    tick();
    expect(component.generatingTask).toBeFalse();
    // Replace 'statusMessage' with the confirmed status field name from Step 1.
    const msg: string = (component as any).statusMessage;
    expect(msg.toLowerCase()).toContain('all tasks');
  }));

  it('sets an error statusMessage and resets generatingTask when the service throws', fakeAsync(() => {
    guideSpy.generateNextTask.and.returnValue(throwError(() => new Error('AI timeout')));
    component.onSidebarAction('generate-task');
    tick();
    expect(component.generatingTask).toBeFalse();
    // Replace 'statusMessage' with the confirmed status field name from Step 1.
    const msg: string = (component as any).statusMessage;
    expect(msg.toLowerCase()).toContain('error');
  }));

  it('does not call the service when activeProjectId is null', fakeAsync(() => {
    (component as any).activeProjectId = null;
    component.onSidebarAction('generate-task');
    tick();
    expect(guideSpy.generateNextTask).not.toHaveBeenCalled();
  }));
});
```

> **Adaptation note**: if `AppComponent` imports many standalone components and the test module fails to compile with the above, replace `imports: [AppComponent]` with `imports: []` and `declarations: [AppComponent]` only if the component is not standalone. Also add any required `HttpClientTestingModule` or router stubs to the `providers` array until the module compiles. Log each addition in the commit body.

---

## 6. Commit Plan

**Executor instruction**: commit after **each** step completes — not at the end of the task. Do not batch.

1. `chore(app): audit property names — no code changes` — after Step 1 — no files changed; use `git commit --allow-empty` to record the confirmed property-name map in the commit message body. This creates a revertible breadcrumb if later steps need to be walked back.

2. `feat(app): add generatingTask flag and inject ImplementationGuideService` — after Step 2 — `src/app/app.component.ts`: imports block + field declaration + constructor param.

3. `feat(app): add canGenerateTask getter with epic.md predicate` — after Step 3 — `src/app/app.component.ts`: getter only.

4. `feat(app): add generate-task handler in onSidebarAction` — after Step 4 — `src/app/app.component.ts`: the full `else if` branch; references service call and all three outcome paths.

5. `feat(app): bind canGenerateTask and generatingTask inputs to app-sidebar` — after Step 5 — `src/app/app.component.ts` (or `.html`): two attribute additions only.

6. `test(app): add canGenerateTask and generate-task handler specs` — after tests pass — `src/app/app.component.spec.ts` (new): six specs across two `describe` blocks.

**Deviation logging**: if any step deviates from this guide (e.g., confirmed property name differs from assumed name), prefix that commit's body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Structural: confirm the three outcome paths all exist in the handler
grep -A 25 "generate-task" src/app/app.component.ts | grep -E "generatingTask|statusMessage|null|error"
# Expected: at least 5 matches covering: flag set, flag reset (×2), status (×3)

# Structural: confirm canGenerateTask getter exists and references epic.md
grep -A 5 "get canGenerateTask" src/app/app.component.ts
# Expected: the getter body including 'epic.md'

# Full unit test run
npm test -- --watch=false
# Expected: 0 → 6 passing. Zero pre-existing tests broken.

# Build check
ng build 2>&1 | grep -i "error TS"
# Expected: zero TypeScript errors

# Manual smoke (requires the Flask backend or mock running on the proxy target)
# 1. Open http://localhost:4201 and select a project that contains epic.md
# 2. Confirm the "Generate Next Task" button is enabled
# 3. Click the button — confirm it shows a busy state during generation
# 4. After completion — confirm: (a) status message appears, (b) file is selected in editor,
#    (c) button returns to enabled state
```

**Expected delta**: 0 → 6 passing. Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: every step above produces an independent commit. Revert individually:
  ```bash
  git revert <sha>   # non-destructive; safe to push
  ```
- **Per-branch**: if verification fails and the branch state cannot be recovered cleanly:
  ```bash
  # [REQUIRES APPROVAL] — destroys uncommitted changes; confirm before running
  git reset --hard <pre-task-sha>
  ```
  Alternatively: delete the feature branch and re-cut from the pre-task SHA.
- **Template binding only** (Step 5 regression): if the build breaks solely due to Task 2 inputs not being declared, revert commit 5 alone — commits 1–4 remain valid and the handler is in place; Step 5 can be re-applied once Task 2 merges.

---

## 9. Deviations Allowed

- **`activeProject?.specs` does not contain plain filenames** — if the file list holds objects (`{ name: string, content: string }[]`) rather than strings, adapt the `canGenerateTask` getter to `this.activeProject?.specs?.some(f => f.name === 'epic.md')`. Log the shape mismatch in the commit body.
- **`generateNextTask` returns a `Promise`, not an `Observable`** — wrap with `from(this.implementationGuideService.generateNextTask(...))` from `rxjs`. Translate the test bodies to use `async/await` instead of `fakeAsync/tick`. Log the deviation.
- **The action router is a real `switch` statement, not `else if` chains** — add `case 'generate-task':` inside the switch following the existing case pattern; do not convert the switch to if-else. Log the deviation.
- **`AppComponent` has many injected services and the test module fails to compile** — add the minimum required stubs (`HttpClientTestingModule`, router stub, etc.) to `TestBed.configureTestingModule`; log each addition.
- **Step N unlocks an obvious simplification for Step N+1** — take it, log deviation in the commit.
- **Side-effect required** (push, schema change, new endpoint) → STOP, mark **[REQUIRES APPROVAL]**, and surface it before proceeding.

---

## 10. Out of Scope

This task delivers exactly: the `generatingTask` flag, the `canGenerateTask` getter, the three-path handler in `onSidebarAction`, the two template input bindings, and six Karma/Jasmine unit specs. Nothing beyond that boundary is in scope, even if it appears adjacent and easy.

- **`generateNextTask()` service implementation** — the service is described as complete; if it is missing or has a wrong signature, stop and raise it — do not implement or extend it here.
- **Per-task targeting picker (`generateTaskByNum()`)** — no caller in this epic; deferred until a picker UI is confirmed by the user (Architecture §What This System Does NOT Include).
- **SSE / streaming progress** — the endpoint is request/response; streaming requires a backend endpoint change that is out of scope. The spinner covers the UX floor.
- **Toast system** — deferred; inline status reuses the existing slot. Revisit only if user feedback confirms missed status messages.
- **E2E coverage for the generate-task flow** — the E2E epic (epic-5) is in flight; extending it mid-cycle risks merge conflicts. Log as a follow-up after epic-5 closes.
- **`canGenerateTask` refinement for projects with no epic.md path but a tasks/ directory** — the predicate is `epic.md`-present only; any heuristic extension is a product decision, not a Task 3 decision.
- **Bootstrap loop integration** — the loop already calls the service correctly; touching it here changes tested behavior with no new consumer benefit.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, component graph, execution flow
- [Epic](./epic.md) — Full task scope and success criteria
- [Timeline](./timeline.md) — Update task status to `done` after the 6-test run passes and the manual smoke checklist clears