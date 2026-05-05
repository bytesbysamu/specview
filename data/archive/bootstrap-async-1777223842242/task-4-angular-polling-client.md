Now I have enough context to write the guide. The Angular files are in a sibling directory outside the sandbox, but the API OpenAPI contract, DTOs, route handlers, and existing polling pattern (task_gen) are all visible. I'll write the guide from these confirmed sources plus the architecture document.

---

# Task 4: Angular Polling Client — Implementation Guide

## 1. Context

Task 4 wires the Angular application to the new async bootstrap contract introduced by Task 2 (T2). Before T2, `POST /api/ai/text/bootstrap-project` held the connection open for the full 10–25 minute chain and returned 200 with all files — an HTTP connection that infrastructure outside the app's control terminates silently. T2 replaces that with a 202+`job_id` response in milliseconds and a separate `GET /api/ai/text/bootstrap-project/status/{job_id}` polling endpoint. T4's job is purely on the Angular side: two new methods in `ai.service.ts` (`startBootstrapProject`, `getBootstrapStatus`) and a `setTimeout`-based polling loop in `new-project.component.ts` that waits for `status.done`, re-throws on `status.error`, and navigates with `status.files` after the first terminal read — without issuing a second GET. This is a hard cutover; the old synchronous `bootstrapProject` method is removed entirely.

**Trade-offs considered:**
- **RxJS `interval` + `takeUntil`** — rejected because it obscures the "resolve on first terminal read" invariant and requires a Subject to clean up; `setTimeout` recursion expresses the loop's exit condition more directly.
- **SSE / WebSocket for progress streaming** — rejected for this task; that is the province of the `braindump-streaming-task-gen` epic; the `partial` field arrives via that path once it lands.
- **`setTimeout` loop + `firstValueFrom`** — preferred; minimal RxJS footprint, terminal condition is explicit in one place, and the 3 s fixed interval is trivially extensible to jitter without restructuring.

---

## 2. Pre-flight

Run **from the `{SPEC_DOC_ROOT}` directory** (the directory that contains `api/` and the Angular project) — NOT from inside `api/`:

```bash
# 0. Confirm T2 is merged: new endpoint must exist in openapi.yaml
grep -n "bootstrap-project/status" api/openapi.yaml
# Expected: at least one line matching the GET status path.
# If grep returns nothing, T2 is not merged — STOP.

# 1. Confirm generated Python DTOs include BootstrapJobStart / BootstrapJobStatus
grep -n "BootstrapJobStart\|BootstrapJobStatus" api/dtos/models.py
# Expected: two class definitions.  If absent, run `cd api && make generate-dtos` first.

# 2. Locate Angular source files — resolve {FRONTEND} for the rest of this guide
find . -name "ai.service.ts" -not -path "*/node_modules/*"
find . -name "new-project.component.ts" -not -path "*/node_modules/*"
# Record both absolute paths.  Every subsequent path in this guide uses
# {FRONTEND} as the directory that contains ai.service.ts.

# 3. Audit current bootstrap method name in the service
grep -n "bootstrapProject\|bootstrap_project\|bootstrap-project" {FRONTEND}/ai.service.ts
# Record the exact method name — used in Step 3 (deletion) and Step 4 (component replacement).

# 4. Git state
git status
git diff HEAD -- {FRONTEND}/ai.service.ts {FRONTEND}/new-project.component.ts
# Flag any unrelated M entries. Stash or commit them separately before continuing.

# 5. Baseline Angular tests
cd {SPEC_DOC_ROOT} && ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -5
# Record: N tests passing.
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: N / N passing (executor fills in after running step 5).

---

## 3. Files

### To Create (new)
- *(none)* — The task fits within existing files; no new Angular modules, components, or services are introduced.

### To Modify (cite CODEBASE CONTEXT)
- `{FRONTEND}/ai.service.ts` — add `startBootstrapProject` (POST, no timeout) and `getBootstrapStatus` (GET, 10 s `timeout()` per call); remove the old synchronous `bootstrapProject` method; add/update `BootstrapJobStart` and `BootstrapJobStatus` TypeScript interfaces to match T2's OpenAPI shapes (see `api/openapi.yaml` `#/components/schemas/BootstrapJobStart` and `BootstrapJobStatus` added by T2).
- `{FRONTEND}/new-project.component.ts` — replace the single `await this.aiService.bootstrapProject(…)` call (name confirmed in pre-flight step 3) with a `startBootstrapProject` call followed by `pollBootstrapStatus`; add the private `pollBootstrapStatus` helper; no template or module changes.
- `{FRONTEND}/ai.service.spec.ts` — add tests for both new service methods.
- `{FRONTEND}/new-project.component.spec.ts` — add tests for the polling loop (resolve on done, reject on error, no re-poll after done).

### To Leave Alone
- `api/openapi.yaml` — T2 owns this; T4 reads from it but does not edit it.
- `api/dtos/models.py` — generated; never hand-edited (confirmed in `api/CLAUDE.md`).
- `api/modules/ai/routes.py` — T2 owns the backend changes; T4 does not touch it.
- Any other Angular component, service, or module — port budget is ≤ 30 lines across two files; scope creep is a failure.

---

## 4. Implementation Steps

### Step 1: Confirm T2 DTO shapes and record TypeScript interface target

**Action**: Read T2's OpenAPI additions to pin the exact wire shape the TypeScript interfaces must match. This step is read-only; it produces notes for Steps 2–4.

**File**: `api/openapi.yaml` (CODEBASE CONTEXT — confirmed present at `api/openapi.yaml`, line 426 area)

```bash
# Run this; record the schemas T2 added:
grep -A 20 "BootstrapJobStart\|BootstrapJobStatus" api/openapi.yaml
```

**Expected wire shapes from T2** (from architecture doc; executor confirms against actual yaml):
```yaml
# POST /api/ai/text/bootstrap-project → 202
BootstrapJobStart:
  type: object
  required: [job_id]
  properties:
    job_id:
      type: string

# GET /api/ai/text/bootstrap-project/status/{job_id} → 200
BootstrapJobStatus:
  type: object
  required: [running, done]
  properties:
    running:
      type: boolean
    done:
      type: boolean
    files:
      type: array
      items:
        $ref: '#/components/schemas/BootstrapFile'
    error:
      type: string
    latencyMs:
      type: integer
      minimum: 0
```

**Verify**: `grep -c "BootstrapJobStart\|BootstrapJobStatus" api/openapi.yaml` — expect ≥ 2 hits. If 0, T2 is not merged; STOP and surface this as a blocker.

---

### Step 2: Update TypeScript interfaces in `ai.service.ts`

**Action**: Locate the existing `BootstrapProjectResponse` interface (or equivalent) in `ai.service.ts`. Replace it with `BootstrapJobStart` and `BootstrapJobStatus`. Keep `BootstrapFile` if it already exists; add it if it doesn't.

**File**: `{FRONTEND}/ai.service.ts` (confirmed path in pre-flight)

**Pattern** — add/replace near the top of the file in the interfaces block:
```typescript
// ── Bootstrap async contract (T2) ─────────────────────────────────────
// These replace BootstrapProjectResponse (synchronous 200 shape).

export interface BootstrapJobStart {
  job_id: string;
}

export interface BootstrapJobStatus {
  running: boolean;
  done: boolean;
  files?: BootstrapFile[];
  error?: string;
  latencyMs?: number;
}

// BootstrapFile was already present before T2; keep as-is if found.
export interface BootstrapFile {
  filename: string;
  content: string;
}
```

**Deviation note**: If `BootstrapFile` already exists elsewhere in the file, do not duplicate it. If `BootstrapProjectResponse` is referenced in other components, leave a `@deprecated` JSDoc comment on it rather than hard-deleting — but do NOT keep the synchronous HTTP method that uses it (removed in Step 3).

**Verify**:
```bash
grep -n "BootstrapJobStart\|BootstrapJobStatus\|BootstrapFile" {FRONTEND}/ai.service.ts
```
Expect three distinct interface names present.

---

### Step 3: Add `startBootstrapProject` and `getBootstrapStatus`; remove old `bootstrapProject`

**Action**: Add the two new service methods immediately after the existing generate-task methods (or wherever bootstrap-related methods live). Delete the old synchronous `bootstrapProject` method identified in pre-flight step 3.

**File**: `{FRONTEND}/ai.service.ts`

**Pattern** — the two new methods:
```typescript
import { firstValueFrom } from 'rxjs';
import { timeout } from 'rxjs/operators';

// …inside the @Injectable() class body:

/** POST /api/ai/text/bootstrap-project → 202 { job_id }.
 *  No Angular timeout — server returns in milliseconds. */
startBootstrapProject(req: BootstrapProjectRequest): Promise<BootstrapJobStart> {
  return firstValueFrom(
    this.http.post<BootstrapJobStart>('/api/ai/text/bootstrap-project', req)
  );
}

/** GET /api/ai/text/bootstrap-project/status/{jobId}.
 *  10 s timeout per poll guards against a hung status endpoint
 *  without treating a slow chain as an error. */
getBootstrapStatus(jobId: string): Promise<BootstrapJobStatus> {
  return firstValueFrom(
    this.http.get<BootstrapJobStatus>(
      `/api/ai/text/bootstrap-project/status/${jobId}`
    ).pipe(timeout(10_000))
  );
}
```

**Verify**:
```bash
grep -n "startBootstrapProject\|getBootstrapStatus\|bootstrapProject" {FRONTEND}/ai.service.ts
```
Expect `startBootstrapProject` present, `getBootstrapStatus` present, old method name **absent** (or present only as a `@deprecated` stub if other callers exist — log this as a deviation if so).

---

### Step 4: Replace synchronous call in `new-project.component.ts` with start-then-poll loop

**Action**: Replace the single `await this.aiService.bootstrapProject(…)` call (or equivalent) with a two-phase flow: call `startBootstrapProject`, then `pollBootstrapStatus`. Add the private helper `pollBootstrapStatus`. No template or module changes.

**File**: `{FRONTEND}/new-project.component.ts`

**Pattern — replace the old synchronous call block**:
```typescript
// BEFORE (remove this):
const result = await this.aiService.bootstrapProject(req);
const files = result.files;

// AFTER (replace with):
const { job_id } = await this.aiService.startBootstrapProject(req);
const status   = await this.pollBootstrapStatus(job_id);
const files    = status.files!;
```

**Pattern — add private helper inside the class**:
```typescript
/** Poll GET /api/ai/text/bootstrap-project/status/{jobId} every 3 s.
 *
 *  Resolves with the first terminal BootstrapJobStatus where done=true.
 *  Re-throws on status.error.  Does NOT issue a second GET after done.
 *  The resolved status object carries files and latencyMs. */
private pollBootstrapStatus(jobId: string): Promise<BootstrapJobStatus> {
  return new Promise<BootstrapJobStatus>((resolve, reject) => {
    const tick = async (): Promise<void> => {
      try {
        const status = await this.aiService.getBootstrapStatus(jobId);
        if (status.error) {
          reject(new Error(status.error));
          return;
        }
        if (status.done) {
          resolve(status);   // files + latencyMs are present here
          return;
        }
        setTimeout(tick, 3_000);
      } catch (err) {
        reject(err);
      }
    };
    void tick();
  });
}
```

**Verify**:
```bash
grep -n "startBootstrapProject\|pollBootstrapStatus\|getBootstrapStatus\|bootstrapProject" \
  {FRONTEND}/new-project.component.ts
```
Expect:
- `startBootstrapProject` present (1 call site)
- `pollBootstrapStatus` present (definition + 1 call site)
- Old method name absent

---

## 5. Tests

Both test files use Angular's default Jasmine + TestBed + `HttpClientTestingModule`. Run `grep -n "describe\|TestBed\|jasmine" {FRONTEND}/ai.service.spec.ts` before editing to confirm the framework and import paths match.

### `ai.service.spec.ts` — additions

```typescript
import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { AiService, BootstrapJobStart, BootstrapJobStatus } from './ai.service';

describe('AiService — bootstrap async', () => {
  let service: AiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AiService],
    });
    service = TestBed.inject(AiService);
    http    = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  // ── startBootstrapProject ────────────────────────────────────────────

  it('startBootstrapProject fires POST to /api/ai/text/bootstrap-project', fakeAsync(() => {
    let result: BootstrapJobStart | undefined;
    service.startBootstrapProject({
      project_name: 'Acme',
      braindump: 'build a thing',
    }).then(r => (result = r));

    const req = http.expectOne('/api/ai/text/bootstrap-project');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ project_name: 'Acme', braindump: 'build a thing' });

    req.flush({ job_id: 'abc-123' } satisfies BootstrapJobStart);
    tick();

    expect(result).toEqual({ job_id: 'abc-123' });
  }));

  it('startBootstrapProject carries NO Angular timeout operator', () => {
    // Verify no timeout in the Observable chain by inspecting source —
    // this is a structural check: the method must not call .pipe(timeout(...)).
    const src = (service.startBootstrapProject as Function).toString();
    // The GET status method uses timeout; the POST must not.
    const postMethodLines = src.split('\n');
    const hasTimeout = postMethodLines.some(l => l.includes('timeout('));
    expect(hasTimeout).toBeFalse();
    http.expectOne('/api/ai/text/bootstrap-project').flush({ job_id: 'x' });
  });

  // ── getBootstrapStatus ───────────────────────────────────────────────

  it('getBootstrapStatus fires GET to /api/ai/text/bootstrap-project/status/{jobId}', fakeAsync(() => {
    let result: BootstrapJobStatus | undefined;
    service.getBootstrapStatus('job-999').then(r => (result = r));

    const req = http.expectOne('/api/ai/text/bootstrap-project/status/job-999');
    expect(req.request.method).toBe('GET');

    const mockStatus: BootstrapJobStatus = {
      running: false,
      done: true,
      files: [{ filename: 'analysis.md', content: '# Analysis' }],
      latencyMs: 42000,
    };
    req.flush(mockStatus);
    tick();

    expect(result).toEqual(mockStatus);
  }));

  it('getBootstrapStatus rejects with TimeoutError when no response within 10 s', fakeAsync(() => {
    let caughtError: unknown;
    service.getBootstrapStatus('job-slow').catch(e => (caughtError = e));

    http.expectOne('/api/ai/text/bootstrap-project/status/job-slow');
    // Do NOT flush — simulate a hung endpoint by letting time advance past the timeout.
    tick(10_001);

    expect(caughtError).toBeTruthy();
    // RxJS TimeoutError carries name 'TimeoutError'
    expect((caughtError as Error).name).toBe('TimeoutError');
  }));
});
```

### `new-project.component.spec.ts` — additions

```typescript
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NewProjectComponent } from './new-project.component';
import { AiService, BootstrapJobStatus } from '../../services/ai.service';
// Adjust the AiService import path to match the actual path found in pre-flight.

describe('NewProjectComponent — bootstrap polling loop', () => {
  let component: NewProjectComponent;
  let fixture: ComponentFixture<NewProjectComponent>;
  let aiServiceSpy: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    aiServiceSpy = jasmine.createSpyObj<AiService>('AiService', [
      'startBootstrapProject',
      'getBootstrapStatus',
    ]);

    await TestBed.configureTestingModule({
      declarations: [NewProjectComponent],
      providers: [{ provide: AiService, useValue: aiServiceSpy }],
    }).compileComponents();

    fixture   = TestBed.createComponent(NewProjectComponent);
    component = fixture.componentInstance;
  });

  it('resolves when getBootstrapStatus returns done=true on first poll', fakeAsync(async () => {
    aiServiceSpy.startBootstrapProject.and.returnValue(
      Promise.resolve({ job_id: 'job-1' })
    );
    const terminalStatus: BootstrapJobStatus = {
      running: false,
      done: true,
      files: [
        { filename: 'analysis.md', content: '# Analysis' },
        { filename: 'epic.md',     content: '# Epic' },
      ],
      latencyMs: 5000,
    };
    aiServiceSpy.getBootstrapStatus.and.returnValue(
      Promise.resolve(terminalStatus)
    );

    // Access the private method via type cast for testing
    const result = await (component as any).pollBootstrapStatus('job-1');

    expect(result).toEqual(terminalStatus);
    // Must have polled exactly once (done on first call)
    expect(aiServiceSpy.getBootstrapStatus).toHaveBeenCalledTimes(1);
    expect(aiServiceSpy.getBootstrapStatus).toHaveBeenCalledWith('job-1');
  }));

  it('continues polling until done=true; issues one GET per interval', fakeAsync(async () => {
    aiServiceSpy.startBootstrapProject.and.returnValue(
      Promise.resolve({ job_id: 'job-2' })
    );

    const runningStatus: BootstrapJobStatus = { running: true, done: false };
    const doneStatus: BootstrapJobStatus = {
      running: false,
      done: true,
      files: [{ filename: 'epic.md', content: '# Epic' }],
      latencyMs: 12000,
    };

    let callCount = 0;
    aiServiceSpy.getBootstrapStatus.and.callFake(() => {
      callCount++;
      return callCount < 3
        ? Promise.resolve(runningStatus)
        : Promise.resolve(doneStatus);
    });

    let resolved: BootstrapJobStatus | undefined;
    (component as any).pollBootstrapStatus('job-2').then((s: BootstrapJobStatus) => (resolved = s));

    // First tick fires synchronously in the Promise microtask queue
    await Promise.resolve();
    tick(3_000);   // interval 1 → poll 2
    await Promise.resolve();
    tick(3_000);   // interval 2 → poll 3 (done)
    await Promise.resolve();

    expect(aiServiceSpy.getBootstrapStatus).toHaveBeenCalledTimes(3);
    expect(resolved).toEqual(doneStatus);
  }));

  it('rejects with the server error message when status.error is set', fakeAsync(async () => {
    aiServiceSpy.startBootstrapProject.and.returnValue(
      Promise.resolve({ job_id: 'job-err' })
    );
    aiServiceSpy.getBootstrapStatus.and.returnValue(
      Promise.resolve({ running: false, done: true, error: 'architecture step timed out' })
    );

    let caught: Error | undefined;
    await (component as any).pollBootstrapStatus('job-err').catch((e: Error) => (caught = e));

    expect(caught).toBeDefined();
    expect(caught!.message).toBe('architecture step timed out');
  }));

  it('does NOT call getBootstrapStatus a second time after receiving done=true', fakeAsync(async () => {
    aiServiceSpy.startBootstrapProject.and.returnValue(
      Promise.resolve({ job_id: 'job-once' })
    );
    const done: BootstrapJobStatus = {
      running: false,
      done: true,
      files: [{ filename: 'README.md', content: '# readme' }],
    };
    aiServiceSpy.getBootstrapStatus.and.returnValue(Promise.resolve(done));

    await (component as any).pollBootstrapStatus('job-once');
    // Advance time well past two poll intervals to confirm no re-poll
    tick(10_000);

    expect(aiServiceSpy.getBootstrapStatus).toHaveBeenCalledTimes(1);
  }));

  it('rejects when getBootstrapStatus itself throws (e.g. timeout)', fakeAsync(async () => {
    aiServiceSpy.startBootstrapProject.and.returnValue(
      Promise.resolve({ job_id: 'job-net' })
    );
    aiServiceSpy.getBootstrapStatus.and.returnValue(
      Promise.reject(new Error('TimeoutError'))
    );

    let caught: Error | undefined;
    await (component as any).pollBootstrapStatus('job-net').catch((e: Error) => (caught = e));

    expect(caught).toBeDefined();
    expect(caught!.message).toBe('TimeoutError');
  }));
});
```

---

## 6. Commit Plan

**Executor instruction**: run each `git commit` command immediately after completing the corresponding step. Do not batch commits at the end.

```
1. feat(ai-service): add BootstrapJobStart and BootstrapJobStatus TypeScript interfaces
   — after Step 2 — files: {FRONTEND}/ai.service.ts
   Message: feat(ai-service): add BootstrapJobStart and BootstrapJobStatus interfaces (T4)

2. feat(ai-service): add startBootstrapProject and getBootstrapStatus; remove synchronous bootstrapProject
   — after Step 3 — files: {FRONTEND}/ai.service.ts
   Message: feat(ai-service): add start/status bootstrap methods, remove sync bootstrapProject (T4)

3. feat(new-project): replace synchronous bootstrap call with start-then-poll loop
   — after Step 4 — files: {FRONTEND}/new-project.component.ts
   Message: feat(new-project): replace sync bootstrap with 202+poll loop, 3 s interval (T4)

4. test(bootstrap-polling): add service and component polling tests
   — after tests pass — files: {FRONTEND}/ai.service.spec.ts, {FRONTEND}/new-project.component.spec.ts
   Message: test(bootstrap-polling): add startBootstrapProject, getBootstrapStatus, pollBootstrapStatus tests (T4)
```

**Deviation logging**: if any step diverges from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {SPEC_DOC_ROOT}
ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -20
```

**Expected delta**: N → N+9 passing (5 component tests + 4 service tests added in Section 5). Zero pre-existing tests broken.

Separately, smoke-test the backend contract that T4 depends on:
```bash
cd {SPEC_DOC_ROOT}/api && make test 2>&1 | tail -5
```
Expected: all existing API tests still pass (T4 does not touch the backend).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  ```bash
  git revert <sha>   # reverts exactly one step; repeat for each commit to unwind
  ```
- **Per-branch**: if verification fails and the branch is unrecoverable:
  ```bash
  git reset --hard <pre-task-sha>   # ⚠ destructive — loses all T4 commits on this branch
  # or, if working on a feature branch:
  git checkout main && git branch -D feature/t4-angular-polling
  ```
  Record `<pre-task-sha>` from `git log --oneline -1` before starting Step 2.

---

## 9. Deviations Allowed

- **Angular file paths differ from inferred**: pre-flight step 2 resolves the real paths with `find`. Use those; do not invent. Log in commit body.
- **T2 used a different DTO name** (e.g., `BootstrapStartResponse` instead of `BootstrapJobStart`): adopt T2's exact names; update the interface names in this guide accordingly. Log in commit body.
- **Existing service has no `bootstrapProject` method** (T2 already removed it): skip the deletion in Step 3; log as a deviation (good deviation — less work).
- **Angular uses a different import path for `timeout`** (e.g., `rxjs` directly rather than `rxjs/operators`): match the file's existing import style. RxJS 7+ exports `timeout` from both; either works.
- **Test framework is Jest not Jasmine**: translate `jasmine.createSpyObj` → `jest.fn()`, `toBeFalse()` → `toBe(false)`, `fakeAsync/tick` → `jest.useFakeTimers()/jest.advanceTimersByTime()`. Note translation in commit body.
- **Side-effect required** (push, publish, schema migration): STOP, mark `[REQUIRES APPROVAL]`, and surface it.
- **Step N reveals a simplification for Step N+1**: take it, log it.

---

## 10. Out of Scope

This task modifies exactly two Angular files and adds two test files. It does not extend the backend, alter the OpenAPI contract, change navigation routes, or add UI feedback for in-progress polling state. An executor reading this guide might be tempted to add loading spinners, error toasts, or cancel buttons — all of which require UX decisions that have not been made. Equally tempting would be to wire the `partial` field from `BootstrapJobStatus` into a progress indicator, but that field arrives via the streaming epic, not this one.

- **Progress UI (spinner, percentage, step labels)** — deferred; requires a UX design pass and likely a dedicated `streaming-progress` epic before it enters scope.
- **`partial` field support** — deferred; the `braindump-streaming-task-gen` epic owns this field; T4 must not add a `partial` property to `BootstrapJobStatus` prematurely.
- **Cancellation / abort button** — deferred; `WorkflowExecution.request_cancel()` exists on the backend but the runtime does not yet check between steps; a user-facing abort UX must be scoped first.
- **Exponential backoff or jitter on the 3 s poll interval** — deferred; fixed interval is correct for a single-user tool; the `setTimeout` loop accommodates this change in one line when multi-user load makes it necessary.
- **Persistent job ID across page refreshes** — deferred; if the Angular client crashes between `startBootstrapProject` and the terminal poll, the job ID is lost and the result is gone; the architecture document accepts this for a dev tool; session storage or route state is a follow-on decision.
- **Removal of `BootstrapProjectResponse` from other consumers** — verify in pre-flight; if other components use the old type, flag them rather than silently removing it in this task's blast radius.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than absorbing it into T4.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale (primary reference for this guide)
- [Epic](./epic.md) — Task scope and dependency map
- [Timeline](./timeline.md) — Status tracking (mark T4 In Progress when starting, Done after verification)