# Solution Architecture: Spec Doc Flask API — Phase 2: AI Text Operations

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

Phase 2 is a wiring task, not a build task. The chain adapter, three providers, context loader, and file parser are all implemented and tested from Phase 1. The Angular frontend already sends requests to the right paths. The gap between them is a thin route layer — seven handlers that validate input, inject context, call the adapter, and return normalized envelopes. No new infrastructure is introduced.

The central design choice is keeping the route layer as shallow as possible by moving all prompt construction out of route handlers and into a `prompts/` submodule of pure functions. Route handlers should read like a protocol: validate → load context → call adapter → serialize response. The prompt logic — which is what actually changes when product behavior evolves — lives separately, testable in isolation without spinning up HTTP.

Context injection is the one place where the route layer must reach outside itself. The generate, iterate, and generate-spec endpoints benefit from builder and principles context already captured in the context module. That injection happens at the adapter boundary, not inside prompt functions, preserving the invariant that prompt functions remain pure and context-free.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Routes are thin | Each route handler does exactly four things: validate input, load context if needed, call chain adapter, return envelope. Business logic belongs in prompts/. |
| Prompts are testable code | Prompt functions are pure: context dicts → string. No HTTP fixture required to assert prompt shape or content. |
| Adapter boundary is mandatory | All 7 routes call `chain.adapter.generate()` or `chain.adapter.rewrite()`. No route imports directly from `chain.providers.*`. |
| Explicit fallback over silent failure | Review and lint-braindump parse JSON from model output; if parsing fails, raw string is returned rather than 500. The caller handles ambiguity. |
| Guard at the server boundary | The CLI-refusal guard on scan catches a known failure mode from Claude CLI's tool-use behavior and converts it to a meaningful 502 rather than returning garbage content to the Angular client. |

---

## System Boundaries

### What This System Includes

- `modules/ai/` Flask blueprint — URL prefix `/api/ai/text/`, registered in `create_app.py` ENABLED_MODULES
- `modules/ai/routes.py` — 7 route handlers; thin wrappers over chain adapter
- `modules/ai/prompts/` — pure prompt-construction functions; one per endpoint family; unit-testable without HTTP
- CLI-refusal guard — detects Claude CLI permission stubs in scan responses; returns 502
- Context injection — generate, iterate, and generate-spec routes call `modules/context/service.py read_context()` before constructing prompts
- JSON extraction — inline parsing with raw-string fallback for review and lint-braindump response envelopes

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| `POST /api/ai/implement` | Requires SSE streaming + Docker container execution. No Angular caller in normal editor flow. Re-scope when implementation runner is built in Phase 3. |
| Streaming on text endpoints | Angular's `ai.service.ts` uses standard HTTP requests; no `text/event-stream` consumer exists. Adding SSE here ships infrastructure with no caller. |
| Rate limiting / token counting | No usage dashboard, no second product sharing this API. One consumer today. Re-scope when a second product lands or a usage cap is needed. |
| Retry / backoff machinery | The `anthropic` SDK already provides `max_retries=2, timeout=60` at the provider layer (ported from humanize-me). Adding application-level retry wraps working infrastructure for no gain. |
| Shared prompt registry / versioning | Each prompt has one consumer today. Promote to a registry when a second consumer appears and the duplication would be real, not hypothetical. |
| New operation types | No Angular caller exists. Adding endpoints without callers is infrastructure before features. |

---

## Component Design

### `modules/ai/` Blueprint

**Purpose**: Flask registration unit for the AI text surface. Provides the URL prefix and collects all 7 route handlers in one module so `create_app.py` can enable or disable the entire AI surface with a single ENABLED_MODULES entry.

**Key Parts**:
- `blueprint` — Flask Blueprint with url_prefix `/api/ai/text`; consumed by `create_app.py`
- `routes.py` — 7 handler functions; each follows the validate → context → adapter → envelope protocol; all 7 are consumers of the chain adapter

**Why a blueprint over a flat routes file**: Blueprints make ENABLED_MODULES meaningful — the Phase 1 pattern already uses this for `context` and `projects`. Consistency matters more than the marginal overhead of one extra file.

### `modules/ai/prompts/`

**Purpose**: Extract prompt construction from route handlers so prompts can be asserted in unit tests without an HTTP fixture. This is the key structural decision for testability.

**Key Parts**:
- `rewrite_prompt(text, instructions)` — consumed by the `/rewrite` route; builds the instruction-driven transform prompt; no context injection (rewrite is caller-driven, not builder-driven)
- `generate_prompt(prompt, builder, principles, tone)` — consumed by `/generate`; injects builder and principles at the prompt boundary, not inside the adapter
- `iterate_prompt(base_spec, current_content, builder, principles)` — consumed by `/iterate`; merges editing delta into canonical structure
- `generate_spec_prompt(input, builder, principles)` — consumed by `/generate-spec`; the `===FILE: filename===` marker contract is enforced here, in the prompt, not in the route handler
- `review_prompt(documents)` — consumed by `/review`; requests 6-dimension JSON score
- `lint_braindump_prompt(braindump)` — consumed by `/lint-braindump`; requests readiness + flags JSON
- `scan_prompt(tree_text)` — consumed by `/scan`; describes the filesystem snapshot for summarization; explicitly must NOT contain write instructions (rationale: Claude CLI converts write intent into a tool-use permission stub rather than text content)

**Why pure functions over inline route logic**: The Node.js Express server built prompts inline in route handlers (`server.js:667–693, 718–1000`). That works at the scale of one file, but it means the only way to test prompt shape is to spin up an HTTP server and parse the request. Pure functions allow a unit test to call `generate_spec_prompt(input, {}, {})` and assert the output contains the marker format without any HTTP fixture. Given that prompt correctness is the highest-leverage failure mode in this system, that testability is worth the extra submodule.

### CLI-Refusal Guard

**Purpose**: Defend against a known failure mode specific to the `cli` provider: when a prompt implies a file-write intention, Claude CLI invokes a write tool and returns a permission stub (`"I don't have permission to..."` or similar) rather than the expected text content. Without detection, that stub becomes the codebase.md content the Angular client saves and displays.

**Key Parts**:
- `looks_like_cli_refusal(text)` — single predicate; consumed by the `/scan` route handler; checks for the permission-stub pattern ported from `server.js:1231–1243`
- `/scan` route — calls the predicate on the adapter response; returns 502 with a structured error if triggered; the 502 signals to the Angular client that the scan failed at the AI layer, not the HTTP layer

**Why 502 over 200 with error field**: The Angular client maps HTTP status codes to error states. A 502 triggers retry UX; a 200 with an error field in the body would silently save garbage content. The distinction matters for user experience.

**Why the guard lives in the route, not the adapter**: The refusal pattern is specific to the `cli` provider and the scan use case — it is not a general chain failure. Putting it in the adapter would generalize a scan-specific guard to every route, making the adapter aware of caller intent. Route-level detection keeps the adapter provider-agnostic.

### Context Injection at Generate Routes

**Purpose**: Apply builder profile and feature-specific principles to generated content without embedding that logic in individual prompt functions.

**Key Parts**:
- `modules/context/service.py read_context()` — already implemented in Phase 1; returns builder, principles, and references dicts; consumed by the `/generate`, `/iterate`, and `/generate-spec` route handlers before prompt construction
- Chain adapter `generate()` signature — accepts `user` and `feature` kwargs; the adapter's `_effective_system()` prepends context blocks to the system prompt (ELA Adapter pattern, ported from `spec-doc/server.js aiAdapter`)

**Why context injection at the route, not the prompt function**: Prompt functions are pure (context dicts → string). If context injection happened inside prompt functions, the functions would need to call `read_context()`, making them impure and untestable without filesystem state. Route handlers call `read_context()` once, pass the result as arguments to prompt functions, and then pass the combined system prompt to the adapter. Prompt functions stay assertable in isolation.

**Which routes need context injection**: generate, iterate, generate-spec. Rewrite is instruction-driven by the user — injecting builder context into a user-authored rewrite instruction would change user-facing behavior unpredictably. Review and lint-braindump evaluate documents rather than generating builder-aligned content — context injection is not applicable. Scan generates a structural summary, not builder-aligned output.

### JSON Extraction Layer

**Purpose**: The review and lint-braindump endpoints ask the model to return JSON, but model output is not guaranteed to be clean JSON — it may include reasoning preamble, code fences, or natural language explanation. Angular expects a structured object. The extraction layer bridges that gap.

**Key Parts**:
- `extract_json(text)` — single function; attempts to parse raw text as JSON; on failure, scans for the first `{` / `[` to `}` / `]` balanced substring; falls back to returning the raw string; consumed by `/review` and `/lint-braindump` route handlers only

**Why inline, not a shared utility**: Two consumers today (review, lint-braindump). The extraction logic is ~10 lines. Promoting it to a shared utility for two callers adds a file without removing duplication. When a third consumer appears, extract then. The current shape avoids premature abstraction.

**Why raw-string fallback over 500**: A 500 on JSON parse failure means any model output variation — a preamble sentence, a trailing explanation — breaks the bootstrap flow. The raw-string fallback degrades gracefully: Angular receives something it can display, the quality signal is still usable even if unparsed, and the product keeps functioning while the prompt is iterated.

### Generate-Spec Marker Contract

**Purpose**: The Angular `new-project.component.ts` parser splits multi-file output on exact `===FILE: filename===` markers. This is a hard contract between the backend prompt and the frontend parser. Any deviation in marker format produces garbled files or silent data loss.

**Key Parts**:
- `generate_spec_prompt()` — the marker format is expressed in the prompt instruction, not in route handler post-processing; the prompt tells the model exactly how to delimit files
- `/generate-spec` route — passes model output directly to the response envelope without transformation; it is the prompt's responsibility to produce correct markers, not the route's

**Why enforce the contract in the prompt, not in post-processing**: Post-processing the model output to impose markers would require parsing partially-structured text with heuristics — fragile. Expressing the format as a prompt constraint means the model produces markers directly. If the model deviates, the failure is visible in the prompt, not buried in a string-manipulation function.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Flask blueprint | Matches Phase 1 pattern; `create_app.py` ENABLED_MODULES already handles blueprint registration |
| AI (batch) | `chain.adapter.generate()` / `chain.adapter.rewrite()` | Phase 1 adapter already ported; provider selection via `AI_PROVIDER` env var; no new infrastructure |
| AI (provider) | `claude_sdk` (default), `cli`, `mock` | `claude_sdk` is the production path; `cli` for local dev; `mock` for tests without API calls |
| Context | `modules/context/service.py` | Already implemented and tested in Phase 1; `read_context()` returns builder, principles, references |
| Filesystem scan | Python `os.walk` | Stdlib; no dependencies; the scan output is a codebase summary, not a search index — no need for a more capable tool |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Module name: `modules/ai/` | Mirrors the URL prefix `/api/ai/text/`; makes the ENABLED_MODULES entry self-documenting and consistent with how the Express server organized the same surface | `modules/text/` was the alternative — rejected because "text" describes the data shape, not the capability; the capability is AI-powered operations |
| Prompts in `prompts/` submodule, not inline | Prompt correctness is the highest-leverage failure mode; pure functions allow unit tests without HTTP fixtures | One extra submodule and import hop; the cost is minimal against the gain in testability |
| No streaming on text endpoints | Angular has no `text/event-stream` consumer; the chain adapter already supports `stream()` — it can be wired later with zero infrastructure changes | Latency on long generate calls is higher without streaming; acceptable for v1 since the bootstrap modal shows a loading state |
| JSON extraction with raw-string fallback | Prevents the bootstrap flow from breaking on model output variation; the quality signal is still usable even if unparsed | Review score display in Angular must handle both object and string shapes; that's Angular-side complexity, but it's bounded and preferable to a hard failure |
| CLI-refusal guard at route level, not adapter level | The refusal pattern is scan-specific; the adapter should remain provider-agnostic | If the CLI provider develops additional refusal patterns in other endpoints, the guard would need to be replicated; acceptable given that `claude_sdk` is the production provider |
| Context injection at route, not prompt function | Keeps prompt functions pure and unit-testable; context loading (filesystem reads) is an I/O side effect that belongs at the route boundary | Routes must explicitly pass context to prompt functions — slightly more verbose call sites |

---

## Patterns

### Adapter Boundary (ELA Pattern #1)

**When to use**: Any route handler that needs AI capability.

**How it works**: All 7 routes call only `chain.adapter.generate()` or `chain.adapter.rewrite()`. No route imports from `chain.providers.*` directly. Provider selection, context prepending, and timing all happen inside the adapter. The structural test `test_featureModules_mustNotImportProvidersDirectly` enforces this at CI time.

**Example in this system**: The `/rewrite` route calls `chain.adapter.rewrite(system, prompt)`. The adapter selects the claude_sdk provider via `AI_PROVIDER`, prepends any applicable context via `with_context()`, calls `provider.create_message()`, and returns a `ChainResult`. The route never knows which provider ran.

### Validate → Context → Adapter → Envelope

**When to use**: Every route handler in `modules/ai/routes.py`.

**How it works**: Four steps, no exceptions. Validate request fields first (return 400 on missing required fields). Load context if this endpoint injects builder/principles (generate, iterate, generate-spec). Call the adapter with the constructed system and prompt strings. Serialize to `{ text, latencyMs }` (or `{ review, latencyMs }` / `{ advisory, latencyMs }` / `{ content, latencyMs }` for the three variant envelopes).

**Why this ordering matters**: Validating before loading context means no filesystem reads on malformed requests. Loading context before calling the adapter means the adapter always receives a complete system string — it does not need to fetch context itself.

### Pure Prompt Functions

**When to use**: All prompt construction in `modules/ai/prompts/`.

**How it works**: Functions accept only primitive values and dicts — no I/O, no imports from `modules.context`, no adapter calls. They return a string. Tests call them directly with fixture dicts and assert on string content.

**Example in this system**: `generate_spec_prompt(input, builder, principles)` takes the raw brain dump string and context dicts, returns the full system+user prompt string with `===FILE: filename===` instructions embedded. A test can call this with empty dicts and assert the marker instruction appears in the output.

---

## Execution Flow

```
Task 1: Module scaffold + prompt functions
  (no dependencies)
         │
         ▼
Task 2: Rewrite endpoint        Task 3: Generate family (5 endpoints)
  (smoke test for wiring)         (parallel with Task 2)
         │                                │
         └──────────── Task 4: Scan endpoint ─────────────┘
                         (parallel with 2 and 3)
```

Task 1 has no dependencies and must complete first — it establishes the blueprint, ENABLED_MODULES entry, and `prompts/` submodule that tasks 2, 3, and 4 import from. Tasks 2, 3, and 4 are fully parallel once Task 1 is done. Task 2 is the smoke test: if the rewrite endpoint works end-to-end against the Angular client with the `claude_sdk` provider, the wiring pattern is validated and tasks 3 and 4 proceed with low risk.

The CLI-refusal guard in Task 4 is independent of the generate family in Task 3 — both can be written and tested simultaneously. Task 4's dependency is only on the module scaffold (Task 1), not on Task 2 or 3.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview