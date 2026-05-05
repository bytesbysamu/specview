Now I have everything I need. Let me write the guide.

# Task 1: Unify Context Services

## 1. Context

Four Angular services (`BuilderService`, `PrinciplesService`, `CodebaseService`, `ReferencesService`) and eight Flask routes (`GET`/`PUT` × four keys) are structurally identical — same two-method contract, same DTO shapes, differing only in the path string. This task collapses them: one Angular `ContextService` with a `ContextKey` parameter, one Flask route pair at `GET /api/context/{key}` / `PUT /api/context/{key}`.

The Flask backend already does the right thing internally: `_get_handler(key)` and `_put_handler(key)` are private helpers that accept any key string; the eight public routes just call them with a hardcoded literal. Only the public-facing surface needs to change.

**Route count change:** 21 → 17 (−4 GET + 4 PUT individual routes, +1 GET + 1 PUT parameterised route).

**Key constraint from CLAUDE.md:** `everyOpenapiPath_hasRouteHandler` in `tests/test_ai_rewrite.py` enforces that every `openapi.yaml` path has a Flask route and vice versa. This test **will fail** between editing `openapi.yaml` and adding the new route. Do not run `make test` between those two edits — complete both atomically in Step 3.

---

## 2. Pre-flight

```bash
cd /workspace/api

# Confirm suite is green before touching anything
make test

# Confirm existing route inventory (should show 8 context routes)
python - <<'EOF'
from create_app import create_app
app = create_app()
for r in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if 'builder' in r.rule or 'principles' in r.rule or 'codebase' in r.rule or 'references' in r.rule:
        print(r.rule, sorted(r.methods - {'HEAD','OPTIONS'}))
EOF
# Expected output — 8 lines:
# /api/builder    ['GET']
# /api/builder    ['PUT']
# /api/codebase   ['GET']
# /api/codebase   ['PUT']
# /api/principles ['GET']
# /api/principles ['PUT']
# /api/references ['GET']
# /api/references ['PUT']
```

> Angular pre-flight — run in a second terminal:
> ```bash
> cd /workspace/web
> ng build --configuration development 2>&1 | tail -20
> # Must exit 0 with no TS errors before you start
> ```

---

## 3. Files

### Flask backend — `/workspace/api/`

| File | Action |
|---|---|
| `openapi.yaml` | **Edit** — remove 4 named paths, add `/api/context/{key}` |
| `modules/context/routes.py` | **Edit** — replace 8 individual routes with 2 parameterised |
| `tests/test_context_files.py` | **Edit** — update all route strings + structural assertion |
| `tests/test_contracts.py` | **Edit** — update `test_contextBuilder_matchesOpenApiSchema` |

### Angular frontend — `/workspace/web/src/app/`

| File | Action |
|---|---|
| `services/context.service.ts` | **New** |
| `services/context.service.spec.ts` | **New** |
| `services/builder.service.ts` | **Delete** |
| `services/principles.service.ts` | **Delete** |
| `services/codebase.service.ts` | **Delete** |
| `services/references.service.ts` | **Delete** |
| `services/builder.service.spec.ts` | **Delete** (if exists) |
| `services/principles.service.spec.ts` | **Delete** (if exists) |
| `services/codebase.service.spec.ts` | **Delete** (if exists) |
| `services/references.service.spec.ts` | **Delete** (if exists) |
| `components/builder-profile/builder-profile.component.ts` | **Edit** — swap injection |
| `components/principles-editor/principles-editor.component.ts` | **Edit** — swap injection |
| `components/codebase-editor/codebase-editor.component.ts` | **Edit** — swap injection |
| `components/references-editor/references-editor.component.ts` | **Edit** — swap injection |
| `components/new-project/new-project.component.ts` | **Edit** — injects all 4 services (imports lines 5,7,8,9; ctor lines 465–468; `.get()` calls lines 472, 476, 480, 484). Replace each call with `contextService.get('<key>')`. |

> **Path note:** Angular component paths above are inferred from the exploration report and existing implementation guides. Run `find /workspace/web/src/app/components -name "*.component.ts" | xargs grep -l "BuilderService\|PrinciplesService\|CodebaseService\|ReferencesService"` to get the exact list before editing.

---

## 4. Implementation Steps

### Step 1 — Update `openapi.yaml`

Replace the four named context paths (lines 143–269 in the current file) with a single parameterised path. **Do this and Step 2 atomically — do not run `make test` between them.**

Remove the following block entirely (all four path keys):

```yaml
  /api/builder:
    ...  # (entire get + put block)
  /api/principles:
    ...
  /api/codebase:
    ...
  /api/references:
    ...
```

Insert in its place (after `/api/projects/{id}/files/{filename}`, before `/api/ai/text/rewrite`):

```yaml
  /api/context/{key}:
    parameters:
      - name: key
        in: path
        required: true
        schema:
          type: string
          enum: [builder, principles, codebase, references]
    get:
      summary: Read a context file by key
      operationId: getContext
      responses:
        "200":
          description: Context file content
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ContextResponse"
        "404":
          $ref: "#/components/responses/NotFound"
    put:
      summary: Write a context file by key
      operationId: putContext
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ContextUpdateRequest"
      responses:
        "200":
          description: Context updated
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/SuccessResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "404":
          $ref: "#/components/responses/NotFound"
        "500":
          $ref: "#/components/responses/InternalError"
```

Verify the total path count dropped from 11 to 8:

```bash
python -c "import yaml; s=yaml.safe_load(open('openapi.yaml')); print(len(s['paths']), 'paths')"
# Expected: 8 paths
```

---

### Step 2 — Rewrite `modules/context/routes.py`

Replace the entire file content. The private `_get_handler` / `_put_handler` helpers are unchanged. Only the public route surface changes.

```python
# modules/context/routes.py
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from config import CONTEXT_PATHS
from dtos.models import ContextResponse, ContextUpdateRequest, SuccessResponse
from .service import read_context, write_context

logger = logging.getLogger(__name__)
context_bp = Blueprint("context", __name__)

_VALID_KEYS: frozenset[str] = frozenset(CONTEXT_PATHS.keys())
# {'builder', 'principles', 'codebase', 'references'} — derived from config,
# not hardcoded, so adding a key to CONTEXT_PATHS is the only change needed.


def _get_handler(key: str):
    content = read_context(key)
    return jsonify(ContextResponse(content=content, exists=len(content) > 0).model_dump())


def _put_handler(key: str):
    payload = ContextUpdateRequest.model_validate(request.get_json(force=True) or {})
    try:
        write_context(key, payload.content)
    except OSError:
        logger.error("Failed to write context file: %s", key)
        return jsonify({"error": f"Failed to save {key}"}), 500
    return jsonify(SuccessResponse(success=True).model_dump())


@context_bp.get("/api/context/<key>")
def get_context(key: str):
    if key not in _VALID_KEYS:
        return jsonify({"error": f"Unknown context key: {key!r}"}), 404
    return _get_handler(key)


@context_bp.put("/api/context/<key>")
def put_context(key: str):
    if key not in _VALID_KEYS:
        return jsonify({"error": f"Unknown context key: {key!r}"}), 404
    return _put_handler(key)
```

Verify the app boots and the new routes are present:

```bash
python - <<'EOF'
from create_app import create_app
app = create_app()
rules = {r.rule for r in app.url_map.iter_rules()}
assert "/api/context/<key>" in rules, "new route missing"
for old in ("/api/builder", "/api/principles", "/api/codebase", "/api/references"):
    assert old not in rules, f"old route still registered: {old}"
print("Route check passed")
EOF
```

Now you can run `make test` — `everyOpenapiPath_hasRouteHandler` should pass since both edits are complete.

---

### Step 3 — Regenerate DTOs

The schema shapes (`ContextResponse`, `ContextUpdateRequest`, `SuccessResponse`) are unchanged; only operationIds and paths changed. Still run the regeneration step to keep the committed Python artifact in sync. (Note: this repo only generates Python DTOs — there is no `src/app/models/api.d.ts` to regenerate.)

```bash
make generate-dtos
make check-dtos
# Both must exit 0. If check-dtos fails, git add -f dtos/models.py
```

---

### Step 4 — Update `tests/test_context_files.py`

**4a.** Replace every occurrence of the old route strings in parametrize decorators and test bodies:

| Old | New |
|---|---|
| `"/api/builder"` | `"/api/context/builder"` |
| `"/api/principles"` | `"/api/context/principles"` |
| `"/api/codebase"` | `"/api/context/codebase"` |
| `"/api/references"` | `"/api/context/references"` |

This affects the following parametrize lists at lines 99–104, 118–123, 142–147, and the route strings inside `existingContent_putOverwrites` (line 175) and `putThenGet_returnsExactSameContent` (line 222).

**4b.** Replace the `createApp_allContextRoutesRegistered` function (lines 235–251) with:

```python
def createApp_contextRoute_registeredAndOldRoutesAbsent():
    """Parameterised /api/context/<key> is registered; the four old flat routes are gone."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from create_app import create_app

    app = create_app()
    rules = {r.rule for r in app.url_map.iter_rules()}

    assert "/api/context/<key>" in rules, (
        "/api/context/<key> not registered in Flask app — did routes.py get saved?"
    )
    for stale in ("/api/builder", "/api/principles", "/api/codebase", "/api/references"):
        assert stale not in rules, (
            f"Old flat route {stale!r} still registered — remove it from routes.py"
        )
```

**4c.** Append this new test function at the end of the file (after `contextReadError_putBuilder_returns500`):

```python
def unknownKey_getReturns404(client):
    """GET /api/context/<unknown> returns 404 with an error body."""
    resp = client.get("/api/context/nonexistent")
    assert resp.status_code == 404, f"expected 404, got {resp.status_code}"
    body = json.loads(resp.data)
    assert "error" in body, f"expected 'error' key in body; got {body!r}"


def unknownKey_putReturns404(client):
    """PUT /api/context/<unknown> returns 404 with an error body."""
    resp = client.put(
        "/api/context/nonexistent",
        data=json.dumps({"content": "anything"}),
        content_type="application/json",
    )
    assert resp.status_code == 404, f"expected 404, got {resp.status_code}"
    body = json.loads(resp.data)
    assert "error" in body, f"expected 'error' key in body; got {body!r}"
```

---

### Step 5 — Update `tests/test_contracts.py`

The `TestOpenApiResponseShape` class has one context assertion that references the old path in both the spec lookup and the HTTP call. Update it:

```python
# Before (line ~263)
def test_contextBuilder_matchesOpenApiSchema(self, mock_client, spec):
    schema = responseSchemaFor(spec, "/api/builder", "get", "200")
    resp = mock_client.get("/api/builder")
    assert resp.status_code == 200
    jsonschema.validate(resp.get_json(), schema)

# After
def test_contextBuilder_matchesOpenApiSchema(self, mock_client, spec):
    schema = responseSchemaFor(spec, "/api/context/{key}", "get", "200")
    resp = mock_client.get("/api/context/builder")
    assert resp.status_code == 200
    jsonschema.validate(resp.get_json(), schema)
```

---

### Step 6 — Run Flask tests

```bash
cd /workspace/api
make test
# All 192+ tests must pass. Key tests to watch:
#   tests/test_context_files.py::everyOpenapiPath_hasRouteHandler  PASSED
#   tests/test_context_files.py::createApp_contextRoute_registeredAndOldRoutesAbsent  PASSED
#   tests/test_context_files.py::unknownKey_getReturns404  PASSED
#   tests/test_contracts.py::TestOpenApiResponseShape::test_contextBuilder_matchesOpenApiSchema  PASSED
```

---

### Step 7 — Create `src/app/services/context.service.ts`

```typescript
// src/app/services/context.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type ContextKey = 'builder' | 'principles' | 'codebase' | 'references';

export interface ContextResponse {
  content: string;
  exists: boolean;
}

export interface ContextSaveResponse {
  success: boolean;
}

@Injectable({ providedIn: 'root' })
export class ContextService {
  constructor(private http: HttpClient) {}

  get(key: ContextKey): Observable<ContextResponse> {
    return this.http.get<ContextResponse>(`/api/context/${key}`);
  }

  save(key: ContextKey, content: string): Observable<ContextSaveResponse> {
    return this.http.put<ContextSaveResponse>(`/api/context/${key}`, { content });
  }
}
```

---

### Step 8 — Update each consuming component

Find every component that injects the old services:

```bash
grep -rl "BuilderService\|PrinciplesService\|CodebaseService\|ReferencesService" \
  /workspace/web/src/app/components/
```

For **each** file returned, apply this pattern (shown for `BuilderService`; repeat for each key):

```typescript
// BEFORE
import { BuilderService } from '../../services/builder.service';
// ...
constructor(private builderService: BuilderService) {}
// ...
this.builderService.get().subscribe(...)
this.builderService.save(content).subscribe(...)

// AFTER
import { ContextService } from '../../services/context.service';
// ...
constructor(private contextService: ContextService) {}
// ...
this.contextService.get('builder').subscribe(...)
this.contextService.save('builder', content).subscribe(...)
```

The key string passed to `ContextService` must match the component's domain:

| Old service | Key argument |
|---|---|
| `BuilderService` | `'builder'` |
| `PrinciplesService` | `'principles'` |
| `CodebaseService` | `'codebase'` |
| `ReferencesService` | `'references'` |

Verify no TypeScript providers or barrel files re-export the old services:

```bash
grep -r "BuilderService\|PrinciplesService\|CodebaseService\|ReferencesService" \
  /workspace/web/src/app/ --include="*.ts"
# Must return zero lines after all updates are complete
```

---

### Step 9 — Delete the four old services

```bash
cd /workspace/web/src/app/services
rm builder.service.ts principles.service.ts codebase.service.ts references.service.ts
# Also remove any spec files for the deleted services if present:
rm -f builder.service.spec.ts principles.service.spec.ts \
       codebase.service.spec.ts references.service.spec.ts
```

---

### Step 10 — Verify Angular build

```bash
cd /workspace/web
ng build --configuration development 2>&1 | tail -30
# Must exit 0 — zero TS errors, zero unresolved imports
```

---

## 5. Tests

### Flask — `tests/test_context_files.py` additions (Step 4c)

Both functions follow the repo's camelCase/`test_` naming convention (pytest collects functions whose name contains `_`).

```python
def unknownKey_getReturns404(client):
    """GET /api/context/<unknown> returns 404 with an error body."""
    resp = client.get("/api/context/nonexistent")
    assert resp.status_code == 404, f"expected 404, got {resp.status_code}"
    body = json.loads(resp.data)
    assert "error" in body, (
        f"404 body must contain 'error' key; got {body!r}"
    )


def unknownKey_putReturns404(client):
    """PUT /api/context/<unknown> returns 404 with an error body."""
    resp = client.put(
        "/api/context/nonexistent",
        data=json.dumps({"content": "anything"}),
        content_type="application/json",
    )
    assert resp.status_code == 404, f"expected 404, got {resp.status_code}"
    body = json.loads(resp.data)
    assert "error" in body, (
        f"404 body must contain 'error' key; got {body!r}"
    )
```

### Angular — `src/app/services/context.service.spec.ts` (new file, Step 7)

Framework: Karma + Jasmine with `HttpClientTestingModule`. Matches the pattern of `projects.service.spec.ts`.

```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ContextService, ContextKey } from './context.service';

describe('ContextService', () => {
  let service: ContextService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ContextService],
    });
    service = TestBed.inject(ContextService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  const KEYS: ContextKey[] = ['builder', 'principles', 'codebase', 'references'];

  KEYS.forEach((key) => {
    describe(`key=${key}`, () => {
      it('get() calls relative GET with no localhost', () => {
        service.get(key).subscribe((r) => {
          expect(r.content).toBe('# Test content');
          expect(r.exists).toBeTrue();
        });
        const req = httpMock.expectOne(`/api/context/${key}`);
        expect(req.request.method).toBe('GET');
        expect(req.request.url).not.toContain('localhost');
        req.flush({ content: '# Test content', exists: true });
      });

      it('save() calls relative PUT with content body, no localhost', () => {
        service.save(key, '# Updated').subscribe((r) => {
          expect(r.success).toBeTrue();
        });
        const req = httpMock.expectOne(`/api/context/${key}`);
        expect(req.request.method).toBe('PUT');
        expect(req.request.body).toEqual({ content: '# Updated' });
        expect(req.request.url).not.toContain('localhost');
        req.flush({ success: true });
      });
    });
  });
});
```

Run Angular tests:

```bash
cd /workspace/web
# Skip ng test if no Chrome/Chromium binary is available in the environment;
# rely on `npx tsc --noEmit` and `make test` (Flask) for the verification gate.
ng test --watch=false --browsers=ChromeHeadless || echo "ng test skipped — no Chrome" 2>&1 | tail -20
# context.service.spec.ts — 8 specs (2 per key × 4 keys), 0 failures
```

---

## 6. Commit Plan

Two commits on a feature branch. **No direct push to `master`** (enforced by repo rule). The container has no `ssh` and no `gh` — commit locally and skip the `gh pr create` block at the end of this section; the user will push and open the PR separately.

```bash
cd /workspace/api
git checkout -b task/1-unify-context-services

# Commit 1 — backend only (Flask + tests pass independently)
git add openapi.yaml modules/context/routes.py \
        tests/test_context_files.py tests/test_contracts.py \
        dtos/models.py
git commit -m "$(cat <<'EOF'
refactor(context): replace 8 flat routes with GET/PUT /api/context/{key}

Four named Flask routes and their individual test parametrize entries
collapse to one parameterised pair. openapi.yaml drops from 11 to 8
paths. everyOpenapiPath_hasRouteHandler and all contract tests pass.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# Commit 2 — Angular (after ng build passes)
cd /workspace/web
git add src/app/services/context.service.ts \
        src/app/services/context.service.spec.ts \
        src/app/components/
git rm src/app/services/builder.service.ts \
       src/app/services/principles.service.ts \
       src/app/services/codebase.service.ts \
       src/app/services/references.service.ts
# add any deleted spec files:
git rm -f src/app/services/builder.service.spec.ts \
           src/app/services/principles.service.spec.ts \
           src/app/services/codebase.service.spec.ts \
           src/app/services/references.service.spec.ts 2>/dev/null || true
git commit -m "$(cat <<'EOF'
refactor(context): replace 4 Angular services with ContextService(key)

BuilderService, PrinciplesService, CodebaseService, and ReferencesService
deleted. ContextService accepts a ContextKey param and calls /api/context/{key}.
All consuming components updated. ng build clean, 8 Jasmine specs added.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# Open PR
gh pr create \
  --base master \
  --title "Task 1: Unify context services into ContextService(key)" \
  --body "$(cat <<'EOF'
## Summary
- 8 Flask context routes → 2 (`GET`/`PUT /api/context/{key}`)
- `openapi.yaml` 11 paths → 8 paths; `make check-dtos` passes
- 4 Angular services deleted; `ContextService` with `ContextKey` union type replaces them
- All 192+ Flask tests green; 8 new Jasmine specs added

## Test plan
- [ ] `make test` passes in `spec-doc/api`
- [ ] `ng test --watch=false` passes in `spec-doc`
- [ ] `ng build --configuration development` exits 0
- [ ] Manual smoke: open app, load Builder tab, edit and save — verify round-trip via DevTools network tab shows `/api/context/builder`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## 7. Verification

### Automated

```bash
# Flask
cd /workspace/api
make test
# Expected: all tests pass (count will be ≥192; new tests add 2 more)

# DTO sync
make check-dtos
# Expected: exit 0

# openapi.yaml route parity
python -c "
import yaml, re
from create_app import create_app
spec = yaml.safe_load(open('openapi.yaml'))
app = create_app()
declared = set(spec['paths'])
registered = {re.sub(r'<(?:[^:>]+:)?([^>]+)>', r'{\1}', r.rule)
              for r in app.url_map.iter_rules()
              if r.rule.startswith('/api') or r.rule == '/health'}
print('declared only:', declared - registered)
print('registered only:', registered - declared)
assert declared == registered
print('Parity OK')
"

# Angular
cd /workspace/web
ng build --configuration development
ng test --watch=false --browsers=ChromeHeadless
```

### Manual smoke test

1. `make dev` in `spec-doc/api`
2. `ng serve` in `spec-doc`
3. Open browser DevTools → Network tab
4. Navigate to each context tab (Builder, Principles, Codebase, References)
5. Confirm each triggers `GET /api/context/<key>` — **not** `/api/builder` etc.
6. Edit content and save in one tab — confirm `PUT /api/context/<key>` with `{"content": "..."}` body and 200 response

---

## 8. Rollback

The old route surface is still expressible via the existing `_get_handler` / `_put_handler` private helpers — they are unchanged. To revert:

```bash
# Backend: restore routes.py from git
git checkout master -- modules/context/routes.py openapi.yaml \
                       tests/test_context_files.py tests/test_contracts.py \
                       dtos/models.py

# Angular: restore services from git (if committed)
git checkout master -- src/app/services/builder.service.ts \
                       src/app/services/principles.service.ts \
                       src/app/services/codebase.service.ts \
                       src/app/services/references.service.ts
# Revert component edits:
git checkout master -- src/app/components/
# Remove new ContextService:
rm src/app/services/context.service.ts src/app/services/context.service.spec.ts
```

If on a feature branch (the normal case), simply close the PR and delete the branch. `master` is untouched.

---

## 9. Deviations Allowed

| Deviation | Condition |
|---|---|
| Return `400` instead of `404` for unknown key | Acceptable if the team prefers client-error semantics for a bad path param. Update the two new test assertions accordingly. |
| Use a Python `Enum` class instead of `frozenset` for `_VALID_KEYS` in `routes.py` | Fine — import `from enum import Enum`, define `class ContextKey(str, Enum)`, and use `ContextKey(key)` inside a try/except `ValueError` block. Same observable behaviour. |
| Angular `ContextKey` as `enum` instead of union type | Fine — `enum ContextKey { Builder = 'builder', ... }`. Update the spec file's `KEYS` array accordingly. |
| Combine both commits into one | Fine if all changes are ready simultaneously. |

---

## 10. Out of Scope

| Item | Reason |
|---|---|
| Key validation via Pydantic DTO (path param model) | Flask doesn't natively support Pydantic path param validation; frozenset check at the route boundary is simpler and sufficient |
| Caching the context file reads | No cache layer — second context type triggers that, per architecture doc |
| A `ContextKey` registry with auto-discovery | Explicit `CONTEXT_PATHS` dict in `config.py` is the correct single source of truth; no auto-registration |
| Angular proxy config (`proxy.conf.json`) | Pre-existing concern; not introduced by this task |
| `openapi.yaml` for Task 5 (final surface consolidation) | Task 5 is a separate task dependent on Tasks 1 and 4 both landing |
| Deprecation shims for the four deleted Angular services | The tool has no external API consumers; hard delete is the correct failure mode (compile-time, not runtime) |