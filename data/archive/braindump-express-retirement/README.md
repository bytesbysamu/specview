# Brain Dump — Express Retirement: Full Flask API Migration

> **DONE** — completed via Epic 3 (`api/docs/epic-3-express-retirement/`).
> All 5 AI endpoints migrated to Flask; Express removed.
>
> Do not generate a spec from this file. The capability is shipped.
> Reference `api/docs/epic-3-express-retirement/README.md` for what landed.

---

## (Original brain dump below — do not act on)

## What

Complete the spec-doc-api Flask backend so Express (server.js) can be permanently retired. Angular should talk to Flask only — no fallback, no split routing.

**What's already on Flask (done):**
- All project CRUD (`/api/projects`)
- All context files (`/api/builder`, `/api/principles`, `/api/codebase`, `/api/references`)
- `POST /api/ai/text/rewrite`

**What's still on Express (migration target):**

Group A — AI text operations (5 endpoints, task 3 already specced in Phase 2):
- `POST /api/ai/text/generate` — free-form generation with builder + principles context
- `POST /api/ai/text/iterate` — update a doc in-place given base spec + instructions
- `POST /api/ai/text/generate-spec` — brain dump → `===FILE: filename===` delimited multi-doc
- `POST /api/ai/text/review` — JSON score output (`{scores, issues}`) with raw fallback
- `POST /api/ai/text/lint-braindump` — JSON readiness check (`{ready, flags}`)

Group B — Scan (1 endpoint, task 4 already specced in Phase 2):
- `POST /api/ai/text/scan` — filesystem tree → structured markdown; must refuse CLI re-invocation

Group C — Implement (SSE streaming, not yet specced):
- `POST /api/ai/implement` — SSE event stream; takes `{taskNum, taskName, projectContext, workspaceId}`; runs Claude in container (if `workspaceId` present) or local; emits `start`, `output`, `complete`, `error` events; keepalive every 15s; long-running (minutes)

Group D — Container management (4 endpoints, not yet specced):
- `GET /api/container/status` — checks Docker availability + image readiness
- `POST /api/container/:workspaceId/preview` — starts preview server in container, returns port
- `DELETE /api/container/:workspaceId/preview` — stops preview
- `DELETE /api/container/:workspaceId` — tears down workspace container

Group E — Cutover (no code, just wiring):
- Remove `/api` catch-all fallback from `proxy.conf.json`
- Angular routes 100% to Flask
- Express process retired (remove `npm run api`, remove from CLAUDE.md)

## Why now

Flask is live at port 3101. Angular proxy already routes known endpoints to Flask. The catch-all `/api → 3100` fallback is the only thing keeping Express alive. Every unported endpoint is a thread keeping the old process running. Once Groups A–D ship, Express has zero remaining consumers and can be deleted.

The implement + container endpoints are the only ones with non-trivial complexity (SSE, Docker SDK). The AI text group is prompt functions + route handlers — already proven by rewrite.

## What's missing / decisions to make

**SSE in Flask**: `flask.Response(stream_with_context(generator), content_type='text/event-stream')`. Generator yields `event: name\ndata: json\n\n` strings. No third-party package needed. Keepalive via a background thread or generator timeout.

**Implement endpoint — container vs local**: Express uses `spawn('claude', ...)` locally or a containerService wrapper for workspaceId runs. Flask should use `chain.adapter` for local (same as rewrite/generate), and `subprocess` or Docker SDK for container mode. Decision: keep container execution as a direct `docker exec` call via subprocess — no Docker SDK dependency until a second consumer needs it.

**Container management — Docker SDK vs subprocess**: Express uses a `containerService.js` module that wraps Docker CLI calls. Flask equivalent: `docker` Python SDK (`pip install docker`) gives typed responses and no subprocess shell injection risk. One module: `modules/container/service.py`.

**`generate-spec` marker format**: Angular parser splits on `===FILE: filename===` exact string. Flask must produce this exact format — no variation. Prompt already enforces it; route must pass response through unchanged (no JSON wrapping of the text).

**`review` JSON extraction**: Express does `JSON.parse(text)` with a raw-string fallback if Claude wraps in markdown fences. Flask: `json.loads(re.sub(r'^```json\n|```$', '', text.strip()))` — inline, not a shared utility (one consumer).

**Parity harness**: before retiring Express, run both backends against a fixed set of inputs and diff outputs. Five representative calls per endpoint family. Acceptance: same HTTP status, same response shape (not byte-identical text since LLM output varies).

## Explicitly out of scope

- SSE streaming for non-implement endpoints (generate, rewrite etc.) — these are fast enough synchronous; streaming adds complexity with no current Angular consumer
- WebSocket upgrade — no consumer
- Multi-user auth / rate limiting — not in current Express; out of scope here
- Deployment (Dockerfile, Coolify config) — separate DevEx epic
- Any new AI capability not currently in Express — pure port, no scope creep
- Migrating `server.js` git history into spec-doc-api — already handled via subtree merge
