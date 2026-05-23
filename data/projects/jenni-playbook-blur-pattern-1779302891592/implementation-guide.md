# Implementation Guide: Jenni Playbook Blur Pattern

## Overview
This epic builds a suspension-based conversion funnel for Specview modeled on Jenni AI's blur pattern. An anonymous visitor pastes a brain dump and receives a fully rendered analysis document for free, then sees four additional spec documents (epic, architecture, timeline, implementation guide) with visible section headers but blurred content. The funnel converts that psychological tension into paid access via Stripe Checkout. Tasks sequence as follows: Task 1 (anonymous analysis) and Task 3 (analytics) have no dependencies and run in parallel; Task 2 (blur wall) depends on Task 1; Task 4 (auth and payments) depends on Tasks 2 and 3; Task 5 (pro unlock) depends on Task 4. The target is a measurable 3% anonymous-analyze-to-signup conversion rate before Show HN.

## Shared Pre-flight
- Confirm the existing Flask backend runs on port 3101 and the Angular frontend runs on port 4201 with no breaking state.
- Verify the existing generation pipeline in `modules/ai/workflows/spec_gen/` can produce an analysis document in isolation (without requiring the other four document types).
- Ensure the existing `modules/auth` JWT system issues and validates tokens correctly, as Tasks 4 and 5 depend on it.
- Install the Stripe Python SDK and configure `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, and `STRIPE_WEBHOOK_SECRET` as environment variables.
- Add new route blueprints for `modules/anon/`, `modules/payments/`, and `modules/analytics/` to the Flask application factory.
- Define all new endpoints in `openapi.yaml` before writing any route handler, per the OpenAPI-first principle.
- Create the `data/analytics/` directory for flat-file event storage.
- Confirm that no file created or modified in this epic exceeds 200 lines, per the project's file-size principle.

---

## Task 1: Anonymous Analysis Hook  [Effort: 3 days]

### What
This task enables unauthenticated visitors to submit a brain dump and receive a fully rendered analysis document without signing up. It is the free-tier hook that proves time-to-value in under sixty seconds and feeds the top of the conversion funnel.

### Files
- **Create**: `modules/anon/__init__.py` — Package init for the anonymous module.
- **Create**: `modules/anon/routes.py` — Flask route for anonymous analysis submission; accepts brain dump payload and anonymous session ID header, returns 202 with a job ID.
- **Create**: `modules/anon/service.py` — Business logic for creating an anonymous project record (marked `anonymous: true` with session ID), invoking only the analysis step of the generation pipeline, and handling session-to-user claiming on future signup.
- **Modify**: `modules/ai/workflows/spec_gen/` (relevant entry point) — Expose a function that runs only the analysis step of the pipeline without requiring authentication context or generating the other four documents.
- **Modify**: `openapi.yaml` — Add the `POST /api/anon/analyze` endpoint schema (request body: brain dump text; header: anonymous session ID; response: 202 with job ID) and the `GET /api/anon/analyze/{job_id}` polling endpoint schema.
- **Create**: `web-ng/src/app/anon-analyze/anon-analyze.component.ts` — Standalone Angular component with a text area for brain dump submission, a submit button, and a polling-based progress indicator that renders the completed analysis using the existing newspaper design system.
- **Create**: `web-ng/src/app/anon-analyze/anon-analyze.component.html` — Template for the anonymous analysis submission and result view.
- **Create**: `web-ng/src/app/anon-analyze/anon-analyze.component.scss` — Styles matching the existing newspaper design system.
- **Modify**: `web-ng/src/app/services/ai.service.ts` — Add methods for posting an anonymous analysis request and polling for its result.
- **Modify**: `web-ng/src/app/app.routes.ts` — Add route for the anonymous analysis page as the primary landing experience.

### Steps
1. Define the anonymous analysis endpoints in `openapi.yaml`: a POST endpoint at `/api/anon/analyze` that accepts a JSON body with a `braindump` text field and an `X-Anonymous-Session-ID` header, returning 202 with a `job_id`; and a GET endpoint at `/api/anon/analyze/{job_id}` that returns the analysis status and content when complete.
2. Create `modules/anon/service.py` with a function `start_anonymous_analysis` that creates a project record marked as anonymous, attaches the session ID, and calls only the analysis step of the existing generation pipeline using the background-thread pattern already established in `spec_gen`. Add a function `get_analysis_status` that checks the in-process state dict for job completion and returns the analysis content when ready. Add a function `claim_anonymous_projects` that transfers all projects associated with a given session ID to a newly created user account.
3. Modify the generation pipeline entry point in `modules/ai/workflows/spec_gen/` to expose a callable that runs the analysis chain only, skipping epic, architecture, timeline, and implementation guide steps. This function accepts a brain dump string and a project ID, calls the existing chain adapter for the analysis prompt, and stores the result in the project record.
4. Create `modules/anon/routes.py` with two route handlers: one for POST that validates the brain dump is non-empty, extracts the session ID from the request header, calls `start_anonymous_analysis`, and returns 202 with the job ID; and one for GET that calls `get_analysis_status` and returns either a 200 with the analysis content or a 202 indicating generation is still in progress.
5. Register the anonymous blueprint in the Flask application factory so the routes are active.
6. Implement the Angular `anon-analyze` component with a text area bound to a braindump model property, a submit handler that calls the new `submitAnonymousAnalysis` method on `ai.service.ts`, and a polling loop that checks the job status every two seconds until the analysis is ready. On completion, render the analysis document using the existing document rendering approach from the newspaper design system.
7. Add a `generateAnonymousSessionId` function to `conversion.service.ts` (created in Task 3 but can be stubbed here) that checks `localStorage` for an existing session ID, generates a UUID if none exists, and returns it. The `anon-analyze` component calls this on initialization and passes the ID with every API request.
8. Wire the anonymous analysis route in `app.routes.ts` so that the root path or a dedicated `/analyze` path loads the `anon-analyze` component.

### Verify
- Submit a brain dump through the UI without logging in and confirm a rendered analysis document appears within sixty seconds.
- Inspect the network tab and confirm the POST returns 202 and the polling GET eventually returns 200 with the full analysis content.
- Confirm that no other document types (epic, architecture, timeline, implementation guide) are generated during the anonymous flow by checking the project record on the server.
- Verify that the anonymous session ID is persisted in `localStorage` and sent as a header on all requests.

---

## Task 2: Blur-Wall Spec Preview  [Effort: 3 days]

### What
This task renders the four locked document types (epic, architecture, timeline, implementation guide) below the free analysis with visible titles and section headers but blurred body content. The blur wall is the psychological trigger that creates conversion tension. The API returns metadata only — never actual content — so the paywall cannot be bypassed client-side.

### Files
- **Create**: `modules/anon/preview.py` — Service function that returns canonical preview metadata for each locked document type: title, section headers (H2 and H3), approximate word counts, and cross-reference mentions to other documents.
- **Modify**: `modules/anon/routes.py` — Add a GET endpoint for blur-wall preview metadata keyed by project ID.
- **Modify**: `openapi.yaml` — Add the `GET /api/anon/preview/{project_id}` endpoint schema with the preview metadata response structure.
- **Create**: `web-ng/src/app/blur-preview/blur-preview.component.ts` — Standalone Angular component that receives preview metadata and renders document skeletons with blurred placeholder content and per-document upgrade CTAs.
- **Create**: `web-ng/src/app/blur-preview/blur-preview.component.html` — Template rendering document title, section headers in normal text, blurred placeholder paragraphs sized by word count, and an overlay CTA button per document.
- **Create**: `web-ng/src/app/blur-preview/blur-preview.component.scss` — Styles using CSS `filter: blur()` on placeholder blocks, matching the existing newspaper typography and layout.
- **Modify**: `web-ng/src/app/anon-analyze/anon-analyze.component.ts` — After analysis rendering is complete, fetch preview metadata and render the four blur-preview components below the analysis.
- **Modify**: `web-ng/src/app/anon-analyze/anon-analyze.component.html` — Add a section below the analysis that iterates over the four locked document types and renders a `blur-preview` component for each.
- **Modify**: `web-ng/src/app/services/projects.service.ts` — Add a method to fetch preview metadata from the new endpoint.

### Steps
1. Define the preview endpoint in `openapi.yaml`: a GET at `/api/anon/preview/{project_id}` that returns an array of four document preview objects, each containing `doc_type`, `title`, `sections` (array of objects with `heading`, `level`, and `word_count`), and `cross_references` (array of strings naming other document types this document references).
2. Create `modules/anon/preview.py` with a function `get_preview_metadata` that returns hardcoded canonical section headers for each of the four document types. These headers come from the structured prompts that define each document type's output format in the generation pipeline. Include realistic word counts (ranging from 80 to 250 per section) and cross-references derived from the prompt templates (for example, the epic references the architecture and timeline; the architecture references the analysis and epic).
3. Add a route handler in `modules/anon/routes.py` that accepts a project ID, verifies the project exists and has a completed analysis, calls `get_preview_metadata`, and returns the metadata array.
4. Build the `blur-preview` component in Angular. The component accepts a single document preview object as an input property. It renders the document title as an H2, each section header at its appropriate heading level, and a placeholder paragraph block below each header. The placeholder block is a div containing meaningless generated text (lorem-style or repeated neutral phrases) sized to approximately match the reported word count, with CSS `filter: blur(8px)` applied. The text must not be the real document content — even with blur removed, the visitor sees only placeholder text.
5. Add a per-document upgrade CTA as an absolutely positioned overlay centered on each blur-preview component. The CTA text should reference the document type (for example, "Unlock the full Epic" or "Read the complete Architecture"). The CTA click emits an event that the parent component handles for navigation to the signup and payment flow.
6. Render cross-references within the analysis document by scanning the analysis content for mentions of the locked document types and styling those mentions as visible links that scroll to the corresponding blur-preview section below. This makes the interconnection between documents tangible.
7. In the `anon-analyze` component, after the analysis finishes rendering, call the preview metadata endpoint via `projects.service.ts` and pass each of the four document preview objects to a `blur-preview` instance rendered in a grid or stacked layout below the analysis.
8. Ensure the blur presentation degrades safely: if CSS blur is unsupported or stripped by a browser extension, the visible text is meaningless placeholder content, not actual spec content.

### Verify
- Complete an anonymous analysis and confirm four blurred document previews appear below it with visible titles and section headers.
- Inspect the network response from the preview endpoint and confirm it contains only metadata (titles, headers, word counts, cross-references) and no actual document content.
- Disable CSS in the browser developer tools and confirm the placeholder text beneath the blur is meaningless generated text, not real spec content.
- Confirm each blurred document has a visible upgrade CTA button that is clickable.

---

## Task 3: Conversion Analytics Pipeline  [Effort: 2 days]

### What
This task builds a lightweight, in-house event-tracking system that measures the full anonymous-analyze-to-signup funnel. It stores events as append-only JSON lines in flat files and exposes a stats endpoint that answers the 3% conversion gate question. This must exist before Show HN so conversion can be diagnosed and improved.

### Files
- **Create**: `modules/analytics/__init__.py` — Package init for the analytics module.
- **Create**: `modules/analytics/routes.py` — Flask routes for event ingestion and funnel stats retrieval.
- **Create**: `modules/analytics/service.py` — Business logic for appending events to daily JSON-lines files and aggregating funnel metrics across date ranges.
- **Modify**: `openapi.yaml` — Add the `POST /api/analytics/event` and `GET /api/analytics/funnel` endpoint schemas.
- **Create**: `web-ng/src/app/services/conversion.service.ts` — Angular service that manages the anonymous session ID in `localStorage`, generates it on first visit, and exposes a method to emit named funnel events to the analytics endpoint.
- **Modify**: `web-ng/src/app/anon-analyze/anon-analyze.component.ts` — Inject `conversion.service.ts` and emit `page_land`, `braindump_paste`, `analysis_start`, and `analysis_view` events at appropriate lifecycle points.
- **Modify**: `web-ng/src/app/blur-preview/blur-preview.component.ts` — Emit `blur_scroll` when the blur wall enters the viewport and `blur_cta_click` when the upgrade CTA is clicked.

### Steps
1. Define the analytics endpoints in `openapi.yaml`: a POST at `/api/analytics/event` that accepts a JSON body with `event_name`, `session_id`, and `timestamp`; and a GET at `/api/analytics/funnel` that accepts optional query parameters for `start_date` and `end_date` and returns step counts, drop-off rates, and overall conversion rate.
2. Create `modules/analytics/service.py` with a function `record_event` that appends a JSON object (event name, session ID, ISO timestamp) as a single line to a daily file at `data/analytics/YYYY-MM-DD.jsonl`. Create a function `compute_funnel` that reads all JSON-lines files in the specified date range, groups events by session ID, determines the furthest funnel step each session reached, and returns counts per step and the conversion rate from `analysis_view` to `signup_complete`. The funnel steps in order are: `page_land`, `braindump_paste`, `analysis_start`, `analysis_view`, `blur_scroll`, `blur_cta_click`, `signup_start`, `signup_complete`, `payment_start`, `payment_complete`.
3. Create `modules/analytics/routes.py` with a POST handler that validates the event name is in the allowed set, calls `record_event`, and returns 204. Add a GET handler for the funnel stats that calls `compute_funnel` and returns the aggregated result as JSON.
4. Register the analytics blueprint in the Flask application factory.
5. Build `conversion.service.ts` in the Angular frontend. On construction, check `localStorage` for an existing `anon_session_id`; if absent, generate a UUID v4 and store it. Expose a method `trackEvent(eventName: string)` that POSTs the event name, session ID, and current ISO timestamp to the analytics endpoint. Expose a getter for the session ID so other services can attach it as a request header.
6. Integrate event emission into the `anon-analyze` component: emit `page_land` on component initialization, `braindump_paste` when the text area first receives input, `analysis_start` when the submit button is clicked, and `analysis_view` when the analysis document finishes rendering.
7. Integrate event emission into the `blur-preview` component: use an Intersection Observer to emit `blur_scroll` once when any blur-preview component enters the viewport, and emit `blur_cta_click` when the upgrade CTA is clicked.

### Verify
- Complete an anonymous analysis flow and confirm that events appear in the daily JSON-lines file at `data/analytics/` with correct event names and session IDs.
- Call the `GET /api/analytics/funnel` endpoint and confirm it returns step counts that match the events you just generated.
- Verify that the session ID persists across page reloads by checking `localStorage` and confirming subsequent events use the same ID.
- Confirm that submitting an event with an invalid event name returns an error, not a 204.

---

## Task 4: Auth + Stripe Payment Gate  [Effort: 3 days]

### What
This task wires up the signup flow and Stripe Checkout integration so that a visitor who clicks an upgrade CTA on the blur wall can create an account and pay in a minimal-friction sequence. Signup happens only after the visitor has seen the blur wall and decided to convert, not before. On signup, anonymous projects and analytics events are stitched to the new user account.

### Files
- **Create**: `modules/payments/__init__.py` — Package init for the payments module.
- **Create**: `modules/payments/adapter.py` — The sole file that imports the Stripe SDK. Exposes two functions: `create_checkout_session` (creates a Stripe Checkout session with a price ID and success/cancel URLs) and `verify_webhook` (validates a Stripe webhook signature and returns the parsed event).
- **Create**: `modules/payments/routes.py` — Flask routes for initiating checkout and receiving the Stripe webhook.
- **Create**: `modules/payments/service.py` — Business logic for creating a checkout session tied to a user, handling the webhook fulfillment (upgrading user tier to pro, triggering generation of the remaining four documents).
- **Modify**: `modules/auth/routes.py` — Add or extend the signup endpoint to accept an `anonymous_session_id` field, and after account creation call `claim_anonymous_projects` from `modules/anon/service.py` to transfer anonymous projects to the new user.
- **Modify**: `modules/auth/service.py` — Extend user creation to accept and process the anonymous session ID for project claiming and analytics stitching.
- **Modify**: `openapi.yaml` — Add the `POST /api/payments/checkout` endpoint, the `POST /api/payments/webhook` endpoint, and the updated signup endpoint schema that includes the anonymous session ID.
- **Create**: `web-ng/src/app/signup/signup.component.ts` — Standalone Angular component for email and password signup that captures the anonymous session ID from `localStorage` and sends it with the signup request.
- **Create**: `web-ng/src/app/signup/signup.component.html` — Signup form template.
- **Create**: `web-ng/src/app/signup/signup.component.scss` — Signup form styles.
- **Modify**: `web-ng/src/app/services/auth.service.ts` — Add a signup method that sends credentials plus the anonymous session ID and stores the returned JWT.
- **Create**: `web-ng/src/app/services/payments.service.ts` — Angular service with a method to initiate checkout by calling the backend, then redirecting to the Stripe Checkout URL.
- **Modify**: `web-ng/src/app/app.routes.ts` — Add routes for the signup page and a payment success/cancel landing page.
- **Modify**: `web-ng/src/app/blur-preview/blur-preview.component.ts` — Wire the CTA click to navigate to the signup page (if unauthenticated) or initiate checkout (if authenticated but unpaid).

### Steps
1. Define the payment and updated auth endpoints in `openapi.yaml`: a POST at `/api/payments/checkout` that accepts a user JWT and a project ID and returns a Stripe Checkout session URL; a POST at `/api/payments/webhook` that Stripe calls with fulfillment events; and the updated signup endpoint that accepts `email`, `password`, and `anonymous_session_id`.
2. Create `modules/payments/adapter.py` with the `create_checkout_session` function that calls `stripe.checkout.Session.create` with the configured price ID, success URL (pointing back to the project page with a success flag), and cancel URL (pointing back to the project page). Add the `verify_webhook` function that calls `stripe.Webhook.construct_event` with the request body, signature header, and webhook secret.
3. Create `modules/payments/service.py` with a function `initiate_checkout` that takes a user ID and project ID, calls the adapter to create a checkout session, and returns the session URL. Add a function `handle_payment_complete` that receives a verified Stripe event, extracts the user ID from the session metadata, updates the user record to set `tier: "pro"`, and triggers generation of the four remaining documents for the user's projects.
4. Create `modules/payments/routes.py` with a POST handler for checkout initiation that requires a valid JWT, extracts the user ID, calls `initiate_checkout`, and returns the Stripe Checkout URL. Add a POST handler for the webhook that reads the raw request body, calls `verify_webhook` from the adapter, and on a `checkout.session.completed` event calls `handle_payment_complete`.
5. Modify `modules/auth/service.py` to accept an optional `anonymous_session_id` during user creation. After the user record is created, call `claim_anonymous_projects` from `modules/anon/service.py` to associate all projects with that session ID to the new user. Also emit a `signup_complete` analytics event with the session ID.
6. Update `modules/auth/routes.py` so the signup endpoint passes the anonymous session ID from the request body through to the service layer.
7. Register the payments blueprint in the Flask application factory.
8. Build the Angular `signup` component with an email and password form. On submission, call `auth.service.ts` signup method which sends credentials plus the anonymous session ID from `localStorage`. On success, store the JWT and emit `signup_complete` via `conversion.service.ts`, then redirect to the payment checkout flow.
9. Create `payments.service.ts` with a method `startCheckout` that calls the backend checkout endpoint with the JWT and project ID, receives the Stripe Checkout URL, and redirects the browser to it using `window.location.href`.
10. Wire the blur-preview CTA click: if the user is not authenticated, navigate to the signup page; if authenticated but not on the pro tier, call `startCheckout`; if already pro, this state should not occur but navigate to the full document view as a fallback.
11. Add a success landing route that the user returns to after Stripe Checkout completes, which shows a progress screen while the four remaining documents generate.

### Verify
- Click an upgrade CTA on the blur wall and confirm navigation to the signup page with the anonymous session ID preserved.
- Complete signup and confirm the anonymous project is now associated with the new user account by checking the backend project record.
- Confirm that Stripe Checkout opens after signup and that a test payment completes successfully using Stripe test card numbers.
- Send a test webhook event to the webhook endpoint and confirm the user record is updated to `tier: pro`.

---

## Task 5: Pro Unlock and Full Suite Delivery  [Effort: 2 days]

### What
This task delivers the remaining four documents (epic, architecture, timeline, implementation guide) after payment completes. Generation is triggered by the Stripe webhook handler and uses the analysis document as input context. The blur wall is replaced with the fully rendered spec suite once generation finishes.

### Files
- **Modify**: `modules/payments/service.py` — In `handle_payment_complete`, call the existing generation pipeline for the four remaining document types, passing the completed analysis as input context, using the background-thread pattern.
- **Modify**: `modules/ai/workflows/spec_gen/` (relevant entry point) — Expose a function that generates the four remaining documents (epic, architecture, timeline, implementation guide) given a project ID with an already-completed analysis, without re-running the analysis step.
- **Create**: `modules/payments/generation.py` — Orchestration logic that takes a project ID, reads the completed analysis from the project record, and invokes each of the four remaining document generation steps sequentially, storing each result in the project record as it completes.
- **Modify**: `web-ng/src/app/anon-analyze/anon-analyze.component.ts` — After payment success redirect, poll for the four remaining documents and progressively render them as they complete, replacing the blur-preview components with fully rendered documents.
- **Modify**: `web-ng/src/app/blur-preview/blur-preview.component.ts` — Add an input property or conditional that switches from blurred preview mode to a fully rendered document view when the document content becomes available.
- **Modify**: `web-ng/src/app/services/projects.service.ts` — Add a method to poll for document generation status and retrieve completed documents for a given project.
- **Modify**: `web-ng/src/app/services/conversion.service.ts` — Emit `payment_start` when checkout is initiated and `payment_complete` when the user returns from Stripe with a success flag.

### Steps
1. Modify the generation pipeline entry point in `modules/ai/workflows/spec_gen/` to expose a function `generate_remaining_documents` that accepts a project ID, reads the existing analysis from the project record, and runs the four remaining document generation steps in sequence (epic, then architecture using the analysis and epic as context, then timeline, then implementation guide). Each step uses the existing chain adapter and stores its result in the project record as it completes.
2. Create `modules/payments/generation.py` with a function `trigger_post_payment_generation` that is called by `handle_payment_complete`. This function spawns a background thread that calls `generate_remaining_documents` for each project associated with the upgraded user. The function updates a generation status field on the project record so the frontend can poll progress.
3. Update `handle_payment_complete` in `modules/payments/service.py` to call `trigger_post_payment_generation` after setting the user tier to pro.
4. Add a generation status endpoint (or extend the existing project endpoint) that returns which documents are complete and which are still generating for a given project. Define this in `openapi.yaml`.
5. Update the frontend success landing page to use the 202-polling pattern: on arrival after Stripe redirect, begin polling the generation status endpoint every three seconds. As each document completes, replace the corresponding blur-preview component with the fully rendered document content. Show a progress indicator for documents still generating.
6. Emit `payment_complete` via `conversion.service.ts` when the success landing page loads, completing the analytics funnel for this session.
7. Handle the edge case where the user navigates away during generation and returns later: on page load, check the project's document status and render whatever is complete, continuing to poll for any documents still in progress.
8. Once all four documents are rendered, remove all blur-wall UI elements and CTA overlays from the page, presenting the clean five-document spec suite.

### Verify
- Complete a test payment and confirm all four remaining documents are generated and rendered within two minutes of payment completion.
- Verify the generation status endpoint correctly reports progress as each document completes sequentially.
- Refresh the page mid-generation and confirm that already-completed documents render immediately while still-generating documents continue to show progress indicators.
- Confirm the `payment_complete` event appears in the analytics JSON-lines file and that the full funnel from `page_land` to `payment_complete` is visible in the funnel stats endpoint for this session.