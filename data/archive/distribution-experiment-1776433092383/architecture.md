---
sidebar_position: 3
---

# 🏗️ Distribution Experiment — Solution Architecture

**Purpose**: Technical design for the 100-strangers funnel tracking and landing page.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Three components, all minimal. A static landing page hosted on Coolify converts Reddit traffic into TestFlight signups. A Flask tracking endpoint records funnel events to Neon Postgres. A Capacitor lifecycle listener in the Bubls app fires app-open events. The day-7 verdict is a SQL query, not a dashboard. No new services, no analytics SDK, no build pipeline for the landing page.

The architecture optimizes for speed-to-deploy and measurement accuracy, not scalability. This system serves one experiment for one week. If the experiment produces signal, the tracking infrastructure evolves into the product's analytics layer. If it doesn't, everything except the Neon table gets deleted.

```
Reddit Post
    │
    ▼
Landing Page (static HTML, Coolify)
    │ page_view event ──→ POST /api/track ──→ Neon: distribution_events
    │
    ▼
TestFlight CTA click
    │ testflight_click event ──→ POST /api/track ──→ Neon: distribution_events
    │
    ▼
TestFlight Install → App Open
    │ app_open event ──→ POST /api/track ──→ Neon: distribution_events
    │
    ▼ (24h+ later)
App Return (derived server-side from app_open timestamps)
    │
    ▼
Day-7 SQL Query → Verdict
```

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | No analytics framework. One table, one endpoint, one query. Build the system only if the experiment says there's a product worth measuring. |
| Neon Postgres for everything | All event tracking in Neon. No Mixpanel, no Amplitude, no PostHog. The data lives where the rest of the product data lives. |
| Flask, minimal | Tracking endpoint is ~20 lines. Flask factory pattern. No middleware, no auth on this endpoint. |
| Mock mode via environment flag | `TRACK_ENABLED=false` skips the DB write and returns 200. Used in dev/test to avoid polluting production data. |
| Anti-Corruption Layer | Landing page and app client fire generic events. The server interprets them (e.g., deriving `app_return` from `app_open` timestamps). Client never decides what qualifies as a "return." |

---

## Component Design

### Task 1: Tracking Endpoint + Schema

**Purpose**: Record funnel events from landing page and app.

**Components**:
- `server/modules/tracking/model.py` — SQLAlchemy model for `distribution_events` table
- `server/modules/tracking/routes.py` — Flask blueprint, single `POST /api/track` route
- `server/modules/tracking/dto.py` — Pydantic model for request validation (event_type enum, session_id UUID, metadata dict)
- `alembic/versions/xxxx_add_distribution_events.py` — Migration

**Schema**:
```sql
CREATE TABLE distribution_events (
    id            SERIAL PRIMARY KEY,
    session_id    UUID NOT NULL,
    event_type    VARCHAR(20) NOT NULL CHECK (event_type IN ('page_view', 'testflight_click', 'app_open', 'app_return')),
    device_id     VARCHAR(64),
    metadata      JSONB DEFAULT '{}',
    ip_hash       VARCHAR(64),
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_type ON distribution_events(event_type);
CREATE INDEX idx_events_device ON distribution_events(device_id) WHERE device_id IS NOT NULL;
CREATE INDEX idx_events_created ON distribution_events(created_at);
```

**Rate limiting**: 10 events/minute per IP. Implemented as a simple in-memory counter (not Redis — one server, one week). IP is hashed (SHA-256, no salt needed — this prevents abuse, not identity tracking) before storage.

**Patterns**: Adapter pattern — the route calls `tracking_adapter.record(event)`, which in production writes to Neon and in mock mode (`TRACK_ENABLED=false`) logs to stdout and returns success.

### Task 2: Landing Page

**Purpose**: Convert Reddit visitors into TestFlight signups and capture non-iOS interest.

**Components**:
- `landing/index.html` — Single HTML file, inline CSS, inline JS
- `landing/Dockerfile` — `nginx:alpine` serving the static file
- `landing/og-image.png` — Open Graph image for Reddit/social previews

**Structure**:
```html
<!-- Entire page in one file, no build step -->
<html>
<head>
    <meta property="og:title" content="Bubls — [one-line pitch]">
    <meta property="og:image" content="og-image.png">
    <!-- inline critical CSS -->
</head>
<body>
    <h1>[What Bubls does]</h1>
    <img src="screenshot.webp" loading="eager" width="300">
    <a href="https://testflight.apple.com/join/[CODE]" data-test="testflight-cta">
        Try on iOS (TestFlight)
    </a>
    <form data-test="email-capture">
        <input type="email" placeholder="Get notified for Android/Web">
        <button type="submit">Notify me</button>
    </form>
    <script>
        // Generate session_id (UUID v4), store in sessionStorage
        // Fire page_view on load
        // Fire testflight_click on CTA tap
        // Email capture POSTs to /api/track with event_type 'email_signup'
    </script>
</body>
</html>
```

**Performance target**: < 1s load on 3G. Achieved by: no framework, inline CSS, single image (WebP, < 100KB), no external fonts, no JS libraries.

**Hosting**: Coolify Docker deployment. Separate from the Bubls app — landing page deploys don't affect the product.

### Task 3: App-Open Event Instrumentation

**Purpose**: Track when strangers actually open the app, and identify returns.

**Components**:
- `src/app/shared/tracking/tracking.service.ts` — Standalone Angular service, sends events to `/api/track`
- `src/app/app.component.ts` — Modified to call tracking on Capacitor `appStateChange`

**Pattern**:
```typescript
// tracking.service.ts
@Injectable({ providedIn: 'root' })
export class TrackingService {
  private http = inject(HttpClient);
  private deviceId = signal<string>('');

  constructor() {
    this.initDeviceId();
  }

  private async initDeviceId() {
    const stored = await Preferences.get({ key: 'device_id' });
    if (stored.value) {
      this.deviceId.set(stored.value);
    } else {
      const id = crypto.randomUUID();
      await Preferences.set({ key: 'device_id', value: id });
      this.deviceId.set(id);
    }
  }

  trackAppOpen() {
    this.http.post(`${environment.apiUrl}/api/track`, {
      event_type: 'app_open',
      device_id: this.deviceId(),
      session_id: crypto.randomUUID(),
      metadata: { platform: Capacitor.getPlatform() }
    }).subscribe();
  }
}
```

**Return detection (server-side)**: The `app_return` event type is never sent by the client. The day-7 verdict query derives it:

```sql
-- A "return" is any device that opened the app more than 24h after its first open
WITH first_opens AS (
    SELECT device_id, MIN(created_at) as first_open
    FROM distribution_events
    WHERE event_type = 'app_open' AND device_id IS NOT NULL
    GROUP BY device_id
)
SELECT de.device_id, fo.first_open, de.created_at as return_at
FROM distribution_events de
JOIN first_opens fo ON de.device_id = fo.device_id
WHERE de.event_type = 'app_open'
  AND de.created_at > fo.first_open + INTERVAL '24 hours';
```

### Task 4: Reddit Research + Post Draft

**Purpose**: Craft the post and validate the channel.

**Components**:
- `docs/distribution/reddit-post-draft.md` — Post text, backup versions
- `docs/distribution/channel-checklist.md` — Rules verification, timing research

**No code.** This task is research and writing. The output is a markdown file committed to the repo so the post can be reviewed before publishing.

### Task 5: Publish + Verify

**Purpose**: Go live and confirm the entire funnel works.

**Components**: No new code. This task is a manual end-to-end walkthrough.

**Verification sequence**:
1. Landing page responds 200 at production URL
2. Open landing page → check `distribution_events` for `page_view` row
3. Click TestFlight CTA → check for `testflight_click` row
4. Install from TestFlight → open app → check for `app_open` row with `device_id`
5. Record: post URL, publish timestamp, subreddit

### Task 6: Day-7 Verdict

**Purpose**: Run the numbers and make the decision.

**Components**:
- `docs/distribution/verdict-day7.md` — Results, funnel numbers, decision

**Verdict query**:
```sql
SELECT
    COUNT(*) FILTER (WHERE event_type = 'page_view') as page_views,
    COUNT(DISTINCT session_id) FILTER (WHERE event_type = 'testflight_click') as testflight_clicks,
    COUNT(DISTINCT device_id) FILTER (WHERE event_type = 'app_open') as unique_opens,
    (SELECT COUNT(DISTINCT de.device_id)
     FROM distribution_events de
     JOIN (SELECT device_id, MIN(created_at) as first_open
           FROM distribution_events
           WHERE event_type = 'app_open' AND device_id IS NOT NULL
           GROUP BY device_id) fo
     ON de.device_id = fo.device_id
     WHERE de.event_type = 'app_open'
       AND de.created_at > fo.first_open + INTERVAL '24 hours'
    ) as returning_users
FROM distribution_events;
```

**Decision framework**:
- `returning_users / unique_opens >= 0.05` → Signal. Plan next distribution channel.
- `returning_users / unique_opens = 0` → No signal. Kill or pivot. Document why.
- Between 0% and 5% → Check qualitative signal (DMs, comments, engagement). Decide within 24h.

---

## Execution Flow

```
[Phase 1 — Build]  (Tasks 1-3 parallel, ~1 day)
   Task 1 (tracking endpoint) ──┐
   Task 2 (landing page)     ──┼──→ Deploy to Coolify
   Task 3 (app instrumentation)┘

[Phase 2 — Prepare]  (Task 4, ~2h)
   Task 4 (Reddit research + post draft)

[Phase 3 — Launch]  (Task 5, ~1h)
   Task 5 (Publish + end-to-end verify)

[Phase 4 — Wait]  (7 days, no code)
   ... strangers encounter the post ...

[Phase 5 — Decide]  (Task 6, ~1h)
   Task 6 (Run verdict query, write decision)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Static HTML landing page vs. Angular route | Static HTML | No build step, no framework overhead, loads instantly. Landing page is throwaway if experiment fails. Decoupled deploys. |
| Neon Postgres for tracking vs. analytics SaaS | Neon Postgres | Already provisioned. Data lives where product data lives. No vendor lock-in for a one-week experiment. Free tier more than sufficient. |
| Server-side return detection vs. client-side | Server-side | Single authoritative definition of "return." No client clock skew. No risk of app update changing the definition. Query-time derivation means the definition can evolve without redeploying. |
| In-memory rate limiting vs. Redis | In-memory | One server, one week, <1000 expected visitors. Redis is infrastructure before a feature. In-memory counter resets on deploy, which is acceptable for abuse prevention at this scale. |
| Hash IP vs. store raw | Hash | No reason to store raw IPs. Hash prevents abuse counting, satisfies data minimization. No salt needed — this isn't password storage, it's rate-limit bucketing. |
| Landing page email capture vs. TestFlight-only | Include email capture | Non-iOS visitors are lost without it. Email list has value for Android/web launch. Costs one `<form>` element and one tracking event. |
| One subreddit vs. cross-post | One subreddit | Analysis constraint: one channel, one post, one week. Cross-posting muddies attribution and may violate Reddit rules. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

