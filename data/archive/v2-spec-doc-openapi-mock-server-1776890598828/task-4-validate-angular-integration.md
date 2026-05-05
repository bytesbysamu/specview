Now I have everything I need. Let me write the guide.

# Implementation Guide: Task 4 — Validate Angular Integration

---

## 1. Context

Task 4 proves the Phase 1 OpenAPI contract from the Angular frontend's point of view: sidebar, editor, auto-save, and all four context panels must work against the mock server at port 3102. The only mechanism required is an Angular proxy configuration — a single `proxy.conf.json` file — that routes all `/api` requests through the Angular dev-server to a configurable backend host. To use it, every Angular service must switch from absolute `http://localhost:3100/...` URLs to relative `/api/...` paths. This task also surfaces one structural gap: `references-editor.component.ts` does not exist and is not wired into the app, meaning the fourth context panel cannot be validated through the UI. Building that component is required before this task can be closed.

**Trade-offs considered:**
- `environment.ts` with `fileReplacements`: rejected — requires a full rebuild per environment and leaves `http://localhost:...` in the production artifact; proxy operates at the dev-server level with no build footprint
- `HttpInterceptor` base URL injection: rejected — moves deployment configuration into application code, adds an abstraction layer that persists in production for what is a local-dev routing concern
- `proxy.conf.json` + relative service paths (chosen): one JSON value changes the target; both mock (3102) and real Express/Flask (3100) can run simultaneously; the swap procedure is a single-field edit with no rebuild

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 1. Confirm working tree state
git status
git diff HEAD -- proxy.conf.json angular.json \
  src/app/services/projects.service.ts \
  src/app/services/ai.service.ts \
  src/app/services/builder.service.ts \
  src/app/services/principles.service.ts \
  src/app/services/references.service.ts \
  src/app/services/codebase.service.ts \
  src/app/services/implementation.service.ts \
  src/app/components/live-preview/live-preview.component.ts \
  src/app/components/sidebar/sidebar.component.ts \
  src/app/app.component.ts

# 2. Verify prerequisite tasks are shipped
test -f flask/openapi.yaml   && echo "Task 1: OK" || echo "BLOCKER: openapi.yaml missing — Task 1 must ship first"
test -d flask/dtos           && echo "Task 2: OK" || echo "BLOCKER: flask/dtos missing — Task 2 must ship first"
test -f flask/mock_server.py && echo "Task 3: OK" || echo "BLOCKER: mock_server.py missing — Task 3 must ship first"

# 3. Confirm URL pattern in mock matches Angular services
# Angular services call /api/builder, /api/principles, /api/codebase, /api/references
# (NOT /api/context/builder as the architecture doc describes)
# If mock_server.py uses /api/context/{key}, stop here — coordinate with Task 1/3 to align URL pattern
grep -n "api/builder\|api/context" flask/mock_server.py || echo "CHECK: verify route pattern"

# 4. Baseline test run (expected: 0 tests, no failure)
npm test -- --watch=false
```

**If working tree is dirty on target files**: stash or commit unrelated changes first.

**URL pattern coordination**: Angular services use `/api/builder`, `/api/principles`, `/api/codebase`, `/api/references`. If `mock_server.py` (Task 3) implements `/api/context/{key}` instead, either the mock routes or these services must align before proceeding. The architecture doc says `/api/context/{key}` but the Angular implementation predates that doc — the correct path forward is for the openapi.yaml (Task 1) to define `/api/{key}` routes matching what the frontend already calls. Raise this with the Task 1/3 executor if the mock uses the `/context/` prefix.

**Baseline recorded**: 0 / 0 passing (no spec files exist yet).

---

## 3. Files

### To Create (new)
- `proxy.conf.json` — Angular CLI dev-server proxy; single target value switches mock (3102) vs real backend (3100)
- `src/app/components/references-editor/references-editor.component.ts` — the missing fourth context panel; mirrors `principles-editor.component.ts`, uses `ReferencesService`
- `src/app/services/projects.service.spec.ts` — Angular unit test verifying relative URL paths
- `src/app/services/builder.service.spec.ts` — Angular unit test verifying relative URL path (representative of all four context services)

### To Modify (cite CODEBASE CONTEXT)
- `angular.json:76` — add `"options": {"proxyConfig": "proxy.conf.json"}` to the `serve` section (currently has no `options` block)
- `src/app/services/projects.service.ts:31` — `http://localhost:3100/api/projects` → `/api/projects`
- `src/app/services/ai.service.ts:24` — `http://localhost:3100/api/ai/text` → `/api/ai/text`
- `src/app/services/builder.service.ts:14` — `http://localhost:3100/api/builder` → `/api/builder`
- `src/app/services/principles.service.ts:9` — `http://localhost:3100/api/principles` → `/api/principles`
- `src/app/services/references.service.ts:7` — `http://localhost:3100/api/references` → `/api/references`
- `src/app/services/codebase.service.ts:9–10` — remove `http://localhost:3100` prefix from both `baseUrl` and `scanUrl`
- `src/app/services/implementation.service.ts:32` — `http://localhost:3100` → `''` (paths already start with `/api/`)
- `src/app/components/live-preview/live-preview.component.ts:226` — `http://localhost:3100` → `''` (paths already start with `/api/`)
- `src/app/components/sidebar/sidebar.component.ts:20` — add `'references'` to `SidebarAction` union type; add References button in template after the Codebase button (line ~81)
- `src/app/app.component.ts` — import and wire `ReferencesEditorComponent`; add `showReferences = false` flag; add handler in `onSidebarAction`

### To Leave Alone
- `flask/` entire directory — outputs of Tasks 1, 2, 3; do not modify
- `server.js` — Express backend on 3100; untouched; proxy routes around it during mock validation
- `src/app/app.component.ts:845` — the `'Make sure the backend is running on localhost:3100'` string is user-facing text, not an HTTP endpoint reference; leave as-is

---

## 4. Implementation Steps

### Step 1: Create proxy.conf.json

**Action**: Create the proxy configuration file pointing at the mock server

**File**: `proxy.conf.json` (new, workspace root)

**Pattern**:
```json
{
  "/api": {
    "target": "http://localhost:3102",
    "secure": false,
    "changeOrigin": true,
    "logLevel": "warn"
  }
}
```

**Verify**: `cat proxy.conf.json` — file exists with target `3102`

---

### Step 2: Register proxy in angular.json

**Action**: Add `options.proxyConfig` to the `serve` architect target so `ng serve` picks up the proxy

**File**: `angular.json:76–87`

Current state:
```json
"serve": {
  "builder": "@angular-devkit/build-angular:dev-server",
  "configurations": {
    "production": { "buildTarget": "spec-doc:build:production" },
    "development": { "buildTarget": "spec-doc:build:development" }
  },
  "defaultConfiguration": "development"
}
```

Target state:
```json
"serve": {
  "builder": "@angular-devkit/build-angular:dev-server",
  "options": {
    "proxyConfig": "proxy.conf.json"
  },
  "configurations": {
    "production": { "buildTarget": "spec-doc:build:production" },
    "development": { "buildTarget": "spec-doc:build:development" }
  },
  "defaultConfiguration": "development"
}
```

**Verify**: `grep -A3 '"options"' angular.json` — shows `proxyConfig`

---

### Step 3: Remove hardcoded host from all services

**Action**: Strip `http://localhost:3100` from the `baseUrl` / `apiBase` / `scanUrl` fields in eight files. All paths already start with `/api/`, so removing the host prefix produces valid relative URLs that the proxy intercepts.

**Files and exact changes**:

`src/app/services/projects.service.ts:31`
```typescript
// before
private baseUrl = 'http://localhost:3100/api/projects';
// after
private baseUrl = '/api/projects';
```

`src/app/services/ai.service.ts:24`
```typescript
// before
private baseUrl = 'http://localhost:3100/api/ai/text';
// after
private baseUrl = '/api/ai/text';
```

`src/app/services/builder.service.ts:14`
```typescript
// before
private baseUrl = 'http://localhost:3100/api/builder';
// after
private baseUrl = '/api/builder';
```

`src/app/services/principles.service.ts:9`
```typescript
// before
private baseUrl = 'http://localhost:3100/api/principles';
// after
private baseUrl = '/api/principles';
```

`src/app/services/references.service.ts:7`
```typescript
// before
private baseUrl = 'http://localhost:3100/api/references';
// after
private baseUrl = '/api/references';
```

`src/app/services/codebase.service.ts:9–10`
```typescript
// before
private baseUrl = 'http://localhost:3100/api/codebase';
private scanUrl = 'http://localhost:3100/api/ai/text/scan';
// after
private baseUrl = '/api/codebase';
private scanUrl = '/api/ai/text/scan';
```

`src/app/services/implementation.service.ts:32`
```typescript
// before
private baseUrl = 'http://localhost:3100';
// after
private baseUrl = '';
```

`src/app/components/live-preview/live-preview.component.ts:226`
```typescript
// before
private apiBase = 'http://localhost:3100';
// after
private apiBase = '';
```

**Verify**:
```bash
grep -rn 'localhost:3100' src/app/services/ src/app/components/
# Expected: one match only — app.component.ts:845 error message string (acceptable)
```

---

### Step 4: Create references-editor component

**Action**: Create the missing fourth context panel, porting from `src/app/components/principles-editor/principles-editor.component.ts` (the pattern is identical; only service injection and display strings differ)

**File**: `src/app/components/references-editor/references-editor.component.ts` (new)

**Pattern** (complete implementation):
```typescript
import { Component, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ReferencesService } from '../../services/references.service';

@Component({
  selector: 'app-references-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="overlay" (click)="onOverlayClick($event)">
      <div class="modal">
        <div class="modal-header">
          <h2>References</h2>
          <span class="subtitle">Links and resources injected into generation prompts</span>
          <button class="close-btn" (click)="close.emit()">&times;</button>
        </div>
        <div class="modal-body">
          <div class="info-bar" *ngIf="!loading">
            <span class="status" [class.active]="content.length > 0">
              {{ content.length > 0 ? 'Active' : 'Empty' }}
            </span>
            <span class="char-count">{{ content.length }} chars</span>
          </div>
          <textarea
            [(ngModel)]="content"
            placeholder="# References&#10;&#10;Docs, links, and resources..."
            rows="24"
            [disabled]="loading"
            (input)="dirty = true">
          </textarea>
          <div class="actions">
            <button class="save-btn" [disabled]="!dirty || saving" (click)="save()">
              {{ saving ? 'Saving...' : 'Save References' }}
            </button>
            <span class="saved-msg" *ngIf="justSaved">Saved</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
    .modal { background: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 12px; width: 90%; max-width: 800px; max-height: 90vh; overflow: hidden; display: flex; flex-direction: column; }
    .modal-header { display: flex; align-items: center; gap: 12px; padding: 20px 24px; border-bottom: 1px solid #3c3c3c; }
    .modal-header h2 { margin: 0; font-size: 18px; color: #fff; }
    .subtitle { font-size: 12px; color: #666; flex: 1; }
    .close-btn { background: none; border: none; font-size: 24px; color: #888; cursor: pointer; padding: 0; line-height: 1; }
    .close-btn:hover { color: #fff; }
    .modal-body { padding: 24px; overflow-y: auto; }
    .info-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .status { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: #3c3c3c; color: #888; }
    .status.active { background: #1a3a1a; color: #4caf50; }
    .char-count { font-size: 11px; color: #666; }
    textarea { width: 100%; padding: 16px; background: #2d2d2d; border: 1px solid #3c3c3c; border-radius: 6px; color: #d4d4d4; font-size: 13px; font-family: 'SF Mono', 'Fira Code', monospace; line-height: 1.6; box-sizing: border-box; resize: vertical; min-height: 400px; }
    textarea:focus { outline: none; border-color: #6eb4ff; }
    .actions { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
    .save-btn { padding: 10px 24px; background: #238636; border: none; border-radius: 6px; color: #fff; font-size: 14px; font-weight: 500; cursor: pointer; }
    .save-btn:hover:not(:disabled) { background: #2ea043; }
    .save-btn:disabled { background: #3c3c3c; color: #666; cursor: not-allowed; }
    .saved-msg { font-size: 13px; color: #4caf50; }
  `]
})
export class ReferencesEditorComponent implements OnInit {
  @Output() close = new EventEmitter<void>();
  content = '';
  loading = true;
  saving = false;
  dirty = false;
  justSaved = false;

  constructor(private referencesService: ReferencesService) {}

  ngOnInit(): void {
    this.referencesService.get().subscribe({
      next: (r) => { this.content = r.content; this.loading = false; },
      error: () => { this.content = ''; this.loading = false; }
    });
  }

  save(): void {
    this.saving = true;
    this.referencesService.save(this.content).subscribe({
      next: () => {
        this.saving = false;
        this.dirty = false;
        this.justSaved = true;
        setTimeout(() => this.justSaved = false, 2000);
      },
      error: () => { this.saving = false; alert('Failed to save.'); }
    });
  }

  onOverlayClick(event: Event): void {
    if ((event.target as HTMLElement).classList.contains('overlay')) this.close.emit();
  }
}
```

**Verify**: `test -f src/app/components/references-editor/references-editor.component.ts && echo OK`

---

### Step 5: Add References action to sidebar

**Action**: Extend `SidebarAction` union type and add the References button after the Codebase button

**File**: `src/app/components/sidebar/sidebar.component.ts`

Line 20 — extend the type:
```typescript
// before
export type SidebarAction = 'implement' | 'copy' | 'new-project' | 'delete-project' | 'builder-profile' | 'principles' | 'codebase';
// after
export type SidebarAction = 'implement' | 'copy' | 'new-project' | 'delete-project' | 'builder-profile' | 'principles' | 'codebase' | 'references';
```

After the Codebase button (~line 81), add:
```html
<button class="action-btn references" (click)="onAction('references')">
  🔗 References
</button>
```

**Verify**: `grep "'references'" src/app/components/sidebar/sidebar.component.ts` — two matches (type and click handler)

---

### Step 6: Wire references panel in app.component.ts

**Action**: Import the component, add it to the `imports` array, add the template block, the `showReferences` flag, and the sidebar action handler

**File**: `src/app/app.component.ts`

Add import (after line 13, alongside the other context panel imports):
```typescript
import { ReferencesEditorComponent } from './components/references-editor/references-editor.component';
```

Add to `imports` array (alongside `CodebaseEditorComponent`):
```typescript
imports: [..., CodebaseEditorComponent, ReferencesEditorComponent],
```

Add template block (after the `app-codebase-editor` block, ~line 55):
```html
<app-references-editor
  *ngIf="showReferences"
  (close)="showReferences = false">
</app-references-editor>
```

Add flag (~line 258, after `showCodebase = false`):
```typescript
showReferences = false;
```

Add handler in `onSidebarAction` (~line 487, after the codebase case):
```typescript
} else if (action === 'references') {
  this.showReferences = true;
}
```

**Verify**: `ng build 2>&1 | grep error` — zero TypeScript errors

---

### Step 7: Start mock server and run validation

**Action**: Start the mock (Task 3), start Angular dev-server, manually exercise all five validation checkpoints

**Commands**:
```bash
# Terminal 1 — mock server
cd flask && python mock_server.py
# Expect: "Running on http://127.0.0.1:3102"

# Terminal 2 — Angular with proxy
npm start
# Expect: "Local:   http://localhost:4201/" and "[HPM] Proxy created: /api → http://localhost:3102"
```

**Validation checklist** (open http://localhost:4201):

| # | Checkpoint | Pass condition |
|---|-----------|----------------|
| 1 | Sidebar loads pre-seeded projects | At least 2 projects visible in sidebar within 2s of page load |
| 2 | File opens in editor | Click a spec file from a pre-seeded project; Monaco editor shows content |
| 3 | Auto-save writes back | Edit a character, wait 2s; check mock server logs for a `PUT /api/projects/{id}/files/{filename}` 200 response |
| 4a | Builder panel reads | Click Builder Profile; modal shows pre-seeded content, not empty |
| 4b | Principles panel reads | Click Principles; modal shows pre-seeded content |
| 4c | Codebase panel reads | Click Codebase; modal shows pre-seeded content |
| 4d | References panel reads | Click References; modal shows pre-seeded content |
| 5 | Context panel writes | In any context modal, edit text, click Save; expect "Saved" confirmation and a `PUT /api/{key}` 200 in mock logs |

**Verify proxy routing** (run while both servers are up):
```bash
curl http://localhost:4201/api/projects | python3 -m json.tool
# Must return the mock's pre-seeded project list (not Express on 3100)
curl http://localhost:4201/health
# Must return mock health response
```

---

### Step 8: Document the swap procedure

This is the deliverable the epic requires for Tasks 2 and 3 to reuse. No code change — just record it in the commit message and this guide.

**Swap procedure**: To redirect Angular from the mock (3102) to the real Flask backend (3100), change one value in `proxy.conf.json`:

```json
{
  "/api": {
    "target": "http://localhost:3100",   ← change this line only
    "secure": false,
    "changeOrigin": true,
    "logLevel": "warn"
  }
}
```

Then restart `npm start`. No rebuild, no source change. The same procedure applies when Tasks 2 and 3 wire up the real Flask routes: change `3102` to `3100` in `proxy.conf.json`, restart, re-run the validation checklist.

---

## 5. Tests

No existing Angular spec files. Framework is Karma + Jasmine (Angular CLI default; confirmed by `angular.json:92` `"builder": "@angular-devkit/build-angular:karma"`).

**`src/app/services/projects.service.spec.ts`** (new):
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ProjectsService } from './projects.service';

describe('ProjectsService', () => {
  let service: ProjectsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ProjectsService]
    });
    service = TestBed.inject(ProjectsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('list() calls relative /api/projects GET', () => {
    service.list().subscribe(projects => {
      expect(projects.length).toBe(1);
    });
    const req = httpMock.expectOne('/api/projects');
    expect(req.request.method).toBe('GET');
    expect(req.request.url).not.toContain('localhost');
    req.flush([{ id: 'p1', name: 'Test', createdAt: '2026-01-01', specs: [] }]);
  });

  it('get() calls relative /api/projects/{id} GET', () => {
    service.get('abc').subscribe(p => {
      expect(p.id).toBe('abc');
    });
    const req = httpMock.expectOne('/api/projects/abc');
    expect(req.request.method).toBe('GET');
    expect(req.request.url).not.toContain('localhost');
    req.flush({ id: 'abc', name: 'Test', createdAt: '2026-01-01', specs: [] });
  });

  it('updateFile() calls relative PUT with content', () => {
    service.updateFile('p1', 'epic.md', '# Epic').subscribe(r => {
      expect(r.success).toBeTrue();
    });
    const req = httpMock.expectOne('/api/projects/p1/files/epic.md');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ content: '# Epic' });
    expect(req.request.url).not.toContain('localhost');
    req.flush({ success: true });
  });

  it('delete() calls relative DELETE', () => {
    service.delete('p1').subscribe(r => {
      expect(r.success).toBeTrue();
    });
    const req = httpMock.expectOne('/api/projects/p1');
    expect(req.request.method).toBe('DELETE');
    req.flush({ success: true });
  });
});
```

**`src/app/services/builder.service.spec.ts`** (new, representative of all four context services):
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { BuilderService } from './builder.service';

describe('BuilderService', () => {
  let service: BuilderService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [BuilderService]
    });
    service = TestBed.inject(BuilderService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('get() calls relative /api/builder GET', () => {
    service.get().subscribe(profile => {
      expect(profile.content).toBe('# Profile');
      expect(profile.exists).toBeTrue();
    });
    const req = httpMock.expectOne('/api/builder');
    expect(req.request.method).toBe('GET');
    expect(req.request.url).not.toContain('localhost');
    req.flush({ content: '# Profile', exists: true });
  });

  it('save() calls relative /api/builder PUT with content body', () => {
    service.save('# My Profile').subscribe(r => {
      expect(r.success).toBeTrue();
    });
    const req = httpMock.expectOne('/api/builder');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ content: '# My Profile' });
    expect(req.request.url).not.toContain('localhost');
    req.flush({ success: true });
  });
});
```

---

## 6. Commit Plan

1. `feat(proxy): add proxy.conf.json and register in angular.json`
   — `proxy.conf.json`, `angular.json`: establishes the env-var-equivalent base URL mechanism; target is 3102 (mock)

2. `refactor(services): replace hardcoded localhost:3100 with relative paths`
   — `src/app/services/*.service.ts` (6 files), `src/app/services/implementation.service.ts`, `src/app/components/live-preview/live-preview.component.ts`: removes all absolute host references from HTTP calls; no behaviour change when proxy target matches the previous hardcoded value

3. `feat(ui): add references-editor panel and sidebar wiring`
   — `src/app/components/references-editor/references-editor.component.ts` (new), `src/app/components/sidebar/sidebar.component.ts`, `src/app/app.component.ts`: closes the gap that prevented validation of the fourth context panel

4. `test(services): add Karma/Jasmine specs asserting relative service URLs`
   — `src/app/services/projects.service.spec.ts` (new), `src/app/services/builder.service.spec.ts` (new)

**Deviation logging**: if any step deviates from this guide (e.g., URL pattern mismatch with mock requires a service path change), prefix the relevant commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Structural: no localhost:3100 in service/component HTTP calls
grep -rn 'localhost:3100' src/app/services/ src/app/components/
# Expected: exactly one match — app.component.ts error message string (not an HTTP call)

# Unit tests
npm test -- --watch=false
# Expected: 0 → 6 passing (4 ProjectsService + 2 BuilderService). Zero pre-existing tests broken.

# Build check
ng build 2>&1 | grep -i 'error'
# Expected: no errors

# Integration (requires mock running on 3102)
python flask/mock_server.py &
MOCK_PID=$!
curl -s http://localhost:4201/api/projects | python3 -m json.tool
# Expected: JSON array with pre-seeded projects
curl -s http://localhost:4201/api/builder | python3 -m json.tool
# Expected: { "content": "...", "exists": true }
kill $MOCK_PID
```

**Expected delta**: 0 → 6 passing unit tests. Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit above is independently revertible:
  ```bash
  git revert <sha>   # safe non-destructive revert
  ```
- **Per-branch**: if verification fails and the branch state is unrecoverable:
  ```bash
  git reset --hard <pre-task-sha>   # [REQUIRES APPROVAL] — destroys uncommitted changes
  ```
  Alternatively, delete the feature branch and re-cut from the pre-task SHA.

- **Proxy target rollback** (no git operation needed): if validation fails because the mock is not ready, restore the target to 3100 in `proxy.conf.json` to resume pointing at the Express backend. No commit, no rebuild.

---

## 9. Deviations Allowed

- **Mock URL pattern is `/api/context/{key}`, not `/api/{key}`**: do NOT silently update Angular services to match. Stop, log a deviation in the commit, and raise with the Task 1/3 executor. The correct fix is to align the openapi.yaml — changing Angular service URLs would introduce a second inconsistency.
- **`angular.json` serve `options` block already exists**: add `proxyConfig` to the existing object rather than creating a new one; log the deviation.
- **Checkpoint 4 panel never shows content (empty state)**: acceptable if the mock pre-seeds empty strings; unacceptable if the endpoint returns 404 — in the latter case the mock route is missing and Task 3 must be reopened.
- **Test framework is not Karma/Jasmine**: match whatever framework exists; translate the test bodies silently and note the translation in the commit body.
- **Step N reveals a simplification for Step N+1**: take it, log it in the commit body.

---

## 10. Out of Scope

This task closes with a functioning proxy mechanism, six passing unit tests, all four context panels reachable in the UI, and a manually verified checklist against the mock. The following work is explicitly deferred and must not be absorbed by this task's executor.

- **Codebase scan validation** — `CodebaseService.scan()` calls `POST /api/ai/text/scan`, which the mock does not implement (AI endpoints are Phase 2). The scan button failing during validation is expected and acceptable; validating the scan is out of scope until Phase 2 routes exist.
- **`implementation.service.ts` and `live-preview.component.ts` functional validation** — relative URL changes are applied in Step 3, but these services call SSE and container endpoints that the mock does not serve. Confirming those features still work against the real Express backend (port 3100) is deferred to a dedicated test run post-merge.
- **Production proxy configuration** — `proxy.conf.json` only applies during `ng serve`. Production builds use the absolute URL of the deployed Flask backend configured elsewhere (e.g., nginx, environment variable at build time). Wiring that is deferred to the deployment task.
- **CI proxy integration** — running `ng test` or `ng e2e` against the mock in CI requires a mock startup step. That is deferred until CI test coverage is explicitly scoped.
- **Specs for all eight service files** — the two spec files written here cover the pattern. Writing specs for every service is deferred; the grep structural check fills the gap for now.
- **`references-editor` button styling** — the button added to the sidebar in Step 5 has no SCSS rule for `.references`. Styling it to match the other context buttons is a cosmetic follow-up, not a validation requirement.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale and URL pattern decision
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Update task status to `done` after all five validation checkpoints pass