# Implementation Guide: Launch: Landing Page with CTA Funnel

## Overview
This epic converts the empty nginx landing page into a live braindump editor that serves as the product's primary conversion funnel. A visitor arrives, sees a textarea pre-filled with rotating demo content, clicks a single "Analyze" CTA, and lands in the Angular app viewing a complete spec result — either instantly from pre-computed JSON (demo mode) or via the existing async bootstrap API (real mode). Tasks 1 and 2 are independent foundation work (design tokens and the data transfer contract), after which Tasks 3 and 4 execute in parallel: the static landing page UI and the Angular app integration that receives the handoff.

## Shared Pre-flight
- Confirm the `landing/` directory exists and is served by the nginx:alpine container in the current Docker Compose topology
- Confirm `web-ng/src/styles.css` contains the newspaper design tokens as CSS custom properties on `:root`
- Verify the Angular route table lives in `web-ng/src/app/app.routes.ts` and confirm the flat route structure
- Verify the existing async bootstrap endpoint `POST /api/ai/text/bootstrap-project` returns a 202 with a job ID and supports status polling at `GET /api/ai/text/bootstrap-project/status/{job_id}`
- Confirm the `BootstrapProjectResponse` DTO shape: an object with a `files` array where each entry has `filename` and `content` fields
- Ensure four demo braindump JSON files are available (or stub placeholders matching the `BootstrapProjectResponse` shape) for integration testing
- Identify whether the landing page and app share an origin or run on separate subdomains in the current deployment topology
- Confirm the `modules/usage/` directory contains the metering infrastructure that will support IP-keyed rate limiting for anonymous access

---

## Task 1: Design Token Extraction  [Effort: 0.5 days]

### What
Extract the newspaper design tokens (colors, fonts, spacing, border radii, typographic scale) from the Angular app's global stylesheet into a standalone CSS file that the static landing page can consume directly. This ensures the landing page textarea is visually indistinguishable from the app's braindump input without coupling the landing page to Angular's build pipeline.

### Files
- **Create**: `landing/tokens.css` — standalone CSS file containing `:root` custom property declarations and base typographic rules extracted from the app
- **Modify**: `landing/index.html` — add a stylesheet link to `tokens.css` in the document head

### Steps
1. Open `web-ng/src/styles.css` and identify all CSS custom properties declared on `:root` that define the newspaper design system — expect roughly 40 properties covering ink colors, paper backgrounds, font families, font size scale, line heights, letter spacing, border radii, and spacing units.
2. Copy those `:root` declarations into a new file at `landing/tokens.css`. Include only the custom property definitions and the base typographic rules (body font-size, line-height, font-family) that establish the newspaper aesthetic. Do not copy component-scoped styles or Angular-specific selectors.
3. Add a stylesheet link referencing `tokens.css` in the head of `landing/index.html`, before any page-specific styles.
4. Apply the extracted token custom properties to a test textarea element in `landing/index.html` and visually compare it side-by-side with the app's braindump modal to confirm typographic rhythm, ink color, border treatment, and font stack match.
5. Strip any properties from `landing/tokens.css` that are unused by the landing page surface to keep the file minimal and intentional.

### Verify
- `landing/tokens.css` exists, contains only CSS custom property declarations and base typographic rules, and has no Angular-specific selectors or component styles
- A textarea styled with the extracted tokens in `landing/index.html` is visually indistinguishable from the app's braindump input when compared in a side-by-side browser screenshot
- The landing page loads in the nginx container without 404s on the token stylesheet
- `landing/tokens.css` contains fewer than 50 custom property declarations, confirming no scope creep from app-specific styles

---

## Task 2: Landing-to-App Data Transfer Contract  [Effort: 1 day]

### What
Define and implement the mechanism for passing braindump content and mode flag across the redirect from the landing page to the Angular app. This contract must work regardless of whether the two surfaces share an origin, ruling out sessionStorage and requiring a URL-based approach: a query parameter for demo mode and a URL fragment for real mode.

### Files
- **Create**: `landing/redirect.js` — JavaScript module exporting a function that constructs the correct redirect URL based on mode (demo slug as query parameter, or base64url-encoded braindump content as URL fragment)
- **Modify**: `web-ng/src/app/app.routes.ts` — register two new route entries: one matching the demo query parameter and one matching the analyze path with fragment data
- **Create**: `web-ng/src/app/landing-handoff.service.ts` — Angular service that reads the demo query parameter or decodes the URL fragment on app initialization, exposing the mode and braindump content to consuming components

### Steps
1. Define the demo-mode URL shape: the app origin followed by a query parameter `demo` whose value is a short slug string identifying the demo braindump (for example, `mobile-app`, `saas-feature`, `side-project`, `refactoring-task`). Document the slug list as a constant array in `landing/redirect.js`.
2. Define the real-mode URL shape: the app origin followed by the path `/analyze` with the braindump content encoded as a base64url string in the URL fragment (hash portion). Choose base64url over standard base64 to avoid URL-unsafe characters.
3. Implement the redirect URL builder in `landing/redirect.js`. The function accepts two arguments: a boolean indicating whether the visitor edited the textarea, and the current content (either a demo slug or the raw braindump text). It returns the fully qualified redirect URL.
4. Implement UTF-8-safe base64url encoding in `landing/redirect.js` using the TextEncoder API to convert the braindump string to bytes before encoding, ensuring all Unicode content survives the round-trip.
5. Create `web-ng/src/app/landing-handoff.service.ts` as an injectable Angular service. On construction, it reads `window.location.search` for the `demo` parameter and `window.location.hash` for the encoded braindump. It exposes a typed result: either demo mode with a slug, real mode with decoded braindump text, or no handoff.
6. Implement the corresponding base64url decoding in the handoff service using TextDecoder to reconstruct the original UTF-8 string from the decoded bytes.
7. Register two new routes in `web-ng/src/app/app.routes.ts`: one that activates when the `demo` query parameter is present, and one at the `/analyze` path for real-mode handoff. Both routes will be wired to their respective components in Task 4.

### Verify
- Manually construct a demo redirect URL with a known slug and confirm the Angular app's handoff service correctly reads the slug from the query parameter
- Manually construct a real-mode redirect URL with a base64url-encoded braindump containing Unicode characters (emoji, accented characters, CJK text) and confirm the handoff service decodes it without data loss
- Confirm that the redirect URLs work when landing and app are on different origins (different ports in local Docker Compose) — no sessionStorage dependency, no CORS requirement
- Run `ng build --configuration production` to verify the new routes and service compile without errors

---

## Task 3: Landing Page Braindump UI  [Effort: 2 days]

### What
Build the static HTML landing page with the braindump textarea as the sole above-the-fold element, a typewriter-style demo text rotation animating through four example braindumps, and a CTA button wired to the redirect contract from Task 2. This is the visitor's first and only interaction surface before entering the app.

### Files
- **Modify**: `landing/index.html` — replace the existing empty shell content with the braindump textarea, CTA button, and page structure styled with the extracted design tokens
- **Create**: `landing/demo-content.js` — JavaScript file containing the four demo braindump text strings and their corresponding slugs as a structured array
- **Create**: `landing/rotation.js` — JavaScript file implementing the typewriter animation loop, textarea focus/pause behavior, and the edited-state boolean tracking
- **Modify**: `landing/redirect.js` — wire the CTA button click handler to call the redirect builder with the current mode and content

### Steps
1. Replace the body content of `landing/index.html` with a centered layout containing a single textarea element and a single button element. The textarea occupies the full above-the-fold viewport height minus button space. Style both elements using the custom properties from `landing/tokens.css` to match the app's newspaper aesthetic.
2. Create `landing/demo-content.js` with an array of four objects, each containing a `slug` field (matching the slugs defined in the Task 2 contract) and a `text` field with the full demo braindump content. The four categories are: mobile app idea, SaaS feature, side project plan, and refactoring task.
3. Implement the typewriter animation in `landing/rotation.js`. The animation types characters sequentially into the textarea's value property at a natural reading pace. When one demo completes, hold for a few seconds, then clear and begin typing the next demo. Track the current demo index so the CTA button knows which slug is active.
4. Add an `input` event listener on the textarea in `landing/rotation.js` that sets a boolean flag to true on the first visitor keystroke. Once this flag is set, immediately stop the rotation animation and leave the visitor's content in place.
5. Add a `focus` event listener on the textarea that pauses the typewriter animation without clearing the current content. The animation does not resume after focus — visitor engagement takes priority over the demo loop.
6. Wire the CTA button's click handler in `landing/redirect.js` to read the edited-state boolean. If false, call the redirect builder with demo mode and the current demo's slug. If true, call the redirect builder with real mode and the textarea's current value. Execute the redirect via `window.location.href` assignment.
7. Add a script tag in `landing/index.html` that imports `demo-content.js`, `rotation.js`, and `redirect.js`, and initializes the rotation on DOMContentLoaded.
8. Test the page on a mobile viewport (375px width) to confirm the textarea and button fill the screen without scrolling, the typewriter animation is visible, and the CTA tap target meets minimum size guidelines.

### Verify
- The landing page loads in under one second on a throttled mobile connection (check with browser DevTools network throttling on the nginx container)
- The textarea is the only element visible above the fold at 375px viewport width — no scrolling required to reach the CTA button
- All four demo braindumps cycle through the typewriter animation with visible character-by-character rendering
- Clicking the CTA without editing redirects to the app with a `demo` query parameter containing the correct slug for the currently displayed braindump

---

## Task 4: App Demo & Real Mode Integration  [Effort: 2 days]

### What
Wire the Angular app to consume the landing page handoff data on load: demo mode fetches and renders a pre-computed static JSON result instantly with no API call, while real mode decodes the braindump from the URL fragment, fires the async bootstrap API, and renders the streaming result. Both paths converge on the same result view and terminate at the conversion gate handoff point.

### Files
- **Create**: `web-ng/src/app/demo-result/demo-result.component.ts` — standalone Angular component for the demo route that fetches a static JSON file by slug and renders the spec result
- **Create**: `web-ng/src/app/analyze-result/analyze-result.component.ts` — standalone Angular component for the analyze route that decodes the fragment, calls the bootstrap API, polls for progress, and renders the streaming result
- **Create**: `web-ng/public/demo/mobile-app.json` — pre-computed demo response file matching the BootstrapProjectResponse shape (one of four; repeat for each slug)
- **Create**: `web-ng/public/demo/saas-feature.json` — pre-computed demo response for the SaaS feature braindump
- **Create**: `web-ng/public/demo/side-project.json` — pre-computed demo response for the side project braindump
- **Create**: `web-ng/public/demo/refactoring-task.json` — pre-computed demo response for the refactoring task braindump
- **Modify**: `web-ng/src/app/app.routes.ts` — point the demo and analyze route entries (registered in Task 2) to the new components
- **Modify**: `web-ng/src/app/landing-handoff.service.ts` — add convenience methods for fetching demo JSON by slug and for initiating the bootstrap API call with decoded braindump text

### Steps
1. Create the demo result component at `web-ng/src/app/demo-result/demo-result.component.ts` as a standalone Angular component. On initialization, inject the landing handoff service, read the demo slug, and use Angular's HttpClient to fetch the corresponding JSON file from `public/demo/{slug}.json`.
2. Render the fetched demo response using the same result view markup and styling that the app uses for real bootstrap results. The response shape matches `BootstrapProjectResponse` — iterate the `files` array and render each file's markdown content. No loading state is needed because the static JSON fetch is effectively instant.
3. Create the analyze result component at `web-ng/src/app/analyze-result/analyze-result.component.ts` as a standalone Angular component. On initialization, inject the landing handoff service, decode the base64url braindump from the URL fragment, and call `POST /api/ai/text/bootstrap-project` with the decoded text and a generated project name.
4. Implement the polling loop in the analyze result component. After receiving the 202 response with a job ID, poll `GET /api/ai/text/bootstrap-project/status/{job_id}` at a reasonable interval. As each partial file arrives in the status response, render it immediately in the result view so the visitor sees progressive output — analysis first, then epic, then architecture.
5. Reuse or reference the existing status bar component's loading indicators to show the visitor that analysis is in progress. Display the partial files as they arrive rather than waiting for the full chain to complete.
6. Add a conversion gate placeholder at the bottom of both the demo and analyze result views — a simple text prompt or styled block indicating "Sign up to create your own." This is a handoff point to a separate epic, not a functional auth gate.
7. Update `web-ng/src/app/app.routes.ts` to point the demo route entry to `DemoResultComponent` and the analyze route entry to `AnalyzeResultComponent`.
8. Place the four demo JSON files in `web-ng/public/demo/` with filenames matching the slugs defined in Task 2. Each file must conform to the `BootstrapProjectResponse` shape with a `files` array containing entries for `analysis.md`, `epic.md`, and `architecture.md` with realistic markdown content.
9. If the existing `@require_auth` decorator on the bootstrap endpoint blocks anonymous access, add a conditional bypass or a parallel anonymous route in the API layer that enforces IP-based rate limiting using the metering infrastructure in `modules/usage/`. This anonymous path shares the same service layer and workflow engine as the authenticated path.

### Verify
- Navigate directly to the app with a demo query parameter (e.g., `/?demo=mobile-app`) and confirm the pre-computed result renders instantly with no network calls to the bootstrap API
- Navigate to the app with an analyze fragment containing a base64url-encoded braindump and confirm the bootstrap API is called, polling begins, and partial results render progressively as each workflow step completes
- Run `ng build --configuration production` and confirm the demo JSON files are included in the build output under the expected asset path
- Confirm that both the demo and analyze result views render identically formatted spec output — same markup, same styling, same file ordering — validating that the two paths converge on a single rendering pipeline