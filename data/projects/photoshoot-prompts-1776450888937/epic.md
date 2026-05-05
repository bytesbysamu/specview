
```markdown
---
sidebar_position: 2
---

# 🎯 Modular Photoshoot Modes – Epic

**Purpose**: Define scope and tasks for porting Trendfy's prompt system into Bubls as selectable generation modes.

**Source Analysis**: See [Analysis](./analysis.md) for resolved decisions on scenario collapsing, picker UX, and custom mode guardrails.

---

## Business Value

The comparison run proved prompt quality is the single biggest lever on output — same model, different style string, dramatically different result. The current photoshoot has exactly one prompt template, which means every generation looks the same regardless of what the tester wanted. That's not a feature, it's a demo.

Trendfy's 5 outfit-specific prompts (casual, formal, streetwear, athleisure, evening) were iterated against real users and real orders. They produced production-quality fashion photos. Those prompts are sitting unused. Porting them into Bubls as an "outfit" mode — alongside the existing "portrait" mode and a new "custom" mode — turns the photoshoot from a one-trick demo into a multi-mode creative tool. The testers who've already trained LoRA models get instant variety from their existing models. No new training, no new infrastructure, no new costs. Just better prompts.

This is the lowest-effort, highest-impact improvement to the photoshoot experience. One config file, one API field, one UI control, one afternoon of work.

---

## Scope

### What This Epic Covers

- Prompt config module with base template and per-mode style blocks
- Porting Trendfy's 5 outfit scenario prompts into a single "outfit" mode (random selection per generation)
- Portrait mode using an improved version of the current default prompt
- Custom mode accepting a user-written style string
- Shared negative prompt in the config
- OpenAPI contract update: `mode` field on generate request
- Frontend mode picker (segmented control on photoshoot page)
- Persisting the full resolved prompt in `superapp_generations.prompt` column (already exists)

### What This Epic Does NOT Cover

- ❌ Per-user style preferences or favorites
- ❌ Prompt A/B testing infrastructure
- ❌ Content moderation for custom mode (TestFlight-only)
- ❌ Individual scenario selection within outfit mode (casual/formal/streetwear picker)
- ❌ Inference parameter tuning per mode — `guidance_scale=7.5`, `num_inference_steps=28` stay fixed
- ❌ Database storage for prompt styles — config dict only
- ❌ Migration to drop `lora_models.default_style_prompt` — column stays, just unused

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Prompt config module** | None | 2 | 0.5 day | High |
| 2 | **OpenAPI + DTO update** | None | 1 | 0.5 day | High |
| 3 | **Backend mode resolution** | 1, 2 | — | 0.5 day | High |
| 4 | **Frontend mode picker** | 2 | 3 | 0.5 day | High |
| 5 | **Integration test + TestFlight QA** | 3, 4 | — | 0.5 day | Medium |

### Task Details

#### Task 1: Prompt Config Module

Create `server/modules/photoshoot/prompts.py` — a pure Python config module defining the prompt architecture. Contains:

- `PROMPT_TEMPLATE`: base template string `"a photo of {trigger}, {style}"` (no f-string — `.format()` at runtime)
- `NEGATIVE_PROMPT`: shared negative prompt string (e.g., `"blurry, low quality, distorted face, extra limbs, watermark, text"`)
- `MODES` dict keyed by mode name (`portrait`, `outfit`, `custom`), where each value contains a `styles` list of style block strings
- Portrait mode: 1 style (the improved default — rich descriptors for studio lighting, natural pose, sharp detail)
- Outfit mode: 5 styles ported from Trendfy (casual, formal, streetwear, athleisure, evening) — each with full descriptors for clothing, pose, setting, lighting
- `resolve_prompt(trigger_word: str, mode: str, custom_style: str | None) -> dict` function returning `{"prompt": str, "negative_prompt": str}` — selects a random style from the mode's list, formats the template, returns the pair
- For custom mode: uses `custom_style` as the style block directly, ignoring `MODES["custom"]`

The Trendfy prompt strings must be extracted from the wardrobai repo (`server/` or `ai-models/lora-experiment.ipynb`). The exact strings are the deliverable — not paraphrases or rewrites.

#### Task 2: OpenAPI + DTO Update

Update `server/openapi/photoshoot.yaml`:
- Add `mode` field (string enum: `portrait`, `outfit`, `custom`) to the `generateFromImage` request body, default `portrait`
- Add `custom_style` field (string, optional) to the request body — required only when `mode=custom`
- Regenerate `src/app/models/photoshoot.api.d.ts` (TS types) and `server/modules/photoshoot/dto.py` (Pydantic) from the updated YAML
- No hand-editing of generated files

#### Task 3: Backend Mode Resolution

Modify `server/modules/photoshoot/service.py`:
- Import `resolve_prompt` from `prompts.py`
- Replace the hardcoded `DEFAULT_PROMPT_TEMPLATE.format(trigger_word=trigger_word)` with a call to `resolve_prompt(trigger_word, mode, custom_style)`
- Pass both `prompt` and `negative_prompt` to `ReplicateService` (if Replicate's API accepts negative prompts for the current model — check the model's input schema first; if not, drop `negative_prompt` silently)
- Store the resolved prompt in the `superapp_generations.prompt` column (already exists)

Modify `server/modules/photoshoot/routes.py`:
- Extract `mode` and `custom_style` from the validated request DTO
- Pass them through to the service function
- Validate: if `mode=custom` and `custom_style` is empty/missing, return 422

#### Task 4: Frontend Mode Picker

Modify `src/app/pages/photoshoot/photoshoot.page.ts`:
- Add an `ion-segment` with three `ion-segment-button` elements: Portrait, Outfit, Custom
- Bind selected mode to a signal: `selectedMode = signal<'portrait' | 'outfit' | 'custom'>('portrait')`
- When custom is selected, show a `ion-textarea` below the segment for the user's style string (bind to `customStyle` signal)
- Position the segment above the capture buttons, below the model label

Modify `src/app/services/photoshoot-api.service.ts`:
- Add `mode` and `custom_style` fields to the `generateFromImage` multipart payload
- Use the regenerated TS types from Task 2

Add `data-test` selectors:
- `data-test="mode-picker"` on the segment
- `data-test="mode-portrait"`, `data-test="mode-outfit"`, `data-test="mode-custom"` on the buttons
- `data-test="custom-style-input"` on the textarea

#### Task 5: Integration Test + TestFlight QA

Backend tests (`server/tests/test_prompts.py`):
- `portrait_resolvesPrompt_containsTriggerWord` — verify trigger word appears in resolved prompt
- `outfit_resolvesPrompt_randomFromFiveScenarios` — call `resolve_prompt` 20 times, verify all 5 scenario styles appear at least once (statistical — if one is missing after 20 calls, the config is wrong)
- `custom_resolvesPrompt_usesCustomStyle` — verify custom string appears verbatim in prompt
- `custom_emptyStyle_raises` — verify ValueError for empty custom style
- `unknownMode_raises` — verify KeyError for invalid mode

Frontend tests (`src/app/pages/photoshoot/photoshoot.page.spec.ts`):
- `modePickerRendered_threeSegments` — verify 3 segment buttons exist via `data-test`
- `customModeSelected_showsTextarea` — verify textarea appears when custom segment is active
- `portraitModeSelected_hidesTextarea` — verify textarea hidden for non-custom modes
- `generateTapped_sendsMode` — verify API service receives selected mode in the payload

TestFlight QA (manual):
- Generate one photo in each mode on a real device
- Verify outfit mode produces visibly different styles across 3 generations (random selection working)
- Verify custom mode with a user-written prompt produces coherent output
- Verify portrait mode output quality matches or exceeds the old default
- Zero regression on camera capture, before/after gallery, photo-library save

---

## Success Criteria

- ✅ Three modes selectable on the photoshoot page: portrait, outfit, custom
- ✅ Outfit mode produces visibly different styles across consecutive generations (5 Trendfy scenarios cycling)
- ✅ Custom mode accepts arbitrary user text and produces coherent output
- ✅ Portrait mode produces equal or better quality than the previous hardcoded default
- ✅ Full resolved prompt persisted in `superapp_generations.prompt` for every generation
- ✅ No new database tables or migrations
- ✅ No new dependencies beyond what's already installed
- ✅ Zero regression on existing photoshoot flow (capture, upload, gallery, photo-library save)

---

## Non-Goals

- ❌ Individual scenario picker within outfit mode
- ❌ Per-user prompt preferences or favorites
- ❌ Content moderation for custom mode
- ❌ Prompt version history or A/B testing
- ❌ Style transfer from reference images
- ❌ Inference parameter tuning per mode

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)
```

