---
sidebar_position: 2
---

# 🎯 Text Chains — Epic

**Purpose**: Define scope and tasks for adding multi-step chain operations to /text.

**Source Analysis**: See [Analysis](./analysis.md) for constraints and resolved questions.

---

## Business Value

Humanize-me validates the market at $195K MRR (StealthGPT benchmark). Its core moat is a 3-pass humanization chain — not a single rewrite, but iterative refinement where each pass strips a different layer of AI fingerprint. Bubls already shipped the chain adapter and /text route but only does single-shot calls through them. Porting the multi-pass pattern (and extending it with context injection from spec-doc's generation pipeline) turns Bubls into the platform: one text surface, N domain-aware operations, each backed by a chain definition + context blocks.

Three paying use cases share one backend path: humanize (proven — direct port of working code), expand-with-voice (builder-profile-injected, context makes it personal), braindump-to-docs (differentiator nobody else ships — multi-file generation from a single brain dump). Each chain operation costs 3–5x tokens vs single-shot. Usage tracking already exists via `superapp_generations`. Pricing tiers deferred to post-validation — bundle everything, measure which chains users actually run, split tiers from data.

The frontend change is minimal: a second row of buttons with a different accent color, plus a tabbed output area for multi-file results. Users don't learn a new interface — they tap a button and get better output. The quality gap between single-shot and 3-pass is the product.

---

## Scope

### What This Epic Covers

- **Chain runner**: new endpoint `POST /api/text/chain` that reads a chain definition, executes steps sequentially through the chain adapter, returns final output
- **Chain definitions**: JSON files in `server/modules/chain/definitions/` naming steps (atomic ops) + context block references
- **Context blocks**: markdown files in `server/context/` (prompts, rubrics) loaded per chain step via manifest
- **Three chain operations**: Deep Humanize (3-pass), Braindump → Docs (multi-file), Rewrite + Review (rubric cycle)
- **UI**: second row of chain-mode buttons on /text page (distinct accent color to signal "takes longer")
- **Multi-file output**: tabbed view within existing output area for braindump-to-docs
- **OpenAPI spec**: updated with chain endpoint, DTOs regenerated both sides
- **Generation persistence**: extend `superapp_generations` with `chain_id` + `step_count` metadata columns
- **Feature-gated**: `text_chains` flag on user's `enabled_features`; null-object fallback (locked buttons, not hidden)
- **Observer event**: `chainCompleted` emitted on every run with `{ chainId, stepCount, inputLength, outputLength, totalTokens }`
- **Structural tests**: enforce module boundaries (loader owns `server/context/`, runner owns `chain/definitions/`)

### What This Epic Does NOT Cover

- ❌ User-editable context blocks (v2)
- ❌ SSE/streaming per chain step (request-response for v1)
- ❌ Chain composition UI (fixed chains, iterate from usage)
- ❌ Cost analytics dashboard
- ❌ Offline execution
- ❌ Changes to existing single-shot modes (additive only)

---

## Tasks

**Note**: Task status tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Context Block Loader** | None | 2 | 0.5 day | High |
| 2 | **Chain Definition Schema + Runner** | None | 1 | 1 day | High |
| 3 | **Deep Humanize Chain** | 1, 2 | 4 | 0.5 day | High |
| 4 | **Braindump → Docs Chain** | 1, 2 | 3 | 1 day | High |
| 5 | **Rewrite + Review Chain** | 1, 2 | 3, 4 | 0.5 day | Medium |
| 6 | **Chain Mode UI (buttons + tabbed output)** | 3, 4 | — | 1 day | High |
| 7 | **Integration Test + QA** | 6 | — | 0.5 day | Medium |

### Task Details

#### Task 1: Context Block Loader

Create `server/modules/context/loader.py` — adapter-shaped module that reads markdown files from `server/context/` and returns named blocks as `dict[str, str]`. A manifest file (`server/context/manifest.json`) maps context-block names to relative file paths:

```json
{
  "humanize-pass-1": "prompts/humanize-pass-1.md",
  "builder": "prompts/builder.md",
  "quality-rubric": "rubrics/quality.md"
}
```

The loader resolves paths relative to `server/context/`. Mock mode (`CONTEXT_PROVIDER=mock`) returns fixture strings for testing — same interface, no file I/O.

**Structural invariant**: only `context/loader.py` reads from `server/context/` directly. Pin with a one-grep-one-assertion test: grep `server/` for `open()` or `Path().read_text()` calls referencing `server/context/` outside `context/loader.py` — fail if found. Failure message: "Only context/loader.py may read from server/context/. Use loader.load_block(name) instead."

#### Task 2: Chain Definition Schema + Runner

Define `ChainDefinition` as a JSON schema: ordered list of steps, each naming an atomic operation (`rewrite`, `generate`, `review`) + mode + context block references. Chain definitions live at `server/modules/chain/definitions/` — inside the module boundary, not at repo root.

Create `server/modules/chain/runner.py` with a `STEP_HANDLERS` dispatch map:

```python
STEP_HANDLERS: dict[str, Callable] = {
    "rewrite": handle_rewrite,   # chain.adapter.rewrite(text, mode, context)
    "generate": handle_generate, # chain.adapter.generate(prompt, context)
    "review": handle_review,     # chain.adapter.generate(review_prompt, context) → JSON
}
```

Given a `ChainDefinition` + user input, the runner: (1) resolves handler by op name from `STEP_HANDLERS`, (2) loads context blocks via the context loader, (3) calls handler through the chain adapter, (4) passes output as input to next step. Adding a new operation = one function + one dict entry. No if/elif branches in the runner loop.

**Observer**: on completion, emit `chainCompleted` event with `{ chainId, stepCount, inputLength, outputLength, totalTokens }`. Analytics subscribes — no coupling. Pattern mirrors `/text`'s existing `outputCompleted` signal from the UX revamp.

**Endpoint**: `POST /api/text/chain` accepts `{ chainId: string, input: string }`. Returns `{ generationId: string, result: string }` (single-file) or `{ generationId: string, files: [{name: string, content: string}] }` (multi-file). Blueprint registered in `ENABLED_MODULES`. Feature-gated: `403 { error: "text_chains not enabled", upgrade: true }` when `text_chains` not in user's `enabled_features`.

**Persistence**: save to `superapp_generations` with `chain_id` + `step_count` metadata columns (Alembic migration).

**Structural test**: grep for `open()` or `json.load()` calls to `chain/definitions/` outside `chain/runner.py` — fail if found. Failure message: "Only chain/runner.py may read from chain/definitions/. Use runner.load_definition(chainId) instead."

**Per-chain gating (deferred)**: single `text_chains` flag gates all chains for v1. Trigger to split: when pricing tiers differ per chain. Future shape named: `enabled_features.chain:{chainId}` — don't build the resolver until the second tier exists.

**Adapter extraction trigger (deferred)**: extract a `RunnerAdapter` interface when a second execution strategy appears (parallel steps, streaming, retry). Until then, the concrete sequential implementation is the only consumer — per Engineering Discipline § "not-yet-built is the right state."

#### Task 3: Deep Humanize Chain

Port `humanize-me/backend/services/humanizer.py` PASS_1/PASS_2/PASS_3 prompt content into `server/context/prompts/humanize-pass-1.md`, `humanize-pass-2.md`, `humanize-pass-3.md`. Register all three in `server/context/manifest.json`.

Create chain definition `server/modules/chain/definitions/deep-humanize.json`:

```json
{
  "id": "deep-humanize",
  "name": "Deep Humanize",
  "steps": [
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-1"] },
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-2"] },
    { "op": "rewrite", "mode": "humanize", "context": ["humanize-pass-3"] }
  ],
  "outputMode": "single"
}
```

End-to-end test: feed casual AI-generated text → output after 3 passes reads natural. Compare quality vs single-shot humanize on the same input — the 3-pass version should be noticeably less detectable.

#### Task 4: Braindump → Docs Chain

Port spec-doc's multi-file generation prompt template (from `server.js` `generate-spec` endpoint, lines 706+) into `server/context/prompts/braindump-to-docs.md`. Create chain definition `server/modules/chain/definitions/braindump-to-docs.json`:

```json
{
  "id": "braindump-to-docs",
  "name": "Brain Dump → Docs",
  "steps": [
    { "op": "review", "context": ["braindump-lint"], "outputKey": "lint" },
    { "op": "generate", "context": ["builder", "principles", "references", "braindump-to-docs"] },
    { "op": "review", "context": ["quality-rubric"], "outputKey": "score" }
  ],
  "outputMode": "multi-file"
}
```

Step 1 = structural pre-flight lint (catches missing sections, contradictions). Step 2 = multi-file generation with `===FILE: {name}===` markers in Claude output. Step 3 = self-review against quality rubric. Chain runner parses file markers from step 2 output and returns `{ files: [{name, content}, ...] }`. Context blocks injected: builder profile, architecture principles, reference materials.

#### Task 5: Rewrite + Review Chain

Create chain definition `server/modules/chain/definitions/rewrite-review.json`:

```json
{
  "id": "rewrite-review",
  "name": "Rewrite + Review",
  "steps": [
    { "op": "rewrite", "mode": "user-selected", "context": [] },
    { "op": "review", "context": ["quality-rubric"] },
    { "op": "rewrite", "mode": "fix", "context": [] }
  ],
  "outputMode": "single"
}
```

Step 1 = rewrite with user's selected mode. Step 2 = review against quality rubric, returns JSON `{ scores: {...}, issues: [...] }`. Step 3 = rewrite again, feeding the issues list as instruction to fix flagged problems. The runner parses the review JSON and injects the `issues` array as the instruction for step 3's rewrite. Context block: `server/context/rubrics/quality.md`.

#### Task 6: Chain Mode UI (buttons + tabbed output)

Extend `OperationBarComponent` (`src/app/components/operation-bar/operation-bar.component.ts`) with a second row of buttons below the existing operation buttons. Same standalone component shape, different accent color to visually signal "multi-step, takes longer." Buttons: **Deep Humanize**, **Brain Dump**, **Rewrite+Review**.

**Feature guard (null object)**: when `text_chains` is disabled in user's `enabled_features`, chain buttons render as **locked** — visible with `opacity: 0.5` + "Pro" badge overlay. Tap shows an upgrade toast. Never hides the buttons. Never returns 404. Same null-object pattern as the photoshoot feature guard.

**Loading state**: shows step progress during chain execution ("Step 2 of 3...") via polling or response metadata.

**Output area**: single-file chains (deep-humanize, rewrite-review) render in the existing output area. Multi-file chains (braindump-to-docs) render as **tabs** — each tab label = filename from the `files` response array, tab content = file content. Copy-per-tab button. Active tab persists during the session.

Add `chainRun(chainId: string, input: string)` method to `AiService` (`src/app/services/ai.service.ts`) calling `POST /api/text/chain`.

New response type in `AiService`:

```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
}
```

`data-test` selectors on every interactive element: `data-test="chain-deep-humanize"`, `data-test="chain-braindump"`, `data-test="chain-rewrite-review"`, `data-test="chain-tab-{filename}"`, `data-test="chain-copy-tab"`, `data-test="chain-step-progress"`.

#### Task 7: Integration Test + QA

End-to-end test each chain:
- **Deep Humanize**: input AI-generated text → output after 3 passes is less detectable than single-shot
- **Braindump → Docs**: input a 3-section braindump → response returns `files` array with ≥3 entries, each with `name` and non-empty `content`
- **Rewrite + Review**: input deliberately flawed text → review step flags ≥1 issue → final output addresses the flagged issue

Structural tests:
- No module outside `context/` reads files from `server/context/` directly
- No module outside `chain/` reads from `chain/definitions/` directly
- No chain definition references a context block name that doesn't exist in `manifest.json`
- No direct provider imports in any chain-related module — all calls through the adapter

Regression: run full existing test suite. Verify zero failures on single-shot modes (Rewrite, Expand, Compress, Clarify, Generate). Verify `OperationBarComponent` existing buttons still function identically.

WCAG-AA check on new UI elements: contrast ratios on chain buttons (locked state included), tab labels, step progress indicator.

---

## Success Criteria

- ✅ `POST /api/text/chain` accepts a `chainId` and runs the definition end-to-end
- ✅ Deep Humanize produces noticeably better output than single-shot Humanize (manual A/B on 3 samples)
- ✅ Braindump → Docs returns ≥3 linked markdown files from a 3-section braindump input
- ✅ Rewrite + Review self-corrects at least one issue flagged by the review step
- ✅ All three chains flow through the chain adapter — no direct provider imports (structural test passes)
- ✅ Context blocks loaded from repo files via manifest, not hardcoded in prompts
- ✅ Tabbed output renders correctly for multi-file chains
- ✅ Zero regressions on existing single-shot modes
- ✅ Feature-gated per user via `enabled_features.text_chains`
- ✅ `chainCompleted` event emitted on every chain run with `{ chainId, stepCount, inputLength, outputLength, totalTokens }`
- ✅ Chain-mode buttons show locked (not hidden) when `text_chains` disabled — null-object guard
- ✅ Structural tests pass: loader boundary, runner boundary, manifest consistency, adapter-only imports
- ✅ Chain endpoint registered as blueprint in `ENABLED_MODULES`
- ✅ `data-test` selectors on all new interactive elements

---

## Non-Goals

- ❌ User-editable context blocks
- ❌ Streaming per step
- ❌ Custom chain composition
- ❌ Cost dashboard
- ❌ Changes to existing 5 rewrite modes
- ❌ Per-chain feature gating (single `text_chains` flag for v1)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

