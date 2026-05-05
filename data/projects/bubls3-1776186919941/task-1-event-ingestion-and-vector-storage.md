Now I have full context. Let me generate the implementation guide.

# Implementation: Event Ingestion and Vector Storage

**Purpose**: Build the Python worker that pulls events from Ticketmaster and Guidle, generates vector embeddings, and stores everything in `bubls_events_raw` — the foundation the entire curation pipeline reads from.

**Effort**: 3 days

**Dependencies**: None — this is a greenfield task on existing infrastructure (Neon Postgres with pgvector already enabled, API keys already provisioned).

**Parallel With**: Task 2 (Cross-platform client) — no shared code or artifacts.

**Blocks**: Task 3 (AI Curation Pipeline) — curation queries `bubls_events_raw` for vector similarity search.

**Related**:
- [Solution Architecture](./architecture.md) — Component design, data model, technology rationale
- [Epic](./epic.md) — Task scope and success criteria

---

## Overview

### What's Included
- Database schema: `bubls_events_raw` table with pgvector `embedding` column
- `TicketmasterClient` — Discovery API v2 integration for Zürich events
- `GuidleClient` — Veranstaltungskalender endpoint integration
- `EmbeddingService` — OpenAI text-embedding-3-small (1536 dimensions)
- `EventStore` — Upsert logic with `source + source_id` deduplication
- `ingest.py` — Single-run entry point script (cron-compatible)
- Environment configuration and local test harness

### What's NOT Included
- AI curation or Claude calls — that's Task 3
- GitHub Actions cron trigger — wire that up when the script is proven locally
- Subscriber-aware queries — ingestion is subscriber-independent
- Unstructured source scraping (EventFrog, Facebook) — APIs only for v1

---

## Prerequisites

Before starting:
- Python 3.11+ installed
- Neon Postgres connection string (from existing shared instance, EU Central 1)
- Ticketmaster API key (Discovery API v2) — already provisioned
- OpenAI API key (for text-embedding-3-small) — already provisioned
- Access to the 2024 Java backend repo for reference (`TicketmasterClient.java`, Guidle integration)
- Familiarity with pgvector — Neon has it enabled, no extension install needed

---

## Implementation Steps

### Step 1: Project scaffolding

**File**: `worker/`

**Purpose**: Set up the Python project with minimal dependencies — no framework, just a script.

Create the project structure:

```
worker/
├── ingest.py              # Entry point
├── clients/
│   ├── __init__.py
│   ├── ticketmaster.py    # TicketmasterClient
│   └── guidle.py          # GuidleClient
├── services/
│   ├── __init__.py
│   ├── embeddings.py      # EmbeddingService
│   └── event_store.py     # EventStore
├── models.py              # Event dataclass
├── config.py              # Environment loading
├── requirements.txt
└── .env.example
```

**requirements.txt**:
```
psycopg2-binary>=2.9
openai>=1.0
requests>=2.31
python-dotenv>=1.0
pgvector>=0.3
```

Install:
```bash
cd worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Step 2: Database schema

**File**: `worker/schema.sql`

**Purpose**: Create the `bubls_events_raw` table with pgvector support on the shared Neon instance.

```sql
-- pgvector is already enabled on Neon, but ensure it:
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS bubls_events_raw (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,           -- 'ticketmaster' or 'guidle'
    source_id       TEXT NOT NULL,           -- External event ID
    title           TEXT NOT NULL,           -- Original (German) title
    description     TEXT,                    -- Event description for embedding
    venue           TEXT,
    address         TEXT,
    city            TEXT NOT NULL DEFAULT 'zurich',
    event_date      TIMESTAMPTZ,
    price_min       NUMERIC(10,2),
    price_max       NUMERIC(10,2),
    currency        TEXT DEFAULT 'CHF',
    url             TEXT,                    -- Link to event source page
    image_url       TEXT,
    category        TEXT,                    -- Genre/type from source
    embedding       vector(1536),            -- OpenAI text-embedding-3-small
    raw_json        JSONB,                   -- Full API response for debugging
    active          BOOLEAN DEFAULT TRUE,    -- Soft-delete flag
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_source_event UNIQUE (source, source_id)
);

-- Index for vector similarity search (used by Task 3 curation)
CREATE INDEX IF NOT EXISTS idx_events_embedding
    ON bubls_events_raw
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- Index for filtering active future events
CREATE INDEX IF NOT EXISTS idx_events_active_date
    ON bubls_events_raw (active, event_date)
    WHERE active = TRUE;
```

Run against Neon:
```bash
psql "$DATABASE_URL" -f schema.sql
```

**Note**: The `ivfflat` index with `lists = 10` is tuned for < 500 rows. At this scale, an exact scan would also be fast, but the index is cheap to create and avoids revisiting this when row counts grow. Rebuild the index after the first ingestion run (`REINDEX INDEX idx_events_embedding;`) for accurate list centroids.

---

### Step 3: Event data model

**File**: `worker/models.py`

**Purpose**: Single dataclass that both API clients produce — replaces Java's MapStruct mappers with plain construction.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Event:
    source: str                    # 'ticketmaster' or 'guidle'
    source_id: str                 # External unique ID
    title: str                     # Original language (usually German)
    description: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    city: str = "zurich"
    event_date: Optional[datetime] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    currency: str = "CHF"
    url: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    raw_json: Optional[dict] = field(default=None, repr=False)

    @property
    def embedding_text(self) -> str:
        """Text sent to OpenAI for embedding generation.
        Combines title, description, venue, and category for richer vectors."""
        parts = [self.title]
        if self.description:
            parts.append(self.description)
        if self.venue:
            parts.append(f"Venue: {self.venue}")
        if self.category:
            parts.append(f"Category: {self.category}")
        return " | ".join(parts)
```

Only 10 fields that matter for curation — everything else stays in `raw_json` for debugging.

---

### Step 4: Configuration

**File**: `worker/config.py`

**Purpose**: Load environment variables with sensible defaults. No config framework — `os.environ` and `.env`.

```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]          # Neon connection string
TICKETMASTER_API_KEY = os.environ["TICKETMASTER_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Guidle doesn't require auth — public API
GUIDLE_BASE_URL = os.getenv("GUIDLE_BASE_URL", "https://www.guidle.com")

# Defaults
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
TICKETMASTER_CITY = "Zürich"
TICKETMASTER_COUNTRY_CODE = "CH"
TICKETMASTER_RADIUS = 30  # km
```

**.env.example**:
```
DATABASE_URL=postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
TICKETMASTER_API_KEY=xxx
OPENAI_API_KEY=sk-xxx
```

---

### Step 5: TicketmasterClient

**File**: `worker/clients/ticketmaster.py`

**Purpose**: Query Discovery API v2 for upcoming Zürich events. Port the proven 2024 Java integration to Python, keeping only the fields the `Event` dataclass needs.

```python
import requests
from datetime import datetime, timezone
from models import Event
import config

class TicketmasterClient:
    BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

    def fetch_events(self) -> list[Event]:
        """Pull upcoming events for Zürich. Paginates through all results."""
        events = []
        page = 0

        while True:
            params = {
                "apikey": config.TICKETMASTER_API_KEY,
                "city": config.TICKETMASTER_CITY,
                "countryCode": config.TICKETMASTER_COUNTRY_CODE,
                "radius": config.TICKETMASTER_RADIUS,
                "unit": "km",
                "startDateTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sort": "date,asc",
                "size": 100,
                "page": page,
            }

            resp = requests.get(self.BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            embedded = data.get("_embedded", {})
            raw_events = embedded.get("events", [])

            if not raw_events:
                break

            for raw in raw_events:
                events.append(self._map_event(raw))

            # Check if more pages exist
            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

        return events

    def _map_event(self, raw: dict) -> Event:
        """Map Ticketmaster response to Event dataclass.
        Only extract the 10 fields that matter for curation."""
        # Venue extraction
        venues = raw.get("_embedded", {}).get("venues", [{}])
        venue = venues[0] if venues else {}
        venue_name = venue.get("name")
        address_parts = []
        if addr := venue.get("address", {}).get("line1"):
            address_parts.append(addr)
        if city := venue.get("city", {}).get("name"):
            address_parts.append(city)

        # Date extraction
        dates = raw.get("dates", {}).get("start", {})
        event_date = None
        if date_str := dates.get("dateTime"):
            event_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Price extraction
        price_ranges = raw.get("priceRanges", [{}])
        price = price_ranges[0] if price_ranges else {}

        # Category extraction
        classifications = raw.get("classifications", [{}])
        classification = classifications[0] if classifications else {}
        genre = classification.get("genre", {}).get("name")

        # Image extraction — prefer 16:9 ratio
        images = raw.get("images", [])
        image_url = None
        for img in images:
            if img.get("ratio") == "16_9":
                image_url = img.get("url")
                break
        if not image_url and images:
            image_url = images[0].get("url")

        return Event(
            source="ticketmaster",
            source_id=raw["id"],
            title=raw.get("name", "Untitled"),
            description=raw.get("info") or raw.get("pleaseNote"),
            venue=venue_name,
            address=" ,".join(address_parts) if address_parts else None,
            event_date=event_date,
            price_min=price.get("min"),
            price_max=price.get("max"),
            currency=price.get("currency", "CHF"),
            url=raw.get("url"),
            image_url=image_url,
            category=genre,
            raw_json=raw,
        )
```

**Key differences from Java version**: No MapStruct, no DTOs, no null-safety wrappers. Python's `dict.get()` with defaults replaces the entire mapping layer. The `raw_json` field preserves the full response for debugging without needing a separate table.

**API notes**:
- Rate limit: 5 requests/second, 5000/day — more than sufficient for a weekly batch of 2-3 pages
- The `startDateTime` filter ensures we only pull future events
- Pagination: Ticketmaster returns max 100 per page, typically 2-3 pages for Zürich

---

### Step 6: GuidleClient

**File**: `worker/clients/guidle.py`

**Purpose**: Query the Guidle Veranstaltungskalender for Zürich events. Navigate the nested `groupSet → offers → events` hierarchy. This is the Swiss-specific source that Ticketmaster doesn't cover well (local cultural events, smaller venues).

```python
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from models import Event

class GuidleClient:
    # Guidle returns XML — the Veranstaltungskalender endpoint
    BASE_URL = "https://www.guidle.com/angebote"

    def fetch_events(self) -> list[Event]:
        """Pull upcoming Zürich events from Guidle's public API."""
        params = {
            "city": "Zürich",
            "startDate": datetime.now().strftime("%Y-%m-%d"),
            "resultLanguage": "de",
            "contentType": "xml",
            "max": 200,
        }

        resp = requests.get(self.BASE_URL, params=params, timeout=30)
        resp.raise_for_status()

        return self._parse_response(resp.text)

    def _parse_response(self, xml_text: str) -> list[Event]:
        """Navigate groupSet → offers → scheduleEntries hierarchy."""
        events = []
        root = ET.fromstring(xml_text)

        # Guidle nests: groupSet > offer > scheduleEntries > scheduleEntry
        for offer in root.iter("offer"):
            offer_id = offer.get("id", "")
            title_el = offer.find(".//title")
            title = title_el.text if title_el is not None else "Untitled"

            desc_el = offer.find(".//shortDescription")
            description = desc_el.text if desc_el is not None else None

            # Venue and address from location
            location = offer.find(".//address")
            venue_name = None
            address = None
            if location is not None:
                company = location.find("company")
                venue_name = company.text if company is not None else None
                street = location.find("street")
                zip_code = location.find("zipCode")
                city = location.find("city")
                addr_parts = []
                if street is not None and street.text:
                    addr_parts.append(street.text)
                if zip_code is not None and zip_code.text:
                    addr_parts.append(zip_code.text)
                if city is not None and city.text:
                    addr_parts.append(city.text)
                address = ", ".join(addr_parts) if addr_parts else None

            # Category
            category_el = offer.find(".//classification/type")
            category = category_el.text if category_el is not None else None

            # Image
            image_el = offer.find(".//image/url")
            image_url = image_el.text if image_el is not None else None

            # URL
            url_el = offer.find(".//externalLink")
            url = url_el.text if url_el is not None else None

            # Parse schedule entries — one Event per date
            for entry in offer.iter("scheduleEntry"):
                event_date = None
                start_date = entry.find("startDate")
                if start_date is not None and start_date.text:
                    try:
                        event_date = datetime.fromisoformat(start_date.text)
                    except ValueError:
                        pass

                entry_id = entry.get("id", "")
                events.append(Event(
                    source="guidle",
                    source_id=f"{offer_id}-{entry_id}" if entry_id else offer_id,
                    title=title,
                    description=description,
                    venue=venue_name,
                    address=address,
                    event_date=event_date,
                    url=url,
                    image_url=image_url,
                    category=category,
                    raw_json=None,  # XML source, not JSON
                ))

        return events
```

**Key notes**:
- Guidle returns XML, not JSON — use `xml.etree.ElementTree` (stdlib, no extra dependency)
- One offer can have multiple schedule entries (recurring events) — create one `Event` per date
- The `source_id` combines offer ID + schedule entry ID for uniqueness
- No auth required — Guidle's Veranstaltungskalender is a public endpoint
- Swiss-specific venue formatting (street, PLZ, city) is preserved as-is

**Important**: The exact Guidle XML structure may have changed since the 2024 Java integration. Run a test fetch first and adjust the XPath queries if the hierarchy differs. The core pattern (offer → scheduleEntry) has been stable, but field names within `<address>` or `<classification>` may vary.

---

### Step 7: EmbeddingService

**File**: `worker/services/embeddings.py`

**Purpose**: Generate 1536-dimensional vectors for event descriptions via OpenAI. Batch events to minimize API calls.

```python
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

class EmbeddingService:

    def generate(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.
        OpenAI supports up to 2048 inputs per call — more than enough for ~200 events."""
        if not texts:
            return []

        response = client.embeddings.create(
            model=config.EMBEDDING_MODEL,
            input=texts,
            dimensions=config.EMBEDDING_DIMENSIONS,
        )

        # Return embeddings in the same order as input texts
        return [item.embedding for item in response.data]
```

**Cost check**: text-embedding-3-small at $0.02/M tokens. 200 events × ~100 tokens each = 20K tokens = $0.0004 per weekly run. Negligible.

**Why batch**: One API call for all 200 events instead of 200 individual calls. Faster and avoids rate limit concerns. The OpenAI embeddings endpoint accepts up to 2048 inputs per request.

---

### Step 8: EventStore

**File**: `worker/services/event_store.py`

**Purpose**: Upsert events into `bubls_events_raw` with deduplication on `source + source_id`. Handle soft-deletion of expired events.

```python
import json
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from models import Event
import config

class EventStore:

    def __init__(self):
        self.conn = psycopg2.connect(config.DATABASE_URL)
        register_vector(self.conn)

    def upsert_events(self, events: list[Event], embeddings: list[list[float]]):
        """Upsert events with embeddings. Deduplicates on (source, source_id).
        Updates existing events if data has changed."""
        if not events:
            return

        rows = []
        for event, embedding in zip(events, embeddings):
            rows.append((
                event.source,
                event.source_id,
                event.title,
                event.description,
                event.venue,
                event.address,
                event.city,
                event.event_date,
                event.price_min,
                event.price_max,
                event.currency,
                event.url,
                event.image_url,
                event.category,
                embedding,
                json.dumps(event.raw_json) if event.raw_json else None,
            ))

        sql = """
            INSERT INTO bubls_events_raw (
                source, source_id, title, description, venue, address, city,
                event_date, price_min, price_max, currency, url, image_url,
                category, embedding, raw_json, active, updated_at
            )
            VALUES %s
            ON CONFLICT (source, source_id) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                venue = EXCLUDED.venue,
                address = EXCLUDED.address,
                event_date = EXCLUDED.event_date,
                price_min = EXCLUDED.price_min,
                price_max = EXCLUDED.price_max,
                currency = EXCLUDED.currency,
                url = EXCLUDED.url,
                image_url = EXCLUDED.image_url,
                category = EXCLUDED.category,
                embedding = EXCLUDED.embedding,
                raw_json = EXCLUDED.raw_json,
                active = TRUE,
                updated_at = NOW()
        """

        template = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb, TRUE, NOW())"

        with self.conn.cursor() as cur:
            execute_values(cur, sql, rows, template=template, page_size=100)
        self.conn.commit()

    def deactivate_expired(self):
        """Soft-delete events whose date has passed.
        Retains rows (and embeddings) for historical analysis."""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE bubls_events_raw
                SET active = FALSE, updated_at = NOW()
                WHERE active = TRUE AND event_date < NOW()
            """)
            count = cur.rowcount
        self.conn.commit()
        return count

    def count_active(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bubls_events_raw WHERE active = TRUE")
            return cur.fetchone()[0]

    def close(self):
        self.conn.close()
```

**Key design decisions**:
- `execute_values` for batch upsert — significantly faster than individual INSERTs
- `ON CONFLICT DO UPDATE` makes the script idempotent — safe to re-run
- Soft-delete via `active = FALSE` keeps embeddings for historical data (per architecture principle: "accumulate data before you need it")
- `pgvector.psycopg2.register_vector` enables native Python list → pgvector conversion

---

### Step 9: Main ingestion script

**File**: `worker/ingest.py`

**Purpose**: Entry point that orchestrates the full pipeline: fetch → embed → store. Designed to be run by cron (GitHub Actions or system cron).

```python
#!/usr/bin/env python3
"""Weekly event ingestion for Bubls.
Run: python ingest.py
Idempotent — safe to re-run for the same week."""

import sys
import logging
from clients.ticketmaster import TicketmasterClient
from clients.guidle import GuidleClient
from services.embeddings import EmbeddingService
from services.event_store import EventStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def main():
    store = EventStore()
    embedder = EmbeddingService()

    # Step 1: Deactivate expired events
    expired = store.deactivate_expired()
    log.info(f"Deactivated {expired} expired events")

    # Step 2: Fetch from all sources
    all_events = []

    try:
        tm_events = TicketmasterClient().fetch_events()
        log.info(f"Ticketmaster: {len(tm_events)} events")
        all_events.extend(tm_events)
    except Exception as e:
        log.error(f"Ticketmaster fetch failed: {e}")
        # Continue with other sources — partial data is better than no data

    try:
        guidle_events = GuidleClient().fetch_events()
        log.info(f"Guidle: {len(guidle_events)} events")
        all_events.extend(guidle_events)
    except Exception as e:
        log.error(f"Guidle fetch failed: {e}")

    if not all_events:
        log.error("No events from any source — aborting")
        sys.exit(1)

    log.info(f"Total events fetched: {len(all_events)}")

    # Step 3: Generate embeddings (single batch call)
    texts = [e.embedding_text for e in all_events]
    log.info(f"Generating embeddings for {len(texts)} events...")
    embeddings = embedder.generate(texts)
    log.info("Embeddings generated")

    # Step 4: Upsert to database
    store.upsert_events(all_events, embeddings)
    active_count = store.count_active()
    log.info(f"Upsert complete. Active events in database: {active_count}")

    store.close()
    log.info("Ingestion complete")


if __name__ == "__main__":
    main()
```

**Design notes**:
- Each source fetch is wrapped in try/except independently — if Ticketmaster is down, Guidle events still get ingested. "5 picks from one source is better than 0 picks from two" (from architecture risk mitigation).
- Exit code 1 only if zero events from all sources — this signals failure to the cron scheduler.
- The script is sequential and completes in under a minute for ~200 events. No async, no parallelism — premature optimization at this scale.

---

## Verification

### Local test run

```bash
cd worker
source .venv/bin/activate

# 1. Run schema migration
psql "$DATABASE_URL" -f schema.sql

# 2. Run ingestion
python ingest.py
```

**Expected output**:
```
2026-04-XX [INFO] Deactivated 0 expired events
2026-04-XX [INFO] Ticketmaster: ~80-150 events
2026-04-XX [INFO] Guidle: ~50-100 events
2026-04-XX [INFO] Total events fetched: ~150-250
2026-04-XX [INFO] Generating embeddings for ~200 events...
2026-04-XX [INFO] Embeddings generated
2026-04-XX [INFO] Upsert complete. Active events in database: ~200
2026-04-XX [INFO] Ingestion complete
```

### Database verification

```bash
# Check row count
psql "$DATABASE_URL" -c "SELECT source, COUNT(*) FROM bubls_events_raw WHERE active = TRUE GROUP BY source;"

# Verify embeddings are present (not null)
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM bubls_events_raw WHERE embedding IS NOT NULL;"

# Test vector similarity (preview for Task 3)
psql "$DATABASE_URL" -c "
    SELECT title, category, 1 - (embedding <=> (
        SELECT embedding FROM bubls_events_raw LIMIT 1
    )) AS similarity
    FROM bubls_events_raw
    WHERE active = TRUE
    ORDER BY embedding <=> (SELECT embedding FROM bubls_events_raw LIMIT 1)
    LIMIT 5;
"
```

### Idempotency check

```bash
# Run twice — row count should stay the same
python ingest.py
python ingest.py
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM bubls_events_raw;"
# Should show same count both times (upsert, not insert)
```

### Rebuild vector index after first run

```bash
psql "$DATABASE_URL" -c "REINDEX INDEX idx_events_embedding;"
```

The `ivfflat` index needs data to compute centroids. After the first ingestion populates ~200 rows, reindex once for accurate similarity search.

---

## Edge Cases to Handle

| Scenario | Behavior |
|----------|----------|
| Ticketmaster API down | Log error, continue with Guidle only |
| Guidle XML format changed | Parsing fails, log error, continue with Ticketmaster only |
| Event has no description | `embedding_text` falls back to title + venue + category |
| Duplicate event across sources | Different `source` values → stored as separate rows (correct — same event from Ticketmaster and Guidle may have different metadata) |
| OpenAI rate limit | Unlikely at 200 events; if hit, the single batch call fails and the script exits with an error for manual retry |
| Re-run same week | Upsert updates existing rows — no duplicates, latest data wins |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 as done
2. Proceed to **Task 3: AI Curation Pipeline** — it depends directly on `bubls_events_raw` being populated with embeddings
3. Optionally: wire up a GitHub Actions workflow with a Thursday cron trigger (`cron: '0 15 * * 4'` — 15:00 UTC = 17:00 CET, giving 1 hour before the 18:00 curation run)

---

## Related Documents

- [Solution Architecture](./architecture.md) — Component design, data model, two-pass ranking rationale
- [Epic](./epic.md) — Task scope and dependencies
- [Timeline](./timeline.md) — Status tracking