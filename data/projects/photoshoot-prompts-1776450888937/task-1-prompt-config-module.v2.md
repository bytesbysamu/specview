# Task 1: Prompt Config Module

**Purpose**: Create the prompt resolution layer that turns mode selection into formatted prompts for Replicate LoRA inference, replacing the single hardcoded template with a config-driven multi-mode system.

**Effort**: 0.5 day

**Dependencies**: None

**Parallel With**: Task 2 (OpenAPI + DTO update)

**Blocks**: Task 3 (Backend mode resolution — imports `resolve_prompt` from this module)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The photoshoot currently uses a single hardcoded template — `"a professional enhanced photo of {trigger_word}, high quality, natural lighting, sharp detail"` — which produces identical-looking output regardless of what the tester wants. The comparison run proved prompt quality is the primary lever on generation quality, not model quality. Trendfy's 5 outfit-specific prompts produced production-quality fashion photos with the same Replicate LoRA pipeline. This task creates a pure Python config module (`prompts.py`) that defines a `MODES` dict with style blocks for portrait and outfit modes, a shared negative prompt, and a `resolve_prompt` function that selects a random style from the mode's list and formats the base template. The module has zero I/O, zero imports beyond `random`, and is testable by calling functions directly. Task 3 will import and wire it into the service.

**Trade-offs considered**:
- **Database table for styles** — rejected because it requires a migration, admin endpoints, and cache logic for 3 modes and 15 TestFlight testers. A Python dict is git-versioned, testable in isolation, and zero infrastructure. The second consumer (admin UI, user preferences) hasn't appeared.
- **Keeping prompts inline in `service.py`** — rejected because the service already owns orchestration (model lookup, Replicate call, persistence). Adding mode resolution and 5+ multiline style strings would bloat it past the 30-line-per-endpoint target. Separation makes the prompts testable without spinning up Flask.
- **Config module with `resolve_prompt` as a pure function** — preferred because it's one file, zero dependencies, directly importable from both the service and test suite. Adding a mode later means adding a dict entry.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                           # Flag any unrelated M/?? entries
git diff HEAD -- server/modules/photoshoot/          # Confirm target directory is clean
cd {WORKSPACE} && python -m pytest server/tests/ -q  # Record baseline pass count
```

**If working tree is dirty on target files**: stash, or commit unrelated changes separately, BEFORE starting.

**Baseline recorded**: N/N passing.

---

## 3. Files

### To Create (new)
- `server/modules/photoshoot/prompts.py` — prompt config module: `PROMPT_TEMPLATE`, `NEGATIVE_PROMPT`, `MODES` dict, `resolve_prompt()` function
- `server/tests/test_prompts.py` — unit tests for prompt resolution (5 test cases)

### To Modify
- None — this task creates a standalone module. Wiring into `service.py` and `routes.py` is Task 3.

### To Leave Alone
- `server/modules/photoshoot/service.py` — still uses `DEFAULT_PROMPT_TEMPLATE` until Task 3 wires `resolve_prompt`
- `server/modules/photoshoot/routes.py` — no `mode` param extraction until Task 3
- `server/modules/photoshoot/__init__.py` — no re-exports needed; Task 3 imports `resolve_prompt` directly from `.prompts`
- `server/openapi/photoshoot.yaml` — schema changes are Task 2

---

## 4. Implementation Steps

### Step 1: Create the prompt config module

**Action**: Create `server/modules/photoshoot/prompts.py` with the base template, negative prompt, modes dict, and resolve function.

**File**: `server/modules/photoshoot/prompts.py` (new)

**Pattern**:
```python
"""Photoshoot prompt config — modes, styles, and prompt resolution.

Pure config module. No I/O, no database, no external imports beyond `random`.
Adding a mode = adding a dict entry. Removing = deleting one.
"""
import random


PROMPT_TEMPLATE = "a photo of {trigger}, {style}"

NEGATIVE_PROMPT = (
    "blurry, low quality, distorted face, extra limbs, "
    "watermark, text, oversaturated, cartoon, illustration"
)

MODES = {
    "portrait": {
        "label": "Portrait",
        "styles": [
            "wearing smart casual clothes, standing naturally in a modern studio setting "
            "with soft diffused lighting, clean background, relaxed natural expression, "
            "professional photography, 85mm lens, shallow depth of field"
        ],
    },
    "outfit": {
        "label": "Outfit",
        "styles": [
            # casual — ported from Trendfy
            "wearing casual everyday clothes, relaxed fit jeans and a comfortable top, "
            "walking through a sunlit city street, golden hour warm lighting, "
            "candid street photography style, natural stride, urban background",
            # formal — ported from Trendfy
            "wearing a tailored formal suit, crisp white shirt, polished shoes, "
            "standing confidently in an upscale lobby with marble floors, "
            "editorial lighting, sharp detail, full body shot, GQ magazine style",
            # streetwear — ported from Trendfy
            "wearing trendy streetwear, oversized hoodie, sneakers, layered accessories, "
            "leaning against a graffiti wall in an urban alley, moody ambient lighting, "
            "street photography, full body, hypebeast editorial style",
            # athleisure — ported from Trendfy
            "wearing athletic wear, fitted leggings and performance top, "
            "standing in a modern gym or outdoor track, bright natural lighting, "
            "fitness photography, dynamic pose, clean sporty aesthetic",
            # evening — ported from Trendfy
            "wearing elegant evening attire, flowing dress or sharp tuxedo, "
            "standing on a rooftop terrace at dusk, city skyline in background, "
            "warm ambient lighting with bokeh, glamour photography, full body",
        ],
    },
}


def resolve_prompt(
    trigger_word: str,
    mode: str,
    custom_style: str | None = None,
) -> dict[str, str]:
    """Resolve a mode + trigger word into a formatted prompt pair.

    Returns {"prompt": str, "negative_prompt": str}.

    Raises:
        ValueError: if mode is "custom" and custom_style is falsy.
        KeyError: if mode is not "custom" and not in MODES.
    """
    if mode == "custom":
        if not custom_style:
            raise ValueError("Custom mode requires a style string")
        style = custom_style
    else:
        if mode not in MODES:
            raise KeyError(f"Unknown mode: {mode}")
        style = random.choice(MODES[mode]["styles"])

    prompt = PROMPT_TEMPLATE.format(trigger=trigger_word, style=style)
    return {"prompt": prompt, "negative_prompt": NEGATIVE_PROMPT}
```

**Verify**: `python -c "from server.modules.photoshoot.prompts import resolve_prompt; r = resolve_prompt('ALICE', 'portrait'); assert 'ALICE' in r['prompt']; print('OK:', r['prompt'])"` — expect `OK: a photo of ALICE, wearing smart casual clothes...`

> **Note on Trendfy prompt strings**: The epic states these must be extracted from the wardrobai repo. The architecture document provides the exact strings marked as "ported from Trendfy." If the executor has access to the wardrobai repo (`server/` or `ai-models/lora-experiment.ipynb`), verify the strings match. If the wardrobai repo is not accessible, the strings from the architecture document are the canonical source — they were authored from the same braindump that informed the Trendfy product. Per the architecture's risk mitigation: "If exact strings aren't found, write new prompts matching the scenario intent — the descriptors are the value, not the exact wording."

### Step 2: Create the test module

**Action**: Create `server/tests/test_prompts.py` with 5 test cases covering all modes, error cases, and the random-selection behavior.

**File**: `server/tests/test_prompts.py` (new)

**Pattern**:
```python
"""Tests for server.modules.photoshoot.prompts — prompt config and resolution."""
import pytest

from server.modules.photoshoot.prompts import (
    MODES,
    NEGATIVE_PROMPT,
    PROMPT_TEMPLATE,
    resolve_prompt,
)


class TestResolvePrompt:
    def test_portrait_resolvesPrompt_containsTriggerWord(self):
        result = resolve_prompt("ALICE", "portrait")
        assert "ALICE" in result["prompt"], (
            f"Trigger word missing from portrait prompt: {result['prompt']}"
        )
        assert result["negative_prompt"] == NEGATIVE_PROMPT
        assert result["prompt"].startswith("a photo of ALICE, ")

    def test_outfit_resolvesPrompt_randomFromFiveScenarios(self):
        """Call resolve_prompt 50 times — all 5 outfit styles must appear."""
        seen_styles = set()
        for _ in range(50):
            result = resolve_prompt("BOB", "outfit")
            # Extract the style portion after "a photo of BOB, "
            style = result["prompt"].removeprefix("a photo of BOB, ")
            seen_styles.add(style)
        assert len(seen_styles) == 5, (
            f"Expected 5 distinct outfit styles after 50 calls, got {len(seen_styles)}. "
            f"Missing styles indicate a config error in MODES['outfit']['styles']."
        )

    def test_custom_resolvesPrompt_usesCustomStyle(self):
        custom = "wearing a dinosaur costume in a library"
        result = resolve_prompt("CAROL", "custom", custom_style=custom)
        assert custom in result["prompt"], (
            f"Custom style not found in prompt: {result['prompt']}"
        )
        assert "CAROL" in result["prompt"]
        assert result["negative_prompt"] == NEGATIVE_PROMPT

    def test_custom_emptyStyle_raisesValueError(self):
        with pytest.raises(ValueError, match="Custom mode requires a style string"):
            resolve_prompt("DAVE", "custom", custom_style="")

    def test_unknownMode_raisesKeyError(self):
        with pytest.raises(KeyError, match="Unknown mode: banana"):
            resolve_prompt("EVE", "banana")
```

**Verify**: `cd {WORKSPACE} && python -m pytest server/tests/test_prompts.py -v` — expect 5/5 passing.

### Step 3: Verify config completeness

**Action**: Manually verify the `MODES` dict structure is consistent — each mode has a `"label"` (string) and `"styles"` (non-empty list of strings). This step is a read-only audit, not a code change.

**File**: `server/modules/photoshoot/prompts.py` (read only)

**Verify**: `python -c "from server.modules.photoshoot.prompts import MODES; [print(f'{k}: {v[\"label\"]}, {len(v[\"styles\"])} styles') for k, v in MODES.items()]"` — expect:
```
portrait: Portrait, 1 styles
outfit: Outfit, 5 styles
```

---

## 5. Tests

Complete assertion bodies above in Step 2. Test framework is **pytest** (matches existing `server/tests/` convention). All 5 tests are wrapped in a `class TestResolvePrompt` to avoid the known pytest `python_functions` caveat that collects bare helper functions as tests.

Test naming follows `condition_expectedOutcome` convention (no "should").

| Test | What it verifies |
|------|------------------|
| `test_portrait_resolvesPrompt_containsTriggerWord` | Trigger word appears in formatted prompt; negative prompt is the shared constant |
| `test_outfit_resolvesPrompt_randomFromFiveScenarios` | All 5 Trendfy styles appear after 50 calls (statistical; failure = config error) |
| `test_custom_resolvesPrompt_usesCustomStyle` | Custom string appears verbatim; trigger word still present |
| `test_custom_emptyStyle_raisesValueError` | Falsy custom_style raises ValueError with message |
| `test_unknownMode_raisesKeyError` | Invalid mode raises KeyError with mode name in message |

---

## 6. Commit Plan

One commit — this is a single logical unit (config module + its tests):

1. `feat(photoshoot): add prompt config module with mode-based resolution` — `server/modules/photoshoot/prompts.py`, `server/tests/test_prompts.py`: Pure config module defining portrait mode (1 improved style), outfit mode (5 Trendfy-ported styles), shared negative prompt, and `resolve_prompt` function. Not yet wired into the service (Task 3).

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE} && python -m pytest server/tests/test_prompts.py -v
```

**Expected delta**: N → N+5 passing. Zero pre-existing tests broken.

Also run the full suite to confirm no regressions:

```bash
cd {WORKSPACE} && python -m pytest server/tests/ -q
```

---

## 8. Rollback

- **Per-step**: single commit, independently revertible. `git revert <sha>`.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch. No database migrations, no schema changes, no side effects — rollback is clean.
- **Zero blast radius**: this module is not imported by any existing code until Task 3 wires it. Reverting leaves the codebase in its current working state.

---

## 9. Deviations Allowed

- **Trendfy prompt strings differ from architecture doc**: If the executor has access to the wardrobai repo and the exact strings differ from what the architecture document specifies, use the wardrobai originals and log the difference as a deviation. The architecture strings are authoritative if wardrobai is inaccessible.
- **pytest import path differs**: If `from server.modules.photoshoot.prompts import ...` fails due to project layout (missing `__init__.py`, different sys.path convention), adjust the import to match the repo's existing test import pattern. Log the deviation.
- **Additional prompt descriptors needed**: If the portrait style string needs adjustment after visual comparison with the old default (`"a professional enhanced photo of {trigger_word}, high quality, natural lighting, sharp detail"`), the executor may refine descriptors. Log what changed and why.
- **`MODES` structure adjustment**: If downstream Task 3 reveals that `label` is never read, the executor should still keep it — it's cheap and useful for logging/debugging. Do not strip it preemptively.

---

## 10. Out of Scope

This task creates the config module in isolation. It does NOT wire it into the photoshoot service, modify the API contract, or touch the frontend. Those are separate tasks with their own guides.

- **Wiring `resolve_prompt` into `service.py`** — Task 3. This task only creates the module; it is importable but not imported.
- **OpenAPI `mode` enum and DTO regeneration** — Task 2. The config module doesn't depend on the API schema.
- **`negative_prompt` passthrough to Replicate** — Task 3. Whether Replicate's model accepts `negative_prompt` as an input parameter needs to be checked during Task 3 wiring, not here.
- **Dropping `lora_models.default_style_prompt` column** — explicitly deferred (no Alembic migration). The column stays unused.
- **Individual scenario picker within outfit mode** — deferred to v2; trigger is testers asking "I want the streetwear one again."
- **Content moderation for custom mode** — deferred until public launch; TestFlight audience is 15 known testers.
- **Prompt versioning or A/B testing** — change the dict, deploy, compare outputs visually. No infrastructure until there's signal.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, component design, design decisions
- [Epic](./epic.md) – Task scope, success criteria, non-goals
- [Timeline](./timeline.md) – Status tracking (update after done)
- [Photoshoot Task 3](../photoshoot-1776260020498/task-3-photo-capture-and-generation-pipeline.md) – Current prompt construction code (`DEFAULT_PROMPT_TEMPLATE` at line 266)