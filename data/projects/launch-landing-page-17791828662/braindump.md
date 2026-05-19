# Landing Page with CTA Funnel

## What this is

The landing page IS the braindump modal. No hero section with marketing copy, no scroll, no "learn more." The visitor lands and immediately sees the braindump editor — the exact same modal the app uses — pre-filled with a rotating demo braindump. One click: "Analyze this." That click redirects to the app AND fires the analysis call simultaneously. By the time the app loads, the analysis is ready or nearly ready. Zero friction. The product demos itself.

## The core idea

The landing page hero is the braindump modal content. Nothing else. The visitor sees:

1. A braindump textarea pre-filled with a demo braindump (rotating — multiple examples cycle through with text replacement animation)
2. One button: "Analyze" (or similar CTA)
3. That's it. That's the landing page.

When the visitor clicks "Analyze":
- The page redirects to the specview app
- Simultaneously, an API call fires to start the analysis
- The app loads with the analysis already in progress or completed
- If the visitor didn't edit the demo braindump, the response is **mocked** — pre-computed, instant, no API cost

If the visitor edits the braindump before clicking, it's a real analysis. If they leave the demo text, it's a cached/mocked response. Either way: one click to value.

## Mock braindumps — rotating demo content

Multiple example braindumps that cycle through the textarea with a typewriter or fade effect:

- A mobile app idea (messy, unstructured, real-feeling)
- A SaaS feature braindump
- A side project plan
- A refactoring task

Each one shows the kind of chaos developers actually start with. The text replacement is dynamic — visitors see different examples as they watch. This IS the demo. No video, no screenshot, no "see it in action" link. The braindump modal on the landing page IS the action.

## Two paths, same UX

### Path A: Visitor doesn't edit (demo mode)
- Clicks "Analyze" on the pre-filled demo braindump
- Redirects to app with a query param like `?demo=true&braindump_id=xyz`
- App loads and immediately shows the pre-computed analysis result (mocked API response)
- Analysis, epic, architecture — all pre-generated, cached, instant
- Visitor sees the full output and hits the conversion gate: "Sign up to create your own"

### Path B: Visitor edits the braindump (real mode)
- Modifies the text, types their own idea
- Clicks "Analyze"
- Redirects to app with the braindump content passed (URL param, sessionStorage, or POST)
- API call fires: real analysis begins
- App shows loading/streaming state, then the real result
- Conversion gate: "Sign up to save this and generate more"

Both paths: one click from landing to result.

## Why this works

- **No separate demo artifact needed** — the landing page IS the demo
- **No video, no GIF, no 5MB asset** — the rotating braindumps are live text, zero load penalty
- **The product sells itself** — visitors interact with the actual product surface, not a marketing page about the product
- **Mocked responses eliminate cost** — demo braindumps have pre-computed results, no API calls burned on lookers
- **Sub-second to value** — landing page loads fast (static HTML + minimal JS for text rotation), one click, app loads with result ready

## Technical approach

### Landing page
- Still lives in `landing/` directory, still nginx:alpine
- Minimal JS: text rotation for demo braindumps, CTA button handler
- The braindump textarea uses the same newspaper design tokens as the app modal
- On click: stores braindump content + a flag (demo vs custom) in sessionStorage, then redirects to app

### Pre-computed mock responses
- For each demo braindump, pre-generate the full spec output (analysis, epic, architecture)
- Store as static JSON files in the app or landing assets
- When app detects `?demo=true`, load the mocked response instead of calling the API
- This can be a simple lookup: `demo_braindump_id -> cached_response.json`

### API call on CTA click
- For custom braindumps (visitor edited the text): fire the analysis API call from the landing page before redirect
- Pass a job ID or token so the app can poll/retrieve the result
- The app shows a loading state that resolves to the real output
- Alternative: just pass the braindump text to the app and let it fire the API call on load (simpler, slightly slower)

### App integration
- App reads query params or sessionStorage on load
- Demo mode: render pre-computed result immediately
- Real mode: fire API call (or pick up in-flight one), show streaming/loading, then result
- Both paths end at the same conversion gate

## What exists in the codebase

- `landing/` directory with nginx:alpine Dockerfile — already deployed
- `web-ng/src/styles.css` — newspaper design tokens
- `web-ng/src/app/services/auth.service.ts` — existing auth
- `web-ng/src/app/services/token-lifecycle.service.ts` — token management
- `web-ng/src/app/services/projects.service.ts` — project storage
- Braindump modal component in the app — reuse its design/layout for the landing page
- Docker Compose + Coolify deployment pipeline — already running

## Dependencies

- Depends on Task 1 (BYOK decision) — privacy stance determines landing page copy
- Replaces Task 4 (demo artifact) — the landing page IS the demo now, no separate video/GIF needed
- Blocks Task 5 (relaunch) — the landing page URL is the only link in the relaunch post

## Success criteria

- Landing page loads in under 1 second on mobile
- Visitor sees braindump modal immediately (no scroll needed)
- Demo braindumps rotate with visible text animation
- One click from landing page to seeing a complete spec result in the app
- Demo mode: result appears instantly (mocked)
- Real mode: result appears within normal analysis time

## Review findings applied

- **Anonymous-first is exactly right** — strategic review confirmed this is the #1 pattern for dev tools. This takes it further: the visitor doesn't even need to understand what the tool does. They see a braindump, they click analyze, they see the result. The product explains itself.
- **No separate demo artifact needed** — Task 4 (demo video/GIF) is replaced by this approach. The landing page IS the live demo.
- **Mocked responses address the cost concern** — architecture flagged "hosted trial has cost exposure." Pre-computed responses for demo braindumps = zero cost for non-editing visitors.
