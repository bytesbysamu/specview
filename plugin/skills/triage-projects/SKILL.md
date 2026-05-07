---
name: triage-projects
description: "Use this skill when the user wants to clean up, archive, or prioritize projects in Specview. Reads all project.json files, determines which are current vs stale, assigns priorities, archives dead ones, and syncs to the running container."
---

# /triage-projects — Project Triage & Cleanup

Read every project in `data/spec-doc/projects/`, assess its current relevance,
assign a priority (1–5), and mark stale/dead projects as archived. Sync all
changes to the running container without restarting it.

## Parameters

```
/triage-projects [--dry-run]
```

- `--dry-run` — print the proposed changes without writing anything

## Pre-flight

1. Confirm container is running: `docker ps | grep specview-api`
2. Resolve projects dir: `data/spec-doc/projects/` relative to repo root.
3. Read ALL `project.json` files. Also skim the first 40 lines of the primary
   `.md` file in each directory (prefer `braindump.md`, else the first `.md`
   alphabetically) to understand the project's purpose and recency.

## Triage Rules

For each project, determine:

| Field | Values | Rule |
|-------|--------|------|
| `archived` | `true` / absent | Set `true` if project is dead, replaced, or a historical duplicate |
| `priority` | `1`–`5` | 1 = active P0, 2 = active P1, 3 = backlog, 4 = low, 5 = parked |
| `section` | `braindumps`, `products`, `platform`, `archive` | Update if miscategorised |

**Archive candidates** (set `archived: true`):
- Superseded by a newer project on the same topic (keep only the latest)
- One-off tasks already completed (e.g. twitter-bio, linkedin-update, reddit-post-draft)
- Duplicate or near-duplicate projects (bubls, bubls2, bubls3 → keep only most recent)
- Historical snapshots that add no forward value

**Priority guide**:
- P1 (priority 1): shipping soon, being actively worked on
- P2 (priority 2): next up, clear scope
- P3 (priority 3): backlog, real intent but not scheduled
- P4 (priority 4): parked ideas, low confidence
- P5 (priority 5): reference only

## Procedure

### 1. Read and inventory

For every directory in `data/spec-doc/projects/`:
- Read `project.json` → name, section, current priority/archived
- Skim primary `.md` → topic, recency signals, completion status

Build a working list:
```
[slug] | [name] | [section] | [current priority] | [archived?] | [synopsis 1 line]
```

### 2. Assess and propose

Apply triage rules. For each project produce a proposed outcome:
```
[slug]
  action:   keep | archive
  priority: 1–5
  section:  braindumps | products | platform
  reason:   one sentence
```

Print the full proposal before writing anything. If `--dry-run`, stop here.

### 3. Confirm with user

Ask: "Apply these changes? (yes / adjust <slug> / skip <slug>)"

Accept inline adjustments — e.g. "adjust bubls priority=1" before confirming.

### 4. Write project.json files

For each project being changed, read its current `project.json`, apply the
delta (add/update `archived`, `priority`, `section`), and write it back.
Do not touch any `.md` files.

### 5. Sync to container

```bash
for each changed project:
  docker cp data/spec-doc/projects/<slug>/project.json \
            specview-api-1:/data/spec-doc/projects/<slug>/project.json
```

The Flask API reads project.json on every request — no restart needed.

### 6. Report

```
triage-projects: complete
  Kept active:  N projects
  Archived:     N projects
  Priority set: list of (slug → priority)
  Container:    synced
```

## Abort Conditions

- `data/spec-doc/projects/` not found → stop, wrong working directory.
- `docker ps` shows no `specview-api` container → warn, write files but skip sync.
- User answers "no" to the confirmation → stop, write nothing.

## Notes

- Never delete directories — only set `archived: true` in project.json.
- The API filters out `archived: true` projects from the listing automatically.
- Priority 99 = unset (API default) — always assign an explicit 1–5.
- Run `/triage-projects` again any time the project list gets cluttered.
- After triage, refresh http://localhost:8095/ to see the updated ordering.
