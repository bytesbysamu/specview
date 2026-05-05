# Spec-Doc API Contract

Reverse-engineered from `server.js` on 2026-04-22.
Flask must match every route, method, payload field, and response shape exactly.
Any deviation breaks Angular without a frontend code change.

**Express port:** 3100 (source of truth)
**Flask port:** 3101 (migration target)

---

## Health

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/health` | GET | — | `{"status": "ok"}` |

> Flask adds this route. Express does not expose it.

---

## Context Routes

All context routes share the same response shapes.

### Builder Profile

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/builder` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/builder` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `builder.md` at workspace root
**exists logic:** `content.length > 0`
**PUT validation:** content must be a string; 400 if not

### Principles

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/principles` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/principles` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `principles.md` at workspace root
**exists logic:** `content.length > 0`
**PUT validation:** content must be a string; 400 if not

### Codebase

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/codebase` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/codebase` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `codebase.md` at workspace root
**exists logic:** `content.length > 0`
**PUT validation:** content must be a string; 400 if not

### References

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/references` | GET | — | `{"content": string, "exists": boolean}` |
| `/api/references` | PUT | `{"content": string}` | `{"success": boolean}` |

**File path (Express):** `references.md` at workspace root
**exists logic:** `content.length > 0`
**PUT validation:** content must be a string; 400 if not

---

## Project Routes

### List Projects

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/api/projects` | GET | — | `ProjectSummary[]` sorted newest-first |

**ProjectSummary shape:**
```json
{
  "id": "string",
  "name": "string",
  "createdAt": "ISO-8601 string",
  "specs": [{ "filename": "string", "label": "string" }]
}
```

- `id` = directory name under `projects/`
- `specs` = all `.md` files in the directory (filename only, no content)
- `label` = filename without `.md`, hyphens replaced with spaces, title-cased
  (`f.replace('.md', '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())`)
- Sort: descending by `createdAt` from `project.json`
- Directories without `project.json` are silently skipped

### Get Project

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/api/projects/:id` | GET | — | `ProjectDetail` |

**ProjectDetail shape:** same as ProjectSummary but `specs[].content` is populated (full file contents).

```json
{
  "id": "string",
  "name": "string",
  "createdAt": "ISO-8601 string",
  "specs": [{ "filename": "string", "label": "string", "content": "string" }]
}
```

- Returns 404 `{"error": "Project not found"}` if directory or `project.json` is missing

### Create Project

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/projects` | POST | `{"name": string, "files": [{"filename": string, "content": string}]}` | `{"id": string, "name": string, "createdAt": string}` |

- HTTP status: **201 Created**
- `id` = `{slugified-name}-{Date.now()}`
- Slug formula: `name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')`
- Creates `projects/{id}/`, writes `project.json` + each file from `files[]`
- `project.json` shape: `{"name": string, "createdAt": ISO-8601}`
- 400 `{"error": "Name and files are required"}` if `name` missing, `files` missing, or `files` not an array

### Update Project File

| Route | Method | Request Body | Response |
|-------|--------|-------------|----------|
| `/api/projects/:id/files/:filename` | PUT | `{"content": string}` | `{"success": boolean}` |

- Writes `content` to `projects/{id}/{filename}`
- Returns 404 `{"error": "Project not found"}` if `projects/{id}/` does not exist

### Delete Project

| Route | Method | Request | Response |
|-------|--------|---------|----------|
| `/api/projects/:id` | DELETE | — | `{"success": boolean}` |

- Removes `projects/{id}/` recursively (`fs.rmSync` with `{ recursive: true }`)
- Returns 404 `{"error": "Project not found"}` if directory does not exist

---

## AI Routes (Phase 2 — NOT implemented in Flask Phase 1)

These routes exist in Express. Flask Phase 1 does not expose them.

| Route | Method | Notes |
|-------|--------|-------|
| `/api/ai/text/rewrite` | POST | Phase 2 — req: `{text, instructions}`, res: `{text, latencyMs}` |
| `/api/ai/text/generate` | POST | Phase 2 — req: `{prompt, tone?}`, res: `{text, latencyMs}` |
| `/api/ai/text/iterate` | POST | Phase 2 — req: `{baseSpec, currentContent}`, res: `{text, latencyMs}` |
| `/api/ai/text/generate-spec` | POST | Phase 2 — req: `{input}`, res: `{text, latencyMs}` |
| `/api/ai/text/review` | POST | Phase 2 — req: `{documents}`, res: `{review, latencyMs}` |
| `/api/ai/text/lint-braindump` | POST | Phase 2 — req: `{braindump}`, res: `{advisory, latencyMs}` |
| `/api/ai/text/scan` | POST | Phase 2 + Walker — req: `{workspacePath}`, res: `{content, latencyMs}` |
| `/api/ai/implement` | POST (SSE) | Phase 2 — req: `{taskNum, taskName, projectContext, workspaceId?}`, SSE stream |
| `/api/container/status` | GET | Phase 2+ — Docker status |
| `/api/container/:workspaceId/preview` | POST | Phase 2+ — start preview |
| `/api/container/:workspaceId/preview` | DELETE | Phase 2+ — stop preview |
| `/api/container/:workspaceId` | DELETE | Phase 2+ — cleanup workspace |

---

## Error Conventions (reverse-engineered from Express)

| Condition | Status | Body |
|-----------|--------|------|
| Missing required field | 400 | `{"error": "descriptive message"}` |
| Resource not found | 404 | `{"error": "Project not found"}` or `{"error": "not found"}` |
| Filesystem error | 500 | `{"error": string}` |

> Flask must use `jsonify({"error": "..."})` with matching status codes. The Angular frontend checks the `error` key.
