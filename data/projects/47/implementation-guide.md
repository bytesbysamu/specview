# Implementation Guide: Thin API Layer — Plugin-Driven AI Services

## Overview

This epic removes all embedded prompt logic from three Python services (`epic_guide.py`, `task_gen.py`, `bootstrap.py`) and routes AI generation through the Claude Code plugin's chain-agent instead. Python keeps file I/O, HTTP, and job orchestration; the agent owns output structure and generation rules. Work sequences as: safety-net baseline → migrate epic_guide (simplest, one AI call) → migrate task_gen (medium, keep lint gate) → migrate bootstrap (hardest, multi-step chain) → cleanup and production flip.

## Shared Pre-flight

- Confirm `CHAIN_PROVIDER=cli` is set in `api/.env` and unset `CHAIN_AGENT` until you are ready for each phase.
- Run `pytest api/ -q` and record the pass count — this is your regression baseline.
- Confirm `plugin/agents/chain-agent.md` and `plugin/references/chain-conventions.md` are current.
- Confirm the Claude CLI binary is available: `claude --version`.
- Keep a terminal open on `docker compose logs -f api` (or the local process log) throughout.

---

## Task 1: Safety Net — Baseline Snapshots  [Effort: 0.5 days]

### What
Before any code changes, capture the current output shape and test baseline so regressions can be detected objectively. Nothing is changed in the codebase during this task.

### Files
- **Create**: `data/spec-doc/projects/thin-api-layer-baseline/` — directory to hold snapshot outputs; create manually or via a one-off bootstrap call.
- **Modify**: `api/modules/ai/routes/tests/test_spec_gen_routes.py` — add a response-shape assertion for the bootstrap status endpoint if one doesn't exist.

### Steps
1. Run `pytest api/ -q` and save the summary line (e.g. "142 passed") to a scratch note — this is the number to beat after every subsequent task.
2. Trigger a full bootstrap run against a known small braindump and save the resulting `analysis.md`, `epic.md`, `architecture.md` to `data/spec-doc/projects/thin-api-layer-baseline/`.
3. In `test_spec_gen_routes.py`, add an assertion that the bootstrap status response contains keys `done`, `running`, and optionally `files` — these must not change after migration.
4. Confirm `CHAIN_AGENT` is absent from `api/.env` and all compose files; if present, remove it before proceeding.

### Verify
- `pytest api/ -q` reports the same pass count as before.
- `data/spec-doc/projects/thin-api-layer-baseline/` contains non-empty `analysis.md`, `epic.md`, `architecture.md`.
- `git status` shows only test additions — no service or prompt files touched.

---

## Task 2: Migrate `epic_guide.py`  [Effort: 0.5 days]

### What
Replace the `build_epic_guide_prompt()` call and its six `read_context()` dependencies with a single path-based prompt string. This is the lowest-risk migration: one AI call, one output file, no multi-step dependencies. Proves the pattern before touching the more complex services.

### Files
- **Modify**: `api/modules/ai/services/epic_guide.py` — remove `build_epic_guide_prompt` import and all `read_context()` calls (lines 79–94); replace with a one-line prompt string passed to `chain_adapter.generate()`.
- **Delete**: `api/modules/ai/prompts/epic_guide.py` — no longer imported anywhere after this change.

### Steps
1. In `epic_guide.py`, delete the import of `build_epic_guide_prompt` from `modules.ai.prompts.epic_guide` and all six `read_context(...)` calls for builder, principles, codebase, references, versions, and the local `_spec()` helper calls that feed them.
2. Replace the `system, user = build_epic_guide_prompt(...)` and `result = chain_adapter.generate(system, user, ...)` block with: construct `project_dir` from `projects_dir / project_id`, then call `chain_adapter.generate("", f"Generate implementation-guide.md for the project at {project_dir}. Read epic.md and architecture.md.", max_tokens=8192)`.
3. Leave `update_file(...)` and `execution.complete()` calls unchanged — file write and state management stay in Python.
4. Set `CHAIN_AGENT=chain-agent` in `api/.env` locally and restart the API process.
5. Trigger an epic guide generation for a test project and confirm `implementation-guide.md` is written to its directory.
6. Delete `api/modules/ai/prompts/epic_guide.py`.

### Verify
- `pytest api/ -q` passes with the same count as the Task 1 baseline.
- `implementation-guide.md` is written with non-empty content and begins with `#`.
- `grep -r "build_epic_guide_prompt" api/` returns no matches.
- `api/modules/ai/prompts/epic_guide.py` no longer exists.

---

## Task 3: Migrate `task_gen.py`  [Effort: 1 day]

### What
Strip prompt construction from the largest service while keeping the lint gate and prior-task contract helpers intact — these are deterministic application logic, not AI logic. The prompt becomes a short string with the task number, name, project path, and optionally the prior-task contract block appended.

### Files
- **Modify**: `api/modules/ai/services/task_gen.py` — remove `build_implementation_guide_prompt` import and all six `read_context()` calls (steps 6–8 of `run_generation`); replace with path-based prompt; keep `collect_prior_task_contracts`, `_format_contracts`, and the lint gate unchanged.
- **Delete**: `api/modules/ai/prompts/impl_guide.py` — no longer imported after this change.

### Steps
1. In `task_gen.py`, delete the import of `build_implementation_guide_prompt` from `modules.ai.prompts.impl_guide` and the six `read_context(...)` calls for builder, principles, codebase, references, quality, and versions.
2. Construct `project_dir = projects_dir / project_id`. Build the prompt string: `f"Generate task guide for task {task['num']} ({task['name']}) in project at {project_dir}. Read epic.md and architecture.md."`.
3. If `prior_ctx` (from `_format_contracts(collect_prior_task_contracts(...))`) is non-empty, append it to the prompt string as a plain-text block — keep the `collect_prior_task_contracts` and `_format_contracts` functions untouched.
4. Replace `result = chain_adapter.generate(system, user)` with `result = chain_adapter.generate("", prompt)`. The lint gate at steps 10–11 runs on `result.text` exactly as before.
5. Set `CHAIN_AGENT=chain-agent` in `api/.env` (already set from Task 2) and trigger a task guide generation for a test project.
6. Delete `api/modules/ai/prompts/impl_guide.py`.

### Verify
- `pytest api/ -q` passes with the same count.
- A task guide is written to `task-{N}-{slug}.md` with non-empty content.
- Lint gate fires correctly: introduce a deliberate format violation in a test prompt, confirm the route returns a lint error rather than writing the file.
- `grep -r "build_implementation_guide_prompt" api/` returns no matches.

---

## Task 4: Migrate `bootstrap.py`  [Effort: 1 day]

### What
Replace the four `AICall` step definitions — which import Python prompt constants — with path-based prompt strings. This is the most complex migration because the bootstrap chain is sequential (each step's output feeds the next) and the architecture step streams. The `WorkflowExecution` state machine and per-step streaming/polling are unchanged.

### Files
- **Modify**: `api/modules/ai/workflows/spec_gen/bootstrap.py` — remove all six `from modules.ai.prompts import BOOTSTRAP_*` imports; replace `AICall` `system` and `prompt_template` values in `_analysis_step()`, `_epic_step()`, and `_architecture_step()` with path-based strings; update `.inputs()` declarations to include path keys instead of content keys.
- **Modify**: `api/modules/ai/routes/text.py` (or whichever route calls bootstrap) — pass `braindump_path` as a string path rather than braindump content in the workflow inputs dict.
- **Delete**: `api/modules/ai/prompts/spec_gen.py` — no longer imported after this change.

### Steps
1. In `bootstrap.py`, delete the import block for `BOOTSTRAP_ANALYSIS_SYSTEM`, `BOOTSTRAP_ANALYSIS_USER`, `BOOTSTRAP_EPIC_SYSTEM`, `BOOTSTRAP_EPIC_USER`, `BOOTSTRAP_ARCHITECTURE_SYSTEM`, `BOOTSTRAP_ARCHITECTURE_USER`.
2. Rewrite `_analysis_step()`: set `system=""`, set `prompt_template` to `"Generate analysis for project '{project_name}' from braindump at {braindump_path}. Write output to {analysis_path}."`, update `input_keys` to `("project_name", "braindump_path", "analysis_path")`.
3. Rewrite `_epic_step()` similarly: prompt references `{analysis_path}` and `{epic_path}` as file locations; `input_keys` includes `analysis_path` and `epic_path`.
4. Rewrite `_architecture_step()` similarly: prompt references `{epic_path}` and `{arch_path}`; keep `stream=True` and `max_tokens=16384` unchanged.
5. In the route handler that invokes the bootstrap workflow, construct the four path strings from `project_dir` and pass them as workflow inputs instead of file content strings.
6. Run a full bootstrap against a test project — watch the per-step polling endpoint update as each step completes.
7. Delete `api/modules/ai/prompts/spec_gen.py`.

### Verify
- `pytest api/ -q` passes with the same count.
- A full bootstrap produces non-empty `analysis.md`, `epic.md`, `architecture.md` in the project directory.
- The bootstrap status polling endpoint returns `done: true` and `files` list after completion.
- `grep -r "BOOTSTRAP_ANALYSIS_SYSTEM\|BOOTSTRAP_EPIC_SYSTEM\|BOOTSTRAP_ARCHITECTURE_SYSTEM" api/` returns no matches.

---

## Task 5: Cleanup and Production Flip  [Effort: 0.5 days]

### What
Delete the remaining `prompts/` infrastructure, activate `CHAIN_AGENT` in all environments, update the plugin skill to document the plugin-direct path, and open the PR. This task has no AI logic changes — it is a cleanup and deployment step.

### Files
- **Delete**: `api/modules/ai/prompts/builder.py`, `api/modules/ai/prompts/__init__.py`, `api/modules/ai/prompts/tests/` (entire directory), `api/modules/ai/tests/test_prompts.py`, `api/modules/ai/tests/test_prompts_snapshots.py`, `api/modules/ai/tests/test_bootstrap_prompts.py`.
- **Modify**: `api/modules/ai/workflows/spec_gen/tests/test_bootstrap_workflow.py` — remove any import or reference to `modules.ai.prompts`.
- **Modify**: `docker-compose.yml` — add `CHAIN_AGENT: chain-agent` to the `api` service `environment` block.
- **Modify**: `plugin/skills/spec-pipeline/SKILL.md` — add a Plugin-Direct Procedure section describing the `claude --agent chain-agent -p "..."` commands for each step.
- **Modify**: `api/modules/runtime/chain/tests/test_structural.py` — add an assertion that `api/modules/ai/prompts/` does not exist on disk.

### Steps
1. Delete all files listed above using `rm -rf api/modules/ai/prompts/` and individual test file deletions; confirm no remaining imports reference `modules.ai.prompts` with `grep -r "modules.ai.prompts\|from modules.ai import.*prompts" api/`.
2. Run `pytest api/ -q` — fix any import errors surfaced by the deletions before proceeding.
3. In `test_structural.py`, add an assertion using `pathlib.Path` that `api/modules/ai/prompts` does not exist; run `pytest api/modules/runtime/chain/tests/test_structural.py -v` to confirm it passes.
4. Add `CHAIN_AGENT: chain-agent` to the `api` service environment in `docker-compose.yml`; rebuild with `docker compose build api && docker compose up -d api`.
5. Update `plugin/skills/spec-pipeline/SKILL.md` with a Plugin-Direct Procedure block listing the four `claude --agent chain-agent -p "..."` commands for analysis, epic, architecture, and timeline steps.
6. Run `/dev-review` and address any convention violations before opening the PR.
7. Open PR against `master`; CI must pass `pytest api/` before merge.

### Verify
- `pytest api/ -q` passes with the same or higher count as Task 1 baseline.
- `ls api/modules/ai/prompts/` returns "No such file or directory".
- `docker compose logs api` shows `CHAIN_AGENT=chain-agent` in the startup env dump.
- A full bootstrap and epic guide generation run successfully against the Docker container.
- PR CI is green.
