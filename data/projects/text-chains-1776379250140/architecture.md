---
sidebar_position: 3
---

# 🏗️ Text Chains — Architecture

**Purpose**: Technical design for chain operations.

**References**: See [Epic](./epic.md) for scope. See [Analysis](./analysis.md) for constraints.

---

## Overview

Text Chains adds three layers on top of the existing /text infrastructure: a context-block loader, a chain runner with step-handler dispatch, and chain definitions as static JSON. All three are server-side, inside their own module boundaries. The frontend extends the /text page with a second button row and a tabbed output area for multi-file results. No new services beyond the two new modules. No new database tables — existing `superapp_generations` gets two metadata columns (`chain_id`, `step_count`) via Alembic migration.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Feature = Bounded Context | Context loader and chain runner are separate modules with structural tests enforcing their boundaries |
| Adapter (every feature service) | Context loader is adapter-shaped: `CONTEXT_PROVIDER=mock` returns fixture strings. Chain runner calls Claude exclusively through the existing chain adapter |
| Strategy (AI providers) | Chain definitions declare operations by name; `STEP_HANDLERS` dispatch map resolves to the correct adapter call without if/elif |
| Observer (cross-feature events) | `chainCompleted` event emitted on every chain run — analytics subscribes without coupling to the runner |
| Feature Guard with Null Object | Disabled `text_chains` → locked buttons with "Pro" badge, never hidden. Backend returns 403 with upgrade hint, never 404 |
| Registry (feature flags) | `text_chains` in user's `enabled_features`. Blueprint registered in `ENABLED_MODULES`. Per-chain gating shape named but not built |
| Anti-Corruption Layer | File markers (`===FILE:===`) parsed server-side into structured `{name, content}` objects — LLM output format doesn't leak to frontend |

---

## System Boundaries

```
┌──────────────────────────────────────────────────────┐
│  /text page (Angular)                                 │
│  ┌─────────────────┐  ┌──────────────────────────┐   │
│  │ Single-shot keys │  │ Chain-mode keys (new)    │   │
│  │ Rewrite, Expand  │  │ Deep Humanize, BrainDump │   │
│  │ Compress, Clarify│  │ Rewrite+Review           │   │
│  │ Generate         │  │ [locked if !text_chains] │   │
│  └────────┬────────┘  └────────────┬─────────────┘   │
│           │                        │                  │
│  AiService.rewrite()    AiService.chainRun()          │
│  AiService.generate()   POST /api/text/chain          │
└───────────┼────────────────────────┼──────────────────┘
            │                        │
            ▼                        ▼
┌───────────────────┐   ┌──────────────────────────────┐
│  Existing text    │   │  chain.runner (new)           │
│  endpoints        │   │  ┌─────────────────────────┐ │
│  /api/ai/text/*   │   │  │ STEP_HANDLERS dispatch  │ │
│                   │   │  │ rewrite → handle_rewrite │ │
│                   │   │  │ generate → handle_generate│ │
│                   │   │  │ review  → handle_review  │ │
│                   │   │  └────────────┬────────────┘ │
│                   │   │               │              │
│                   │   │  Loads ChainDefinition JSON   │
│                   │   │  Loads context via loader     │
│                   │   │  Calls chain.adapter per step │
│                   │   │  Emits chainCompleted event   │
└───────────────────┘   └──────────────┬───────────────┘
                                       │
                        ┌──────────────┼──────────────┐
                        │              │              │
                        ▼              ▼              ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ chain.adapter│  │ context/     │  │ chain/       │
            │ (existing)   │  │ loader.py    │  │ definitions/ │
            │              │  │ manifest.json│  │ *.json       │
            │ → Claude API │  │ prompts/     │  └──────────────┘
            └──────────────┘  │ rubrics/     │
                              └──────────────┘
```

---

## Component Design

### Context Block Loader (`server/modules/context/loader.py`)

**Purpose**: Adapter-shaped module that resolves context-block names to markdown content.

**Interface**:
```python
def load_block(name: str) -> str
def load_blocks(names: list[str]) -> dict[str, str]
```

**Manifest** (`server/context/manifest.json`):
```json
{
  "humanize-pass-1": "prompts/humanize-pass-1.md",
  "humanize-pass-2": "prompts/humanize-pass-2.md",
  "humanize-pass-3": "prompts/humanize-pass-3.md",
  "braindump-lint": "prompts/braindump-lint.md",
  "braindump-to-docs": "prompts/braindump-to-docs.md",
  "builder": "prompts/builder.md",
  "principles": "prompts/principles.md",
  "references": "prompts/references.md",
  "quality-rubric": "rubrics/quality.md"
}
```

- Paths resolved relative to `server/context/`
- Missing block → `KeyError` with block name in message (fail loud, not silent empty string)
- Missing file on disk → `FileNotFoundError` with full path (catch mismatches between manifest and filesystem)
- **Mock mode**: `CONTEXT_PROVIDER=mock` returns deterministic fixture strings keyed by block name. Same interface, no file I/O. Controlled via env flag in `conftest.py`.

**Structural invariant**: only `context/loader.py` reads from `server/context/`. Enforced by grep-based structural test:
```python
def test_contextFiles_onlyReadByLoader():
    # grep server/ for open()/read_text() referencing server/context/ outside loader.py
    # fail: "Only context/loader.py may read from server/context/. Use loader.load_block(name)."
```

### Chain Runner (`server/modules/chain/runner.py`)

**Purpose**: Given a chain definition + user input, execute steps sequentially through the chain adapter.

**Step Handler Dispatch**:
```python
STEP_HANDLERS: dict[str, Callable] = {
    "rewrite": handle_rewrite,   # adapter.rewrite(text, mode, context)
    "generate": handle_generate, # adapter.generate(prompt, context)
    "review": handle_review,     # adapter.generate(review_prompt, context) → JSON
}
```

Adding a new operation = one function + one dict entry. The runner loop iterates `definition.steps`, looks up the handler by `step.op`, calls it with the current text + resolved context blocks, and passes the output as input to the next step. No if/elif. No switch-case.

**Multi-file parsing**: when `definition.outputMode == "multi-file"`, the runner scans the final step's output for `===FILE: {name}===` markers and splits into `[{name, content}]`. This is an anti-corruption layer: the LLM output format (marker-delimited) is parsed into a structured response before reaching the frontend.

**Observer**: on completion, emit `chainCompleted` signal:
```python
emit("chainCompleted", {
    "chainId": definition.id,
    "stepCount": len(definition.steps),
    "inputLength": len(user_input),
    "outputLength": len(final_output),
    "totalTokens": sum(step_tokens)
})
```
Mirrors the existing `outputCompleted` pattern from the UX revamp. Analytics, future cost dashboard, and usage-limit enforcement subscribe to this event without importing from the chain module.

**Error handling**: if any step fails, return `{ error: str, partialOutput: str, failedStep: int }`. Don't swallow the error. Don't retry (retry/backoff machinery is deferred infrastructure — trigger: when a real failure teaches us a retry budget).

**Structural invariant**: only `chain/runner.py` reads from `chain/definitions/`. Grep-based test:
```python
def test_chainDefinitions_onlyReadByRunner():
    # grep server/ for open()/json.load() referencing chain/definitions/ outside runner.py
    # fail: "Only chain/runner.py may read from chain/definitions/. Use runner.load_definition(chainId)."
```

**Deferred infrastructure** (not built, triggers named):
- `RunnerAdapter` interface → extract when a second execution strategy appears (parallel, streaming, retry)
- Per-chain feature gating resolver → extract when pricing tiers diverge per chain
- `chain_call` + `chain_signal` tables → extract when cost tracking becomes a reporting requirement, not just a logging concern

### Chain Definitions (`server/modules/chain/definitions/*.json`)

Chain definitions live **inside** the chain module boundary. Each definition is a JSON file:

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

**Schema fields**: `id` (string, unique, used as `chainId` in API), `name` (human-readable label for UI), `steps` (ordered array), `outputMode` (`"single"` or `"multi-file"`). Each step: `op` (must exist in `STEP_HANDLERS`), `mode` (optional, operation-specific), `context` (array of block names from manifest), `outputKey` (optional, names the output for downstream reference).

### API Endpoint (`POST /api/text/chain`)

**Request**: `{ chainId: string, input: string }`

**Response** (single-file): `{ generationId: string, result: string }`

**Response** (multi-file): `{ generationId: string, files: [{name: string, content: string}] }`

**Error** (feature-gated): `403 { error: "text_chains not enabled", upgrade: true }`

**Error** (chain not found): `404 { error: "Chain definition not found: {chainId}" }`

**Error** (step failure): `500 { error: string, partialOutput: string, failedStep: number }`

- Blueprint registered in `ENABLED_MODULES` — same registration pattern as existing feature modules
- Feature-gated via middleware: checks `user.enabled_features` for `text_chains`
- Persists to `superapp_generations` with `chain_id` + `step_count` columns
- Alembic migration adds the two columns (nullable, backfill not needed — existing rows have `NULL`)

### Frontend: Chain Mode UI

**AiService extension** (`src/app/services/ai.service.ts`):
```typescript
export interface ChainResponse {
  generationId: string;
  result?: string;
  files?: Array<{ name: string; content: string }>;
}

chainRun(chainId: string, input: string): Observable<ChainResponse> {
  return this.http.post<ChainResponse>(`${this.baseUrl}/chain`, { chainId, input });
}
```

**OperationBarComponent extension** (`src/app/components/operation-bar/operation-bar.component.ts`):
- Second `.operations` row with chain buttons
- Each button emits a `ChainOperationEvent` with `chainId`
- Buttons have `data-test` selectors: `data-test="chain-deep-humanize"`, `data-test="chain-braindump"`, `data-test="chain-rewrite-review"`
- **Null-object guard**: when `textChainsEnabled` input is `false`, buttons render with `opacity: 0.5`, "Pro" badge, click shows upgrade toast instead of executing
- **Step progress**: during chain execution, loading indicator shows "Step N of M..." (derived from chain definition step count + progress callback or polling)

**Tabbed output area** (new, within existing output region):
- Renders when response has `files` array
- Tab per file: label = `file.name`, content = `file.content`
- Copy-per-tab button with `data-test="chain-copy-tab"`
- Active tab tracked via signal, persists during session
- Single-file chains render in existing output area with no tabs

### Feature Guard — Null Object Fallback

| Layer | Behavior when `text_chains` disabled |
|-------|--------------------------------------|
| Frontend buttons | Visible, locked (`opacity: 0.5`), "Pro" badge, tap → upgrade toast |
| Backend endpoint | `403 { error: "text_chains not enabled", upgrade: true }` |
| Chain definitions | Still loaded (no conditional logic in runner init) |
| Context blocks | Still available (loader is independent of feature flags) |

Never hide. Never 404. The user knows the feature exists and what it costs to unlock.

---

## Execution Flow

```
[Phase 1 — Foundation]  (parallel)
   Task 1: Context Block Loader ──┐
   Task 2: Chain Runner + Endpoint─┤
                                   │
[Phase 2 — Chain Definitions]  (parallel, after Phase 1)
   Task 3: Deep Humanize ─────────┤
   Task 4: Braindump → Docs ──────┤
   Task 5: Rewrite + Review ──────┤
                                   │
[Phase 3 — UI]                     ▼
   Task 6: Chain Mode UI ─────────┤
                                   │
[Phase 4 — Verification]          ▼
   Task 7: Integration Test + QA
```

**Critical path**: Task 2 → Task 4 → Task 6 → Task 7 (longest chain: runner + braindump-to-docs is the most complex definition + UI integration + final QA).

**Parallel opportunity**: Tasks 1+2 are independent. Tasks 3+4+5 are independent once 1+2 complete.

---

## Design Decisions

| Decision | Choice | Why | Rejected |
|---|---|---|---|
| Chain defs as JSON files | Static JSON in `server/modules/chain/definitions/` | Versionable, reviewable, no DB schema, inside module boundary | DB-stored chains (premature — no user editing in v1), YAML (no tooling benefit), repo-root placement (violates bounded context) |
| Context blocks as markdown | Flat .md files + `manifest.json` | Human-readable, git-diffable, same shape as spec-doc's `builder.md`/`principles.md` | Structured YAML (overkill for v1), DB blobs (not versionable), inline in chain definitions (duplicates content across chains) |
| Single endpoint with chainId | `POST /api/text/chain` with `chainId` param | Scales to N chains without N routes; chain defs are data not code | Per-chain routes (route explosion), GraphQL (overkill for 3 operations) |
| Multi-file output via markers | `===FILE: name===` in LLM output, parsed server-side | Proven in spec-doc's generate-spec, single LLM call, no orchestration | Multiple LLM calls per file (expensive, slow), structured JSON output (LLM less reliable at producing valid JSON for long content) |
| Tabbed output in existing area | Tabs within the output region | No new page, no new route, minimal frontend scope | Accordion (harder to scan multi-file), download zip (loses in-app preview), new route (scope creep) |
| STEP_HANDLERS dispatch map | `dict[str, Callable]` | One function + one dict entry to add an operation. No if/elif. Readable, extensible | If/elif chain (grows with each op), class hierarchy (overengineered for 3 ops) |
| Observer for chainCompleted | Event emitted, subscribers decouple | Analytics, cost tracking, usage limits subscribe without importing chain module | Direct function calls (coupling), return value inspection (fragile) |
| Request-response (not SSE) | Synchronous response for v1 | Matches existing `/api/ai/text/rewrite` pattern, simpler error handling | SSE per step (deferred — trigger: chains exceeding 30s with user-reported perceived hangs) |

---

## Tech Stack (no changes)

```
Frontend: Angular 19 + Ionic 8 (existing /text page extended)
Backend:  Flask + chain adapter (existing) + runner (new) + context loader (new)
Storage:  Neon Postgres via SQLAlchemy (existing superapp_generations extended)
AI:       Claude API via chain adapter (existing)
```

No new dependencies. No new services. No new database tables.

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)

