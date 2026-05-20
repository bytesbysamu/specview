The document will be output as markdown directly. Here is the Solution Architecture:

# 🏗️ Solution Architecture: Anonymous Landing Analyze

## Architecture Overview

The anonymous landing analyze capability grafts a single public surface onto specview's existing AI pipeline. A visitor pastes unstructured text into a textarea on the static landing page, and the system runs the same analysis step that authenticated users get — the first stage of the five-document spec pipeline — without requiring an account, a token, or even an email address. The result renders as formatted HTML directly below the input, followed by a conversion CTA pointing to signup.

Structurally, this is three components stitched across a network boundary: a static HTML form served from the existing `landing/` nginx container, a new unauthenticated Flask blueprint that receives the brain dump and orchestrates analysis generation, and a reuse of the existing chain adapter calling the analysis prompt on the Haiku model. The rate limiter sits at the route level, keyed by IP, rejecting requests beyond the daily cap before any AI cost is incurred. The design deliberately avoids pulling the landing page into the Angular SPA, avoids building new prompt logic, and avoids any infrastructure beyond what already ships in the Docker Compose stack.

The key architectural insight is that this feature adds almost no new surface area. The analysis prompt, the chain adapter, the background-thread job pattern, and the IP rate-limiting pattern all exist in the codebase today. The work is composition and exposure — wiring existing internals to an unauthenticated entry point — not new capability.

## Design Principles

| Principle | Application in This Feature |
|-----------|----------------------------|
| **P1 — Adapter Boundary** | The public analysis route calls `adapter.generate()` exactly like the authenticated pipeline does. No direct provider import. The public surface inherits provider switching (CLI, SDK, mock) for free. |
| **P2 — Thin HTTP Layer** | The new route validates input (character cap, rate limit check), delegates to a service function, and returns the response. Zero business logic in the handler. |
| **P3 — Async 202 + Polling** | Analysis on Haiku can reach 30–45 seconds. The route returns 202 with a job identifier immediately. A status endpoint lets the landing page poll until `done: true`. No long-held HTTP connection. |
| **P4 — No Speculative Abstractions** | One route, one service function, one rate-limit decorator invocation. No "public analysis framework." No generic anonymous-endpoint base class. |
| **P5 — OpenAPI-First** | The `/api/public/analyze` POST and `/api/public/analyze/{job_id}` GET endpoints are defined in `openapi.yaml` before any route is written. DTOs generated from the spec. |
| **P7 — File Size & Structure** | The new blueprint, service module, and any landing page JS each stay under 200 lines. One file per concern. |

## Component Design

### Public Analysis Service

**Purpose**: Isolates the analysis-generation logic so the route handler stays thin and the same service is testable without HTTP.

This module extracts the analysis prompt construction that currently lives inside the bootstrap workflow's `_analysis_step()` in `modules/ai/workflows/spec_gen/generate_spec.py`. It takes a raw brain-dump string and a job identifier, builds the same system and user prompts the pipeline uses, calls `adapter.generate()` with the Haiku model, and writes the result into the in-process job state dict. The service function runs inside a daemon thread — the same pattern every other long-running generation in specview uses.

The critical distinction from the authenticated pipeline: this service does not write to the filesystem. Authenticated spec generation persists analysis to `projects/<id>/analysis.md` because downstream steps (epic, architecture) read it. The anonymous flow has no project, no downstream steps, and no persistence requirement. The analysis text lives only in the job state dict and is garbage-collected when the dict entry expires.

### Public Analysis Route (Blueprint)

**Purpose**: Exposes the unauthenticated HTTP surface for anonymous analysis.

A new Flask blueprint (`public_bp`) registered in the `ENABLED_MODULES` list with prefix `/api/public`. It contains two endpoints:

- **POST `/api/public/analyze`** — Accepts the brain dump, validates the character cap, checks the IP rate limit, spawns the analysis in a background thread, and returns 202 with the job identifier.
- **GET `/api/public/analyze/{job_id}`** — Returns the job snapshot: `running`, `done`, `error`, and when done, the `analysis` field containing the rendered markdown.

This blueprint deliberately does not import `require_auth`. It is the only blueprint in the application that serves unauthenticated traffic, which makes it trivially auditable — if a route file does not import `require_auth`, it must live in this blueprint, and this blueprint must have rate limiting on every endpoint.

### IP Rate Limiter

**Purpose**: Caps anonymous AI cost exposure per IP before any token is spent.

The codebase already contains an IP-based rate-limiting decorator in `modules/auth/rate_limit.py` — a module-level dictionary of timestamps per `request.remote_addr`, pruned on each request, returning 429 with a `Retry-After` header when the window is exceeded. That decorator is parameterized by `max_requests` and `window_seconds`.

For the public analysis route, the limiter is configured at 3 requests per 86,400-second window (24 hours). This is the same decorator, same pruning logic, same 429 response shape — just different parameters. No new rate-limiting module is needed.

The rate-limit check executes before the background thread is spawned, which means a rejected request incurs zero AI cost. The 429 response includes the `Retry-After` header so the landing page JS can display a human-readable wait message.

### Input Boundary Enforcement

**Purpose**: Bounds the token cost of any single anonymous request.

A character cap on the brain-dump field (defined in `openapi.yaml` as a `maxLength` constraint on the request schema) rejects oversized input at the validation layer before it reaches the service or the adapter. The cap is set to a value that keeps the Haiku input token count within a predictable cost envelope — the exact number is a configuration choice, not an architectural one, but the enforcement point is fixed: request validation, not the AI call.

This works in concert with the rate limiter. The rate limiter bounds requests-per-IP. The character cap bounds cost-per-request. Together they define a maximum daily AI spend per anonymous visitor that is calculable from two numbers.

### Landing Page Analyze Box

**Purpose**: The user-facing surface — a textarea, a button, and a result container on the existing static landing page.

This lives in the `landing/` directory, which already serves static HTML via an nginx:alpine container. The analyze box is added to the existing page markup: a textarea with placeholder copy, a submit button, and a hidden result div that becomes visible when the analysis returns. All interaction is vanilla JavaScript — a `fetch()` POST to `/api/public/analyze`, then a polling loop on the status endpoint until the job completes, then rendering the markdown response as formatted HTML in the result container.

Markdown-to-HTML conversion happens client-side. The Flask API returns raw markdown (consistent with how every other analysis in the system is stored and transmitted). The landing page includes a lightweight markdown renderer — the only external dependency this feature introduces on the frontend. This keeps the API response format consistent and avoids building a server-side HTML rendering path that nothing else in the system uses.

A loading state is visible during the 30–45 second generation window: the button disables, a timer or progress indicator appears, and the textarea becomes read-only. This is critical UX — 45 seconds of no feedback will cause abandonment.

### Conversion CTA

**Purpose**: Converts the impressed visitor into a signup.

A static HTML block that renders below the analysis result. It is hidden until the analysis completes, then fades in. The copy directs the visitor to the signup flow: "Want the full spec? Epic, architecture, timeline, implementation guide — sign up free." The CTA links to the existing `/signup` route in the Angular SPA.

If the signup flow does not yet exist at the time this feature ships, the CTA links to a waitlist or placeholder. The architecture does not depend on auth or signup being complete — the CTA is a static link, and the destination is a separate concern.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Landing page UI** | Static HTML + vanilla JS in `landing/` | Already served by nginx:alpine. No build step. No framework overhead. The analyze box is a textarea and a fetch call — Angular adds zero value here and would require pulling the landing page into the SPA build. |
| **API route** | Flask Blueprint (`public_bp`) | Consistent with every other route in the system. Registered in `ENABLED_MODULES`. Isolated from auth-protected blueprints by convention and by the absence of `require_auth` import. |
| **AI execution** | `adapter.generate()` with `claude-haiku-4-5` | The adapter is the only AI call boundary (P1). Haiku is the cheapest model in the fleet and already used for the analysis step in the authenticated pipeline. Using the same model ensures output quality parity between anonymous and authenticated analysis. |
| **Background execution** | `threading.Thread(daemon=True)` + module-level dict | The existing pattern for every long-running generation in specview. No Redis, no Celery, no external queue. Single gunicorn worker with `gthread` class means the dict is process-local and consistent. |
| **Rate limiting** | Existing `ip_rate_limit` decorator | Already built, tested, and parameterized. Reuse with different window configuration. |
| **Markdown rendering** | Client-side JS library (e.g., marked, markdown-it) | Keeps API response format as raw markdown (consistent with all other spec outputs). Avoids a server-side HTML rendering path. The library is loaded from CDN or vendored into `landing/` — no npm build. |
| **API contract** | `openapi.yaml` | P5: endpoints defined in the spec before implementation. DTOs generated. Request schema includes `maxLength` on the brain dump field. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Static HTML, not Angular** | The landing page is a marketing surface served by nginx. Pulling it into the Angular SPA would require routing changes, a production build for what is currently a static file, and would couple the landing page deploy to the SPA deploy cycle. Vanilla JS is sufficient for one fetch call and one polling loop. | No component reuse with the SPA. If the landing page grows significantly in interactivity, this decision may need revisiting. For one textarea and one result div, it is clearly correct. |
| **202 + polling, not synchronous response** | P3 is non-negotiable: operations exceeding 30 seconds return 202 immediately. Analysis on Haiku ranges from 20–45 seconds depending on input length. Even if some requests complete under 30 seconds, designing for the synchronous case would mean the first slow request hangs the visitor's browser tab with no feedback. The polling pattern gives the frontend a heartbeat. | Adds a second endpoint (GET status) and a polling loop in JS. This is ~15 lines of vanilla JavaScript and one additional route definition — trivial cost for reliable UX on a 45-second operation. |
| **Reuse existing analysis prompt, not a custom public prompt** | The anonymous analysis must produce the same quality as the authenticated analysis. Using the same prompt from `generate_spec.py` guarantees parity. A custom "lighter" prompt would create a maintenance fork — two prompts doing the same job, drifting independently. | The prompt was tuned for the pipeline context (downstream epic and architecture steps read the analysis). Some of its structural directives (like "Hard Constraints" or "Dependencies & Sequencing") may be less relevant for a standalone anonymous analysis. If user testing reveals confusion, the prompt can be adjusted — but starting with parity avoids premature divergence. |
| **No persistence of anonymous analyses** | Anonymous analyses are not written to the filesystem or any database. They exist only in the in-process job dict until the entry is pruned. There is no project, no `analysis.md` file, no audit trail. | Cannot resurface a past anonymous analysis to a visitor. Cannot track which analyses led to signups (no linkage between the anonymous job and a later signup event). If conversion attribution becomes important, a lightweight event log can be added later — but building it now without data on whether the feature converts at all violates P4. |
| **Haiku model, not Sonnet or Opus** | Haiku is 10–20x cheaper per token than Sonnet. Anonymous analysis is unmetered traffic hitting the AI adapter with zero revenue attached. Cost-per-visitor must be minimized until the conversion funnel is proven. Haiku already powers the authenticated analysis step, so quality is validated. | If a visitor's brain dump is highly complex (nested dependencies, ambiguous scope), Haiku may produce shallower analysis than Sonnet would. This is acceptable — the goal is to demonstrate the product's structure, not to deliver production-grade analysis to unauthenticated visitors. |
| **Character cap enforced at validation, not at the adapter** | Rejecting oversized input before it reaches the service layer means the rate-limit counter is not consumed, the background thread is not spawned, and no adapter call is made. The validation layer is the cheapest place to reject. | The specific cap value requires tuning — too low and legitimate brain dumps are truncated; too high and a single request can be expensive. The cap is defined in `openapi.yaml` so it can be changed without code modifications. |
| **Separate blueprint (`public_bp`), not added to existing `ai_bp`** | Every route on `ai_bp` is decorated with `@require_auth`. Adding an unauthenticated route to the same blueprint creates a security inconsistency — a new developer adding a route to `ai_bp` would reasonably assume auth is enforced. A dedicated public blueprint makes the auth boundary visible at the file level: if a route is in `public_bp`, it is unauthenticated. | One more file, one more `ENABLED_MODULES` entry. Trivial cost for a clear security boundary. |
| **CTA links to existing signup route, not embedded signup** | Building an inline signup form on the static landing page would require auth infrastructure on a page that currently has none. The CTA is a link. The destination is the Angular SPA's `/signup` route (or a placeholder if signup is not yet built). | The visitor leaves the static page and enters the SPA. There is a context switch. This is acceptable because the visitor has already experienced the product — the CTA lands on a warm lead, not a cold one. |
| **Client-side markdown rendering, not server-side HTML** | Every other spec document in the system is stored and transmitted as markdown. The Angular SPA renders it client-side. The landing page should do the same. Adding a server-side HTML rendering path for one route creates a rendering inconsistency and a new dependency in the Flask layer. | Requires loading a JS markdown library on the landing page (adds ~20KB gzipped for a library like marked). Acceptable for a page that currently loads minimal JS. |

## Cross-Cutting Concerns

### Cost Containment

Three layers bound anonymous AI spend: the IP rate limiter (3 requests/day/IP), the character cap on input (bounded tokens per request), and the model choice (Haiku, cheapest available). The worst-case daily cost per IP is calculable: 3 × (max input tokens + max output tokens) × Haiku price-per-token. At scale, the rate limiter ensures that even a botnet distributing requests across IPs is limited to 3 analyses per IP per day — and each analysis is capped in size.

### Security Surface

The public route is the first unauthenticated endpoint that triggers AI generation. The rate limiter must ship with the route — never before the route exists, never after. The epic's success criteria make this explicit: "An unprotected `/api/public/analyze` endpoint never exists in production." The blueprint, the rate-limit decorator, and the character-cap validation are a single atomic deployment unit.

Input sanitization matters because the brain dump is interpolated into a prompt template. The service must treat the brain dump as untrusted user input — no format-string injection, no template variable leakage. The existing `generate_spec.py` prompt builder already handles this by passing the brain dump as a discrete user-message field rather than interpolating it into the system prompt.

### Nginx Routing

The landing page and the Flask API run in separate containers. The analyze box on the landing page makes fetch calls to `/api/public/analyze`, which nginx reverse-proxies to the Flask container. This is the same routing pattern every Angular-to-Flask call in the system uses — nginx serves static assets for paths it owns and proxies `/api/*` to Flask. No new nginx configuration is needed beyond what already exists for the `/api` prefix.

### Job State Lifecycle

Anonymous job entries in the in-process dict need a TTL. Without cleanup, a high-traffic landing page would grow the dict indefinitely. A lazy-pruning strategy — delete entries older than N minutes on each new request — is consistent with how the IP rate limiter prunes its timestamp lists. The TTL should be generous enough that a slow-polling client can still retrieve its result (10–15 minutes) but short enough that memory pressure stays negligible.

## Related Documents

- [Analysis](./analysis.md) — Problems, constraints, and open questions driving this feature
- [Epic](./epic.md) — Business value, scope boundaries, and task breakdown
- [Timeline](./timeline.md) — Delivery sequence and status tracking