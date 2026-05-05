# 🛠️ Task 3: AI Curation Pipeline

**Purpose**: Build the two-pass ranking system that transforms ~200 raw events into 5 personalized, opinionated picks per subscriber — the core value proposition of Bubls.

**Effort**: 2 days

**Dependencies**: Task 1 (Event Ingestion) must be complete — `bubls_events_raw` must contain events with embeddings.

**Parallel With**: Task 5 (Onboarding) if Task 2 is done

**Blocks**: Task 4 (Push + Email Delivery) — cannot deliver picks that don't exist yet

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Vector similarity query to narrow ~200 events to ~15 candidates per subscriber
- Claude Haiku prompt that ranks, filters, and summarizes 15 → 5 picks
- Structured JSON output written to `bubls_picks` table
- Bilingual handling: German titles preserved, English summaries generated
- Full subscriber loop: process all subscribers in one curation run
- Idempotent writes: re-running for the same week overwrites, never duplicates

### What's NOT Included
- Notification/email delivery — that's Task 4
- Subscriber signup or interest management — that's Task 5
- Engagement tracking writes — the `bubls_engagement` table exists but nothing writes to it yet
- Parallelized subscriber processing — sequential loop is correct at < 200 subscribers

---

## Prerequisites

Before starting:
- Task 1 complete: `bubls_events_raw` populated with events and `embedding vector(1536)` columns filled
- `bubls_subscribers` table exists with at least one test subscriber (insert manually for dev)
- `bubls_picks` table created (see Step 1)
- Python environment with `psycopg2`, `anthropic`, `numpy` installed
- `ANTHROPIC_API_KEY` and `NEON_DATABASE_URL` available as environment variables
- OpenAI API access (for embedding subscriber interest keywords)

---

## Implementation Steps

### Step 1: Create the `bubls_picks` table

**File**: `pipeline/sql/003_create_picks.sql`

**Purpose**: Storage for the denormalized weekly picks per subscriber.

The table is keyed on `subscriber_id + week_start` so re-running curation for the same week is an upsert, not a duplicate insert. The `picks` column is JSONB containing the full 5-pick payload — no JOINs needed at read time.

**Pattern**:
```sql
CREATE TABLE IF NOT EXISTS bubls_picks (
    id SERIAL PRIMARY KEY,
    subscriber_id INTEGER NOT NULL REFERENCES bubls_subscribers(id),
    week_start DATE NOT NULL,
    picks JSONB NOT NULL,
    model_used TEXT DEFAULT 'claude-haiku',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (subscriber_id, week_start)
);

CREATE INDEX idx_picks_subscriber_week 
    ON bubls_picks(subscriber_id, week_start DESC);
```

Run this migration against your Neon instance before proceeding.

### Step 2: Build the vector similarity query

**File**: `pipeline/curation_service.py`

**Purpose**: First pass — reduce ~200 events to ~15 relevant candidates per subscriber using pgvector cosine similarity.

The query embeds the subscriber's interests as a single combined vector, then finds the closest events by cosine distance. The interest keywords (e.g., "music", "food", "outdoors") are concatenated into a single string and embedded via OpenAI, then compared against stored event embeddings.

**Pattern**:
```python
import psycopg2
import openai
import json
from datetime import date, timedelta

def get_interest_embedding(interests: list[str]) -> list[float]:
    """Embed subscriber interests as a single vector."""
    combined = ", ".join(interests)
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=combined
    )
    return response.data[0].embedding

def get_candidate_events(conn, interest_embedding: list[float], limit: int = 15) -> list[dict]:
    """Vector similarity search: return top N candidate events."""
    # Only consider events happening in the upcoming week
    today = date.today()
    window_end = today + timedelta(days=10)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, source, source_id, title, description, 
                   venue_name, venue_address, start_datetime, end_datetime,
                   price_info, url, category,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM bubls_events_raw
            WHERE start_datetime >= %s
              AND start_datetime <= %s
              AND expired = FALSE
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (interest_embedding, today, window_end, interest_embedding, limit))
        
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
```

Key details:
- `<=>` is pgvector's cosine distance operator — lower is more similar
- The date window filters to upcoming events only (no point recommending expired ones)
- 15 candidates gives Claude enough variety without blowing up token cost
- `similarity` score is returned for debugging but not passed to Claude — let the LLM make its own judgment

### Step 3: Build the Claude Haiku curation prompt

**File**: `pipeline/curation_service.py` (continued)

**Purpose**: Second pass — Claude ranks 15 candidates, selects 5, and generates English summaries while preserving German titles.

The prompt is the algorithm. It encodes editorial taste: prefer variety over clustering, prefer unique over generic, prefer actionable details (price, time) over vague descriptions. The structured JSON output format ensures the response can be parsed without regex.

**Pattern**:
```python
import anthropic

CURATION_PROMPT = """You are a local event curator for Zürich, Switzerland. You help international residents discover the best events happening this week.

You will receive {candidate_count} candidate events. Your job:

1. **Select exactly 5 events** that make the best weekly recommendation set
2. **Rank them** from most to least compelling
3. **Write a 1-2 sentence English summary** for each — opinionated, not neutral. Say why someone should go, not just what it is.
4. **Preserve the original German title exactly** — do not translate it

Selection criteria:
- VARIETY: Don't pick 3 concerts. Spread across different experience types.
- UNIQUENESS: Prefer one-time events over recurring weekly ones.
- QUALITY SIGNAL: Named performers, specific venues, and clear pricing suggest a real event. Vague listings suggest filler.
- ACTIONABILITY: Events with clear time/venue/price are more useful than "TBA" listings.

The subscriber is interested in: {interests}

Respond with ONLY a JSON array of exactly 5 objects. No markdown, no commentary.

Each object must have:
- "title": string (original German title, exactly as provided)
- "summary": string (your English editorial summary, 1-2 sentences)
- "venue_name": string
- "venue_address": string
- "start_datetime": string (ISO 8601)
- "end_datetime": string or null
- "price_info": string or "Free" or "TBA"
- "url": string (link to event source)
- "source_event_id": integer (the id from the candidate list)

CANDIDATES:
{candidates_json}"""

def curate_picks(candidates: list[dict], interests: list[str]) -> list[dict]:
    """Send candidates to Claude Haiku, get back 5 ranked picks."""
    # Format candidates for the prompt — strip embedding vectors, keep readable fields
    candidates_for_prompt = []
    for c in candidates:
        candidates_for_prompt.append({
            "id": c["id"],
            "title": c["title"],
            "description": c["description"][:500],  # Truncate long descriptions
            "venue_name": c["venue_name"],
            "venue_address": c["venue_address"],
            "start_datetime": str(c["start_datetime"]),
            "end_datetime": str(c["end_datetime"]) if c["end_datetime"] else None,
            "price_info": c["price_info"] or "TBA",
            "url": c["url"],
            "category": c["category"]
        })
    
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": CURATION_PROMPT.format(
                candidate_count=len(candidates_for_prompt),
                interests=", ".join(interests),
                candidates_json=json.dumps(candidates_for_prompt, indent=2, default=str)
            )
        }]
    )
    
    response_text = message.content[0].text
    picks = json.loads(response_text)
    
    if len(picks) != 5:
        raise ValueError(f"Expected 5 picks, got {len(picks)}")
    
    return picks
```

Key details:
- Description truncated to 500 chars per candidate to keep input tokens bounded (~15 candidates × 500 chars ≈ 2K tokens input)
- The prompt explicitly says "no markdown, no commentary" to get clean JSON — Haiku follows this reliably
- `source_event_id` in the output links picks back to `bubls_events_raw` for engagement tracking later
- The `interests` string gives Claude context for its ranking without embedding the full subscriber profile

### Step 4: Write picks to `bubls_picks`

**File**: `pipeline/curation_service.py` (continued)

**Purpose**: Persist the 5 curated picks as a single JSONB row per subscriber per week.

The upsert on `(subscriber_id, week_start)` makes the pipeline idempotent — re-running Thursday's curation overwrites picks instead of creating duplicates.

**Pattern**:
```python
def write_picks(conn, subscriber_id: int, picks: list[dict]):
    """Upsert this week's picks for a subscriber."""
    # Week starts on Monday — picks are generated Thursday, consumed Thu-Sun
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday of current week
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO bubls_picks (subscriber_id, week_start, picks, model_used)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (subscriber_id, week_start)
            DO UPDATE SET 
                picks = EXCLUDED.picks,
                model_used = EXCLUDED.model_used,
                created_at = NOW()
        """, (subscriber_id, week_start, json.dumps(picks), "claude-haiku-4-5-20251001"))
    
    conn.commit()
```

### Step 5: Orchestrate the full curation run

**File**: `pipeline/curate.py`

**Purpose**: Main entry point — loop through all active subscribers, run the two-pass pipeline for each, write results.

This is the script that gets triggered by cron every Thursday. It processes subscribers sequentially — at < 200 subscribers, the full run completes in under 5 minutes. Each subscriber is independent, so a failure for one subscriber doesn't block the others.

**Pattern**:
```python
import os
import sys
import logging
import psycopg2
from curation_service import get_interest_embedding, get_candidate_events, curate_picks, write_picks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def get_active_subscribers(conn) -> list[dict]:
    """Fetch all active subscribers with their interests."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, email, interests 
            FROM bubls_subscribers 
            WHERE active = TRUE
        """)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

def run_curation():
    conn = psycopg2.connect(os.environ["NEON_DATABASE_URL"])
    
    subscribers = get_active_subscribers(conn)
    logger.info(f"Processing {len(subscribers)} active subscribers")
    
    success_count = 0
    error_count = 0
    
    for sub in subscribers:
        try:
            logger.info(f"Curating for subscriber {sub['id']} ({sub['email']})")
            
            # Pass 1: Vector similarity
            interest_embedding = get_interest_embedding(sub["interests"])
            candidates = get_candidate_events(conn, interest_embedding, limit=15)
            
            if len(candidates) < 5:
                logger.warning(f"Only {len(candidates)} candidates for subscriber {sub['id']} — skipping")
                continue
            
            # Pass 2: Claude curation
            picks = curate_picks(candidates, sub["interests"])
            
            # Write results
            write_picks(conn, sub["id"], picks)
            success_count += 1
            logger.info(f"Wrote 5 picks for subscriber {sub['id']}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Failed for subscriber {sub['id']}: {e}")
            continue  # Don't let one subscriber's failure block others
    
    conn.close()
    logger.info(f"Curation complete: {success_count} succeeded, {error_count} failed")
    
    if error_count > 0 and success_count == 0:
        sys.exit(1)  # All failed — signal error to CI

if __name__ == "__main__":
    run_curation()
```

Key details:
- If fewer than 5 candidates are found, the subscriber is skipped rather than asking Claude to work with insufficient data
- Per-subscriber error handling with `continue` — one bad subscriber doesn't stop the batch
- Exit code 1 only if every subscriber failed (total pipeline failure), not on partial failures
- Logging includes subscriber ID and email for debugging curation quality issues

### Step 6: Add the curation step to the GitHub Actions workflow

**File**: `.github/workflows/weekly-pipeline.yml`

**Purpose**: Wire the curation script into the Thursday cron workflow, running after ingestion completes.

If Task 1 already created this workflow with the ingestion step, add the curation step after it. If not, create the full workflow — ingestion and curation run sequentially in the same job.

**Pattern**:
```yaml
# Add this step AFTER the ingestion step in the weekly pipeline job
- name: Run AI curation
  env:
    NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    cd pipeline
    python curate.py
```

The curation step depends on ingestion completing first (events must exist in `bubls_events_raw` before they can be queried). Both steps run in the same job, sequentially. No need for separate jobs or artifact passing — they share the same Python environment and database connection.

---

## Verification

### Local verification with a test subscriber

```bash
# 1. Insert a test subscriber (if not already present)
psql $NEON_DATABASE_URL -c "
  INSERT INTO bubls_subscribers (email, city, interests, token, active)
  VALUES ('test@example.com', 'zurich', '{music,food,outdoors}', gen_random_uuid(), TRUE)
  ON CONFLICT (email) DO NOTHING;
"

# 2. Verify events exist with embeddings
psql $NEON_DATABASE_URL -c "
  SELECT COUNT(*) as total_events, 
         COUNT(embedding) as with_embeddings 
  FROM bubls_events_raw 
  WHERE expired = FALSE;
"

# 3. Run curation
cd pipeline
NEON_DATABASE_URL=$NEON_DATABASE_URL \
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
OPENAI_API_KEY=$OPENAI_API_KEY \
python curate.py

# 4. Check the output
psql $NEON_DATABASE_URL -c "
  SELECT s.email, p.week_start, 
         jsonb_array_length(p.picks) as pick_count,
         p.picks->0->>'title' as first_pick_title,
         p.picks->0->>'summary' as first_pick_summary
  FROM bubls_picks p
  JOIN bubls_subscribers s ON s.id = p.subscriber_id
  ORDER BY p.created_at DESC
  LIMIT 5;
"
```

**Expected Result**:
- Curation log shows "Wrote 5 picks for subscriber X" for each active subscriber
- `bubls_picks` contains one row per subscriber for the current week
- Each row's `picks` JSONB has exactly 5 objects
- Titles are in German (original), summaries are in English
- Picks show variety (not all the same category)
- Total pipeline runtime < 30 seconds for 1 subscriber, < 5 minutes for 200

### Cost verification

After running for N subscribers, check your Anthropic dashboard:
- Expected input: ~2K tokens/subscriber (15 candidates × ~130 tokens each)
- Expected output: ~500 tokens/subscriber (5 picks with summaries)
- Expected cost: ~$0.02/subscriber on Haiku pricing
- For 200 subscribers: ~$4 total per weekly run

---

## Edge Cases to Handle

| Case | Behavior |
|------|----------|
| Fewer than 5 candidate events | Skip subscriber, log warning. Don't ask Claude to pad with irrelevant picks. |
| Claude returns malformed JSON | Catch `json.JSONDecodeError`, log the raw response, skip subscriber. |
| Claude returns != 5 picks | Raise `ValueError`, log it, skip subscriber. Don't silently accept 3 or 7 picks. |
| Subscriber has no interests set | Skip subscriber. Interests are required for the vector query — no interests means no signal. |
| All events are from one source | Not a problem — Claude's variety criterion handles this. The prompt says "don't pick 3 concerts," not "don't pick 3 Ticketmaster events." |
| Re-run on same day | Upsert overwrites previous picks. No duplicates, no side effects. |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 as done
2. Proceed to Task 4 (Push + Email Delivery) — this task produces the `bubls_picks` data that Task 4 delivers
3. Test curation quality manually — read through the 5 picks for a test subscriber and assess whether they feel like genuine recommendations or generic listings. Tune the prompt if needed.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Two-pass ranking design, prompt strategy, cost model
- [Epic](./epic.md) – Task scope and dependencies
- [Timeline](./timeline.md) – Status tracking