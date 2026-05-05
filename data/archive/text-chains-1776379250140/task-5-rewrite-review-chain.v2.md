# Task 5: Rewrite + Review Chain

**Purpose**: Define the third chain operation — a three-step cycle that rewrites user text, reviews the result against a quality rubric, and applies a fix pass based on the review's flagged issues.

**Effort**: 0.5 day

**Dependencies**: Task 1 (Context Block Loader) + Task 2 (Chain Runner + Endpoint) must be landed. Task 2 provides `POST /api/text/chain`, `STEP_HANDLERS` dispatch, the runner loop, and the `superapp_generations` persistence with `chain_id` + `step_count` columns. Task 1 provides `load_block()` / `load_blocks()` via the manifest.

**Parallel With**: Task 3 (Deep Humanize), Task 4 (Braindump to Docs)

**Blocks**: Task 6 (Chain Mode UI), Task 7 (Integration Test + QA)

**Related**:
- [Architecture](./architecture.md) — Chain Definition schema, STEP_HANDLERS dispatch, review-step JSON contract
- [Epic](./epic.md) — Task 5 detail, success criteria

---

## 1. Context

The Rewrite + Review chain is the quality-assurance loop: step 1 rewrites with the user's selected mode, step 2 reviews against the quality rubric and returns structured JSON (`{ scores, issues }`), step 3 rewrites again with the issues injected as fix instructions. The chain definition JSON is the simplest of the three chains — three steps, no multi-file output, no context blocks on the rewrite steps (those inherit the user's mode prompt via `STEP_HANDLERS["rewrite"]`). The novel work is the review-step JSON parsing and the injection of flagged issues into step 3's rewrite instruction.

The quality rubric context block (`server/context/rubrics/quality.md`) must already exist from Task 1. This task creates the chain definition, writes the `handle_review` JSON-parsing logic inside the runner's step handler, and wires the fix-step instruction injection.

**Trade-offs considered**:
- **LLM-authored JSON vs. structured output with tool_use** — chose plain JSON in the review prompt's output format. `tool_use` adds SDK coupling to the review handler; plain JSON with a `json.loads` + fallback is simpler and the rubric prompt can enforce the shape. If parsing fails consistently, the trigger to switch is three failed reviews in production telemetry.
- **Separate `handle_fix` handler vs. reusing `handle_rewrite` with injected instruction** — chose reuse. A "fix" rewrite is the same adapter call as any other rewrite; the only difference is the system prompt includes the issues list. Adding a fourth handler would duplicate the adapter call for no behavioral difference. The `mode: "fix"` field in the chain definition signals the runner to inject issues into the prompt, not to dispatch to a different function.
- **Review step returns full rubric scores vs. issues-only** — chose full `{ scores, issues }` so analytics can subscribe to score distributions via the `chainCompleted` event metadata. Issues-only would lose the signal that makes future quality dashboards possible.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status
git diff HEAD -- server/modules/chain/ server/context/
cd server && pytest -q                          # Record BE baseline: [N passing]
cd .. && npm test -- --watch=false --browsers=ChromeHeadless  # Record FE baseline (untouched)
```

**Pre-conditions**:
- `ls server/modules/chain/runner.py` prints a hit. If not, STOP — Task 2 not landed.
- `ls server/context/manifest.json` prints a hit. If not, STOP — Task 1 not landed.
- `python -c "from modules.chain.runner import STEP_HANDLERS; print(sorted(STEP_HANDLERS))"` must print at least `['generate', 'rewrite']`. If `review` is already present, skip Step 2 below and log as deviation.
- `python -c "from modules.context.loader import load_block; print(load_block('quality-rubric')[:40])"` must return content. If it raises `KeyError`, STOP — the rubric context block from Task 1 is missing.

**Baseline recorded**: fill in `[BE: N/N passing]` in commit bodies.

---

## 3. Files

### To Create (new)
- `server/modules/chain/definitions/rewrite-review.json` — chain definition: three steps (rewrite, review, rewrite-fix), `outputMode: "single"`.

### To Modify
- `server/modules/chain/runner.py` — add `handle_review` to `STEP_HANDLERS` dispatch map; add review-JSON parsing helper `_parse_review_json(text: str) -> dict`; add fix-instruction injection logic that reads the prior step's `issues` array and injects it into the next rewrite step's prompt.
- `server/modules/chain/types.py` — add `ReviewResult` dataclass: `scores: dict[str, float]`, `issues: list[str]`, `raw: str`. Used by `handle_review` to normalize the LLM's JSON output before passing to the fix step.
- `server/modules/chain/tests/test_runner.py` — add tests for `handle_review` JSON parsing, fix-step injection, and the full rewrite-review chain end-to-end via mock provider.

### To Leave Alone
- `server/modules/chain/adapter.py` — the adapter already exposes `generate()` which `handle_review` calls. No changes needed.
- `server/modules/chain/providers/` — mock provider already returns deterministic strings; review tests mock at the runner level, not the provider level.
- `server/modules/chain/context.py` — context injection happens at the adapter boundary; this task does not change it.
- `server/modules/text/` — text module routes, service, and prompts are untouched; chain definitions are consumed by the chain runner, not the text module.
- `server/context/rubrics/quality.md` — created by Task 1; this task reads it, does not modify it.
- `server/context/manifest.json` — `quality-rubric` entry created by Task 1; this task reads it, does not modify it.
- `src/app/` — no frontend changes in this task; Task 6 wires the UI.

---

## 4. Implementation Steps

### Step 1: Add `ReviewResult` dataclass to `types.py`

**Action**: Add a frozen dataclass that normalizes the review step's JSON output into a typed contract. This keeps the LLM's output format from leaking into the runner loop.

**File**: `server/modules/chain/types.py`

**Pattern**:
```python
@dataclass(frozen=True)
class ReviewResult:
    """Normalized review output. ``issues`` feeds the fix step; ``scores`` feeds analytics."""
    scores: dict[str, float]
    issues: list[str]
    raw: str
```

**Verify**:
```bash
cd server && python -c "from modules.chain.types import ReviewResult; print(ReviewResult(scores={'clarity': 0.8}, issues=['passive voice'], raw='{}'))"
```

### Step 2: Add `handle_review` to `STEP_HANDLERS` in `runner.py`

**Action**: Implement `handle_review(text, context_blocks, **kwargs) -> str` that: (a) builds a review prompt from the user's text + quality-rubric context block, (b) calls `adapter.generate()` with the review system prompt, (c) parses the response as JSON via `_parse_review_json()`, (d) returns the raw review JSON string as the step output (so the runner can forward it to the next step). Add a `_parse_review_json(text: str) -> dict` helper that extracts JSON from the LLM response (handles markdown code fences, leading/trailing whitespace). Register `"review": handle_review` in `STEP_HANDLERS`.

**File**: `server/modules/chain/runner.py`

**Pattern**:
```python
import json
import re

from modules.chain import adapter
from modules.context import loader
from .types import ReviewResult


def _parse_review_json(text: str) -> dict:
    """Extract JSON from LLM review output. Handles ```json fences."""
    cleaned = text.strip()
    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


def handle_review(
    text: str,
    context_blocks: dict[str, str],
    *,
    user=None,
    feature: str | None = None,
    **kwargs,
) -> str:
    """Review step: evaluate text against rubric, return structured JSON."""
    rubric = "\n\n".join(context_blocks.values()) if context_blocks else ""
    system = (
        "You are a quality reviewer. Evaluate the following text against the rubric below.\n\n"
        f"## Rubric\n{rubric}\n\n"
        "Respond with ONLY valid JSON in this exact shape:\n"
        '{"scores": {"<criterion>": <0.0-1.0>, ...}, "issues": ["<issue description>", ...]}'
    )
    result = adapter.generate(system=system, prompt=text, user=user, feature=feature)
    return result.text


STEP_HANDLERS: dict[str, Callable] = {
    "rewrite": handle_rewrite,
    "generate": handle_generate,
    "review": handle_review,
}
```

**Verify**:
```bash
cd server && python -c "from modules.chain.runner import STEP_HANDLERS; assert 'review' in STEP_HANDLERS; print('OK: review handler registered')"
```

### Step 3: Add fix-step instruction injection to the runner loop

**Action**: Modify the runner's step-execution loop so that when a step has `"mode": "fix"`, the runner parses the previous step's output as review JSON (via `_parse_review_json`), extracts the `issues` array, and prepends it as fix instructions to the current step's prompt. The injection format: `"Fix the following issues:\n- {issue1}\n- {issue2}\n\nOriginal text:\n{text}"`. If review JSON parsing fails, the fix step receives the raw previous output as-is (graceful degradation) and logs a warning.

**File**: `server/modules/chain/runner.py`

**Pattern**:
```python
import logging

_log = logging.getLogger(__name__)


def _inject_fix_instructions(review_output: str, original_text: str) -> str:
    """Build the fix-step prompt by extracting issues from review JSON."""
    try:
        parsed = _parse_review_json(review_output)
        issues = parsed.get("issues", [])
        if not issues:
            return original_text
        bullet_list = "\n".join(f"- {issue}" for issue in issues)
        return f"Fix the following issues:\n{bullet_list}\n\nOriginal text:\n{original_text}"
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        _log.warning("Failed to parse review JSON for fix injection: %s", exc)
        return original_text
```

In the runner loop, when iterating steps from the chain definition, check if `step.get("mode") == "fix"` and the previous step's `op == "review"`. If so, call `_inject_fix_instructions(prev_output, original_input)` to build the prompt for the fix step instead of passing the raw previous output.

**Verify**:
```bash
cd server && python -c "
from modules.chain.runner import _parse_review_json, _inject_fix_instructions
review = '{\"scores\": {\"clarity\": 0.6}, \"issues\": [\"passive voice\", \"run-on sentence\"]}'
result = _inject_fix_instructions(review, 'The ball was thrown.')
assert 'passive voice' in result
assert 'run-on sentence' in result
assert 'The ball was thrown.' in result
print('OK: fix injection works')
"
```

### Step 4: Create the chain definition JSON

**Action**: Write the `rewrite-review.json` chain definition. Three steps: (1) rewrite with `mode: "user-selected"` (the runner resolves this to the caller's requested mode at runtime), (2) review against `quality-rubric`, (3) rewrite with `mode: "fix"` (runner injects issues). `outputMode: "single"`.

**File**: `server/modules/chain/definitions/rewrite-review.json` (new)

**Pattern**:
```json
{
  "id": "rewrite-review",
  "name": "Rewrite + Review",
  "steps": [
    { "op": "rewrite", "mode": "user-selected", "context": [] },
    { "op": "review", "context": ["quality-rubric"] },
    { "op": "rewrite", "mode": "fix", "context": [] }
  ],
  "outputMode": "single"
}
```

**Verify**:
```bash
cd server && python -c "
import json, pathlib
d = json.loads(pathlib.Path('modules/chain/definitions/rewrite-review.json').read_text())
assert d['id'] == 'rewrite-review'
assert len(d['steps']) == 3
assert d['steps'][1]['op'] == 'review'
assert d['steps'][2]['mode'] == 'fix'
assert d['outputMode'] == 'single'
print('OK: chain definition valid')
"
```

### Step 5: Add `_parse_review_json` tests

**Action**: Add focused unit tests for JSON parsing: clean JSON, JSON in code fences, malformed JSON fallback, empty issues array.

**File**: `server/modules/chain/tests/test_runner.py`

**Pattern**: see Section 5.

**Verify**:
```bash
cd server && pytest modules/chain/tests/test_runner.py -q
```

### Step 6: Add fix-injection tests

**Action**: Add unit tests for `_inject_fix_instructions`: issues extracted and formatted, empty issues returns original text, malformed JSON returns original text with warning.

**File**: `server/modules/chain/tests/test_runner.py`

**Pattern**: see Section 5.

**Verify**:
```bash
cd server && pytest modules/chain/tests/test_runner.py -q
```

### Step 7: Add end-to-end chain test with mock provider

**Action**: Test the full rewrite-review chain via the runner with mock provider. Verify three steps execute sequentially, review step receives the rewrite output, fix step receives injected instructions. Since the mock provider returns deterministic `MOCK[...]` strings (not real JSON), the fix-injection graceful degradation path activates — assert the chain completes without error and the final output is a string.

**File**: `server/modules/chain/tests/test_runner.py`

**Pattern**: see Section 5.

**Verify**:
```bash
cd server && pytest modules/chain/tests/test_runner.py -q -v
```

---

## 5. Tests

Framework: pytest (matching `server/modules/chain/tests/`). Naming: `test_condition_expectedOutcome`. Mock provider forced via `conftest.py` fixture.

### `server/modules/chain/tests/test_runner.py` additions

```python
# ── Review JSON parsing ──────────────────────────────────────────────

def test_parseReviewJson_cleanJson_returnsDict():
    from modules.chain.runner import _parse_review_json
    result = _parse_review_json('{"scores": {"clarity": 0.8}, "issues": ["vague"]}')
    assert result["scores"]["clarity"] == 0.8
    assert result["issues"] == ["vague"]


def test_parseReviewJson_jsonInCodeFence_extractsContent():
    from modules.chain.runner import _parse_review_json
    text = '```json\n{"scores": {"tone": 0.9}, "issues": []}\n```'
    result = _parse_review_json(text)
    assert result["scores"]["tone"] == 0.9
    assert result["issues"] == []


def test_parseReviewJson_malformedJson_raisesValueError():
    from modules.chain.runner import _parse_review_json
    import json
    with pytest.raises(json.JSONDecodeError):
        _parse_review_json("not json at all")


def test_parseReviewJson_jsonWithLeadingWhitespace_parses():
    from modules.chain.runner import _parse_review_json
    result = _parse_review_json('  \n  {"scores": {}, "issues": ["x"]}  \n  ')
    assert result["issues"] == ["x"]


# ── Fix-instruction injection ────────────────────────────────────────

def test_injectFixInstructions_withIssues_formattedAsBullets():
    from modules.chain.runner import _inject_fix_instructions
    review = '{"scores": {"clarity": 0.5}, "issues": ["passive voice", "run-on"]}'
    result = _inject_fix_instructions(review, "The ball was thrown by him.")
    assert "- passive voice" in result
    assert "- run-on" in result
    assert "The ball was thrown by him." in result
    assert result.startswith("Fix the following issues:")


def test_injectFixInstructions_emptyIssues_returnsOriginalText():
    from modules.chain.runner import _inject_fix_instructions
    review = '{"scores": {"clarity": 0.9}, "issues": []}'
    result = _inject_fix_instructions(review, "Clean text.")
    assert result == "Clean text."


def test_injectFixInstructions_malformedJson_returnsOriginalText():
    from modules.chain.runner import _inject_fix_instructions
    result = _inject_fix_instructions("not json", "Original.")
    assert result == "Original."


def test_injectFixInstructions_missingIssuesKey_returnsOriginalText():
    from modules.chain.runner import _inject_fix_instructions
    review = '{"scores": {"clarity": 0.7}}'
    result = _inject_fix_instructions(review, "Some text.")
    assert result == "Some text."


# ── handle_review handler ────────────────────────────────────────────

def test_handleReview_callsAdapterGenerate_returnsText():
    from modules.chain.runner import handle_review
    result = handle_review(
        "Some text to review.",
        context_blocks={"quality-rubric": "Score clarity 0-1."},
    )
    # Mock provider returns MOCK[model]::sys=...::prompt=...
    assert isinstance(result, str)
    assert len(result) > 0


# ── End-to-end rewrite-review chain ─────────────────────────────────

def test_rewriteReviewChain_threeSteps_completesWithFinalOutput():
    """Full chain with mock provider. The review step returns mock text
    (not real JSON), so fix-injection gracefully degrades — the chain
    still completes and produces a string output."""
    from modules.chain.runner import STEP_HANDLERS
    assert "review" in STEP_HANDLERS, "review handler must be registered"

    # Simulate the runner loop for three steps
    from modules.chain import adapter
    from modules.chain.runner import _inject_fix_instructions

    # Step 1: rewrite
    step1_result = adapter.generate(
        system="You rewrite text.", prompt="Fix my text please."
    )
    assert isinstance(step1_result.text, str)

    # Step 2: review (mock returns non-JSON, that's fine)
    review_result = adapter.generate(
        system="You are a reviewer.", prompt=step1_result.text
    )
    assert isinstance(review_result.text, str)

    # Step 3: fix (graceful degradation — mock output isn't JSON)
    fix_prompt = _inject_fix_instructions(review_result.text, step1_result.text)
    step3_result = adapter.generate(system="You fix text.", prompt=fix_prompt)
    assert isinstance(step3_result.text, str)
    assert len(step3_result.text) > 0
```

---

## 6. Commit Plan

1. `feat(chain): add ReviewResult type to chain.types` — `server/modules/chain/types.py`: frozen dataclass with `scores`, `issues`, `raw` fields.

2. `feat(chain): handle_review handler + JSON parsing + fix injection` — `server/modules/chain/runner.py`: `_parse_review_json()`, `_inject_fix_instructions()`, `handle_review()`, registration in `STEP_HANDLERS`, fix-mode detection in runner loop.

3. `feat(chain): rewrite-review chain definition` — `server/modules/chain/definitions/rewrite-review.json`: three-step chain, `outputMode: "single"`.

4. `test(chain): cover review parsing, fix injection, e2e chain` — `server/modules/chain/tests/test_runner.py`: 9 new test functions.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd server && pytest -q
```

**Expected delta**: BE `[N]` -> `[N+9]` passing (4 parse tests + 4 injection tests + 1 handler test). Zero pre-existing tests broken. FE untouched.

**Structural check** (should already pass from Task 2):
```bash
cd server && pytest modules/chain/tests/test_adapter.py::test_featureModules_mustNotImportProvidersDirectly -v
```

**Chain definition validation**:
```bash
cd server && python -c "
import json, pathlib
d = json.loads(pathlib.Path('modules/chain/definitions/rewrite-review.json').read_text())
manifest = json.loads(pathlib.Path('context/manifest.json').read_text()) if pathlib.Path('context/manifest.json').exists() else {}
for step in d['steps']:
    for ctx in step.get('context', []):
        assert ctx in manifest, f'Context block {ctx!r} not in manifest'
print('OK: all context refs resolve')
"
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any one unit.
  - Commit 1 (types): reverts a single dataclass addition; no consumers outside this task.
  - Commit 2 (handler): reverts handler + parsing; chain definitions that reference `"review"` will fail at runtime (acceptable if Task 5 is fully rolled back).
  - Commit 3 (definition): reverts a single JSON file; the endpoint returns 404 for `chainId: "rewrite-review"` which is the correct behavior for an undefined chain.
  - Commit 4 (tests): reverts test additions only; no production impact.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the feature branch. No migrations in this task (Task 2 owns the Alembic migration). No shared-module changes beyond the chain module boundary.

---

## 9. Deviations Allowed

- **`STEP_HANDLERS` dict location differs from `runner.py`** — if Task 2 placed the dispatch map in a separate file (e.g., `handlers.py`), add `handle_review` there instead; update imports; log in commit body.
- **Runner loop already supports `mode: "fix"` injection** — if Task 2 or Task 3 already implemented fix-mode detection, skip the injection logic in Step 3; verify with existing tests; log in commit body.
- **`handle_review` already exists from Task 4** — if braindump-to-docs (Task 4) already registered `handle_review`, skip Step 2's handler creation but still verify the JSON-parsing and fix-injection logic exist or add them; log in commit body.
- **Context loader interface differs** — if Task 1 named the function `get_block()` instead of `load_block()`, use the actual name; log in commit body.
- **Chain definitions directory does not exist yet** — create `server/modules/chain/definitions/` as part of Step 4; log in commit body.
- **`_parse_review_json` already exists** — if Task 4's review step already has the same helper, reuse it; do not duplicate; log in commit body.
- **Side-effect required** (push, publish, migration) — STOP and mark `[REQUIRES APPROVAL]`. This task should not need any.

---

## 10. Out of Scope

The executor must STOP and flag (not absorb) any of the following:

- **Retry logic for failed review JSON parsing** — if the LLM returns invalid JSON, the fix step degrades gracefully. Retry machinery is deferred infrastructure; trigger: three consecutive parse failures in production telemetry.
- **Streaming per chain step** — request-response for v1. SSE deferred per architecture doc.
- **Quality rubric editing UI** — user-editable context blocks are v2.
- **Score persistence / analytics dashboard** — the `chainCompleted` event carries scores via metadata; a dashboard is a future task.
- **Frontend changes** — Task 6 owns the chain mode UI. This task is backend-only.
- **Modifying the quality rubric content** — Task 1 owns `server/context/rubrics/quality.md`. If the rubric is empty or unhelpful, flag it; do not rewrite it here.
- **Adding `rewrite-review` to the OpenAPI spec** — Task 2 owns the `/api/text/chain` endpoint and its OpenAPI definition. Chain definitions are runtime data, not new API routes.
- **Per-chain feature gating** — single `text_chains` flag for v1. Splitting per-chain is deferred until pricing tiers diverge.
- **Extracting a `RunnerAdapter` interface** — deferred until a second execution strategy appears (parallel, streaming, retry).

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) -- STEP_HANDLERS dispatch, review JSON contract, anti-corruption layer
- [Epic](./epic.md) -- Task 5 detail, success criteria
- [Timeline](./timeline.md) -- Status tracking (update after done)

##### Post-generation review (pipeline)
Quality rubric is Task 4 dep (not Task 1 as cited). Pre-flight should test for handle_rewrite + handle_generate explicitly. Add one e2e test through run_definition() not just adapter.generate() calls. Add structural test pinning handle_review to adapter boundary.
