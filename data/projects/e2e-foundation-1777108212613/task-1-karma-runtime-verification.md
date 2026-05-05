# Task 1: Karma Runtime Verification — Implementation Guide

## 1. Context

The 16 frontend service specs in `spec-doc/src/app/services/` were authored without a live Karma runner. They represent claims, not measurements. This task runs them against a real Chrome-headed Karma instance, aligns any assertions that diverge from actual service behaviour (port budget: ≤5 corrections), and wires the result into a GitHub Actions job so the baseline is machine-enforced before the E2E layer in Tasks 2–4 depends on the same component code. No new specs are written; this task narrows the gap between "specs exist" and "specs pass".

**Trade-offs considered:**
- **Fix assertions vs. delete-and-rewrite failing specs** — rejected; the specs encode intent that was correct when written; only the assertion wiring may be stale. Deleting specs shrinks the baseline before it's been validated.
- **Full Chrome vs. ChromeHeadless for CI** — full Chrome requires a display server (`Xvfb`), adds setup time, and has been the source of phantom CI failures on Ubuntu in comparable setups. `ChromeHeadlessCI` with `--no-sandbox` runs reliably on `ubuntu-latest` without a display.
- **Single combined CI job vs. separate Karma job** — a dedicated `test-frontend` job can run in parallel with `test-backend` (the existing backend suite), matches the builder's path-filtered CI pattern, and keeps the blast radius of a frontend failure isolated from backend output.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# Confirm working tree is clean on target files
git status
git diff HEAD -- spec-doc/karma.conf.js spec-doc/src/app/services/

# Inspect the 16 specs before touching anything
cat spec-doc/karma.conf.js
cat spec-doc/src/app/services/ai.service.spec.ts
cat spec-doc/src/app/services/projects.service.spec.ts

# Record baseline — expect failures or a Chrome-not-found error
cd spec-doc && npm test -- --watch=false 2>&1 | tail -30
```

**Expected pre-flight state**: either `ERROR: Chrome could not be found` (Chrome not installed / not on PATH) or one or more failing specs. Record the exact error and failing spec names before editing.

**If working tree is dirty on target files**: stash or commit unrelated changes before starting.

**Baseline recorded**: 0/16 passing (runner fails) → target: 16/16 passing.

---

## 3. Files

### To Create (new)
- `.github/workflows/test-frontend.yml` — GitHub Actions job that runs `npm test` with ChromeHeadlessCI on every push and pull request; (new)

### To Modify (cited from spec-doc CLAUDE.md)
- `spec-doc/karma.conf.js` — add `ChromeHeadlessCI` custom launcher with `--no-sandbox --disable-setuid-sandbox` flags; set `singleRun: true` under the CI environment path
- `spec-doc/src/app/services/ai.service.spec.ts` — conditional: apply ≤5 assertion corrections if specs are red after Chrome runs; no new `it()` blocks added
- `spec-doc/src/app/services/projects.service.spec.ts` — conditional: same constraint

### To Leave Alone
- `spec-doc/angular.json` — the test architect target already points to `karma.conf.js`; do not alter builder config
- `spec-doc/src/app/services/ai.service.ts` — implementation is the source of truth; specs must align to it, not vice versa
- `spec-doc/src/app/services/projects.service.ts` — same; no implementation changes in this task
- `spec-doc/src/app/components/` — component specs (if any) are out of scope for Task 1; touch nothing here
- `spec-doc/package.json` — no new dependencies; Karma and Chrome launcher are already installed in a standard Angular 19 project

---

## 4. Implementation Steps

### Step 1: Read karma.conf.js and add ChromeHeadlessCI launcher

**Action**: Open `spec-doc/karma.conf.js`. Locate the `config.set({...})` block. Add a `customLaunchers` entry for `ChromeHeadlessCI` and update the default `browsers` array so a CI-safe headless browser is always available.

**File**: `spec-doc/karma.conf.js` (cited from spec-doc CLAUDE.md — Angular 19 project root)

**Pattern** — add inside the `config.set({...})` object, adjacent to any existing `browsers` key:

```javascript
// karma.conf.js
module.exports = function (config) {
  config.set({
    // ... existing keys unchanged ...

    customLaunchers: {
      ChromeHeadlessCI: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox', '--disable-setuid-sandbox'],
      },
    },

    // Replace or extend existing browsers array:
    browsers: ['ChromeHeadlessCI'],
    singleRun: false,            // keep false for local `npm test --watch`
  });
};
```

> **Note on `singleRun`**: leave it `false` in `karma.conf.js` (local dev stays in watch mode). The CI command will pass `--watch=false` on the command line, which overrides it.

**Verify**:
```bash
cd spec-doc && npm test -- --watch=false --browsers=ChromeHeadlessCI 2>&1 | tail -40
```
Expect: runner launches, specs execute (pass or fail), no `Chrome could not be found` error. Record exact pass/fail count.

---

### Step 2: Audit and fix failing specs (conditional — apply only if runner is red)

**Action**: For each failing spec, read the assertion and the corresponding service method. Apply the minimal edit that makes the assertion match actual service behaviour. Do **not** delete any `it()` block. Do **not** add new `it()` blocks. Do **not** change the service implementation.

**File**: `spec-doc/src/app/services/ai.service.spec.ts` and/or `spec-doc/src/app/services/projects.service.spec.ts`

**Decision tree per failing spec**:

1. **Wrong expected value** (e.g., URL path changed from `/api/ai` to `/api/ai/text`) — update the `toEqual` / `expectOne` argument to match the actual service call.
2. **HttpClient setup mismatch** — Angular 19 uses `provideHttpClient()` + `provideHttpClientTesting()`, not the legacy `HttpClientTestingModule`. If the spec uses the legacy form, migrate the `TestBed.configureTestingModule` providers block:

```typescript
// BEFORE (Angular < 15 style — will fail with standalone providers)
imports: [HttpClientTestingModule]

// AFTER (Angular 19 standalone style)
providers: [
  provideHttpClient(),
  provideHttpClientTesting(),
]
```

3. **`TestBed.get()` deprecation** — replace with `TestBed.inject()`:

```typescript
// BEFORE
const http = TestBed.get(HttpTestingController);

// AFTER
const http = TestBed.inject(HttpTestingController);
```

4. **Missing `afterEach(() => http.verify())`** — add it if `HttpTestingController` is used but verify is absent; this causes spec pollution that makes later specs fail non-deterministically.

5. **Async handling** — if a spec calls a method that returns an `Observable` but has no `done` callback or `fakeAsync`/`flush`, wrap with `fakeAsync`:

```typescript
it('validPayload_returnsGeneratedText', fakeAsync(() => {
  service.generate('prompt', 'balanced').subscribe(result => {
    expect(result.text).toBeTruthy();
  });
  const req = http.expectOne('/api/ai/text');
  req.flush({ text: 'generated content' });
  flush();
}));
```

**Port budget hard stop**: if more than 5 `it()` blocks require changes, STOP. Log which specs are failing and why in the commit body, mark as a deviation, and flag for human review. Do not silently expand scope.

**Verify**:
```bash
cd spec-doc && npm test -- --watch=false --browsers=ChromeHeadlessCI 2>&1 | tail -20
```
Expect: `Executed 16 of 16 SUCCESS` (or the number the runner reports — record it; it becomes the canonical baseline count).

---

### Step 3: Add GitHub Actions `test-frontend` job

**Action**: Create `.github/workflows/test-frontend.yml`. Wire it to path filters on `spec-doc/**` so it only runs when the Angular project changes, consistent with the builder's existing path-change detection pattern (dorny/paths-filter).

**File**: `.github/workflows/test-frontend.yml` (new)

**Pattern**:

```yaml
name: test-frontend

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            frontend:
              - 'spec-doc/src/**'
              - 'spec-doc/karma.conf.js'
              - 'spec-doc/angular.json'
              - 'spec-doc/package.json'

  test-frontend:
    needs: changes
    if: needs.changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: spec-doc

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: spec-doc/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Run Karma specs
        run: npm test -- --watch=false --browsers=ChromeHeadlessCI
```

**Verify**:
```bash
# Dry-run: validate YAML syntax locally (requires actionlint or yq)
cat .github/workflows/test-frontend.yml | python3 -c "import sys, yaml; yaml.safe_load(sys.stdin); print('YAML valid')"
```
Expect: `YAML valid` with no parse errors. Full CI verification happens after push (see Section 7).

---

## 5. Tests

The 16 specs already exist. The only test work in this task is assertion correction. Below are the concrete replacement patterns for each failure category identified in Step 2. These are not new tests — they are the repaired forms of pre-existing assertions.

**Framework**: Karma + Jasmine (Angular 19 default). Match `describe` / `it` / `expect` / `fakeAsync` / `flush` syntax exactly.

```typescript
// FILE: spec-doc/src/app/services/ai.service.spec.ts
// Repair pattern A — migrate HttpClientTestingModule to standalone providers
// Apply if TestBed setup uses the legacy imports array form

import { TestBed, fakeAsync, flush } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { AiService } from './ai.service';

describe('AiService', () => {
  let service: AiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AiService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(AiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();   // fails the spec if an unexpected request was made
  });

  // Repair pattern B — wrap Observable consumption in fakeAsync + flush
  it('validPrompt_returnsRewriteResponse', fakeAsync(() => {
    let result: { text: string } | undefined;

    service.rewrite('original text', 'make concise').subscribe(r => { result = r; });

    const req = http.expectOne('http://localhost:3100/api/ai/text');
    expect(req.request.method).toBe('POST');
    req.flush({ text: 'concise version' });
    flush();

    expect(result).toBeDefined();
    expect(result!.text).toBe('concise version');
  }));

  // Repair pattern C — correct URL if service was refactored
  // Check ai.service.ts for the actual endpoint before editing this value
  it('networkError_surfacesErrorToSubscriber', fakeAsync(() => {
    let caughtError: Error | undefined;

    service.rewrite('text', 'expand').subscribe({
      next: () => fail('should not emit'),
      error: (e: Error) => { caughtError = e; },
    });

    const req = http.expectOne('http://localhost:3100/api/ai/text');
    req.error(new ProgressEvent('network error'));
    flush();

    expect(caughtError).toBeDefined();
  }));
});
```

```typescript
// FILE: spec-doc/src/app/services/projects.service.spec.ts
// Repair pattern D — TestBed.inject() replaces TestBed.get()
import { TestBed, fakeAsync, flush } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { ProjectsService } from './projects.service';

describe('ProjectsService', () => {
  let service: ProjectsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ProjectsService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(ProjectsService);       // not TestBed.get()
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => { http.verify(); });

  it('listProjects_callsCorrectEndpoint', fakeAsync(() => {
    let projects: unknown[] | undefined;

    service.list().subscribe(p => { projects = p; });

    const req = http.expectOne('http://localhost:3100/api/projects');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 'proj-1', name: 'Test Project' }]);
    flush();

    expect(projects).toHaveSize(1);
    expect((projects as { id: string }[])[0].id).toBe('proj-1');
  }));

  it('createProject_postsToCorrectEndpoint', fakeAsync(() => {
    let created: { id: string } | undefined;

    service.create({ name: 'New Project' }).subscribe(p => { created = p as { id: string }; });

    const req = http.expectOne('http://localhost:3100/api/projects');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'New Project' });
    req.flush({ id: 'proj-2', name: 'New Project' });
    flush();

    expect(created!.id).toBe('proj-2');
  }));
});
```

> **Executor instruction**: these are the repair shapes. Before applying, read the actual failing assertion and the actual service method. If the repair pattern above matches the failure category, apply it. If the actual failure is something else, apply the minimal fix and log it as a deviation in the commit body.

---

## 6. Commit Plan

**Executor instruction**: commit after **each step** completes — not at the end of the task. Run `git commit` before moving to the next step. Each commit below corresponds to a numbered step above.

1. **`chore(karma): add ChromeHeadlessCI launcher for CI`** — after Step 1 — `spec-doc/karma.conf.js`: adds custom launcher + updates browsers array. Runner must execute without a Chrome-not-found error before this commit.

2. **`fix(specs): align service spec assertions with Angular 19 providers`** — after Step 2 — `spec-doc/src/app/services/ai.service.spec.ts` and/or `projects.service.spec.ts`: minimal assertion corrections only. **Skip this commit entirely if all 16 specs pass after Step 1.** If this commit is created, prefix the body with `Deviations:` and list each changed assertion with one line of reasoning.

3. **`ci(frontend): add Karma test job with path filtering`** — after Step 3 — `.github/workflows/test-frontend.yml`: new file. Include the final passing spec count in the commit body (e.g., `Baseline: 16/16 passing`).

**Deviation logging format**:
```
fix(specs): align service spec assertions with Angular 19 providers

Deviations:
- ai.service.spec.ts: replaced HttpClientTestingModule with provideHttpClientTesting() — Angular 19 standalone providers require this form
- projects.service.spec.ts: replaced TestBed.get() with TestBed.inject() — deprecated API removed in Angular 19
```

---

## 7. Verification

```bash
cd spec-doc && npm test -- --watch=false --browsers=ChromeHeadlessCI
```

**Expected delta**: 0/16 passing (runner error) → **16/16 passing**. If the runner was already launching before this task but some specs were red, the delta is (N failing) → 0 failing. Zero pre-existing green specs may be broken — if any previously passing spec turns red, STOP and investigate before committing.

**CI verification** [REQUIRES APPROVAL — pushes to remote]:
```bash
git push origin <branch-name>
# Then verify the 'test-frontend' Actions job appears and goes green
# on the GitHub Actions tab
```

---

## 8. Rollback

- **Per-step**: every commit is independently revertible.
  - Step 1 revert: `git revert <karma-conf-sha>` — restores original `karma.conf.js`
  - Step 2 revert: `git revert <spec-fix-sha>` — restores original spec assertions
  - Step 3 revert: `git revert <ci-workflow-sha>` — removes the workflow file

- **Per-branch**: if verification fails catastrophically (e.g., a spec fix accidentally broke a previously green spec and the revert isn't clean):
  ```bash
  git reset --hard <pre-task-sha>   # returns to state before task started
  ```
  Record the `pre-task-sha` from `git log --oneline -5` during Pre-flight before editing.

---

## 9. Deviations Allowed

- **`karma.conf.js` already has `ChromeHeadlessCI`** → skip Step 1. Run the specs immediately. Log "ChromeHeadlessCI already configured" in the Step 3 commit body.
- **Spec count is not 16** → the task description says 16; if the runner reports a different number, record the actual count, proceed with making all of them pass, and log the discrepancy in the Step 2 or Step 3 commit body. Do not invent specs to reach 16.
- **More than 5 specs fail** → STOP. This exceeds the port budget. Commit the karma.conf.js change (Step 1) so the runner is functional, then flag the failures with a list of the failing spec names and error messages. Do not attempt mass fixes — this signals a larger alignment problem that requires human triage.
- **`dorny/paths-filter` not present in existing workflows** → use the same version already in the repo (inspect `.github/workflows/*.yml` first). If no workflows exist at all, omit the `changes` job and trigger unconditionally on push/PR — log as deviation.
- **Side-effect required** (push to remote, schema migration, `npm install` of new package) → STOP, mark `[REQUIRES APPROVAL]`, ask before proceeding.
- **Step N fix unlocks an obvious simplification for Step N+1** → take it, log the deviation in the commit body.

---

## 10. Out of Scope

This task delivers exactly one thing: 16 existing service specs confirmed passing on a real Chrome-based Karma runner, with a CI job that keeps them green. It does not expand test coverage, touch component code, or introduce any new testing infrastructure beyond the ChromeHeadlessCI launcher and the GitHub Actions workflow.

- **Component specs** (`editor`, `preview`, `operation-bar`, `sidebar`, `new-project`) — explicitly deferred in the architecture. Trigger condition: component coverage is named as the gap blocking a release.
- **`[data-test]` selector retrofit on Angular templates** — belongs to Task 2. The executor must not add `data-test` attributes to any template while working on this task.
- **Playwright installation** — belongs to Task 2. No new `devDependencies` are installed here.
- **`@pytest.mark` sweep on the Flask backend suite** — belongs to a separate backend concern. Do not touch `spec-doc/flask/tests/`.
- **Spec file creation for uncovered services or components** — port budget is 0 new specs. Any `it()` block that does not already exist in the repo is out of scope.
- **Performance optimisation of the Karma run** (parallel workers, sharding) — premature until the baseline has run through CI for one sprint and timing data motivates it.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than absorbing it into this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for the E2E foundation
- [Epic](./epic.md) — Scope and task list
- [Timeline](./timeline.md) — Update Task 1 status to ✅ after CI job goes green