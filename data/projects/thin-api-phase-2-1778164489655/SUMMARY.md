# Thin API Phase 2 — Implementation Summary

## Status

**Complete.** All in-scope tasks shipped. Task 2 (Benchmark Runner) skipped by decision.

---

## What Was Built

### Task 1 — Skill Registry Contract
- `api/modules/ai/job_store.py` — In-process job store. `SkillJob` dataclass (job_id, skill_name, skill_version, status, result, error). Thread-safe via `_LOCK`.
- `api/modules/ai/routes/generic_skill_route.py` — Blueprint at `/api/skills`. Three endpoints. Security gate: name regex → skill.json existence → validated. Branches on `execution_model` from skill.json.
- `api/modules/ai/routes/generic_skill_service.py` — Reads SKILL.md → `chain_adapter.generate()` → validates output. Zero AI strings in Python.
- `api/modules/ai/routes/output_validator.py` — Strips markdown fences, parses JSON, checks `required` fields from `output_schema`.
- `docker-compose.override.yml` — `PLUGIN_DIR=/app/plugin` + plugin volume mounted read-only.

### Task 3 — Track A Sync Migration (rewrite, iterate, review)
- `api/modules/ai/routes/text.py` — `rewrite`, `iterate`, `review` handlers now call `load_skill_registry()` + `run_skill()` from generic_skill_service. No prompt building in Python.
- `api/modules/ai/services/text_prompts.py` — `rewrite_prompt`, `iterate_prompt`, `lint_braindump_prompt`, `review_prompt` deleted. Zero AI strings in migrated handlers.
- Old route URLs (`/api/ai/text/rewrite`, etc.) preserved — frontend unchanged.

### Task 4 — Track B Async Migration (brainstorm, spec-pipeline)
- `api/modules/ai/routes/text.py` — `lint_braindump` handler migrated to `brainstorm` skill. Returns `{questions, recommendations, rewritten_braindump, suggested_action}` replacing `{ready, flags}`.
- `plugin/skills/spec-pipeline/skill.json` — Added (`execution_model: async`). spec-pipeline now registered in the skill registry.

---

## Plugin Skills

| Skill | execution_model | Status |
|-------|----------------|--------|
| rewrite | sync | Live — `/api/ai/text/rewrite` calls it |
| iterate | sync | Live — `/api/ai/text/iterate` calls it |
| review | sync | Live — `/api/ai/text/review` calls it |
| brainstorm | async | Live — `/api/ai/text/lint-braindump` calls it |
| spec-pipeline | async | Registered (skill.json present); bootstrap-project not yet migrated |

---

## Core Invariant

`api/modules/ai/routes/text.py` contains zero AI instruction strings for the four migrated routes. Remaining strings in `text_prompts.py` are exclusively for `bootstrap_*` functions (WorkflowExecution path — out of scope).

Verifiable: `grep -rn '"You are' api/modules/ai/routes/text.py` → empty.

---

## Routes

| Method | URL | Behavior |
|--------|-----|----------|
| `POST` | `/api/skills/run/<skill_name>` | Generic skill route. sync → `200 {"result":...}` + `X-Job-Id`. async → `202 {"job_id":"..."}`. |
| `GET` | `/api/skills/jobs/<job_id>` | Poll async job. |
| `GET` | `/api/skills/` | List all registered skills from skill.json. |
| `POST` | `/api/ai/text/rewrite` | Calls rewrite skill (backward-compat URL). |
| `POST` | `/api/ai/text/iterate` | Calls iterate skill. |
| `POST` | `/api/ai/text/review` | Calls review skill. |
| `POST` | `/api/ai/text/lint-braindump` | Calls brainstorm skill (new response shape). |

---

## What's Deferred

- **Task 2 (Benchmark Runner)** — skipped by decision.
- **bootstrap-project → spec-pipeline migration** — WorkflowExecution path requires separate effort.
- **Brainstorm → spec-pipeline guided flow** — `suggested_action` field stubbed; frontend two-step UX is a follow-on.
