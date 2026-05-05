# 🏗️ Solution Architecture: Express Retirement: Full Flask API Migration: A

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Flask already owns the pattern. `POST /api/ai/text/rewrite` in `flask/modules/ai/routes.py` demonstrates the complete shape: route handler validates a Pydantic DTO, calls `chain.adapter` for AI, raises `ServiceError` on failure, returns a typed response. The `flask/modules/ai/prompts/` module already contains pure functions for every target endpoint — `iterate_prompt`, `review_prompt`, `lint_braindump_prompt`, and `generate_spec_prompt` exist today. This migration is wiring, not invention: the four remaining Express endpoints need route handlers and OpenAPI entries, not new infrastructure.

The key structural insight is that `chain/adapter.py` is the only door to AI providers. Routes call `chain.adapter.generate()` or `chain.adapter.rewrite()` — never `chain.providers.claude` directly. This boundary is enforced by the existing structural test in `flask/modules/ai/tests/` and keeps provider-swapping (SDK → mock in tests) invisible to route code. The migration adds four new consumers of `chain/adapter.py` without changing the adapter.

The proxy in `proxy.conf.json` today routes six known paths to Flask (3101) and falls back all unknown `/api` traffic to Express (3100). That fallback is the last coupling between the two runtimes. As each endpoint migrates, it gets added to the explicit Flask list. When all four are added and confirmed, the fallback route is removed and Express is no longer started. Retirement is a proxy diff and a `package.json` script removal, not a code change.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Parity only | Each endpoint reproduces Express behavior exactly — no added streaming, retry, or formatting changes |
| One consumer, inline extraction | `review` fence-stripping and `lint-braindump` JSON parsing stay inline; no shared utility for a single consumer |
| Adapter boundary preserved | All four new routes call `chain/adapter.py`; none import from `chain/providers/*` |
| OpenAPI contract drives DTOs | Four new endpoint pairs (request + response) added to `flask/openapi.yaml`; Pydantic models regenerated, never hand-authored |
| Prompt functions stay pure | Prompts are already in `flask/modules/ai/prompts/` as argument-in, string-out functions; route handlers call them, do not contain them |

---

## System Boundaries

### What This System Includes

- Route handlers for `iterate`, `lint-braindump`, `review`, and `generate-spec` in `flask/modules/ai/routes.py`
- OpenAPI entries and generated Pydantic DTOs for each new request/response shape in `flask/openapi.yaml` and `flask/dtos/models.py`
- Inline JSON extraction logic specific to `lint-braindump` (`{ready, flags}`) and `review` (`{scores, issues}` with fence-stripping)
- `proxy.conf.json` update adding four new Flask routes and removing the Express fallback
- `package.json` script update removing Express from `dev` and retiring the `api` script

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Shared JSON fence-stripping utility | `review` is the only consumer; extract when a second consumer materialises |
| Retry/backoff on AI calls | No named production failure case; the right budget comes from a real failure, not anticipation |
| Streaming for migrated endpoints | Express served these buffered; Flask matches that behavior; streaming is a separate feature decision |
| Express as a post-migration fallback | A fallback extends the dual-runtime maintenance surface; retire cleanly |
| `generate` endpoint | Already specced in Phase 2 work; out of scope per the Epic |

---

## Component Design

### `flask/modules/ai/routes.py` — AI Route Handlers

**Purpose**: Route boundary for all AI text operations. Validates incoming requests, delegates to `chain/adapter.py`, and returns typed responses. The four new handlers join the existing `rewrite` handler in this file — they share its error-handling contract (`ServiceError` raised, not caught at the route) and its DTO validation pattern.

**Key Parts**:
- `IterateRequest` / `IterateResponse` — request carries base document and instruction; response carries transformed text and latency
- `LintBraindumpRequest` / `LintBraindumpResponse` — response shape is `{ready: bool, flags: list}`; JSON parsing from Claude's output is inline in this handler
- `ReviewRequest` / `ReviewResponse` — response shape is `{scores: dict, issues: list}`; fence-stripping (`re.sub` on markdown code fences) is inline here; raw-string fallback matches Express behavior
- `GenerateSpecRequest` / `GenerateSpecResponse` — route is a passthrough; Claude's raw text response (containing `===FILE: filename===` markers) is returned as-is; no JSON wrapping

**Consumed by**: Tasks 1–4 from the Epic.

**Patterns**: Route-as-boundary (validate DTO → delegate → return); `ServiceError` raised on `ProviderError`, mapped by `create_app.py`'s registered handler.

### `flask/openapi.yaml` + `flask/dtos/models.py` — Contract and Generated DTOs

**Purpose**: `openapi.yaml` is the single source of truth for all request/response shapes. `dtos/models.py` is generated from it — never edited by hand. Adding an endpoint means adding its schema to `openapi.yaml` and regenerating; CI fails if the committed DTO file would change after regeneration, catching drift before merge.

**Key Parts**:
- Four new path entries (`/api/ai/text/iterate`, `/api/ai/text/lint-braindump`, `/api/ai/text/review`, `/api/ai/text/generate-spec`) with request and response schemas
- Corresponding Pydantic v2 models generated to `flask/dtos/models.py` by `datamodel-codegen`

**Consumed by**: Route handlers in `routes.py` (validate requests, construct responses); `make dto` target in Makefile; CI `make ci` check.

### `proxy.conf.json` — Angular Proxy Routing

**Purpose**: Maps Angular dev-server traffic to Flask or Express by path prefix. Today, six explicit paths go to Flask (3101); everything else falls to Express (3100). As each endpoint migrates, its path joins the explicit list. After Task 4, the fallback `/api` → 3100 entry is removed.

**Key Parts**:
- Explicit Flask entries for `/api/ai/text/iterate`, `/api/ai/text/lint-braindump`, `/api/ai/text/review`, `/api/ai/text/generate-spec` — added in Task 4 (atomically with the Flask routes, before Express fallback removal)
- Fallback Express entry removed in Task 5

**Consumed by**: Angular dev server (all frontend → backend traffic in local development); Task 5 from the Epic.

### `flask/modules/chain/adapter.py` — AI Provider Adapter (Unchanged)

**Purpose**: The sole import boundary for AI generation. Feature routes call `adapter.generate()`, `adapter.rewrite()`, or context-wrapped variants. Provider selection (`CHAIN_PROVIDER` env var) is resolved here — route code never sees whether Claude SDK or the CLI fallback is active. This component is not modified by this migration; it gains four new callers.

**Key Parts**:
- `generate(prompt, system)` — used by `iterate`, `lint-braindump`, `review`, `generate-spec` routes
- `with_context(builder, principles)` — wraps generation with injected builder and principles context where the prompt requires it
- `chain/providers/` — implementations behind the adapter; never imported directly by feature code

**Consumed by**: All four new route handlers in `modules/ai/routes.py`; existing `rewrite` handler; structural test that enforces the no-direct-provider-import invariant.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Flask (Python) | Already owns four of five AI text endpoints and all CRUD; parity migration, not a stack change |
| AI | Anthropic SDK via `chain/adapter.py` | SDK gives typed exceptions, token metrics, and no subprocess overhead; CLI spawn is the no-key fallback |
| Contract | OpenAPI YAML + `datamodel-codegen` | One schema, both sides always in sync; drift caught by CI before merge |
| Frontend proxy | `proxy.conf.json` (Angular CLI) | Existing mechanism; two-line change per endpoint added, one-line removal to retire Express |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Inline JSON parsing for `lint-braindump` and `review` | One consumer each; extracting a utility for a single caller is premature abstraction — the second caller is the trigger | If a third endpoint needs fence-stripping, the pattern is in two places rather than one; accept that cost until the signal arrives |
| `generate-spec` as raw text passthrough | Angular parser splits on `===FILE: filename===` exact string; JSON wrapping would break the parser contract and require a frontend change | Response is opaque text, not a typed DTO — the acceptance test is behavioral (Angular parser splits correctly), not schema-validated |
| Add proxy entries atomically with Flask routes in Task 4 | Flask routes and proxy update go in one commit; a Flask route with no proxy entry means Angular still hits Express for that path | Requires both files in one commit; the alternative (proxy first, route second) leaves the proxy pointing at a 404 for the window between commits |
| No Express fallback post-migration | A fallback extends the dual-runtime maintenance surface and obscures routing bugs | Any path not yet migrated would silently hit Express; removing the fallback makes missing migrations visible immediately |
| Tasks 2 and 3 parallelisable after Task 1 | `iterate` establishes the module pattern (DTO shape, route structure, error handling); `lint-braindump` and `review` are independent once the pattern exists | Neither Task 2 nor 3 can start cold — Task 1 must be committed first so the executor follows an established pattern, not infers one |

---

## Patterns

### Route-as-Boundary

**When to use**: Every Flask route handler in this migration.

**How it works**: The route handler does exactly three things — validate the incoming request against a Pydantic DTO, delegate to `chain/adapter.py`, and return the typed response DTO. It raises `ServiceError` on failure; it does not catch. The registered `errorhandler` in `create_app.py` maps `ServiceError` to a consistent `{"error": message}` envelope with the right status. Per-route error handling is the pattern that produced N different 500 shapes in Express; this pattern eliminates that.

**Example**: `review` route — validates `ReviewRequest` DTO at the boundary, calls `chain.adapter.generate()` with `review_prompt(doc)`, parses the response inline (fence-strip → `json.loads`), constructs `ReviewResponse`, returns it. If `json.loads` fails, raises `ServiceError("review_parse_failed", 502)` — the errorhandler emits the envelope.

### Prompt-as-Pure-Function

**When to use**: Every AI call in `modules/ai/`.

**How it works**: Prompt functions in `flask/modules/ai/prompts/` take document content (or other plain data) as arguments and return a string. No I/O, no HTTP, no imports from `chain/`. This makes prompts testable without spinning up Flask or hitting the AI provider — the existing `test_prompts.py` tests this pattern and the four new prompt functions are already present.

**Example**: `generate_spec_prompt(braindump)` is a pure function; the `generate-spec` route calls it, passes the result to `chain.adapter.generate()`, and returns the raw string response. The prompt function is responsible for the `===FILE: filename===` marker format; the route is responsible for passing Claude's output through unchanged.

### Adapter Isolation

**When to use**: Any code in `modules/` that needs AI generation.

**How it works**: `chain/adapter.py` is the only import path for AI functionality. Route code imports `from flask.modules.chain.adapter import generate, with_context` — never from `chain.providers.claude` or `chain.providers.cli` directly. The structural test in `flask/modules/ai/tests/` greps for direct provider imports and fails if any appear. Provider selection is an env-var concern resolved inside the adapter; feature code is indifferent to it.

---

## Execution Flow

```
[Phase 1 — Establish Pattern]
  Task 1: iterate ──────────────────────────────────┐
                                                     │
[Phase 2 — Parallel Port]                           ▼
  Task 2: lint-braindump ──┐         (pattern confirmed)
  Task 3: review ──────────┤
                           ▼
[Phase 3 — Highest-Risk Port]
  Task 4: generate-spec ──────────────────────────┐
           (proxy update atomic with Flask route)  │
                                                   ▼
[Phase 4 — Retirement]
  Task 5: Express retired ─────────────────── Done
           (fallback removed, process stopped)
```

Task 1 must complete before Tasks 2 and 3 begin — it establishes the DTO, route, and error-handling pattern the parallel tasks follow. Tasks 2 and 3 have no dependency on each other and can proceed in parallel. Task 4 depends on both because `generate-spec` is the highest-contract-risk endpoint and should not ship until the simpler pattern is confirmed working. Task 5 is a config-only retirement that follows Task 4's smoke-test sign-off.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview