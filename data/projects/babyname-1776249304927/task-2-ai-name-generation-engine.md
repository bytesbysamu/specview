# Implementation: AI Name Generation Engine

**Purpose**: Build the Flask backend proxy that receives structured preferences from the app, constructs a Claude prompt, calls the API, validates the structured JSON response, and returns name cards. The prompt engineering is the entire product — this is where generation quality, cultural accuracy, and personalized rationale are determined.

**Effort**: 2 days

**Dependencies**: Task 1 (Preference Input Flow) — the `PreferenceModel` defines the input contract this engine consumes.

**Parallel With**: —

**Blocks**: Task 3 (Name Card UI + Results Screen), Task 5 (Paywall + Subscription)

**Related**:
- [Solution Architecture](./architecture.md) — Generation Engine component design, Prompt-as-Product pattern, Structured AI Output pattern
- [Epic](./epic.md) — Task 2 definition, under-10-second generation target

---

## Overview

### What's Included
- Flask backend with `/api/generate` endpoint that proxies Claude API calls
- `PromptTemplate` module — system prompt and user message construction from preferences
- Structured JSON output schema and response validation
- Retry logic for malformed Claude responses (single retry)
- `UsageMeter` — generation count tracking per device ID in Neon Postgres
- Angular `GenerationService` — frontend service that posts preferences and receives name cards
- `NameCard` TypeScript interface matching the Claude output schema

### What's NOT Included
- Paywall enforcement — Task 5 wires `UsageMeter` counts into gating logic; this task only tracks counts
- Name card UI rendering — Task 3 consumes the `NameCard[]` response
- Caching of generation results — per [Architecture](./architecture.md), every generation is unique
- Streaming — batch response by design; parents want complete cards, not partial names

---

## Prerequisites

Before starting:
- Task 1 complete — `PreferenceModel` interface exists in `src/app/models/preference.model.ts`
- Anthropic API key provisioned and accessible as environment variable
- Neon Postgres connection string available (shared instance, same as other products)
- Python 3.11+ with Flask installed locally
- `pip install flask anthropic psycopg2-binary python-dotenv`

---

## Implementation Steps

### Step 1: Define the NameCard Interface

**File**: `src/app/models/name-card.model.ts`

**Purpose**: Create the TypeScript interface that matches the JSON schema Claude will return. This is the contract between backend and frontend — the generation engine produces these, the results screen (Task 3) renders them.

This interface must exactly mirror the JSON structure specified in the prompt. Any mismatch means parsing failures or missing UI data.

**Pattern**:
```typescript
export interface NameCard {
  name: string;
  pronunciation: string;
  origin: string;
  meaning: string;
  popularity: 'common' | 'rising' | 'rare';
  rationale: string;
}

export interface GenerationResponse {
  names: NameCard[];
  generationsRemaining: number | null;
}
```

Design notes:
- `popularity` is a constrained enum, not a free string — this maps to visual indicators in the card UI (Task 3).
- `rationale` is the differentiator. It must reference the user's stated preferences. The prompt enforces this, not the schema.
- `generationsRemaining` is nullable — `null` means the user is subscribed (unlimited). This field comes from `UsageMeter`, not Claude.

### Step 2: Scaffold the Flask Backend

**File**: `backend/app.py`

**Purpose**: Set up the Flask app with CORS, environment variable loading, and the health check endpoint. This follows the same minimal Flask pattern used in Humanize-me.

```bash
mkdir -p backend
```

**Pattern**:
```python
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:8100",    # Ionic dev server
    "capacitor://localhost",    # iOS Capacitor
    "http://localhost",         # Android Capacitor
])

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3200, debug=True)
```

Design notes:
- Port 3200 avoids collision with Spec Doc's Express server on 3100.
- CORS origins include both browser and native Capacitor origins. In production, tighten to the actual domain.
- `flask_cors` and `python-dotenv` are standard dependencies across the builder's Flask apps.

### Step 3: Build the Prompt Template

**File**: `backend/prompt.py`

**Purpose**: Construct the system prompt and user message from structured preferences. This is the product — prompt quality directly determines name quality, rationale accuracy, and cultural sensitivity. Treat this file as the most important code in the entire backend.

The prompt must do four things: (1) instruct Claude on the output JSON schema, (2) inject the user's specific preferences so rationale references them, (3) set guardrails for cultural sensitivity and pronunciation accuracy, (4) control the count and diversity of results.

**Pattern**:
```python
import json
from typing import Optional

SYSTEM_PROMPT = """You are a baby name expert with deep knowledge of names across cultures, 
their etymologies, pronunciation, and cultural significance.

You generate personalized baby name suggestions based on specific parental preferences.
Every name you suggest must be a real name with verifiable origin and meaning — do not 
invent names.

CRITICAL RULES:
- Each rationale MUST directly reference the parent's stated preferences to explain why 
  this specific name fits
- Pronunciation guides use simple phonetic spelling (e.g., "ah-REE-ah" not IPA)
- Be culturally accurate — do not attribute a name to the wrong origin
- Popularity tiers: "common" (top 100 nationally), "rising" (gaining popularity, 
  100-500 range), "rare" (uncommon, below 500)
- Return ONLY valid JSON — no markdown, no explanation outside the JSON structure

OUTPUT FORMAT:
Return a JSON array of objects with exactly these fields:
{
  "names": [
    {
      "name": "string",
      "pronunciation": "string (phonetic, e.g. 'ah-REE-ah')",
      "origin": "string (primary cultural origin)",
      "meaning": "string (literal meaning or interpretation)",
      "popularity": "common | rising | rare",
      "rationale": "string (1-2 sentences explaining why this name fits THIS parent's preferences)"
    }
  ]
}"""


def build_user_message(preferences: dict) -> str:
    """Construct the user message from structured preferences."""
    parts = []

    gender = preferences.get("gender", "neutral")
    gender_label = {
        "boy": "a boy",
        "girl": "a girl",
        "neutral": "any gender (gender-neutral names preferred)"
    }.get(gender, "any gender")

    parts.append(f"I'm looking for baby names for {gender_label}.")

    styles = preferences.get("styles", [])
    if styles:
        style_str = ", ".join(styles)
        parts.append(f"Style preferences: {style_str}.")

    origins = preferences.get("origins", [])
    if origins:
        origin_str = ", ".join(origins)
        parts.append(f"Cultural origins I'm drawn to: {origin_str}.")

    themes = preferences.get("meaningThemes", [])
    if themes:
        theme_str = ", ".join(themes)
        parts.append(f"I want the name to evoke: {theme_str}.")

    letter = preferences.get("startingLetter")
    if letter:
        parts.append(f"Prefer names starting with the letter {letter}.")

    siblings = preferences.get("siblingNames", [])
    if siblings:
        sibling_str = ", ".join(siblings)
        parts.append(
            f"Sibling names to harmonize with: {sibling_str}. "
            f"The new name should sound good alongside these."
        )

    count = preferences.get("count", 8)
    parts.append(f"Generate exactly {count} name suggestions.")

    parts.append(
        "For each name, explain in the rationale WHY it fits my specific "
        "preferences — reference my stated style, origin, or meaning preferences directly."
    )

    return " ".join(parts)
```

Design notes:
- The system prompt is a constant — it defines Claude's role and output format. Changes here affect every generation.
- The user message is dynamic — it injects preferences so Claude's rationale can reference them. The phrase "reference my stated style, origin, or meaning preferences directly" is load-bearing. Without it, rationale becomes generic.
- `count` defaults to 8 names — enough variety without overwhelming, and keeps API cost per request reasonable.
- No few-shot examples in the prompt. Claude's instruction following is strong enough that examples add token cost without improving quality. If output quality is inconsistent, add one example as a first iteration step.

### Step 4: Implement the Claude API Call

**File**: `backend/generate.py`

**Purpose**: Call the Claude API with the constructed prompt, parse the JSON response, validate it, and retry once on malformed output. This is the Structured AI Output pattern from the [Architecture](./architecture.md).

**Pattern**:
```python
import json
import anthropic
from prompt import SYSTEM_PROMPT, build_user_message

client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

REQUIRED_FIELDS = {"name", "pronunciation", "origin", "meaning", "popularity", "rationale"}
VALID_POPULARITY = {"common", "rising", "rare"}


def generate_names(preferences: dict) -> list[dict]:
    """Generate name cards from preferences via Claude API.
    
    Returns a list of validated name card dicts.
    Retries once on malformed response.
    """
    user_message = build_user_message(preferences)

    for attempt in range(2):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text
        names = _parse_and_validate(text)
        if names is not None:
            return names

    raise ValueError("Failed to get valid structured response from Claude after 2 attempts")


def _parse_and_validate(text: str) -> list[dict] | None:
    """Parse Claude's response and validate the name card schema.
    
    Returns validated name list, or None if parsing/validation fails.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try extracting JSON from markdown code block if Claude wraps it
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        else:
            return None

    # Handle both {"names": [...]} and bare [...]
    if isinstance(data, list):
        names = data
    elif isinstance(data, dict) and "names" in data:
        names = data["names"]
    else:
        return None

    if not isinstance(names, list) or len(names) == 0:
        return None

    # Validate each name card
    validated = []
    for card in names:
        if not isinstance(card, dict):
            continue
        if not REQUIRED_FIELDS.issubset(card.keys()):
            continue
        if card.get("popularity") not in VALID_POPULARITY:
            card["popularity"] = "rising"  # Safe fallback
        validated.append(card)

    return validated if len(validated) > 0 else None
```

Design notes:
- Uses `claude-sonnet-4-6` — fast enough for 3-8 second response times with good quality. Upgrade to `claude-opus-4-6` only if rationale quality is insufficient after prompt iteration.
- `max_tokens=2048` is generous for 8 name cards (~150 tokens each). Keeps headroom for longer rationale.
- The JSON fallback parser handles the edge case where Claude wraps output in a markdown code block despite being told not to. This is defensive, not expected.
- Popularity fallback to "rising" is a pragmatic choice — "rising" is the safest default that doesn't mislead (unlike "common" or "rare" which make specific claims).
- Single retry is sufficient. Claude's structured output reliability is ~99%+. If both attempts fail, something is wrong with the prompt, not with luck.

### Step 5: Set Up the Usage Meter

**File**: `backend/usage.py`

**Purpose**: Track generation count per device ID in Neon Postgres. This is the data layer for paywall enforcement (Task 5 wires the gating logic). For now, it increments counts and reports remaining generations.

**Pattern**:
```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

FREE_GENERATION_LIMIT = 3

def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Create the usage tracking table if it doesn't exist."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS babyname_usage (
                    device_id TEXT PRIMARY KEY,
                    generation_count INTEGER DEFAULT 0,
                    first_used TIMESTAMPTZ DEFAULT NOW(),
                    last_used TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            conn.commit()


def get_usage(device_id: str) -> dict:
    """Get current generation count and remaining free generations."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT generation_count FROM babyname_usage WHERE device_id = %s",
                (device_id,)
            )
            row = cur.fetchone()

    count = row["generation_count"] if row else 0
    remaining = max(0, FREE_GENERATION_LIMIT - count)

    return {
        "count": count,
        "remaining": remaining,
        "limit_reached": remaining == 0,
    }


def increment_usage(device_id: str) -> int:
    """Increment generation count. Returns new remaining count."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO babyname_usage (device_id, generation_count, last_used)
                VALUES (%s, 1, NOW())
                ON CONFLICT (device_id) DO UPDATE
                SET generation_count = babyname_usage.generation_count + 1,
                    last_used = NOW()
                RETURNING generation_count
            """, (device_id,))
            conn.commit()
            new_count = cur.fetchone()["generation_count"]

    return max(0, FREE_GENERATION_LIMIT - new_count)
```

Design notes:
- `FREE_GENERATION_LIMIT = 3` matches the paywall trigger discussed in the [Epic](./epic.md). This constant is the single source of truth for the free tier boundary.
- `UPSERT` via `ON CONFLICT` handles first-use and repeat-use in one query. No need to check-then-insert.
- `first_used` and `last_used` timestamps are useful for future analytics but aren't consumed by any current feature.
- Connection-per-query is fine at validation scale. Connection pooling is a scaling concern for post-200-user optimization.

### Step 6: Wire the Generate Endpoint

**File**: `backend/app.py` (extend)

**Purpose**: Connect the pieces — receive preferences + device ID from the app, check usage, call Claude, validate response, increment usage, return name cards. This is the `GenerationProxy` from the [Architecture](./architecture.md).

**Pattern**:
```python
from generate import generate_names
from usage import init_db, get_usage, increment_usage

# Initialize the usage table on startup
with app.app_context():
    if os.getenv("DATABASE_URL"):
        init_db()


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()

    if not data or "preferences" not in data:
        return jsonify({"error": "Missing preferences"}), 400

    preferences = data["preferences"]
    device_id = data.get("deviceId", request.headers.get("X-Device-Id", "anonymous"))

    # Check usage (soft check — Task 5 adds hard paywall gating)
    usage = get_usage(device_id) if os.getenv("DATABASE_URL") else None

    try:
        names = generate_names(preferences)
    except ValueError as e:
        return jsonify({"error": str(e)}), 502

    # Track usage
    remaining = None
    if os.getenv("DATABASE_URL"):
        remaining = increment_usage(device_id)

    return jsonify({
        "names": names,
        "generationsRemaining": remaining,
    })
```

Design notes:
- `deviceId` comes from the request body or an `X-Device-Id` header. The app sends `identifierForVendor` on iOS (Capacitor provides this). Falls back to "anonymous" for browser testing.
- `DATABASE_URL` check allows running without Postgres during local development — Claude API works, usage tracking is skipped. This avoids requiring a database for prompt iteration.
- Error handling is minimal by design. A 502 on Claude failure is honest — the client shows "generation failed, try again." No retry logic at the HTTP layer; the Claude call already retries once internally.
- The response shape matches the `GenerationResponse` TypeScript interface from Step 1.

### Step 7: Create the Environment File

**File**: `backend/.env`

**Purpose**: Store API keys and database connection strings. This file is gitignored.

**Pattern**:
```bash
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

Add to `.gitignore`:
```
backend/.env
```

### Step 8: Build the Angular Generation Service

**File**: `src/app/services/generation.service.ts`

**Purpose**: Frontend service that posts the `PreferenceModel` to the backend and returns typed `NameCard[]`. This is the bridge between the preference wizard (Task 1) and the results screen (Task 3).

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PreferenceModel } from '../models/preference.model';
import { GenerationResponse } from '../models/name-card.model';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class GenerationService {

  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  generate(
    preferences: PreferenceModel,
    deviceId: string
  ): Observable<GenerationResponse> {
    return this.http.post<GenerationResponse>(
      `${this.apiUrl}/api/generate`,
      { preferences, deviceId }
    );
  }
}
```

**File**: `src/environments/environment.ts`

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:3200',
};
```

### Step 9: Get Device ID for Usage Tracking

**File**: `src/app/services/device.service.ts`

**Purpose**: Retrieve a stable device identifier for usage tracking. On iOS, this is `identifierForVendor` via Capacitor. In the browser (dev), generate and persist a UUID.

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Device } from '@capacitor/device';
import { Preferences } from '@capacitor/preferences';

const DEVICE_ID_KEY = 'device_id';

@Injectable({ providedIn: 'root' })
export class DeviceService {

  private cachedId: string | null = null;

  async getDeviceId(): Promise<string> {
    if (this.cachedId) return this.cachedId;

    if (Capacitor.isNativePlatform()) {
      const info = await Device.getId();
      this.cachedId = info.identifier;
    } else {
      // Browser fallback — generate and persist a UUID
      const { value } = await Preferences.get({ key: DEVICE_ID_KEY });
      if (value) {
        this.cachedId = value;
      } else {
        this.cachedId = crypto.randomUUID();
        await Preferences.set({ key: DEVICE_ID_KEY, value: this.cachedId });
      }
    }

    return this.cachedId;
  }
}
```

Design notes:
- `@capacitor/device` provides `identifierForVendor` on iOS — stable per vendor, resets on reinstall. This is the device fingerprinting strategy from the [Architecture](./architecture.md).
- Browser fallback uses `crypto.randomUUID()` persisted to Capacitor Preferences. Good enough for development and web testing.

### Step 10: Wire Generation into the Preference Flow

**File**: `src/app/pages/preferences/preferences.page.ts` (extend the `submit` method from Task 1)

**Purpose**: Connect the preference wizard's submit action to the generation service. After caching preferences, call the backend and navigate to results with the response.

**Pattern**:
```typescript
import { GenerationService } from '../../services/generation.service';
import { DeviceService } from '../../services/device.service';

// In constructor:
constructor(
  private router: Router,
  private prefCache: PreferenceCacheService,
  private generationService: GenerationService,
  private deviceService: DeviceService,
) {}

isGenerating = false;

async submit(): Promise<void> {
  await this.prefCache.save(this.preferences);
  this.isGenerating = true;

  const deviceId = await this.deviceService.getDeviceId();

  this.generationService.generate(this.preferences, deviceId).subscribe({
    next: (response) => {
      this.isGenerating = false;
      this.router.navigate(['/results'], {
        state: {
          names: response.names,
          generationsRemaining: response.generationsRemaining,
          preferences: this.preferences,
        }
      });
    },
    error: (err) => {
      this.isGenerating = false;
      // Show a toast or inline error — Task 3 refines the error UX
      console.error('Generation failed:', err);
    }
  });
}
```

Add a loading state to the template:
```html
<!-- In the nav-bar section -->
<ion-button (click)="submit()" [disabled]="!canProceed() || isGenerating">
  <ion-spinner *ngIf="isGenerating" name="crescent"></ion-spinner>
  <span *ngIf="!isGenerating">
    {{ currentStep === totalSteps - 1 ? 'Find Names' : 'Next' }}
  </span>
</ion-button>
```

Design notes:
- `isGenerating` flag disables the button and shows a spinner during the 3-8 second Claude API call. No timeout — Claude's own timeout handles hung requests.
- Router state carries both the name cards and the preferences, so the results page can display "Showing names for: modern, nature-inspired girl names" without re-fetching.
- Error handling is minimal here. A `console.error` is sufficient for Task 2 — Task 3 adds user-facing error states.

---

## Verification

How to verify this implementation works:

### Backend verification (no frontend needed):

```bash
cd backend
pip install flask flask-cors anthropic psycopg2-binary python-dotenv
python app.py
```

```bash
# Health check
curl http://localhost:3200/api/health

# Generate names (minimal preferences — gender only)
curl -X POST http://localhost:3200/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {"gender": "girl", "styles": [], "origins": [], "meaningThemes": [], "startingLetter": null, "siblingNames": []},
    "deviceId": "test-device-1"
  }'

# Generate names (full preferences)
curl -X POST http://localhost:3200/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {"gender": "boy", "styles": ["modern", "nature"], "origins": ["Japanese", "Scandinavian"], "meaningThemes": ["Strength", "Wisdom"], "startingLetter": "K", "siblingNames": ["Luna"]},
    "deviceId": "test-device-2"
  }'
```

**Expected Result**:
- Response returns in 3-8 seconds
- JSON response contains `names` array with 8 objects
- Each object has all 6 required fields: `name`, `pronunciation`, `origin`, `meaning`, `popularity`, `rationale`
- `popularity` values are one of: `common`, `rising`, `rare`
- `rationale` references the user's stated preferences (check that "modern", "nature", "Japanese", etc. appear in rationale text)
- `generationsRemaining` is a number (or `null` if no DATABASE_URL)

### Prompt quality check:

After the curl test, manually review the output:
1. Are the names real and culturally accurate?
2. Do pronunciations make sense phonetically?
3. Does each rationale reference specific stated preferences?
4. Is there diversity in the results (not all from one origin, not all the same style)?
5. Does the starting letter constraint hold?
6. Do the names sound harmonious with the sibling name?

If any of these fail, iterate the prompt in `backend/prompt.py`. This is expected — prompt iteration is the core development loop for this task.

### Usage tracking verification (requires DATABASE_URL):

```bash
# Run the generate curl 3 times with the same device ID
# Check remaining count decrements: 2, 1, 0

# Query the database directly
psql $DATABASE_URL -c "SELECT * FROM babyname_usage WHERE device_id = 'test-device-1'"
```

### End-to-end verification (with frontend):

```bash
# Terminal 1: Backend
cd backend && python app.py

# Terminal 2: Frontend
ionic serve
```

1. Complete the preference wizard from Task 1
2. Tap "Find Names" — spinner appears
3. After 3-8 seconds, app navigates to `/results` with name card data in router state
4. Open browser devtools, check the Network tab for the `/api/generate` request and response

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 as done
2. Proceed to **Task 3: Name Card UI + Results Screen** — it consumes the `NameCard[]` and `GenerationResponse` this task produces
3. Iterate the prompt in `backend/prompt.py` based on output quality — this iteration continues throughout development and post-launch

---

## Related Documents

- [Solution Architecture](./architecture.md) — Generation Engine component design, Prompt-as-Product pattern, Structured AI Output pattern
- [Epic](./epic.md) — Task 2 scope, generation quality as product differentiator
- [Analysis](./analysis.md) — Why personalized rationale matters: no competitor explains why a name fits
- [Timeline](./timeline.md) — Status tracking