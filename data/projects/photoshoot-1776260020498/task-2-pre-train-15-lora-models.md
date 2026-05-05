# 🛠️ Task 2: Pre-train 15 LoRA models

**Purpose**: Collect selfies from 15 friends/testers, train a personalized LoRA model for each on Replicate, seed the user-to-model mappings in Neon Postgres, and validate every model produces acceptable results — so that when users open the app, their AI model is already waiting.

**Effort**: 3 days

**Dependencies**: None — runs independently of shell development

**Parallel With**: Task 1 (Shell + Auth + Gating)

**Blocks**: Task 4 (Deploy + Invite Testers) — testers can't be invited until their models are trained and validated

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Photo collection protocol: gathering 10-20 selfies per person from 15 testers
- LoRA training on Replicate using Trendfy's existing pipeline
- Neon Postgres schema creation (`lora_models` table)
- Database seeding: one row per tester mapping user → trained model
- Quality validation: 3-5 test generations per model before inviting that user
- Pre-warming: dummy inference on each model to reduce cold-start latency at invite time

### What's NOT Included
- Self-serve training pipeline — that's Month 2 scope; manual is deliberate
- Style selection or multiple styles per user — one default style ships faster
- Image storage migration — Replicate-hosted URLs are sufficient for Month 1
- Android or web-only testing — iOS TestFlight only for Month 1

---

## Prerequisites

Before starting:
- Replicate account with API token (already provisioned from Trendfy)
- Replicate CLI installed (`pip install replicate` or `npm install replicate`)
- Neon Postgres connection string (shared instance, EU Central 1 — already running)
- `psql` or a Postgres client to run schema migrations
- 15 testers identified and willing to send selfies
- Reference Trendfy's training scripts for prompt/parameter baselines

---

## Implementation Steps

### Step 1: Create the `lora_models` table in Neon

**File**: `migrations/001_lora_models.sql` (or run directly via `psql`)

**Purpose**: Establish the data model that maps users to their Replicate LoRA models.

The `lora_models` table is the single piece of infrastructure that makes personalization work. Every generation request resolves through this table. Create it in the shared Neon instance's `public` schema alongside existing tables.

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS lora_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    replicate_model_id TEXT NOT NULL,          -- e.g. "username/model-name:version"
    training_status TEXT NOT NULL DEFAULT 'pending',  -- pending | training | ready | failed
    num_training_images INT,
    trained_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX idx_lora_models_user_id ON lora_models(user_id);
CREATE INDEX idx_lora_models_status ON lora_models(training_status);
```

**Notes**:
- `UNIQUE(user_id)` enforces one model per user — the resolution query is always a single-row lookup
- `training_status` exists for future self-serve training; for Month 1, all rows are inserted as `'ready'`
- If the `users` table doesn't exist yet (Task 1 creates it), create `lora_models` without the foreign key constraint and add it later with `ALTER TABLE`

**Verification**:
```bash
psql $NEON_CONNECTION_STRING -c "\d lora_models"
```

---

### Step 2: Collect training photos from 15 testers

**Purpose**: Gather high-quality selfie datasets that produce good LoRA results.

This is a people problem, not a code problem. The quality of training data directly determines model quality. Set up a lightweight collection pipeline.

**Collection protocol**:

1. **Create a shared album or folder per tester** — Google Photos shared album, iCloud shared album, or a simple Google Drive folder. One per person.

2. **Send testers the photo guidelines**:
   ```
   Hey! I'm building an AI photo app and need 10-20 selfies from you to train your personal model.

   What works best:
   - Different angles (front, 3/4, profile)
   - Different lighting (indoor, outdoor, natural light)
   - Different expressions (smile, neutral, candid)
   - Solo shots only (no group photos)
   - Recent photos (last 6 months)
   - Clear face, no heavy filters

   What to avoid:
   - Sunglasses covering eyes
   - Hands covering face
   - Blurry or heavily compressed images
   - Same pose/angle repeated
   - Heavy Instagram filters

   Just drop them in this folder: [link]
   ```

3. **Aim for 15-20 images per person** — Replicate's FLUX LoRA trainer works well with 10-20 images. More variety in angles/lighting beats more quantity of the same pose.

4. **Download and organize locally**:
   ```
   training-data/
   ├── tester-01-alice/
   │   ├── photo_01.jpg
   │   ├── photo_02.jpg
   │   └── ... (10-20 images)
   ├── tester-02-bob/
   │   └── ...
   └── tester-15-olivia/
       └── ...
   ```

**Timeline**: Send requests on Day 1 morning. Most people respond within 24 hours. Start training models as photos arrive — don't wait for all 15.

---

### Step 3: Train LoRA models on Replicate

**Purpose**: Train one FLUX LoRA model per tester using Replicate's training API.

Replicate's `ostris/flux-dev-lora-trainer` (or the latest FLUX LoRA trainer) handles the heavy lifting. Each training run takes 15-30 minutes and costs ~$2-5 depending on image count and steps.

**Training script** (`scripts/train_lora.py`):
```python
import replicate
import os
import zipfile
import tempfile
import json
from pathlib import Path

REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"]

def create_training_zip(image_dir: str) -> str:
    """Zip training images for upload to Replicate."""
    zip_path = tempfile.mktemp(suffix=".zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for img in Path(image_dir).glob("*"):
            if img.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                zf.write(img, img.name)
    return zip_path

def train_model(tester_name: str, image_dir: str, trigger_word: str = None):
    """Train a LoRA model for one tester."""
    if trigger_word is None:
        trigger_word = tester_name.upper()

    zip_path = create_training_zip(image_dir)

    print(f"Training model for {tester_name} with trigger word '{trigger_word}'...")

    # Create a model on Replicate to store the trained version
    model = replicate.models.create(
        owner="your-replicate-username",  # Replace with your username
        name=f"photoshoot-{tester_name.lower()}",
        visibility="private",
        hardware="gpu-t4-nano"
    )

    # Start training
    training = replicate.trainings.create(
        version="ostris/flux-dev-lora-trainer:latest",
        input={
            "input_images": open(zip_path, "rb"),
            "trigger_word": trigger_word,
            "steps": 1000,
            "lora_rank": 16,
            "optimizer": "adamw8bit",
            "batch_size": 1,
            "resolution": "512,768,1024",
            "autocaption": True,
            "autocaption_prefix": f"a photo of {trigger_word},",
        },
        destination=f"your-replicate-username/photoshoot-{tester_name.lower()}"
    )

    print(f"Training started: {training.id}")
    print(f"Status URL: https://replicate.com/p/{training.id}")

    return {
        "tester": tester_name,
        "training_id": training.id,
        "model_destination": f"your-replicate-username/photoshoot-{tester_name.lower()}",
        "trigger_word": trigger_word,
    }

def check_training_status(training_id: str):
    """Poll training status."""
    training = replicate.trainings.get(training_id)
    print(f"Status: {training.status}")
    if training.status == "succeeded":
        print(f"Model version: {training.output.get('version', 'N/A')}")
    return training.status

# Usage:
# result = train_model("alice", "training-data/tester-01-alice")
# check_training_status(result["training_id"])
```

**Batch training script** (`scripts/train_all.py`):
```python
import json
from pathlib import Path
from train_lora import train_model

TRAINING_DATA_DIR = "training-data"
RESULTS_FILE = "training-results.json"

def train_all():
    results = []
    data_dir = Path(TRAINING_DATA_DIR)

    for tester_dir in sorted(data_dir.iterdir()):
        if not tester_dir.is_dir():
            continue

        image_count = len(list(tester_dir.glob("*.jpg")) + list(tester_dir.glob("*.png")))
        if image_count < 10:
            print(f"SKIP {tester_dir.name}: only {image_count} images (need 10+)")
            continue

        tester_name = tester_dir.name.split("-", 2)[-1]  # "tester-01-alice" → "alice"
        result = train_model(tester_name, str(tester_dir))
        results.append(result)

    # Save results for later use when seeding the database
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nStarted {len(results)} training jobs. Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    train_all()
```

**Key parameters to tune** (based on Trendfy experience):
- `steps: 1000` — Good balance for face LoRAs; increase to 1500 if results are weak
- `lora_rank: 16` — Standard rank; 32 for more detail but larger model size
- `autocaption: True` — Let Replicate auto-caption training images; saves manual captioning work
- `trigger_word` — Use the person's name in caps (e.g., `ALICE`); this is what you'll include in generation prompts

**Cost estimate**: ~$2-5 per model × 15 models = $30-75 total

---

### Step 4: Validate each trained model

**Purpose**: Generate 3-5 test images per model and reject any that don't meet quality threshold. A bad model poisons first impressions — better to retrain than invite a user to a broken experience.

**Validation script** (`scripts/validate_model.py`):
```python
import replicate
import json

def validate_model(model_id: str, trigger_word: str, num_tests: int = 5):
    """Run test generations against a trained model."""
    test_prompts = [
        f"a professional headshot photo of {trigger_word}, studio lighting, neutral background",
        f"a casual outdoor photo of {trigger_word}, golden hour, natural lighting",
        f"a close-up portrait of {trigger_word}, soft lighting, shallow depth of field",
        f"a photo of {trigger_word} in a coffee shop, warm ambient lighting",
        f"a photo of {trigger_word}, urban street photography style, natural expression",
    ]

    results = []
    for i, prompt in enumerate(test_prompts[:num_tests]):
        print(f"  Test {i+1}/{num_tests}: {prompt[:60]}...")
        output = replicate.run(
            model_id,
            input={
                "prompt": prompt,
                "num_outputs": 1,
                "guidance_scale": 7.5,
                "num_inference_steps": 28,
            }
        )
        url = output[0] if isinstance(output, list) else output
        results.append({"prompt": prompt, "output_url": str(url)})
        print(f"    → {url}")

    return results

def validate_all():
    with open("training-results.json") as f:
        models = json.load(f)

    validation = {}
    for model in models:
        print(f"\nValidating {model['tester']}...")
        results = validate_model(
            model["model_destination"],
            model["trigger_word"]
        )
        validation[model["tester"]] = results

    with open("validation-results.json", "w") as f:
        json.dump(validation, f, indent=2)

    print("\nValidation complete. Review images at the URLs above.")
    print("Mark pass/fail for each tester before seeding the database.")

if __name__ == "__main__":
    validate_all()
```

**Quality checklist per model** (review manually):

| Criterion | Pass | Fail |
|-----------|------|------|
| Face resembles the actual person | Recognizable | Wrong person or distorted |
| Consistent identity across 3+ outputs | Same person each time | Different face each generation |
| No artifacts on face/hands | Clean output | Melted features, extra fingers |
| Responds to different prompts | Varied compositions | Same output regardless of prompt |
| Acceptable at phone-screen resolution | Sharp enough | Blurry or pixelated |

**If a model fails**: Retrain with adjusted parameters:
- Add more training images (especially varied angles)
- Increase steps to 1500
- Ensure training images don't have filters or heavy edits
- Try a different `lora_rank` (32 instead of 16)

Do not invite a tester whose model fails validation.

---

### Step 5: Seed the database with model mappings

**Purpose**: Insert one row per validated model into `lora_models`, creating the user-to-model mapping that the generation pipeline will resolve at runtime.

**Seeding script** (`scripts/seed_models.py`):
```python
import psycopg2
import json
import os
from datetime import datetime

NEON_CONNECTION_STRING = os.environ["NEON_DATABASE_URL"]

def seed_models():
    with open("training-results.json") as f:
        models = json.load(f)

    # Map tester names to user IDs — fill these in after users table is populated
    # If users table isn't ready yet (Task 1 in progress), create users here
    tester_user_map = {
        # "alice": "uuid-from-users-table",
        # "bob": "uuid-from-users-table",
        # Fill in after Task 1 creates user records
    }

    conn = psycopg2.connect(NEON_CONNECTION_STRING)
    cur = conn.cursor()

    for model in models:
        tester = model["tester"]
        user_id = tester_user_map.get(tester)

        if not user_id:
            print(f"SKIP {tester}: no user_id mapped yet")
            continue

        # Get the trained model version from Replicate
        model_id = model["model_destination"]

        cur.execute("""
            INSERT INTO lora_models (user_id, replicate_model_id, training_status, num_training_images, trained_at)
            VALUES (%s, %s, 'ready', %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                replicate_model_id = EXCLUDED.replicate_model_id,
                training_status = EXCLUDED.training_status,
                updated_at = NOW()
        """, (
            user_id,
            model_id,
            model.get("num_images", 15),
            datetime.utcnow(),
        ))
        print(f"Seeded: {tester} → {model_id}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nSeeded {len(models)} models into lora_models table.")

if __name__ == "__main__":
    seed_models()
```

**If Task 1 isn't done yet**: The `users` table may not exist. Two options:
1. **Create users directly** — Insert user records with email and a placeholder auth provider ID. Task 1 will connect these to Supabase Auth later.
2. **Seed models without user FK** — Insert into `lora_models` with `user_id = NULL`, then update with real user IDs once Task 1 creates user records. This requires temporarily dropping the NOT NULL constraint or the foreign key.

Option 1 is cleaner — create the user records as part of seeding and let Task 1's auth integration find and link them.

---

### Step 6: Pre-warm models to reduce cold-start latency

**Purpose**: Replicate cold-starts cause 10-30s latency on first inference. Running a dummy generation before inviting testers ensures their first real experience is on a warm model.

**Pre-warm script** (`scripts/prewarm_models.py`):
```python
import replicate
import json

def prewarm_all():
    with open("training-results.json") as f:
        models = json.load(f)

    for model in models:
        print(f"Pre-warming {model['tester']}...")
        try:
            output = replicate.run(
                model["model_destination"],
                input={
                    "prompt": f"a photo of {model['trigger_word']}, portrait",
                    "num_outputs": 1,
                    "num_inference_steps": 20,  # Fewer steps — we just need to warm the model
                }
            )
            print(f"  Warm: {output}")
        except Exception as e:
            print(f"  FAILED: {e}")

if __name__ == "__main__":
    prewarm_all()
```

**Timing**: Run this 30-60 minutes before sending invite links. Models stay warm for roughly 5-15 minutes on Replicate's infrastructure, so don't run it hours in advance.

---

## Day-by-Day Schedule

| Day | Morning | Afternoon |
|-----|---------|-----------|
| **Day 1** | Send photo collection requests to all 15 testers. Create `lora_models` table in Neon. | Set up training scripts. Train models as photos arrive (expect 3-5 ready by EOD). |
| **Day 2** | Continue collecting photos from slow responders. Train remaining models as photos come in. | Validate early models (3-5 test generations each). Retrain any failures. |
| **Day 3** | Final stragglers — if someone hasn't sent photos, train with what you have or drop to 14. Validate all remaining models. | Seed database with all validated models. Run pre-warm before Task 4 begins. |

---

## Tracking Progress

Keep a simple tracking sheet (or a JSON file):

```json
{
  "testers": [
    {"name": "alice", "photos_received": 18, "training_status": "ready", "validation": "pass", "model_id": "user/photoshoot-alice:v1"},
    {"name": "bob", "photos_received": 0, "training_status": "waiting", "validation": null, "model_id": null}
  ]
}
```

States: `waiting` → `photos_received` → `training` → `trained` → `validating` → `pass` / `retrain` → `seeded`

---

## Verification

After all steps complete:

```bash
# 1. Verify table exists with correct schema
psql $NEON_DATABASE_URL -c "\d lora_models"

# 2. Verify all 15 models are seeded and ready
psql $NEON_DATABASE_URL -c "SELECT user_id, replicate_model_id, training_status FROM lora_models WHERE training_status = 'ready'"

# 3. Verify model resolution works (the query the Flask endpoint will use)
psql $NEON_DATABASE_URL -c "
    SELECT u.email, lm.replicate_model_id
    FROM users u
    JOIN lora_models lm ON u.id = lm.user_id
    WHERE lm.training_status = 'ready'
"

# 4. Run one inference against a seeded model to confirm end-to-end
python -c "
import replicate
output = replicate.run('your-username/photoshoot-alice:latest', input={'prompt': 'a photo of ALICE, portrait'})
print(output)
"
```

**Expected Result**:
- `lora_models` table contains 15 rows, all with `training_status = 'ready'`
- Each `replicate_model_id` resolves to a working Replicate model
- Test inference returns a valid image URL
- Each model produces images that recognizably resemble the corresponding tester

---

## Failure Modes and Fixes

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| Tester sends < 10 photos | Insufficient variety for LoRA training | Ask for more, or train with what you have (8+ can work with `steps: 1500`) |
| Training fails on Replicate | Bad input images or Replicate service issue | Check Replicate dashboard for error logs; retry. Ensure images are valid JPEG/PNG, not HEIC |
| Model produces wrong face | Training data contaminated or insufficient | Remove non-solo photos, ensure all photos are of the same person, retrain |
| Model produces artifacts | Overfitting or bad training params | Reduce steps to 800, increase training images, lower `lora_rank` to 8 |
| Replicate model URL format changes | API version mismatch | Check `replicate` Python package version, update if needed |
| HEIC images from iPhone | Replicate trainer may not accept HEIC | Convert to JPEG before zipping: `sips -s format jpeg input.HEIC --out output.jpg` (macOS) |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 as done
2. Coordinate with Task 1 (shell) to ensure user records in `users` table are linked to `lora_models` entries
3. Task 3 (generation pipeline) can begin testing against these trained models using a single developer's model
4. Run pre-warm script again just before Task 4 (deploy + invite)

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, data model, and user-to-model resolution pattern
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking