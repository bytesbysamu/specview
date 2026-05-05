# 🔍 SaaS Anthropic SDK Provider — Analysis

## The Problem
The deployed Coolify container has no `claude` CLI binary, no Claude Code subscription, and no way to authenticate the existing CLI provider — so every AI call in production fails today. Cost visibility, per-step model routing, and the `--max-tokens` CLI workaround are all blocked behind the same fix: making the Anthropic SDK provider the production default and surfacing token-usage on `ChainResult`.

## Hard Constraints
- **P0 deployment blocker** — no SaaS feature ships until SDK calls succeed in the deploy container.
- **Adapter boundary stays sole import point** — feature modules MUST NOT import `runtime/chain/providers/*` directly; ELA Pattern #1 holds.
- **Backward-compatible** — any dev environment without `ANTHROPIC_API_KEY` keeps using CLI; existing `make test` (using `CHAIN_PROVIDER=mock`) is unchanged.
- **Modular layout (already shipped)** — provider lives at `api/modules/runtime/chain/providers/`, NOT `flask/modules/...`; cost endpoint lives under `modules/ai/routes/text.py` (or new sibling), not at top level.
- **Pricing constants are version-pinned** — Sonnet 4.5 = $3/$15 per million in/out; Haiku 4.5 and Opus 4.7 land alongside per-step routing in this capability.
- **Independent of auth/billing/persistence tracks** — usage accounting is org-wide (single deploy), per-tenant attribution is the metering capability's concern.

## Open Questions
- **Provider name in adapter mapping**: `_select_provider` currently maps `"claude"` to `providers.claude`; the brain dump uses `"anthropic"`. Decision: keep `"claude"` as the canonical name, accept `"anthropic"` as an alias, OR rename. Architecture must lock one before the auto-detection branch is added.
- **Default model per call site**: brain dump §"What's missing" picks Sonnet 4.5 as the floor. Confirm in architecture and pin to `DEFAULT_MODEL` constant; per-step overrides happen in `modules/ai/workflows/*` AICall definitions.
- **Startup gate scope**: brain dump §7 hard-fails when `FLASK_DEBUG=0` and no `ANTHROPIC_API_KEY` — does it also fail under `CHAIN_PROVIDER=mock`? Decision: mock is a test-only escape hatch, allow it; everything else hard-fails.
- **`/api/stats` route placement**: belongs in `modules/ai/routes/text.py` (sibling of `/generate`, `/rewrite`) or its own `modules/ai/routes/stats.py`. Decision: new sibling file keeps the text routes file from sprouting unrelated concerns.

## Dependencies & Sequencing
- SDK provider lands first; tokens flow into `ChainResult.tokens_in/tokens_out` (already declared, never populated).
- Adapter auto-detection ships next; switches default when `ANTHROPIC_API_KEY` is set.
- Cost accumulator + `/api/stats` ship third; depends on tokens being populated by the SDK provider.
- Per-step model routing in workflow definitions ships fourth; depends on `/api/stats` so the cost reduction is observable.
- Startup gate ships last; it locks the production posture in `create_app.py`.

## Explicitly Out of Scope
- **OpenAI / Gemini / Replicate providers** — Bridge pattern remains a future v3 concern; deferred until a second non-Anthropic consumer exists (ELA #5).
- **Streaming token accounting** — token counts arrive at end-of-stream only; mid-stream cost tracking requires a different SDK surface, not this capability.
- **Per-tenant API keys ("BYO key")** — single org-wide key for v1; revisit when a paid enterprise tier requests it.
- **Anthropic batch API** — interactive workload, not batch.
- **Replacing the CLI provider** — kept indefinitely as a dev convenience; just no longer the default when the API key is present.
- **Persistence of usage counters** — in-process accumulator only; persistence belongs to the saas-monetisation/usage-metering track, not here.
- **Per-user cost attribution** — joins on `auth_user_id` belong with the usage-metering capability; this one tracks the whole deploy.
