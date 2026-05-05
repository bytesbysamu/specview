# Phase 2 Brain Dump — AI Operations for Flask Backend

## What This Is

Phase 1 delivered a tested Flask backend that serves the Angular frontend's project CRUD and context file surfaces identically to Express. Phase 2 ports the AI text capabilities — the surface the editor's operation bar and bootstrap modal depend on. This is not a line-for-line port of server.js; it is a capability description with the Angular contract locked and the implementation open.

## Current Angular Contract (must not break)

The Angular frontend talks to these endpoints today. The Flask backend must accept the same request shapes and return the same response shapes. No Angular changes are planned for Phase 2.

### Text Operations

**POST /api/ai/text/rewrite**
- Request: `{ text: string, instructions: string }`
- Response: `{ text: string, latencyMs: number }`
- Angular uses: rewrite (custom instruction), expand, compress, clarify, formalize — all go through this same endpoint with different instruction strings

**POST /api/ai/text/generate**
- Request: `{ prompt: string, tone?: string }`
- Response: `{ text: string, latencyMs: number }`
- Angular uses: arbitrary prompt generation; the bootstrap pipeline (new-project component) drives all spec file generation through this endpoint

**POST /api/ai/text/iterate**
- Request: `{ baseSpec: string, currentContent: string }`
- Response: `{ text: string, latencyMs: number }`
- Angular uses: "Iterate" button on a spec — merges user's current edits with the canonical base spec structure

**POST /api/ai/text/generate-spec**
- Request: `{ input: string }`
- Response: `{ text: string, latencyMs: number }`
- Angular uses: bootstrap modal, passes brain dump text, expects back a multi-file string with `===FILE: filename===` markers. The Angular parser splits on those markers to write individual files.

### Quality and Utility Operations

**POST /api/ai/text/review**
- Request: `{ documents: { [name: string]: string } }`
- Response: `{ review: object | string, latencyMs: number }`
- Returns quality scores across 6 dimensions; Angular parses the review object for display.

**POST /api/ai/text/lint-braindump**
- Request: `{ braindump: string }`
- Response: `{ advisory: object, latencyMs: number }`
- Called in the bootstrap flow before spec generation. Returns readiness flag and structured advisory JSON.

**POST /api/ai/text/scan**
- Request: `{ workspacePath: string }`
- Response: `{ content: string, latencyMs: number }`
- Walks the filesystem at the given path, generates codebase.md content, saves it server-side to the codebase context file.

## Capabilities to Preserve

### 1. Prompt-In / Text-Out Adapter

Every AI endpoint is a thin shell: validate request → build prompt → call AI provider → return text. The chain module (already ported in Phase 1) is the provider layer. Phase 2 wires the HTTP surface to that layer.

What to keep:
- Provider is swappable at runtime: Claude SDK, CLI subprocess, mock. The environment variable determines which one runs.
- All endpoints return `{ text, latencyMs }` — consistent shape regardless of provider.
- Error responses are `{ error: string }` with appropriate status codes.

What can change:
- Express used inline prompt strings; Flask can put prompts in dedicated functions or a prompts module. Whatever keeps the business logic readable.
- The mock provider currently lives in-memory in server.js. In Flask it lives in the chain module already.

### 2. Context Injection

Three endpoints (generate, iterate, generate-spec) inject server-side context files into the prompt before calling the AI provider. The context files are:
- Builder profile (who the user is, their preferences)
- Architecture principles (non-negotiable constraints)
- Reference files (cross-project code the spec can cite)

What to keep:
- Context is read from the filesystem at request time, not cached.
- Context is injected into the prompt as labeled markdown sections.
- If a context file is absent or empty, the section is omitted silently.

What can change:
- Express hardcoded the file paths as constants. Flask can use the context module already built in Phase 1 — those same files, just loaded through the existing read functions.

### 3. Multi-File Output Parsing (generate-spec)

The generate-spec endpoint asks the AI to produce multiple files in a single response using `===FILE: filename===` markers. The server returns the raw text; Angular parses it into individual files.

What to keep:
- The marker format `===FILE: filename===` must stay exactly as-is — Angular's parser depends on it.
- The server returns raw text. It does not parse or split the files — that is Angular's job.
- Response shape is `{ text, latencyMs }` same as all other text endpoints.

What can change:
- The prompt template inside generate-spec can be restructured. The five-file scaffold (spec-index, analysis, epic, architecture, timeline) is the current default; that can be extracted to a template file if cleaner.

### 4. JSON-Structured Responses (review, lint-braindump)

Two endpoints expect the AI to return valid JSON embedded in its text response. The server attempts to extract and parse the JSON; if parsing fails it returns the raw text.

What to keep:
- Attempt JSON extraction with regex `{[\s\S]*}` first; fall back to `{ raw: text }` on parse failure. Angular handles both shapes.
- Response envelope: `{ review: object|string, latencyMs }` for review; `{ advisory: object, latencyMs }` for lint.

What can change:
- Python's `json.loads` + try/except is a cleaner implementation than the JS equivalent.

### 5. Codebase Scan (scan)

Takes a local filesystem path, walks it to collect file tree + source file heads + entry points, builds a structured prompt, calls the AI provider, saves the result to the codebase context file, returns the content.

What to keep:
- The scan prompt must NOT ask the model to write files — the Claude CLI interprets write intent as a tool call. The server persists the result.
- After successful scan, the server writes the result to the codebase context file path (same path the context module reads from in Phase 1).
- The response is `{ content: string, latencyMs }`.

What can change:
- The file walker is currently inline JavaScript. Python's `os.walk` or `pathlib` is a natural replacement with no behavior change.
- The scan prompt template can live in a `prompts/` module.

### 6. Task Implementation / SSE (implement)

**OUT OF SCOPE FOR PHASE 2.** The `/api/ai/implement` endpoint uses SSE streaming and spawns Claude CLI in a Docker container. It is the most complex endpoint and has no dependency from Phase 2's other endpoints. It ships in Phase 3 once AI text is proven on Flask.

## Explicitly Out of Scope

- `/api/ai/implement` — SSE streaming, container execution, Phase 3
- Walker module beyond what scan needs — Phase 3 when the scan endpoint is tested
- Streaming on any text endpoint — `text/event-stream` is not called by Angular today; all text operations are request/response
- Prompt versioning or A/B testing — no current consumer
- Rate limiting or token counting — no current consumer
- New operation types (summarize, translate, etc.) — no current Angular caller

## Implementation Notes

### Provider Selection

The chain module in Phase 1 has three providers: `claude_sdk`, `cli`, `mock`. Phase 2 routes each endpoint through the adapter. The adapter selects the provider based on the `AI_PROVIDER` env var. No new providers needed.

### Prompt Templates

Express built prompts inline in route handlers. Flask can do the same or extract prompts into a `prompts/` module. The criterion: prompts are testable in isolation. A function that takes context dicts and returns a string is easier to unit test than a route handler that mixes HTTP concerns with prompt assembly.

### Concurrency

Express is async by default. Flask with gunicorn workers handles the same load. Claude CLI subprocess calls are slow (2–10s); that is acceptable for the editor's non-streaming operations.

### Test Strategy

Each endpoint needs:
1. A unit test for the prompt builder (no AI call, assert the injected context appears correctly)
2. An integration test against the mock provider (asserts response shape and latency field)
3. The Angular frontend pointed at Flask on 3101 as the final acceptance check

Phase 1's pytest patterns apply directly.
