# Task 2: Frontend Service Specs

## 1. Context

This task closes the five-of-seven uncovered service gap in spec-doc's Angular test suite by writing spec files for `ai.service.ts`, `principles.service.ts`, `codebase.service.ts`, `references.service.ts`, and `implementation.service.ts`, and by co-locating a per-service mock factory file alongside each. No new testing infrastructure is introduced — each spec follows the absolute-URL and `HttpTestingController` pattern already established in `builder.service.spec.ts` and `projects.service.spec.ts`. The mock factories are the primary forward-looking deliverable: they become the contract for how component tests stub service dependencies when that epic begins, so the factory shape must reflect the real service interface and remain stable.

**Trade-offs considered**:
- **Single combined spec file for all five services** — rejected; couples unrelated services in one run and makes focused re-runs harder to scope, especially when a single service method signature changes
- **Mock factories in a central `__mocks__/` directory** — rejected; co-location with the source file is the Angular convention (`ai.service.ts` + `ai.service.mock.ts` in the same directory), matches the existing `builder.service.mock.ts` shape if one exists, and avoids import-path confusion for component test authors
- **Chosen: one spec + one mock per service, collocated with the source** — consistent with existing pattern, independently runnable per service, each mock factory independently importable; the `createMock*()` return type mirrors the real interface so component tests compile with the same type checker guarantees as production code

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# Confirm clean working tree on target directory
git status
git diff HEAD -- src/app/services/

# Read the two established pattern references BEFORE writing anything
cat src/app/services/builder.service.spec.ts
cat src/app/services/projects.service.spec.ts

# Read each service to record its public methods, return types, and HTTP endpoints
cat src/app/services/ai.service.ts
cat src/app/services/principles.service.ts
cat src/app/services/codebase.service.ts
cat src/app/services/references.service.ts
cat src/app/services/implementation.service.ts

# Record baseline test count — fill in N below before editing
npx ng test --watch=false 2>&1 | tail -10
```

**If working tree is dirty on target files**: stash unrelated changes before starting.

**Baseline recorded**: ___/___ passing (executor fills in from pre-flight output).

**Hard gate**: The architecture doc names the TestBed vs render-wrapper question as a prerequisite for this task because the mock factory shape locks in the component test convention. Before writing any mock factory, confirm that `builder.service.spec.ts` uses `TestBed.configureTestingModule` (not a render wrapper). If it does not, STOP and flag — do not proceed until the component test convention is confirmed.

**Provider pattern note**: Angular 19 standalone projects may use either `HttpClientTestingModule` (legacy) or `provideHttpClient() + provideHttpClientTesting()` (current). Record exactly which form the existing spec files use and replicate it verbatim — do not mix forms.

---

## 3. Files

### To Create (new)
- `src/app/services/ai.service.spec.ts` — spec for `AiService`; covers all public HTTP-calling methods; follows recorded pattern
- `src/app/services/ai.service.mock.ts` — exports `createMockAiService(): jasmine.SpyObj<AiService>`; method list derived from the service's public surface
- `src/app/services/principles.service.spec.ts` — spec for `PrinciplesService`
- `src/app/services/principles.service.mock.ts` — exports `createMockPrinciplesService(): jasmine.SpyObj<PrinciplesService>`
- `src/app/services/codebase.service.spec.ts` — spec for `CodebaseService`
- `src/app/services/codebase.service.mock.ts` — exports `createMockCodebaseService(): jasmine.SpyObj<CodebaseService>`
- `src/app/services/references.service.spec.ts` — spec for `ReferencesService`
- `src/app/services/references.service.mock.ts` — exports `createMockReferencesService(): jasmine.SpyObj<ReferencesService>`
- `src/app/services/implementation.service.spec.ts` — spec for `ImplementationService`
- `src/app/services/implementation.service.mock.ts` — exports `createMockImplementationService(): jasmine.SpyObj<ImplementationService>`

### To Modify
- None — no existing files are modified in this task.

### To Leave Alone
- `src/app/services/builder.service.spec.ts` — pattern reference only; read, do not edit
- `src/app/services/projects.service.spec.ts` — pattern reference only; read, do not edit
- `src/app/services/ai.service.ts` — source of truth for `AiService` interface; read only
- `src/app/services/principles.service.ts` — source of truth; read only
- `src/app/services/codebase.service.ts` — source of truth; read only
- `src/app/services/references.service.ts` — source of truth; read only
- `src/app/services/implementation.service.ts` — source of truth; read only
- `server.js` — Express backend; frontend test work does not touch it
- `src/app/components/**` — component test authoring is deferred; do not add `data-test` attributes or component specs in this task

---

## 4. Implementation Steps

### Step 1: Extract and record the provider pattern from existing specs

**Action**: Read `builder.service.spec.ts` and `projects.service.spec.ts`. Extract and note the exact import paths, provider registration form (`HttpClientTestingModule` vs `provideHttpClient()`), `beforeEach` teardown, and the absolute-URL base string used in `expectOne()` calls. This step produces no files — it is recon only. Do not commit.

**File**: `src/app/services/builder.service.spec.ts`, `src/app/services/projects.service.spec.ts` (read only)

**Pattern** (representative — executor must verify against actual file):
```typescript
// One of two possible forms — match exactly what the existing files use:

// Form A — Angular 19 current:
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
TestBed.configureTestingModule({
  providers: [BuilderService, provideHttpClient(), provideHttpClientTesting()]
});

// Form B — legacy:
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
TestBed.configureTestingModule({
  imports: [HttpClientTestingModule],
  providers: [BuilderService]
});
```

**Verify**: `cat src/app/services/builder.service.spec.ts` — read succeeds and the provider form is legible. Record which form is in use before proceeding.

---

### Step 2: `ai.service.spec.ts` + `ai.service.mock.ts`

**Action**: Read `ai.service.ts`. Record every `public` method that issues an HTTP call and the endpoint path each calls. The spec-doc CLAUDE.md states base URL `http://localhost:3100/api/ai/text`; verify this is what the service file uses. Write the spec with one `it` block per HTTP-calling method. Write the mock factory with `jasmine.createSpyObj` listing every public method name.

**File**: `src/app/services/ai.service.spec.ts` (new), `src/app/services/ai.service.mock.ts` (new)

**Pattern** (adapt method names and endpoint paths to match actual `ai.service.ts`):
```typescript
// ai.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AiService } from './ai.service';

describe('AiService', () => {
  let service: AiService;
  let httpMock: HttpTestingController;
  const BASE = 'http://localhost:3100/api/ai/text';

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AiService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(AiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => { httpMock.verify(); });

  it('generate_usesAbsolutePostUrl', () => {
    service.generate('Write an epic').subscribe();
    const req = httpMock.expectOne(`${BASE}/generate`);
    expect(req.request.method).toBe('POST');
    req.flush({ text: 'Generated content' });
  });

  it('rewrite_usesAbsolutePostUrl', () => {
    service.rewrite('original text', 'expand').subscribe();
    const req = httpMock.expectOne(`${BASE}/rewrite`);
    expect(req.request.method).toBe('POST');
    req.flush({ text: 'Rewritten content' });
  });
});
```

```typescript
// ai.service.mock.ts
import { AiService } from './ai.service';

export function createMockAiService(): jasmine.SpyObj<AiService> {
  // List every public method from ai.service.ts — adapt if the actual interface differs
  return jasmine.createSpyObj<AiService>('AiService', ['generate', 'rewrite']);
}
```

**Verify**: `npx ng test --watch=false --include=src/app/services/ai.service.spec.ts 2>&1 | tail -5` — all `ai.service.spec.ts` specs pass, 0 failing.

---

### Step 3: `principles.service.spec.ts` + `principles.service.mock.ts`

**Action**: Read `principles.service.ts`. Record every public HTTP-calling method and its endpoint. Write the spec and mock factory following the same structural pattern as Step 2.

**File**: `src/app/services/principles.service.spec.ts` (new), `src/app/services/principles.service.mock.ts` (new)

**Pattern** (endpoint path derived from service file — adjust `expectOne` URL to match):
```typescript
// principles.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PrinciplesService } from './principles.service';

describe('PrinciplesService', () => {
  let service: PrinciplesService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [PrinciplesService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(PrinciplesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => { httpMock.verify(); });

  it('get_usesAbsoluteGetUrl', () => {
    // Adjust URL string to the exact endpoint the service calls
    service.get().subscribe();
    const req = httpMock.expectOne('http://localhost:3100/api/principles');
    expect(req.request.method).toBe('GET');
    req.flush('# Architecture Principles');
  });
});
```

```typescript
// principles.service.mock.ts
import { PrinciplesService } from './principles.service';

export function createMockPrinciplesService(): jasmine.SpyObj<PrinciplesService> {
  return jasmine.createSpyObj<PrinciplesService>('PrinciplesService', ['get']);
}
```

**Verify**: `npx ng test --watch=false --include=src/app/services/principles.service.spec.ts 2>&1 | tail -5` — all specs pass, 0 failing.

---

### Step 4: `codebase.service.spec.ts` + `codebase.service.mock.ts`

**Action**: Read `codebase.service.ts`. Write spec and mock factory.

**File**: `src/app/services/codebase.service.spec.ts` (new), `src/app/services/codebase.service.mock.ts` (new)

**Pattern**:
```typescript
// codebase.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { CodebaseService } from './codebase.service';

describe('CodebaseService', () => {
  let service: CodebaseService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CodebaseService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(CodebaseService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => { httpMock.verify(); });

  it('getContext_usesAbsoluteGetUrl', () => {
    // Adjust URL to match the actual endpoint in codebase.service.ts
    service.getContext().subscribe();
    const req = httpMock.expectOne('http://localhost:3100/api/codebase');
    expect(req.request.method).toBe('GET');
    req.flush('# Codebase Context');
  });
});
```

```typescript
// codebase.service.mock.ts
import { CodebaseService } from './codebase.service';

export function createMockCodebaseService(): jasmine.SpyObj<CodebaseService> {
  return jasmine.createSpyObj<CodebaseService>('CodebaseService', ['getContext']);
}
```

**Verify**: `npx ng test --watch=false --include=src/app/services/codebase.service.spec.ts 2>&1 | tail -5` — all specs pass, 0 failing.

---

### Step 5: `references.service.spec.ts` + `references.service.mock.ts`

**Action**: Read `references.service.ts`. Write spec and mock factory.

**File**: `src/app/services/references.service.spec.ts` (new), `src/app/services/references.service.mock.ts` (new)

**Pattern**:
```typescript
// references.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ReferencesService } from './references.service';

describe('ReferencesService', () => {
  let service: ReferencesService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ReferencesService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(ReferencesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => { httpMock.verify(); });

  it('getAll_usesAbsoluteGetUrl', () => {
    // Adjust URL to match the actual endpoint in references.service.ts
    service.getAll().subscribe();
    const req = httpMock.expectOne('http://localhost:3100/api/references');
    expect(req.request.method).toBe('GET');
    req.flush('## Reference Code');
  });
});
```

```typescript
// references.service.mock.ts
import { ReferencesService } from './references.service';

export function createMockReferencesService(): jasmine.SpyObj<ReferencesService> {
  return jasmine.createSpyObj<ReferencesService>('ReferencesService', ['getAll']);
}
```

**Verify**: `npx ng test --watch=false --include=src/app/services/references.service.spec.ts 2>&1 | tail -5` — all specs pass, 0 failing.

---

### Step 6: `implementation.service.spec.ts` + `implementation.service.mock.ts`

**Action**: Read `implementation.service.ts`. Write spec and mock factory. This service likely posts a task spec body and receives a generated implementation guide — assert both the method and the request body shape.

**File**: `src/app/services/implementation.service.spec.ts` (new), `src/app/services/implementation.service.mock.ts` (new)

**Pattern**:
```typescript
// implementation.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ImplementationService } from './implementation.service';

describe('ImplementationService', () => {
  let service: ImplementationService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ImplementationService, provideHttpClient(), provideHttpClientTesting()]
    });
    service = TestBed.inject(ImplementationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => { httpMock.verify(); });

  it('generate_postsToAbsoluteUrl', () => {
    const taskSpec = '## Task 2\nWrite service specs';
    // Adjust method name, URL, and request body fields to match the actual service
    service.generate(taskSpec).subscribe();
    const req = httpMock.expectOne('http://localhost:3100/api/implementation');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(jasmine.objectContaining({ spec: taskSpec }));
    req.flush({ text: '# Implementation Guide\n...' });
  });
});
```

```typescript
// implementation.service.mock.ts
import { ImplementationService } from './implementation.service';

export function createMockImplementationService(): jasmine.SpyObj<ImplementationService> {
  return jasmine.createSpyObj<ImplementationService>('ImplementationService', ['generate']);
}
```

**Verify**: `npx ng test --watch=false --include=src/app/services/implementation.service.spec.ts 2>&1 | tail -5` — all specs pass, 0 failing.

---

## 5. Tests

Complete `it` block bodies for all five services. The executor adapts method names and URL strings from the actual service files but must not stub out assertions.

```typescript
// --- AiService ---
it('generate_usesAbsolutePostUrl', () => {
  service.generate('Write an epic').subscribe();
  const req = httpMock.expectOne('http://localhost:3100/api/ai/text/generate');
  expect(req.request.method).toBe('POST');
  req.flush({ text: 'Generated content' });
});

it('rewrite_usesAbsolutePostUrl', () => {
  service.rewrite('original text', 'expand').subscribe();
  const req = httpMock.expectOne('http://localhost:3100/api/ai/text/rewrite');
  expect(req.request.method).toBe('POST');
  req.flush({ text: 'Rewritten content' });
});

// --- PrinciplesService ---
it('get_usesAbsoluteGetUrl', () => {
  service.get().subscribe(result => {
    expect(result).toContain('Architecture');
  });
  const req = httpMock.expectOne('http://localhost:3100/api/principles');
  expect(req.request.method).toBe('GET');
  req.flush('# Architecture Principles\n...');
});

// --- CodebaseService ---
it('getContext_usesAbsoluteGetUrl', () => {
  service.getContext().subscribe(result => {
    expect(result).toBeTruthy();
  });
  const req = httpMock.expectOne('http://localhost:3100/api/codebase');
  expect(req.request.method).toBe('GET');
  req.flush('# Codebase Context\n...');
});

// --- ReferencesService ---
it('getAll_usesAbsoluteGetUrl', () => {
  service.getAll().subscribe(result => {
    expect(result).toBeTruthy();
  });
  const req = httpMock.expectOne('http://localhost:3100/api/references');
  expect(req.request.method).toBe('GET');
  req.flush('## Reference Code\n...');
});

// --- ImplementationService ---
it('generate_postsToAbsoluteUrl', () => {
  const taskSpec = '## Task 2\nWrite service specs';
  service.generate(taskSpec).subscribe(result => {
    expect(result).toEqual(jasmine.objectContaining({ text: jasmine.any(String) }));
  });
  const req = httpMock.expectOne('http://localhost:3100/api/implementation');
  expect(req.request.method).toBe('POST');
  expect(req.request.body).toEqual(jasmine.objectContaining({ spec: taskSpec }));
  req.flush({ text: '# Implementation Guide\n...' });
});
```

**Note on `httpMock.verify()`**: the `afterEach` call to `verify()` is itself a test assertion — it fails if any request was opened but not flushed. Every `it` block that calls a service method must flush the matching `expectOne` request, or `verify()` will fail with an unconsumed-request error.

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end. Step 1 produces no files; the first commit is after Step 2.

1. `test(ai): add AiService spec and mock factory` — after Step 2 — `src/app/services/ai.service.spec.ts`, `src/app/services/ai.service.mock.ts`
2. `test(principles): add PrinciplesService spec and mock factory` — after Step 3 — `src/app/services/principles.service.spec.ts`, `src/app/services/principles.service.mock.ts`
3. `test(codebase): add CodebaseService spec and mock factory` — after Step 4 — `src/app/services/codebase.service.spec.ts`, `src/app/services/codebase.service.mock.ts`
4. `test(references): add ReferencesService spec and mock factory` — after Step 5 — `src/app/services/references.service.spec.ts`, `src/app/services/references.service.mock.ts`
5. `test(implementation): add ImplementationService spec and mock factory` — after Step 6 — `src/app/services/implementation.service.spec.ts`, `src/app/services/implementation.service.mock.ts`

**Deviation logging**: if a step's method name, endpoint URL, or provider registration form required adjustment from the guide, prefix the commit body with `Deviations:` and one line per deviation (e.g., `Deviations: rewrite() signature is rewrite(payload: RewriteRequest), adjusted expectOne body assertion`).

---

## 7. Verification

```bash
npx ng test --watch=false 2>&1 | tail -10
```

**Expected delta**: baseline N → N+9 passing (2 new specs for `AiService`, 1 each for the remaining four services = 6 new spec functions; the mock factory files contain no `it` blocks and add 0 to the spec count). Zero pre-existing tests broken. The exact delta depends on how many `it` blocks the executor writes per service — the minimum is one per HTTP-calling public method; if a service has two methods, its spec contributes 2 specs. The executor should record the final count and update the timeline.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` undoes that service pair without touching the others.
- **Per-branch**: if verification fails and the cause is unclear, `git reset --hard <pre-task-sha>` restores the baseline. Because all ten files are new (nothing modified), a hard reset loses only the new files, with zero risk to pre-existing tests.
- **Targeted file removal**: if a single service spec is causing cascading failures, `git rm src/app/services/{name}.service.spec.ts src/app/services/{name}.service.mock.ts && git commit -m "revert({name}): remove broken spec pair"` isolates the rollback without touching the other four pairs.

---

## 9. Deviations Allowed

- **Method name differs from the pattern snippet** — read the actual service file and adjust; log in commit body. The patterns in this guide use inferred names (`generate`, `rewrite`, `get`, `getContext`, `getAll`) that may not match exactly.
- **Endpoint URL differs** — adjust `expectOne()` to match the actual URL the service calls; log in commit body. The base `http://localhost:3100` prefix is from the spec-doc CLAUDE.md and should be stable, but path segments may vary.
- **Provider registration uses `HttpClientTestingModule` not `provideHttpClient()`** — match exactly what the existing spec files use; do not introduce the alternative form, even if it is the Angular 19 preferred path; log as a deviation if the form used here differs from the existing pattern.
- **A service method returns a `Signal<T>` rather than `Observable<T>`** — the `httpMock.expectOne` pattern is `Observable`-specific; if a method wraps an `HttpClient` call in a signal, test the signal's computed value rather than subscribing; log as a deviation and adapt the assertion accordingly.
- **Step N unlocks an obvious mock factory simplification for Step N+1** — take it, log deviation in the commit body.
- **Side-effect required** (push, schema change, package install) — STOP, mark `[REQUIRES APPROVAL]`, and ask.

---

## 10. Out of Scope

This task delivers service specs and mock factories only. It does not author component tests, retrofit `data-test` attributes, or add any E2E infrastructure — those depend on the mock factories this task ships and are scoped to separate tasks in the epic. The executor must not expand scope even if a component test looks easy to add alongside a service spec.

- **Component test authoring** — deferred; the architecture doc is explicit that component tests begin only after at least one mock factory file has a confirmed real consumer; no `*.component.spec.ts` file is written here
- **`data-test` attribute retrofit** — scoped to Task 5 and limited to the four components that E2E feature files exercise; do not add attributes to templates in this task
- **Additional `it` blocks for error paths** — the spec for each service covers the happy-path HTTP exchange; error-path coverage (network error, 4xx/5xx response handling) is intentionally deferred until the snapshot and contract integration layers (Tasks 3 and 4) establish the envelope shape those error paths are expected to return
- **Mock return value pre-configuration** — mock factory files export spy objects with all methods as spies; they do not pre-configure `returnValue` defaults; component tests configure return values inline per scenario, keeping the factory reusable across test scenarios that expect different outcomes
- **`ng test` Karma configuration changes** — do not add `--include` patterns to `angular.json` or `karma.conf.js`; per-file runs in this guide use CLI flags only

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than absorbing it into this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Full design rationale including the TestBed decision and mock factory shape
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Update status to ✅ Done after verification passes