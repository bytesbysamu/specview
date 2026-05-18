---
name: specview local data directory
description: Where spec project files live when running the API locally (no Docker)
type: project
---

Local dev (no Docker): `SPEC_DOC_DIR=/Users/sam/Projects/specview/data`
Projects live at: `data/projects/<project-id>/`
Each project needs a `project.json` with `{"name": "...", "createdAt": "...Z"}` to appear in the API.
Context files (builder.md, principles.md, codebase.md, references.md, quality.md, versions.md) live at `data/*.md`.

**Why:** SPEC_DOC_DIR is set in `api/.env`. `config.py` appends `/projects` to get PROJECTS_DIR. All context files and projects sit under `data/` — the old `data/spec-doc/` path was a Docker convention that doesn't match the local layout.

**How to apply:** When creating or placing project files for the local dev API, always use `data/spec-doc/projects/<id>/` not `data/projects/<id>/`.
