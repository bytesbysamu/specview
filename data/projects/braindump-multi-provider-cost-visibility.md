# spec-doc-api — Multi-Provider Support + Token Cost Visibility

> **MERGED** into `braindump-saas-anthropic-sdk-provider.md` on 2026-04-26.
>
> The SDK-provider brain dump now owns both the provider migration AND the
> cost-tracking accumulator + `/api/stats` endpoint that originally lived here.
> They were always coupled — token counts only become real once the SDK
> provider lands. Splitting them across two brain dumps was a mistake.
>
> This file is preserved for git history; do not generate a spec from it.
> Read the consolidated version instead.

---

## (Original brain dump below — do not act on)

## What

Add an Anthropic SDK provider alongside the existing CLI provider. Make the active provider selectable via env var. Track input/output token counts on every AI call and expose cumulative cost via a `/api/stats` endpoint. This gives cost visibility across the bootstrap + task-gen calls without requiring external tooling.

The CLI provider works but is opaque — no token counts, no cost estimate, no way to know if a complex project just consumed $0.50 or $5.00.

### 1. Anthropic SDK provider — api/modules/chain/providers/anthropic_sdk.py

```python
"""Anthropic SDK provider — direct API, returns token counts."""
from __future__ import annotations

import os
import anthropic

from ..errors import ProviderError

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY not set", 500)
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def create_message(
    system: str,
    prompt: str,
    *,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 16384,
) -> tuple[str, dict]:
    """Returns (text, usage) where usage = {input_tokens, output_tokens}."""
    try:
        msg = _get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens}
        return msg.content[0].text, usage
    except anthropic.APIError as exc:
        raise ProviderError(str(exc), 502) from exc
```

### 2. Chain adapter — unified return type with usage

```python
# modules/chain/adapter.py
from dataclasses import dataclass, field

@dataclass
class ChainResult:
    text: str
    usage: dict = field(default_factory=dict)  # {input_tokens, output_tokens} or {}


def generate(system: str, user: str, *, max_tokens: int = 4096) -> ChainResult:
    provider_name = os.environ.get("AI_PROVIDER", "cli")
    if provider_name == "anthropic":
        from .providers.anthropic_sdk import create_message
        text, usage = create_message(system, user, max_tokens=max_tokens)
        _record_usage(usage)
        return ChainResult(text=text, usage=usage)
    else:
        from .providers.cli import create_message
        text = create_message(system, user, max_tokens=max_tokens)
        return ChainResult(text=text)
```

`AI_PROVIDER=anthropic` in `.env` switches providers. Default stays `cli` — no existing behavior changes.

### 3. Usage tracking — module-level accumulator

```python
# modules/chain/adapter.py
import threading

_USAGE_LOCK = threading.Lock()
_USAGE: dict = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

# Pricing (claude-sonnet-4-5, per million tokens, as of 2026-04)
_INPUT_COST_PER_M  = 3.00   # USD
_OUTPUT_COST_PER_M = 15.00  # USD


def _record_usage(usage: dict) -> None:
    with _USAGE_LOCK:
        _USAGE["input_tokens"]  += usage.get("input_tokens", 0)
        _USAGE["output_tokens"] += usage.get("output_tokens", 0)
        _USAGE["calls"]         += 1


def get_usage_summary() -> dict:
    with _USAGE_LOCK:
        inp  = _USAGE["input_tokens"]
        out  = _USAGE["output_tokens"]
        cost = (inp / 1_000_000 * _INPUT_COST_PER_M) + (out / 1_000_000 * _OUTPUT_COST_PER_M)
        return {
            "calls":         _USAGE["calls"],
            "input_tokens":  inp,
            "output_tokens": out,
            "cost_usd":      round(cost, 4),
            "provider":      os.environ.get("AI_PROVIDER", "cli"),
        }
```

Resets on process restart (in-process only — no persistence).

### 4. GET /api/stats — new endpoint

```python
# modules/ai/routes.py
from modules.chain.adapter import get_usage_summary

@ai_bp.get("/stats")
def ai_stats():
    return jsonify(get_usage_summary())
```

Response:
```json
{
  "calls": 12,
  "input_tokens": 48200,
  "output_tokens": 31800,
  "cost_usd": 0.6210,
  "provider": "anthropic"
}
```

### 5. .env additions

```bash
# .env
AI_PROVIDER=anthropic          # or cli (default)
ANTHROPIC_API_KEY=sk-ant-...   # required when AI_PROVIDER=anthropic
```

### 6. requirements.txt addition

```
anthropic>=0.49.0
```

Only imported when `AI_PROVIDER=anthropic`. CLI provider has no new dependency.

## Why now

The CLI provider is free (Claude Code subscription) but opaque and non-portable. The Anthropic SDK provider is needed for:
1. **Cost accounting** — know what each project costs before committing to automation
2. **Server deployments** — the deployed server doesn't have Claude Code installed
3. **Model selection** — SDK allows `claude-opus-4-6` for architecture, `claude-haiku-4-5` for analysis

The `/api/stats` endpoint is useful today regardless of provider — even without token counts, tracking call counts surfaces runaway generation loops.

## What's missing

Two decisions:

1. **Token cost constants**: Prices change. Options: (a) hardcode and update manually (proposed), (b) fetch from Anthropic pricing API (doesn't exist), (c) configurable via env vars.

2. **Persistence across restarts**: `_USAGE` resets on deploy. Options: (a) accept the reset (proposed) — session-level cost visibility is sufficient, (b) write to a SQLite file — durable but adds a dependency.

## Explicitly out of scope

- Per-project cost breakdown — tracking by project_id requires passing project context into the chain adapter
- Budget alerts / hard limits — no quota enforcement; visibility only
- Multiple simultaneous providers — one active provider per process
- Streaming token counting — add after streaming provider lands
