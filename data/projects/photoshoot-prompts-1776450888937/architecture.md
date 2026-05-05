
```markdown
---
sidebar_position: 3
---

# 🏗️ Modular Photoshoot Modes – Solution Architecture

**Purpose**: Technical design for the prompt config layer and mode picker.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This is a config change with a thin API surface, not a feature build. The architecture adds one layer to the existing inference pipeline: a prompt resolution step between the photoshoot service and the Replicate adapter. Today the service hardcodes `DEFAULT_PROMPT_TEMPLATE.format(trigger_word=trigger_word)` and passes the result to `ReplicateService`. After this epic, the service calls `resolve_prompt(trigger_word, mode, custom_style)` which returns a `{"prompt": str, "negative_prompt": str}` dict by looking up the mode in a config dict and formatting the base template.

The config dict lives in a single Python module (`server/modules/photoshoot/prompts.py`). No database table, no admin UI, no API to manage styles. Adding a mode means adding an entry to the dict and a value to the OpenAPI enum. Removing a mode means the reverse. The module is importable and testable in isolation — `resolve_prompt` is a pure function with no I/O.

The frontend change is a single `ion-segment` control on the photoshoot page. It sends a `mode` string in the generate request. The backend validates it against the enum. The segmented control follows the immersive photoshoot world's visual language from the UX revamp.

No new Replicate models. No new inference parameters. No new database columns or migrations. No new adapters. No new services.

---

## System Boundaries

### What This System Includes

- `server/modules/photoshoot/prompts.py` — prompt config module (modes, styles, negative prompt, resolve function)
- `server/openapi/photoshoot.yaml` — `mode` and `custom_style` fields on generate request
- `server/modules/photoshoot/service.py` — replace hardcoded template with `resolve_prompt` call
- `server/modules/photoshoot/routes.py` — extract `mode` and `custom_style` from request
- `src/app/pages/photoshoot/photoshoot.page.ts` — segmented control mode picker + custom textarea
- `src/app/services/photoshoot-api.service.ts` — `mode` and `custom_style` in multipart payload

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| `prompt_styles` database table | Config dict is simpler, testable, versionable in git; DB adds migration, admin UI, and cache for zero users asking for it |
| Content moderation for custom mode | TestFlight-only audience of 15 known testers; moderation adds a Claude API call per generation for a problem that doesn't exist yet |
| Inference parameter tuning per mode | `guidance_scale=7.5` and `num_inference_steps=28` work well across all tested scenarios; per-mode tuning is optimization without signal |
| Individual Trendfy scenario picker | 5-scenario picker is decision fatigue; random selection within "outfit" proves variety, testers requesting specific scenarios is the trigger to expose them |
| Prompt versioning or A/B testing | Change the dict, deploy, compare outputs manually — infrastructure for something that can be done by eye at 15-user scale |

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Config not DB | Style blocks stored in a Python dict, versioned in git, testable in isolation — no migration, no admin UI, no cache |
| Adapter boundary holds | `ReplicateService` interface unchanged — it receives `prompt`, `negative_prompt`, `image`, and inference params. The config module sits upstream, within the feature service |
| OpenAPI-first | `mode` enum and `custom_style` field added to YAML first; TS types and Pydantic DTOs regenerated, not hand-edited |
| Feature = bounded context | All changes stay within `photoshoot/` (backend) and `pages/photoshoot/` (frontend). No new shared modules. No cross-feature imports |
| Not-yet-built is the right state | No prompt management service, no style gallery, no favorites system — concrete need is 3 modes, concrete solution is a dict |

---

## Component Design

### Task 1: Prompt Config Module (`server/modules/photoshoot/prompts.py`)

**Purpose**: Single source of truth for all photoshoot prompt construction.

**Components**:
- `PROMPT_TEMPLATE = "a photo of {trigger}, {style}"` — base template, not an f-string
- `NEGATIVE_PROMPT = "blurry, low quality, distorted face, extra limbs, watermark, text, oversaturated, cartoon, illustration"` — shared across all modes
- `MODES: dict[str, dict]` — keyed by mode name, each containing:
  - `"label"`: human-readable name (for future UI/logging)
  - `"styles"`: list of style block strings
- `resolve_prompt(trigger_word: str, mode: str, custom_style: str | None = None) -> dict` — pure function

**Config structure**:
```python
MODES = {
    "portrait": {
        "label": "Portrait",
        "styles": [
            "wearing smart casual clothes, standing naturally in a modern studio setting "
            "with soft diffused lighting, clean background, relaxed natural expression, "
            "professional photography, 85mm lens, shallow depth of field"
        ]
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
            "warm ambient lighting with bokeh, glamour photography, full body"
        ]
    }
}
```

**`resolve_prompt` logic**:
1. If `mode == "custom"` and `custom_style` is truthy: use `custom_style` as style block
2. If `mode == "custom"` and `custom_style` is falsy: raise `ValueError("Custom mode requires a style string")`
3. If `mode` not in `MODES`: raise `KeyError(f"Unknown mode: {mode}")`
4. Select a random style from `MODES[mode]["styles"]` using `random.choice`
5. Format `PROMPT_TEMPLATE` with `trigger=trigger_word` and `style=selected_style`
6. Return `{"prompt": formatted_prompt, "negative_prompt": NEGATIVE_PROMPT}`

**Patterns**: Pure function, no I/O, no database, no imports beyond `random`. Testable by calling `resolve_prompt` directly and asserting on the returned dict.

### Task 2: OpenAPI + DTO Update

**Purpose**: Extend the generate contract with mode selection.

**Components**:
- `server/openapi/photoshoot.yaml` — add `mode` (enum) and `custom_style` (string) to `generateFromImage` request
- `src/app/models/photoshoot.api.d.ts` — regenerated via `npx openapi-typescript`
- `server/modules/photoshoot/dto.py` — regenerated via `datamodel-codegen`

**YAML addition**:
```yaml
# Under generateFromImage requestBody schema properties:
mode:
  type: string
  enum: [portrait, outfit, custom]
  default: portrait
  description: Generation style mode
custom_style:
  type: string
  maxLength: 500
  description: User-written style prompt. Required when mode is custom.
```

**Patterns**: OpenAPI-first. Both TS and Python types regenerated from the same YAML. No hand edits to generated files.

### Task 3: Backend Mode Resolution

**Purpose**: Replace the hardcoded prompt template with mode-aware prompt resolution.

**Components**:
- `server/modules/photoshoot/service.py` — import and call `resolve_prompt`
- `server/modules/photoshoot/routes.py` — extract `mode` and `custom_style` from request

**Change in service.py**:
```python
# BEFORE:
prompt = DEFAULT_PROMPT_TEMPLATE.format(trigger_word=trigger_word)
output = replicate_service.run(model_id, {"prompt": prompt, ...})

# AFTER:
from .prompts import resolve_prompt
resolved = resolve_prompt(trigger_word, mode, custom_style)
output = replicate_service.run(model_id, {
    "prompt": resolved["prompt"],
    "negative_prompt": resolved["negative_prompt"],
    ...
})
```

**Change in routes.py**:
```python
@bp.post("/generate-from-image")
def generate_from_image():
    # ... existing image extraction ...
    mode = request.form.get("mode", "portrait")
    custom_style = request.form.get("custom_style")
    if mode == "custom" and not custom_style:
        return jsonify({"error": "custom_style is required when mode is custom"}), 422
    result = service.generate_from_image(g.current_user, image, mode=mode, custom_style=custom_style)
    # ... existing response ...
```

**Patterns**: The service function signature gains two optional kwargs (`mode="portrait"`, `custom_style=None`). Existing callers (if any call without mode) get portrait by default — backward compatible.

### Task 4: Frontend Mode Picker

**Purpose**: Let the user choose a generation mode before tapping Generate.

**Components**:
- `src/app/pages/photoshoot/photoshoot.page.ts` — `ion-segment` control + conditional `ion-textarea`

**Layout** (within the photoshoot page, above capture buttons):
```html
<ion-segment [value]="selectedMode()" (ionChange)="onModeChange($event)"
             data-test="mode-picker">
  <ion-segment-button value="portrait" data-test="mode-portrait">
    <ion-label>Portrait</ion-label>
  </ion-segment-button>
  <ion-segment-button value="outfit" data-test="mode-outfit">
    <ion-label>Outfit</ion-label>
  </ion-segment-button>
  <ion-segment-button value="custom" data-test="mode-custom">
    <ion-label>Custom</ion-label>
  </ion-segment-button>
</ion-segment>

@if (selectedMode() === 'custom') {
  <ion-textarea
    [(ngModel)]="customStyle"
    placeholder="Describe the style you want..."
    [maxlength]="500"
    [rows]="3"
    data-test="custom-style-input">
  </ion-textarea>
}
```

**Signals**:
```typescript
selectedMode = signal<'portrait' | 'outfit' | 'custom'>('portrait');
customStyle = '';

onModeChange(event: SegmentCustomEvent) {
  this.selectedMode.set(event.detail.value as 'portrait' | 'outfit' | 'custom');
}
```

**API service change**: Add `mode` and `custom_style` to the FormData in `generateFromImage`:
```typescript
formData.append('mode', mode);
if (mode === 'custom' && customStyle) {
  formData.append('custom_style', customStyle);
}
```

**Patterns**: Standalone component, OnPush, signal-based state. `ion-segment` is Ionic's native segmented control — fits the immersive world pattern. Conditional textarea via `@if` control flow.

---

## Execution Flow

```
[Phase 1 — Day 1 morning, parallel]
  Task 1 (prompts.py) ──┬── Task 2 (OpenAPI + regen)
                         │
[Phase 2 — Day 1 afternoon, parallel]
  Task 3 (backend wiring) ──┬── Task 4 (frontend picker)
  depends on 1 + 2           │   depends on 2
                              │
[Phase 3 — Day 2 morning]    ▼
  Task 5 (integration test + TestFlight QA)
  depends on 3 + 4
```

Total elapsed: 1.5 days. Tasks 1+2 are independent. Tasks 3+4 are independent but each depends on earlier tasks. Task 5 integrates everything.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Config dict over database table | Python dict in `prompts.py` | Zero migrations, zero endpoints, git-versioned, testable in isolation. A DB table adds infrastructure for a feature with 3 modes and 15 users. The second consumer (admin UI, user preferences) hasn't appeared. |
| Collapse 5 Trendfy scenarios into one "outfit" mode | `random.choice` from 5 styles per generation | Avoids a 7-option picker (portrait + 5 outfits + custom). Random selection gives variety without decision fatigue. If testers consistently ask "I want the streetwear one again," that's signal to expose individual scenarios — but not before. |
| Segmented control over dropdown or swipe | `ion-segment` with 3 buttons | 3 options is the sweet spot for a segmented control. Dropdown hides choices. Swipe conflicts with gallery scroll. Segmented control is standard iOS UX for mode switching (e.g., Camera app photo/video/portrait). |
| No guardrails on custom mode | Freeform text, max 500 chars | 15 TestFlight testers, all known personally. Content filtering (Claude moderation call) adds latency and a dependency for a non-problem. `maxLength=500` prevents prompt-length edge cases without blocking creativity. |
| `default_style_prompt` column stays but goes unused | No Alembic migration to drop it | Dropping a column requires coordination (migration + deploy + verify no code reads it). Leaving it is harmless — the column is nullable, the service stops reading it. If we ever need per-user style overrides, the column is already there. |
| Negative prompt shared across all modes | One string in config, not per-mode | The negative prompt addresses universal generation artifacts (blur, distortion, watermarks). Per-mode negatives are optimization without signal. |
| `resolve_prompt` returns a dict, not a string | `{"prompt": str, "negative_prompt": str}` | Keeps the negative prompt coupled with the positive prompt at the config boundary. The service doesn't need to know about negative prompts separately — it passes the whole dict to Replicate. |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Trendfy prompt strings can't be located in the wardrobai repo | Outfit mode has no battle-tested content | The 5 scenario descriptions in the Analysis are informed by the braindump. If exact strings aren't found, write new prompts matching the scenario intent — the descriptors are the value, not the exact wording. |
| Replicate model doesn't support `negative_prompt` param | Negative prompt silently ignored | Check the model's input schema on Replicate before wiring. If unsupported, log a warning and omit. The positive prompt carries the quality signal. |
| Random outfit selection produces the same scenario 3x in a row | Tester thinks "outfit mode is broken — same output every time" | Acceptable at 1/5 × 1/5 = 4% probability. If it becomes a complaint, switch to `random.sample` with a session-level "last used" exclusion. Not worth building before the complaint exists. |
| Custom mode produces nonsense output from bad prompts | Tester blames the app, not their prompt | The trigger word is still prepended (`a photo of {trigger}, {custom_style}`). Even a bad style string produces a recognizable face. Worst case is a weird but clearly-their-face image. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)
- [Photoshoot Task 3](../photoshoot-1776260020498/task-3-photo-capture-and-generation-pipeline.md) — current prompt construction code
```

