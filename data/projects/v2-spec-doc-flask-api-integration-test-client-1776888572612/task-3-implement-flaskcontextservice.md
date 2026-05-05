# Implementation Guide: Task 3 — FlaskContextService

## 1. Context

`FlaskContextService` is an Angular service that gives `ContractCompareSpec` (Task 4) typed HTTP access to the four context resource paths (`/api/builder`, `/api/principles`, `/api/codebase`, `/api/references`) on the Flask server at `localhost:3101`. It collapses what the Express side spreads across four separate service files — `BuilderService`, `PrinciplesService`, `CodebaseService`, `ReferencesService` — into one file, because it has exactly one consumer and splitting adds file overhead with no isolation benefit for a temporary test harness. Every method mirrors its Express counterpart's name and signature so the compare spec can call both backends symmetrically on adjacent lines.

**Trade-offs considered:**
- **Four separate Flask service files (mirroring Express structure)** — rejected because the single consumer (`ContractCompareSpec`) calls all four paths in the same test suite; file-per-resource adds overhead with no separation benefit for a read-only harness.
- **A shared `FlaskBaseService` with injectable base URL** — rejected because there is no second consumer; a base class would add indirection for one concrete instantiation, and the architecture explicitly forbids premature abstraction for this epic.
- **One file, eight methods, hardcoded `localhost:3101`** — preferred because it is the minimum code that satisfies the single consumer, matches the ~100-line port budget from the epic, and leaves no residual abstraction to maintain when Flask fully replaces Express.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm working tree state
git status

# 2. Verify Task 1's type file exists
ls src/app/services/flask-api.types.ts

# 3. Confirm expected exports are present
grep -E "ContextReadResponse|ContextWriteResponse" src/app/services/flask-api.types.ts

# 4. Baseline Angular test run (expect 0 passing — no spec files yet)
ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -5
```

**If `flask-api.types.ts` is missing entirely**: Task 1 has not been completed. Do not proceed. Run Task 1 first, then return here.

**If `flask-api.types.ts` exists but is missing `ContextReadResponse` or `ContextWriteResponse`**: Task 1 was partially completed. Step 1 below adds them — proceed.

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: 0 Angular spec files, 0 passing.

---

## 3. Files

### To Create (new)
- `src/app/services/flask-context.service.ts` — the service; one `@Injectable`, eight methods, `localhost:3101` hardcoded
- `src/app/services/flask-context.service.spec.ts` — Jasmine unit tests for all eight methods using `HttpClientTestingModule`

### To Modify (cite CODEBASE CONTEXT)
- `src/app/services/flask-api.types.ts` — Task 1 artifact; may need `ContextReadResponse` and `ContextWriteResponse` added if absent. Do NOT touch any types already present.

### To Leave Alone
- `src/app/services/builder.service.ts` — Express service; method signatures here are the mirror target, do not modify
- `src/app/services/principles.service.ts` — same reason
- `src/app/services/codebase.service.ts` — same reason; `scan()` is intentionally NOT mirrored (Phase 2, out of scope)
- `src/app/services/references.service.ts` — same reason
- `src/app/services/projects.service.ts` — Task 2 territory, not context layer
- `flask/` directory — Python backend; not touched by Angular tasks
- `server.js` — Express server on port 3100; unchanged by this task
- `karma.conf.js` — if it exists, do not modify

---

## 4. Implementation Steps

### Step 1: Verify context types in `flask-api.types.ts`

**Action**: Open `flask-api.types.ts`. If `ContextReadResponse` and `ContextWriteResponse` are already exported, skip this step. If either is absent, append them.

**File**: `src/app/services/flask-api.types.ts` (Task 1 artifact, modify only if types are missing)

**Pattern** — append only what is absent:
```typescript
// Derived from flask/api-contract.md — Context Routes section
// GET /api/{builder|principles|codebase|references}
export interface ContextReadResponse {
  content: string;
  exists: boolean;
}

// PUT /api/{builder|principles|codebase|references}
export interface ContextWriteResponse {
  success: boolean;
}
```

**Verify**:
```bash
grep -E "export interface ContextReadResponse|export interface ContextWriteResponse" src/app/services/flask-api.types.ts
# expect: two lines, one per interface
```

---

### Step 2: Create `FlaskContextService`

**Action**: Create the service file. Eight methods: `getBuilder`, `saveBuilder`, `getPrinciples`, `savePrinciples`, `getCodebase`, `saveCodebase`, `getReferences`, `saveReferences`. Import types from Step 1. Hardcode `localhost:3101`. No `scan()` method — that maps to a Phase 2 route not in Flask Phase 1.

The method naming convention is `{verb}{Resource}` — identical verb (`get`/`save`) to the Express counterpart, resource prefix distinguishes methods within the single-service file. `save` matches `BuilderService.save()`, `PrinciplesService.save()`, etc.

**File**: `src/app/services/flask-context.service.ts` (new)

**Complete implementation** — port budget ~40 lines:
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ContextReadResponse, ContextWriteResponse } from './flask-api.types';

@Injectable({ providedIn: 'root' })
export class FlaskContextService {
  private readonly baseUrl = 'http://localhost:3101';

  constructor(private http: HttpClient) {}

  // Builder — mirrors BuilderService.get() / .save()
  getBuilder(): Observable<ContextReadResponse> {
    return this.http.get<ContextReadResponse>(`${this.baseUrl}/api/builder`);
  }

  saveBuilder(content: string): Observable<ContextWriteResponse> {
    return this.http.put<ContextWriteResponse>(`${this.baseUrl}/api/builder`, { content });
  }

  // Principles — mirrors PrinciplesService.get() / .save()
  getPrinciples(): Observable<ContextReadResponse> {
    return this.http.get<ContextReadResponse>(`${this.baseUrl}/api/principles`);
  }

  savePrinciples(content: string): Observable<ContextWriteResponse> {
    return this.http.put<ContextWriteResponse>(`${this.baseUrl}/api/principles`, { content });
  }

  // Codebase — mirrors CodebaseService.get() / .save() (scan() is Phase 2, not mirrored)
  getCodebase(): Observable<ContextReadResponse> {
    return this.http.get<ContextReadResponse>(`${this.baseUrl}/api/codebase`);
  }

  saveCodebase(content: string): Observable<ContextWriteResponse> {
    return this.http.put<ContextWriteResponse>(`${this.baseUrl}/api/codebase`, { content });
  }

  // References — mirrors ReferencesService.get() / .save()
  getReferences(): Observable<ContextReadResponse> {
    return this.http.get<ContextReadResponse>(`${this.baseUrl}/api/references`);
  }

  saveReferences(content: string): Observable<ContextWriteResponse> {
    return this.http.put<ContextWriteResponse>(`${this.baseUrl}/api/references`, { content });
  }
}
```

**Verify**:
```bash
npx tsc --noEmit
# expect: zero errors
```

---

### Step 3: Create `flask-context.service.spec.ts`

**Action**: Create the spec file using Karma/Jasmine + `HttpClientTestingModule`. Each test verifies URL, HTTP method, request body (for PUTs), and response shape. See full assertion bodies in Section 5.

**File**: `src/app/services/flask-context.service.spec.ts` (new)

**Pattern — shape only**:
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { FlaskContextService } from './flask-context.service';
import { ContextReadResponse, ContextWriteResponse } from './flask-api.types';

describe('FlaskContextService', () => {
  let service: FlaskContextService;
  let http: HttpTestingController;
  const BASE = 'http://localhost:3101';

  beforeEach(() => { /* TestBed setup */ });
  afterEach(() => http.verify());

  describe('builder', () => { /* 2 tests */ });
  describe('principles', () => { /* 2 tests */ });
  describe('codebase', () => { /* 2 tests */ });
  describe('references', () => { /* 2 tests */ });
});
```

**Verify**:
```bash
ng test --watch=false --browsers=ChromeHeadless 2>&1 | grep -E "SUMMARY|SUCCESS|FAILED|Executed"
# expect: Executed 8 of 8 SUCCESS
```

---

## 5. Tests

Framework: **Karma + Jasmine** (`karma ~6.4.0`, `jasmine-core ~5.4.0`, `@types/jasmine ~5.1.0` — confirmed in `package.json`). No external test utilities needed beyond `@angular/common/http/testing`.

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { FlaskContextService } from './flask-context.service';
import { ContextReadResponse, ContextWriteResponse } from './flask-api.types';

describe('FlaskContextService', () => {
  let service: FlaskContextService;
  let http: HttpTestingController;
  const BASE = 'http://localhost:3101';

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(FlaskContextService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  // ── Builder ─────────────────────────────────────────────────────────────

  describe('builder', () => {
    it('getBuilder() issues GET /api/builder and returns content + exists', (done) => {
      const mock: ContextReadResponse = { content: 'builder profile', exists: true };
      service.getBuilder().subscribe(res => {
        expect(res.content).toBe('builder profile');
        expect(res.exists).toBeTrue();
        done();
      });
      const req = http.expectOne(`${BASE}/api/builder`);
      expect(req.request.method).toBe('GET');
      req.flush(mock);
    });

    it('saveBuilder() issues PUT /api/builder with {content} body and returns {success}', (done) => {
      const mock: ContextWriteResponse = { success: true };
      service.saveBuilder('updated builder').subscribe(res => {
        expect(res.success).toBeTrue();
        done();
      });
      const req = http.expectOne(`${BASE}/api/builder`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ content: 'updated builder' });
      req.flush(mock);
    });
  });

  // ── Principles ───────────────────────────────────────────────────────────

  describe('principles', () => {
    it('getPrinciples() issues GET /api/principles and returns content + exists', (done) => {
      const mock: ContextReadResponse = { content: 'design principles', exists: true };
      service.getPrinciples().subscribe(res => {
        expect(res.content).toBe('design principles');
        expect(res.exists).toBeTrue();
        done();
      });
      const req = http.expectOne(`${BASE}/api/principles`);
      expect(req.request.method).toBe('GET');
      req.flush(mock);
    });

    it('savePrinciples() issues PUT /api/principles with {content} body and returns {success}', (done) => {
      const mock: ContextWriteResponse = { success: true };
      service.savePrinciples('updated principles').subscribe(res => {
        expect(res.success).toBeTrue();
        done();
      });
      const req = http.expectOne(`${BASE}/api/principles`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ content: 'updated principles' });
      req.flush(mock);
    });
  });

  // ── Codebase ─────────────────────────────────────────────────────────────

  describe('codebase', () => {
    it('getCodebase() issues GET /api/codebase and returns content + exists=false when empty', (done) => {
      const mock: ContextReadResponse = { content: '', exists: false };
      service.getCodebase().subscribe(res => {
        expect(res.content).toBe('');
        expect(res.exists).toBeFalse();
        done();
      });
      const req = http.expectOne(`${BASE}/api/codebase`);
      expect(req.request.method).toBe('GET');
      req.flush(mock);
    });

    it('saveCodebase() issues PUT /api/codebase with {content} body and returns {success}', (done) => {
      const mock: ContextWriteResponse = { success: true };
      service.saveCodebase('codebase snapshot').subscribe(res => {
        expect(res.success).toBeTrue();
        done();
      });
      const req = http.expectOne(`${BASE}/api/codebase`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ content: 'codebase snapshot' });
      req.flush(mock);
    });
  });

  // ── References ───────────────────────────────────────────────────────────

  describe('references', () => {
    it('getReferences() issues GET /api/references and returns content + exists', (done) => {
      const mock: ContextReadResponse = { content: 'reference docs', exists: true };
      service.getReferences().subscribe(res => {
        expect(res.content).toBe('reference docs');
        expect(res.exists).toBeTrue();
        done();
      });
      const req = http.expectOne(`${BASE}/api/references`);
      expect(req.request.method).toBe('GET');
      req.flush(mock);
    });

    it('saveReferences() issues PUT /api/references with {content} body and returns {success}', (done) => {
      const mock: ContextWriteResponse = { success: true };
      service.saveReferences('ref links').subscribe(res => {
        expect(res.success).toBeTrue();
        done();
      });
      const req = http.expectOne(`${BASE}/api/references`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ content: 'ref links' });
      req.flush(mock);
    });
  });
});
```

---

## 6. Commit Plan

1. `feat(flask-context.service): add context types to flask-api.types.ts` — `src/app/services/flask-api.types.ts`: add `ContextReadResponse` and `ContextWriteResponse` (skip if Task 1 already included them — commit only if the file changed)
2. `feat(flask-context.service): implement FlaskContextService for four context paths` — `src/app/services/flask-context.service.ts`: eight methods covering builder/principles/codebase/references GET+PUT against localhost:3101
3. `test(flask-context.service): add Jasmine unit tests for all eight methods` — `src/app/services/flask-context.service.spec.ts`: 8 assertions verifying URL, HTTP verb, body, and response shape

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
ng test --watch=false --browsers=ChromeHeadless
```

**Expected delta**: 0 → 8 passing. Zero pre-existing tests broken (there are no pre-existing Angular specs).

Additionally verify TypeScript compiles clean:
```bash
npx tsc --noEmit
# expect: no output (zero errors)
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible.
  - `git revert <sha-of-types-commit>` — removes context type additions
  - `git revert <sha-of-service-commit>` — removes `flask-context.service.ts`
  - `git revert <sha-of-test-commit>` — removes the spec file
- **Per-branch**: if verification fails and the working tree is in a bad state, `git reset --hard <sha-before-task-3>`. The pre-task sha is readable from `git log` before any edits are made; record it at pre-flight time.

---

## 9. Deviations Allowed

- **`flask-api.types.ts` missing context types**: add them in Step 1 as described; log in the commit body that Task 1 did not include them.
- **`flask-api.types.ts` uses different interface names** (e.g. `ContextResponse` instead of `ContextReadResponse`): use the existing names, update the import in `flask-context.service.ts` and the spec to match; log the deviation.
- **Test framework mismatch** (e.g. project was migrated to Jest after this guide was written): translate `expect(...).toBeTrue()` → `expect(...).toBe(true)`, `done()` callbacks → `async/await`; match the repo's convention and note it.
- **`ng test` never runs cleanly before this task** (Karma not yet configured): investigate `angular.json` test configuration; do not skip tests — fix the runner first.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.

---

## 10. Out of Scope

This task creates `FlaskContextService` and its unit tests. It does not verify that Flask actually returns the right data (that is Task 4's job), does not touch the AI routes layer, and does not wire `FlaskContextService` into any UI component — it is a test harness service consumed only by `ContractCompareSpec`.

- **`scan()` method mirroring `CodebaseService.scan()`** — deferred because `/api/ai/text/scan` is Phase 2 and not implemented in Flask Phase 1. Revisit when the AI routes are ported.
- **`ContractCompareSpec` (Task 4)** — the spec that uses `FlaskContextService` symmetrically against its Express counterparts. Not started here; depends on both Tasks 2 and 3 compiling.
- **`FlaskProjectsService` / `FlaskHealthService` (Task 2)** — parallel task; this guide does not cover those services even if they remain unimplemented when Task 3 runs.
- **Environment-variable indirection for `localhost:3101`** — explicitly excluded by the architecture. No staging environment is planned; do not add `environment.ts` references.
- **Error handling, retry logic, auth headers** — this is a single-user local dev harness; reliability requirements end at "the test run completes." Do not add them.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, mirror pattern, one-consumer rule
- [Epic](./epic.md) — Task scope and port budget (~100 lines)
- [Timeline](./timeline.md) — Update Task 3 status to `done` after verification passes
- `flask/api-contract.md` — Authoritative source for context route shapes (GET/PUT, `content`/`exists`/`success` fields)