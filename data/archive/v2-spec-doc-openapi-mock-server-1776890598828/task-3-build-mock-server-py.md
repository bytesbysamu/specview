# Task 3: Build mock_server.py

## 1. Context

`flask/mock_server.py` is a temporary Flask application on port 3102 that implements all Phase 1 routes using in-memory state, enabling the Angular frontend to exercise the full API contract before a single production Flask route exists. Pre-seeded with three realistic projects and four context keys, it lets the sidebar render immediately on load, the editor open files, and context panels round-trip — proving the spec correct from the Angular consumer's perspective. This task also closes the "env var swap, not code change" gap called out in the architecture: `projects.service.ts` currently has `http://localhost:3100/api/projects` hardcoded at line 31, which must be extracted to `environment.ts` before the mock can serve as a drop-in port swap.

**Trade-offs considered:**
- Extending `flask/app.py` with a `MOCK=true` flag and in-memory adapters — rejected because it entangles real and mock code paths, adds conditionals that must be cleaned up before Tasks 2/3, and increases blast radius.
- Building the mock as json-server (Node.js) — rejected because Flask is already a project dependency; a single Python file introduces nothing new.
- Single flat file, no blueprints or service layer — chosen because the mock has one consumer, one purpose, and a planned deletion date; structural layering has zero downstream payoff for throwaway infrastructure.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# From spec-doc/
git status                                                         # note: references.md and new-project.component.ts are already dirty — they are NOT targets for this task
git diff HEAD -- flask/mock_server.py                              # expect: fatal or no output (file does not exist)
git diff HEAD -- src/app/services/projects.service.ts              # confirm clean before editing
git diff HEAD -- src/environments/                                 # expect: no such directory

cd flask && python -m pytest tests/ -q                            # record baseline pass count
```

**If working tree is dirty on `projects.service.ts`**: stash or commit those changes first before starting.

**Note on existing dirty files**: `references.md` (modified context file) and `src/app/components/new-project/new-project.component.ts` are already modified per git status. Leave them alone — they are not targets for this task.

**Baseline recorded**: ___ / ___ passing.

---

## 3. Files

### To Create (new)
- `flask/mock_server.py` — standalone Flask mock on port 3102; in-memory `_PROJECTS` and `_CONTEXT` stores; no imports from `flask/modules/`
- `src/environments/environment.ts` — Angular environment file; exports `environment.apiUrl`; consumed by `projects.service.ts`

### To Modify (cite CODEBASE CONTEXT)
- `src/app/services/projects.service.ts` — line 31 currently reads `private baseUrl = 'http://localhost:3100/api/projects'`; replace with `environment.apiUrl`-driven construction; no other logic changes

### To Leave Alone
- `flask/modules/` — production Flask routes; mock is a parallel file, not a modification
- `flask/app.py`, `flask/create_app.py` — production startup; mock has its own `if __name__ == '__main__'` block
- `flask/tests/` — existing pytest suite; architecture decision: mock has no pytest coverage (Angular integration is the test)
- `src/app/services/ai.service.ts` — AI routes are Phase 2; mock does not implement them; hardcoded `http://localhost:3100/api/ai/text` stays in place
- `references.md`, `src/app/components/new-project/new-project.component.ts` — in-progress user changes; unrelated to this task

---

## 4. Implementation Steps

### Step 1: Create src/environments/environment.ts

**Action**: Create the `src/environments/` directory and `environment.ts` with `apiUrl` defaulting to the real Express backend (3100). This is the single-value swap point documented in the architecture. Default value is the real backend so the file can be committed without requiring the mock.

**File**: `src/environments/environment.ts` (new)

**Pattern**:
```typescript
export const environment = {
  apiUrl: 'http://localhost:3100',
};
```

**Verify**: `ls src/environments/environment.ts` — file exists and contains the above content.

---

### Step 2: Update projects.service.ts Base URL

**Action**: Add an import for `environment` and replace the hardcoded `http://localhost:3100` in `baseUrl` at line 31 with `environment.apiUrl`. Change no other methods or logic.

**File**: `src/app/services/projects.service.ts` (existing — line 31: `private baseUrl = 'http://localhost:3100/api/projects'`)

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

// ... interfaces unchanged ...

@Injectable({ providedIn: 'root' })
export class ProjectsService {
  private baseUrl = `${environment.apiUrl}/api/projects`;

  // all other methods unchanged
}
```

**Verify**:
```bash
grep -n "localhost:3100" src/app/services/projects.service.ts   # expect: 0 matches
grep -n "environment.apiUrl" src/app/services/projects.service.ts  # expect: 1 match
```

---

### Step 3: Write flask/mock_server.py

**Action**: Create the mock server as a single file. No imports from `flask/modules/`. Route shapes follow `flask/api-contract.md` exactly. Context routes use the flat path pattern (`/api/builder`, `/api/principles`, etc.) matching the existing Flask implementation in `flask/modules/context/routes.py`. The dynamic `GET /api/<key>` and `PUT /api/<key>` handlers work correctly because Flask's static routes (`/api/projects`, `/api/projects/<id>`) take priority at registration time — `/api/<key>` only fires for the four context key names.

**File**: `flask/mock_server.py` (new)

**Pattern** (complete implementation — ~145 lines):
```python
"""
mock_server.py — in-memory mock on port 3102.
One consumer: Angular frontend during Task 4 contract validation.
Replace with real Flask routes in Tasks 2 and 3.
"""
import os
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["http://localhost:4201"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _make_id(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    return f"{slug}-{ts}"


def _label(filename: str) -> str:
    return filename.removesuffix(".md").replace("-", " ").title()


# ── in-memory stores (reset on restart — intentional) ─────────────────────────

_PROJECTS: dict = {
    "spec-doc-1704067200000": {
        "id": "spec-doc-1704067200000",
        "name": "Spec Doc",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "files": {
            "analysis.md": "# Analysis\n\nSpec Doc solves the gap between AI chat and structured specs.",
            "epic.md": "# Epic\n\n## Goal\nShip a document-first AI editor.\n\n## MVP\nBootstrap → Edit → Save.",
            "architecture.md": "# Architecture\n\n## Stack\n- Frontend: Angular 19\n- Backend: Express + Flask",
        },
    },
    "humanize-me-1704153600000": {
        "id": "humanize-me-1704153600000",
        "name": "Humanize Me",
        "createdAt": "2024-01-02T00:00:00.000Z",
        "files": {
            "analysis.md": "# Analysis\n\nAI-generated text is detectable. Users need undetectable rewrites.",
            "epic.md": "# Epic\n\n## Goal\n$1K MRR in 30 days.\n\n## MVP\nSingle-pass humanize endpoint.",
        },
    },
    "trendfy-1704240000000": {
        "id": "trendfy-1704240000000",
        "name": "Trendfy",
        "createdAt": "2024-01-03T00:00:00.000Z",
        "files": {
            "analysis.md": "# Analysis\n\nFashion brands need affordable product photography.",
            "architecture.md": "# Architecture\n\n## Stack\n- Angular 19 + Flask + Replicate LoRA",
        },
    },
}

_CONTEXT: dict[str, str] = {
    "builder": "# Builder Profile\n\nFull-stack developer building SaaS products fast.",
    "principles": "# Principles\n\n- Ship fast, validate, iterate\n- Claude IS the algorithm",
    "codebase": "",
    "references": "",
}

_CONTEXT_KEYS = frozenset(_CONTEXT)


# ── health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# ── projects ──────────────────────────────────────────────────────────────────

@app.get("/api/projects")
def list_projects():
    summaries = [
        {
            "id": p["id"],
            "name": p["name"],
            "createdAt": p["createdAt"],
            "specs": [{"filename": f, "label": _label(f)} for f in p["files"]],
        }
        for p in sorted(_PROJECTS.values(), key=lambda x: x["createdAt"], reverse=True)
    ]
    return jsonify(summaries)


@app.get("/api/projects/<project_id>")
def get_project(project_id: str):
    project = _PROJECTS.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify({
        "id": project["id"],
        "name": project["name"],
        "createdAt": project["createdAt"],
        "specs": [
            {"filename": f, "label": _label(f), "content": c}
            for f, c in project["files"].items()
        ],
    })


@app.post("/api/projects")
def create_project():
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    project_id = _make_id(name)
    _PROJECTS[project_id] = {
        "id": project_id,
        "name": name,
        "createdAt": _now(),
        "files": {f["filename"]: f.get("content", "") for f in body.get("files", [])},
    }
    p = _PROJECTS[project_id]
    return jsonify({"id": p["id"], "name": p["name"], "createdAt": p["createdAt"]}), 201


@app.put("/api/projects/<project_id>/files/<filename>")
def update_file(project_id: str, filename: str):
    project = _PROJECTS.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    body = request.get_json(silent=True) or {}
    project["files"][filename] = body.get("content", "")
    return jsonify({"success": True})


@app.delete("/api/projects/<project_id>")
def delete_project(project_id: str):
    if project_id not in _PROJECTS:
        return jsonify({"error": "Project not found"}), 404
    del _PROJECTS[project_id]
    return jsonify({"success": True})


# ── context ───────────────────────────────────────────────────────────────────
# Flat routes match flask/modules/context/routes.py: /api/builder, /api/principles, etc.
# Flask static routes (/api/projects, /api/projects/<id>) take priority over /api/<key>.

@app.get("/api/<key>")
def get_context(key: str):
    if key not in _CONTEXT_KEYS:
        return jsonify({"error": "Not found"}), 404
    content = _CONTEXT[key]
    return jsonify({"content": content, "exists": bool(content)})


@app.put("/api/<key>")
def put_context(key: str):
    if key not in _CONTEXT_KEYS:
        return jsonify({"error": "Not found"}), 404
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("content"), str):
        return jsonify({"error": "content must be a string"}), 400
    _CONTEXT[key] = body["content"]
    return jsonify({"success": True})


# ── startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3102))
    print(f"[Mock] Spec Doc mock on http://0.0.0.0:{port}")
    print(f"[Mock] {len(_PROJECTS)} projects pre-seeded | Context: {', '.join(sorted(_CONTEXT_KEYS))}")
    app.run(host="0.0.0.0", port=port, debug=True)
```

**Verify**:
```bash
cd flask && python mock_server.py &
MOCK_PID=$!
sleep 1
curl -s http://localhost:3102/health         # expect: {"status":"ok"}
curl -s http://localhost:3102/api/projects | python -c \
  "import sys,json; d=json.load(sys.stdin); assert len(d)==3, f'got {len(d)}'; print('OK: 3 projects')"
kill $MOCK_PID
```

---

### Step 4: Swap Angular to Mock and Validate (manual)

**Action**: Change `environment.ts` `apiUrl` to `http://localhost:3102`. Run both servers. Execute the validation checklist. Restore `apiUrl` to `http://localhost:3100` **before committing**.

**Swap to mock**:
```typescript
// src/environments/environment.ts
export const environment = {
  apiUrl: 'http://localhost:3102',  // ← mock
};
```

**Start servers**:
```bash
cd flask && python mock_server.py &   # port 3102
cd .. && npm start                    # Angular on port 4201
```

**Validation checklist** (in browser at http://localhost:4201):
1. Sidebar renders exactly 3 projects: Trendfy (newest), Humanize Me, Spec Doc
2. Clicking a project opens it and all its files appear in the sidebar
3. Opening a file renders its markdown content in the editor
4. Editing a file triggers auto-save; the PUT request to `http://localhost:3102/api/projects/<id>/files/<filename>` returns `{"success":true}` (confirm in browser DevTools Network tab)
5. Creating a new project via the bootstrap modal returns 201 and the project appears in the sidebar
6. `curl -s http://localhost:3102/api/builder` returns `{"content":"# Builder Profile...","exists":true}`
7. `curl -s http://localhost:3102/api/codebase` returns `{"content":"","exists":false}`

**Restore before commit**:
```typescript
export const environment = {
  apiUrl: 'http://localhost:3100',  // ← restore to real backend
};
```

```bash
grep "localhost:3102" src/environments/environment.ts  # expect: 0 results
```

---

## 5. Tests

The architecture explicitly excludes a pytest suite for the mock: *"A passing pytest suite without a working frontend proves nothing about the contract from the consumer's perspective."* (Architecture, Design Decisions table.) The Angular validation in Step 4 is the test.

The following curl-based smoke script is the machine-verifiable equivalent and can be run before the Angular session:

```bash
#!/usr/bin/env bash
set -e
cd flask
python mock_server.py &
MOCK_PID=$!
sleep 1

BASE="http://localhost:3102"

# Health
assert_status() {
  actual=$(curl -s -o /dev/null -w "%{http_code}" "$1" ${@:2})
  [ "$actual" = "$2" ] || { echo "FAIL $1: expected $2 got $actual"; kill $MOCK_PID; exit 1; }
}

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health")
[ "$STATUS" = "200" ] || { echo "FAIL health: $STATUS"; kill $MOCK_PID; exit 1; }

# List — expect 3 items, newest-first (Trendfy → Humanize Me → Spec Doc)
FIRST=$(curl -s "$BASE/api/projects" | python -c "import sys,json; d=json.load(sys.stdin); assert len(d)==3; assert d[0]['id']=='trendfy-1704240000000'; print('OK')")
[ "$FIRST" = "OK" ] || { echo "FAIL list_projects: $FIRST"; kill $MOCK_PID; exit 1; }

# Get existing project
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/projects/spec-doc-1704067200000")
[ "$STATUS" = "200" ] || { echo "FAIL get_project: $STATUS"; kill $MOCK_PID; exit 1; }

# Get project — detail shape includes specs with content
HAS_CONTENT=$(curl -s "$BASE/api/projects/spec-doc-1704067200000" | python -c "
import sys, json
d = json.load(sys.stdin)
assert 'specs' in d
assert all('content' in s for s in d['specs']), 'missing content field'
print('OK')
")
[ "$HAS_CONTENT" = "OK" ] || { echo "FAIL get_project detail: $HAS_CONTENT"; kill $MOCK_PID; exit 1; }

# Get missing project — 404
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/projects/nonexistent")
[ "$STATUS" = "404" ] || { echo "FAIL get_missing: $STATUS"; kill $MOCK_PID; exit 1; }

# Create project — 201, returned id matches name slug
RESP=$(curl -s -X POST "$BASE/api/projects" \
  -H "Content-Type: application/json" \
  -d '{"name": "Smoke Test", "files": [{"filename": "notes.md", "content": "hello"}]}')
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/projects" \
  -H "Content-Type: application/json" \
  -d '{"name": "Smoke Test 2", "files": []}')
[ "$STATUS" = "201" ] || { echo "FAIL create_project status: $STATUS"; kill $MOCK_PID; exit 1; }

NEW_ID=$(echo "$RESP" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
[ -n "$NEW_ID" ] || { echo "FAIL create_project: no id"; kill $MOCK_PID; exit 1; }

# Create — missing name returns 400
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/api/projects" \
  -H "Content-Type: application/json" -d '{}')
[ "$STATUS" = "400" ] || { echo "FAIL create_no_name: $STATUS"; kill $MOCK_PID; exit 1; }

# Update file — mutation persists within session
curl -s -X PUT "$BASE/api/projects/$NEW_ID/files/notes.md" \
  -H "Content-Type: application/json" -d '{"content": "updated"}' > /dev/null
AFTER=$(curl -s "$BASE/api/projects/$NEW_ID" | python -c "
import sys, json
d = json.load(sys.stdin)
spec = next(s for s in d['specs'] if s['filename'] == 'notes.md')
assert spec['content'] == 'updated', f'got: {spec[\"content\"]}'
print('OK')
")
[ "$AFTER" = "OK" ] || { echo "FAIL update_file mutation: $AFTER"; kill $MOCK_PID; exit 1; }

# Delete project
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE/api/projects/$NEW_ID")
[ "$STATUS" = "200" ] || { echo "FAIL delete_project: $STATUS"; kill $MOCK_PID; exit 1; }
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/projects/$NEW_ID")
[ "$STATUS" = "404" ] || { echo "FAIL delete_not_gone: $STATUS"; kill $MOCK_PID; exit 1; }

# Context GET — builder has content (exists: true)
EXISTS=$(curl -s "$BASE/api/builder" | python -c "import sys,json; print(json.load(sys.stdin)['exists'])")
[ "$EXISTS" = "True" ] || { echo "FAIL context_get_builder exists: $EXISTS"; kill $MOCK_PID; exit 1; }

# Context GET — codebase is empty (exists: false)
EXISTS=$(curl -s "$BASE/api/codebase" | python -c "import sys,json; print(json.load(sys.stdin)['exists'])")
[ "$EXISTS" = "False" ] || { echo "FAIL context_get_codebase exists: $EXISTS"; kill $MOCK_PID; exit 1; }

# Context PUT round-trip
curl -s -X PUT "$BASE/api/principles" \
  -H "Content-Type: application/json" -d '{"content": "ship daily"}' > /dev/null
AFTER=$(curl -s "$BASE/api/principles" | python -c "import sys,json; print(json.load(sys.stdin)['content'])")
[ "$AFTER" = "ship daily" ] || { echo "FAIL context_put round-trip: $AFTER"; kill $MOCK_PID; exit 1; }

# Context PUT — non-string content returns 400
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$BASE/api/references" \
  -H "Content-Type: application/json" -d '{"content": 42}')
[ "$STATUS" = "400" ] || { echo "FAIL context_put_type: $STATUS"; kill $MOCK_PID; exit 1; }

# Unknown context key — 404
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/unknown-key")
[ "$STATUS" = "404" ] || { echo "FAIL unknown_key: $STATUS"; kill $MOCK_PID; exit 1; }

kill $MOCK_PID
echo "All smoke tests passed."
```

---

## 6. Commit Plan

1. `feat(env): extract Angular apiUrl to environment.ts, update projects.service` — `src/environments/environment.ts` (new), `src/app/services/projects.service.ts` (line 31 + import): closes hardcoded URL gap; enables single-value swap to mock port

2. `feat(mock): implement mock_server.py on port 3102 with pre-seeded data` — `flask/mock_server.py` (new): full Phase 1 route implementation against in-memory stores; 3 pre-seeded projects; 4 context keys; no imports from production modules

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

**Important**: commit `environment.ts` with `apiUrl: 'http://localhost:3100'` (real backend). The `http://localhost:3102` value is a local dev swap — never commit it.

---

## 7. Verification

```bash
# Existing pytest suite must be unaffected
cd flask && python -m pytest tests/ -q
```

**Expected delta**: N → N passing (zero change). This task adds no pytest tests.

**Smoke suite** (see Tests section): all assertions pass.

**Angular integration** (see Step 4 checklist): sidebar renders 3 pre-seeded projects on first load; editor opens a file; auto-save PUT reaches 3102; context panels read and write without error.

---

## 8. Rollback

- **Commit 1 revert**: `git revert <sha>` — removes `src/environments/environment.ts` and restores `projects.service.ts` line 31 to the hardcoded string
- **Commit 2 revert**: `git revert <sha>` — removes `flask/mock_server.py`
- **Per-branch (catastrophic)**: `git reset --hard <pre-task-sha>` — both commits are small and sequential; a single reset restores clean state with zero collateral damage to `references.md` or `new-project.component.ts` (those changes predate this task)

---

## 9. Deviations Allowed

- **`src/environments/` path differs** → inspect `angular.json` for `sourceRoot`; adjust the relative import path in `projects.service.ts` accordingly; log in commit body
- **`projects.service.ts` line 31 has moved** → `grep -n "localhost:3100" src/app/services/projects.service.ts`; update the correct line; log deviation
- **Flask routing conflict with `/api/<key>`** → if startup raises an `AssertionError` about overlapping routes, replace the two dynamic handlers with eight explicit routes (`@app.get("/api/builder")`, etc.) using `request.path.rsplit("/",1)[-1]` to extract the key; log deviation
- **Angular `npm start` fails after adding `environment.ts`** → check `angular.json` for an existing `fileReplacements` stanza; add one if required; do NOT create `environment.production.ts` unless `angular.json` requires it
- **Step N simplification for Step N+1** → take it, log in commit body
- **Side-effect required** (push, publish, schema change) → STOP, mark [REQUIRES APPROVAL] and ask

---

## 10. Out of Scope

This task delivers a proof-of-contract mock, not a production system. The items below are explicitly deferred and must not be absorbed by the executor even if they appear helpful.

- **pytest suite for mock routes** — architecture decision: a passing pytest suite cannot detect contract mismatches from the Angular consumer's perspective; revisit only if the mock outlives Task 4 and needs regression coverage
- **DTOs from flask/dtos/** — Task 2 (DTO generation) is parallel with this task and may not be complete; the mock uses plain dicts and `jsonify()`; the mock is throwaway so backfilling DTO usage is not worth the effort even after Task 2 ships
- **openapi.yaml alignment check** — the mock implements routes from `flask/api-contract.md`; if `openapi.yaml` now exists (Task 1 complete), manually verify the route shapes match, but do not add `openapi-spec-validator` runtime validation to the mock
- **ai.service.ts base URL extraction** — AI endpoints are Phase 2; extracting a shared base URL for both projects and AI services requires decomposing the two services' URL structures and is not needed for Task 3 or Task 4
- **Angular context service** — exploration found no `context.service.ts`; context calls may be inline in components; do not create a new service or refactor component code as part of this task
- **Persistence in the mock** — restart resets are intentional; do not add SQLite, file-based state, or any durability mechanism
- **Request validation in the mock** — Flask route implementations in Tasks 2/3 own validation; duplicating rules here creates two sources of truth for zero benefit during this phase
- **Swagger UI or openapi.yaml serving** — no named consumer at this stage; do not add `flask-swagger-ui` or route serving for the spec file

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale and component descriptions
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Update to ✅ after Step 4 Angular validation passes