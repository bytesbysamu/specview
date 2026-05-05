Now I have all the context needed. Here's the complete implementation guide:

# 🛠️ Task 4: Deploy and distribute

**Purpose**: Ship the complete photoshoot app to Coolify (web) and TestFlight (iOS), invite 15 pre-trained testers, and validate the end-to-end experience on real devices before iterating.

**Effort**: 1 day

**Dependencies**: Task 1 (Shell + Auth), Task 2 (15 LoRA models trained and seeded), Task 3 (Generation pipeline working)

**Parallel With**: —

**Blocks**: —

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Docker Compose configuration for web + Flask backend deployment to Coolify
- iOS build via Capacitor and Xcode, submitted to TestFlight
- GitHub Actions workflow reused from Bubls/Springular patterns
- Pre-warm all 15 LoRA models with dummy inference to avoid cold-start on first real use
- TestFlight invite for 15 pre-trained testers
- Smoke testing: auth, camera permissions, generation, and gallery on a real iOS device
- Coolify webhook deployment for the web build

### What's NOT Included
- Android build — iOS-only for Month 1 per [Epic](./epic.md) scope
- App Store submission — TestFlight only; public release is post-validation
- Custom domain or CDN — Coolify's default domain is sufficient for 15 testers
- Monitoring or alerting — query Neon directly for Month 1; no Grafana or Sentry setup
- Automated E2E tests — manual smoke testing covers the 15-user scale

---

## Prerequisites

Before starting:
- Task 1 complete: shell + auth working, users table populated with 15 tester records
- Task 2 complete: all 15 LoRA models trained, validated, and seeded in `lora_models` table
- Task 3 complete: capture → generate → result → gallery flow working locally
- Apple Developer account active with App Store Connect access (already working from Bubls)
- Xcode installed with valid signing certificate and provisioning profile
- Coolify instance running and accessible (already hosting Humanize-me)
- Docker installed locally for building production images
- Fastlane installed (`gem install fastlane` or `brew install fastlane`) — reuse config from Bubls
- GitHub repo created for the super app (or using existing Constellation repo)
- Environment variables ready for production: `NEON_DATABASE_URL`, `REPLICATE_API_TOKEN`, Supabase keys

---

## Implementation Steps

### Step 1: Create production Docker Compose for web + backend

**File**: `docker-compose.yml` (project root)

**Purpose**: Define the two-service stack (Angular web app served via Nginx, Flask API) as a single deployable unit that Coolify pulls and runs.

This mirrors the Humanize-me deployment pattern: Nginx serves the static Angular build while reverse-proxying `/api` to the Flask backend. One Compose file, one deploy trigger.

**Pattern**:
```yaml
version: "3.8"

services:
  frontend:
    build:
      context: .
      dockerfile: docker/frontend.Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - NEON_DATABASE_URL=${NEON_DATABASE_URL}
      - REPLICATE_API_TOKEN=${REPLICATE_API_TOKEN}
      - FLASK_ENV=production
    restart: unless-stopped
```

### Step 2: Create the frontend Dockerfile

**File**: `docker/frontend.Dockerfile`

**Purpose**: Multi-stage build — Node builds the Angular app, Nginx serves the static output with API proxying.

**Pattern**:
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build -- --configuration=production

# Stage 2: Serve
FROM nginx:alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/spec-doc/browser /usr/share/nginx/html
EXPOSE 80
```

### Step 3: Create the Nginx config with API proxy

**File**: `docker/nginx.conf`

**Purpose**: Serve the Angular SPA and proxy `/api` requests to the Flask backend. This avoids CORS issues in production — the browser sees one origin.

**Pattern**:
```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — all non-file routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to Flask backend
    location /api/ {
        proxy_pass http://backend:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;  # Replicate can take 60s+ on cold start
        client_max_body_size 10M;  # Allow photo uploads
    }
}
```

**Key decision**: `proxy_read_timeout 120s` accommodates worst-case Replicate cold starts. The default 60s would cause timeouts for some users.

### Step 4: Create the Flask backend Dockerfile

**File**: `backend/Dockerfile`

**Purpose**: Minimal Python image running the Flask API with Gunicorn for production.

**Pattern**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
```

**Notes**:
- 4 Gunicorn workers handle concurrent generation requests from 15 users. Per [Architecture](./architecture.md), synchronous Replicate calls block each worker for 10-60s, so 4 workers means 4 simultaneous generations.
- `--timeout 120` matches the Nginx proxy timeout to prevent Gunicorn killing the worker before Replicate responds.

### Step 5: Configure Coolify deployment

**Purpose**: Set up the Coolify project to pull from the GitHub repo and deploy on push.

This reuses the webhook deployment pattern from Humanize-me and Springular.

**Steps**:
1. Log into your Coolify instance
2. Create a new project → select "Docker Compose"
3. Point to the GitHub repo and branch (`main`)
4. Add environment variables in Coolify's UI:
   - `NEON_DATABASE_URL` — production Neon connection string
   - `REPLICATE_API_TOKEN` — Replicate API token
5. Set the domain (Coolify auto-assigns one, or configure a custom subdomain)
6. Deploy — Coolify builds both services from Docker Compose and starts them

**Verification**:
```bash
# After Coolify deploys, test the web build
curl https://YOUR-COOLIFY-DOMAIN/api/generations/YOUR_TEST_USER_UUID
# Should return JSON array of past generations (or empty array)
```

### Step 6: Configure the GitHub Actions workflow

**File**: `.github/workflows/deploy.yml`

**Purpose**: Automate deployment on push to `main`. The workflow triggers the Coolify webhook so every merge deploys automatically.

Reuse the `dorny/paths-filter` pattern from Springular to avoid unnecessary deploys when only docs change.

**Pattern**:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      app: ${{ steps.filter.outputs.app }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            app:
              - 'src/**'
              - 'backend/**'
              - 'docker/**'
              - 'docker-compose.yml'
              - 'package.json'

  deploy-web:
    needs: changes
    if: needs.changes.outputs.app == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Coolify webhook
        run: |
          curl -X POST "${{ secrets.COOLIFY_WEBHOOK_URL }}" \
            -H "Authorization: Bearer ${{ secrets.COOLIFY_TOKEN }}"

  deploy-ios:
    needs: changes
    if: needs.changes.outputs.app == 'true'
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run build -- --configuration=production

      - name: Sync Capacitor
        run: npx cap sync ios

      - name: Install Fastlane
        run: gem install fastlane

      - name: Build and upload to TestFlight
        env:
          APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.ASC_KEY_ID }}
          APP_STORE_CONNECT_API_ISSUER_ID: ${{ secrets.ASC_ISSUER_ID }}
          APP_STORE_CONNECT_API_KEY: ${{ secrets.ASC_PRIVATE_KEY }}
          MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
        run: |
          cd ios/App
          fastlane beta
```

**Key decisions**:
- `paths-filter` prevents iOS builds (slow, expensive macOS runner) when only backend changes ship
- The Coolify webhook approach avoids putting Docker build logic in CI — Coolify handles the build
- Fastlane `beta` lane handles code signing, archive, and TestFlight upload in one step

### Step 7: Configure Fastlane for TestFlight

**File**: `ios/App/fastlane/Fastfile`

**Purpose**: Define the `beta` lane that builds the Xcode project and uploads to TestFlight. Reuse the Bubls Fastlane configuration.

**Pattern**:
```ruby
default_platform(:ios)

platform :ios do
  desc "Build and push to TestFlight"
  lane :beta do
    setup_ci

    api_key = app_store_connect_api_key(
      key_id: ENV["APP_STORE_CONNECT_API_KEY_ID"],
      issuer_id: ENV["APP_STORE_CONNECT_API_ISSUER_ID"],
      key_content: ENV["APP_STORE_CONNECT_API_KEY"],
      is_key_content_base64: true
    )

    match(
      type: "appstore",
      api_key: api_key,
      readonly: true
    )

    increment_build_number(
      build_number: Time.now.strftime("%Y%m%d%H%M")
    )

    build_app(
      workspace: "App.xcworkspace",
      scheme: "App",
      export_method: "app-store",
      clean: true
    )

    upload_to_testflight(
      api_key: api_key,
      skip_waiting_for_build_processing: true
    )
  end
end
```

**Notes**:
- `match` handles code signing certificates via a private Git repo (same as Bubls)
- Build number uses timestamp to auto-increment
- `skip_waiting_for_build_processing` prevents the CI job from blocking for 15+ minutes while Apple processes the build

### Step 8: Update iOS configuration for production

**File**: `ios/App/App/capacitor.config.ts` (or `capacitor.config.json`)

**Purpose**: Point the iOS app's webview to the production API URL instead of localhost.

**Pattern**:
```typescript
const config: CapacitorConfig = {
  appId: 'com.yourname.superapp',
  appName: 'Photoshoot',
  webDir: 'dist/spec-doc/browser',
  server: {
    // In production iOS builds, the web assets are bundled locally.
    // API calls go to the production backend.
    url: undefined, // Use bundled assets
  },
};
```

The Angular `environment.prod.ts` should contain the production API URL:

**File**: `src/environments/environment.prod.ts`
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://YOUR-COOLIFY-DOMAIN/api',
};
```

Update `PhotoService` and any other service to use `environment.apiUrl` instead of hardcoded localhost:

```typescript
import { environment } from '../../environments/environment';

private apiUrl = environment.apiUrl;
```

### Step 9: Pre-warm all 15 LoRA models

**Purpose**: Run a dummy inference on each of the 15 trained models so Replicate moves them from cold to warm state. This prevents the first real user from hitting a 60s cold start.

**Pattern**:
```bash
#!/bin/bash
# pre-warm.sh — Run once before inviting testers

# Fetch all ready models from Neon
MODELS=$(psql $NEON_DATABASE_URL -t -c \
  "SELECT replicate_model_id FROM lora_models WHERE training_status = 'ready'")

# Use a small test image
TEST_IMAGE="test-photo.jpg"

for MODEL in $MODELS; do
  echo "Warming up: $MODEL"
  python3 -c "
import replicate
output = replicate.run('$MODEL', input={
    'prompt': 'a photo of a person, natural lighting',
    'image': open('$TEST_IMAGE', 'rb'),
    'num_outputs': 1,
    'num_inference_steps': 10,
})
print(f'  → Warm: {output}')
" &
done

wait
echo "All models warmed up."
```

**When to run**: After deploying to Coolify, before sending TestFlight invites. Replicate models stay warm for ~15 minutes of inactivity, so time this close to the invite window.

**Note**: This addresses the [Architecture](./architecture.md) risk mitigation for Replicate cold starts. The warm state won't persist indefinitely, but it ensures the first-impression "wow" moment isn't ruined by a 60s wait.

### Step 10: Build and submit the iOS app

**Purpose**: Create the production iOS build and push it to TestFlight. This can run locally (faster for the first time) or via CI.

**Local build (first time)**:
```bash
# 1. Build the Angular app for production
npm run build -- --configuration=production

# 2. Sync to the iOS project
npx cap sync ios

# 3. Open in Xcode for the first build (verify signing, capabilities)
npx cap open ios

# In Xcode:
# - Select your signing team
# - Verify Camera and Photo Library usage descriptions in Info.plist
# - Set the deployment target (iOS 16+)
# - Product → Archive → Distribute → TestFlight
```

**Subsequent builds via Fastlane**:
```bash
cd ios/App
fastlane beta
```

**Verification**: The build appears in App Store Connect → TestFlight within 15-30 minutes.

### Step 11: Invite 15 testers to TestFlight

**Purpose**: Add pre-trained testers to the TestFlight group and send invitations.

**Steps**:
1. Go to App Store Connect → Your App → TestFlight
2. Create an internal testing group (e.g., "Month 1 Testers")
3. Add the 15 testers by email — these must match the emails in the `users` table
4. TestFlight sends invite emails automatically
5. Testers install the app via the TestFlight app on their iPhones

**Alternative — Fastlane pilot**:
```bash
# Add testers via CLI (one per line in testers.csv)
fastlane pilot add \
  --email "tester1@example.com" \
  --group "Month 1 Testers"
```

**Critical check**: Ensure each tester's email in TestFlight matches their `users` table record, which in turn maps to their `lora_models` entry. If the email doesn't match, auth will create a new user with no model → waitlist experience instead of "instant magic."

### Step 12: Smoke test on a real device

**Purpose**: Validate the complete flow on an actual iPhone before declaring Task 4 done. Browser testing misses camera permission behavior, native performance, and real network conditions.

**Test checklist**:

| Test | What to check | Pass criteria |
|------|---------------|---------------|
| Install | TestFlight install completes | App opens, shell loads |
| Auth | Sign in with tester email | User is authenticated, redirected to /photoshoot |
| Camera permission | Tap "Open Camera" | iOS permission dialog appears with custom message from Info.plist |
| Camera capture | Take a photo | Preview shows, generation starts |
| Loading UX | Watch during generation | Phase messages cycle: "Uploading..." → "Your AI model is creating..." → "Still working..." |
| Result display | Generation completes | Before/after slider works, result image is the tester's LoRA output |
| Gallery | Navigate to gallery tab | Shows the generation just completed |
| Upload flow | Use "Choose from Gallery" instead | Same result as camera capture |
| No-model boundary | Sign in as a user without a model | Sees waitlist message, not a crash or empty screen |
| Error recovery | Kill network mid-generation | Error message appears with retry button; retry works when network returns |
| Web build | Visit Coolify domain in Safari | Same functionality as native (minus native camera — uses file picker) |

**If any test fails**: Fix the issue before inviting remaining testers. The first impression is the product — a broken first generation kills the "instant magic" moment.

---

## Day Schedule

| Time | Task |
|------|------|
| **Morning** | Steps 1-5: Docker Compose, Dockerfiles, Nginx config, deploy to Coolify. Verify web build loads and API responds. |
| **Midday** | Steps 6-8: GitHub Actions workflow, Fastlane config, production environment config. Push to trigger first automated deploy. |
| **Afternoon** | Steps 9-12: Pre-warm models, build iOS, submit to TestFlight, invite testers, smoke test on a real device. |

---

## Verification

How to verify the full deployment works:

```bash
# 1. Web build: verify the production domain serves the app
curl -I https://YOUR-COOLIFY-DOMAIN
# Expected: 200 OK, Content-Type: text/html

# 2. API proxy: verify /api routes reach Flask through Nginx
curl https://YOUR-COOLIFY-DOMAIN/api/generations/YOUR_TEST_USER_UUID
# Expected: JSON array (empty or with test generations)

# 3. Generate via production endpoint
curl -X POST https://YOUR-COOLIFY-DOMAIN/api/generate \
  -F "image=@test-photo.jpg" \
  -F "user_id=YOUR_TEST_USER_UUID"
# Expected: JSON with result_image_url (10-60s response time)

# 4. TestFlight build status
fastlane pilot builds
# Expected: Latest build shows "Ready to Test" or "Processing"

# 5. Check all 15 models are warm
psql $NEON_DATABASE_URL -c \
  "SELECT u.email, lm.training_status, lm.replicate_model_id
   FROM users u
   JOIN lora_models lm ON lm.user_id = u.id
   WHERE lm.training_status = 'ready'"
# Expected: 15 rows, all with status 'ready'
```

**Expected Result**: The web app loads on the Coolify domain. The iOS app installs from TestFlight. A pre-trained tester can sign in, take a photo, receive a LoRA-enhanced result, and view it in the gallery — on both web and native iOS.

---

## Rollback Plan

If the deployment introduces critical issues:

| Issue | Rollback |
|-------|----------|
| Web build broken on Coolify | Redeploy previous working commit via Coolify's rollback UI |
| iOS crash on launch | TestFlight builds are immutable; push a fix and submit a new build (Fastlane makes this < 15 minutes) |
| Flask API unreachable | Check Coolify container logs (`docker logs`); restart the backend service |
| Replicate calls failing in production | Verify `REPLICATE_API_TOKEN` env var is set in Coolify; test with `curl` from the server |
| Auth not working on production domain | Ensure Supabase redirect URLs include the Coolify domain; update in Supabase dashboard |

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 as done — this completes the epic
2. Monitor the 15 testers for the first 48 hours — watch for failed generations, auth issues, or camera permission denials via direct Neon queries:
   ```sql
   -- Failed generations in last 24h
   SELECT u.email, g.error_message, g.created_at
   FROM generations g JOIN users u ON u.id = g.user_id
   WHERE g.status = 'failed' AND g.created_at > NOW() - INTERVAL '24 hours';

   -- Active users (generated at least once)
   SELECT COUNT(DISTINCT user_id) FROM generations
   WHERE status = 'completed' AND created_at > NOW() - INTERVAL '7 days';
   ```
3. Fix critical bugs reported by testers — this is the "watch, collect feedback, fix" gate per the [Epic](./epic.md)
4. Begin tracking the retention metric: 40%+ of 15 users returning within 4 weeks validates the feature

---

## Related Documents

- [Solution Architecture](./architecture.md) – Deployment targets, Docker Compose pattern, risk mitigations for cold starts and URL expiry
- [Epic](./epic.md) – Task scope and success criteria (15 users on TestFlight, web + iOS live)
- [Task 2: Pre-train 15 LoRA models](./task-2-pre-train-15-lora-models.md) – Model validation checklist, user-to-model mapping
- [Task 3: Photo capture and generation pipeline](./task-3-photo-capture-and-generation-pipeline.md) – End-to-end flow that this deployment ships
- [Timeline](./timeline.md) – Status tracking