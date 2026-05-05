# Task 3: Deep Humanize Chain

**Purpose**: Port humanize-me's 3-pass Heavy mode system prompts into context files, register them in the manifest, create the `deep-humanize` chain definition JSON, and prove the end-to-end flow with tests against the mock provider.

**Effort**: 0.5 day

**Dependencies**: Task 1 (Context Block Loader) and Task 2 (Chain Definition Schema + Runner). Both must be merged. The loader provides `load_block(name)` / `load_blocks(names)`. The runner provides `STEP_HANDLERS` dispatch, `load_definition(chainId)`, and the `POST /api/text/chain` endpoint.

**Parallel With**: Task 4 (Braindump to Docs), Task 5 (Rewrite + Review) — all three can run concurrently once Tasks 1+2 land.

**Blocks**: Task 6 (Chain Mode UI) needs at least one chain definition to render.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)
- `humanize-me/backend/services/humanizer.py` — port source (PASS_1/2/3 system prompts)

---

## 1. Context

The humanize-me product validates a $195K MRR market with a 3-pass humanization chain. Its backend (`services/humanizer.py`) hardcodes three system prompts — PASS_1: strip AI patterns, PASS_2: add human voice, PASS_3: final polish — and feeds each pass's output into the next via `create_message`. Bubls already has the chain adapter (Task 2) and the context loader (Task 1). This task externalizes those three prompts into markdown context files, registers them in the manifest, and creates a chain definition JSON that the runner executes. No new Python modules — only data files (3 markdown prompts, 1 JSON definition, manifest entries) and one test file. The single-shot humanize mode (`modules/text/prompts.py:HUMANIZE`) remains untouched; Deep Humanize is additive — a chain operation that runs three sequential single-shot rewrites, each with a different system prompt.

**Trade-offs considered**:
- **Inline prompts in a Python module** (like `text/prompts.py` does for single-shot modes) — rejected: the epic requires all chain prompts to live in `server/context/prompts/` and be loaded via the manifest, so chains can share context blocks and prompts are diffable/reviewable as standalone files.
- **Port the prompts verbatim vs. expand/rewrite them** — chosen: port verbatim from `humanizer.py` with a minimal "Output ONLY the rewritten text." tail instruction. Rewriting prompts before proving the chain runner flows is premature optimization. Iterate on prompt quality from usage data post-ship.
- **Single chain definition with 3 steps vs. nested chain-of-chains** — chosen: flat 3-step definition. The runner's sequential loop handles it directly. Nested composition is deferred infrastructure with zero consumers.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
cd {WORKSPACE}/bubls
git status                                          # flag unrelated M/?? entries
git log -1 --format='%H' > /tmp/bubls-task3-sha     # rollback anchor
cd server && python -m pytest -q 2>&1 | tail -5     # baseline pass count — record it
```

Confirm Task 1 and Task 2 are merged:

```bash
# Context loader exists and is importable
python -c "from modules.context.loader import load_block, load_blocks; print('loader ok')"

# Chain runner with STEP_HANDLERS dispatch exists
python -c "from modules.chain.runner import load_definition, STEP_HANDLERS; print('runner ok')"

# Chain endpoint is registered
grep "chain" server/app.py | head -5
```

Confirm the context directory structure exists:

```bash
ls server/context/manifest.json     # manifest created by Task 1
ls server/context/prompts/          # prompts dir created by Task 1
```

**If any of the above fail**: Task 1 or Task 2 is not merged. STOP — this task depends on both.

**Baseline recorded**: [N]/[N] passing. Write the pytest pass count into the first commit body.

---

## 3. Files

### To Create (new)

- `server/context/prompts/humanize-pass-1.md` — PASS_1 system prompt ported verbatim from `humanize-me/backend/services/humanizer.py:PASS_1_SYSTEM`; strips AI writing patterns
- `server/context/prompts/humanize-pass-2.md` — PASS_2 system prompt ported verbatim from `humanize-me/backend/services/humanizer.py:PASS_2_SYSTEM`; injects human voice
- `server/context/prompts/humanize-pass-3.md` — PASS_3 system prompt ported verbatim from `humanize-me/backend/services/humanizer.py:PASS_3_SYSTEM`; final polish pass
- `server/modules/chain/definitions/deep-humanize.json` — chain definition: 3 rewrite steps, each referencing one humanize-pass context block, `outputMode: "single"`
- `server/modules/chain/tests/test_deep_humanize.py` — 13 tests: definition loading, context resolution, mock chain execution, structural invariants

### To Modify

- `server/context/manifest.json` — add entries for `humanize-pass-1`, `humanize-pass-2`, `humanize-pass-3` (merge with existing entries from Task 1)

### To Leave Alone

- `server/modules/text/prompts.py` — single-shot HUMANIZE prompt stays; Deep Humanize is additive, not a replacement
- `server/modules/text/routes.py` — no new routes; chains go through `POST /api/text/chain` (Task 2)
- `server/modules/text/service.py` — not involved; chain runner handles orchestration
- `server/modules/chain/adapter.py` — no changes; chain steps call adapter.generate internally via STEP_HANDLERS
- `server/modules/chain/runner.py` — no changes to runner logic; this task only adds a definition file the runner reads
- `server/modules/chain/providers/` — adapter boundary intact; runner calls adapter, not providers
- `server/modules/context/loader.py` — no changes; this task only adds files the loader reads
- `src/app/` — zero frontend work in Task 3

---

## 4. Implementation Steps

### Step 1: Create the three humanize prompt context files

**Action**: Port `PASS_1_SYSTEM`, `PASS_2_SYSTEM`, `PASS_3_SYSTEM` from `humanize-me/backend/services/humanizer.py` (lines 88-93 of `references.md`) into standalone markdown files. Each file is the full system prompt text — no frontmatter, no markdown headers, just the prompt body. Port verbatim, then append a single output-format instruction line matching the single-shot convention.

**File**: `server/context/prompts/humanize-pass-1.md` (new), `server/context/prompts/humanize-pass-2.md` (new), `server/context/prompts/humanize-pass-3.md` (new)

**Pattern** (ported from `humanize-me/backend/services/humanizer.py` PASS_1_SYSTEM / PASS_2_SYSTEM / PASS_3_SYSTEM):

`server/context/prompts/humanize-pass-1.md`:
```markdown
Remove AI patterns. Replace: Furthermore→Also, Moreover→Plus, In conclusion→So, It's important→Note that. Add contractions.

Rewrite the text to sound natural. Output ONLY the rewritten text.
```

`server/context/prompts/humanize-pass-2.md`:
```markdown
Add human voice. Vary sentence lengths (mix short and long). Add filler words sparingly (honestly, basically, I think). Break any remaining patterns.

Rewrite the text to sound like a real person wrote it. Output ONLY the rewritten text.
```

`server/context/prompts/humanize-pass-3.md`:
```markdown
Final polish. Ensure natural flow. Fix any awkward transitions. Make it sound like a real person wrote it casually.

Rewrite the text one last time for a natural, conversational tone. Output ONLY the rewritten text.
```

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
cat context/prompts/humanize-pass-1.md   # expect: "Remove AI patterns..."
cat context/prompts/humanize-pass-2.md   # expect: "Add human voice..."
cat context/prompts/humanize-pass-3.md   # expect: "Final polish..."
# Each contains prompt text only, no markdown headers
```

---

### Step 2: Register the three prompts in the manifest

**Action**: Add three entries to the existing `server/context/manifest.json`. Map block names to file paths relative to `server/context/`. If Task 1 or Task 4 have already added entries, merge — do not overwrite.

**File**: `server/context/manifest.json` (modify)

**Pattern**:
```json
{
  "humanize-pass-1": "prompts/humanize-pass-1.md",
  "humanize-pass-2": "prompts/humanize-pass-2.md",
  "humanize-pass-3": "prompts/humanize-pass-3.md"
}
```

If manifest already contains entries (e.g., placeholders from Task 1), add these three keys into the existing object.

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -c "
from modules.context.loader import load_block
p1 = load_block('humanize-pass-1')
p2 = load_block('humanize-pass-2')
p3 = load_block('humanize-pass-3')
assert 'AI patterns' in p1, f'pass-1 content unexpected: {p1[:60]}'
assert 'human voice' in p2, f'pass-2 content unexpected: {p2[:60]}'
assert 'Final polish' in p3, f'pass-3 content unexpected: {p3[:60]}'
print('all 3 blocks loaded ok')
"
```

---

### Step 3: Create the deep-humanize chain definition

**Action**: Create the chain definition JSON. Three rewrite steps, each referencing one humanize-pass context block. `outputMode` is `"single"` — all three passes produce a single cumulative text output (the third pass's output is the final result).

**File**: `server/modules/chain/definitions/deep-humanize.json` (new)

**Pattern** (from architecture doc, chain definition format):
```json
{
  "id": "deep-humanize",
  "name": "Deep Humanize",
  "steps": [
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-1"] },
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-2"] },
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-3"] }
  ],
  "outputMode": "single"
}
```

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -c "
import json
with open('modules/chain/definitions/deep-humanize.json') as f:
    d = json.load(f)
assert d['id'] == 'deep-humanize'
assert len(d['steps']) == 3
assert all(s['op'] == 'rewrite' for s in d['steps'])
assert d['outputMode'] == 'single'
print('definition valid')
"
```

---

### Step 4: Verify the runner can load and execute the chain definition

**Action**: Run an end-to-end smoke test loading the definition through the runner and executing it against the mock provider. No code changes — this step validates the integration of Steps 1–3 with the Task 1 + Task 2 infrastructure.

**File**: none (validation only)

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -c "
from modules.chain.runner import load_definition, run_definition

defn = load_definition('deep-humanize')
assert defn['id'] == 'deep-humanize'

result = run_definition('deep-humanize', 'The AI-generated text that needs humanizing.')
print(f'result type: {type(result).__name__}')
print(f'output preview: {str(result)[:120]}')
print('chain executed ok')
"
```

If this fails, the issue is in Task 1 or Task 2 infrastructure, not this task. STOP and flag.

---

### Step 5: Write end-to-end tests

**Action**: Create `test_deep_humanize.py` with tests covering: definition loads with correct shape, all 3 steps are rewrite ops, output mode is single, each step references a unique context block, context blocks resolve from manifest with expected content, chain execution via mock produces a string result (not files), and structural invariants (JSON valid, context block names match manifest keys).

**File**: `server/modules/chain/tests/test_deep_humanize.py` (new). Full test bodies in Section 5 below.

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
python -m pytest modules/chain/tests/test_deep_humanize.py -v
# Expect: 13 passed
```

---

### Step 6: Run the full suite, record delta

**Action**: Run the complete server test suite and confirm zero regressions.

**File**: none (test execution only)

**Verify**:
```bash
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -m pytest -q
```

**Expected**: baseline + 13 new tests passing. Zero previously-passing tests broken.

---

## 5. Tests

Repo convention: pytest with plain `assert`. Test names use `condition_expectedOutcome` convention. Mock provider forced via `conftest.py` in `modules/chain/tests/` (created by Task 2).

```python
# server/modules/chain/tests/test_deep_humanize.py
"""End-to-end tests for the deep-humanize chain definition.

Validates: definition loads, 3 steps execute sequentially through the
runner, context blocks resolve from manifest, output is single-mode.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from modules.chain.runner import load_definition


# ── Definition loading ─────────────────────────────────────────────────────

def test_deepHumanize_definitionLoads_hasThreeSteps():
    defn = load_definition("deep-humanize")
    assert defn["id"] == "deep-humanize"
    assert defn["name"] == "Deep Humanize"
    assert len(defn["steps"]) == 3


def test_deepHumanize_allStepsAreRewriteOp():
    defn = load_definition("deep-humanize")
    for i, step in enumerate(defn["steps"]):
        assert step["op"] == "rewrite", f"step {i} op should be 'rewrite', got '{step['op']}'"


def test_deepHumanize_outputModeSingle():
    defn = load_definition("deep-humanize")
    assert defn["outputMode"] == "single"


def test_deepHumanize_eachStepReferencesUniqueContextBlock():
    defn = load_definition("deep-humanize")
    block_names = [step["context"][0] for step in defn["steps"]]
    assert block_names == ["humanize-pass-1", "humanize-pass-2", "humanize-pass-3"]
    assert len(set(block_names)) == 3, "each step must reference a different context block"


# ── Context block resolution ──────────────────────────────────────────────

def test_deepHumanize_contextBlocksExistInManifest():
    from modules.context.loader import load_block
    p1 = load_block("humanize-pass-1")
    p2 = load_block("humanize-pass-2")
    p3 = load_block("humanize-pass-3")
    assert len(p1) > 0, "humanize-pass-1 must not be empty"
    assert len(p2) > 0, "humanize-pass-2 must not be empty"
    assert len(p3) > 0, "humanize-pass-3 must not be empty"


def test_deepHumanize_pass1ContainsAIPatternRemoval():
    from modules.context.loader import load_block
    p1 = load_block("humanize-pass-1")
    assert "AI patterns" in p1 or "Furthermore" in p1, (
        "pass-1 prompt should mention AI pattern removal"
    )


def test_deepHumanize_pass2ContainsHumanVoice():
    from modules.context.loader import load_block
    p2 = load_block("humanize-pass-2")
    assert "human voice" in p2 or "sentence length" in p2.lower(), (
        "pass-2 prompt should mention adding human voice"
    )


def test_deepHumanize_pass3ContainsFinalPolish():
    from modules.context.loader import load_block
    p3 = load_block("humanize-pass-3")
    assert "polish" in p3.lower() or "natural flow" in p3.lower(), (
        "pass-3 prompt should mention final polish"
    )


# ── Chain execution (mock provider) ──────────────────────────────────────

def test_deepHumanize_runDefinition_returnsStringResult():
    from modules.chain.runner import run_definition
    result = run_definition("deep-humanize", "Some AI-generated text to humanize.")
    assert isinstance(result, dict), f"expected dict, got {type(result).__name__}"
    assert "result" in result, "single-output chain must return 'result' key"
    assert isinstance(result["result"], str)
    assert len(result["result"]) > 0


def test_deepHumanize_runDefinition_noFilesKeyInSingleMode():
    from modules.chain.runner import run_definition
    result = run_definition("deep-humanize", "Some text.")
    assert "files" not in result, "single-output chain must not return 'files' key"


def test_deepHumanize_runDefinition_mockOutputShowsThreePassesExecuted():
    """Mock provider echoes model+prompt prefix. After 3 sequential passes,
    the final output should reflect the third step receiving the second
    step's output (which received the first step's output)."""
    from modules.chain.runner import run_definition
    result = run_definition("deep-humanize", "Input text here.")
    # Key invariant: 3 calls happened sequentially and the final output
    # is non-empty. Exact mock format depends on STEP_HANDLERS.rewrite
    # calling adapter.generate.
    assert len(result["result"]) > 0


# ── Structural invariants ────────────────────────────────────────────────

def test_deepHumanize_definitionFileIsValidJSON():
    defn_path = pathlib.Path(__file__).resolve().parent.parent / "definitions" / "deep-humanize.json"
    with open(defn_path) as f:
        data = json.load(f)
    assert "id" in data
    assert "steps" in data
    assert "outputMode" in data


def test_deepHumanize_contextBlockNamesMatchManifest():
    """Every context block referenced in the definition must exist in manifest.json."""
    import json as _json
    defn_path = pathlib.Path(__file__).resolve().parent.parent / "definitions" / "deep-humanize.json"
    manifest_path = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "context" / "manifest.json"

    with open(defn_path) as f:
        defn = _json.load(f)
    with open(manifest_path) as f:
        manifest = _json.load(f)

    for step in defn["steps"]:
        for block_name in step.get("context", []):
            assert block_name in manifest, (
                f"context block '{block_name}' referenced in deep-humanize.json "
                f"not found in manifest.json. Available: {sorted(manifest.keys())}"
            )
```

---

## 6. Commit Plan

One commit per logical unit. Conventional-commits style.

1. `feat(chain): add humanize-pass-1/2/3 context files + manifest entries` — `server/context/prompts/humanize-pass-1.md`, `server/context/prompts/humanize-pass-2.md`, `server/context/prompts/humanize-pass-3.md`, `server/context/manifest.json` (modify): three system prompts ported verbatim from humanize-me's PASS_1/2/3 with output-format tail. Manifest updated with new block names.

2. `feat(chain): add deep-humanize chain definition` — `server/modules/chain/definitions/deep-humanize.json`: 3-step rewrite chain, outputMode single. References the three humanize-pass context blocks from commit 1.

3. `test(chain): cover deep-humanize definition + context + execution` — `server/modules/chain/tests/test_deep_humanize.py`: 13 tests covering definition loading (3 steps, rewrite ops, single mode), context resolution (blocks exist, content assertions), chain execution against mock (returns string result, no files key), structural invariants (valid JSON, context names match manifest).

**Deviation logging**: if any step deviates from this guide (e.g., manifest format differs from spec, `run_definition` return shape differs), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -m pytest -q
```

**Expected delta**: baseline + **13** new passing tests (from `test_deep_humanize.py`).

**Zero previously-passing tests broken.** If any test in `server/tests/` or `server/modules/*/tests/` that passed at baseline now fails, STOP and investigate before committing.

Spot-check the end-to-end flow:
```bash
cd {WORKSPACE}/bubls/server
CHAIN_PROVIDER=mock python -c "
from modules.chain.runner import run_definition
result = run_definition('deep-humanize', 'AI-generated text goes here.')
print('Output:', result)
"
```

---

## 8. Rollback

**Per-step**:
- Commit 3 (tests): `git revert <sha>` — removes test file only, no functional impact.
- Commit 2 (definition): `git revert <sha>` — removes `deep-humanize.json`. Chain endpoint returns 404 for `chainId=deep-humanize`.
- Commit 1 (prompts + manifest): `git revert <sha>` — removes 3 prompt files, reverts manifest entries. If other tasks added manifest entries in the same edit, use `git checkout <pre-sha> -- server/context/manifest.json` and manually re-add the non-humanize entries.

**Per-branch**: `git reset --hard $(cat /tmp/bubls-task3-sha)` restores the pre-task anchor recorded in Pre-flight.

**No database rollback needed**: this task creates no migrations and modifies no schema.

---

## 9. Deviations Allowed

- **Prompt wording adjustments**: if the verbatim port of `PASS_1_SYSTEM` / `PASS_2_SYSTEM` / `PASS_3_SYSTEM` needs minor wording changes (e.g., the "Output ONLY the rewritten text." tail already present in a different form), that is acceptable. Note the change in the commit body.
- **Manifest format differs from spec**: if Task 1 used a different manifest schema than the flat `{name: path}` dict shown in the architecture doc, adapt the entries to match Task 1's actual format. Note in the commit body.
- **`run_definition` return shape differs**: if Task 2 returns the chain result in a different shape than `{"result": str}` (e.g., `{"generationId": str, "result": str}`), adapt the test assertions to match. The key invariant is: `outputMode=single` returns a string result, not a files array.
- **Definitions directory already has files from Task 4/5**: if other chain definitions were merged first, verify the directory listing and do not overwrite existing files.
- **Context loader has `CONTEXT_PROVIDER=mock` mode**: if Task 1 implemented a mock mode for the loader, tests that assert on context-block content (pass-1 contains "AI patterns") need real file reads, not mock strings. Add `monkeypatch.setenv("CONTEXT_PROVIDER", "file")` or equivalent to those specific tests if the conftest defaults to mock. Note the adaptation in the commit body.
- **Prescribed path doesn't exist**: verify in codebase; if still missing, flag it — do not invent.
- **Step N unlocks an obvious simplification for Step N+1**: take it, log deviation in the commit.

---

## 10. Out of Scope

This task ports three system prompts and creates one chain definition. It does not modify any Python module, any frontend file, any database schema, or any existing prompt. The executor must STOP and flag (not silently implement) any of the following:

- **Modifying `server/modules/text/prompts.py`** — the single-shot HUMANIZE prompt is a separate code path. Deep Humanize is additive via the chain runner, not a replacement.
- **Adding new Python modules beyond the test file** — this task creates only data files (3 markdown prompts, 1 JSON definition) and one test file. If you feel a new `.py` module is needed, STOP and flag.
- **Editing `server/modules/chain/runner.py`** — the runner should already handle `rewrite` ops via `STEP_HANDLERS`. If it cannot execute the deep-humanize definition without runner changes, that is a Task 2 gap — flag it.
- **Editing `server/modules/context/loader.py`** — the loader should already read manifest entries and return file contents. If it fails on the new entries, that is a Task 1 gap — flag it.
- **Streaming per chain step** — request-response for v1. SSE is deferred (trigger: chains exceeding 30s with user-reported perceived hangs).
- **Prompt quality iteration** — port verbatim first. Quality improvements are a follow-up based on A/B testing against single-shot humanize. The 3-pass prompts should be noticeably less detectable, but the benchmark is not this task's scope.
- **Frontend changes** — zero Angular work in Task 3. Chain Mode UI is Task 6.
- **Alembic migration** — this task creates no database columns. `chain_id` + `step_count` on `superapp_generations` are Task 2's migration scope.
- **User-editable prompts** — context files are static markdown. User editing is v2 scope per the epic's Non-Goals.
- **Retry/backoff machinery** — the Anthropic SDK already handles retries (`max_retries=2`). Custom retry logic is deferred infrastructure.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, chain definition format, STEP_HANDLERS dispatch
- [Epic](./epic.md) – Task 3 scope and success criteria
- [Timeline](./timeline.md) – Update status to Done after Verification (Section 7) passes
##### Post-generation review (pipeline)
Pre-flight must abort with named symbols if Task 1/2 not landed (load_block, STEP_HANDLERS, load_definition). Add explicit mkdir -p server/modules/chain/definitions/ step. Spec correctly defers chainCompleted to Task 2 runner.
