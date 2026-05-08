# Architecture — Thin API Layer / Plugin-Driven AI Services

## Current State

```
Route handler
  └── Service (run_generation thread)
        ├── read_context(...)            ← file I/O ✓
        ├── build_*_prompt(...)          ← prompt engineering ✗ (this goes away)
        └── chain_adapter.generate(...)  ← AI call, subprocess or SDK
              └── providers/cli.py
                    └── claude -p "..."  ← raw system prompt passed as string
```

Three files embed the most prompt logic:

| File | Lines | What it builds |
|------|-------|---------------|
| `api/modules/ai/workflows/spec_gen/bootstrap.py` | 198 | 4-step workflow: analysis → epic → architecture (imports `BOOTSTRAP_*_SYSTEM` and `BOOTSTRAP_*_USER` from `prompts/`) |
| `api/modules/ai/services/epic_guide.py` | 130 | Calls `build_epic_guide_prompt()` before `chain_adapter.generate()` |
| `api/modules/ai/services/task_gen.py` | 536 | Calls `build_implementation_guide_prompt()` — 10-section format, prior-task contracts, lint gate |
| `api/modules/ai/prompts/` | ~600 | Python prompt builders: `spec_gen.py`, `epic_guide.py`, `impl_guide.py` |

## Target State

```
Route handler
  └── Service (run_generation thread)
        ├── read_file(path)              ← file I/O ✓
        └── chain_adapter.stream_generate(
              system="",                 ← empty or one-liner
              prompt=f"generate {step} for project at {path}"
            )
              └── providers/cli.py
                    └── claude --agent chain-agent -p "..."
                          └── chain-agent reads plugin refs,
                              knows output format, writes stdout
```

The agent's system prompt is its `plugin/agents/chain-agent.md` definition. Output structure lives in plugin reference files and skill SKILL.md — not in Python strings.

## Decision Record

### D1 — Context via file path, not inline content

**Options considered:**
- (a) Pass braindump/epic content inline in `-p`: simpler Python, but `-p` has a shell length limit and is not inspectable.
- (b) Pass file path only; agent reads disk: agent needs correct `SPEC_DOC_DIR` path. Python passes `--cwd` or an absolute path in the prompt.
- **(c) Chosen: pass absolute file path in the prompt string.** Agent reads the file. Python never constructs content-bearing strings.

`prompt = f"Generate analysis for the project at {project_dir}/braindump.md. Write output to {project_dir}/analysis.md."`

### D2 — Agent writes output file, Python confirms

**Options considered:**
- (a) Agent returns content via stdout; Python writes: two moving parts, stdout capture adds latency to streaming.
- **(b) Chosen: agent writes the file; Python reads it back to confirm and return content to the HTTP client.**

For streaming steps (architecture), `stream_generate()` still captures stdout for live preview. Non-streaming steps use `generate()` and check the output file exists post-call.

### D3 — One subprocess call per workflow step

The bootstrap chain has four steps. Each step's output is the next step's input (analysis → epic → architecture). This dependency chain requires sequential calls.

**Chosen: keep one `claude` call per step, chained in Python with file paths.** This preserves the existing `WorkflowExecution` state machine and the per-step streaming/polling UX. A single multi-step agent call would sacrifice per-step progress visibility.

### D4 — Delete `prompts/` after migration (no fallback)

Keeping `prompts/` as a fallback creates the same dual-source problem we're solving. After migration and a passing test run, delete `api/modules/ai/prompts/` entirely.

### D5 — `CHAIN_AGENT=chain-agent` set per-endpoint during migration

Rather than a single env var flip, wrap each migrated service in a check:

```python
agent = os.getenv("CHAIN_AGENT")  # already read by cli.py
```

`CHAIN_AGENT` is already consumed by `providers/cli.py` — when set, it appends `--agent chain-agent` to every `claude` invocation. Setting it in the container env activates all routes simultaneously. Migration sequence: migrate one service at a time locally with `CHAIN_AGENT` set; flip env var in production only after all three services pass.

## Component Changes

### 1. `bootstrap.py` — remove AICall prompt imports

**Before:**
```python
from modules.ai.prompts import (
    BOOTSTRAP_ANALYSIS_SYSTEM,
    BOOTSTRAP_ANALYSIS_USER,
    ...
)
step = AICall(
    name="analysis",
    system=BOOTSTRAP_ANALYSIS_SYSTEM,
    prompt_template=BOOTSTRAP_ANALYSIS_USER,
    ...
)
```

**After:**
```python
step = AICall(
    name="analysis",
    system="",
    prompt_template="Generate analysis for project '{project_name}' from braindump at {braindump_path}.",
    input_keys=("project_name", "braindump_path"),
    model="claude-haiku-4-5",
)
```

The agent resolves format rules from its loaded references — no Python encoding needed.

Route layer change: pass `braindump_path` (absolute Path as string) instead of braindump content. This is the only interface change — the JSON body gains `braindump_path`, loses `braindump` (raw content). The frontend sends neither; the Python route constructs the path from `project_id` and `SPEC_DOC_DIR`.

### 2. `epic_guide.py` — remove `build_epic_guide_prompt`

**Before:**
```python
system, user = build_epic_guide_prompt(epic=epic, arch=arch, ...)
result = chain_adapter.generate(system, user, max_tokens=8192)
```

**After:**
```python
prompt = f"Generate implementation-guide.md for the project at {project_dir}. Read epic.md and architecture.md from that directory."
result = chain_adapter.generate("", prompt, max_tokens=8192)
update_file(projects_dir, project_id, OUTPUT_FILENAME, result.text)
```

`read_context()` calls removed — the agent loads builder/principles from its reference files automatically via `with_context()` in `generate()`. Wait: `generate()` still injects builder/principles if they are passed — keep passing them if the agent needs override capability. Otherwise, pass empty strings and let the agent use its own context.

### 3. `task_gen.py` — remove `build_implementation_guide_prompt`, keep lint gate

The lint gate (`lint_task_guide`) is application logic, not AI logic — it stays in Python.

**Before (Steps 6–9):**
```python
builder = read_context("builder")
...
system, user = build_implementation_guide_prompt(task_num=..., ...)
result = chain_adapter.generate(system, user)
```

**After:**
```python
prompt = (
    f"Generate task guide for task {task['num']} ({task['name']}) "
    f"in project at {project_dir}. "
    f"Read epic.md and architecture.md from that directory. "
    f"Output filename: {filename}"
)
result = chain_adapter.generate("", prompt)
```

Prior-task contract injection (`collect_prior_task_contracts`, `_format_contracts`) — these are deterministic helpers that inject structured context the agent cannot derive from disk. **Keep them.** Pass the formatted contract string in the prompt:

```python
prior_ctx = _format_contracts(collect_prior_task_contracts(specs, task["num"]))
if prior_ctx:
    prompt += f"\n\nPrior task file declarations:\n{prior_ctx}"
```

This is file I/O + formatting (reading already-generated task guides, extracting declared paths) — not prompt engineering. It stays in Python.

### 4. `api/modules/ai/prompts/` — delete entire directory

After all three services are migrated and `pytest` is green:
- Delete `prompts/builder.py`, `prompts/spec_gen.py`, `prompts/epic_guide.py`, `prompts/impl_guide.py`.
- Delete `prompts/tests/`.
- Remove `prompts/` import from `bootstrap.py`.
- Update `test_structural.py` to assert `prompts/` does not exist (or remove the import-boundary test for prompts).

### 5. `plugin/skills/spec-pipeline/SKILL.md` — new plugin-first procedure

Add a second procedure block describing the plugin-only path (no API required):

```
## Plugin-Direct Procedure (no API)

claude --agent chain-agent -p "generate analysis for project at {dir}/braindump.md, write to {dir}/analysis.md"
claude --agent chain-agent -p "generate epic from analysis at {dir}/analysis.md, write to {dir}/epic.md"
...
```

This serves as the canonical description of what the migrated Python services now do internally — and as a runnable manual override when the API is unavailable.

## Data Flow (post-migration)

```
POST /api/ai/text/bootstrap-project
  { project_name }             ← no braindump content in body; route reads from disk

Route handler
  → lookup project_dir = SPEC_DOC_DIR / project_id
  → verify braindump_path exists
  → spawn Thread(run_generation)
  → return { job_id }

run_generation thread:
  step 1: claude --agent chain-agent -p "generate analysis from {braindump_path} → {analysis_path}"
  step 2: claude --agent chain-agent -p "generate epic from {analysis_path} → {epic_path}"
  step 3: claude --agent chain-agent -p "generate architecture from {epic_path} → {arch_path}" (stream)
  step 4: read files back → BootstrapFile list → execution.complete()

GET /api/ai/text/bootstrap-project/status/<job_id>
  → snapshot() unchanged
```

## Files Changed

| File | Change |
|------|--------|
| `api/modules/ai/workflows/spec_gen/bootstrap.py` | Remove prompt imports; replace AICall system/template strings with path-based prompts |
| `api/modules/ai/services/epic_guide.py` | Remove `build_epic_guide_prompt`; replace with one-liner prompt |
| `api/modules/ai/services/task_gen.py` | Remove `build_implementation_guide_prompt`; keep lint gate and contract helpers |
| `api/modules/ai/prompts/` | Delete entire directory |
| `docker-compose.yml` (or override) | Add `CHAIN_AGENT=chain-agent` to `api` service env |
| `plugin/skills/spec-pipeline/SKILL.md` | Add plugin-direct procedure block |

## Files Unchanged

- All route handlers (`routes/spec_gen.py`, `routes/task_gen.py`, `routes/text.py`)
- Auth and usage-limit decorators
- `providers/cli.py` (already supports `CHAIN_AGENT`)
- `adapter.py` public API
- Angular frontend
- SQLModel models and Alembic migrations
- `modules/quality/lint.py` and lint gate logic in `task_gen.py`
- `test_structural.py` (adapter boundary test)

## Test Strategy

1. **Snapshot tests** — Before migrating, capture current output for a known braindump → analysis/epic/architecture/timeline. After migration, compare shapes (not exact text, since the agent may rephrase).
2. **Contract tests** — `test_spec_gen_routes.py` already tests the HTTP contract; these pass unchanged because route signatures don't change.
3. **Service unit tests** — `test_service_helpers.py` tests pure helpers (`find_next_missing_task`, `extract_task_desc`, `collect_prior_task_contracts`). These are unaffected — helpers stay in Python.
4. **Structural test** — `test_structural.py` will pass trivially once `prompts/` is deleted (nothing left to import from providers).
5. **Integration** — Run `/spec-pipeline thin-api-layer-braindump` against the live container with `CHAIN_AGENT=chain-agent` set; verify four files generated with correct filenames and non-empty content.
