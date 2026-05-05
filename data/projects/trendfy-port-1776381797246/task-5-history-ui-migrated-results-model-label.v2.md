The guide is ready. Here are the key improvements over the v2:

**Structural changes:**
- **Removed ORM model column additions** — Task 5 is a UI task. The `expired` column on `Generation` comes from Task 3, and `model_name`/`is_active` on `LoraModel` from Task 2. Pre-flight verifies they exist; if missing, executor STOPs.
- **No new Blueprint file** — the `GET /api/photoshoot/active-model` route goes into the existing `routes.py` Blueprint, avoiding a separate `lora_routes.py` and the `server/app.py` registration step.
- **Added `_model_display_name` fallback chain** — handles the uncertainty of whether Task 2 shipped a `model_name` column: tries `model_name` → parses `replicate_model_id` slug → falls back to `trigger_word`. Robust to either Task 2 outcome.

**Executor quality:**
- Tighter file lists (1 file to create vs. 2 in v2)
- Backend test asserts on `model_name is not None` + `len > 0` rather than a specific string, because the display name derivation varies
- Clearer deviation section for the `model_name` column ambiguity
- Explicit backend/frontend rollback symmetry — each side degrades gracefully when the other is reverted

**Test delta**: BE +3, FE +6 = 9 new tests total.

Want me to save this to the file?