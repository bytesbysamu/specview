# spec-doc — Anthropic SDK Provider as Production Default

> **Priority**: P0 — deployment blocker (no `claude` CLI in the production container).
> **Effort**: ~1 day (SDK provider + cost accumulator + `/api/stats` + startup gate).
> **Blocks**: any cloud-deploy AI call; SaaS launch in general.
> **Depends on**: nothing (independent of the data-layer/auth track — can ship in parallel).
> **Siblings**: `braindump-raise-max-tokens.md` (CLI bug; SDK sidesteps it),
>               `braindump-saas-usage-metering.md` (per-user attribution joins on top of org cost),
>               `braindump-saas-stripe-billing.md` (cost data informs pricing decisions).
> **Consolidates**: former `braindump-multi-provider-cost-visibility.md` is folded in here (§5).

## What

Make the Anthropic SDK provider the default for any deployment that isn't a developer's laptop. The CLI provider (`api/modules/chain/providers/cli.py`) **does not work in cloud deploys** — there is no `claude` binary in the production container, no Claude Code subscription tied to the deploy account, no way to authenticate the CLI from a server. This is the load-bearing blocker for shipping a deployed SaaS.

This brain dump differs from the existing `braindump-multi-provider-cost-visibility.md` in framing: that one treats the SDK provider as one of two options switchable for cost analytics. **This one treats the SDK provider as the production-mandatory path** and the CLI as the dev-only legacy.

Port the SDK shape from humanize-me (`backend/services/claude.py`, the original that bubls forked from). Use bubls's per-step model routing (Haiku for analysis, Opus for architecture) as the price/quality lever. Use trendfy's pattern for credential management (single secret in env, lazy client init, no caching across requests in case of key rotation).

### 1. Anthropic SDK provider — `api/modules/chain/providers/anthropic_sdk.py`

```python
"""Anthropic SDK provider — production default.

The CLI provider is dev-only. Production must use this provider because
there is no `claude` binary in the deploy container.
"""
import os
from anthropic import Anthropic, APIError, RateLimitError, APIConnectionError
from ..errors import ProviderError
from ..types import ChainResult


def create_message(
    system: str,
    prompt: str,
    *,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 4096,
) -> ChainResult:
    """One-shot Anthropic SDK call. Returns ChainResult with text + token usage."""
    client = Anthropic(timeout=900.0, max_retries=2)
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except RateLimitError:
        raise ProviderError("AI provider rate-limited. Try again in a moment.", 429)
    except APIConnectionError:
        raise ProviderError("Cannot reach AI provider. Try again.", 502)
    except APIError as exc:
        raise ProviderError(f"AI provider error: {exc.message}", 502)

    return ChainResult(
        text=msg.content[0].text,
        latency_ms=0,  # adapter wraps with timing
        tokens_in=msg.usage.input_tokens,
        tokens_out=msg.usage.output_tokens,
    )


def stream_message(system, prompt, *, model="claude-sonnet-4-5", max_tokens=4096):
    """SSE-style chunk stream. Yields text deltas."""
    client = Anthropic(timeout=900.0, max_retries=2)
    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as response:
            for text in response.text_stream:
                yield text
    except RateLimitError:
        raise ProviderError("AI provider rate-limited.", 429)
```

`ChainResult` gains `tokens_in` and `tokens_out` fields (already declared in `modules/chain/types.py`; the SDK provider is the first to populate them — CLI cannot).

### 2. Adapter — flip the default

```python
# modules/chain/adapter.py
def _select_provider():
    name = os.environ.get("CHAIN_PROVIDER")
    if name is None:
        # Production default: SDK if API key is set, CLI as dev fallback
        name = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "cli"
    mapping = {
        "anthropic": providers.anthropic_sdk,
        "cli":       providers.cli,
        "mock":      providers.mock,
    }
    if name not in mapping:
        raise ValueError(f"Unknown CHAIN_PROVIDER={name!r}")
    return mapping[name]
```

Auto-detect: if `ANTHROPIC_API_KEY` is set, use SDK. Otherwise CLI. Production deployments set the key; developer machines may set neither (then they get CLI, which works locally with their Claude Code subscription). `CHAIN_PROVIDER=mock` for tests.

This change is **backward-compatible**: every existing dev environment without `ANTHROPIC_API_KEY` keeps using CLI. Production gets SDK automatically once the key is set.

### 3. Per-step model routing — extend `AICall`

Today `AICall` has `model: str = chain_adapter.DEFAULT_MODEL`. Add per-step overrides in workflow definitions:

```python
# modules/spec_gen/workflows/generate_spec.py
.step(AICall(
    name="analysis",
    system=ANALYSIS_SYSTEM,
    prompt_template=ANALYSIS_USER,
    input_keys=("braindump", "project_name", "builder"),
    model="claude-haiku-4-5",   # cheap, short prompts
    max_tokens=4096,
))
.step(AICall(
    name="architecture",
    system=ARCHITECTURE_SYSTEM,
    prompt_template=ARCHITECTURE_USER,
    input_keys=("braindump", "project_name", "builder", "principles", "epic", "codebase", "references"),
    model="claude-opus-4-7",    # quality matters most here
    max_tokens=16384,
))
```

The per-step `model` field already exists in `AICall` from Task 1.2; this brain dump just confirms the routing convention. Saves ~3x on cost for the analysis step (Haiku is ~5x cheaper than Sonnet for input tokens).

### 4. Credential management

```bash
# .env.example
ANTHROPIC_API_KEY=sk-ant-...           # production: set; dev: optional (falls back to CLI)
ANTHROPIC_BASE_URL=                    # tests use this to redirect to a stub server
CHAIN_PROVIDER=                        # explicit override; rarely set
```

Production secrets live in Coolify env vars (per Epic 6), never in `.env`. The `_make_client()` helper reads `ANTHROPIC_BASE_URL` per-call so test infrastructure can `monkeypatch.setenv` to redirect SDK traffic to a local stub server (already shipped in the existing claude provider).

### 5. Cost accounting (folded in from former `braindump-multi-provider-cost-visibility.md`)

A module-level usage accumulator + a `/api/stats` endpoint. Resets on process restart — in-process only, no persistence.

```python
# modules/chain/adapter.py
import threading

_USAGE_LOCK = threading.Lock()
_USAGE: dict = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

# Pricing (claude-sonnet-4-5, per million tokens, as of 2026-04). Hard-coded;
# revisit when Anthropic changes prices. Per-model rates land alongside
# per-step model routing (§3 above).
_INPUT_COST_PER_M  = 3.00   # USD
_OUTPUT_COST_PER_M = 15.00  # USD


def _record_usage(result: ChainResult) -> None:
    with _USAGE_LOCK:
        _USAGE["input_tokens"]  += result.tokens_in or 0
        _USAGE["output_tokens"] += result.tokens_out or 0
        _USAGE["calls"]         += 1


def get_usage_summary() -> dict:
    with _USAGE_LOCK:
        inp, out = _USAGE["input_tokens"], _USAGE["output_tokens"]
        cost = (inp / 1_000_000 * _INPUT_COST_PER_M) + (out / 1_000_000 * _OUTPUT_COST_PER_M)
        return {
            "calls":         _USAGE["calls"],
            "input_tokens":  inp,
            "output_tokens": out,
            "cost_usd":      round(cost, 4),
            "provider":      os.environ.get("CHAIN_PROVIDER", "cli"),
        }
```

`adapter.generate()` calls `_record_usage(result)` after every successful provider call. The CLI provider returns `tokens_in=tokens_out=None` so usage tracking is a no-op for CLI calls; only SDK calls feed real numbers.

```python
# modules/ai/routes.py
@ai_bp.get("/stats")
def ai_stats():
    return jsonify(get_usage_summary())
```

Response shape:

```json
{"calls": 12, "input_tokens": 48200, "output_tokens": 31800, "cost_usd": 0.6210, "provider": "anthropic"}
```

Per-user cost attribution (joining usage with `user_id`) lands alongside the SaaS metering brain dump — not here. This brain dump's accounting is org-wide ("how much is this deploy spending today") rather than per-tenant.

### 6. Structural test — refresh the boundary

The existing `featureModules_mustNotImportProvidersDirectly` test catches feature code that imports `providers.cli` directly. Extend it to also flag any code that switches behaviour based on which provider is selected (e.g., `if CHAIN_PROVIDER == 'cli'`). The selection point is the adapter; nothing else should know.

### 7. Deployment gate

The Coolify deploy job (Epic 6's `deploy.yml`) gains a one-line health check: container won't start in production mode unless `ANTHROPIC_API_KEY` is set:

```python
# create_app.py
def create_app():
    app = Flask(__name__)
    if os.environ.get("FLASK_DEBUG", "0") == "0" and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "Production mode requires ANTHROPIC_API_KEY. "
            "Set CHAIN_PROVIDER=mock to override (tests only)."
        )
    ...
```

Hard fail loud. Better to crash on startup than to discover at first AI call that the SDK can't authenticate.

## Why now

The Coolify deploy is shipped (Epic 6). The Workflows epic is shipped. The bootstrap-async brain dump is queued. **None of those work in production today** because the deployed container has no `claude` CLI binary. Every other SaaS brain dump — auth, billing, metering, landing page — is moot if the AI calls themselves don't function on the deploy target.

Three additional reasons it should land soon:
- **Cost visibility** is impossible until the provider returns token counts. The CLI provider can't.
- **Per-step model routing** (Haiku for cheap steps, Opus for architecture) is a 60–80% cost reduction on bootstrap, achievable today via `AICall(model=...)` once the SDK is in.
- **The `--max-tokens` CLI bug** (covered in `braindump-raise-max-tokens.md`) is moot for SDK callers — the SDK respects `max_tokens` correctly. Cloud deploy gets the right behaviour for free.

## What's missing

One decision: **what model is the production default?** Options:
- (a) `claude-sonnet-4-5` everywhere unless overridden (proposed) — middle of the price/quality curve, current dev default
- (b) `claude-haiku-4-5` default + opt-in to Sonnet/Opus per call — minimum cost, quality regression on bootstrap
- (c) `claude-opus-4-7` default — best quality, ~5x cost vs Sonnet

(a) is right. Workflow definitions override per step (analysis: Haiku, architecture: Opus, everything else: default Sonnet). The default keeps the cost from creeping if a new feature forgets to set `model=`.

## Explicitly out of scope

- **OpenAI / Gemini providers** — the Bridge pattern in the v3 brain dump describes how to add them; out of scope until a concrete consumer or pricing pressure justifies it.
- **Streaming for cost accounting** — token counts arrive at end-of-stream; mid-stream cost tracking requires a different SDK surface; deferred.
- **Per-user / per-tenant API keys** — single org-wide Anthropic key for v1; per-tenant keys belong with a "bring your own key" enterprise feature.
- **Anthropic batch API** — useful for offline workloads; spec-doc is interactive; not needed.
- **Replicate / image-generation providers** — out of scope until spec-doc has an image-output workflow; when that lands, see the Bridge pattern in the v3 brain dump.
- **Replacing the CLI provider** — kept indefinitely as a dev convenience; just no longer the default when the API key is present.
