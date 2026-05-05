
```markdown
---
sidebar_position: 0
---

# 📋 Modular Photoshoot Modes

> Port Trendfy's battle-tested prompt system into Bubls as swappable generation modes — portrait, outfit, custom.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

The Bubls photoshoot currently fires a single hardcoded prompt template (`a professional enhanced photo of {trigger_word}, high quality, natural lighting, sharp detail`) on every generation. The comparison run proved that prompt quality is the biggest lever — same LoRA model, different style string, dramatically different output. A rich, scenario-specific prompt produces studio-quality images while the generic default produces flat, lifeless results.

Trendfy shipped 5 outfit-specific prompts (casual, formal, streetwear, athleisure, evening) that were tested against real orders and real users. Those prompts are battle-tested artifacts sitting in a dead codebase. This epic ports them into Bubls as selectable generation modes, turning the photoshoot from a one-trick feature into a multi-mode creative tool without adding any new AI infrastructure — the LoRA models, inference pipeline, and Replicate integration are already there.

The architecture is a prompt config layer, not a feature build. A base template (`{TRIGGER}, {STYLE}, {SUFFIX}`) with swappable style blocks per mode, stored as a Python config dict — not in the database. The frontend gets a mode picker (portrait / outfit / custom) that sends a `mode` key with the generate request. The backend resolves the mode to a style block and constructs the full prompt. Negative prompt and inference parameters (`guidance_scale=7.5`, `num_inference_steps=28`) stay fixed.

## Related Documents

- [Analysis](./analysis.md)
- [Trendfy Port Epic](../trendfy-port-1776381797246/epic.md) — prior data migration
- [Photoshoot Architecture](../bubls2-1776263128609/architecture.md) — shell + inference design
- [UX Revamp](../bubls-ux-revamp-1776370239783/epic.md) — immersive photoshoot world
```

