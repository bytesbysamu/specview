# Implementation Guide: Anonymous Landing Analyze

## Overview
This epic adds a product-led acquisition channel to specview's landing page by letting unauthenticated visitors paste a brain dump and receive a structured analysis — the same first step of the five-document spec pipeline — without signing up. The five tasks sequence linearly with one parallelism opportunity: Task 1 (rate limiter parameterization) unblocks Task 2 (public endpoint), which unblocks Task 3 (landing page UI) and Task 5 (input guardrails) in parallel, and Task 4 (CTA) follows Task 3.

## Shared Pre-flight
- Confirm the existing rate limiter at `modules/auth/rate_limit.py` works and review its current 5-requests/3600-second defaults
- Confirm the analysis prompt constants `ANALYSIS_SYSTEM` and `ANALYSIS_USER` in `modules/ai/workflows/spec_gen/generate_spec.py` produce reliable standalone output on Haiku
- Confirm `modules/ai/job_store.py` and its `create_job`, `get_job`, `complete_job`, `fail_job` functions are operational — this is the async pattern to reuse
- Confirm `modules/runtime/chain/adapter.py` exposes `generate()` returning a `ChainResult` dataclass with `text`, `latency_ms`, `tokens_in`, `tokens_out`
- Confirm `openapi.yaml` at project root is the source of truth for DTOs and that `dtos/models.py` is regenerated from it
- Confirm nginx already proxies `/api/*` to the Flask container — no new nginx config is needed
- Verify the `ENABLED_MODULES` list in `create_app.py` (lines 23–36) to understand where the new blueprint registration goes
- Decide on the brain-dump character cap value (5,000 or 10,000 characters) — this affects the `maxLength` in the OpenAPI schema and bounds per-request token cost

---

## Task 1: IP Rate Limiter Module  [Effort: 0.5 days]

### What
The existing rate limiter in `modules/auth/rate_limit.py` is hardcoded to 5 requests per 3600-second window. This task parameterizes the decorator so callers can specify `max_requests` and `window_seconds`, enabling the public analysis route to use 3 requests per 86,400 seconds (24 hours) while preserving the current behavior for all existing call sites.

### Files
- **Modify**: `modules/auth/rate_limit.py` — refactor `ip_rate_limit` from a simple decorator into a decorator factory that accepts `max_requests` and `window_seconds` keyword arguments, defaulting to 5 and 3600 respectively so existing usages remain unchanged

### Steps
1. Read the current `ip_rate_limit` decorator in `modules/auth/rate_limit.py` and note its pruning logic, the module-level `_ip_timestamps` dictionary, and the 429 response with `Retry-After` header.
2. Refactor `ip_rate_limit` into a decorator factory: the outer function accepts `max_requests` (default 5) and `window_seconds` (default 3600) and returns the actual decorator. The inner decorator retains the existing pruning, timestamp-check, and 429-response logic but uses the parameterized values instead of hardcoded constants.
3. Ensure backward compatibility: when `ip_rate_limit` is called without arguments (the way `modules/auth/routes.py` currently uses it on the `request-magic-link` endpoint), it must still work as a bare decorator. Detect whether the first argument is a function (bare decorator usage) or whether keyword arguments were passed (factory usage).
4. Verify the `Retry-After` header value is computed from the parameterized `window_seconds`, not the old hardcoded 3600.
5. Run the existing test suite to confirm no regressions on the auth rate-limiting behavior.

### Verify
- Calling `@ip_rate_limit` with no arguments on the existing `request-magic-link` route still enforces 5 requests per hour
- Calling `@ip_rate_limit(max_requests=3, window_seconds=86400)` returns a working decorator that rejects the 4th request from the same IP within 24 hours with a 429 status and correct `Retry-After` header
- `python -m pytest tests/ -k rate_limit` passes with no failures
- Grep the codebase for all usages of `ip_rate_limit` and confirm none are broken by the refactor

---

## Task 2: Public Analysis Endpoint  [Effort: 1 day]

### What
This task creates the unauthenticated Flask blueprint and service module that receive a brain dump, spawn analysis generation in a background thread, and expose a polling endpoint for the result. It is the backend core of the anonymous analysis feature.

### Files
- **Modify**: `openapi.yaml` — add `POST /api/public/analyze` and `GET /api/public/analyze/{job_id}` endpoint definitions with request/response schemas including `PublicAnalyzeRequest` (with `braindump` field and `maxLength`) and `PublicAnalyzeJobStatus` (with `running`, `done`, `error`, `analysis` fields)
- **Modify**: `dtos/models.py` — add `PublicAnalyzeRequest` and `PublicAnalyzeJobStatus` Pydantic models matching the new OpenAPI schemas
- **Create**: `modules/ai/services/public_analyze.py` — service module containing a `start_analysis` function that extracts the analysis prompt from `generate_spec.py` constants, calls `adapter.generate()` with Haiku, and writes the result into the job store via `complete_job`
- **Create**: `modules/ai/routes/public_analyze.py` — Flask blueprint `public_analyze_bp` with prefix `/api/public`, containing the POST and GET endpoints, applying the parameterized rate limiter from Task 1
- **Modify**: `create_app.py` — add `('modules.ai.routes.public_analyze', 'public_analyze_bp')` to the `ENABLED_MODULES` list

### Steps
1. Define the two new endpoints in `openapi.yaml`. The POST endpoint accepts a JSON body with a `braindump` string field (set `maxLength` to the agreed character cap). The GET endpoint returns a status object with boolean `running` and `done` fields, an optional `analysis` string field, and an optional `error` string field. The POST returns 202 with a `job_id` string. The GET returns 200.
2. Add the corresponding Pydantic models `PublicAnalyzeRequest` and `PublicAnalyzeJobStatus` to `dtos/models.py`, matching the OpenAPI schemas exactly.
3. Create the service module at `modules/ai/services/public_analyze.py`. Import `ANALYSIS_SYSTEM` and `ANALYSIS_USER` from `modules.ai.workflows.spec_gen.generate_spec`. Import `generate` from `modules.runtime.chain.adapter`. Import `create_job`, `complete_job`, and `fail_job` from `modules.ai.job_store`. Define a `run_analysis` function that takes a `job_id` and `braindump` string, formats the user prompt by injecting the braindump into `ANALYSIS_USER`, calls `adapter.generate()` with the system prompt `ANALYSIS_SYSTEM` and model `claude-haiku-4-5`, and on success calls `complete_job` with the `ChainResult.text`. Wrap the adapter call in a try/except that calls `fail_job` on any exception.
4. Define a `start_analysis` function in the same service module that creates a job via `create_job` (passing skill name `"public_analyze"` and version `"1"`), spawns a daemon thread targeting `run_analysis` with the job ID and braindump, and returns the job object.
5. Create the blueprint module at `modules/ai/routes/public_analyze.py`. Instantiate a `Blueprint` named `"public_analyze"` with `url_prefix="/api/public"`. Define `POST /analyze` that validates the request body against `PublicAnalyzeRequest`, applies `@ip_rate_limit(max_requests=3, window_seconds=86400)`, calls `start_analysis`, and returns 202 with the job ID. Define `GET /analyze/<job_id>` that calls `get_job` from the job store and returns the status as `PublicAnalyzeJobStatus`.
6. Register the new blueprint in `create_app.py` by adding the tuple `('modules.ai.routes.public_analyze', 'public_analyze_bp')` to `ENABLED_MODULES`.
7. Confirm the blueprint does not import `require_auth` anywhere — this is the security-boundary convention.

### Verify
- `POST /api/public/analyze` with a valid braindump string returns 202 with a JSON body containing `job_id`
- `GET /api/public/analyze/{job_id}` returns `running: true` immediately, then `done: true` with a non-empty `analysis` field after generation completes
- The 4th POST from the same IP within 24 hours returns 429 with a `Retry-After` header
- `python -m pytest tests/` passes — no import errors, no registration failures
- Grep `modules/ai/routes/public_analyze.py` for `require_auth` returns zero matches

---

## Task 3: Landing Page Analyze Box  [Effort: 1.5 days]

### What
This task builds the visitor-facing UI: a textarea, a submit button, a loading state, and a result container on a new static landing page. All interaction is vanilla JavaScript making fetch calls to the endpoints from Task 2. A client-side markdown library renders the raw analysis response as formatted HTML.

### Files
- **Create**: `landing/index.html` — static HTML page with the analyze textarea, submit button, a hidden result div, and a loading indicator; includes the vanilla JS inline or via a script tag, and loads a markdown rendering library (marked.js) from a vendored file or CDN
- **Create**: `landing/styles.css` — minimal stylesheet for the analyze box, result container, loading state, and page layout
- **Create**: `landing/analyze.js` — vanilla JavaScript handling form submission (POST to `/api/public/analyze`), the polling loop (GET to `/api/public/analyze/{job_id}` every 2–3 seconds), markdown-to-HTML rendering of the result, loading/disabled states, and error display for 429 rate-limit responses
- **Modify**: `docker-compose.yml` (or the relevant compose/nginx config) — add a volume mount or service entry so nginx serves the `landing/` directory as the static landing page, if not already configured

### Steps
1. Create the `landing/` directory at the project root.
2. Build `landing/index.html` with semantic markup: a header section with product copy, a main section containing a textarea element (with placeholder text like "Paste your idea, feature plan, or brain dump here..."), a submit button, a hidden div for the analysis result, and a loading indicator element (spinner or progress text) that is hidden by default.
3. Create `landing/styles.css` with styles for the page layout, textarea sizing, button states (default, disabled/loading, hover), the result container, and the loading indicator. Keep the textarea large enough to invite multi-paragraph input. Style the result container to render formatted HTML (headings, lists, bold) readably.
4. Create `landing/analyze.js` with three concerns. First, the submit handler: on button click, read the textarea value, validate it is non-empty and under the character cap, disable the button and textarea, show the loading indicator, and POST the braindump to `/api/public/analyze`. Second, the polling loop: on 202 response, extract the `job_id`, then poll `GET /api/public/analyze/{job_id}` every 2.5 seconds; when `done` is true, stop polling and render the `analysis` field; when `error` is present, display the error message. Third, error handling: if the POST returns 429, parse the `Retry-After` header and display a human-readable message ("You've reached the daily limit. Try again in X hours."); re-enable the form on any error.
5. Include the marked.js library (either vendored into `landing/lib/marked.min.js` or loaded from a CDN) and use it to convert the raw markdown analysis into HTML before inserting it into the result div.
6. Add a visible timer or elapsed-time counter during the loading state so the visitor knows the system is working during the 30–45 second generation window. Disable the textarea to read-only and the button to prevent double submission.
7. Configure the Docker Compose or nginx setup to serve the `landing/` directory. If the existing nginx container already serves a static directory, add the landing page files there. If a new volume mount is needed, add it to the compose file pointing the nginx container at `landing/`.

### Verify
- Opening the landing page in a browser shows the textarea, placeholder text, and submit button
- Submitting a brain dump disables the form, shows the loading indicator, and after 30–45 seconds renders formatted HTML analysis below the textarea
- Submitting an empty textarea shows a client-side validation message and does not make a network request
- After a 429 response, the form re-enables and displays a rate-limit message with the retry window
- The rendered analysis contains proper heading, list, and emphasis formatting (not raw markdown syntax)

---

## Task 4: Conversion CTA & Signup Handoff  [Effort: 0.5 days]

### What
This task adds a call-to-action block that appears immediately after every successful analysis, directing the visitor toward signup and the full spec pipeline. The CTA is hidden until analysis completes and fades in alongside the result.

### Files
- **Modify**: `landing/index.html` — add a CTA div below the result container, hidden by default, containing the conversion copy and a link to `/signup` (or a placeholder/waitlist URL if the signup route does not yet exist)
- **Modify**: `landing/styles.css` — add styles for the CTA block including a fade-in animation, visual emphasis (background color, border, or card treatment), and responsive sizing
- **Modify**: `landing/analyze.js` — after the analysis result renders successfully, unhide the CTA div and trigger the fade-in animation

### Steps
1. Add a hidden CTA div in `landing/index.html` positioned directly below the analysis result container. The copy should read something like: "Want the full spec? Epic, architecture, timeline, implementation guide — sign up free." Include an anchor element linking to `/signup`.
2. Check whether the Angular SPA has a `/signup` route defined. If it exists, the CTA links there. If it does not exist, link to a waitlist page or a placeholder route and add a comment in the HTML noting this is a placeholder pending the auth epic.
3. Add CSS in `landing/styles.css` for the CTA block: a fade-in transition (opacity 0 to 1 over 0.3–0.5 seconds), a visually distinct container (subtle background, border-radius, padding), and a prominent link or button styled as the primary action.
4. In `landing/analyze.js`, after the analysis markdown is rendered into the result div, remove the hidden attribute from the CTA div and add a CSS class that triggers the fade-in animation.
5. Ensure the CTA appears on every successful analysis, not just the first one. If the visitor submits a second brain dump (within rate limits), the CTA should reappear after the new result.

### Verify
- After a successful analysis, the CTA block fades in below the result with the correct copy
- The CTA link points to `/signup` (or the agreed placeholder URL) and is clickable
- Submitting a second analysis re-triggers the CTA fade-in after the new result
- The CTA is not visible on page load or during the loading state — it only appears after a successful analysis

---

## Task 5: Input Guardrails & Abuse Hardening  [Effort: 0.5 days]

### What
This task adds server-side input validation and job-state lifecycle management to prevent abuse and resource exhaustion. It enforces the character cap at the validation layer (before any AI cost), adds TTL-based pruning to anonymous job entries, and hardens the public endpoint against malformed or adversarial input.

### Files
- **Modify**: `openapi.yaml` — confirm `maxLength` is set on the `braindump` field in the `PublicAnalyzeRequest` schema (should already be present from Task 2, but verify the value is correct and add `minLength: 1` if missing)
- **Modify**: `modules/ai/routes/public_analyze.py` — add explicit server-side validation that rejects requests where the braindump exceeds the character cap or is empty/whitespace-only, returning 400 with a descriptive error message, before the rate-limit check consumes a slot
- **Modify**: `modules/ai/services/public_analyze.py` — add TTL-based lazy pruning to the anonymous job entries: on each new `start_analysis` call, iterate the job store and remove entries older than 15 minutes to prevent unbounded memory growth
- **Modify**: `modules/ai/job_store.py` — if the job store does not already expose a pruning function, add a `prune_expired(ttl_seconds: int)` function that removes entries older than the TTL; this is consistent with the rate limiter's pruning pattern

### Steps
1. Verify that the `maxLength` constraint on `braindump` in `openapi.yaml` matches the agreed character cap. Add `minLength: 1` if not already present to reject empty strings at the schema level.
2. In `modules/ai/routes/public_analyze.py`, add validation at the top of the POST handler (before the rate-limit decorator fires) that strips the braindump and rejects it with a 400 response if it is empty, whitespace-only, or exceeds the character cap. The validation should run before the rate limiter so that malformed requests do not consume a rate-limit slot.
3. Review the ordering of decorators on the POST endpoint: the input validation must execute first (innermost decorator or inline at the top of the handler), then the rate-limit check. If the rate limiter is a decorator, the character-cap check should be inline at the top of the handler body so it runs after the decorator has already been entered but before `start_analysis` is called. Alternatively, restructure so the validation is fully inline and the rate-limit decorator wraps the handler.
4. Add a `prune_expired` function to `modules/ai/job_store.py` that accepts a `ttl_seconds` parameter, acquires the lock, and removes all entries from the `_JOBS` dict where `started_at` is older than the TTL. This mirrors the pruning pattern in the rate limiter.
5. Call `prune_expired(ttl_seconds=900)` at the top of the `start_analysis` function in `modules/ai/services/public_analyze.py` so that stale job entries are cleaned up on each new anonymous analysis request.
6. Ensure the braindump string passed to the service is stripped of leading/trailing whitespace before being injected into the prompt template, preventing whitespace-padded inputs from inflating token counts.

### Verify
- A POST with an empty braindump or whitespace-only string returns 400 and does not consume a rate-limit slot
- A POST with a braindump exceeding the character cap returns 400 and does not consume a rate-limit slot
- After 15 minutes, completed job entries are no longer returned by `GET /api/public/analyze/{job_id}` (they have been pruned)
- `python -m pytest tests/` passes with no failures
- `ng build --configuration production` (or the equivalent Flask/Docker build command) succeeds with no errors