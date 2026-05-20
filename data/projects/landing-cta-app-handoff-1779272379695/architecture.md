# 🏗️ Solution Architecture: Landing CTA App Handoff

## Architecture Overview

This design converts the landing page CTA from a self-contained demo into a product onboarding funnel by making one structural change: the landing page stops rendering results and starts creating real projects. When a visitor clicks Analyze, the backend creates a genuine filesystem project — identical in shape to what authenticated users produce — and the browser redirects into the Angular app where the analysis renders progressively in the real project view. The visitor never sees a "demo" experience; they see the actual product with their actual data.

The system already has two anonymous analysis paths: the lightweight `POST /api/public/analyze` that returns a throwaway in-memory result, and the heavier `POST /api/ai/anonymous/bootstrap-project` that runs the full three-step workflow but discards results after the job completes. Neither creates a real project. This architecture closes that gap by teaching the public analyze endpoint to create a real filesystem project, persist the braindump, write analysis output to that project directory, and return a project-scoped job identifier that the Angular app can poll. The project directory is the source of truth — not the in-memory job store.

The key insight is that the job identifier and the project identifier should be the same value. This eliminates a mapping layer, makes the URL self-describing, and means the Angular app can load the project and poll the job with a single identifier. The project ID in the URL serves as a bearer token: anyone who has it can view the result, but all mutation operations require authentication. This matches the existing public share pattern in `modules/data/public/routes.py`, where a slug grants read-only access without auth.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | AI calls continue through `modules/runtime/chain/adapter.py` only. The public analyze service never imports a provider directly, even though it targets a specific model. |
| P2 — Thin HTTP Layer | The modified `public_analyze` route handler validates input, calls the service, and returns 202. Project creation, braindump persistence, and thread spawning live in the service layer. |
| P3 — Async 202 + Polling | The endpoint returns 202 immediately with a project-scoped job ID. A daemon thread runs the analysis. The status endpoint reads progress from the in-process job store and completed output from the filesystem. No HTTP connection held open. |
| P4 — No Speculative Abstractions | No "anonymous session manager" or "project claim orchestrator." One endpoint creates one project. One route displays it. The claim flow is a future epic. |
| P5 — OpenAPI-First | The modified `POST /api/public/analyze` response shape and the new `GET /api/public/analyze/{job_id}` progressive response shape are defined in `openapi.yaml` before implementation. |
| P7 — File Size & Structure | The Angular anonymous analyze component is a single file under 200 lines. It composes existing sub-components rather than duplicating view logic. |

## Component Design

### Backend: Public Analyze Endpoint (Modified)

**Purpose**: Transform the existing lightweight public analysis into a real-project-creating onboarding entry point.

The current `POST /api/public/analyze` in `modules/ai/routes/public_analyze.py` accepts a braindump, spawns a daemon thread that calls `adapter.rewrite()` with haiku, stores the result in an in-memory dict with a 15-minute TTL, and returns a job ID. The result never touches the filesystem.

The modified endpoint adds three responsibilities before spawning the thread: generate a project ID in the standard `slug-timestamp` format, create the project directory under `PROJECTS_DIR`, and write `braindump.md` and `project.json` to that directory. The job ID returned to the caller is the project ID itself. The daemon thread then runs the analysis and writes the output to `analysis.md` in the project directory — the same location and format that authenticated projects use. The in-memory job store tracks progress for polling but is no longer the source of truth for the result; the filesystem is.

The `GET /api/public/analyze/{job_id}` status endpoint continues to read progress from the in-memory store while the job is running, but once the job completes, it reads the analysis content from the project's `analysis.md` file. This means a server restart after completion does not lose the result — the file is already persisted. The response shape adds a `project_id` field so the app knows which project to load.

The IP-based rate limiter stays as-is. No auth decorator is added. The endpoint remains fully anonymous.

### Backend: Anonymous Project in the Data Layer

**Purpose**: Allow projects to exist without an owner so that anonymous visitors get real projects that can later be claimed.

The `Project` model in `modules/data/projects/models.py` currently requires a `user_id` foreign key. Anonymous projects need this field to be nullable. A project with `user_id = NULL` is an anonymous project — unclaimed, visible only via its project ID, and subject to TTL cleanup.

The project service in `modules/data/projects/service.py` already handles filesystem operations (directory creation, file writes, `project.json` generation) independently of the database layer. The public analyze service calls these filesystem functions directly to create the project directory and persist files. The database row is created with `user_id = NULL` and a new `anonymous = True` flag column for efficient querying during cleanup.

The existing project query paths in `modules/data/projects/routes.py` are all decorated with `@require_auth` and scoped to `g.current_user.id`. Anonymous projects are invisible in those queries by construction — they have no owner to match against. No guard changes needed on authenticated routes.

### Backend: Anonymous Project Cleanup

**Purpose**: Prevent unbounded disk growth from unclaimed anonymous projects.

A scheduled cleanup function sweeps the database for projects where `user_id IS NULL` and `created_at` is older than a configurable TTL (default: 48 hours). For each expired project, it deletes the project directory from the filesystem and removes the database row.

The cleanup runs as a daemon thread on a timer interval, started once during app initialization in `create_app.py`. This follows the existing pattern of daemon threads for background work and avoids adding an external scheduler dependency. The timer interval is generous (every 6 hours) because the cost of a few extra hours of anonymous project storage is negligible compared to the complexity of a tighter loop.

The 48-hour TTL is deliberately long. A visitor who analyzes their braindump at 11 PM should be able to return the next morning, find the URL in their browser history, and still see their analysis. Shorter TTLs optimize for disk at the cost of conversion — the wrong trade-off when each anonymous project is a potential sign-up.

### Frontend: Anonymous Analyze Route

**Purpose**: Give anonymous visitors a URL that renders their analysis in the real app UI without requiring authentication.

A new route at `/analyze` in `app.routes.ts` accepts a `job` query parameter. This route has no `canActivate` auth guard — it is the only non-auth route in the app besides the login and signup pages. The route loads a new `anonymous-analyze.component.ts` that reads the job ID from the query parameter, polls the public analyze status endpoint, and renders the analysis progressively.

The anonymous analyze component does not duplicate the project view. It composes the existing `reader-panel.component` and `status-bar.component` to render the analysis in the same layout that authenticated users see. The braindump is loaded as the project's source document in the sidebar. The analysis renders in the reader panel as it arrives. The status bar shows generation progress using the same signals-based pattern as the authenticated flow.

The component wraps the project view in a "preview shell" that replaces the authenticated app chrome (navigation, project grid, settings) with a minimal header showing the specview logo and a sign-up CTA. This gives the visitor the real reading experience without the distraction of features they cannot yet use. Every action beyond viewing — generating additional spec documents, editing, saving — shows a sign-up prompt instead of executing.

### Frontend: Landing Page Handoff

**Purpose**: Replace inline result rendering with a POST-and-redirect flow that moves the visitor into the real app.

The current `landing/analyze.js` handles the full lifecycle: POST the braindump, poll for results, render the analysis in a DOM element below the textarea. The modified version strips everything after the POST response. Once the 202 response arrives with a job ID, `analyze.js` redirects the browser to the app URL with the job ID as a query parameter. No polling. No rendering. No result DOM. The landing page's only job is to fire the API call and hand off.

The redirect is a full page navigation via `window.location.href`, not an AJAX call or client-side router transition. This is intentional: the landing page and the app are separate deployments on separate subdomains. A full navigation is the cleanest handoff — no shared state, no iframe, no postMessage. The visitor's browser simply moves from the static landing page to the Angular SPA.

During the brief window between clicking the CTA and the redirect completing, the landing page shows a loading state indicating the analysis is starting. This covers the round-trip time for the POST request (typically under one second). The visitor is never staring at a blank screen.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend API | Flask (existing `modules/ai/routes/public_analyze.py`) | Endpoint already exists and handles anonymous analysis. Modify in place rather than creating a new module. |
| Async execution | `threading.Thread(daemon=True)` with module-level dict | Matches the existing `_BOOTSTRAP_JOBS` and `_JOBS` patterns. Single gunicorn worker means in-process state is safe. |
| Project storage | Filesystem (`PROJECTS_DIR`) + SQLite via SQLModel | Same dual-write pattern as authenticated projects. Filesystem is source of truth for spec files; DB is source of truth for ownership and metadata. |
| Frontend route | Angular standalone component | Flat file in `src/app/` per project convention. Composes existing sub-components. No new services needed — `projects.service.ts` already handles polling. |
| Landing handoff | Vanilla JS (`analyze.js`) | Landing page is a static nginx site. No framework. The modification removes code rather than adding it. |
| Cross-origin | Full page redirect (`window.location.href`) | Landing page and app are separate deployments. Redirect is simpler and more reliable than any shared-state approach. |
| Cleanup | Daemon timer thread in Flask process | No external cron, no Redis, no celery. Consistent with the single-process architecture. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Project ID is the job ID | Eliminates a mapping layer between the job store and the project store. The URL `?job=<id>` directly identifies the project in the filesystem and database. One identifier serves as both the polling key and the project key. | If the project ID format ever changes, existing anonymous URLs break. Acceptable because project IDs are already stable slugs used in authenticated URLs. |
| Nullable `user_id` for anonymous projects | Clean data model: an unclaimed project is simply one with no owner. The claim flow (future epic) sets `user_id` on sign-up. No sentinel "anonymous user" row needed, no separate anonymous project table. | Requires a schema migration on the `Project` table. The migration is additive (nullable column) so it is non-breaking and does not require downtime. |
| Modify existing `public_analyze` endpoint instead of creating a new one | The landing page already calls `POST /api/public/analyze`. Keeping the same URL means zero landing page changes to the API target — only the response handling changes. The backend upgrade is invisible to the POST caller. | The endpoint's responsibilities grow: it now creates projects and persists files in addition to running analysis. This is managed by keeping the route handler thin and moving all new logic into the service layer. |
| Write analysis to filesystem during generation, not after | The daemon thread writes `analysis.md` progressively as chunks arrive, rather than buffering the full result and writing once. This means a status poll can read partial content from disk even if the in-memory job store has been evicted. | Partial writes mean the file may be in an incomplete state if the process crashes mid-generation. Acceptable because the file is overwritten on completion, and anonymous projects are ephemeral by nature. |
| Full page redirect instead of shared state | The landing page and app are separate deployments served by separate containers. A full page navigation is the simplest handoff with zero shared runtime state. No postMessage, no iframe, no cookie-based session linking. | The visitor sees a brief page load as the Angular app bootstraps. This is mitigated by the app's loading shell and by the fact that the analysis is still generating — the visitor expects to wait. |
| 48-hour TTL for anonymous projects | Optimizes for conversion over disk usage. A visitor who discovers the tool in the evening should find their analysis the next morning. Disk cost of abandoned projects for two days is negligible compared to the value of a returning visitor. | Disk usage grows linearly with anonymous traffic until cleanup runs. At expected volumes (low tens per day), this is measured in megabytes — not a concern. |
| Reuse reader-panel and status-bar components in anonymous view | The visitor sees the real product UI, not a stripped-down version. This is the entire point of the epic — the CTA becomes a product experience. Reusing components also means zero duplication and automatic benefit from future UI improvements. | The anonymous view inherits the full complexity of the project view components. Some features (edit, generate, settings) must be gated behind auth checks within the component. This adds conditional logic but is preferable to maintaining a parallel "lite" view. |
| IP rate limiting stays at 3 per day | The existing rate limit on `POST /api/public/analyze` is unchanged. Creating real projects raises the cost of abuse slightly (disk writes vs. memory-only), but the rate limit already constrains volume. Adding more sophisticated abuse prevention is explicitly deferred per the epic scope. | A determined abuser can rotate IPs. Acceptable for launch. The 48-hour TTL cleanup provides a natural ceiling on accumulated abuse. |
| No CORS changes for the POST | The landing page already makes a cross-origin POST to the API, so CORS headers are already configured to allow the landing page origin. The redirect is a full navigation, not an AJAX call, so it requires no CORS at all. | If the landing page origin changes (rebrand, new domain), the CORS allowlist needs updating. This is an existing operational concern, not a new one. |

## Data Flow

The handoff involves three systems (landing page, API, Angular app) and two transitions (POST, redirect). The data flows in one direction: visitor input enters through the landing page, persists in the API, and renders in the app.

The landing page collects the braindump and POSTs it to the API. The API creates a project directory, writes `braindump.md` and `project.json`, enqueues the analysis job, and returns 202 with the project ID as the job ID. The landing page reads the job ID from the response and redirects the browser to the app URL with the job ID as a query parameter.

The Angular app reads the job ID from the URL, begins polling the status endpoint, and renders the analysis as it arrives. The status endpoint reads from the in-memory job store while the job is running and falls back to the filesystem after completion. The app loads the braindump from the project directory to display alongside the analysis.

The visitor's browser is the only thing that crosses the boundary between systems. No server-to-server communication is needed. The project ID in the URL is the single thread connecting all three systems.

## Security Considerations

The project ID functions as a bearer token for anonymous access. Anyone who possesses the URL can view the analysis. This is an intentional design choice — the same pattern used by the existing public share feature in `modules/data/public/`. The project ID is a slug with a timestamp suffix, which provides reasonable unguessability without requiring cryptographic randomness. For this use case (ephemeral anonymous analyses with a 48-hour TTL), this level of security is appropriate.

All mutation operations (editing files, generating additional documents, deleting the project) require authentication. The anonymous analyze route and its corresponding API endpoints are strictly read-only. The sign-up gate is enforced in the Angular component by intercepting mutation actions and showing a sign-up prompt.

The IP rate limiter prevents bulk anonymous project creation. The TTL cleanup prevents indefinite accumulation. Together, these two mechanisms bound the attack surface: an abuser can create at most 3 projects per IP per day, and all unclaimed projects are deleted within 48 hours.

## Integration Points

The modified `public_analyze` service depends on the project filesystem service in `modules/data/projects/service.py` for directory creation and file writes. This is the only new cross-module dependency. The AI adapter, rate limiter, and job store patterns are all existing dependencies that remain unchanged.

The Angular anonymous analyze component depends on existing sub-components (`reader-panel`, `status-bar`) and the existing `projects.service.ts` for HTTP calls. A new method on the projects service handles the public status endpoint polling, but the polling pattern (interval-based with signal updates) is identical to the authenticated flow.

The landing page's `analyze.js` depends on the API response shape (specifically the `job_id` field) and the app's URL structure (specifically the `/analyze?job=` route). These two contracts are the only coupling between the three systems.

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design
- [Epic](./epic.md) — Scope, tasks, and success criteria for Landing CTA App Handoff
- [Timeline](./timeline.md) — Status tracking for implementation