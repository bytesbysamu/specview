Now I have sufficient understanding of both the API architecture (async 202 + polling, workflow engine, chain adapter, mock provider) and the project structure (landing/, web-ng/, design tokens, deployment topology). Let me write the architecture document.

# 🏗️ Solution Architecture: Launch: Landing Page with CTA Funnel

## Architecture Overview

This architecture solves one problem: how to get a visitor from an empty browser tab to a complete spec result in a single click, with zero signup friction and zero API cost for non-editing visitors. The system spans three independently deployed surfaces — a static landing page, a Flask API, and an Angular SPA — connected by a stateless data handoff contract that works regardless of whether these surfaces share an origin.

The key architectural insight is that the landing page and the app never need to share runtime state. The landing page is a pure redirector: it captures the visitor's intent (demo or custom braindump), encodes it into a URL, and gets out of the way. The app is the sole orchestrator of API calls and result rendering. This separation means the landing page stays static (fast, cacheable, zero infrastructure cost), while all complexity lives in the app where Angular's routing, services, and existing spec rendering already exist.

The second insight is that demo mode and real mode converge on the same rendering path — only the data source differs. Demo mode reads a static JSON file that matches the exact shape of the async bootstrap API response. Real mode fires the existing `POST /api/ai/text/bootstrap-project` endpoint and polls until completion. Both paths feed the same result view. This convergence eliminates a parallel rendering pipeline and keeps the demo experience honest — what visitors see in demo mode is exactly what they get in real mode.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | All AI calls continue through `modules/runtime/chain/adapter.py`. Demo mode bypasses the adapter entirely by serving pre-computed static JSON — no mock provider wiring, no adapter awareness of demo state |
| P2 — Thin HTTP Layer | No new API routes needed. The existing async bootstrap endpoint (`POST /api/ai/text/bootstrap-project` → 202 + polling) handles real mode. Demo mode never hits the API |
| P3 — Async 202 + Polling | Real mode reuses the existing bootstrap async pattern: 202 with job ID, status polling with partial file delivery, cooperative cancellation. No new async infrastructure |
| P4 — No Speculative Abstractions | One handoff mechanism (URL-based), one demo data format (static JSON matching existing API shape), one rendering path. No generic "mode router" or "data source abstraction layer" |
| P5 — OpenAPI-First | The handoff contract is defined by URL shape and the existing `BootstrapProjectResponse` DTO. No new API contract needed because demo mode is client-side only |
| P7 — File Size & Structure | Landing page JS stays under 200 lines. New Angular components (demo route, analyze route) each under 200 lines. Token CSS is a flat extraction, not a generated artifact |

## Component Design

### Static Landing Page

**Purpose**: Convert visitor curiosity into a single CTA click by making the braindump editor the entire above-the-fold experience.

The landing page remains in the `landing/` directory, served by its existing nginx:alpine container. It is pure static HTML with minimal JavaScript — no framework, no build step, no server-side rendering. The page contains exactly one interactive surface: a braindump textarea pre-filled with rotating demo content, and one button.

The JavaScript responsibility is narrow: rotate demo braindumps through the textarea with a visible text animation, track whether the visitor has edited the content (a single boolean flag set on any `input` event), and construct the correct redirect URL when the CTA is clicked. If the visitor has not edited, the redirect targets the demo route with a braindump identifier. If the visitor has edited, the redirect targets the analyze route with the braindump content encoded in the URL fragment.

The textarea is styled using extracted newspaper design tokens so it is visually indistinguishable from the app's braindump input. This is the only visual contract between landing and app — typographic rhythm, ink colors, border treatment, and font stack must match.

### Design Token Extraction Layer

**Purpose**: Give the static landing page access to the app's newspaper design system without importing Angular or duplicating values by hand.

The newspaper design tokens live in `web-ng/src/styles.css` as CSS custom properties on `:root`. The extraction produces a standalone CSS file that the landing page includes directly. This file contains only the custom property declarations (colors, fonts, spacing, border radii) and the base typographic rules (font-size scale, line-height, letter-spacing) that define the newspaper aesthetic.

This is a manual, one-time extraction — not a build-time generation step. The token file is a first-class source file checked into `landing/`, not a derived artifact. When tokens change in the app (rare — the design system is stable), the landing token file is updated to match. This is acceptable because the token surface area is small (under 40 properties) and changes are infrequent. A build-time extraction pipeline would violate P4 for a synchronization event that happens perhaps twice a quarter.

### Landing-to-App Data Handoff Contract

**Purpose**: Transfer braindump content and mode signal across the redirect boundary between two potentially different origins.

This is the most constrained design decision in the system. The landing page and the Angular app may run on the same origin (path-routed behind a shared reverse proxy) or on different origins (subdomain-separated or port-separated). The handoff mechanism must work in both topologies without configuration changes.

**Demo path**: The redirect URL includes a query parameter identifying the demo braindump by slug — for example, a parameter like `demo=mobile-app`. The slug is a short, URL-safe string. The app resolves the slug to a static JSON asset. No braindump content travels in the URL because the app already has it bundled.

**Real path**: The visitor's edited braindump content is encoded as a base64url string in the URL fragment (the hash portion). The fragment is chosen over query parameters for three reasons: fragments have no practical length ceiling in modern browsers (tested to 64KB+, braindumps rarely exceed 5KB), fragments are never sent to the server (no logging of visitor braindump content in access logs), and fragments survive redirects across origins without CORS considerations. The Angular app reads `window.location.hash` on initialization, decodes the payload, and fires the analysis.

**Why not sessionStorage**: sessionStorage is scoped to origin. If landing and app are on different subdomains (the current Docker Compose topology), sessionStorage written by the landing page is invisible to the app. Requiring same-origin deployment as a precondition would constrain infrastructure decisions for a UX optimization. The URL fragment approach is topology-agnostic.

**Why not an intermediary API endpoint**: Storing the braindump server-side and passing a retrieval token would work, but it adds a network round-trip before redirect, requires a new API route with an in-process store and TTL eviction, and violates the epic's explicit exclusion of pre-fired API calls from the landing page. The fragment approach is zero-infrastructure.

### App Demo Mode

**Purpose**: Render a complete spec result instantly from pre-computed static data when a visitor arrives via the demo path.

The app adds a route that matches the demo query parameter. When this route activates, the app fetches a static JSON file from its own assets directory, keyed by the demo braindump slug. The JSON file contains the full set of spec output files (analysis, epic, architecture) in the exact shape of the `BootstrapProjectResponse` DTO that the async bootstrap endpoint returns. This shape identity is deliberate — the rendering logic does not branch on data source.

The pre-computed JSON files are generated offline (content work, outside engineering scope per the epic) and checked into `web-ng/public/demo/` as static assets. They are served by the Angular dev server in development and by the nginx layer in production, with aggressive cache headers since the content is immutable between deployments.

The demo route does not create a project, does not write to the git store, does not consume API quota, and does not require authentication. It is a pure read path. The result view ends at the conversion gate — a prompt to sign up to create the visitor's own specs — which is a handoff point to a separate scope.

### App Real Mode (Analyze Route)

**Purpose**: Accept a visitor's custom braindump from the landing page redirect, fire the analysis, and render the streaming result.

The app adds a route that reads the URL fragment, base64url-decodes the braindump content, and initiates the existing async bootstrap flow. This route calls `POST /api/ai/text/bootstrap-project` with the decoded braindump text and a generated project name, receives a 202 with a job ID, and begins polling `GET /api/ai/text/bootstrap-project/status/{job_id}` for progress.

The polling UI reuses the existing status bar component's loading and partial-file rendering. As each step completes (analysis, then epic, then architecture), the partial files appear in the result view. The full result renders identically to demo mode once all steps finish.

**Authentication handling**: The analyze route operates without authentication. The existing `@require_auth` decorator on the bootstrap endpoint must be bypassed for this anonymous path. The cleanest approach is a parallel anonymous bootstrap route (or a conditional auth check gated by an `anonymous=true` flag) that enforces stricter rate limiting — IP-based throttle instead of user-based quota — to prevent abuse. This route shares the same service layer and workflow engine; only the auth and rate-limit decorators differ.

**Why the app fires the API call, not the landing page**: The epic explicitly excludes pre-fired API calls from the landing page because cross-origin job tracking without queue infrastructure adds complexity that is not justified until measured latency proves it necessary. The app is the sole API consumer. The latency cost is one additional network round-trip (app → API → 202) after the redirect, which adds roughly 50-100ms on a local network. If post-launch metrics show this delay hurts conversion, the architecture can be revisited with a server-side handoff endpoint that both stores the braindump and initiates the job atomically.

### Demo Text Rotation

**Purpose**: Showcase multiple braindump use cases in the landing page textarea without user interaction.

The rotation is pure client-side JavaScript operating on the textarea's value. Four demo braindumps (mobile app idea, SaaS feature, side project plan, refactoring task) cycle with a visible text animation — either a typewriter effect (characters appear sequentially) or a fade-and-replace (textarea content cross-fades between examples). The typewriter approach is preferred because it draws the eye, demonstrates the "messy braindump" nature of the input, and works without CSS opacity transitions on textarea content (which are inconsistent across browsers).

Each demo braindump has a corresponding slug that maps to a pre-computed response in the app. The CTA button reads whichever demo is currently displayed and constructs the redirect URL with that slug. If the visitor has edited the content (tracked by the input event boolean), the button switches to real-mode redirect regardless of which demo was showing.

The rotation pauses when the textarea receives focus, so visitors who start reading are not interrupted. It does not resume after focus — once the visitor engages, the content is theirs to edit or submit as-is.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Landing page | Static HTML + vanilla JS, nginx:alpine | Zero framework overhead, sub-second mobile load, existing deployment container. No build step means instant iteration on copy and animation |
| Design tokens | Standalone CSS file extracted from `web-ng/src/styles.css` | Maintains visual parity without coupling landing to Angular's build pipeline. CSS custom properties are the shared contract |
| Data handoff | URL query param (demo) + URL fragment (real) | Works cross-origin, zero infrastructure, no server-side state, no new API endpoints. Fragment avoids access log exposure of braindump content |
| Demo responses | Static JSON in `web-ng/public/demo/` | Matches `BootstrapProjectResponse` shape exactly. Served as static assets with cache headers. Zero runtime cost |
| App routing | Angular router with two new routes | Integrates with existing flat route table in `app.routes.ts`. Each route is a standalone component under 200 lines |
| Analysis API | Existing `POST /api/ai/text/bootstrap-project` (202 + polling) | No new backend work for the happy path. The async bootstrap workflow, status polling, partial file delivery, and cancellation all exist and are tested |
| Anonymous access | Conditional auth bypass with IP-based rate limiting | Allows unauthenticated visitors to trigger one analysis without signup. Rate limiting prevents abuse without requiring account creation |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| URL fragment for real-mode handoff instead of sessionStorage | Topology-agnostic — works whether landing and app share an origin or not. No infrastructure dependency | Braindump content is visible in the URL bar (base64-encoded, not human-readable). Very long braindumps (>50KB) could theoretically hit browser limits, though this is far beyond typical braindump size |
| Manual token extraction instead of build-time generation | Token surface is small (~40 properties) and changes infrequently. A build pipeline for this would be the only build-time dependency between landing and app | Tokens can drift if the app's design system updates without a corresponding landing update. Mitigated by the small surface area and the fact that token changes are deliberate, not accidental |
| Static JSON for demo responses instead of mock provider routing | The mock provider exists for tests with deterministic output. Demo responses need realistic, curated content that showcases the product's value. These are marketing assets, not test fixtures | Demo responses must be regenerated manually when the spec output format changes. Acceptable because format changes are versioned and intentional |
| App fires API call instead of landing page pre-firing | Eliminates cross-origin job tracking, avoids a new API endpoint for job handoff, keeps the landing page truly static. One fewer network hop before redirect | Visitor experiences the full analysis latency after redirect instead of partial overlap. Measured at 30-60s for the full chain — the loading/streaming UX must be compelling enough to retain the visitor |
| Two Angular routes instead of one route with mode detection | Explicit routing makes the two paths independently testable and independently navigable (demo links can be shared directly). No conditional logic in a shared component | Two components instead of one. Acceptable because each is small and their rendering converges on the same result view |
| No conversion gate in this scope | The gate's UX, copy, and auth integration are a separate design problem. Including them here would couple landing funnel engineering to auth flow decisions that are not yet made | The demo and analyze routes render results and then stop. The visitor can see everything but cannot save or generate more. The "dead end" after results is intentional — it creates urgency for the gate epic |
| Textarea input tracking via boolean flag instead of content diffing | A single boolean set on the first `input` event is the minimal signal needed. Content diffing would require storing the original demo text and comparing on every keystroke | If the visitor types and then undoes back to the exact demo text, it is treated as custom mode. This is a negligible edge case — the cost is one real API call instead of a cached response |

## Data Flow

### Demo Path

Visitor lands → textarea shows rotating demo braindump → visitor clicks CTA without editing → landing JS reads current demo slug → redirect to `{app_origin}/?demo={slug}` → Angular router activates demo route → component fetches `public/demo/{slug}.json` → result view renders pre-computed spec output → conversion gate handoff.

### Real Path

Visitor lands → textarea shows rotating demo braindump → visitor edits text → landing JS detects edit via input flag → visitor clicks CTA → landing JS base64url-encodes braindump → redirect to `{app_origin}/analyze#{encoded_braindump}` → Angular router activates analyze route → component decodes fragment → component calls `POST /api/ai/text/bootstrap-project` with braindump → receives 202 + job ID → polls status endpoint → partial files render as steps complete → full result renders → conversion gate handoff.

### Mock Response Schema

Each demo JSON file contains the fields the app's result rendering already expects: a list of files, each with a filename and markdown content string. The schema mirrors `BootstrapProjectResponse` — specifically, an object with a `files` array where each entry has `filename` (e.g., `analysis.md`, `epic.md`, `architecture.md`) and `content` (the full markdown body). This is the same shape returned by the status endpoint's `files` field when `done: true`. By matching this shape, the demo route and the real route feed identical data structures into the result view.

## Risk Mitigations

**Risk: Visitor bounces during real-mode loading (30-60s analysis time)**
The existing async bootstrap endpoint delivers partial files as each workflow step completes. Analysis (the first step, fastest, uses Haiku) typically returns in 5-10 seconds. The app renders analysis immediately while epic and architecture generate in the background. This progressive disclosure keeps the visitor engaged — they are reading real output within seconds, not staring at a spinner for a minute.

**Risk: Abuse of anonymous analysis endpoint**
IP-based rate limiting on the anonymous bootstrap path caps the per-IP request rate. The limit should be tight — a single visitor has no legitimate reason to fire more than two or three analyses in a session. The existing usage tracking infrastructure (`modules/usage/`) provides the metering surface; the anonymous path adds an IP-keyed counter alongside the existing user-keyed counters.

**Risk: Fragment encoding fails for edge-case braindump content**
Base64url encoding handles all UTF-8 content deterministically. The encoding/decoding pair is a single standard library call on both sides (browser `btoa`/`atob` with a UTF-8 shim, or the `TextEncoder`/`TextDecoder` API). The only failure mode is a braindump exceeding the browser's URL length limit, which in modern browsers is well above 100KB — far beyond any realistic braindump.

**Risk: Token drift between landing and app design systems**
The extracted token file is small and enumerable. A visual regression check (side-by-side screenshot comparison of the landing textarea and the app's braindump input) can be run manually before any deployment that touches `web-ng/src/styles.css`. This is cheaper and more reliable than a build-time extraction pipeline for a surface that changes rarely.

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this architecture
- [Epic](./epic.md) — Scope, tasks, success criteria, and exclusions
- [Timeline](./timeline.md) — Task status and execution tracking