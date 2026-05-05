# 🏗️ Solution Architecture: SaaS Anthropic SDK Provider

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The deployed container has no `claude` CLI binary, so the existing CLI provider is unusable in production. The fix is a one-adapter, two-provider posture: feature modules continue to import only `runtime/chain/adapter.py`; the adapter chooses between an SDK provider (production default when `ANTHROPIC_API_KEY` is set) and the CLI provider (developer-laptop fallback). Both implement the same `create_message` / `stream_message` interface; only the SDK provider populates token counts.

The token counts unblock a small in-process accumulator in `adapter.py` that records every call's input/output tokens and exposes them via a new `GET /api/ai/stats` route. Cost is computed from per-model pricing constants, not stored — pricing changes happen by editing the constants, not by migrating data. The accumulator is org-wide and resets on process restart, intentionally trivial: per-user attribution and persistence are downstream capabilities (usage-metering, monetisation), not this one.

The change is layered, not invasive. Task 1 widens the SDK provider's return shape. Task 2 changes one branch in `_select_provider`. Task 3 bolts the accumulator and route on. Task 4 sets `model=` on three existing AICall steps. Task 5 adds a startup guard. No existing route signature changes; no DTO drifts; no module moves.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| ELA #1 — Adapter Boundary | `runtime/chain/adapter.py` is the only file that knows which provider is active; structural test extended to reject any feature-side `if CHAIN_PROVIDER == ...` branch |
| ELA #2 — Blueprint Module Structure | New `/api/ai/stats` route lives in `modules/ai/routes/stats.py` with its own `stats_bp`; routes own no business logic — accumulator helpers live in `adapter.py` |
| ELA #3 — OpenAPI-First | `/api/ai/stats` added to `openapi.yaml` with the exact response shape `{calls, input_tokens, output_tokens, cost_usd, provider}`; DTOs regenerated via `make generate-dtos` |
| ELA #5 — Not-Yet-Built | Two providers only (Anthropic SDK + CLI); no Bridge abstraction, no provider registry, no `BaseProvider` ABC — exactly one concrete shape per file |
| ELA #7 — In-Process State | `_USAGE` dict + `threading.Lock` in `adapter.py` — single consumer (the new `/api/ai/stats` route), no Redis, no DB |

---

## System Boundaries

### What This System Includes

- A widened `runtime/chain/providers/claude.py` returning `(text, input_tokens, output_tokens)` from both `create_message` and `stream_message`
- An updated `runtime/chain/adapter.py` whose `_select_provider` auto-detects SDK vs CLI based on `ANTHROPIC_API_KEY` and accepts `"anthropic"` as an alias for `"claude"`
- A module-level usage accumulator in `adapter.py` (`_USAGE`, `_USAGE_LOCK`, `_record_usage`, `get_usage_summary`) plus per-model pricing constants for Sonnet 4.5, Haiku 4.5, Opus 4.7
- A new Flask Blueprint `stats_bp` at `modules/ai/routes/stats.py` exposing `GET /api/ai/stats`, registered in `create_app.ENABLED_MODULES`
- Per-step `model=` overrides on existing `AICall` definitions in `modules/ai/workflows/` (analysis → Haiku; architecture → Opus; default → Sonnet)
- A startup gate in `create_app()` that raises `RuntimeError` for inconsistent production env

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| OpenAI / Gemini / Replicate provider modules | No second non-Anthropic consumer; ELA #5 defers Bridge pattern |
| `BaseProvider` ABC or provider registry | Two concrete providers; abstraction would describe a single shape |
| Streaming-cost accounting | Tokens arrive at end-of-stream only; different SDK surface |
| Persistent usage counters | Belongs to monetisation/usage-metering capability; in-process is correct here |
| Per-tenant `auth_user_id` cost attribution | Joins on user belong with usage-metering |
| BYO Anthropic key per tenant | Single org-wide key for v1 |
| CLI provider removal | Dev fallback when no API key present |
| `--max-tokens` CLI bug fix | SDK respects the value correctly; sibling brain dump owns the CLI path |
| Anthropic batch API | Interactive workload |
| Cost dashboard UI | `/api/ai/stats` is consumer-agnostic; Angular consumption is a separate capability |

---

## Component Design

### `runtime/chain/providers/claude.py` — SDK Provider

**Purpose**: The production default. Wraps the Anthropic Python SDK with consistent error mapping (`RateLimitError` → 503, `APIConnectionError` → 502, `APIError` → 502).

**Key Parts**:
- `_make_client()` — lazy per-call client; reads `ANTHROPIC_BASE_URL` at call time so test fixtures can redirect via `monkeypatch.setenv`
- `create_message(system, prompt, *, model, max_tokens)` — returns `(text, input_tokens, output_tokens)` instead of just text after this capability
- `stream_message(...)` — yields text deltas; final yield optionally carries usage when SDK exposes it; consumer is `adapter.stream`

**Patterns**: Stateless module; no class hierarchy; ELA #1 boundary respected.

**Consumer**: `runtime/chain/adapter.py` only.

---

### `runtime/chain/adapter.py` — Selection + Accumulation

**Purpose**: Sole import point for AI calls. Owns provider selection, token-usage accumulation, and pricing.

**Key Parts**:
- `_select_provider()` — returns `providers.claude` when `CHAIN_PROVIDER` resolves to `"claude"` or `"anthropic"`; `providers.cli` when `"cli"`; `providers.mock` when `"mock"`. Default branch reads `ANTHROPIC_API_KEY`: present → SDK, absent → CLI
- `generate(...)`, `rewrite(...)`, `stream(...)` — public adapter functions; pass `model` through; call `_record_usage(result)` after every successful return so token counts feed the accumulator
- `_USAGE` (module-level dict) + `_USAGE_LOCK` (`threading.Lock`) — singleton accumulator; ELA #7
- `_PRICING` — `{model_id: (input_per_million, output_per_million)}` for Sonnet 4.5, Haiku 4.5, Opus 4.7
- `get_usage_summary()` — public read; computes `cost_usd` from `_USAGE` totals across the recorded models, rounds to 4 decimals

**Patterns**: Adapter (ELA #1); module-level state (ELA #7).

**Consumers**: every `modules/ai/services/*` and `modules/ai/workflows/*` calls `generate`/`rewrite`/`stream`; the new `stats_bp` calls `get_usage_summary`.

---

### `modules/ai/routes/stats.py` — Cost Visibility Route (new)

**Purpose**: Single GET endpoint. No business logic; calls `adapter.get_usage_summary()` and `jsonify`s the result.

**Key Parts**:
- `stats_bp` — Flask Blueprint registered in `create_app.ENABLED_MODULES`
- `GET /api/ai/stats` handler — returns the snapshot DTO; provider field reads `os.environ.get("CHAIN_PROVIDER")` at request time so a deploy that flips the env var post-restart shows the right value

**Patterns**: ELA #2 (route owns no logic).

**Consumer**: any HTTP client (initial use is curl from the deploy host; UI consumption is out of scope).

---

### `modules/ai/workflows/*` — Per-Step Model Routing

**Purpose**: Workflow definitions for bootstrap-project (and future chains) request the cheapest model that meets each step's quality bar.

**Key Parts**:
- AICall(name="analysis", ..., model="claude-haiku-4-5") — short prompt, low quality bar; ~5x cheaper input than Sonnet
- AICall(name="epic", ..., model="claude-sonnet-4-5") — middle of the curve; default
- AICall(name="architecture", ..., model="claude-opus-4-7") — quality matters; cost is acceptable for one call

**Patterns**: ELA #6 (workflow definitions are data).

**Consumer**: `WorkflowRuntime` from `modules/runtime/workflows/runtime.py`.

---

### `create_app.py` — Production Startup Gate

**Purpose**: Crash loud when production env is missing the API key. Better here than at first AI call.

**Key Parts**:
- One guard block at the top of `create_app()` after `load_dotenv()`. Three escape conditions: `FLASK_DEBUG=1` (dev), `ANTHROPIC_API_KEY` set (prod ready), or `CHAIN_PROVIDER=mock` (test). Otherwise raise `RuntimeError` with a one-sentence remediation message.

**Patterns**: Fail fast; named consumer is the deploy job.

**Consumer**: gunicorn `create_app:create_app()` invocation in the Coolify container; `make dev`; pytest fixtures.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| AI SDK | `anthropic` Python SDK | Already in `requirements.txt`; `claude.py` provider already imports it; SDK is the official client |
| HTTP framework | Flask 3.x | Existing app; new route file is a Blueprint following the existing pattern |
| Concurrency | `threading.Lock` | ELA #7 — single-process Flask + gthread workers; no Redis, no DB |
| Pricing source | Hard-coded constants in `adapter.py` | Pricing changes ~quarterly; constants are easier to audit and version-control than fetching from a remote |
| Auth provider for SaaS context | Neon Auth (RS256 JWTs) | Locked decision; documented here for cross-capability consistency. This capability does NOT call out to Neon Auth — usage is org-wide |
| DB engine for SaaS context | Neon Postgres (prod) / SQLite (dev) | Locked decision; this capability stores nothing |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| SDK as production default, CLI kept as dev fallback | Deploy container has no CLI binary; dev laptops have a Claude Code subscription; the brain dump's framing is a posture flip, not a deletion | Two providers to maintain; structural test must keep both behind the adapter |
| `_select_provider` auto-detects on `ANTHROPIC_API_KEY` rather than requiring `CHAIN_PROVIDER=claude` | The deploy job already sets the API key; making it the implicit signal removes one config step | A dev who sets `ANTHROPIC_API_KEY` for another tool gets SDK calls unexpectedly; mitigated by Sonnet 4.5 default cost being low |
| `"anthropic"` alias for `"claude"` in provider mapping | Brain dump uses `"anthropic"`; existing module is named `claude.py`; aliasing is cheaper than renaming the module and updating tests | Two names for one thing; documented in adapter docstring |
| Org-wide accumulator, not per-user | Per-user attribution requires `auth_user_id` joins which depend on the auth capability; this capability ships independently | "Whose call cost what" needs the metering capability; this only answers "what does the deploy spend in aggregate" |
| Reset on process restart (in-process dict) | A monthly invoice doesn't need second-by-second persistence; gunicorn restart is rare; persistence is the monetisation track's responsibility | A crash loses today's counters; acceptable for v1 |
| Hard-coded pricing constants per model | Pricing changes are infrequent; a remote fetch adds startup latency and a failure mode | Editing constants is a manual step; checklisted in a comment block |
| Default model = Sonnet 4.5 | Middle of the price/quality curve; matches existing `DEFAULT_MODEL`; per-step override handles the cheap and quality cases | A new feature that forgets `model=` pays Sonnet rates — acceptable floor |
| Production startup gate raises `RuntimeError` | Crash on startup is loud and fast; first-AI-call failure is silent until a user triggers it | Gunicorn restarts are noisier; mitigated by exit-code monitoring being already wired |

---

## Execution Flow

```
Phase 1 — Plumbing
  Task 1 (provider returns tokens) ──→ Task 2 (adapter auto-detects)

Phase 2 — Visibility
  Task 2 ──→ Task 3 (accumulator + /api/ai/stats)

Phase 3 — Cost lever + safety
  Task 3 ──→ Task 4 (per-step model routing)
  Task 2 ──→ Task 5 (production startup gate; parallel with Task 4)
```

---

## Open Questions

- **Pricing constant ownership** — keep `_PRICING` in `adapter.py` (current plan) or move to a sibling `runtime/chain/pricing.py`? Options: (A) inline in adapter, (B) sibling module. Re-decision trigger: a third pricing-related concern lands (e.g., per-tenant rate tables) — at that point pricing earns its own file under ELA #5's "second consumer" rule.
- **`stats_bp` URL prefix** — `/api/ai/stats` (current plan) is consistent with the `ai_bp` prefix; alternative is `/api/stats` at app root. Options: (A) under `ai_bp`, (B) top-level. Re-decision trigger: a non-AI cost surface emerges (DB query stats, queue stats) and `stats_bp` becomes a multi-domain aggregator.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview
