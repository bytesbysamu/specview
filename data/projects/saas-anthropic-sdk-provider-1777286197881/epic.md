# 🎯 Epic: SaaS Anthropic SDK Provider

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Every SaaS feature on the roadmap — auth, billing, usage metering, observability — is moot until AI calls work in the deploy container. Today they don't, because the Coolify image has no `claude` CLI binary and no Claude Code subscription. This capability flips the production default from CLI to the Anthropic SDK so the deploy can answer its first `/api/ai/generate` request without crashing. It is the keystone unlocking the entire SaaS roadmap.

The same change unlocks two cost levers at zero extra effort. First, the SDK reports input/output tokens per call, enabling the org-wide cost dashboard the founder needs before opening the deploy to even friendly traffic. Second, per-step model routing (Haiku for cheap analysis steps, Opus only for architecture) cuts bootstrap-project spend by an estimated 60–80% — a saving that compounds over every spec generated.

There is no consumer that pays for this capability directly; it is infrastructure that every paid feature depends on. Skipping it means choosing not to ship to the cloud at all.

**Value Proposition**: One day of SDK provider work makes the deploy container functional and turns AI cost from invisible to observable, unblocking the entire SaaS roadmap.

---

## Scope

### What This Epic Covers

- **SDK provider tokens** – populate `ChainResult.tokens_in/tokens_out` from the existing `runtime/chain/providers/claude.py` so the cost accumulator has real numbers to work with
- **Adapter auto-detection** – `_select_provider()` defaults to `claude` when `ANTHROPIC_API_KEY` is set, falls back to `cli` otherwise; explicit `CHAIN_PROVIDER=mock` still overrides for tests
- **Cost accumulator + `/api/ai/stats`** – module-level dict keyed by `{calls, input_tokens, output_tokens, cost_usd, provider}`, threading-locked, reset on process restart; new GET endpoint behind `ai_bp`
- **Per-step model routing convention** – wire `model=` overrides into existing `AICall` definitions in `modules/ai/workflows/*` so analysis steps use Haiku and architecture uses Opus
- **Production startup gate** – `create_app()` raises `RuntimeError` when `FLASK_DEBUG=0` and no `ANTHROPIC_API_KEY` and `CHAIN_PROVIDER` is unset or not `mock`

### What This Epic Does NOT Cover

- ❌ OpenAI / Gemini / Replicate providers — no second consumer; ELA #5 defers Bridge pattern
- ❌ Streaming cost accounting — tokens only arrive at end-of-stream; deferred to a streaming-cost capability
- ❌ Per-tenant API keys — org-wide key only; "BYO key" is enterprise-tier future work
- ❌ Persistent usage counters — in-process only; persistence belongs to monetisation/usage-metering capability
- ❌ Per-user (`auth_user_id`) cost attribution — usage-metering capability owns this join
- ❌ CLI provider removal — stays indefinitely as the dev fallback when no API key is present
- ❌ Anthropic batch API — interactive workload
- ❌ `--max-tokens` CLI bug fix in `providers/cli.py` — sibling brain dump; SDK sidesteps it for the deploy path

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Surface SDK token usage on ChainResult** | None | — | 0.3 days | High |
| 2 | **Auto-detect SDK provider in adapter** | Task 1 | — | 0.2 days | High |
| 3 | **Add cost accumulator and `/api/ai/stats` endpoint** | Task 1, Task 2 | — | 0.3 days | High |
| 4 | **Wire per-step model routing into AI workflows** | Task 3 | — | 0.2 days | High |
| 5 | **Add production startup gate to create_app** | Task 2 | Task 4 | 0.1 days | High |

### Task 1: Surface SDK Token Usage on ChainResult

The `claude.py` provider already calls `client.messages.create` but only returns `response.content[0].text`, throwing away `response.usage.input_tokens` and `response.usage.output_tokens`. The provider signature must widen to return both text and usage; the adapter then populates the existing-but-unused `tokens_in`/`tokens_out` fields on `ChainResult`. CLI and mock providers continue to return `None` for both fields — the accumulator handles that gracefully.

**Port budget**: Modify `providers/claude.py` (return tuple), thread tokens through `adapter.generate/rewrite/stream`, leave `cli.py` and `mock.py` untouched. ~30 LOC plus tests.

### Task 2: Auto-Detect SDK Provider in Adapter

`_select_provider()` currently reads `CHAIN_PROVIDER` and falls back to `"cli"`. Replace the literal default with a function: if no env var is set, choose `"claude"` when `ANTHROPIC_API_KEY` is present, else `"cli"`. Explicit `CHAIN_PROVIDER` still wins. Resolve the analysis open question by treating `"anthropic"` as an alias for `"claude"` in the mapping so the brain dump's naming and the existing module name both work.

**Port budget**: ~15 LOC change in `adapter.py`; structural test extension in `runtime/chain/tests/test_structural.py` to reject `if CHAIN_PROVIDER == 'cli'` style branches in feature code.

### Task 3: Add Cost Accumulator and `/api/ai/stats` Endpoint

Add a module-level `_USAGE` dict + `threading.Lock` to `adapter.py`, plus `_record_usage(result)` called after every successful provider call and `get_usage_summary()` returning the public snapshot. Add per-model pricing (Sonnet 4.5, Haiku 4.5, Opus 4.7) keyed by model id; the summary computes `cost_usd` from accumulated tokens. Add a new route file `modules/ai/routes/stats.py` exposing `GET /api/ai/stats` behind a new `stats_bp` Blueprint, registered in `ENABLED_MODULES`.

**Port budget**: ~50 LOC in adapter, ~25 LOC in new route file, ~30 LOC of tests; one openapi.yaml entry; one DTO regeneration via `make generate-dtos`.

### Task 4: Wire Per-Step Model Routing into AI Workflows

The `AICall` step kind already accepts a `model=` arg. Update existing workflow definitions in `modules/ai/workflows/` (notably the bootstrap-project chain) so the analysis step requests `claude-haiku-4-5`, the architecture step requests `claude-opus-4-7`, and everything else falls through to `DEFAULT_MODEL`. Verify via `/api/ai/stats` that calling bootstrap once produces a measurably lower cost than the all-Sonnet baseline.

**Port budget**: 2–3 line edits per existing workflow file; no schema changes; one new test asserting Haiku is requested for the analysis step.

### Task 5: Add Production Startup Gate to create_app

Add a guard at the top of `create_app()` that raises `RuntimeError` when `FLASK_DEBUG` is unset or `"0"`, no `ANTHROPIC_API_KEY` is present, and `CHAIN_PROVIDER` is unset or anything other than `"mock"`. The error message names the two escape hatches (set the key, or set `CHAIN_PROVIDER=mock`). Crash on startup, never wait for the first failed AI call to surface the misconfiguration.

**Port budget**: ~10 LOC at the top of `create_app.py`; one new test in `api/tests/` covering the three branches (key set → no raise; debug → no raise; mock → no raise; otherwise → raise).

---

## Success Criteria

- ✅ A successful `POST /api/ai/generate` call against the SDK provider returns text AND records non-zero `input_tokens`/`output_tokens` in `/api/ai/stats`
- ✅ With `ANTHROPIC_API_KEY` set and no explicit `CHAIN_PROVIDER`, the adapter selects the SDK provider; without the key, it falls back to CLI
- ✅ `GET /api/ai/stats` returns `{calls, input_tokens, output_tokens, cost_usd, provider}` with `cost_usd` computed from the per-model pricing constants
- ✅ Bootstrap-project workflow drives the analysis step against Haiku and the architecture step against Opus — verified by a unit test on the workflow definition
- ✅ `create_app()` raises on startup when production-mode env vars are inconsistent; passes when any of the three escape conditions hold
- ✅ Existing CLI-based dev workflow (`make dev` + `make test`) continues to pass with no regressions
- ✅ Adapter remains the sole provider import point (structural test green)

---

## Non-Goals

- ❌ Per-tenant key isolation — single org key only; revisit when a paying enterprise asks
- ❌ Persistent / cross-restart usage counters — in-process is correct for v1; persistence is the monetisation track's call
- ❌ Cost dashboards in the Angular UI — `/api/ai/stats` is consumer-agnostic; UI consumption is a separate UX capability
- ❌ Replacing the CLI provider entirely — dev convenience preserved
- ❌ A generic "provider switching" abstraction — concrete two-provider case only (ELA #5)
- ❌ Streaming token accounting — different SDK surface; deferred

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
