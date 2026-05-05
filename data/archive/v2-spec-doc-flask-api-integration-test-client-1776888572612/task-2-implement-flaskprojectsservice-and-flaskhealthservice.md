Now I have everything I need. Let me write the guide.

# Task 2: Implement FlaskProjectsService and FlaskHealthService

## 1. Context

This task creates two Angular services — `FlaskProjectsService` and `FlaskHealthService` — that call `localhost:3101` instead of `localhost:3100`, with method signatures identical to their Express counterparts (`ProjectsService`). Both services are consumed exclusively by `ContractCompareSpec` (Task 4), which calls Express and Flask clients side-by-side on the same inputs and compares field-level responses. The symmetry constraint drives every decision: the compare spec must be able to call `expressProjectsService.list()` and `flaskProjectsService.list()` on adjacent lines with no adapter logic between them.

**Trade-offs considered:**
- **Shared base class with configurable `baseUrl`** — rejected. One consumer exists; a base class adds indirection for a single instantiation. Re-scope when a second consumer is named.
- **Injectable `BASE_URL` token** — rejected. No staging or remote Flask environment is in scope; `environment.ts` indirection adds configuration surface for a deployment scenario that has not been specified.
- **Hard-coded `localhost:3101` in each service** — preferred. Matches the architecture decision; keeps each file self-contained and trivially readable during the migration window.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status
# Expected: M references.md, M src/app/components/new-project/new-project.component.ts
# Flag anything else touching src/app/services/ or src/app/flask/

git diff HEAD -- src/app/flask/flask-api.types.ts
# Must exist and be clean — Task 1 MUST be complete before starting Task 2

ls src/app/flask/flask-api.types.ts
# If this returns "No such file", STOP. Complete Task 1 first.

npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -10
# Record baseline. Expected: 0 specs, 0 failures (no spec.ts files exist yet).
```

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Task 1 gate**: `src/app/flask/flask-api.types.ts` must export at minimum: `ProjectSummary`, `ProjectDetail`, `HealthResponse`. If any are missing, raise it as a deviation and add them to that file — do not inline types into the service files.

**Baseline recorded**: 0 specs / 0 failures.

---

## 3. Files

### To Create (new)
- `src/app/flask/flask-projects.service.ts` — Angular service, five CRUD methods mirroring `ProjectsService`, base URL `localhost:3101/api/projects`
- `src/app/flask/flask-health.service.ts` — Angular service, one `check()` method calling `localhost:3101/health`
- `src/app/flask/flask-projects.service.spec.ts` — Jasmine/Karma tests for `FlaskProjectsService` (complete assertion bodies, no stubs)
- `src/app/flask/flask-health.service.spec.ts` — Jasmine/Karma tests for `FlaskHealthService`

### To Modify (cite CODEBASE CONTEXT)
- `src/app/flask/flask-api.types.ts` — Task 1 output. Verify it exports `ProjectSummary`, `ProjectDetail`, `HealthResponse`. Add any missing interface **only** if confirmed absent — do not duplicate.

### To Leave Alone
- `src/app/services/projects.service.ts` — source of truth for method signatures; read it, mirror it, never touch it. Express stays on port 3100.
- `server.js` — Express server; out of scope for this task.
- `flask/` — Python backend; tested separately via pytest. No changes here.
- All existing `src/app/services/*.ts` files — production wiring unchanged.

---

## 4. Implementation Steps

### Step 1: Verify Task 1 types

**Action**: Read `flask-api.types.ts` and confirm it exports `ProjectSummary`, `ProjectDetail`, and `HealthResponse`. If `HealthResponse` is missing, add it to that file (not the service file).

**File**: `src/app/flask/flask-api.types.ts` (Task 1 output)

**Required exports** (derive from `src/app/services/projects.service.ts:5-24` and `flask/api-contract.md`):
```typescript
// Must already exist from Task 1. Add only if absent:
export interface HealthResponse {
  status: string;
}
```

**Verify**: `grep -n "HealthResponse\|ProjectSummary\|ProjectDetail" src/app/flask/flask-api.types.ts` — expect all three names in output.

---

### Step 2: Create FlaskProjectsService

**Action**: Create the service file. Port method names and return types directly from `src/app/services/projects.service.ts:30-54`. Replace `localhost:3100` with `localhost:3101`. Import response types from `flask-api.types.ts` instead of defining them inline.

**File**: `src/app/flask/flask-projects.service.ts` (new)

**Pattern** (port from `src/app/services/projects.service.ts:27-54`):
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ProjectSummary, ProjectDetail } from './flask-api.types';

@Injectable({ providedIn: 'root' })
export class FlaskProjectsService {
  private baseUrl = 'http://localhost:3101/api/projects';

  constructor(private http: HttpClient) {}

  list(): Observable<ProjectSummary[]> {
    return this.http.get<ProjectSummary[]>(this.baseUrl);
  }

  get(id: string): Observable<ProjectDetail> {
    return this.http.get<ProjectDetail>(`${this.baseUrl}/${id}`);
  }

  create(
    name: string,
    files: { filename: string; content: string }[]
  ): Observable<{ id: string; name: string; createdAt: string }> {
    return this.http.post<{ id: string; name: string; createdAt: string }>(
      this.baseUrl,
      { name, files }
    );
  }

  updateFile(
    projectId: string,
    filename: string,
    content: string
  ): Observable<{ success: boolean }> {
    return this.http.put<{ success: boolean }>(
      `${this.baseUrl}/${projectId}/files/${filename}`,
      { content }
    );
  }

  delete(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.baseUrl}/${id}`);
  }
}
```

**Verify**: `npx tsc --project tsconfig.spec.json --noEmit` — expect zero errors.

---

### Step 3: Create FlaskHealthService

**Action**: Create the health service. The Express server does not expose `/health` (`flask/api-contract.md` notes "Express does not expose it"), but the architecture specifies `FlaskHealthService` as a standalone service for Task 4's health assertion. Use `check()` as the method name.

**File**: `src/app/flask/flask-health.service.ts` (new)

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { HealthResponse } from './flask-api.types';

@Injectable({ providedIn: 'root' })
export class FlaskHealthService {
  private baseUrl = 'http://localhost:3101';

  constructor(private http: HttpClient) {}

  check(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/health`);
  }
}
```

**Verify**: `npx tsc --project tsconfig.spec.json --noEmit` — expect zero errors.

---

### Step 4: Write FlaskProjectsService tests

**Action**: Create the Jasmine spec using `HttpClientTestingModule` and `HttpTestingController`. Each test verifies the correct HTTP verb, URL, and request body.

**File**: `src/app/flask/flask-projects.service.spec.ts` (new)

**Complete test file**:
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { FlaskProjectsService } from './flask-projects.service';
import { ProjectSummary, ProjectDetail } from './flask-api.types';

describe('FlaskProjectsService', () => {
  let service: FlaskProjectsService;
  let httpMock: HttpTestingController;

  const BASE = 'http://localhost:3101/api/projects';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [FlaskProjectsService],
    });
    service = TestBed.inject(FlaskProjectsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('list() sends GET to /api/projects', () => {
    const mockResponse: ProjectSummary[] = [
      { id: 'proj-1', name: 'Test', createdAt: '2026-04-22T00:00:00.000Z', specs: [] },
    ];

    service.list().subscribe(result => {
      expect(result.length).toBe(1);
      expect(result[0].id).toBe('proj-1');
      expect(result[0].name).toBe('Test');
    });

    const req = httpMock.expectOne(BASE);
    expect(req.request.method).toBe('GET');
    req.flush(mockResponse);
  });

  it('get() sends GET to /api/projects/:id', () => {
    const mockDetail: ProjectDetail = {
      id: 'proj-1',
      name: 'Test',
      createdAt: '2026-04-22T00:00:00.000Z',
      specs: [{ filename: 'epic.md', label: 'Epic', content: '# Epic' }],
    };

    service.get('proj-1').subscribe(result => {
      expect(result.id).toBe('proj-1');
      expect(result.specs.length).toBe(1);
      expect(result.specs[0].content).toBe('# Epic');
    });

    const req = httpMock.expectOne(`${BASE}/proj-1`);
    expect(req.request.method).toBe('GET');
    req.flush(mockDetail);
  });

  it('create() sends POST to /api/projects with name and files body', () => {
    const files = [{ filename: 'epic.md', content: '# Epic' }];
    const mockResponse = { id: 'test-123', name: 'MyProject', createdAt: '2026-04-22T00:00:00.000Z' };

    service.create('MyProject', files).subscribe(result => {
      expect(result.id).toBe('test-123');
      expect(result.name).toBe('MyProject');
    });

    const req = httpMock.expectOne(BASE);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'MyProject', files });
    req.flush(mockResponse);
  });

  it('updateFile() sends PUT to /api/projects/:projectId/files/:filename with content body', () => {
    service.updateFile('proj-1', 'epic.md', '# Updated').subscribe(result => {
      expect(result.success).toBe(true);
    });

    const req = httpMock.expectOne(`${BASE}/proj-1/files/epic.md`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ content: '# Updated' });
    req.flush({ success: true });
  });

  it('delete() sends DELETE to /api/projects/:id', () => {
    service.delete('proj-1').subscribe(result => {
      expect(result.success).toBe(true);
    });

    const req = httpMock.expectOne(`${BASE}/proj-1`);
    expect(req.request.method).toBe('DELETE');
    req.flush({ success: true });
  });
});
```

**Verify**: `npx tsc --project tsconfig.spec.json --noEmit` — expect zero errors.

---

### Step 5: Write FlaskHealthService tests

**Action**: Create the Jasmine spec for health service.

**File**: `src/app/flask/flask-health.service.spec.ts` (new)

**Complete test file**:
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { FlaskHealthService } from './flask-health.service';
import { HealthResponse } from './flask-api.types';

describe('FlaskHealthService', () => {
  let service: FlaskHealthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [FlaskHealthService],
    });
    service = TestBed.inject(FlaskHealthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('check() sends GET to /health', () => {
    const mockResponse: HealthResponse = { status: 'ok' };

    service.check().subscribe(result => {
      expect(result.status).toBe('ok');
    });

    const req = httpMock.expectOne('http://localhost:3101/health');
    expect(req.request.method).toBe('GET');
    req.flush(mockResponse);
  });

  it('check() returns the status field from the response', () => {
    service.check().subscribe(result => {
      expect(result.status).toBeDefined();
      expect(typeof result.status).toBe('string');
    });

    const req = httpMock.expectOne('http://localhost:3101/health');
    req.flush({ status: 'ok' });
  });
});
```

**Verify**: `npx tsc --project tsconfig.spec.json --noEmit` — expect zero errors.

---

### Step 6: Run the full Angular test suite

**Action**: Run Karma to confirm all new tests pass.

**File**: n/a

**Pattern**:
```bash
npx ng test --watch=false --browsers=ChromeHeadless
```

**Verify**: Expect 7 specs, 0 failures (5 for projects, 2 for health). Zero pre-existing tests broken.

---

## 5. Tests

Tests are embedded in Steps 4 and 5 with complete assertion bodies. Summary of coverage:

| Test file | Tests | What is covered |
|-----------|-------|-----------------|
| `flask-projects.service.spec.ts` | 5 | `list()` GET URL; `get()` GET URL with ID; `create()` POST URL + body; `updateFile()` PUT URL + body; `delete()` DELETE URL |
| `flask-health.service.spec.ts` | 2 | `check()` GET URL; `check()` returns typed `status` field |

Framework: Karma + Jasmine. Module: `HttpClientTestingModule` + `HttpTestingController`. Pattern is identical to the Angular docs standard — `expectOne(url)` → `request.method` assertion → `flush(mockData)` → subscriber assertion.

---

## 6. Commit Plan

1. `feat(flask): add FlaskProjectsService mirroring ProjectsService at localhost:3101` — `src/app/flask/flask-projects.service.ts`: five CRUD methods, hardcoded base URL, types imported from flask-api.types
2. `feat(flask): add FlaskHealthService calling localhost:3101/health` — `src/app/flask/flask-health.service.ts`: single `check()` method returning `Observable<HealthResponse>`
3. `test(flask): Jasmine specs for FlaskProjectsService and FlaskHealthService` — `src/app/flask/flask-projects.service.spec.ts`, `src/app/flask/flask-health.service.spec.ts`: 7 tests total, all passing

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npx ng test --watch=false --browsers=ChromeHeadless
```

**Expected delta**: 0 → 7 passing. Zero pre-existing tests broken.

Type-check only (no browser needed):
```bash
npx tsc --project tsconfig.spec.json --noEmit
```
Expect zero errors.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible via `git revert <sha>`. Steps 1–2 (service files) can be reverted without affecting Step 3 (tests).
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` and delete `src/app/flask/flask-projects.service.ts` and `src/app/flask/flask-health.service.ts` manually. `src/app/flask/flask-api.types.ts` (Task 1) must be preserved.

---

## 9. Deviations Allowed

- **`HealthResponse` already defined in `flask-api.types.ts`** → import it, do not redefine. If absent, add it to that file in the same commit and note the deviation.
- **`ProjectSummary` / `ProjectDetail` type shape differs from what's in `projects.service.ts`** → the types file is the authority. Adapt service return type annotations to match; do not fork the types. Log the deviation.
- **Test framework mismatch** (e.g., repo has switched to Jest) → match whatever framework `tsconfig.spec.json` declares; translate Jasmine matchers to Jest equivalents silently but note in commit body.
- **`src/app/flask/` already partially populated** → read existing files before writing. Do not overwrite Task 1's work.
- **Side-effect required** (push, schema change, npm publish) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task creates the Angular service shells and their unit tests using `HttpTestingController`. It does NOT verify that `localhost:3101` is actually running, does NOT compare responses between Express and Flask (that is Task 4's job), and does NOT implement `FlaskContextService` (Task 3). No retry logic, interceptors, error-boundary UI, or shared base class are introduced — these would require a second consumer that does not exist in this epic's scope.

- **`FlaskContextService`** — Task 3, independent parallel track. Can be developed concurrently but is not a dependency of this task.
- **`ContractCompareSpec`** — Task 4; depends on Tasks 2 and 3 both being compiled. Not started here.
- **Live integration assertions** (actual Flask server running) — Task 4's responsibility; these unit tests mock HTTP with `HttpTestingController` only.
- **Error path testing** (4xx/5xx responses)** — deferred to Task 4's live compare spec, where mismatches surface as Jasmine failures against real server responses. Unit tests here cover the happy path only, matching the single-consumer, local-dev-tool scope.
- **`environment.ts` wiring for `localhost:3101`** — explicitly out of scope per the architecture decision; if a second deployment target is ever named, re-scope at that point.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale
- [Epic](./epic.md) — Task scope
- [Timeline](./timeline.md) — Update status after verification passes