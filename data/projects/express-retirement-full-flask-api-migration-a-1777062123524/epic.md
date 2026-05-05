# 🎯 Epic: Express Retirement: Full Flask API Migration: A

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Two runtimes mean two failure modes, two deployment configs, and two error shapes on the same API surface. Express was never the intended AI backend — Flask inherited the AI surface incrementally as endpoints migrated. Each half-migrated state was correct at the time; completing it eliminates the debt those correct decisions accumulated.

A single Flask runtime means one set of logs, one `ServiceError` handler, one test suite, and one process to restart. Future AI endpoint development starts from a clean, consistent baseline rather than a split one where the right place to add code depends on which endpoint you're near.

Express retirement is also the pre-condition for simplifying the Angular proxy: the fallback route exists only to cover Express. Once Flask owns all five AI text endpoints, the proxy becomes a straightforward mapping with no fallback surface and no cross-runtime inconsistency to debug.

**Value Proposition**: One backend, one error shape, one dev command — Express removed.

---

## Scope

### What This Epic Covers

- `POST /api/ai/text/iterate` migration — in-place document update given a base spec and user instruction
- `POST /api/ai/text/lint-braindump` migration — JSON readiness check (`{ready, flags}`)
- `POST /api/ai/text/review` migration — JSON score output (`{scores, issues}`) with inline fence-stripping
- `POST /api/ai/text/generate-spec` migration — multi-doc marker-delimited passthrough with Angular parser contract validation
- Express retirement — proxy fallback removal, process elimination, end-to-end smoke-test sign-off

### What This Epic Does NOT Cover

- ❌ `POST /api/ai/text/generate` — already specced in prior Phase 2 work; not in this scope
- ❌ Shared JSON fence-stripping utility — `review` is the only consumer; extract when a second consumer appears
- ❌ Retry/backoff on AI calls — no named failure case in this migration; defer until a route fails in production with a retriable error
- ❌ Behavior changes to any migrated endpoint — parity only; new behavior ships in a separate epic
- ❌ Express as a post-migration fallback — no stated benefit; retire cleanly

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Migrate `iterate` endpoint** | None | — | 1 day | High |
| 2 | **Migrate `lint-braindump` endpoint** | 1 | 3 | 0.5 days | High |
| 3 | **Migrate `review` endpoint** | 1 | 2 | 0.5 days | High |
| 4 | **Migrate `generate-spec` endpoint** | 2, 3 | — | 1 day | High |
| 5 | **Retire Express** | 4 | — | 0.5 days | High |

### Task 1: Migrate `iterate` endpoint

Port `POST /api/ai/text/iterate` to Flask: accepts a base document and user instruction, calls Claude via the Anthropic SDK, and returns transformed text. This endpoint goes first to establish the Flask module pattern — route, service method, prompt function, Pydantic DTO, `ServiceError` raise — that tasks 2 and 3 will follow.

**Port budget**: ~30 lines across route handler, service method, and prompt function — no streaming, no retry machinery, no shared utilities beyond what the existing `modules/ai` structure already exposes.

### Task 2: Migrate `lint-braindump` endpoint

Port `POST /api/ai/text/lint-braindump` to Flask: returns `{"ready": bool, "flags": [...]}` from Claude. The route validates the request DTO, calls Claude, and parses the JSON response inline — one consumer, so no shared utility is introduced here.

**Port budget**: ~25 lines — JSON parsing stays inline; no streaming; no fallback output format; the Pydantic response DTO enforces the `{ready, flags}` shape at the route boundary.

### Task 3: Migrate `review` endpoint

Port `POST /api/ai/text/review` to Flask: returns `{"scores": {...}, "issues": [...]}` with inline fence-stripping (`json.loads(re.sub(...))`) and a raw-string fallback matching Express behavior. The fence-stripping stays inline — `review` is the only consumer and extracting a utility for one consumer is premature.

**Port budget**: ~30 lines — fence-stripping inline; no shared JSON utility introduced; Pydantic DTO validates both request and response shape at the boundary.

### Task 4: Migrate `generate-spec` endpoint

Port `POST /api/ai/text/generate-spec` to Flask: the highest-contract-risk endpoint. Flask passes Claude's response as raw text — no JSON wrapping — so the Angular parser's `===FILE: filename===` split continues to work unchanged. The proxy update and Flask route ship atomically; the Angular parser successfully splitting the response is the acceptance test before this task is marked done.

**Port budget**: ~30 lines — the route is a passthrough; the prompt already enforces the marker format; no additional formatting logic is added in this task; validation is behavioral (smoke-test against the live Angular client), not structural.

### Task 5: Retire Express

Remove Express from the running stack: update the Angular proxy to drop the Express fallback route, remove Express start scripts from package.json, and smoke-test all four migrated endpoints end-to-end against Flask. Express is not left as a fallback — retire cleanly, no maintenance surface retained.

**Port budget**: Config changes only, no new code — proxy diff, package.json diff, and a smoke-test pass against each migrated endpoint on Flask port 3101.

---

## Success Criteria

This epic is complete when:

- ✅ All four endpoints (`iterate`, `lint-braindump`, `review`, `generate-spec`) return parity responses from Flask port 3101
- ✅ The Angular proxy routes all AI text endpoints to Flask; no traffic reaches Express
- ✅ `generate-spec` response splits correctly on `===FILE: filename===` in the Angular parser, confirmed by live smoke-test
- ✅ `review` returns valid JSON under both nominal and fence-wrapped Claude output; raw fallback confirmed
- ✅ `lint-braindump` returns `{"ready": bool, "flags": [...]}` with correct types under nominal output
- ✅ Express process is not started by `npm run dev`; no Express fallback route remains in the proxy

---

## Non-Goals

- ❌ Streaming for non-streaming endpoints — Express served these buffered; Flask matches that behavior; streaming is a separate feature decision
- ❌ Behavior changes to migrated endpoints — parity only; new behavior belongs in a separate epic
- ❌ Shared JSON fence-stripping utility — one consumer; extract when a second consumer exists
- ❌ Retry/backoff on AI calls — defer until a production failure teaches the right retry budget
- ❌ Express as a post-migration fallback — no stated benefit; eliminated, not preserved

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview