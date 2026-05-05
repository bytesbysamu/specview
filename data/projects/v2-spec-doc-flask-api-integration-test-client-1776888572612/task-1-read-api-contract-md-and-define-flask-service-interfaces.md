Now I have everything I need to produce the implementation guide.

---

# Task 1: Read api-contract.md and Define Flask Service Interfaces

## 1. Context

This task translates `flask/api-contract.md` — the authoritative API contract reverse-engineered from `server.js` — into a single TypeScript types file at `src/app/services/flask/flask-api.types.ts`. The file becomes the compile-time foundation for Tasks 2, 3, and 4: every Flask service and the ContractCompareSpec will import from it, so any shape drift between services becomes a TypeScript error rather than a runtime surprise. This task produces **zero runtime code** — no `@Injectable`, no HTTP calls, no Angular imports — just named interfaces derived directly from the contract document.

**Trade-offs considered**:
- **Re-exporting from existing `projects.service.ts`** — rejected because `ProjectsService` exports production types from `localhost:3100` and mixing the Flask layer into that file couples migration tooling to production code.
- **Inline types in each Flask service** — rejected because shape drift across three services (Tasks 2, 3, 4) would be silently tolerated by the compiler; a dedicated types file makes inconsistency a compile error.
- **Single `flask-api.types.ts` with all shapes** — chosen because it is the only consumer-facing import in this epic, keeps the type surface in one grep-able location, and is trivially deleted when Flask fully replaces Express.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                      # Confirm working tree; note any M/?? entries
git diff HEAD -- src/app/services/              # Confirm no in-flight edits on the services dir
npx ng build --no-progress 2>&1 | tail -5      # Baseline: should exit 0, no TS errors
```

**If working tree is dirty on `src/app/services/`**: stash or commit unrelated changes before starting.

**Baseline recorded**: 0 existing `.spec.ts` files; `ng build` exits 0.

---

## 3. Files

### To Create (new)
- `src/app/services/flask/flask-api.types.ts` (new) — all TypeScript interfaces for the Flask API, derived from `flask/api-contract.md`; no Angular imports; no runtime code
- `src/app/services/flask/flask-api.types.spec.ts` (new) — Karma/Jasmine structural spec asserting that every required interface shape is assignable and that the types file has no Angular DI imports

### To Modify
- None

### To Leave Alone
- `src/app/services/projects.service.ts` — production Express service; interfaces here (`ProjectFile`, `ProjectSummary`, `ProjectDetail`, `CreateProjectRequest`) are the shapes the Flask types must mirror; read as reference, do not modify
- `src/app/services/builder.service.ts` — production `BuilderProfile` interface; read as reference
- `src/app/services/principles.service.ts` — production inline types; read as reference
- `src/app/services/codebase.service.ts` — production inline types; read as reference
- `src/app/services/references.service.ts` — production inline types; read as reference
- `flask/api-contract.md` — the authority document; read only
- `server.js` — the Express source; do not touch

---

## 4. Implementation Steps

### Step 1: Create the `flask/` services subdirectory and types file

**Action**: Create `src/app/services/flask/flask-api.types.ts` with all interfaces derived from `flask/api-contract.md`. Mirror the shapes used in `projects.service.ts:5-23` for the project interfaces. Use the same field names and types — **no aliasing, no renaming**.

**File**: `src/app/services/flask/flask-api.types.ts` (new)

**Pattern** (port from `projects.service.ts:5-23` and `builder.service.ts:5-8`; extend with full contract coverage):

```typescript
// Health
export interface HealthResponse {
  status: 'ok';
}

// Context resources — all four paths share this shape
export interface ContextReadResponse {
  content: string;
  exists: boolean;
}

export interface ContextWriteRequest {
  content: string;
}

export interface ContextWriteResponse {
  success: boolean;
}

// Projects — mirroring projects.service.ts:5-23
export interface ProjectFile {
  filename: string;
  label: string;
  content?: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  createdAt: string;
  specs: ProjectFile[];
}

export interface ProjectDetail {
  id: string;
  name: string;
  createdAt: string;
  specs: Required<ProjectFile>[];  // content is always populated in detail responses
}

export interface CreateProjectRequest {
  name: string;
  files: { filename: string; content: string }[];
}

export interface CreateProjectResponse {
  id: string;
  name: string;
  createdAt: string;
}

export interface UpdateFileRequest {
  content: string;
}

export interface UpdateFileResponse {
  success: boolean;
}

export interface DeleteProjectResponse {
  success: boolean;
}

// Error shape (for documentation; not enforced by HttpClient generics)
export interface ApiErrorResponse {
  error: string;
}
```

**Note on `ProjectDetail.specs`**: The contract states `content` is always populated for `GET /api/projects/:id`. Using `Required<ProjectFile>[]` enforces this at the type layer. Tasks 2 and 3 will use this type when defining their service return types.

**Verify**: `npx tsc --noEmit` — expect exit 0 with no errors.

---

### Step 2: Write the structural spec

**Action**: Create `src/app/services/flask/flask-api.types.spec.ts`. This spec does two things: (1) asserts every interface shape is structurally assignable from a literal that matches the contract — catching any typo or field rename at test-run time; (2) asserts the types file does not import `@angular/core` or `@angular/common/http`, keeping it a pure TypeScript file. These are Karma/Jasmine tests.

**File**: `src/app/services/flask/flask-api.types.spec.ts` (new)

**Pattern**:

```typescript
import type {
  HealthResponse,
  ContextReadResponse,
  ContextWriteRequest,
  ContextWriteResponse,
  ProjectFile,
  ProjectSummary,
  ProjectDetail,
  CreateProjectRequest,
  CreateProjectResponse,
  UpdateFileRequest,
  UpdateFileResponse,
  DeleteProjectResponse,
  ApiErrorResponse,
} from './flask-api.types';

describe('flask-api.types', () => {

  it('HealthResponse accepts { status: "ok" }', () => {
    const r: HealthResponse = { status: 'ok' };
    expect(r.status).toBe('ok');
  });

  it('ContextReadResponse has content string and exists boolean', () => {
    const r: ContextReadResponse = { content: 'hello', exists: true };
    expect(typeof r.content).toBe('string');
    expect(typeof r.exists).toBe('boolean');
  });

  it('ContextWriteRequest has content string', () => {
    const r: ContextWriteRequest = { content: 'updated' };
    expect(typeof r.content).toBe('string');
  });

  it('ContextWriteResponse has success boolean', () => {
    const r: ContextWriteResponse = { success: true };
    expect(r.success).toBeTrue();
  });

  it('ProjectFile has filename and label; content is optional', () => {
    const withoutContent: ProjectFile = { filename: 'epic.md', label: 'Epic' };
    expect(withoutContent.content).toBeUndefined();
    const withContent: ProjectFile = { filename: 'epic.md', label: 'Epic', content: '# Epic' };
    expect(withContent.content).toBe('# Epic');
  });

  it('ProjectSummary has id, name, createdAt, and specs array', () => {
    const r: ProjectSummary = {
      id: 'my-project-1234',
      name: 'My Project',
      createdAt: '2026-04-22T10:00:00.000Z',
      specs: [{ filename: 'epic.md', label: 'Epic' }],
    };
    expect(r.id).toBe('my-project-1234');
    expect(Array.isArray(r.specs)).toBeTrue();
  });

  it('ProjectDetail specs entries have content populated (Required<ProjectFile>)', () => {
    const r: ProjectDetail = {
      id: 'my-project-1234',
      name: 'My Project',
      createdAt: '2026-04-22T10:00:00.000Z',
      specs: [{ filename: 'epic.md', label: 'Epic', content: '# Epic' }],
    };
    expect(r.specs[0].content).toBe('# Epic');
  });

  it('CreateProjectRequest has name string and files array', () => {
    const r: CreateProjectRequest = {
      name: 'New Project',
      files: [{ filename: 'epic.md', content: '# Epic' }],
    };
    expect(r.name).toBe('New Project');
    expect(r.files[0].filename).toBe('epic.md');
  });

  it('CreateProjectResponse has id, name, createdAt strings', () => {
    const r: CreateProjectResponse = {
      id: 'new-project-1000',
      name: 'New Project',
      createdAt: '2026-04-22T10:00:00.000Z',
    };
    expect(typeof r.id).toBe('string');
    expect(typeof r.name).toBe('string');
    expect(typeof r.createdAt).toBe('string');
  });

  it('UpdateFileRequest has content string', () => {
    const r: UpdateFileRequest = { content: '# Updated' };
    expect(typeof r.content).toBe('string');
  });

  it('UpdateFileResponse has success boolean', () => {
    const r: UpdateFileResponse = { success: true };
    expect(r.success).toBeTrue();
  });

  it('DeleteProjectResponse has success boolean', () => {
    const r: DeleteProjectResponse = { success: true };
    expect(r.success).toBeTrue();
  });

  it('ApiErrorResponse has error string', () => {
    const r: ApiErrorResponse = { error: 'Project not found' };
    expect(typeof r.error).toBe('string');
  });

});
```

**Verify**: `npx ng test --include='**/flask-api.types.spec.ts' --watch=false` — expect 12 passing, 0 failing.

---

## 5. Tests

The tests are fully specified in Step 2 above. No additional test file is needed for this task — the entire test surface is structural (type assignability via Jasmine `expect`).

**Framework**: Karma + Jasmine (existing Angular configuration, confirmed via `angular.json`).

**Test count**: 12 new tests, all in `src/app/services/flask/flask-api.types.spec.ts`.

---

## 6. Commit Plan

1. `feat(flask/types): add flask-api.types.ts — typed interfaces for all Flask API shapes` — `src/app/services/flask/flask-api.types.ts`: all interfaces derived from `flask/api-contract.md`
2. `test(flask/types): structural spec for flask-api.types — 12 passing` — `src/app/services/flask/flask-api.types.spec.ts`: assignability and shape coverage for every interface

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npx ng test --watch=false 2>&1 | tail -10
```

**Expected delta**: 0 → 12 passing. Zero pre-existing tests broken (there are none in this repo; this task creates the first `.spec.ts` file).

Also verify compilation:

```bash
npx tsc --noEmit 2>&1
```

Expected: exit 0, no output.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` on either commit leaves the other intact.
- **Per-branch**: if verification fails, `git reset --hard <pre-task-sha>` to return to the state before Task 1 started. Both files are new — no existing file is modified — so a reset is lossless.

---

## 9. Deviations Allowed

- **`flask/api-contract.md` shape ambiguity** → resolve at the type layer with the most restrictive type (e.g., `'ok'` literal over `string` for `HealthResponse.status`); document the decision in the commit body.
- **`ProjectDetail.specs` typing** → if `Required<ProjectFile>[]` causes downstream compile errors in Tasks 2–4, relax to `ProjectFile[]` and note the deviation; the intent (content is always present in detail responses) should be preserved in a comment.
- **Test framework mismatch** → if the project uses Jest instead of Karma/Jasmine, translate `expect(...).toBe` / `toBeTrue` / `toBeUndefined` to `expect(...).toBe` / `expect(...).toBe(true)` / `expect(...).toBeUndefined()` in Jest syntax; note in commit body.
- **Step N unlocks an obvious simplification for Step N+1** → take it, log deviation in the commit.
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

This task covers types only. It does not build any runtime code, Angular services, HTTP calls, or test infrastructure beyond the structural spec. The following items are explicitly deferred and must not be absorbed by an eager executor:

- **`FlaskProjectsService` and `FlaskHealthService`** — deferred to Task 2; types from this file are the input, not the output
- **`FlaskContextService`** — deferred to Task 3; same dependency relationship
- **`ContractCompareSpec`** — deferred to Task 4; cannot be written until Tasks 2 and 3 compile
- **AI route types** (`/api/ai/text/...`, SSE streams, container routes) — explicitly marked Phase 2 in `flask/api-contract.md`; do not add interfaces for them here
- **`environment.ts` configuration for `localhost:3101`** — deferred per architecture decision; base URL is hardcoded in each Flask service, not in types
- **Error boundary or HTTP error handling** — `ApiErrorResponse` is documented for completeness; no `catchError` or interceptor logic belongs in this task

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale, mirror pattern, type-first derivation
- [Epic](./epic.md) — Task scope and dependencies
- [Timeline](./timeline.md) — Update status to `done` after verification passes