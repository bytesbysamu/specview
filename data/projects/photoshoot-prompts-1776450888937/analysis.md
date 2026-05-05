
```markdown
---
sidebar_position: 1
---

# 🔍 Modular Photoshoot Modes – Analysis

**Purpose**: Catch contradictions between braindump and principles, surface unmade decisions, kill scope before the epic inflates.

**Date**: 2026-04-17

---

## Problem

The photoshoot uses a single hardcoded style string. The comparison run showed that prompt quality — not model quality — is the primary lever on output. Trendfy's 5 scenario-specific prompts produced production-quality outfit photos; the generic 4-word default produces flat images. Those prompts sit unused in a dead codebase. The LoRA models, inference pipeline, and Replicate integration already exist. The only missing piece is prompt variety.

## Hard Constraints (checked against builder + principles)

- **Config not DB**: Braindump says "stored as config not DB." This aligns with "not-yet-built is the right state for infrastructure nobody's asked for" — a `prompt_styles` table with admin UI is speculative. A Python dict in a config module is one file, zero migrations, zero endpoints.
- **No new AI providers**: Same Replicate API, same LoRA models, same inference params. The architecture principle "strategy pattern for AI providers" doesn't trigger because we're not adding a provider — we're changing the input to the existing one.
- **Adapter boundary holds**: `ReplicateService` is the adapter. Feature code (routes, service) calls it through the adapter. The prompt config module sits between the feature service and the adapter — feature service resolves mode → style block, passes full prompt to `ReplicateService`. No adapter change needed.
- **OpenAPI-first**: The generate endpoint gains a `mode` field. YAML changes first, DTO regen follows. No hand-edited types.
- **TestFlight-only audience**: 15 trusted testers. Custom mode guardrails (prompt injection, content policy) are not needed for v1.

## Open Questions (resolved in this analysis)

| Question | Decision | Why |
|----------|----------|-----|
| Port all 5 Trendfy scenarios as separate modes or collapse? | Collapse into one "outfit" mode that randomly selects a scenario per generation | 7-mode picker is decision fatigue for 15 testers. One "outfit" mode that cycles through casual/formal/streetwear/athleisure/evening gives variety without complexity. If testers ask for scenario control, that's signal to expose individual modes in v2. |
| Mode picker: radio buttons, dropdown, or swipe gesture? | Segmented control (Ionic `ion-segment`) | Fits the immersive photoshoot world from the UX revamp. 3 segments (portrait / outfit / custom) are scannable. Swipe conflicts with the contact-sheet gallery scroll. Dropdown hides options. Segmented control is native iOS convention for mode switching. |
| Custom mode guardrails? | Freeform for v1 | TestFlight-only, 15 known users. Adding content filtering adds a dependency (Claude moderation call or regex rules) for an audience that doesn't need it. Revisit when the app goes public. |
| Where does the negative prompt live? | In the same config dict, shared across all modes | Braindump says "negative prompt stays fixed." One key in the config, referenced by the prompt builder function. Not per-mode. |
| Does the `lora_models.default_style_prompt` column get deprecated? | Yes — it becomes dead data | The column was seeded with a generic style during the pre-train phase. The config module replaces it as the source of truth for style. The column stays in the schema (no migration to drop it) but the service stops reading it. |

## Dependencies

- **UX revamp (done)**: The immersive photoshoot world and contact-sheet gallery are already merged on `ux-revamp-integrated`. The mode picker slots into the existing photoshoot page layout.
- **Trendfy port (done)**: The 7 migrated LoRA models and 76 historical results are already in Bubls tables. The mode picker applies to new generations only — historical results retain whatever prompt was used at generation time.
- **Trendfy source code (read access needed)**: The 5 scenario prompts need to be extracted from Trendfy's codebase. The wardrobai repo has a `lora-experiment.ipynb` and the Flask server — the prompts are in there somewhere.

## Explicitly Out of Scope

- Per-user style preferences (favorites, defaults) — config is global, not per-user
- Mode history (tracking which mode produced which generation) — the `prompt` column on `superapp_generations` already stores the full prompt used; that's sufficient for retrospective analysis
- Prompt A/B testing infrastructure — if we want to test prompt variants, we change the config dict and compare outputs manually
- Self-serve prompt creation beyond the custom textarea — no prompt builder UI, no template editor
- Inference parameter tuning per mode — `guidance_scale` and `num_inference_steps` stay fixed across all modes
```

