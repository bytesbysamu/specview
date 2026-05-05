# Task 4: Write ContractCompareSpec

---

## 1. Context

This task produces `contract-compare.spec.ts` — the single Karma/Jasmine spec that drives the Flask migration acceptance gate. It calls every endpoint through both the Express client (port 3100) and Flask client (port 3101) with identical inputs and asserts that every response field matches, with failure messages that name the endpoint, the differing field, and both values. The spec is the only consumer of `FlaskProjectsService`, `FlaskHealthService`, and `FlaskContextService` from Tasks 2 and 3; it cannot emit meaningful pass/fail results until those services exist and the Flask routes behind them are implemented. It is designed to be written structurally before Flask routes are complete — it will show failing assertions, which is the expected state during the migration window.

**Trade-offs considered:**
- **`HttpClientTestingModule` + mocked responses** — rejected. A mock-based spec would test that the Angular service correctly constructs requests, not that Flask agrees with Express. The migration gate requires live comparison against real servers.
- **Node script calling both APIs without Angular DI** — rejected. Flask services depend on Angular's `HttpClient` and DI container; a Node script would require a parallel HTTP client with no shared infrastructure, duplicating service logic outside its intended execution context.
- **Karma with real `HttpClient` + both servers live** — preferred. Reuses the existing Angular test runner (already configured, zero new tooling), keeps the Flask services in their native DI context, and produces Jasmine assertion failures directly in the terminal with no file I/O.

---

## 2. Pre-flight

```bash
# 1. Confirm git state — two unrelated M entries are expected; do not commit them
git status
# Expected: M references.md, M src/app/components/new-project/new-project.component.ts
# If target files are dirty: stash before starting

git diff HEAD -- src/app/services/flask/
# Expected: nothing — directory does not exist yet; this confirms Task 2 and Task 3 must be done first

# 2. Confirm Tasks 2 and 3 are complete — these files must exist
ls src/app/services/flask/flask-projects.service.ts
ls src/app/services/flask/flask-health.service.ts
ls src/app/services/flask/flask-context.service.ts
ls src/app/services/flask/flask-api.types.ts
# If any file is missing: STOP. Task 4 cannot compile without them. Implement the missing task first.

# 3. Confirm both servers are live
curl -s http://localhost:3100/api/projects | head -c 50   # Express must respond
curl -s http://localhost:3101/health                       # Flask must return {"status":"ok"}

# 4. Confirm Express allows CORS from Karma's default port (9876)
curl -s -I -H "Origin: http://localhost:9876" http://localhost:3100/api/projects | grep -i access-control
# Expected: Access-Control-Allow-Origin header present
# If missing: add cors() middleware to server.js and restart Express [REQUIRES APPROVAL to modify server.js]

# 5. Baseline test count
npm test -- --watch=false 2>&1 | tail -5
# Expected: 0 specs, 0 failures (no .spec.ts files exist yet)
```

**Baseline recorded:** 0 / 0 passing.

---

## 3. Files

### To Create (new)
- `src/app/services/flask/contract-compare.spec.ts` — the one Karma/Jasmine spec file; imports all three Flask services and their Express counterparts, asserts response shapes match per endpoint

### To Modify
None. This task adds one new file only.

### To Leave Alone
- `src/app/services/projects.service.ts` — Express reference client; must not be modified
- `src/app/services/builder.service.ts` — Express reference client; must not be modified
- `src/app/services/principles.service.ts` — Express reference client; must not be modified
- `src/app/services/codebase.service.ts` — Express reference client; must not be modified
- `src/app/services/references.service.ts` — Express reference client; must not be modified
- `src/app/services/flask/flask-projects.service.ts` — Task 2 deliverable; read only
- `src/app/services/flask/flask-health.service.ts` — Task 2 deliverable; read only
- `src/app/services/flask/flask-context.service.ts` — Task 3 deliverable; read only
- `src/app/services/flask/flask-api.types.ts` — Task 1 deliverable; read only
- `server.js` — Express server; out of scope unless CORS pre-flight fails (see Pre-flight step 4)
- `angular.json`, `tsconfig.spec.json` — no changes; the spec file at `src/app/services/flask/` is picked up automatically by the default `src/**/*.spec.ts` glob

---

## 4. Implementation Steps

### Step 1: Verify FlaskContextService method names

**Action:** Before writing a single line of the spec, open `src/app/services/flask/flask-context.service.ts` and record the exact public method names. The spec will call them by name; any mismatch is a compile error.

**File:** `src/app/services/flask/flask-context.service.ts` (Task 3 deliverable)

**Pattern — what to look for:**
```typescript
// Minimum expected public API (Task 3 must have exported these or equivalent):
getBuilder(): Observable<{ content: string; exists: boolean }>
saveBuilder(content: string): Observable<{ success: boolean }>
getPrinciples(): Observable<{ content: string; exists: boolean }>
savePrinciples(content: string): Observable<{ success: boolean }>
getCodebase(): Observable<{ content: string; exists: boolean }>
saveCodebase(content: string): Observable<{ success: boolean }>
getReferences(): Observable<{ content: string; exists: boolean }>
saveReferences(content: string): Observable<{ success: boolean }>
```

**Verify:** `npx tsc --noEmit 2>&1 | grep flask-context` — expect zero errors. If the method names differ from the above, adjust the spec's call sites at the corresponding `it` lines in Step 2. Log the actual names as a deviation.

---

### Step 2: Write `contract-compare.spec.ts`

**Action:** Create the file at the path below. The full body is the canonical implementation; do not abridge.

**File:** `src/app/services/flask/contract-compare.spec.ts` (new)

**Complete implementation:**
```typescript
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { Observable, firstValueFrom } from 'rxjs';
import { ProjectsService } from '../projects.service';
import { BuilderService } from '../builder.service';
import { PrinciplesService } from '../principles.service';
import { CodebaseService } from '../codebase.service';
import { ReferencesService } from '../references.service';
import { FlaskProjectsService } from './flask-projects.service';
import { FlaskHealthService } from './flask-health.service';
import { FlaskContextService } from './flask-context.service';

const m = (ep: string, key: string, express: unknown, flask: unknown): string =>
  `[${ep}] '${key}': Express=${JSON.stringify(express)}, Flask=${JSON.stringify(flask)}`;

describe('ContractCompareSpec: Express (3100) vs Flask (3101)', () => {
  jasmine.DEFAULT_TIMEOUT_INTERVAL = 15000;

  let xp: ProjectsService;
  let fp: FlaskProjectsService;
  let fh: FlaskHealthService;
  let xb: BuilderService;
  let xpr: PrinciplesService;
  let xc: CodebaseService;
  let xr: ReferencesService;
  let fc: FlaskContextService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        ProjectsService, FlaskProjectsService, FlaskHealthService,
        BuilderService, PrinciplesService, CodebaseService, ReferencesService,
        FlaskContextService,
      ]
    });
    xp  = TestBed.inject(ProjectsService);
    fp  = TestBed.inject(FlaskProjectsService);
    fh  = TestBed.inject(FlaskHealthService);
    xb  = TestBed.inject(BuilderService);
    xpr = TestBed.inject(PrinciplesService);
    xc  = TestBed.inject(CodebaseService);
    xr  = TestBed.inject(ReferencesService);
    fc  = TestBed.inject(FlaskContextService);
  });

  // ── Health ────────────────────────────────────────────────────────────────────
  describe('GET /health', () => {
    it('Flask returns { status: "ok" }', async () => {
      const r = await firstValueFrom(fh.check());
      expect(r.status).withContext(m('GET /health', 'status', 'ok', r.status)).toBe('ok');
    });
  });

  // ── Projects ──────────────────────────────────────────────────────────────────
  describe('Projects', () => {
    let id: string;

    beforeEach(async () => {
      id = (await firstValueFrom(
        xp.create('__contract__', [{ filename: 't.md', content: '# test' }])
      )).id;
    });

    afterEach(async () => {
      try { await firstValueFrom(xp.delete(id)); } catch { /* already deleted in DELETE test */ }
    });

    it('GET /api/projects — list shape matches', async () => {
      const [xl, fl] = await Promise.all([firstValueFrom(xp.list()), firstValueFrom(fp.list())]);
      const xi = xl.find(p => p.id === id)!;
      const fi = fl.find(p => p.id === id)!;
      expect(fi).withContext(m('GET /api/projects', 'item-present', xi?.id, fi?.id)).toBeTruthy();
      (['id', 'name', 'createdAt'] as const).forEach(k => {
        expect(fi[k]).withContext(m('GET /api/projects', k, xi[k], fi[k])).toBe(xi[k]);
      });
      expect(Array.isArray(fi.specs))
        .withContext(m('GET /api/projects', 'specs.isArray', true, fi.specs)).toBe(true);
    });

    it('GET /api/projects/:id — detail shape matches', async () => {
      const [xd, fd] = await Promise.all([firstValueFrom(xp.get(id)), firstValueFrom(fp.get(id))]);
      (['id', 'name', 'createdAt'] as const).forEach(k => {
        expect(fd[k]).withContext(m('GET /api/projects/:id', k, xd[k], fd[k])).toBe(xd[k]);
      });
      const xs = xd.specs.find(s => s.filename === 't.md')!;
      const fs = fd.specs.find(s => s.filename === 't.md')!;
      expect(fs?.content)
        .withContext(m('GET /api/projects/:id', 'spec.content', xs?.content, fs?.content))
        .toBe(xs?.content);
    });

    it('POST /api/projects — create response shape matches', async () => {
      const files = [{ filename: 'c.md', content: '# c' }];
      const [xc2, fc2] = await Promise.all([
        firstValueFrom(xp.create('__contract-cx__', files)),
        firstValueFrom(fp.create('__contract-cf__', files)),
      ]);
      (['id', 'name', 'createdAt'] as const).forEach(k => {
        expect(typeof fc2[k])
          .withContext(m('POST /api/projects', `${k}.type`, typeof xc2[k], typeof fc2[k]))
          .toBe(typeof xc2[k]);
      });
      await Promise.all([firstValueFrom(xp.delete(xc2.id)), firstValueFrom(fp.delete(fc2.id))]);
    });

    it('PUT /api/projects/:id/files/:filename — update shape matches', async () => {
      const [xu, fu] = await Promise.all([
        firstValueFrom(xp.updateFile(id, 't.md', '# updated-x')),
        firstValueFrom(fp.updateFile(id, 't.md', '# updated-f')),
      ]);
      expect(fu.success)
        .withContext(m('PUT /api/projects/:id/files/:filename', 'success', xu.success, fu.success))
        .toBe(xu.success);
    });

    it('DELETE /api/projects/:id — delete shape matches', async () => {
      // Create one project per client to avoid shared-filesystem race on the same id
      const [xid, fid] = await Promise.all([
        firstValueFrom(xp.create('__del-x__', [{ filename: 'x.md', content: '' }])).then(r => r.id),
        firstValueFrom(fp.create('__del-f__', [{ filename: 'x.md', content: '' }])).then(r => r.id),
      ]);
      const [xdel, fdel] = await Promise.all([
        firstValueFrom(xp.delete(xid)),
        firstValueFrom(fp.delete(fid)),
      ]);
      expect(fdel.success)
        .withContext(m('DELETE /api/projects/:id', 'success', xdel.success, fdel.success))
        .toBe(xdel.success);
    });
  });

  // ── Context ───────────────────────────────────────────────────────────────────
  describe('Context', () => {
    type CR = { content: string; exists: boolean };
    type SR = { success: boolean };

    async function cmpGet(ep: string, xFn: () => Observable<CR>, fFn: () => Observable<CR>) {
      const [x, f] = await Promise.all([firstValueFrom(xFn()), firstValueFrom(fFn())]);
      expect(typeof f.content).withContext(m(ep, 'content.type', typeof x.content, typeof f.content)).toBe(typeof x.content);
      expect(typeof f.exists).withContext(m(ep, 'exists.type', typeof x.exists, typeof f.exists)).toBe(typeof x.exists);
    }

    async function cmpSave(ep: string, xFn: () => Observable<SR>, fFn: () => Observable<SR>) {
      const [x, f] = await Promise.all([firstValueFrom(xFn()), firstValueFrom(fFn())]);
      expect(f.success).withContext(m(ep, 'success', x.success, f.success)).toBe(x.success);
    }

    it('GET /api/builder',    async () => cmpGet('GET /api/builder',     () => xb.get(),  () => fc.getBuilder()));
    it('PUT /api/builder',    async () => cmpSave('PUT /api/builder',    () => xb.save('__t__'), () => fc.saveBuilder('__t__')));
    it('GET /api/principles', async () => cmpGet('GET /api/principles',  () => xpr.get(), () => fc.getPrinciples()));
    it('PUT /api/principles', async () => cmpSave('PUT /api/principles', () => xpr.save('__t__'), () => fc.savePrinciples('__t__')));
    it('GET /api/codebase',   async () => cmpGet('GET /api/codebase',    () => xc.get(),  () => fc.getCodebase()));
    it('PUT /api/codebase',   async () => cmpSave('PUT /api/codebase',   () => xc.save('__t__'), () => fc.saveCodebase('__t__')));
    it('GET /api/references', async () => cmpGet('GET /api/references',  () => xr.get(),  () => fc.getReferences()));
    it('PUT /api/references', async () => cmpSave('PUT /api/references', () => xr.save('__t__'), () => fc.saveReferences('__t__')));
  });
});
```

**Verify:** `npx tsc --noEmit 2>&1 | grep contract-compare` — expect zero errors. If TypeScript errors appear on Flask service imports, the prerequisite services are missing or have incompatible signatures (log as deviation).

---

### Step 3: Run the spec

**Action:** Start both servers (if not already live), then run `npm test`.

**File:** terminal

**Pattern:**
```bash
# In one terminal (if not already running):
npm run api        # Express on 3100

# In another terminal (if not already running):
cd flask && python app.py   # Flask on 3101

# Run tests:
npm test -- --watch=false
```

**Verify:** Terminal shows `14 specs, N failures` where N is the number of Flask routes not yet implemented. Every failure message must follow the pattern `[ENDPOINT] 'FIELD': Express=..., Flask=...`. If a failure message does NOT follow that pattern (e.g., a network error or a TypeScript runtime crash), diagnose before proceeding — that is a spec bug, not a Flask implementation gap.

---

## 5. Tests

The spec file itself is the test deliverable. The assertions below summarize what each `it` block verifies. These are the complete assertion bodies — already shown in Step 2; restated here for the executor's verification checklist.

**Health (1 assertion):**
```typescript
// GET /health
expect(r.status).withContext(m('GET /health', 'status', 'ok', r.status)).toBe('ok');
```

**Projects list (4 assertions):**
```typescript
// Presence in list, id/name/createdAt equality, specs.isArray
expect(fi).withContext(m('GET /api/projects', 'item-present', xi?.id, fi?.id)).toBeTruthy();
expect(fi[k]).withContext(m('GET /api/projects', k, xi[k], fi[k])).toBe(xi[k]);  // × 3 fields
expect(Array.isArray(fi.specs)).withContext(...).toBe(true);
```

**Projects detail (4 assertions):**
```typescript
// id/name/createdAt equality, spec content equality
expect(fd[k]).withContext(m('GET /api/projects/:id', k, xd[k], fd[k])).toBe(xd[k]);  // × 3
expect(fs?.content).withContext(m('GET /api/projects/:id', 'spec.content', xs?.content, fs?.content)).toBe(xs?.content);
```

**Projects create (3 assertions — typeof comparison, not value):**
```typescript
// id/name/createdAt type equality
expect(typeof fc2[k]).withContext(m('POST /api/projects', `${k}.type`, typeof xc2[k], typeof fc2[k])).toBe(typeof xc2[k]);  // × 3
```

**Projects update (1 assertion):**
```typescript
expect(fu.success).withContext(m('PUT /api/projects/:id/files/:filename', 'success', xu.success, fu.success)).toBe(xu.success);
```

**Projects delete (1 assertion):**
```typescript
expect(fdel.success).withContext(m('DELETE /api/projects/:id', 'success', xdel.success, fdel.success)).toBe(xdel.success);
```

**Context — 8 `it` blocks, 2 assertions each:**
```typescript
// cmpGet: content.type and exists.type both match
expect(typeof f.content).withContext(m(ep, 'content.type', typeof x.content, typeof f.content)).toBe(typeof x.content);
expect(typeof f.exists).withContext(m(ep, 'exists.type', typeof x.exists, typeof f.exists)).toBe(typeof x.exists);

// cmpSave: success value matches
expect(f.success).withContext(m(ep, 'success', x.success, f.success)).toBe(x.success);
```

Total assertions: 1 + 4 + 4 + 3 + 1 + 1 + (8 × 2) = **30 assertions across 14 `it` blocks.**

---

## 6. Commit Plan

One commit — this task is a single file:

1. `test(flask): ContractCompareSpec — 14 Karma/Jasmine assertions against Express+Flask shape parity` — `src/app/services/flask/contract-compare.spec.ts`: full spec comparing all five project endpoints and eight context endpoints

**Deviation logging:** if any Flask service method name required adjustment (Step 1), prefix the commit body with:
```
Deviations:
- FlaskContextService.{actualName} used instead of {expectedName} — Task 3 chose different naming
```

---

## 7. Verification

```bash
npm test -- --watch=false
```

**Expected delta:** 0 → 14 specs registered. With Flask routes fully implemented (Tasks 2 and 3 complete and Flask routes live), expected outcome is 14 passing, 0 failing. During the migration window when Flask routes are partially implemented, failing tests are expected — every failure message must name the endpoint, field, and both values.

**Zero pre-existing tests broken:** the baseline was 0 specs; adding this file cannot regress prior tests.

**Structural smoke check (run after creating the file):**
```bash
# Confirm the spec file does not import from providers directly (N/A here — Angular, not Python)
# Confirm no absolute paths leaked into the spec
grep -n "/Users/\|/home/" src/app/services/flask/contract-compare.spec.ts
# Expected: no output
```

---

## 8. Rollback

- **Per-step:** this task has one commit. `git revert <sha>` removes the spec file cleanly. No other files were modified.
- **Per-branch:** `git reset --hard <pre-task-sha>` returns to the state before Task 4. The Flask service files from Tasks 2 and 3 remain untouched.

---

## 9. Deviations Allowed

- **FlaskContextService method names differ** → read the actual method names from `flask-context.service.ts`, update the call sites in the spec's Context describe block, log in the commit body.
- **FlaskHealthService method is not `check()`** → read the actual name, update the `fh.{method}()` call site in the Health describe block, log in the commit body.
- **`withContext` unavailable** → if `jasmine-core` version predates the `withContext` API, use the `.message(...)` form instead — translate silently, note in commit.
- **CORS blocks requests at runtime** → add `cors()` to `server.js` (Express, port 3100) with `origin: 'http://localhost:9876'`; Flask already uses `flask-cors` or needs it added [REQUIRES APPROVAL for both server changes]; do not work around by changing Karma's port.
- **TypeScript errors on imports** → Tasks 2 or 3 are incomplete or structurally different; STOP, flag which file is missing, do not invent stub services.
- **Step N simplification** → take it, log in commit body.

---

## 10. Out of Scope

This task produces only `contract-compare.spec.ts`. It does not implement Flask routes, modify Express, change any production code path, or configure CI. The spec is intentionally temporary — a migration gate that becomes obsolete when Flask fully replaces Express. Scope is bounded to writing and verifying the one file.

- **Flask route implementation** — belongs in Tasks 2 and 3; this spec only calls them
- **CORS middleware changes** (`server.js`, `flask/app.py`) — pre-flight gate only; if CORS is already configured, no change needed; if not, [REQUIRES APPROVAL] and is a separate commit
- **`scan()` endpoint on CodebaseService** — not mirrored in FlaskContextService; `flask/api-contract.md` marks it Phase 2; do not add it here
- **AI routes** (`/api/ai/text/*`, `/api/ai/implement`) — Phase 2 per `flask/api-contract.md:149`; not covered in any Flask service from Tasks 1–3
- **Error-shape comparison** (404 on missing project, 400 on bad payload) — the architecture explicitly excludes error boundary handling from this epic; compare success-path shapes only
- **Headless Chrome Karma configuration** — currently requires a visible browser process; headless configuration is a CI integration concern deferred until CI integration is planned

**Rule for the executor:** if a change appears helpful but is on this list, STOP and flag it as a deviation rather than expanding scope.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale; sections "Verification Layer" and "Technology Stack"
- [Epic](./epic.md) – Task scope and port budget (~120 lines, one spec file)
- [Timeline](./timeline.md) – Mark Task 4 `in_progress` at start, `done` after verification passes