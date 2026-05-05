# 🏗️ Solution Architecture: Raise max\_tokens

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The root cause is a broken contract at the provider boundary. `chain/adapter.py` is the single import path for all AI calls and correctly threads `max_tokens` as a parameter to whichever provider is active. The CLI provider (`modules/chain/providers/cli.py`) accepts that parameter in its function signature and then silently drops it — the subprocess invocation never carries `--max-tokens` to the binary. Every call that passes a ceiling higher than the binary's built-in default is quietly ignored. The fix lives entirely in that provider.

Raising the ceiling at the provider layer is necessary but not sufficient. Two call sites — the architecture step in the bootstrap workflow and the implementation-guide generation in `task_gen/service.py` — must explicitly pass 16 384 tokens, because the ceiling only takes effect if the caller asks for it. These are the only two sites identified by the analysis as regularly producing output that exceeds 4 096 tokens; all other call sites stay at today's defaults to avoid unnecessary latency and cost increases.

The third layer of the fix is a post-call quality gate. Even with a raised ceiling, truncation can happen — models have hard limits, prompts can be unexpectedly long, and future call sites may not yet be tuned. A lightweight heuristic in `task_gen/service.py` inspects the raw output text, populates a `warnings` list on the task state if truncation signals are present, and writes the file regardless. The `warnings` field is then surfaced via the polling endpoint, making it a first-class part of the task-status contract rather than an internal implementation detail.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Single adapter boundary | All AI calls flow through `chain/adapter.py`. The provider fix is invisible to call sites; they pass `max_tokens` to the adapter and the adapter delegates to whichever provider is active. No call site imports the CLI provider directly. |
| Surgical targeting | Only the two call sites whose output demonstrably exceeds 4 096 tokens receive raised ceilings. A global ceiling raise would silently increase latency and cost for all calls, including short ones that never approach the limit. |
| Write-then-warn | Partial output is more useful than no output. The truncation heuristic is additive — it annotates the task state; it does not block file writes or surface an error to the caller. |
| Heuristic, not deterministic | The CLI binary's response does not include a machine-readable truncation signal. Detection is inferred from the text itself. The heuristic accepts false positives (a yellow warning on a complete document) in preference to false negatives (a silently broken document with no warning). |
| Additive schema changes | `warnings` is a list, not a boolean, so future heuristics can append additional entries without requiring a schema version. The field is absent today; adding it is a backwards-compatible extension of the task-status response. |

---

## System Boundaries

### What This System Includes

- **CLI provider flag forwarding** — `modules/chain/providers/cli.py` forwarding `--max-tokens` to the subprocess so the binary honours the caller's ceiling
- **Call-site ceiling configuration** — explicit 16 384-token values at the architecture step (`modules/spec_gen/workflows/generate_spec.py`) and implementation-guide generation (`modules/task_gen/service.py`)
- **Truncation heuristic** — a post-call text inspection function in `task_gen/service.py` that populates `warnings` on the task state object
- **OpenAPI `warnings` contract** — the `warnings` array declared on the task-status response in `openapi.yaml` and reflected in the regenerated `dtos/models.py`

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Timeout increases | No specific files, layers, or current values have been identified. Scoping timeout work without a concrete inventory produces the wrong changes in the wrong places. Deferred until an inventory exists. |
| Streaming output | Owned by `braindump-streaming-task-gen.md`. Streaming supersedes the synchronous fix architecturally but is a larger, separate effort. This system ships in days; streaming ships in weeks. |
| Auto-retry on truncation | The write-then-warn decision is closed. Auto-retry logic belongs in a dedicated auto-recovery brain dump where the restart-loop risk can be addressed properly. |
| Anthropic SDK provider | `max_tokens` already works in the SDK provider. No parity fix is needed there. |
| Angular warning badge | The badge is a frontend consumer of the `warnings` field. This system ends at the API contract. The badge is a separate deliverable. |
| Token-cost accounting | Owned by `braindump-multi-provider-cost-visibility.md`. Usage tracking is a cross-provider concern that goes beyond this fix. |
| `max_tokens` for analysis and epic prompts | Both fit within 4 096 tokens today. Raising them unnecessarily would increase cost with no quality benefit. |

---

## Component Design

### CLI Provider (`modules/chain/providers/cli.py`)

**Purpose**: Translate the `max_tokens` parameter — already accepted by `create_message` and already threaded through `chain/adapter.py` — into the `--max-tokens` flag on the subprocess invocation. The parameter has been present in the function signature since the provider was written; the gap is only in what gets passed to the binary.

**Key Parts**:

- `create_message` — the function that constructs and executes the subprocess command. The flag is added to the command list unconditionally so the binary always receives an explicit ceiling rather than falling back to its built-in default. This is the only change in this file.

**Patterns**: Provider implementation behind the adapter boundary (ELA Pattern #1). The adapter is the sole caller; no other component imports the CLI provider directly. The fix is invisible to all call sites — they already pass `max_tokens` to the adapter.

**Prerequisite**: The deployed CLI binary must accept `--max-tokens`. If it does not, a binary upgrade is a hard prerequisite before this change can ship. Shipping the flag to a binary that rejects it produces an error on every call.

---

### Architecture Step Call Site (`modules/spec_gen/workflows/generate_spec.py`)

**Purpose**: Raise the ceiling for the architecture-generation step in the bootstrap workflow to 16 384 tokens. The `AICall` structure that defines this step already carries a `max_tokens` field per the bootstrap async migration's Task 1.2; the change here is the value, not the mechanism.

**Key Parts**:

- The `architecture` step's `AICall` — the compile-time declaration that sets the per-step ceiling. Consumer: the bootstrap workflow executor, which reads `max_tokens` from each `AICall` and passes it to the chain adapter.

**Why this site specifically**: The architecture step is identified in the analysis as the highest-frequency source of truncation. Its output is structurally long — it must cover overview, components, decisions, and flows in a single generation. The 4 096 default was never adequate for non-trivial projects.

---

### Implementation-Guide Call Site (`modules/task_gen/service.py`)

**Purpose**: Raise the ceiling for implementation-guide generation to 16 384 tokens. This is the call site that produced the observed failure — Task 1 of the Workflows project was cut mid-header at 65 lines.

**Key Parts**:

- The `chain_adapter.generate` invocation in the implementation-guide path — the direct call that becomes the vehicle for the raised ceiling. Consumer: any workflow step that triggers implementation-guide generation via `task_gen/service.py`.

**Why this site specifically**: Implementation guides are the longest-form output in the system. They must cover purpose, prerequisites, step-by-step design decisions, and verification criteria. Unlike analysis or epic documents, which are bounded summaries, implementation guides grow with the complexity of the task they describe.

---

### Truncation Heuristic (`modules/task_gen/service.py`)

**Purpose**: Detect likely truncation from the raw output text after the chain call returns, without any additional model call or API round-trip. Populate a `warnings` list on the task state so the polling endpoint can surface it to callers.

**Key Parts**:

- `_looks_truncated` — a pure function that inspects the output text against three signals: output length below a minimum threshold (suspiciously short output is likely truncated), unbalanced code fences (an odd number of triple-backtick markers means the model stopped mid-block), and terminal-line punctuation absence (the last non-empty line ends without a sentence-terminal or structure-terminal character).
- `warnings` annotation in `run_generation` — the post-call site that calls the heuristic, constructs the warnings list, writes the file, and stores the list on the task state. The file is written regardless of the heuristic's verdict.

**Patterns**: Quality gate as a post-call annotation. The heuristic does not intercept or modify the chain call; it inspects only the result. Write-then-warn: the caller always receives output; the warning is additive context, not a failure mode.

**Why these three signals**: Each is detectable from the text string in constant time with no external dependencies. Together they cover the observed failure modes: a model that hits its ceiling mid-sentence (terminal punctuation check), mid-code-block (fence balance check), or produces a suspiciously short document (length check). False positives (a legitimate document that ends without punctuation) produce a dismissible yellow badge; false negatives (a truncated document that passes all three checks) produce a silently broken document — the same state as today. The heuristic trades false positives for false negatives deliberately.

---

### Task State and OpenAPI Contract (`openapi.yaml`, `dtos/models.py`)

**Purpose**: Make `warnings` a first-class field on the task-status response so any consumer — including the Angular badge deferred to a future epic — can treat it as a stable contract rather than an undocumented field.

**Key Parts**:

- `openapi.yaml` task-status response schema — the authoritative declaration of the `warnings` field as an array of strings, present on every task-status response (empty list when no warnings are detected).
- `dtos/models.py` — the generated DTO file that reflects the schema. Never hand-edited; regenerated via `make generate-dtos` after the schema change.

**Patterns**: Schema-first contract. The DTO is derived from the OpenAPI declaration, not the other way around. This ensures the polling endpoint's response shape is always consistent with what `openapi.yaml` declares, and what `make check-dtos` validates.

**Why a list, not a boolean**: A boolean encodes only presence or absence. A list allows multiple heuristics to append independent warnings (e.g., a future "context length exceeded" signal from the adapter layer) without a schema change. The cost is trivial — an empty list serialises to `[]`; a boolean false serialises to `false` — and the flexibility is permanent.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| AI provider | Claude CLI binary via subprocess | Already the production provider. The fix is a flag addition to an existing subprocess invocation; no new technology introduced. |
| Adapter boundary | `modules/chain/adapter.py` | The single import path per project rules. All call sites already use it; the provider fix is transparent to them. |
| Heuristic runtime | Python string operations | The three truncation signals (length, fence balance, terminal punctuation) are all O(n) string operations. No model call, no external service, no additional dependency. |
| API contract | OpenAPI 3.x + generated DTOs | Already the contract mechanism for the entire API. The `warnings` addition follows the same schema-first, generate-then-commit pattern used for all other fields. |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Write-then-warn rather than auto-retry or hard failure | Partial output is inspectable and often useful. Auto-retry carries restart-loop risk — the model frequently restarts rather than continuing. Hard failure forces a manual loop on every truncation event, defeating the purpose of a quality heuristic. | A user who receives a truncated document with a warning must decide whether to regenerate manually. Auto-retry, if it worked reliably, would be more seamless. That reliability cannot be assumed. |
| Two named call sites at 16 384, not a global ceiling raise | The analysis identifies exactly two call sites as the sources of observed truncation. A global raise silently increases token consumption — and therefore latency and cost — for all calls, including analysis and epic prompts that fit comfortably in 4 096. | If a third call site emerges as a truncation source, it must be raised explicitly. There is no safety net for undiscovered sites. The alternative (global raise) provides that net at a cost paid on every call. |
| Sequential prerequisite ordering (provider fix before ceiling raise) | If the ceiling raise ships before the provider fix, callers that pass 16 384 receive no benefit — the binary still runs at its default. The change is a silent no-op, not a detectable failure, which makes the bug harder to diagnose. | Sequential ordering means Task 2 cannot ship until Task 1 is confirmed live. Parallel development is possible but deployment is gated. |
| Heuristic detection rather than a binary-provided signal | The CLI binary does not expose a machine-readable truncation field in its output. The only signal available is the text itself. A model API call to ask "was this truncated?" would add latency, cost, and a second failure mode. | The heuristic has false positive and false negative cases. False positives produce unnecessary warnings; false negatives produce silently broken documents. The heuristic reduces false negatives at the cost of some false positives. |
| `warnings` as a list of strings, not a boolean or enum | A list is the most extensible representation. Future heuristics can append entries; callers that only care about presence can check `len(warnings) > 0`; callers that want to display context have the string content. A boolean would require a schema change to add context; an enum would require a schema change to add new warning types. | A list is slightly more verbose to serialise and check than a boolean. For a field that is empty on the vast majority of task responses, this overhead is negligible. |

---

## Execution Flow

The four tasks execute in dependency order. Tasks 1 and 2 are sequentially dependent on deployment (the ceiling raise is a no-op until the provider fix is live). Tasks 3 and 4 are sequentially dependent on Task 2 (the heuristic has no effect until larger output is actually being generated, and the OpenAPI field is meaningless until the heuristic populates it). Within each task, the work is confined to the files named in the component design.

```
Phase 1 — Provider Fix
  CLI provider flag forwarding (cli.py)

Phase 2 — Ceiling Raise  [requires Phase 1 deployed]
  Architecture step ceiling (generate_spec.py)
  Impl-guide ceiling (task_gen/service.py)

Phase 3 — Quality Gate  [requires Phase 2]
  Truncation heuristic + warnings state (task_gen/service.py)

Phase 4 — Contract  [requires Phase 3]
  OpenAPI warnings field (openapi.yaml → dtos/models.py)
```

The structural route-handler test (`everyOpenapiPath_hasRouteHandler`) passes throughout — Phase 4 adds a field to an existing response schema, not a new path. No new route handlers are required.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview