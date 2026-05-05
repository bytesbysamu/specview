# Epic: Chain Primitive Port — From bubls `agent_runtime/` to spec-doc-api

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

The `/api/ai/text/generate-spec` endpoint already runs a four-step pipeline (`analysis → epic → architecture → spec-doc-spec`), but encodes it as a single Claude call with string markers. That approach has a hard ceiling: no streaming, no per-step observability, and no testability without running the full 30+ second call. Users stare at a blank loading state for the entire duration — not because the problem is hard, but because the structure isn't visible to the runtime.

Surfacing the pipeline as executable code delivers SSE streaming as a direct consequence. Each of the four steps emits progress events — output arrives as it's generated rather than in one batch at the end. The batch endpoint stays alive through a soak window, giving streaming time to prove itself before the fallback is removed.

The port also seeds the chain primitive that the next pipelined feature will draw from. `draft → review → revise` and `lint → suggest-fixes → apply` are both natural fits once the primitive exists. Building it now, against a real pipeline, calibrates its shape against one concrete data point instead of speculation.

**Value Proposition**: Replace a fragile 30-second black-box call with a testable, streaming four-step pipeline that shows users progress and gives the next feature a proven primitive to build on.

---

## Scope

### What This Epic Covers

- **Chain runner** (`flask/modules/chain/`) — `ChainDefinition`, `ChainStep`, `ChainEvent`, and `run_chain()`, ported from bubls with two explicit adaptations (no DB logging, no user object)
- **Prompt split** — `generate_spec_prompt()` decomposed into four independent step functions, each a pure callable receiving only the inputs its step needs; `===FILE:` marker instruction removed
- **`SPEC_CHAIN` declaration** — the four steps wired together with explicit input resolution
- **SSE endpoint** — `POST /api/ai/text/generate-spec/stream` returning `text/event-stream`; existing batch endpoint kept alive through the soak window
- **OpenAPI + DTO regen** — stream endpoint and `ChainEvent` schema declared in `openapi.yaml`; DTOs regenerated via `make dto`

### What This Epic Does NOT Cover

- ❌ **Batch endpoint removal** — deferred until streaming has ≥1 week of green dev traffic; separate PR
- ❌ **Angular SSE consumer** — `AiService` changes tracked in a separate epic
- ❌ **Signal-capture endpoint** — no UX consumer; trigger: A/B test requirement on prompt variants
- ❌ **Retry/backoff per step** — no failure data; trigger: first production rate-limit incident
- ❌ **Provider routing per step** — no cost signal; trigger: cost optimization becomes a named goal
- ❌ **Chain persistence / resumability** — in-memory only; trigger: a chain run exceeds server restart tolerance
- ❌ **Chain-call DB table** — structlog JSON to stdout is sufficient; trigger: token-aggregation query becomes too slow for log-grep

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Port chain runner** | None | — | 0.5d | High |
| 2 | **Split step prompts + declare SPEC_CHAIN** | 1 | — | 0.5d | High |
| 3 | **Add SSE streaming endpoint** | 1, 2 | — | 0.5d | High |
| 4 | **OpenAPI declaration + DTO regen** | 3 | — | 0.5d | High |

### Task 1: Port chain runner

Port `ChainDefinition`, `ChainStep`, `ChainEvent`, and `run_chain()` from bubls's `agent_runtime/runner.py` into `flask/modules/chain/`. The runner is the only layer that calls the chain adapter; no feature code touches adapter internals directly. Step failure emits an `error` event and halts the chain — unhandled exceptions inside the generator are caught and re-emitted before the stream closes, never truncated silently. Unit tests cover the full event sequence against a mock provider. See [Solution Architecture](./architecture.md) for the `ChainEvent` type decision and error-halt contract.

**Port budget**: ~80–100 lines across runner and tests; excludes DB logging (stdout via structlog), user-object threading, retry/backoff, and provider-routing — all of which require a second data point to calibrate.

### Task 2: Split step prompts + declare SPEC_CHAIN

Decompose `generate_spec_prompt()` in `flask/modules/ai/prompts/__init__.py` into four pure functions — one per step — each receiving only the inputs its step needs. Drop the `===FILE:` marker instruction; output framing is the runner's responsibility. Wire the four steps into `SPEC_CHAIN` in `flask/modules/ai/chains.py` with explicit input resolution. Update existing prompt unit tests. See [Solution Architecture](./architecture.md) for the context-loader ownership decision (route reads context, runner receives a flat inputs dict).

**Port budget**: ~60 lines across four prompt functions and the chain declaration; excludes inter-step coordination logic (the runner owns sequencing) and prompt-parameter validation beyond Python type annotations.

### Task 3: Add SSE streaming endpoint

Add `POST /api/ai/text/generate-spec/stream` to `flask/modules/ai/routes.py`. The route validates the request via the existing `GenerateSpecRequest` DTO, reads context, and yields SSE-formatted `ChainEvent` JSON via a Flask generator response. The existing batch `POST /api/ai/text/generate-spec` endpoint is untouched. Integration test covers the full SSE round-trip against a mock provider. Structural test `test_pipelinedFeatures_useRunChain` confirms no route handler calls the chain adapter more than once per request outside of `run_chain()`.

**Port budget**: ~25 lines for the route handler and generator; excludes reconnection logic (client responsibility), in-memory chain-state tracking, and per-step timeout or cancellation.

### Task 4: OpenAPI declaration + DTO regen

Declare `/api/ai/text/generate-spec/stream` and the `ChainEvent` schema in `openapi.yaml`. Run `make dto` to regenerate Python DTOs. The SSE stream schema is best-effort — `datamodel-codegen` does not emit useful streaming types; the `ChainEvent` Pydantic model is the authoritative server-side type. Validate the spec passes `make validate-openapi`.

**Port budget**: ~30 lines in `openapi.yaml` plus the schema component; excludes frontend DTO generation (tracked in the Angular SSE consumer epic).

---

## Success Criteria

This epic is complete when:

- ✅ `POST /api/ai/text/generate-spec/stream` returns `text/event-stream` with one `step_started`, one or more `step_delta`, and one `step_completed` per step, followed by `chain_completed`
- ✅ An unhandled exception inside any step emits an `error` event and closes the stream cleanly — no silent truncation
- ✅ The existing batch endpoint returns the same output shape as before the port (regression test passes)
- ✅ All four step-prompt functions have unit tests that pass without an API call
- ✅ `run_chain()` has a unit test asserting the full event sequence against a mock provider
- ✅ `test_pipelinedFeatures_useRunChain` structural test passes
- ✅ `make ci` passes: tests, lint, typecheck, openapi-valid, DTO drift check

---

## Non-Goals

- ❌ **Angular EventSource consumer** — this epic delivers the server contract; frontend follows separately
- ❌ **Streaming for other endpoints** — generalizing SSE to other routes requires a second concrete use case
- ❌ **Chain-of-chains** — linear sequential steps only; composition trigger is when a second pipeline shares ≥2 steps with `SPEC_CHAIN`
- ❌ **Generalized agent concept** — the primitive is a chain executor, not a planner or tool-using agent

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design and open-question resolutions
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview