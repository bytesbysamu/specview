# Timeline — Thin API Layer / Plugin-Driven AI Services

## Phases

### Phase 0 — Safety net (before any code change)

**Goal:** Capture current behaviour so regressions are detectable.

| Task | Owner | Notes |
|------|-------|-------|
| Run existing pytest suite; record pass count | dev | Baseline: `pytest api/ -q` |
| Snapshot one full bootstrap run output (analysis + epic + architecture) | dev | Save to `data/projects/thin-api-layer-baseline/` |
| Add a response-shape test for `/api/ai/text/bootstrap-project/status` | dev | Asserts keys: `done`, `running`, `files` shape |
| Confirm `CHAIN_AGENT` env var is absent from all compose files | dev | Ensure current production is unaffected during migration |

**Exit criterion:** Baseline snapshots saved; all tests pass; CHAIN_AGENT absent.

---

### Phase 1 — Migrate `epic_guide.py` (lowest risk, no multi-step dependency)

**Goal:** Prove the pattern on the simplest service — one AI call, one output file.

| Task | File | Change |
|------|------|--------|
| Remove `build_epic_guide_prompt` call | `epic_guide.py:85` | Replace with `prompt = f"Generate implementation-guide.md for project at {project_dir}..."` |
| Remove `read_context(...)` calls (builder, principles, codebase, references, versions) | `epic_guide.py:79–93` | Agent loads context from its references automatically |
| Delete `api/modules/ai/prompts/epic_guide.py` | `prompts/epic_guide.py` | Delete file |
| Test: start epic guide generation against dev container with `CHAIN_AGENT=chain-agent` | local | Verify `implementation-guide.md` is written to project dir |
| Test: `pytest api/modules/ai/services/tests/ -q` | CI | Confirm unit tests pass |

**Exit criterion:** Epic guide generates correctly via agent; service tests green; `prompts/epic_guide.py` deleted.

---

### Phase 2 — Migrate `task_gen.py` (medium risk, lint gate must stay)

**Goal:** Migrate the largest service while keeping the lint gate and contract helpers intact.

| Task | File | Change |
|------|------|--------|
| Remove `build_implementation_guide_prompt` import and call | `task_gen.py:34,464` | Replace Steps 6–8 with path-based prompt |
| Remove `read_context(...)` calls (builder, principles, codebase, references, quality, versions) | `task_gen.py:440–445` | Remove lines; keep `collect_prior_task_contracts` |
| Keep prior-task contract formatting | `task_gen.py:447–465` | Append `prior_ctx` to prompt string if non-empty |
| Keep lint gate (Steps 10–11) | `task_gen.py:471–499` | Lint gate is application logic — unchanged |
| Delete `api/modules/ai/prompts/impl_guide.py` | `prompts/impl_guide.py` | Delete file |
| Test: generate task 1 for a known project via dev container | local | Verify `task-1-*.md` written; lint gate fires correctly on bad output |
| Test: `pytest api/ -q` | CI | Full suite pass |

**Exit criterion:** Task guide generates via agent; lint gate enforced; `prompts/impl_guide.py` deleted.

---

### Phase 3 — Migrate `bootstrap.py` (highest complexity, multi-step chain)

**Goal:** Replace the four-step AICall workflow with path-based prompt strings.

| Task | File | Change |
|------|------|--------|
| Replace `_analysis_step()` system + prompt_template with path-based one-liner | `bootstrap.py:66–72` | `system=""`, `prompt_template="Generate analysis for '{project_name}' from {braindump_path} → {analysis_path}."` |
| Replace `_epic_step()` | `bootstrap.py:75–83` | Same pattern; input from `analysis_path` |
| Replace `_architecture_step()` | `bootstrap.py:85–105` | Same; keep `stream=True` and `max_tokens=16384` |
| Remove all `from modules.ai.prompts import ...` | `bootstrap.py:13–21` | Delete import block |
| Update workflow `.inputs()` to include `braindump_path`, `analysis_path`, `epic_path`, `arch_path` instead of raw content keys | `bootstrap.py:112–125` | Route layer passes paths, not content |
| Update route handler to pass paths instead of braindump content | `routes/text.py` or `routes/spec_gen.py` | `braindump_path=str(project_dir / "braindump.md")` |
| Delete `api/modules/ai/prompts/spec_gen.py` | `prompts/spec_gen.py` | Delete file |
| Test: full bootstrap run against dev container | local | Four files generated in project dir |
| Test: `pytest api/ -q` | CI | Full suite green |

**Exit criterion:** Bootstrap chain runs end-to-end via agent; all four spec files generated; `prompts/spec_gen.py` deleted.

---

### Phase 4 — Cleanup and production flip

**Goal:** Remove all remaining prompt infrastructure and activate in production.

| Task | File | Change |
|------|------|--------|
| Delete `api/modules/ai/prompts/builder.py` | `prompts/builder.py` | Delete |
| Delete `api/modules/ai/prompts/__init__.py` | `prompts/__init__.py` | Delete |
| Delete `api/modules/ai/prompts/tests/` | `prompts/tests/` | Delete directory |
| Delete `api/modules/ai/tests/test_prompts*.py` | `ai/tests/` | Delete prompt snapshot tests |
| Update `test_structural.py` to assert `prompts/` dir does not exist | `test_structural.py` | Add assertion |
| Add `CHAIN_AGENT=chain-agent` to `docker-compose.yml` api service env | `docker-compose.yml` | Activate in all environments |
| Update `plugin/skills/spec-pipeline/SKILL.md` to add plugin-direct procedure | `plugin/skills/spec-pipeline/SKILL.md` | Document no-API path |
| Run `/dev-review` | all changed files | Convention compliance check |
| Open PR; CI must pass | GitHub | `pytest api/` + build check |

**Exit criterion:** `prompts/` directory does not exist; `CHAIN_AGENT` set in compose; PR merged with CI green.

---

## Milestone Summary

| Milestone | What is true |
|-----------|-------------|
| M0 — Baseline captured | Tests pass; snapshots saved; no code changed |
| M1 — Epic guide migrated | `epic_guide.py` prompt-free; `prompts/epic_guide.py` deleted |
| M2 — Task gen migrated | `task_gen.py` prompt-free; lint gate intact; `prompts/impl_guide.py` deleted |
| M3 — Bootstrap migrated | `bootstrap.py` prompt-free; `prompts/spec_gen.py` deleted |
| M4 — Production activated | `prompts/` gone; `CHAIN_AGENT` live; PR merged |

## Risks and Mitigations

| Risk | Phase | Mitigation |
|------|-------|-----------|
| Agent output format differs from Python-encoded format | M1–M3 | Compare snapshot before/after; check frontend renders correctly |
| Path injection in prompt string (project_id contains `../`) | M1–M3 | Sanitise `project_id` in route handler — already done via UUID validation |
| `CHAIN_AGENT` set globally breaks existing tests that use mock provider | M4 | Tests set `CHAIN_PROVIDER=mock` explicitly — `CHAIN_AGENT` only affects cli provider |
| Architecture step exceeds agent context window | M3 | Architecture prompt includes only paths; agent reads files directly — no content in prompt |
| `prompts/tests/` deletion breaks CI import | M4 | Delete test files before removing imports; run `pytest --collect-only` to confirm |
