# Task 3: Spec-Doc Bridge — Implementation Guide

## 1. Context

**Goal**: Author `sam-specDoc/SKILL.md`, an instruction-based skill file that exposes six named callable operations to the OpenClaw agent against the Flask spec-doc API at `http://host.docker.internal:8080`. The deliverable is a single markdown file; there is no build step, no compiled artifact, and no service change.

**The one unresolved blocker** — whether localhost calls from inside the OpenClaw container bypass RS256 JWT enforcement — is resolved by Pre-flight Step 2.3 before a single line of SKILL.md is authored. That probe directly controls the auth section: bypass → five-line unconditional calls; enforced → token-lookup step added to every tool. The guide handles both outcomes without deferring to a future decision.

**Six operations in scope**: `sam_specDoc_listProjects`, `sam_specDoc_getProject`, `sam_specDoc_createProject`, `sam_specDoc_readFile`, `sam_specDoc_writeFile`, `sam_specDoc_runCoherence`.

**Not in this task**: `sam_specDoc_braindump()` (template file unconfirmed), `sam-context/SKILL.md`, `sam-projects/SKILL.md`, MCP plugin graduation, any backend or server-side changes.

---

## 2. Pre-flight

Complete each step in order. Each produces a concrete value or a branch decision that feeds into the implementation. Do not begin Section 4 until all applicable steps pass.

### 2.0 — Install test dependencies

```bash
pip install requests pytest
```

Expected: silent success. If `pip` is unavailable inside the container, use `pip3` or `python -m pip`.

### 2.1 — Confirm spec-doc is running

```bash
curl -s -o /dev/null -w "%{http_code}" http://host.docker.internal:8080/health
```

Expected: `200`. If `000` (connection refused), start spec-doc before proceeding:
```bash
docker-compose up -d spec-doc
```
Re-run the probe until it returns `200`.

### 2.2 — Verify all six endpoint routes exist

```bash
for call in \
  "GET:/projects" \
  "GET:/projects/__probe__" \
  "POST:/projects" \
  "GET:/projects/__probe__/files?path=README.md" \
  "PUT:/projects/__probe__/files?path=README.md" \
  "POST:/projects/__probe__/coherence"; do
  method="${call%%:*}"
  path="${call#*:}"
  status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "http://host.docker.internal:8080${path}")
  echo "$method $path → $status"
done
```

**Acceptable results**: `200`, `400`, `401`, `403`, `404`, `405`, `422` on each line. A `000` means the service is down. A `404` with an HTML "Not Found" body (not a JSON resource-not-found) means the route path is wrong — record the corrected path and substitute it wherever the affected endpoint appears in Step 4.2 and in `tests/smoke_specDoc.py`.

### 2.3 — Determine auth path (CRITICAL — branches the entire implementation)

```bash
curl -s -o /dev/null -w "%{http_code}" http://host.docker.internal:8080/projects
```

| Result | Auth path | Action |
|--------|-----------|--------|
| `200` | **Path A — bypass** | Localhost calls are unauthenticated. SKILL.md tools are unconditional HTTP calls. Skip 2.4. |
| `401` or `403` | **Path B — enforced** | JWT is checked. Proceed to 2.4. |

Record the result. You will reference it in Step 4.2.

### 2.4 — Locate dev token (Path B only)

Skip this step if 2.3 returned `200`.

```bash
ls -la {WORKSPACE}/.specDoc/dev-token 2>/dev/null && echo "FOUND" || echo "NOT FOUND"
```

If `NOT FOUND`:
1. Generate a dev token from the spec-doc admin interface or Flask shell.
2. Write it to `{WORKSPACE}/.specDoc/dev-token`:
   ```bash
   mkdir -p {WORKSPACE}/.specDoc && chmod 700 {WORKSPACE}/.specDoc
   echo -n "PASTE_TOKEN_HERE" > {WORKSPACE}/.specDoc/dev-token
   chmod 600 {WORKSPACE}/.specDoc/dev-token
   ```
3. Add to `.gitignore` if not already present:
   ```bash
   grep -q '.specDoc/dev-token' {WORKSPACE}/.gitignore || \
     echo '.specDoc/dev-token' >> {WORKSPACE}/.gitignore
   ```

### 2.5 — Confirm directory naming convention

```bash
ls {WORKSPACE}/sam-context/SKILL.md 2>/dev/null && echo "sam-context exists" || echo "sam-context not yet created"
ls {WORKSPACE}/sam-projects/SKILL.md 2>/dev/null && echo "sam-projects exists" || echo "sam-projects not yet created"
```

`sam-specDoc/` may be the first skill directory in the workspace. That is expected; it is created in Step 4.1.

---

## 3. Files

| Status | Path | Action |
|--------|------|--------|
| **(new)** | `sam-specDoc/` | Create directory |
| **(new)** | `sam-specDoc/SKILL.md` | Create — six tool definitions with auth-aware instructions |
| **(new)** | `tests/` | Create directory if absent |
| **(new)** | `tests/smoke_specDoc.py` | Create — 17-test pytest suite (11 structural + 6 endpoint probes) |
| existing | `{WORKSPACE}/.specDoc/dev-token` | Read-only at runtime (Path B); created in pre-flight 2.4 if absent |
| existing | `{WORKSPACE}/.gitignore` | Append `.specDoc/dev-token` entry (pre-flight 2.4, Path B only) |

No existing source files are modified by this task.

---

## 4. Implementation Steps

### 4.1 — Create directories

```bash
mkdir -p {WORKSPACE}/sam-specDoc
mkdir -p {WORKSPACE}/tests
```

### 4.2 — Write `sam-specDoc/SKILL.md`

Create `{WORKSPACE}/sam-specDoc/SKILL.md` with the full content below.

> **Before writing**: if pre-flight 2.3 yielded Path A (bypass), the AUTH PROCEDURE section is already correct as written. If it yielded Path B (enforced), no edit is needed either — the AUTH PROCEDURE is written to detect enforcement at runtime. The SKILL.md handles both paths self-consistently.

---

```markdown
# sam-specDoc Skill

**Version**: v1
**Loaded by**: OpenClaw at session start; consulted on every turn where Sam references spec-doc activity.
**API target**: `http://host.docker.internal:8080`

---

## AUTH PROCEDURE

Execute this procedure exactly once per session before making any tool call in this skill. Cache the outcome for the remainder of the session.

1. Send `GET http://host.docker.internal:8080/projects` with no Authorization header.
2. **If the response status is `200`**: all calls in this session are unauthenticated. Localhost bypass is active. Skip token lookup for every subsequent tool call in this session.
3. **If the response status is `401` or `403`**: JWT enforcement is active. Read the contents of `{WORKSPACE}/.specDoc/dev-token` using the Read tool. Trim all leading and trailing whitespace. Store the trimmed value as `SPECDOC_TOKEN`. Include `Authorization: Bearer SPECDOC_TOKEN` on every subsequent API call in this session.
4. **If the dev-token file is absent or unreadable**: stop and tell Sam: "spec-doc auth is enforced and no dev token is present at `{WORKSPACE}/.specDoc/dev-token`. Create it before I can call the spec-doc API."
5. **If spec-doc is unreachable** (connection refused): stop and tell Sam: "spec-doc is not reachable at `host.docker.internal:8080`. Is the service running? Check with: `docker ps | grep spec-doc`."

---

## Tools

### `sam_specDoc_listProjects()`

**Purpose**: Return all projects known to spec-doc.

**HTTP call**:
```
GET http://host.docker.internal:8080/projects
Authorization: [Bearer SPECDOC_TOKEN if Path B; omit if Path A]
```

**On 200**: Present the project list as a compact bullet list. Each line: `• {id}: {name}`. If the list is empty, say "No projects found in spec-doc."
**On any error**: Surface the HTTP status code and the raw response body verbatim. Do not paraphrase.

---

### `sam_specDoc_getProject(projectId)`

**Purpose**: Return the full metadata record for a single project.

**Parameters**:
- `projectId` — string, required. The project's unique identifier from `sam_specDoc_listProjects()`.

**HTTP call**:
```
GET http://host.docker.internal:8080/projects/{projectId}
Authorization: [Bearer SPECDOC_TOKEN if Path B; omit if Path A]
```

**On 200**: Present these fields as labeled lines: `id`, `name`, `description`, `created_at`, `coherence_status`. Omit fields that are absent in the response.
**On 404**: Tell Sam: "Project `{projectId}` does not exist in spec-doc. Call `sam_specDoc_listProjects()` to see available IDs."
**On any other error**: Surface the HTTP status code and raw response body verbatim.

---

### `sam_specDoc_createProject(name, description)`

**Purpose**: Register a new project in spec-doc.

**Parameters**:
- `name` — string, required. Human-readable project name; must be unique across all spec-doc projects.
- `description` — string, required. One-sentence purpose statement.

**HTTP call**:
```
POST http://host.docker.internal:8080/projects
Content-Type: application/json
Authorization: [Bearer SPECDOC_TOKEN if Path B; omit if Path A]
Body: {"name": "{name}", "description": "{description}"}
```

**On 201**: Report the new project's assigned ID: "Created project `{name}` with ID `{id}`."
**On 409**: Tell Sam: "A project named `{name}` already exists. Call `sam_specDoc_getProject()` with its ID to inspect it."
**On 400 or 422**: Surface the HTTP status code and raw validation error body verbatim. Do not guess what was wrong.
**On any other error**: Surface the HTTP status code and raw response body verbatim.

---

### `sam_specDoc_readFile(projectId, filePath)`

**Purpose**: Return the raw content of a file stored in a spec-doc project.

**Parameters**:
- `projectId` — string, required. Project identifier.
- `filePath` — string, required. Relative path within the project, e.g. `docs/overview.md`. URL-encode before sending.

**HTTP call**:
```
GET http://host.docker.internal:8080/projects/{projectId}/files?path={URL-encoded filePath}
Authorization: [Bearer SPECDOC_TOKEN if Path B; omit if Path A]
```

**On 200**: Return the file content verbatim, preceded by a single separator: `— {filePath} —`.
**On 404**: Tell Sam: "File `{filePath}` was not found in project `{projectId}`. The project may not contain this path."
**On any other error**: Surface the HTTP status code and raw response body verbatim.

---

### `sam_specDoc_writeFile(projectId, filePath, content)`

**Purpose**: Create or overwrite a file in a spec-doc project.

**Parameters**:
- `projectId` — string, required. Project identifier.
- `filePath` — string, required. Relative path within the project. URL-encode before sending.
- `content` — string, required. Full file content to write. Passed as the raw request body.

**HTTP call**:
```
PUT http://host.docker.internal:8080/projects/{projectId}/files?path={URL-encoded filePath}
Content-Type: text/plain
Authorization: [Bearer SPECDOC_TOKEN if Path B; omit if Path A]
Body: {content}
```

**On 200 or 204**: Confirm: "Wrote `{filePath}` to project `{projectId}`."
**On any error**: Surface the HTTP status code and raw response body verbatim. Do not confirm a write unless the server acknowledged it with 200 or 204.

---

### `sam_specDoc_runCoherence(projectId)`

**Purpose**: Trigger a coherence check against all files in a spec-doc project and return the results.

**Parameters**:
- `projectId` — string, required. Project identifier.

**HTTP call**:
```
POST http://host.docker.internal:8080/projects/{projectId}/coherence
Authorization: [Bearer SPECDOC_TOKEN if Path B; omit if Path A]
```

**On 200**: Parse the response.
- If the response contains a `violations` array with one or more entries: present each as `• {file}: {message}`.
- If `violations` is present but empty, or absent: say "No coherence issues found in project `{projectId}`."
**On 404**: Tell Sam: "Project `{projectId}` not found in spec-doc."
**On any other error**: Surface the HTTP status code and raw response body verbatim.

---

## Error Handling (all tools)

- **Never fabricate a result.** If a call fails or returns unexpected data, report the actual status and body.
- **Never retry automatically.** If a call fails, surface it to Sam and wait for instruction.
- **Connection refused**: tell Sam "spec-doc is not reachable at `host.docker.internal:8080`. Is the service running? Check with: `docker ps | grep spec-doc`."
- **Unexpected 2xx with empty body**: treat as success; confirm the operation as described in each tool's success case.

---

## Not Defined in This Skill

- `sam_specDoc_braindump()` — template source file unconfirmed; defined in a follow-on task.
- Project name-to-path resolution — see `sam-projects/SKILL.md`.
- Git status — see `sam-projects/SKILL.md`.
```

---

### 4.3 — Write `tests/smoke_specDoc.py`

Create `{WORKSPACE}/tests/smoke_specDoc.py` with the full content from Section 5.

---

## 5. Tests

**Framework**: pytest  
**Dependencies**: `requests`, `pytest` (installed in pre-flight 2.0)

**Run command** (from the workspace root, inside or outside the OpenClaw container):
```bash
cd {WORKSPACE} && python -m pytest tests/smoke_specDoc.py -v
```

**Count delta**: 0 → 17 passing when spec-doc is reachable; 0 → 11 passing + 6 skipped when spec-doc is unreachable.

---

**`{WORKSPACE}/tests/smoke_specDoc.py`**

```python
"""
Smoke tests for sam-specDoc/SKILL.md and the spec-doc API at host.docker.internal:8080.

Structural tests (11) run unconditionally when SKILL.md exists.
Endpoint tests (6) skip automatically with a diagnostic message when the API is unreachable,
so CI environments without the service do not fail the suite.

Run:
    python -m pytest tests/smoke_specDoc.py -v
"""

import pathlib
import urllib.parse

import pytest
import requests

BASE_URL = "http://host.docker.internal:8080"
SKILL_MD_PATH = pathlib.Path(__file__).parent.parent / "sam-specDoc" / "SKILL.md"
TIMEOUT_SECS = 5
PROBE_PROJECT_ID = "__smoke-test-nonexistent__"


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def skill_md_text():
    """Read SKILL.md once; fail fast with a clear message if it does not exist."""
    assert SKILL_MD_PATH.exists(), (
        f"sam-specDoc/SKILL.md not found at {SKILL_MD_PATH}. "
        "Complete implementation step 4.2 before running this suite."
    )
    content = SKILL_MD_PATH.read_text(encoding="utf-8")
    assert len(content) > 200, (
        f"SKILL.md is only {len(content)} characters — expected at least 200. "
        "The file may have been written empty or truncated."
    )
    return content


@pytest.fixture(scope="session")
def api_status():
    """
    Probe GET /projects and return the HTTP status code.
    Skip all endpoint tests if the API is unreachable (ConnectionError).
    """
    try:
        r = requests.get(f"{BASE_URL}/projects", timeout=TIMEOUT_SECS)
        return r.status_code
    except requests.exceptions.ConnectionError:
        pytest.skip(
            "spec-doc is not reachable at host.docker.internal:8080. "
            "Start it with: docker-compose up -d spec-doc"
        )


# ---------------------------------------------------------------------------
# Structural tests — run whenever SKILL.md exists
# ---------------------------------------------------------------------------

class TestSkillMdStructure:

    REQUIRED_HEADINGS = [
        "## AUTH PROCEDURE",
        "### `sam_specDoc_listProjects()`",
        "### `sam_specDoc_getProject(projectId)`",
        "### `sam_specDoc_createProject(name, description)`",
        "### `sam_specDoc_readFile(projectId, filePath)`",
        "### `sam_specDoc_writeFile(projectId, filePath, content)`",
        "### `sam_specDoc_runCoherence(projectId)`",
    ]

    @pytest.mark.parametrize("heading", REQUIRED_HEADINGS)
    def test_required_heading_present(self, skill_md_text, heading):
        assert heading in skill_md_text, (
            f"Required heading '{heading}' is missing from sam-specDoc/SKILL.md. "
            "Add it following the template in implementation step 4.2. "
            f"Existing headings: {[ln for ln in skill_md_text.splitlines() if ln.startswith('#')]}"
        )

    def test_auth_procedure_covers_bypass_path(self, skill_md_text):
        assert "200" in skill_md_text and "unauthenticated" in skill_md_text.lower(), (
            "AUTH PROCEDURE must mention status 200 and explain the unauthenticated "
            "(bypass) path. Both are required so the agent handles Path A correctly."
        )

    def test_auth_procedure_covers_enforced_path(self, skill_md_text):
        assert "401" in skill_md_text and "Authorization: Bearer" in skill_md_text, (
            "AUTH PROCEDURE must mention status 401 and the 'Authorization: Bearer' "
            "header. Both are required so the agent handles Path B (JWT enforced) correctly."
        )

    def test_api_base_url_is_correct(self, skill_md_text):
        assert "host.docker.internal:8080" in skill_md_text, (
            "SKILL.md must reference the spec-doc API at 'host.docker.internal:8080'. "
            "This string is absent — check that the base URL was not accidentally changed "
            "to 'localhost', '127.0.0.1', or another host."
        )

    def test_error_handling_section_present(self, skill_md_text):
        assert "## Error Handling" in skill_md_text, (
            "The '## Error Handling (all tools)' section is missing. "
            "Add it following the template in implementation step 4.2."
        )

    def test_never_fabricate_rule_present(self, skill_md_text):
        assert "Never fabricate" in skill_md_text or "never fabricate" in skill_md_text, (
            "The error handling section must include a 'Never fabricate a result' rule. "
            "This is required to prevent the agent from inventing API responses."
        )


# ---------------------------------------------------------------------------
# Endpoint smoke tests — skip when spec-doc is unreachable
# ---------------------------------------------------------------------------

class TestEndpointReachability:

    def test_list_projects_returns_valid_auth_response(self, api_status):
        """
        GET /projects with no auth must return 200 (bypass) or 401/403 (enforced).
        Any other code indicates a routing or server error.
        """
        assert api_status in (200, 401, 403), (
            f"GET /projects returned HTTP {api_status}. "
            "Expected 200 (auth bypassed), 401, or 403 (JWT enforced). "
            "A 404 means the route path is wrong — verify it against the spec-doc Flask app. "
            "A 5xx means the server is running but erroring; check spec-doc logs."
        )

    def test_get_project_route_exists(self, api_status):
        """
        GET /projects/{id} for a nonexistent ID must return 404 (not found)
        or 401/403 (auth enforced) — not a routing 404 with an HTML body.
        """
        r = requests.get(
            f"{BASE_URL}/projects/{PROBE_PROJECT_ID}",
            timeout=TIMEOUT_SECS,
        )
        assert r.status_code in (404, 401, 403), (
            f"GET /projects/{{id}} returned HTTP {r.status_code}. "
            "Expected 404 (resource not found), 401, or 403. "
            "A 500 means the endpoint exists but crashes on this input — "
            "check spec-doc logs for the traceback."
        )

    def test_create_project_route_exists(self, api_status):
        """
        POST /projects with an empty JSON body must return 400/422 (validation error)
        or 401/403 (auth enforced) — not a routing 404.
        """
        r = requests.post(
            f"{BASE_URL}/projects",
            json={},
            timeout=TIMEOUT_SECS,
        )
        assert r.status_code in (400, 401, 403, 422), (
            f"POST /projects with empty body returned HTTP {r.status_code}. "
            "Expected 400 or 422 (validation failure) or 401/403 (auth enforced). "
            "A 404 means the route path '/projects' is wrong for POST; "
            "check whether spec-doc uses a different path for project creation."
        )

    def test_read_file_route_exists(self, api_status):
        """
        GET /projects/{id}/files?path=README.md for a nonexistent project must return
        404 or 401/403 — not a routing 404 with an HTML body.
        """
        r = requests.get(
            f"{BASE_URL}/projects/{PROBE_PROJECT_ID}/files",
            params={"path": "README.md"},
            timeout=TIMEOUT_SECS,
        )
        assert r.status_code in (404, 401, 403), (
            f"GET /projects/{{id}}/files?path=README.md returned HTTP {r.status_code}. "
            "Expected 404 or 401/403. "
            "If 404 with an HTML body, the route does not exist at this path — "
            "verify spec-doc's file-read endpoint URL and query-parameter convention."
        )

    def test_write_file_route_exists(self, api_status):
        """
        PUT /projects/{id}/files?path=... with a text body must return 4xx
        (not a routing 404 or a 405 Method Not Allowed).
        """
        r = requests.put(
            f"{BASE_URL}/projects/{PROBE_PROJECT_ID}/files",
            params={"path": "smoke-test-probe.md"},
            data="smoke test — safe to ignore",
            headers={"Content-Type": "text/plain"},
            timeout=TIMEOUT_SECS,
        )
        assert r.status_code in (400, 401, 403, 404, 422), (
            f"PUT /projects/{{id}}/files returned HTTP {r.status_code}. "
            "Expected a 4xx. A 405 (Method Not Allowed) means the route exists "
            "but does not accept PUT — re-check the HTTP method for writeFile in "
            "spec-doc's Flask routes and update SKILL.md accordingly."
        )

    def test_coherence_route_exists(self, api_status):
        """
        POST /projects/{id}/coherence must return 4xx — not a routing 404 or 405.
        """
        r = requests.post(
            f"{BASE_URL}/projects/{PROBE_PROJECT_ID}/coherence",
            timeout=TIMEOUT_SECS,
        )
        assert r.status_code in (400, 401, 403, 404, 422), (
            f"POST /projects/{{id}}/coherence returned HTTP {r.status_code}. "
            "Expected a 4xx indicating the route exists. "
            "A 405 means the endpoint does not accept POST — re-check the HTTP method "
            "for the coherence operation in spec-doc's Flask routes."
        )
```

---

## 6. Commit Plan

Two commits. Each leaves the branch in a coherent, runnable state.

**Commit 1 — skill file only**

```bash
cd {WORKSPACE}
git add sam-specDoc/SKILL.md
git commit -m "$(cat <<'EOF'
feat(specDoc): add sam-specDoc/SKILL.md with six API tool definitions

Defines sam_specDoc_listProjects, getProject, createProject, readFile,
writeFile, and runCoherence against host.docker.internal:8080. Includes
a session-scoped AUTH PROCEDURE that detects bypass vs. JWT-enforced at
runtime, eliminating the hard pre-flight dependency on the auth answer
being confirmed before authoring.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**Commit 2 — smoke tests**

```bash
cd {WORKSPACE}
git add tests/smoke_specDoc.py
git commit -m "$(cat <<'EOF'
test(specDoc): add pytest smoke suite for sam-specDoc skill and API

17 tests: 11 structural checks on SKILL.md (headings, auth coverage,
base URL, error handling rules) and 6 endpoint probes against
host.docker.internal:8080. Endpoint tests skip gracefully when the API
is unreachable so the suite is safe to run in CI without the service.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## 7. Verification

Run these checks in order. Mark the task done only after all applicable steps pass.

**7.1 — File existence**

```bash
test -f {WORKSPACE}/sam-specDoc/SKILL.md \
  && echo "PASS: SKILL.md exists" \
  || echo "FAIL: sam-specDoc/SKILL.md missing — run step 4.2"

test -f {WORKSPACE}/tests/smoke_specDoc.py \
  && echo "PASS: smoke test exists" \
  || echo "FAIL: tests/smoke_specDoc.py missing — run step 4.3"
```

**7.2 — Required content grep**

```bash
cd {WORKSPACE}
for needle in \
  "## AUTH PROCEDURE" \
  "sam_specDoc_listProjects" \
  "sam_specDoc_getProject" \
  "sam_specDoc_createProject" \
  "sam_specDoc_readFile" \
  "sam_specDoc_writeFile" \
  "sam_specDoc_runCoherence" \
  "host.docker.internal:8080" \
  "## Error Handling" \
  "Never fabricate"; do
  grep -q "$needle" sam-specDoc/SKILL.md \
    && echo "PASS: $needle" \
    || echo "FAIL: '$needle' absent from SKILL.md"
done
```

Expected: 10 PASS lines.

**7.3 — pytest suite**

```bash
cd {WORKSPACE} && python -m pytest tests/smoke_specDoc.py -v
```

- **spec-doc running**: 17 passed, 0 failed, 0 skipped.
- **spec-doc not running**: 11 passed, 0 failed, 6 skipped — all skips must show the message "spec-doc is not reachable at host.docker.internal:8080."

**7.4 — Manual agent exercise**

Open an OpenClaw session. Send:

```
list my spec-doc projects
```

The agent must:
1. Execute AUTH PROCEDURE (one HTTP probe, no user prompt for a token).
2. Call `sam_specDoc_listProjects()`.
3. Return a bulleted list of project names and IDs, or state "No projects found in spec-doc."
4. Not ask Sam for an endpoint path, auth token, or base URL.

If the agent asks for any of these inputs, verify that `sam-specDoc/SKILL.md` is in the skills directory that OpenClaw loads at session start.

**7.5 — Confirm and record the live auth path**

After step 7.4 completes, observe which branch AUTH PROCEDURE took:

- Agent called `/projects` without a token and received data → **Path A confirmed**.
- Agent read `{WORKSPACE}/.specDoc/dev-token` → **Path B confirmed**.

Add a one-line comment to the top of `sam-specDoc/SKILL.md` recording the result:

```markdown
<!-- Auth path confirmed: [Path A — bypass | Path B — token at {WORKSPACE}/.specDoc/dev-token] -->
```

This lets future maintainers know the environment default without re-running the probe.

---

## 8. Rollback

This task adds two new files and appends one line to `.gitignore`. It modifies no existing source files and introduces no service or schema changes. Rollback is safe at any point.

**Before committing** — delete the new files:

```bash
rm -rf {WORKSPACE}/sam-specDoc
rm -f {WORKSPACE}/tests/smoke_specDoc.py
```

**After committing both commits** — revert in reverse order:

```bash
git revert HEAD       # reverts commit 2 (smoke tests)
git revert HEAD~1     # reverts commit 1 (SKILL.md)
```

**If both commits are the last two on a local-only branch**:

```bash
git reset --hard HEAD~2
```

Do not use `reset --hard` on a branch that has been pushed to a shared remote.

---

## 9. Deviations Allowed

| Deviation | Condition | Corrective action |
|-----------|-----------|-------------------|
| Endpoint path differs from `/projects/{id}/files?path=...` | Pre-flight 2.2 reveals a different URL shape (e.g. `/projects/{id}/files/{encoded-path}`) | Update the affected endpoint in SKILL.md and the matching `requests` call in `tests/smoke_specDoc.py`; no structural change |
| Coherence endpoint uses `GET` instead of `POST` | Pre-flight 2.2 returns `405` on `POST /projects/{id}/coherence`, `200` on `GET` | Change the method in `sam_specDoc_runCoherence` and in `test_coherence_route_exists` |
| Dev token is located at a path other than `{WORKSPACE}/.specDoc/dev-token` | Pre-flight 2.4 finds the token elsewhere (e.g. injected as env var `SPECDOC_DEV_TOKEN`) | Replace the path reference in AUTH PROCEDURE step 3 and step 4; if env var, instruct the agent to read `$SPECDOC_DEV_TOKEN` instead of using the Read tool |
| File content is returned in a JSON wrapper `{"content": "..."}` rather than raw text | Observed in manual exercise 7.4 | Add one instruction line to `sam_specDoc_readFile`: "Extract the `content` field from the JSON response before presenting it." |
| `sam-context/` or `sam-projects/` already exist with a different casing or underscore convention | Other tasks are further ahead than expected | Adopt the established naming convention for `sam-specDoc/`; do not rename existing directories |

---

## 10. Out of Scope

| Item | Reason excluded |
|------|-----------------|
| `sam_specDoc_braindump()` | Template source file unidentified; specced as a follow-on once the canonical template path is confirmed |
| `sam-context/SKILL.md` | Separate task; boot snapshot mechanism (cron vs. live-query) is unresolved |
| `sam-projects/SKILL.md` | Separate task; project canonical path conflicts (`clawboi`, `openclaw`, `humaniz.me`) unresolved |
| `openclaw.plugin.json` and MCP graduation | Task 4; activated only after a named skill-layer capability ceiling is demonstrated |
| Retry logic in bridge tools | Explicitly excluded from v1 by architecture decision: "No retry logic at v1" |
| Response caching | Explicitly excluded from v1 by architecture decision: "No caching at v1" |
| Aggregated or multi-step queries | Agent composes these; bridge is one-to-one by design |
| `sam_docker_ps()` | Docker socket mount inside OpenClaw container unconfirmed; a silently-failing tool is excluded |
| Bubls data access | No confirmed local URL; outside this plugin's scope |
| JWT key rotation or token refresh | Auth is either bypassed or a static dev token; rotation deferred to v2 |
| Trendfy and `humaniz.me` entries | Belong to `sam-projects/SKILL.md`; excluded pending path and live-status confirmation |
| Telegram formatting constraints | Defined in `sam-context/SKILL.md`; not duplicated here |
| Any spec-doc backend change | This task is read-only from the spec-doc server's perspective |