# Epic — Thin API Layer: Plugin-Driven AI Services

## Summary

Remove all embedded prompt templates and AI logic from Python services. Route all AI generation through the Claude Code plugin's chain-agent, so Python handles only file I/O, HTTP, and job orchestration.

## User Story

**As** a developer adding a new spec generation capability to specview,  
**I want** to write a markdown skill file in `plugin/skills/`,  
**So that** I do not need to touch Python code, rebuild the container, or redeploy to add the new capability.

## Scope

### In scope

- Strip system prompt strings from `bootstrap.py`, `epic_guide.py`, `task_gen.py`.
- Delete or empty `api/modules/ai/prompts/` directory.
- Set `CHAIN_AGENT=chain-agent` in the Docker Compose environment for the `api` container.
- Create (or update) a plugin skill file for each migrated generation type if one does not exist.
- Verify all existing API endpoints return the same response shape post-migration.
- Ensure `test_structural.py` and all service tests pass.

### Out of scope

- Angular frontend changes.
- New generation types (this epic only migrates existing ones).
- Changes to auth, usage limiting, or route handlers.
- Changes to the `mock` provider or test fixtures.
- Changes to Alembic migrations or SQLModel models.

## Acceptance Criteria

1. `POST /api/ai/text/bootstrap-project` returns `{ job_id }` and eventually produces `analysis.md`, `epic.md`, `architecture.md`, `timeline.md` in `SPEC_DOC_DIR/{project_id}/` — identical contract to today.
2. `GET /api/ai/text/bootstrap-project/status/<job_id>` returns `{ done, running, files? }` — unchanged.
3. `GET /api/projects/<id>/implementation-guide` streams the guide via SSE or returns it as text — unchanged.
4. `GET /api/projects/<id>/task/<task_id>/implementation-guide` returns per-task guide — unchanged.
5. No Python file in `api/modules/ai/` contains an inline string longer than 80 characters that encodes output format or section structure.
6. `pytest api/` passes with zero failures.
7. A new spec generation type can be demonstrated by adding only a skill markdown file (no Python changes required).

## Dependencies

- `CHAIN_AGENT` env var support already in `providers/cli.py` — no new infrastructure needed.
- Claude CLI binary mounted and credentialed in the Docker container (`~/.claude`).
- Plugin agent and reference files already written and accurate.

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Agent output format differs from Python-encoded format — frontend breaks | Medium | Snapshot current output; write a response-shape test before migrating |
| Multi-step bootstrap chain is hard to express as a single agent prompt | Medium | Keep one `claude` subprocess call per step; chain them in Python with file paths |
| Streaming breaks if agent writes to file instead of returning stdout | Low | Keep `stream_generate()` path; agent returns stdout; Python writes file |
| `CHAIN_AGENT` in production causes latency regression | Low | Baseline latency before and after; agent call overhead is subprocess startup only |

## Definition of Done

- All AC above are met.
- `/dev-review` passes with no convention violations flagged.
- `CHAIN_AGENT=chain-agent` is set in `docker-compose.yml` (or `docker-compose.override.yml`).
- `plugin/skills/spec-pipeline/SKILL.md` is updated to reflect the new plugin-only flow.
- No `prompts/` Python files remain with embedded AI instructions.
