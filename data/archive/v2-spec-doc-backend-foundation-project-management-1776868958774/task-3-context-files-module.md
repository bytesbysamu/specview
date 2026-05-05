I have all the context needed. Here's the implementation guide:

# Task 3: Context Files Module

**Epic**: Spec Doc
**Estimated effort**: 1 day (~150 lines server, ~80 lines services, ~80 lines tests)
**Dependencies**: None
**Parallel With**: Tasks 1, 2 (editor and AI operations)
**Blocks**: Task 4+ (context injection into generate-spec, implementation-guide prompts)

---

## 1. Context

The context files module provides 8 REST endpoints (GET/PUT for builder, principles, codebase, references) that read and write flat markdown files from the Spec Doc project root. These files are user-edited profiles — a builder profile, architecture principles, codebase summary, and cross-project reference code — that downstream AI operations inject into generation prompts. Unlike the manifest-based context loader used in Bubls (which routes prompt templates through `manifest.json`), these endpoints use direct file I/O: each maps to a single `.md` file at `{WORKSPACE}/builder.md`, `principles.md`, `codebase.md`, `references.md`. The frontend Angular services mirror the same GET/PUT shape, and modal editor components let users view and edit each file in the browser.

**Trade-offs considered**:
- **Database storage vs flat file** — rejected DB because these files are single-user, version-controlled by git, and need no indexing or relational queries. Flat files match the project's existing pattern of persisting project specs to disk.
- **Unified `/api/context/:type` parameterized route vs 4 separate route groups** — rejected unified route because each context file has a different helper function used by other parts of the server (e.g., `getBuilderProfile()` is called by `aiAdapter.generate()`, `getArchPrinciples()` by `generate-spec`). Named routes keep the wiring explicit.
- **Separate Express route groups with per-route `express.json()` middleware** — chosen because the context file routes are registered before the global `app.use(express.json())` call at line 470 of `server.js`, so each route group needs its own body parser. This avoids reordering middleware for the entire server.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                    # Flag any unrelated M/?? entries
git diff HEAD -- server.js                    # Confirm target file is clean
npm run test:server                           # Record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: ~81 / ~81 passing (`server.test.js`).

---

## 3. Files

### To Create (new)
- `src/app/services/builder.service.ts` — Angular service wrapping GET/PUT `/api/builder`
- `src/app/services/principles.service.ts` — Angular service wrapping GET/PUT `/api/principles`
- `src/app/services/codebase.service.ts` — Angular service wrapping GET/PUT `/api/codebase` + POST `/api/ai/text/scan`
- `src/app/services/references.service.ts` — Angular service wrapping GET/PUT `/api/references`

### To Modify (cite CODEBASE CONTEXT)
- `server.js` — add 8 endpoints (4 GET + 4 PUT), 4 file-path constants, 4 reader helper functions. Current state: Express server with projects CRUD + AI endpoints. Target state: adds context file routes between the AI adapter section and `app.use(cors())`

### To Leave Alone
- `src/app/components/new-project/new-project.component.ts` — bootstrap prompt component; consumes context services but is wired in a later task
- `src/app/services/implementation-guide.service.ts` — uses `getBuilderBlock()` / `getCodebaseBlock()` / `getReferencesBlock()` but those are wired in the implementation-guide task, not here
- `scripts/context-loader.mjs` — Node-side context block formatters; reads the same `.md` files but from the CLI scripts, not from the Express server

---

## 4. Implementation Steps

### Step 1: Add builder profile endpoints to server.js

**Action**: After the AI Adapter section (~line 318) and before `app.use(cors())` (~line 469), add the builder file constant, reader helper, `express.json()` middleware, GET and PUT routes.

**File**: `server.js`

**Pattern**:
```javascript
const BUILDER_FILE = path.join(__dirname, 'builder.md');

function getBuilderProfile() {
  try {
    if (fs.existsSync(BUILDER_FILE)) {
      return fs.readFileSync(BUILDER_FILE, 'utf-8');
    }
  } catch (err) {
    console.error('Error reading builder profile:', err);
  }
  return '';
}

app.use('/api/builder', express.json());

app.get('/api/builder', (req, res) => {
  const content = getBuilderProfile();
  res.json({ content, exists: content.length > 0 });
});

app.put('/api/builder', (req, res) => {
  try {
    const { content } = req.body;
    if (typeof content !== 'string') {
      return res.status(400).json({ error: 'content must be a string' });
    }
    fs.writeFileSync(BUILDER_FILE, content);
    console.log(`[Builder] Updated (${content.length} chars)`);
    res.json({ success: true });
  } catch (err) {
    console.error('Error saving builder profile:', err);
    res.status(500).json({ error: 'Failed to save builder profile' });
  }
});
```

**Verify**: `curl http://localhost:3100/api/builder` — expect `{"content":"...","exists":true|false}`

### Step 2: Add principles endpoints to server.js

**Action**: Same pattern as Step 1, with `PRINCIPLES_FILE = path.join(__dirname, 'principles.md')` and `getArchPrinciples()` helper.

**File**: `server.js`

**Pattern**:
```javascript
const PRINCIPLES_FILE = path.join(__dirname, 'principles.md');

function getArchPrinciples() {
  try {
    if (fs.existsSync(PRINCIPLES_FILE)) {
      return fs.readFileSync(PRINCIPLES_FILE, 'utf-8');
    }
  } catch (err) {
    console.error('Error reading principles:', err);
  }
  return '';
}

app.use('/api/principles', express.json());

app.get('/api/principles', (req, res) => {
  const content = getArchPrinciples();
  res.json({ content, exists: content.length > 0 });
});

app.put('/api/principles', (req, res) => {
  // same shape: validate string, writeFileSync, return { success: true }
});
```

**Verify**: `curl http://localhost:3100/api/principles` — expect `{"content":"...","exists":...}`

### Step 3: Add codebase endpoints to server.js

**Action**: Same pattern with `CODEBASE_FILE = path.join(__dirname, 'codebase.md')` and `getCodebase()` helper. Condensed style is fine for this and references since the pattern is identical.

**File**: `server.js`

**Pattern**:
```javascript
const CODEBASE_FILE = path.join(__dirname, 'codebase.md');

function getCodebase() {
  try {
    if (fs.existsSync(CODEBASE_FILE)) return fs.readFileSync(CODEBASE_FILE, 'utf-8');
  } catch (err) { console.error('Error reading codebase:', err); }
  return '';
}

app.use('/api/codebase', express.json());
app.get('/api/codebase', (req, res) => { /* same shape */ });
app.put('/api/codebase', (req, res) => { /* same shape */ });
```

**Verify**: `curl -X PUT http://localhost:3100/api/codebase -H 'Content-Type: application/json' -d '{"content":"# Test"}' && curl http://localhost:3100/api/codebase` — expect `{"success":true}` then `{"content":"# Test","exists":true}`

### Step 4: Add references endpoints to server.js

**Action**: Identical pattern with `REFERENCES_FILE = path.join(__dirname, 'references.md')` and `getReferences()` helper.

**File**: `server.js`

**Pattern**:
```javascript
const REFERENCES_FILE = path.join(__dirname, 'references.md');

function getReferences() {
  try {
    if (fs.existsSync(REFERENCES_FILE)) return fs.readFileSync(REFERENCES_FILE, 'utf-8');
  } catch (err) { console.error('Error reading references:', err); }
  return '';
}

app.use('/api/references', express.json());
app.get('/api/references', (req, res) => { /* same shape */ });
app.put('/api/references', (req, res) => { /* same shape */ });
```

**Verify**: `curl http://localhost:3100/api/references` — expect `{"content":"","exists":false}` (empty on first run)

### Step 5: Create Angular BuilderService

**Action**: Create a minimal Angular service that wraps the GET/PUT `/api/builder` endpoints.

**File**: `src/app/services/builder.service.ts` (new)

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class BuilderService {
  private baseUrl = 'http://localhost:3100/api/builder';
  constructor(private http: HttpClient) {}

  get(): Observable<{ content: string; exists: boolean }> {
    return this.http.get<{ content: string; exists: boolean }>(this.baseUrl);
  }

  save(content: string): Observable<{ success: boolean }> {
    return this.http.put<{ success: boolean }>(this.baseUrl, { content });
  }
}
```

**Verify**: `ng build --configuration development` — no compilation errors

### Step 6: Create Angular PrinciplesService, CodebaseService, ReferencesService

**Action**: Create three more services following the identical shape as BuilderService, each pointing to their respective API base URL. `CodebaseService` additionally exposes a `scan(workspacePath)` method that calls POST `/api/ai/text/scan`.

**Files**: `src/app/services/principles.service.ts`, `src/app/services/codebase.service.ts`, `src/app/services/references.service.ts` (all new)

**Pattern** (CodebaseService — the one with the extra method):
```typescript
@Injectable({ providedIn: 'root' })
export class CodebaseService {
  private baseUrl = 'http://localhost:3100/api/codebase';
  private scanUrl = 'http://localhost:3100/api/ai/text/scan';
  constructor(private http: HttpClient) {}

  get(): Observable<{ content: string; exists: boolean }> { /* same */ }
  save(content: string): Observable<{ success: boolean }> { /* same */ }

  scan(workspacePath: string): Observable<{ content: string; latencyMs: number }> {
    return this.http.post<{ content: string; latencyMs: number }>(this.scanUrl, { workspacePath });
  }
}
```

**Verify**: `ng build --configuration development` — no compilation errors for all four services

---

## 5. Tests

Framework: `node:test` + `node:assert/strict` (matching `server.test.js`).

### Server unit tests (add to `server.test.js`)

```javascript
describe('Builder Profile', () => {
  it('server has GET /api/builder endpoint', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.get('/api/builder'"), 'should have GET /api/builder');
  });

  it('server has PUT /api/builder endpoint', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.put('/api/builder'"), 'should have PUT /api/builder');
  });
});

describe('Codebase Context', () => {
  it('server has GET /api/codebase', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.get('/api/codebase'"), 'should have GET /api/codebase');
  });

  it('server has PUT /api/codebase', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.put('/api/codebase'"), 'should have PUT /api/codebase');
  });

  it('codebase.md persistence wired to project root', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(
      server.includes("CODEBASE_FILE = path.join(__dirname, 'codebase.md')"),
      'CODEBASE_FILE should resolve to project-root/codebase.md'
    );
    assert.ok(server.includes('function getCodebase()'), 'getCodebase helper should exist');
  });
});

describe('References Context', () => {
  it('server has GET /api/references', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.get('/api/references'"), 'should have GET /api/references');
  });

  it('server has PUT /api/references', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(server.includes("app.put('/api/references'"), 'should have PUT /api/references');
  });

  it('references.md persistence wired to project root', () => {
    const server = readFile(SERVER_PATH);
    assert.ok(
      server.includes("REFERENCES_FILE = path.join(__dirname, 'references.md')"),
      'REFERENCES_FILE should resolve to project-root/references.md'
    );
    assert.ok(server.includes('function getReferences()'), 'getReferences helper should exist');
  });
});
```

### Integration tests (add to `server.integration.test.js`)

Requires the server running with `AI_PROVIDER=mock`.

```javascript
describe('Builder Profile CRUD', () => {
  let original;

  before(async () => {
    original = (await get('/api/builder')).json.content;
  });

  after(async () => {
    await put('/api/builder', { content: original });
  });

  it('GET returns current profile', async () => {
    const res = await get('/api/builder');
    assert.equal(res.status, 200);
    assert.ok('content' in res.json);
    assert.ok('exists' in res.json);
  });

  it('PUT saves and persists', async () => {
    const content = '# Test Builder\n## Stack\n- Node: 20';
    const res = await put('/api/builder', { content });
    assert.equal(res.status, 200);
    assert.ok(res.json.success);
    const verify = await get('/api/builder');
    assert.equal(verify.json.content, content);
  });

  it('PUT rejects non-string', async () => {
    const res = await put('/api/builder', { content: 42 });
    assert.equal(res.status, 400);
  });

  it('PUT handles empty string', async () => {
    await put('/api/builder', { content: '' });
    const verify = await get('/api/builder');
    assert.equal(verify.json.content, '');
    assert.equal(verify.json.exists, false);
  });
});
```

Repeat the same CRUD pattern for `/api/principles`, `/api/codebase`, `/api/references` — save/restore original in before/after, verify GET shape, PUT roundtrip, PUT reject non-string, PUT empty string.

---

## 6. Commit Plan

1. `feat(server): add context file endpoints (builder, principles, codebase, references)` — `server.js`: 4 file constants, 4 reader helpers, 8 routes (GET+PUT each)
2. `feat(frontend): add context file Angular services` — `src/app/services/builder.service.ts`, `principles.service.ts`, `codebase.service.ts`, `references.service.ts`
3. `test(server): add context file endpoint tests` — `server.test.js`, `server.integration.test.js`: structural + integration tests for all 8 endpoints

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npm run test:server                    # structural tests
npm run test:integration               # integration tests (needs AI_PROVIDER=mock server)
```

**Expected delta**: ~81 → ~91 passing (server.test.js gains ~10 assertions across builder, codebase, references sections). Integration tests gain ~16 (4 CRUD tests x 4 endpoints). Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag it, do not invent.
- **Test framework mismatch** → match the repo's convention (`node:test` + `node:assert/strict`); translate silently but note in commit body.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.
- **`express.json()` ordering** — if global middleware order changes, the per-route `app.use('/api/builder', express.json())` calls may become redundant. Remove them silently if they are, note in commit.

---

## 10. Out of Scope

This task covers only the 8 GET/PUT endpoints and their Angular service wrappers. It does NOT cover the UI components that consume these services (editor modals), the injection of context into AI prompts (that's the generate-spec and implementation-guide tasks), or the filesystem walker/scan endpoint (that's the codebase-scan task).

- **Builder profile modal (`BuilderProfileComponent`)** — deferred to the UI wiring task; the service is enough for other services to consume
- **Principles editor modal (`PrinciplesEditorComponent`)** — same; deferred to UI wiring
- **Codebase editor with scan button (`CodebaseEditorComponent`)** — deferred; `scan()` method on `CodebaseService` is included here for API completeness but the UI is separate
- **References editor modal** — no dedicated editor component exists yet; deferred until a UI task creates one
- **File history/versioning** — explicitly excluded by the epic; git provides versioning
- **Validation beyond confirming the write succeeded** — no schema validation on markdown content; the endpoints trust the client
- **`manifest.json` indirection** — the epic identified this as a separate concern (prompt templates vs user context files)
- **Sidebar wiring** — adding `'builder-profile'`, `'principles'`, `'codebase'` actions to the sidebar and app component routing belongs to the UI wiring task

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) -- Design rationale
- [Epic](./epic.md) -- Task scope
- [Timeline](./timeline.md) -- Status tracking (update after done)