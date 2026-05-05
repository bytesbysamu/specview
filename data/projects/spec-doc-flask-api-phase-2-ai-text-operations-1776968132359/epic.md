# Epic: Spec Doc Flask API — Phase 2: AI Text Operations

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The AI operations are what make Spec Doc a tool rather than a file browser. Rewrite, expand, compress, generate-spec, review — these are the actions a user performs dozens of times per session. Phase 1 proved the non-AI surface (projects, context, health) and left the chain module fully ported and tested. Phase 2 wires it to HTTP. Until it does, the operation bar is inert and the bootstrap modal returns 404s on every call.

The bootstrap pipeline — lint-braindump → generate-spec → review — is the highest-value user flow in the product. A solo founder drops a brain dump into the modal and gets a structured spec tree in seconds. That flow is the product's first-use promise. It is also the clearest validation signal: if a user completes bootstrap and opens the generated files, the core loop is proved. Phase 2 is the prerequisite for observing that signal at all.

Phase 2 is a wiring task, not a build task. The chain adapter, three providers, file_parser, and context_loader are implemented and tested. The Angular frontend already calls the right paths. The context module already exposes `read_context()` for builder, principles, and references injection. The only work is routes and prompts — no new infrastructure, no new contracts, unusually low risk for the value delivered.

**Value Proposition**: Activate the AI editor by wiring the already-built chain module to the 7 endpoint paths the Angular frontend already calls.

---

## Scope

### What This Epic Covers

- **`POST /api/ai/text/rewrite`** — Serves all 5 Angular text-transform operations (rewrite, expand, compress, clarify, formalize) with different instruction strings; single route, instruction-driven
- **`POST /api/ai/text/generate`** — Powers the `generate()` operation and each step of the bootstrap pipeline via `chain.adapter.generate()`
- **`POST /api/ai/text/iterate`**, **`/generate-spec`**, **`/review`**, **`/lint-braindump`** — Complete the generate family; review requires JSON extraction with raw-string fallback; generate-spec must produce `===FILE: filename===` markers the Angular parser depends on
- **`POST /api/ai/text/scan`** — Walks local filesystem at `workspacePath`, returns codebase.md content, saves to context file server-side; CLI-refusal guard returns 502 on permission-stub detection
- **Module naming resolution** — `modules/ai/` decided before any file is created (shapes `create_app.py` ENABLED_MODULES and all import paths)
- **Prompt colocation decision** — Prompts extracted as pure functions (context dicts → string), unit-testable without HTTP, location settled before routes are written

### What This Epic Does NOT Cover

- ❌ `POST /api/ai/implement` — SSE streaming + Docker container execution; no Angular caller in normal editor flow; scoped to Phase 3
- ❌ Streaming on any text endpoint — Angular uses request/response only; no `text/event-stream` consumer exists today
- ❌ Rate limiting, token counting, retry/backoff — no current consumer; re-scope when usage tracking or a second product sharing this API is added
- ❌ New operation types — no Angular caller exists; re-scope when a caller is built

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Module scaffold + prompt functions** | None | — | 0.5 days | High |
| 2 | **Rewrite endpoint** | 1 | 3, 4 | 0.5 days | High |
| 3 | **Generate family (5 endpoints)** | 1 | 2, 4 | 1 day | High |
| 4 | **Scan endpoint + CLI-refusal guard** | 1 | 2, 3 | 0.5 days | High |

### Task 1: Module Scaffold + Prompt Functions

Resolve the module name (`modules/ai/`), create the Flask blueprint, register it in `create_app.py` ENABLED_MODULES, and extract all prompt construction to a `prompts/` submodule as pure functions. No routes are wired in this task — it establishes the shape that tasks 2–4 import from and ensures prompts can be asserted in unit tests without an HTTP fixture.

**Port budget**: ~3 files, ~60 lines; no route handlers, no context injection calls, no provider-selection logic — those belong in tasks 2–4.

### Task 2: Rewrite Endpoint

Wire `POST /api/ai/text/rewrite` through `chain.adapter.rewrite()` using the `{ text, instructions }` request shape and `{ text, latencyMs }` response envelope. This is the smoke test for the entire wiring pattern — if rewrite works end-to-end against the Angular client with `claude_sdk`, tasks 3–4 follow the same path with low risk.

**Port budget**: ~30 lines in the route handler + 1 prompt function from task 1; no context injection (rewrite is instruction-driven; builder/principles context is not needed here).

### Task 3: Generate Family (5 Endpoints)

Wire `generate`, `iterate`, `generate-spec`, `review`, and `lint-braindump` — all route through `chain.adapter.generate()`. Context injection for `generate`, `iterate`, and `generate-spec` uses the existing `modules/context/service.py` `read_context()` — no new infrastructure. `review` requires inline JSON extraction with raw-string fallback (~10 lines). `generate-spec` must produce `===FILE: filename===` markers; the Angular parser splits on exact format.

**Port budget**: ~120 lines across 5 route handlers + 5 prompt functions; JSON extraction is inline per route, not a shared utility — one consumer today.

### Task 4: Scan Endpoint + CLI-Refusal Guard

Wire `POST /api/ai/text/scan` — stdlib filesystem walk at `workspacePath`, generated codebase.md content returned and saved to the context file server-side. The scan prompt must not ask the model to write files (Claude CLI returns a permission stub instead of content on write intent). Implement the CLI-refusal guard: detect the stub pattern, return 502.

**Port budget**: ~40 lines (route + walk + guard); stdlib `os.walk` only; no retry logic, no partial-result caching — the guard fires and the caller corrects the prompt, not the server.

---

## Success Criteria

This epic is complete when:

- ✅ All 7 `POST /api/ai/text/*` routes return correct response envelopes against the `mock` provider with zero Angular-side changes
- ✅ Angular operation bar (rewrite, expand, compress, clarify) produces transformed text end-to-end with `claude_sdk` provider
- ✅ Bootstrap modal completes the full lint-braindump → generate-spec → review flow and writes spec files to the project folder
- ✅ Scan endpoint returns codebase.md content, saves it to the context file, and the CLI-refusal guard returns 502 on permission-stub input
- ✅ All prompt functions are assertable in unit tests without an HTTP fixture (pure functions, no route setup required)
- ✅ Test count grows from the 94-test Phase 1 baseline by at least 35 (7 routes × ~5 assertions each)

---

## Non-Goals

- ❌ Streaming on text endpoints — Angular has no `text/event-stream` consumer; shipping SSE here is infrastructure with no caller
- ❌ Shared prompt registry or prompt versioning — each prompt has one consumer today; extract when a second consumer appears
- ❌ Token counting or cost attribution — no usage dashboard exists; add when a second product shares this API
- ❌ `POST /api/ai/implement` — SSE + Docker; ships in Phase 3 when the implementation runner is scoped as a capability

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview