---
name: WardrobAI AI Pipeline Summary
description: Complete summary of all experiments, notebooks, models tested, costs, and findings in the ai-models workspace
type: project
---

## WardrobAI AI Pipeline — Full Summary (as of 2026-04-03)

### Three notebooks in `/workspace/ai-models/`

**1. `wardrobe-poc.ipynb` — Main VTON Pipeline (13 cells)**
- Cells 1-7: Extract garment → Claude Vision tags → IDM-VTON + Flux VTON → ESRGAN + CodeFormer → comparison grid
- Cells 8-11: Unsplash catalog (10 items) → Claude picks outfit → batch IDM-VTON × 3 → demo grid
- Cells 12-13: Chaining experiments (top → bottom → shoes sequential VTON)

**2. `lora-experiment.ipynb` — Personal LoRA Training (5 cells)**
- 28 photos → zip → train FLUX LoRA on Replicate → generate 5 outfits from text
- Model: `bytesbysamu/wardrobeai-person:ac800a28...`
- Training: 2000 steps, trigger word `WRDRB1PERSON`, ~35 min, ~$1.50

**3. `results-comparison.ipynb` — Visual Review (22 cells)**
- No API calls. Displays all outputs with full provenance and fairness notes.

### Models tested
- `cuuupid/idm-vton` — dedicated VTON, best garment accuracy
- `cedoysch/flux-fill-redux-try-on` — Flux-based VTON alternative
- `lucataco/remove-bg` — background removal
- `naklecha/clothing-segmentation` — garment extraction (FAILED)
- `claude-sonnet-4-6` — garment tagging + outfit picking
- `nightmareai/real-esrgan` — 2x upscaling
- `sczhou/codeformer` — face restoration
- `black-forest-labs/flux-2-pro` — general image gen with reference images (playground only)
- `ostris/flux-dev-lora-trainer` — personal LoRA training
- `bytesbysamu/wardrobeai-person` — trained personal LoRA for inference

### Key findings
- IDM-VTON with clean product photos (batch try-on) = best garment accuracy
- VTON chaining works for 2 steps, degrades on step 3
- LoRA manual runs (blazer, leather jacket) = highest overall image quality + face consistency
- Flux 2 Pro recombines reference images, doesn't generate new outfits from text
- Claude Vision on clean garment gives much richer descriptions than on noisy photo
- Clothing-seg failed; VTON got full silhouette instead of garment-only (hurt quality)

### Total cost: ~$2.50

### Replicate username: bytesbysamu
