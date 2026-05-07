# Thin API Phase 2 — Implementation Summary

## Status

Task 1 (Skill Registry Contract + Generic Route) is complete. Tasks 2–4 are unstarted.

---

## What Was Built (Task 1 complete)

- `api/modules/ai/job_store.py` — In-process job store. `SkillJob` dataclass (job_id, skill_name, skill_version, status, result, error). Thread-safe via `_LOCK`. No eviction. Four functions: `create_job`, `get_job`, `complete_job`, `fail_job`.
- `api/modules/ai/routes/generic_skill_route.py` — Flask Blueprint registered at `/api/skills`. Three endpoints (see Deployment). Name validated against regex before any filesystem access. Branches on `execution_model` from `skill.json` — no per-skill conditionals anywhere.
- `api/modules/ai/routes/generic_skill_service.py` — Execution layer. `load_skill_registry` reads `skill.json`. `_build_prompt` concatenates `SKILL.md` + user input — the full "zero AI strings in Python" enforcement point. `run_skill` calls `chain_adapter.generate()` and delegates to the validator. `run_skill_async` wraps `run_skill` in a daemon thread and updates the job store.
- `api/modules/ai/routes/output_validator.py` — Strips markdown fences, parses JSON, checks `required` fields from `output_schema`. Raises `ValueError` on failure; the route maps that to a 502 skill error before any response is written.
- `plugin/skills/rewrite/skill.json` — `execution_model: sync`, `output_schema: {required: ["text"]}`.
- `plugin/skills/review/skill.json` — `execution_model: sync`, `output_schema: {required: ["scores", "issues"]}`.
- `plugin/skills/brainstorm/skill.json` — `execution_model: async`, `output_schema: {required: ["questions", "recommendations", "rewritten_braindump"], optional: ["suggested_action"]}`.
- `docker-compose.override.yml` — `PLUGIN_DIR=/app/plugin` env var set; `plugin/` mounted read-only at `/app/plugin`.

---

## Plugin Skills

| Skill | execution_model | output_schema required fields | status |
|-------|----------------|-------------------------------|--------|
| rewrite | sync | `text` | skill.json + SKILL.md present |
| review | sync | `scores`, `issues` | skill.json + SKILL.md present |
| brainstorm | async | `questions`, `recommendations`, `rewritten_braindump` (+ optional `suggested_action`) | skill.json + SKILL.md present |
| spec-pipeline | async | — | SKILL.md present; skill.json **missing** |

---

## Architecture Decision

The generic route reads `skill.json` to determine `execution_model` and `output_schema`; it calls `chain_adapter.generate()` with a prompt built entirely from `SKILL.md` + user input; it validates the agent's stdout against `output_schema` before writing any response. No skill name, prompt fragment, or output assumption appears in Python — all behavioral intelligence lives in the skill directory. The core invariant: zero AI instruction strings in Python, verifiable by grep over `api/modules/ai/`.

---

## What's Next

1. **Task 2 — Benchmark Runner**: Consume `.jobs/<job_id>/run.log` corpus. Structural evaluator for async skills (key/type checks against `output_schema`). LLM-as-judge evaluator for sync skills (explicit versioned rubric, routed through `chain_adapter`). Produces per-track pass rate against N=10. Required before any old-route retirement.

2. **Task 3 — Track A Sync Migration**: Run rewrite and review through the generic route under benchmark. Retire old per-skill Python routes only after 95%/N=10 gate clears. Can run in parallel with Task 2 development.

3. **Task 4 — Track B Async Migration**: Add `skill.json` to `spec-pipeline` (currently missing). Migrate brainstorm and spec-pipeline through the generic route. `brainstorm` `suggested_action` field is already declared in the schema (stubbed null). Depends on Tasks 2 and 3 completing their gates.

---

## Deployment

Plugin is mounted read-only at `/app/plugin` (`docker-compose.override.yml`). `PLUGIN_DIR=/app/plugin` tells the service where to find skills. Skills resolve from `$PLUGIN_DIR/skills/<skill_name>/`.

**Route URLs:**

| Method | URL | Behavior |
|--------|-----|----------|
| `POST` | `/api/skills/run/<skill_name>` | Run a skill. Sync → `200 {"result": ...}` + `X-Job-Id` header. Async → `202 {"job_id": "..."}`. |
| `GET` | `/api/skills/jobs/<job_id>` | Poll async job. Returns `{job_id, skill, version, status, done, result?, error?}`. |
| `GET` | `/api/skills/` | List all skills with a `skill.json`. |

**Request body** (POST): any JSON object — passed verbatim as a JSON string appended after `SKILL.md` content in the prompt.

**Auth**: all three endpoints require `@require_auth`. POST also enforces `@check_usage_limit("skill")`.
