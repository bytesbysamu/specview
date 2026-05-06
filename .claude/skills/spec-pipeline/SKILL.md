---
name: spec-pipeline
description: "Run the full spec-doc generation pipeline for a project: braindump -> analysis -> epic -> architecture -> timeline. Usage: /spec-pipeline <project_id_or_name>"
---

# /spec-pipeline — Spec generation pipeline

Run the complete spec generation chain for a project from braindump to timeline.

## Parameters

- `$ARGUMENTS` — project ID or project name (partial match accepted).

## Pre-flight

1. Confirm the API is running: `curl -s http://localhost:8095/api/health` → `{"status": "ok"}`.
2. Locate the project: `GET /api/projects` — find the project matching `$ARGUMENTS`.
3. Verify `braindump.md` exists in the project files. If missing, stop and report.
4. Confirm the user has a valid auth token (ask if unknown).

## Procedure

### Step 1 — Start bootstrap

```
POST /api/ai/text/bootstrap-project
{
  "project_name": "<name>",
  "braindump": "<content of braindump.md>"
}
→ { "job_id": "..." }
```

### Step 2 — Poll until done

```
GET /api/ai/text/bootstrap-project/status/<job_id>
```

Poll every 5 seconds. Print progress on each partial_files update:

```
✦ analysis      done
✦ epic          done
✦ architecture  generating…
```

### Step 3 — Save files

When `done: true`, the response contains `files: [{filename, content}]`.
These are automatically persisted by the backend — no manual save needed.

### Step 4 — Confirm

```
GET /api/projects/<project_id>
```

List the generated files. Report the result:

```
Spec pipeline: complete
  ✦ analysis.md      generated (2.1 kB)
  ✦ epic.md          generated (3.4 kB)
  ✦ architecture.md  generated (4.7 kB)
  ✦ timeline.md      generated (1.8 kB)
Duration: 94s
```

## Output Format

**Success:** As shown in Step 4.

**Failure:**
```
Spec pipeline: FAILED
Step: architecture
Error: claude CLI exited with code 1 — check container logs
```

## Abort Conditions

- API health check fails.
- No `braindump.md` in project files.
- `error` field present in poll response.
- Job runs for more than 10 minutes without `done: true`.

## Allowed Tools

Bash, Read, Glob, Grep, WebFetch, AskUserQuestion
