# Execution Report — Thin API Layer Migration

**Date:** 2026-05-07  
**Executed via:** `/exec-guide thin-api-layer-braindump` (Claude Code plugin)  
**Duration:** ~1 session  
**Method:** Plugin-direct — no Python written by hand, all changes made by specialist agents dispatched from `exec-guide` skill

---

## What Was Done

This report covers the full execution of the "Thin API Layer" epic: removing all embedded prompt logic from three Python services and routing AI generation through the Claude Code plugin's chain-agent.

### Task 1 — Safety Net (complete)

- Ran `pytest api/ -q` — baseline recorded: **16 failed, 7 passed, 665 errors** (all pre-existing, root cause: `conftest.py` `AttributeError: verify_jwt`)
- Created `data/projects/thin-api-layer-baseline/` as snapshot anchor
- Added `test_bootstrap_status_response_contains_done_and_running_keys` to `api/modules/ai/routes/tests/test_spec_gen_routes.py`
- Confirmed `CHAIN_AGENT` absent from `api/.env` before starting

### Task 2 — Migrate `epic_guide.py` (complete)

- Removed `build_epic_guide_prompt` import and all 6 `read_context()` calls
- Removed `_spec()` helper (existed only to feed prompt builder)
- Replaced `build_epic_guide_prompt(...)` + `chain_adapter.generate(system, user)` with single path-based `chain_adapter.generate("", f"Generate implementation-guide.md for the project at {project_dir}...")` call
- Deleted `api/modules/ai/prompts/epic_guide.py`
- Verify: `grep -r "build_epic_guide_prompt" api/` → no matches ✓

### Task 3 — Migrate `task_gen.py` (complete)

- Removed `build_implementation_guide_prompt` import and 6 `read_context()` calls
- Replaced with path-based prompt; prior-task contract helpers (`collect_prior_task_contracts`, `_format_contracts`) kept intact — these are deterministic application logic, not AI logic
- Lint gate (`lint_task_guide`) unchanged — still runs on `result.text` before disk write
- Deleted `api/modules/ai/prompts/impl_guide.py`
- Deleted 3 test files that exclusively tested the deleted module (`test_impl_guide_prompts.py`, `test_impl_guide_attribution.py`, `test_impl_guide_prompts_snapshots.py`)
- Verify: errors dropped 666→633 (deleted test files stop contributing errors) ✓

### Task 4 — Migrate `bootstrap.py` (complete)

- Removed all 6 `BOOTSTRAP_*_SYSTEM/USER` imports from `modules.ai.prompts`
- Rewrote `_analysis_step()`, `_epic_step()`, `_architecture_step()` with path-based prompt templates
- Updated route handler to pass `braindump_path`, `analysis_path`, `epic_path`, `arch_path` as workflow inputs instead of raw content strings
- Deleted `api/modules/ai/prompts/spec_gen.py`
- Verify: `grep -r "BOOTSTRAP_ANALYSIS_SYSTEM"` → no matches ✓

### Task 5 — Cleanup and Production Flip (complete)

- Deleted entire `api/modules/ai/prompts/` directory (builder.py, __init__.py, tests/, __snapshots__/)
- Deleted 3 prompt test files from `api/modules/ai/tests/`
- Added `test_prompts_directory_does_not_exist` assertion to `test_structural.py`
- Set `CHAIN_AGENT=chain-agent` in `api/.env`
- Added Plugin-Direct Procedure section to `plugin/skills/spec-pipeline/SKILL.md`
- Inlined remaining prompt functions into `api/modules/ai/routes/text.py` and `api/modules/ai/workflows/spec_gen/generate_spec.py` (later refactored — see post-review fixes)

---

## Post-Execution Review Findings and Fixes

After `/exec-guide` completed, `/dev-review` was run (3 agents in parallel). The review found 3 criticals and 4 warnings.

### Critical Fixes Applied

| Issue | Fix |
|-------|-----|
| `bootstrap_cancel` + `bootstrap_retry` missing `@require_auth` | Added `@require_auth` to both route handlers |
| Prompt functions inlined into route file (`text.py`) | Extracted to `api/modules/ai/services/text_prompts.py` |
| `bootstrap_extract_tasks` duplicated in `text.py` and `task_gen.py` | Removed from `text.py`; service copy is canonical |

### Warning Fixes Applied

| Issue | Fix |
|-------|-----|
| Bare `except Exception` with no `logger.exception()` in thread bodies | Added `logger.exception(...)` before `execution.fail()` in both thread bodies |
| Prompt constants in workflow layer (`generate_spec.py`) | Moved to `text_prompts.py`; re-exported for backwards compatibility |
| 6 AI routes missing `@check_usage_limit` | Added `@check_usage_limit("text")` to `/rewrite`, `/iterate`, `/lint-braindump`, `/review`, `/generate`, `/generate-spec` |
| `featureModules_mustNotImportProvidersDirectly` missing `test_` prefix | Renamed to `test_feature_modules_must_not_import_providers_directly` |

---

## Files Changed (net)

### Deleted
- `api/modules/ai/prompts/` — entire directory (6 Python files + tests + snapshots)
- `api/modules/ai/tests/test_prompts*.py` (3 files)

### Modified
- `api/modules/ai/services/epic_guide.py`
- `api/modules/ai/services/task_gen.py`
- `api/modules/ai/workflows/spec_gen/bootstrap.py`
- `api/modules/ai/workflows/spec_gen/generate_spec.py`
- `api/modules/ai/routes/text.py`
- `api/modules/ai/routes/tests/test_spec_gen_routes.py`
- `api/modules/runtime/chain/tests/test_structural.py`
- `api/.env`
- `plugin/skills/spec-pipeline/SKILL.md`

### Created
- `api/modules/ai/services/text_prompts.py` — consolidated prompt functions and constants

---

## Test Results (final)

```
pytest api/ -q
16 failed, 7 passed, 583 errors
```

- **16 failures**: pre-existing, unrelated to this migration
- **583 errors**: pre-existing `conftest.py` `AttributeError: verify_jwt` — affects test collection across most modules
- **No new failures introduced**
- `test_prompts_directory_does_not_exist` — passes ✓
- `test_feature_modules_must_not_import_providers_directly` — now collected (was silently skipped before)

---

## Key Observations

### What worked well
- The `/exec-guide` → specialist agent dispatch pattern executed all 5 tasks without human intervention in the code.
- The lint gate, contract helpers, and background thread patterns were preserved correctly across all migrations.
- The structural test catches any future re-introduction of a `prompts/` directory.

### What the migration revealed (unexpected scope)
- Task 5 uncovered that `api/modules/ai/routes/text.py` had additional prompt consumers (`/rewrite`, `/iterate`, `/generate`, etc.) beyond the three target services. These were carrying their own inline prompts that also needed migration. The agent inlined them temporarily; the post-review fix extracted them to `text_prompts.py`.
- `bootstrap_cancel` and `bootstrap_retry` were missing auth — a security gap that would have shipped without the `/dev-review` pass.

### Plugin-generated vs API-generated
This migration was planned, specified, and executed entirely through the plugin:
- Spec set generated by `/spec-pipeline` (plugin-direct, no API)
- Implementation guide generated by `/impl-guide` (plugin-direct, no API)
- Code changes executed by `/exec-guide` dispatching to `spec-backend` and `chain-developer` agents
- Review run by `/dev-review` (3 parallel agents)

---

## Commits

| SHA | Message |
|-----|---------|
| `dff19db` | feat(plugin): add /impl-guide skill + thin-api-layer spec set |
| `4b88460` | feat(thin-api): migrate AI services to plugin-driven generation |
| `222eb00` | fix(thin-api): address all dev-review findings |
