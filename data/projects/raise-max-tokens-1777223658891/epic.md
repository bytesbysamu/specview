# 🎯 Epic: Raise max\_tokens

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Long-form document generation is the core value delivery of Spec Doc. When the CLI provider silently discards the `max_tokens` parameter, implementation guides and architecture documents are truncated at the model's default ceiling — mid-sentence, mid-header, no error, no signal. The user receives a broken document and has no way to know whether it is complete. This is the single highest-frequency quality failure in the tool today, and it is caused by a one-line omission in the provider layer that has existed since the CLI provider was first written.

Fixing the provider unblocks two in-flight epics: the linter brain dump's structured prior-context contracts require full §3 and §5 content from previous tasks, which truncated impl guides cannot supply; and the bootstrap async migration's per-step `max_tokens` tuning in `BOOTSTRAP_WORKFLOW` is a no-op against the live binary until the provider actually forwards the flag. Both epics compound in value only when the underlying truncation is resolved.

A truncation heuristic that writes the file and appends a `warnings` field — rather than surfacing an error or silently shipping the fragment — gives users the lowest-friction path: inspect the partial output, decide whether to regenerate, and do so against a ceiling that now works. The alternative paths (auto-retry, hard failure) are explicitly rejected per the analysis.

**Value Proposition**: Eliminate silent document truncation so long-form generators deliver complete output and downstream epics that depend on full prior-context can ship.

---

## Scope

### What This Epic Covers

- **CLI provider flag forwarding** — ensuring `--max-tokens` is included in every subprocess invocation so the binary honours the caller's ceiling
- **Call-site ceiling raises** — setting 16 384 tokens on the architecture step and impl-guide generation, the two call sites whose output regularly exceeds 4 096 tokens
- **Truncation heuristic** — a lightweight, post-call check in `task_gen/service.py` that detects likely truncation and populates a `warnings` list on the task state
- **API contract for `warnings`** — adding the `warnings` array to the task-status response in `openapi.yaml` and regenerating DTOs, so the field is a first-class part of the polling contract (conditional: only if the field does not already exist)

### What This Epic Does NOT Cover

- ❌ **Timeout increases** — no specific files, layers, or current values have been identified; re-scope after a concrete inventory exists
- ❌ **Streaming output** — owned by `braindump-streaming-task-gen.md`; supersedes the synchronous fix once shipped
- ❌ **Auto-retry on truncation (option b)** — deferred to a future auto-recovery brain dump
- ❌ **Anthropic SDK provider** — `max_tokens` already works there; no change needed
- ❌ **Token-cost accounting** — owned by `braindump-multi-provider-cost-visibility.md`
- ❌ **`analysis` and `epic` prompt ceilings** — fit within 4 096 today; no change
- ❌ **Angular warning badge** — frontend consumer of the `warnings` field; out of scope for this API epic

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Fix CLI Provider: Forward `--max-tokens`** | CLI binary must support flag | — | 0.5 days | High |
| 2 | **Raise Call-Site Ceilings to 16 384** | Task 1; `AICall.max_tokens` plumbing confirmed present | — | 0.5 days | High |
| 3 | **Add Truncation Heuristic + Warnings State** | Task 2 | — | 1 day | High |
| 4 | **Expose `warnings` in OpenAPI Contract** | Task 3; conditional on field being absent | Task 3 (schema work precedes DTO regen) | 0.5 days | High |

### Task 1: Fix CLI Provider — Forward `--max-tokens`

The `max_tokens` parameter is accepted by `cli.py` but never forwarded to the subprocess; every call runs at the binary's built-in default ceiling. Before the code change ships, the deployed CLI binary must be confirmed to accept `--max-tokens`; if not, a CLI upgrade is a hard prerequisite. This task is a blocking dependency for all subsequent tasks — a caller that passes 16 384 before this lands receives no benefit.

**Port budget**: One file (`modules/chain/providers/cli.py`), two-line change. No new abstractions.

---

### Task 2: Raise Call-Site Ceilings to 16 384

The architecture step in the bootstrap workflow and the impl-guide generation in `task_gen/service.py` are the two call sites whose output regularly exceeds 4 096 tokens. This task confirms that `AICall.max_tokens` plumbing already threads through to the chain call (per bootstrap epic Task 1.2) and, if so, sets the ceiling to 16 384 at those two sites only. If the plumbing is absent, it must be added here before the ceiling values matter.

**Port budget**: Two call sites across two files; no new logic, only constant changes.

---

### Task 3: Add Truncation Heuristic and Warnings State

After the chain call returns, a lightweight heuristic in `task_gen/service.py` checks for signals of truncation — unbalanced code fences, absence of terminal punctuation on the final line, output below a minimum length — and appends a human-readable entry to a `warnings` list. The file is written regardless; partial output is preferable to no output. The `warnings` list is stored on the task state object so the polling endpoint can return it to callers.

**Port budget**: One service file; the heuristic is self-contained and does not touch the chain layer or file-writing logic beyond the warnings annotation.

---

### Task 4: Expose `warnings` in OpenAPI Contract

Conditional on `warnings` being absent from the current task-status response schema: add the field to `openapi.yaml`, regenerate `dtos/models.py`, and verify the structural route-handler test passes. If the field already exists, this task is a no-op and can be closed during sprint planning. This is the prerequisite for any frontend consumer — including the Angular badge deferred to a future epic — to treat `warnings` as a stable contract rather than an undocumented field.

**Port budget**: `openapi.yaml` schema addition plus a `make generate-dtos` run; no new route handlers required.

---

## Success Criteria

- ✅ A `chain_adapter.generate(system, user, max_tokens=16384)` call against the live binary produces output that exceeds 4 096 tokens when the model has more to say
- ✅ The architecture step and impl-guide generation no longer truncate mid-document on inputs that previously triggered the 4 096 ceiling
- ✅ A task whose output triggers the truncation heuristic has `warnings: ["output may be truncated — ran into max_tokens ceiling"]` in its polling response
- ✅ A task whose output does not trigger the heuristic has `warnings: []` in its polling response
- ✅ `openapi.yaml` declares the `warnings` field on the task-status response; `make check-dtos` passes
- ✅ All 192 existing tests continue to pass; no regression in tasks that run within 4 096 tokens

---

## Non-Goals

- ❌ **Auto-retry on truncation** — the write-plus-warn strategy is closed; retry logic belongs in a dedicated auto-recovery epic
- ❌ **Timeout increases** — excluded until a specific list of files, layers, and current values is produced
- ❌ **Streaming** — the synchronous fix ships in days; streaming is a separate, larger effort that supersedes it
- ❌ **Angular warning badge** — this epic ends at the API contract; frontend integration is a separate deliverable

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview