# Spec Doc Flask API — Phase 2: AI Text Operations

## What

Wire the Flask backend's chain module (already ported in Phase 1) to the 7 AI text endpoints the Angular frontend calls today. Phase 1 proved the non-AI surface — projects, context files, health. Phase 2 proves the AI surface. The Angular frontend must not change: same 7 endpoint paths, same request/response shapes, same `{ text, latencyMs }` envelope.

The 7 endpoints and their callers:

- `POST /api/ai/text/rewrite` — `ai.service.ts` rewrite(), expand(), compress(), clarify(), formalize(). All five Angular operations send to this one endpoint with different instruction strings. Request: `{ text, instructions }`. Response: `{ text, latencyMs }`.
- `POST /api/ai/text/generate` — `ai.service.ts` generate(), and every step of the bootstrap pipeline in `new-project.component.ts` (analysis, epic, architecture, task guides). Request: `{ prompt, tone? }`. Response: `{ text, latencyMs }`.
- `POST /api/ai/text/iterate` — Iterate button in the editor. Merges user edits back into the canonical base spec structure. Request: `{ baseSpec, currentContent }`. Response: `{ text, latencyMs }`.
- `POST /api/ai/text/generate-spec` — Bootstrap modal. Input is a brain dump string. Output is multi-file text with `===FILE: filename===` markers — Angular parser splits on those markers and writes individual files. Hard contract on the marker format. Request: `{ input }`. Response: `{ text, latencyMs }`.
- `POST /api/ai/text/review` — Quality gate in `new-project.component.ts`. Returns 6-dimension JSON score; Flask must attempt JSON extraction and fall back to raw string. Request: `{ documents: { [name]: string } }`. Response: `{ review: object|string, latencyMs }`.
- `POST /api/ai/text/lint-braindump` — Bootstrap modal pre-flight. Readiness + flags JSON. Request: `{ braindump }`. Response: `{ advisory: object, latencyMs }`.
- `POST /api/ai/text/scan` — Codebase scan button. Walks local filesystem at given path, returns generated codebase.md content, saves it to the codebase context file server-side. Request: `{ workspacePath }`. Response: `{ content, latencyMs }`.

All 7 route through the chain adapter at `modules/chain/adapter.py` (already ported in Phase 1). The adapter's generate() covers 6 endpoints; rewrite() covers 1. Provider is selected by `AI_PROVIDER` env var (claude_sdk | cli | mock).

## Why now

Phase 1 is live and validated — Flask on 3101 serving 67 projects, 94 tests passing. The chain module is sitting idle: adapter, three providers, file_parser, context_loader — all ported, all tested, nothing wired to HTTP yet. The Angular operation bar (rewrite/expand/compress/clarify) and bootstrap modal are hitting dead routes. Phase 2 closes that gap. The only remaining surface after Phase 2 is the SSE streaming implement endpoint, which has a Docker dependency and ships in Phase 3.

Context injection for generate, iterate, and generate-spec uses the context module already built in Phase 1 — `modules/context/service.py` read_context() for builder, principles, and references files. No new infrastructure needed; this is a wiring task.

## What's missing

Three open questions before the first route is written:

- **Module name**: `modules/ai/` or `modules/text/`? The Express server grouped everything under `/api/ai/text/` but the Flask blueprint only needs a URL prefix — the module path is independent. Naming decision shapes `create_app.py` ENABLED_MODULES entry and import paths.
- **Prompt colocation**: Express built prompts inline in route handlers (server.js:667–693, 718–1000). Flask can do the same or extract to a `prompts/` submodule. Criterion: prompt functions must be unit-testable without HTTP. Pure functions (context dicts → string) are easier to assert than route handler internals.
- **Scan prompt constraint**: The scan prompt must NOT ask the model to write files — Claude CLI interprets write intent as a tool call and returns a permission stub instead of content. Express added a `looksLikeCliRefusal()` check (server.js:1231–1243) and returns 502 on detection. Flask needs the same guard.

## Explicitly out of scope

- `POST /api/ai/implement` — SSE streaming + Docker container execution. Phase 3. No Angular caller today except the implementation runner, which isn't part of normal editor flow.
- Streaming on any text endpoint — Angular's HTTP calls are all request/response. No `text/event-stream` consumer exists.
- New operation types — no Angular caller, no scope.
- Rate limiting, token counting, retry/backoff — no current consumer.
