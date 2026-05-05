# Task 3: Extract Template Generators

## 1. Context

Three functions in `new-project.component.ts` — `generateSpecIndex()`, `generateTimeline()`, and `generateReadme()` — produce markdown file content from inside a UI component. They are pure data transformations with no UI state dependency; their only correct home is Flask, where their output can be locked by `syrupy` snapshot tests and silently-drifting string literals become attributable PR diffs.

**Deliverables:**

| # | What | Where |
|---|------|-------|
| A | `generate_spec_index()`, `generate_timeline()`, `generate_readme()` pure Python functions | `modules/templates/generators.py` (new) |
| B | `GET /api/templates/<name>` Flask route | `modules/templates/routes.py` (new) |
| C | Package markers | `modules/templates/__init__.py`, `modules/templates/tests/__init__.py` (new) |
| D | Unit tests + syrupy snapshot tests | `modules/templates/tests/test_generators.py`, `test_generators_snapshots.py` (new) |
| E | HTTP route tests | `tests/test_templates.py` (new) |
| F | OpenAPI schema + path | `openapi.yaml` (edit) |
| G | Generated DTO | `dtos/models.py` (regenerated via `make generate-dtos`) |
| H | Blueprint registration | `create_app.py` (edit) |
| I | Replace three inline functions with HTTP calls | `/workspace/web/src/app/components/new-project/new-project.component.ts` (edit) |

**Route count change:** 21 → 22 (add 1 `GET`).

**`everyOpenapiPath_hasRouteHandler` constraint:** Step 4 (`openapi.yaml` edit) and Step 5 (route registration in `create_app.py`) must both complete before running `make test`. Do not run `make test` between them.

**Port budget:** ≤ 80 lines across the three generator functions in `generators.py`. No Jinja2. No user-customisable template variables.

> **⚠ The function signatures in §4 Step 2 below are PLACEHOLDERS that DO NOT MATCH the actual TypeScript.** Real signatures (verified against `/workspace/web/src/app/components/new-project/new-project.component.ts`):
> - `generateSpecIndex()` — uses `this.projectName`, `this.CAPABILITY_SLUG()`, `this.TODAY()`. **No `filenames` argument** (the scaffold invented one).
> - `generateTimeline(tasks: {num, name, effort}[])` — needs the tasks array.
> - `generateReadme()` — uses `this.projectName`.
>
> Derived helpers `CAPABILITY_SLUG()` and `TODAY()` should be ported as Python helpers inside `generators.py` (slug from project_name, today from `datetime.date.today().isoformat()`).
>
> **HTTP route design issue:** `generate_timeline` needs a structured `tasks` list. Plain GET with repeated query keys is awkward for objects. Options: (a) `POST /api/templates/timeline` with JSON body `{project_name, tasks}`, (b) `GET` accepting `epic_content` and parsing tasks server-side, (c) `GET` with JSON-encoded tasks param. **Pick option (a)** — POST is the cleanest for structured input and matches the openapi.yaml convention used elsewhere. Adjust the openapi.yaml path block, the route handler, and the Angular caller accordingly. The other two endpoints (`spec-index`, `readme`) can remain GET since they need only `project_name`.

> **Container constraints:**
> - No `ssh`, no `gh`. Commit on a feature branch off **master**; do NOT push or open PR. The user does that separately.
> - Per-invocation git identity: `git -c user.email=sbedassa67@gmail.com -c user.name="bytesbysamu" commit ...` — co-author trailer `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`.
> - **Branch off master** (not off task/1 or task/2 — Tasks 1, 2, 3 are independent per architecture's execution flow).
> - **Pre-existing baseline failures on master:** 3 in `tests/test_retire_express.py` (host-path issues, unrelated). Treat as baseline, not blockers.
> - **Snapshot count baseline:** 7 on master (Task 2's 2 new snapshots are NOT yet on master). Add 4 → 11 expected after this task.
> - Karma/Angular UI smoke (Step 7's "Open browser" check) is **skipped** — no Chrome in container; rely on `npx tsc --noEmit` only for the Angular side.

---

## 2. Pre-flight

```bash
cd /workspace/api

# 1. Suite must be green before touching anything
make test
# Expected: all tests pass, 0 failures

# 2. Pin snapshot count — must not change unexpectedly after this task
pytest -m snapshot -v 2>&1 | grep -E "passed|failed|PASSED|FAILED"
# Note the number shown (e.g. "7 passed"). Add 3 after this task.

# 3. Confirm templates module does not exist
ls modules/templates/ 2>/dev/null && echo "EXISTS — STOP" || echo "Not present — OK"

# 4. Confirm syrupy is available
python -c "import syrupy; print('syrupy', syrupy.__version__)"

# 5. Confirm everyOpenapiPath structural test name
grep -n "everyOpenapiPath" tests/ -r
# Expected: at least one match naming the test
```

> **Blocker — read the Angular functions before writing any Python.** The generator bodies must be a semantically exact port of the TypeScript originals. Run this in a second terminal:
>
> ```bash
> cd /workspace/web
> grep -n "generateSpecIndex\|generateTimeline\|generateReadme" \
>   src/app/modules/editor/pages/new-project/new-project.component.ts
> ```
>
> Then read the full body of each function. Do not write `generators.py` until you have read all three. If the file is inaccessible, resolve access before proceeding — there is no correct port without the source.

---

## 3. Files

| File | Status | Notes |
|------|--------|-------|
| `modules/templates/__init__.py` | **new** | Empty package marker |
| `modules/templates/generators.py` | **new** | Three pure functions, ~80 lines |
| `modules/templates/routes.py` | **new** | `GET /api/templates/<name>` |
| `modules/templates/tests/__init__.py` | **new** | Empty |
| `modules/templates/tests/test_generators.py` | **new** | Unit tests |
| `modules/templates/tests/test_generators_snapshots.py` | **new** | Syrupy snapshot tests |
| `tests/test_templates.py` | **new** | HTTP route integration tests |
| `openapi.yaml` | **edit** | Add `/api/templates/{name}` path + `TemplateResponse` schema |
| `dtos/models.py` | **regenerated** | `make generate-dtos`; commit with `git add -f` |
| `create_app.py` | **edit** | Register `templates_bp` in `ENABLED_MODULES` |
| `/workspace/web/src/app/components/new-project/new-project.component.ts` | **edit** | Replace three inline functions with HTTP calls |

---

## 4. Implementation Steps

### Step 1 — Create the package skeleton

```bash
mkdir -p /workspace/api/modules/templates/tests
touch /workspace/api/modules/templates/__init__.py
touch /workspace/api/modules/templates/tests/__init__.py
```

Verify:
```bash
ls /workspace/api/modules/templates/
# Expected: __init__.py  tests/
```

---

### Step 2 — Write `modules/templates/generators.py`

> **⚠ VERIFY FIRST:** The bodies below are written from the project's structural context (spec files named `analysis.md`, `epic.md`, `architecture.md`, `spec-doc-spec.md`; timeline for task tracking; README as project entry point). Read the actual Angular functions before finalising — adjust any string content, heading names, or table columns to match the TypeScript exactly.

```python
# modules/templates/generators.py
"""Stateless markdown template generators.

Ported from new-project.component.ts: generateSpecIndex(), generateTimeline(),
generateReadme(). No I/O. No AI calls. Deterministic output.

IMPORTANT: Verify each function body against the Angular source before merging.
"""
from __future__ import annotations


def generate_spec_index(project_name: str, filenames: list[str]) -> str:
    """Return a spec-index.md table of contents for the given spec files.

    Port of new-project.component.ts:generateSpecIndex(). Verify body against
    Angular source.
    """
    if filenames:
        rows = "\n".join(f"| [{f}](./{f}) | |" for f in filenames)
    else:
        rows = "| _(no spec files yet)_ | |"
    return (
        f"# {project_name} — Spec Index\n\n"
        "| Document | Notes |\n"
        "|----------|-------|\n"
        f"{rows}\n"
    )


def generate_timeline(project_name: str) -> str:
    """Return a timeline.md task-tracking scaffold.

    Port of new-project.component.ts:generateTimeline(). Verify body against
    Angular source.
    """
    return (
        f"# {project_name} — Timeline\n\n"
        "| Task | Status | Notes |\n"
        "|------|--------|-------|\n"
    )


def generate_readme(project_name: str) -> str:
    """Return a README.md project entry point.

    Port of new-project.component.ts:generateReadme(). Verify body against
    Angular source.
    """
    return (
        f"# {project_name}\n\n"
        "A product specification generated with "
        "[Spec Doc](https://github.com/bytesbysamu/spec-doc).\n\n"
        "## Spec Documents\n\n"
        "- [Analysis](./analysis.md)\n"
        "- [Epic](./epic.md)\n"
        "- [Architecture](./architecture.md)\n\n"
        "## Timeline\n\n"
        "See [timeline.md](./timeline.md) for task status.\n"
    )
```

Verify (no I/O side effects, functions importable):
```bash
cd /workspace/api
python -c "
from modules.templates.generators import (
    generate_spec_index, generate_timeline, generate_readme
)
print(generate_readme('My Project'))
print('--- OK ---')
"
```

---

### Step 3 — Write unit tests and snapshot tests

**`modules/templates/tests/test_generators.py`:**

```python
# modules/templates/tests/test_generators.py
"""Unit tests for template generator functions.

Each test verifies a behavioural invariant that must hold regardless of exact
wording. Exact wording is locked by the companion snapshot tests.
"""
import pytest

from modules.templates.generators import (
    generate_spec_index,
    generate_timeline,
    generate_readme,
)


class TestGenerateSpecIndex:
    @pytest.mark.unit
    def test_projectNameInOutput(self):
        result = generate_spec_index("My Project", ["analysis.md"])
        assert "My Project" in result

    @pytest.mark.unit
    def test_filenamesAppearAsLinks(self):
        result = generate_spec_index("P", ["analysis.md", "epic.md"])
        assert "analysis.md" in result
        assert "epic.md" in result

    @pytest.mark.unit
    def test_emptyFilenamesList_returnsNonEmptyString(self):
        result = generate_spec_index("P", [])
        assert isinstance(result, str)
        assert len(result.strip()) > 0

    @pytest.mark.unit
    def test_returnsStr(self):
        assert isinstance(generate_spec_index("P", []), str)


class TestGenerateTimeline:
    @pytest.mark.unit
    def test_projectNameInOutput(self):
        result = generate_timeline("My Project")
        assert "My Project" in result

    @pytest.mark.unit
    def test_returnsStr(self):
        assert isinstance(generate_timeline("P"), str)

    @pytest.mark.unit
    def test_nonEmpty(self):
        assert len(generate_timeline("P").strip()) > 0


class TestGenerateReadme:
    @pytest.mark.unit
    def test_projectNameInOutput(self):
        result = generate_readme("My Project")
        assert "My Project" in result

    @pytest.mark.unit
    def test_returnsStr(self):
        assert isinstance(generate_readme("P"), str)

    @pytest.mark.unit
    def test_nonEmpty(self):
        assert len(generate_readme("P").strip()) > 0
```

**`modules/templates/tests/test_generators_snapshots.py`:**

```python
# modules/templates/tests/test_generators_snapshots.py
"""Snapshot tests for template generator functions.

Run:    pytest -m snapshot
Update: pytest -m snapshot --snapshot-update

Pin the full string output for stable representative inputs. Any future
wording change produces a visible, attributable diff against the golden.
"""
import pytest

from modules.templates.generators import (
    generate_spec_index,
    generate_timeline,
    generate_readme,
)

_PROJECT = "My Project"
_FILENAMES = ["analysis.md", "epic.md", "architecture.md"]


class TestGenerateSpecIndexSnapshot:
    @pytest.mark.snapshot
    def test_withFilenames_returnsStableMarkdown(self, snapshot):
        assert generate_spec_index(_PROJECT, _FILENAMES) == snapshot

    @pytest.mark.snapshot
    def test_emptyFilenames_returnsStableMarkdown(self, snapshot):
        assert generate_spec_index(_PROJECT, []) == snapshot


class TestGenerateTimelineSnapshot:
    @pytest.mark.snapshot
    def test_withProjectName_returnsStableMarkdown(self, snapshot):
        assert generate_timeline(_PROJECT) == snapshot


class TestGenerateReadmeSnapshot:
    @pytest.mark.snapshot
    def test_withProjectName_returnsStableMarkdown(self, snapshot):
        assert generate_readme(_PROJECT) == snapshot
```

Run to generate golden files (no golden yet — `--snapshot-update` is required on first run):

```bash
cd /workspace/api
pytest modules/templates/tests/test_generators_snapshots.py \
  -m snapshot --snapshot-update -v
# Expected: 4 snapshot(s) generated. 0 failed.
```

Then run without `--snapshot-update` to confirm goldens pass:

```bash
pytest modules/templates/tests/test_generators_snapshots.py -m snapshot -v
# Expected: 4 passed
```

Verify golden files were created:
```bash
ls modules/templates/tests/__snapshots__/
# Expected: test_generators_snapshots.ambr
```

---

### Step 4 — Add `TemplateResponse` to `openapi.yaml` and add `/api/templates/{name}` path

> **Do not run `make test` after this step and before Step 5.** The structural test `everyOpenapiPath_hasRouteHandler` will fail until the Flask route is registered in Step 5.

**Edit `openapi.yaml` — add schema** (append inside `components.schemas`, after the last schema entry before `responses:`):

```yaml
    TemplateResponse:
      type: object
      required: [content]
      properties:
        content:
          type: string
          description: Generated markdown string.
```

**Edit `openapi.yaml` — add path** (append inside `paths:`, after the last AI text path and before `components:`):

```yaml
  /api/templates/{name}:
    get:
      summary: Generate a named markdown template
      operationId: getTemplate
      parameters:
        - name: name
          in: path
          required: true
          schema:
            type: string
            enum: [spec-index, timeline, readme]
        - name: project_name
          in: query
          required: true
          schema:
            type: string
            minLength: 1
        - name: filenames
          in: query
          required: false
          style: form
          explode: true
          schema:
            type: array
            items:
              type: string
          description: >
            Spec filenames for the spec-index template (e.g. filenames=analysis.md&filenames=epic.md).
            Ignored for timeline and readme.
      responses:
        "200":
          description: Generated template markdown
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/TemplateResponse"
        "400":
          $ref: "#/components/responses/BadRequest"
        "404":
          $ref: "#/components/responses/NotFound"
```

After editing, regenerate DTOs immediately:

```bash
cd /workspace/api
make generate-dtos
# Expected: dtos/models.py updated with TemplateResponse class

grep "class TemplateResponse" dtos/models.py
# Expected: class TemplateResponse(BaseModel):
```

---

### Step 5 — Write `modules/templates/routes.py` and register blueprint

Write `modules/templates/routes.py`:

```python
# modules/templates/routes.py
"""Templates Blueprint — GET /api/templates/<name>.

Returns generated markdown for three named templates: spec-index, timeline,
readme. The route validates the name at the boundary; unknown names return 404.
Project name is required via query param; missing returns 400.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from dtos.models import TemplateResponse
from .generators import generate_spec_index, generate_timeline, generate_readme

logger = logging.getLogger(__name__)
templates_bp = Blueprint("templates", __name__)

_VALID = frozenset({"spec-index", "timeline", "readme"})


@templates_bp.get("/api/templates/<name>")
def get_template(name: str):
    if name not in _VALID:
        return jsonify({"error": f"Unknown template: {name!r}. Valid: spec-index, timeline, readme"}), 404

    project_name = (request.args.get("project_name") or "").strip()
    if not project_name:
        return jsonify({"error": "project_name query parameter is required"}), 400

    if name == "spec-index":
        filenames = request.args.getlist("filenames")
        content = generate_spec_index(project_name, filenames)
    elif name == "timeline":
        content = generate_timeline(project_name)
    else:  # readme
        content = generate_readme(project_name)

    logger.info("get_template name=%s project_name=%r", name, project_name)
    return jsonify(TemplateResponse(content=content).model_dump())
```

Register blueprint in `create_app.py` — add one line to `ENABLED_MODULES`:

```python
ENABLED_MODULES = [
    ('modules.projects.routes',  'projects_bp'),
    ('modules.context.routes',   'context_bp'),
    ('modules.ai.routes',        'ai_bp'),
    ('modules.templates.routes', 'templates_bp'),   # ← add this line
]
```

Now run `make test` — both the openapi path and its handler now exist:

```bash
cd /workspace/api
make test
# Expected: all tests pass (192 + new). everyOpenapiPath_hasRouteHandler must pass.
```

---

### Step 6 — Write HTTP route tests

**`tests/test_templates.py`:**

```python
# tests/test_templates.py
"""Integration tests for GET /api/templates/<name>.

Tests the HTTP boundary: status codes, response envelope shape, and parameter
validation. Generator output content is locked by snapshot tests in
modules/templates/tests/.
"""
import json
import pytest


@pytest.fixture()
def client():
    from create_app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c


@pytest.mark.unit
class TestGetTemplateValidation:
    def test_unknownName_returns404(self, client):
        r = client.get("/api/templates/bogus?project_name=Test")
        assert r.status_code == 404
        body = json.loads(r.data)
        assert "error" in body

    def test_missingProjectName_returns400(self, client):
        r = client.get("/api/templates/readme")
        assert r.status_code == 400
        body = json.loads(r.data)
        assert "error" in body

    def test_emptyProjectName_returns400(self, client):
        r = client.get("/api/templates/readme?project_name=")
        assert r.status_code == 400
        body = json.loads(r.data)
        assert "error" in body

    def test_whitespaceOnlyProjectName_returns400(self, client):
        r = client.get("/api/templates/readme?project_name=   ")
        assert r.status_code == 400
        body = json.loads(r.data)
        assert "error" in body


@pytest.mark.unit
class TestGetTemplateReadme:
    def test_validRequest_returns200WithContentKey(self, client):
        r = client.get("/api/templates/readme?project_name=My+Project")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "content" in body
        assert isinstance(body["content"], str)
        assert len(body["content"].strip()) > 0

    def test_projectNameAppearsInContent(self, client):
        r = client.get("/api/templates/readme?project_name=SpecialName")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "SpecialName" in body["content"]


@pytest.mark.unit
class TestGetTemplateTimeline:
    def test_validRequest_returns200WithContentKey(self, client):
        r = client.get("/api/templates/timeline?project_name=My+Project")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "content" in body
        assert isinstance(body["content"], str)
        assert len(body["content"].strip()) > 0

    def test_projectNameAppearsInContent(self, client):
        r = client.get("/api/templates/timeline?project_name=TimelineProject")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "TimelineProject" in body["content"]


@pytest.mark.unit
class TestGetTemplateSpecIndex:
    def test_validRequest_returns200WithContentKey(self, client):
        r = client.get(
            "/api/templates/spec-index"
            "?project_name=My+Project"
            "&filenames=analysis.md"
            "&filenames=epic.md"
        )
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "content" in body
        assert isinstance(body["content"], str)

    def test_filenamesAppearInContent(self, client):
        r = client.get(
            "/api/templates/spec-index"
            "?project_name=P"
            "&filenames=analysis.md"
            "&filenames=epic.md"
        )
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "analysis.md" in body["content"]
        assert "epic.md" in body["content"]

    def test_noFilenames_returns200(self, client):
        r = client.get("/api/templates/spec-index?project_name=P")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "content" in body
        assert len(body["content"].strip()) > 0
```

Run the new tests:

```bash
cd /workspace/api
pytest tests/test_templates.py -v
# Expected: 11 passed
```

---

### Step 7 — Update Angular component

> **Read the Angular file before editing.** The exact lines to remove and the call site context depend on the actual TypeScript.

In `/workspace/web/src/app/components/new-project/new-project.component.ts`:

**Remove** the three private methods `generateSpecIndex()`, `generateTimeline()`, and `generateReadme()` entirely.

**Replace** each call site. The three functions are called during project bootstrap, producing files that are then included in `POST /api/projects`. Replace each local call with an HTTP GET to the new endpoint. The Angular `HttpClient` call pattern:

```typescript
// For readme — add to imports: import { lastValueFrom } from 'rxjs';
private async fetchTemplate(name: string, extraParams: Record<string, string> = {}): Promise<string> {
  const params = new HttpParams({ fromObject: { project_name: this.projectName, ...extraParams } });
  const res = await lastValueFrom(
    this.http.get<{ content: string }>(`/api/templates/${name}`, { params })
  );
  return res.content;
}
```

Then replace the three inline calls:

```typescript
// BEFORE (example shape — verify against actual code)
const specIndex = this.generateSpecIndex(name, filenames);
const timeline  = this.generateTimeline(name);
const readme    = this.generateReadme(name);

// AFTER
const [specIndex, timeline, readme] = await Promise.all([
  this.fetchTemplate('spec-index', {
    filenames: filenames  // adjust if HttpParams expects repeated keys differently
  }),
  this.fetchTemplate('timeline'),
  this.fetchTemplate('readme'),
]);
```

> **Note on `filenames` array serialisation:** Angular `HttpParams` with an array value sends repeated keys (`filenames=a.md&filenames=b.md`), which matches Flask's `request.args.getlist('filenames')`. Verify this produces the correct query string in the browser's network tab.

Build check:

```bash
cd /workspace/web
npm run build 2>&1 | tail -20
# Expected: Build at ... complete. 0 errors.
```

---

## 5. Tests

All test files are written in Steps 3 and 6. Summary of assertions:

| File | Marker | Count | What it proves |
|------|--------|-------|----------------|
| `modules/templates/tests/test_generators.py` | `unit` | 10 | Each function returns a non-empty `str`; project name and filenames appear in output |
| `modules/templates/tests/test_generators_snapshots.py` | `snapshot` | 4 | Exact markdown format is locked; any wording change breaks the golden |
| `tests/test_templates.py` | `unit` | 11 | HTTP boundary: 400 on missing params, 404 on unknown name, 200 + `content` key on valid requests |

Run all three groups:

```bash
cd /workspace/api

# Unit tests
pytest modules/templates/tests/test_generators.py tests/test_templates.py -m unit -v
# Expected: 21 passed

# Snapshot tests
pytest modules/templates/tests/test_generators_snapshots.py -m snapshot -v
# Expected: 4 passed (goldens already generated in Step 3)

# Full suite
make test
# Expected: all tests pass
```

---

## 6. Commit Plan

Three commits; no `master` direct push — open a PR.

**Commit 1 — generators + tests** (no route, no openapi change; `make test` passes)

```bash
cd /workspace/api
git add modules/templates/__init__.py \
        modules/templates/generators.py \
        modules/templates/tests/__init__.py \
        modules/templates/tests/test_generators.py \
        modules/templates/tests/test_generators_snapshots.py \
        modules/templates/tests/__snapshots__/test_generators_snapshots.ambr

make test  # must be green before committing

git commit -m "feat(templates): add generate_spec_index/timeline/readme pure functions

Port three markdown generators from new-project.component.ts to
modules/templates/generators.py. Stateless, no I/O. Locked by
4 syrupy snapshot tests.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

**Commit 2 — OpenAPI + route + DTO + blueprint registration** (atomic; `everyOpenapiPath_hasRouteHandler` passes)

```bash
cd /workspace/api
git add openapi.yaml \
        modules/templates/routes.py \
        create_app.py \
        tests/test_templates.py
git add -f dtos/models.py   # generated file requires -f

make test  # must be green before committing

git commit -m "feat(templates): expose GET /api/templates/<name> endpoint

Single parameterised route replaces three would-be individual routes.
Validates name against frozenset; 400 on missing project_name; 404 on
unknown name. openapi.yaml updated and DTOs regenerated.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

**Commit 3 — Angular component** (in `/workspace/web` repo)

```bash
cd /workspace/web
git add src/app/modules/editor/pages/new-project/new-project.component.ts
npm run build  # must compile clean before committing

git commit -m "refactor(new-project): replace inline template generators with /api/templates calls

Removes generateSpecIndex, generateTimeline, generateReadme from the
component. Each is now a GET /api/templates/<name> call, keeping
markdown generation server-side and snapshot-testable.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 7. Verification

```bash
# 1. Full Flask suite green
cd /workspace/api
make test
# Expected: all tests pass; route count in everyOpenapiPath test reflects 22 paths

# 2. Snapshot count increased by 4
pytest -m snapshot -v 2>&1 | grep -E "passed"
# Expected: (pre-task count + 4) passed

# 3. Route is reachable with the dev server running
make dev &
sleep 2
curl -s "http://localhost:3101/api/templates/readme?project_name=Smoke+Test" | python -m json.tool
# Expected: { "content": "# Smoke Test\n..." }

curl -s "http://localhost:3101/api/templates/bogus?project_name=X" | python -m json.tool
# Expected: { "error": "Unknown template: 'bogus'..." }, HTTP 404

curl -s "http://localhost:3101/api/templates/readme" | python -m json.tool
# Expected: { "error": "project_name query parameter is required" }, HTTP 400

# 4. DTO is in sync
make check-dtos
# Expected: exits 0

# 5. Angular build clean (no TypeScript errors)
cd /workspace/web
npm run build 2>&1 | grep -E "error|Error" | grep -v "^$"
# Expected: no output (zero errors)

# 6. Smoke the Angular dev server
npm start &
sleep 5
# Open http://localhost:4201 and trigger the new-project bootstrap flow.
# Observe that spec-index.md, timeline.md, and readme.md are created.
# Confirm network tab shows GET /api/templates/... calls (not local generation).
```

---

## 8. Rollback

If the Flask changes break the suite before commit:

```bash
cd /workspace/api
git checkout -- openapi.yaml create_app.py dtos/models.py
rm -rf modules/templates/
rm -f tests/test_templates.py
make generate-dtos  # restore dtos/models.py to pre-task state
make test           # must return green
```

If committed and needs reverting:

```bash
cd /workspace/api
git revert HEAD~2..HEAD   # reverts commit 1 and commit 2
make generate-dtos        # restore dtos from openapi.yaml
make test
```

For the Angular commit (separate repo):

```bash
cd /workspace/web
git revert HEAD
npm run build
```

---

## 9. Deviations Allowed

| What | Constraint |
|------|-----------|
| **Generator function signatures** | The three function signatures may need additional parameters (e.g. `generate_timeline(project_name, tasks)`) if the Angular source passes more than `project_name`. Adjust `generators.py`, the route query-param parsing, the openapi.yaml parameters block, and the Angular HTTP call together. Re-run `--snapshot-update` if signatures change. |
| **`filenames` serialisation in Angular** | If `HttpParams` does not send repeated keys correctly, switch to comma-separated: `?filenames=a.md,b.md` and change `request.args.getlist('filenames')` to `request.args.get('filenames', '').split(',')`. Update `openapi.yaml` schema style/explode accordingly. |
| **Snapshot golden content** | The `.ambr` files are generated by `--snapshot-update` and will reflect the actual Python string output. Their content is not prescribed here — they are whatever the pure functions produce after the Angular port is complete. |
| **Angular `fetchTemplate` helper placement** | The helper method may live inline in the call site, in a private method, or in a new `TemplateService`. Any placement is acceptable as long as the three local generator methods are fully removed. |

---

## 10. Out of Scope

| Topic | Reason |
|-------|--------|
| Jinja2 or any templating engine | Architecture decision: f-string concatenation is sufficient at this scale and avoids a new dependency |
| User-customisable template variables (slot substitution) | Explicitly deferred — "a second-consumer concern" per the epic. No user has asked for them. |
| `TemplateService` as a standalone Angular service | The task targets the component. A dedicated service is appropriate only when a second Angular caller for the same endpoint appears. |
| POST endpoint for templates | GET is correct — generators are pure functions with no side effects; idempotent retrieval. |
| Task 4 bootstrap integration | Task 4 calls the generators directly via Python import, not via the HTTP route. That wiring is Task 4's concern. |
| Angular E2E or Cypress tests | No E2E test infrastructure has been identified as in scope for this epic. |
| `modules/templates/errors.py` | No I/O in the generators; the only errors at the route boundary are 400 and 404, both handled inline. |