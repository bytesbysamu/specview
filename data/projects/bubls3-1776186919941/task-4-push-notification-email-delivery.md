Now I have enough context. Here's the implementation guide:

# 🛠️ Task 4: Push notification + email delivery

**Purpose**: Wire Thursday 6pm delivery across iOS push notifications and email so every subscriber receives their 5 picks regardless of app install status or push opt-in.

**Effort**: 2 days

**Dependencies**: Task 2 (Cross-Platform Client — provides push token registration UI), Task 3 (AI Curation Pipeline — provides picks to deliver)

**Parallel With**: —

**Blocks**: End-to-end weekly flow (ingestion → curation → delivery)

**Related**:
- [Solution Architecture](./architecture.md) — Notification scheduling and email template design
- [Epic](./epic.md) — Task scope and delivery requirements

---

## Overview

### What's Included
- iOS push notification delivery via APNs (server-side Python)
- Client-side push token registration via `@capacitor/push-notifications`
- Email delivery via Resend API with deep links
- `NotificationScheduler` orchestration — runs after curation, sends both channels in parallel
- `bubls_subscribers` schema extension for device tokens
- Email template with 5 event cards, web deep link (magic link), and iOS universal link

### What's NOT Included
- Android push notifications — iOS-only for v1 per architecture decision
- Subscriber notification preferences UI — both channels always fire, email is not opt-out
- Retry queue or dead-letter handling — at <200 subscribers, manual re-run of the script handles failures
- Push notification analytics — `bubls_engagement` captures clicks but not delivery/open metrics in v1

---

## Prerequisites

Before starting:
- Task 2 complete: Angular + Ionic + Capacitor app shell exists with a working iOS build
- Task 3 complete: `bubls_picks` table is populated with weekly picks per subscriber
- Apple Developer account configured: APNs key (.p8 file) generated, Team ID and Key ID noted
- Resend API key provisioned (already available from Humanize-me)
- `bubls_subscribers` table exists with `email`, `token`, and `interests` columns
- Universal links configured in `apple-app-site-association` on the web domain

---

## Implementation Steps

### Step 1: Extend subscriber schema for device tokens

**File**: `worker/schema.sql` (or migration script)

**Purpose**: Store iOS push tokens so the server-side scheduler can target specific devices.

A subscriber may have zero or one push token. Storing it directly on the subscriber row avoids a junction table — one device per subscriber is sufficient for v1.

**Pattern**:
```sql
ALTER TABLE bubls_subscribers
ADD COLUMN device_token TEXT,
ADD COLUMN device_platform TEXT DEFAULT 'ios',
ADD COLUMN push_enabled BOOLEAN DEFAULT FALSE;
```

No separate device table. At <200 subscribers with one device each, a column on the subscriber row is the correct level of normalization.

---

### Step 2: Register push tokens on the client

**File**: `src/app/services/push.service.ts`

**Purpose**: Request push permission on iOS, capture the device token, and send it to the backend for storage.

Capacitor's push plugin handles the platform check internally — on web, the registration call is a no-op, so no conditional logic is needed in the Angular code.

**Pattern**:
```typescript
import { PushNotifications } from '@capacitor/push-notifications';
import { Capacitor } from '@capacitor/core';

export class PushService {
  constructor(private http: HttpClient) {}

  async registerPush(subscriberToken: string): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    const permission = await PushNotifications.requestPermissions();
    if (permission.receive !== 'granted') return;

    await PushNotifications.register();

    PushNotifications.addListener('registration', (token) => {
      // POST device token to backend
      this.http.post('/api/subscribers/device', {
        subscriber_token: subscriberToken,
        device_token: token.value
      }).subscribe();
    });
  }
}
```

Call `registerPush()` after onboarding completes (Task 5) or on app launch if the subscriber is already authenticated. The listener fires once with the APNs device token — store it and move on.

---

### Step 3: Add device token API endpoint

**File**: `worker/api.py` (or the Express proxy — whichever serves the client API)

**Purpose**: Receive and persist device tokens from the iOS client.

**Pattern**:
```python
@app.route('/api/subscribers/device', methods=['POST'])
def register_device():
    data = request.json
    subscriber_token = data['subscriber_token']
    device_token = data['device_token']

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE bubls_subscribers
            SET device_token = %s, push_enabled = TRUE
            WHERE token = %s
        """, (device_token, subscriber_token))
    conn.commit()

    return jsonify({'status': 'ok'})
```

Upsert semantics — if the subscriber reinstalls the app and gets a new token, this overwrites the old one. No token history needed.

---

### Step 4: Build the email template

**File**: `worker/templates/weekly_picks.py`

**Purpose**: Render the 5 picks into a scannable HTML email with deep links to both web and iOS app.

Resend accepts raw HTML or React email templates. For a solo stack, inline HTML keeps the dependency surface small. The email must include two link types per pick: a web link (with magic link token for authentication) and a universal link (opens the iOS app if installed, falls back to web).

**Pattern**:
```python
def render_picks_email(subscriber, picks, week_label):
    """Render weekly picks into HTML email body."""
    cards_html = ""
    for pick in picks:
        web_url = f"https://bubls.ch/picks?token={subscriber['token']}"
        app_url = f"https://bubls.ch/app/picks"  # Universal link

        cards_html += f"""
        <div style="margin-bottom: 24px; padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h3 style="margin: 0 0 8px;">{pick['title']}</h3>
            <p style="color: #555; margin: 0 0 8px;">{pick['summary']}</p>
            <p style="font-size: 14px; color: #888; margin: 0 0 12px;">
                📍 {pick['venue']} · 📅 {pick['datetime']} · 💰 {pick.get('price', 'Free')}
            </p>
            <a href="{pick['url']}" style="color: #2563eb; text-decoration: none;">View event →</a>
        </div>
        """

    return f"""
    <div style="max-width: 600px; margin: 0 auto; font-family: -apple-system, sans-serif;">
        <h2>Your 5 picks for {week_label} 🎯</h2>
        {cards_html}
        <hr style="margin: 32px 0; border: none; border-top: 1px solid #eee;" />
        <p style="font-size: 14px; color: #888;">
            <a href="{web_url}">View in browser</a> ·
            <a href="{app_url}">Open in app</a>
        </p>
    </div>
    """
```

Keep the template simple. No external CSS, no images, no complex layout — email clients strip most of it anyway. Inline styles only.

---

### Step 5: Build the Resend email sender

**File**: `worker/notifications/email_sender.py`

**Purpose**: Send the rendered email via Resend API to a single subscriber.

**Pattern**:
```python
import resend

resend.api_key = os.environ['RESEND_API_KEY']

def send_picks_email(subscriber, picks, week_label):
    html = render_picks_email(subscriber, picks, week_label)

    resend.Emails.send({
        "from": "Bubls <picks@bubls.ch>",
        "to": subscriber['email'],
        "subject": f"Your 5 picks for {week_label}",
        "html": html
    })
```

No batching API needed. Resend's free tier supports 100 emails/day — at <200 subscribers, sequential sends complete in under a minute. If a single send fails, log and continue to the next subscriber rather than aborting the entire batch.

---

### Step 6: Build the APNs push sender

**File**: `worker/notifications/push_sender.py`

**Purpose**: Send a push notification to a single iOS device via APNs.

Use a lightweight APNs library (`aioapns` or `gobiko.apns`) rather than OneSignal or Firebase — at <200 subscribers, the abstraction layer adds a dependency without reducing complexity.

**Pattern**:
```python
import jwt
import httpx
import time

APNS_KEY_PATH = os.environ['APNS_KEY_PATH']  # .p8 file
APNS_KEY_ID = os.environ['APNS_KEY_ID']
APNS_TEAM_ID = os.environ['APNS_TEAM_ID']
BUNDLE_ID = 'ch.bubls.app'

# Production: api.push.apple.com, Sandbox: api.sandbox.push.apple.com
APNS_HOST = os.environ.get('APNS_HOST', 'https://api.push.apple.com')

def _get_apns_token():
    """Generate short-lived JWT for APNs authentication."""
    with open(APNS_KEY_PATH, 'r') as f:
        key = f.read()

    payload = {
        'iss': APNS_TEAM_ID,
        'iat': int(time.time())
    }
    return jwt.encode(payload, key, algorithm='ES256', headers={
        'kid': APNS_KEY_ID
    })

def send_push(device_token: str, title: str, body: str):
    """Send a single push notification via APNs HTTP/2."""
    token = _get_apns_token()

    headers = {
        'authorization': f'bearer {token}',
        'apns-topic': BUNDLE_ID,
        'apns-push-type': 'alert',
        'apns-priority': '5',  # Normal priority — not time-critical
    }

    payload = {
        'aps': {
            'alert': {
                'title': title,
                'body': body
            },
            'badge': 5,
            'sound': 'default'
        }
    }

    with httpx.Client(http2=True) as client:
        resp = client.post(
            f'{APNS_HOST}/3/device/{device_token}',
            json=payload,
            headers=headers
        )

    if resp.status_code != 200:
        print(f"APNs error for {device_token[:8]}...: {resp.status_code} {resp.text}")
```

Key details:
- APNs requires HTTP/2 — use `httpx` with `http2=True` (requires `pip install httpx[http2]`)
- Token-based auth (.p8 key + JWT) is simpler than certificate-based auth
- `apns-priority: 5` sends at battery-efficient timing — the notification is not urgent enough for priority 10
- Use sandbox host during TestFlight, production host after App Store release

---

### Step 7: Build the NotificationScheduler

**File**: `worker/notifications/scheduler.py`

**Purpose**: Orchestrate delivery across both channels for all subscribers after curation completes.

This is the integration point. It reads picks from `bubls_picks`, iterates subscribers, and fires both push and email for each. Both channels carry the same 5 picks — email is not a degraded fallback.

**Pattern**:
```python
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def deliver_weekly_picks(conn, week_start: str):
    """Send picks to all active subscribers via push + email."""
    week_label = datetime.strptime(week_start, '%Y-%m-%d').strftime('%B %d')

    with conn.cursor() as cur:
        cur.execute("""
            SELECT s.id, s.email, s.token, s.device_token, s.push_enabled,
                   p.picks
            FROM bubls_subscribers s
            JOIN bubls_picks p ON p.subscriber_id = s.id
            WHERE p.week_start = %s AND s.active = TRUE
        """, (week_start,))

        subscribers = cur.fetchall()

    sent = 0
    errors = 0

    for sub in subscribers:
        subscriber = dict(sub)
        picks = subscriber['picks']  # JSONB, already parsed

        # Email — always send
        try:
            send_picks_email(subscriber, picks, week_label)
            logger.info(f"Email sent to {subscriber['email']}")
        except Exception as e:
            logger.error(f"Email failed for {subscriber['email']}: {e}")
            errors += 1

        # Push — only if opted in and has device token
        if subscriber['push_enabled'] and subscriber['device_token']:
            try:
                title_pick = picks[0]['title'] if picks else "Your picks are ready"
                send_push(
                    device_token=subscriber['device_token'],
                    title="Your 5 picks are here 🎯",
                    body=f"Top pick: {title_pick}"
                )
                logger.info(f"Push sent to {subscriber['email']}")
            except Exception as e:
                logger.error(f"Push failed for {subscriber['email']}: {e}")
                errors += 1

        sent += 1

    logger.info(f"Delivery complete: {sent} subscribers, {errors} errors")
    return sent, errors
```

Design notes:
- Email fires for every active subscriber — no opt-in check. Email is the reliable baseline.
- Push fires only when `push_enabled` is true and a `device_token` exists. If the user declined the iOS permission prompt, these fields remain false/null.
- Errors are logged but don't abort the loop. One failed send shouldn't block 199 successful ones.
- The push notification body shows the top pick title as a teaser — enough to drive an app open.

---

### Step 8: Wire delivery into the weekly pipeline

**File**: `worker/pipeline.py` (the main cron script)

**Purpose**: Call `deliver_weekly_picks()` as the final step of the Thursday pipeline.

**Pattern**:
```python
def run_weekly_pipeline():
    conn = get_db()
    week_start = get_current_week_start()  # Thursday's date

    # Phase 1: Ingest (Task 1)
    ingest_events(conn)

    # Phase 2: Curate (Task 3)
    curate_picks(conn, week_start)

    # Phase 3: Deliver (Task 4)
    deliver_weekly_picks(conn, week_start)

    conn.close()
```

The delivery step runs synchronously after curation. No separate cron trigger — delivery is part of the same pipeline run. If curation fails, delivery never executes, which is correct behavior (no picks = nothing to deliver).

---

### Step 9: Configure the GitHub Actions cron

**File**: `.github/workflows/weekly-pipeline.yml`

**Purpose**: Trigger the full pipeline (ingest → curate → deliver) at 6pm CET every Thursday.

**Pattern**:
```yaml
name: Weekly Pipeline

on:
  schedule:
    # 6pm CET = 4pm UTC (winter) / 5pm UTC (summer CEST)
    # Use 4pm UTC — during CEST this delivers at 6pm, during CET at 5pm
    # Adjust seasonally or use 5pm UTC for year-round 6pm CET accuracy
    - cron: '0 16 * * 4'  # Every Thursday at 4pm UTC
  workflow_dispatch: {}  # Manual trigger for testing

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install -r worker/requirements.txt

      - run: python worker/pipeline.py
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          RESEND_API_KEY: ${{ secrets.RESEND_API_KEY }}
          APNS_KEY_PATH: ${{ secrets.APNS_KEY_PATH }}
          APNS_KEY_ID: ${{ secrets.APNS_KEY_ID }}
          APNS_TEAM_ID: ${{ secrets.APNS_TEAM_ID }}
          APNS_HOST: https://api.push.apple.com
```

Note on the APNs .p8 key: GitHub Actions secrets store the key content as a string. The pipeline script should write it to a temp file at runtime rather than expecting a file path:

```python
import tempfile

apns_key_content = os.environ.get('APNS_KEY_CONTENT')
if apns_key_content:
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.p8', delete=False)
    f.write(apns_key_content)
    f.close()
    os.environ['APNS_KEY_PATH'] = f.name
```

---

### Step 10: Configure universal links for email deep links

**File**: `web/.well-known/apple-app-site-association`

**Purpose**: Enable email links to open the iOS app when installed, falling back to the web dashboard.

**Pattern**:
```json
{
  "applinks": {
    "apps": [],
    "details": [
      {
        "appID": "TEAM_ID.ch.bubls.app",
        "paths": ["/app/*", "/picks*"]
      }
    ]
  }
}
```

This file must be served from `https://bubls.ch/.well-known/apple-app-site-association` with `Content-Type: application/json`. No file extension. Coolify/Nginx config must serve this path.

On the Capacitor side, ensure `capacitor.config.ts` includes the associated domain:
```typescript
server: {
  hostname: 'bubls.ch'
}
```

And `ios/App/App/App.entitlements` includes:
```xml
<key>com.apple.developer.associated-domains</key>
<array>
  <string>applinks:bubls.ch</string>
</array>
```

---

## Verification

### Local testing (email)

```bash
# Set RESEND_API_KEY and test with a single subscriber
cd worker
RESEND_API_KEY=re_xxx python -c "
from notifications.email_sender import send_picks_email

test_sub = {'email': 'your@email.com', 'token': 'test-uuid'}
test_picks = [
    {'title': 'Jazz Night', 'summary': 'Live jazz at Moods', 'venue': 'Moods', 'datetime': 'Fri 8pm', 'price': 'CHF 25', 'url': 'https://example.com'},
]
send_picks_email(test_sub, test_picks * 5, 'April 17')
"
```

**Expected Result**: Email arrives with 5 event cards, working deep links, clean rendering in Apple Mail and Gmail.

### Local testing (push — sandbox)

```bash
# Use sandbox APNs host for TestFlight builds
APNS_HOST=https://api.sandbox.push.apple.com python -c "
from notifications.push_sender import send_push
send_push('DEVICE_TOKEN_FROM_REGISTRATION', 'Test', 'Your picks are ready')
"
```

**Expected Result**: Push notification appears on the TestFlight device.

### End-to-end pipeline test

```bash
# Manual trigger via GitHub Actions
gh workflow run weekly-pipeline.yml
gh run watch  # Monitor execution
```

**Expected Result**: All active subscribers receive both an email and a push notification (if opted in) with their 5 picks for the current week.

---

## Dependencies (pip)

Add to `worker/requirements.txt`:
```
resend>=2.0.0
httpx[http2]>=0.27.0
PyJWT>=2.8.0
cryptography>=42.0.0  # Required for ES256 JWT signing
```

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 as done
2. Run an end-to-end test with the full Thursday pipeline (Tasks 1 → 3 → 4)
3. Validate email rendering across Apple Mail, Gmail, and Outlook web
4. Confirm push notifications work on TestFlight devices
5. Proceed to Task 5 (Onboarding) if not already complete

---

## Related Documents

- [Solution Architecture](./architecture.md) – Notification scheduling, email template design, dual-channel rationale
- [Epic](./epic.md) – Task scope and dependency chain
- [Timeline](./timeline.md) – Status tracking