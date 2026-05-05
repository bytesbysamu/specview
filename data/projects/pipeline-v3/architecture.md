---
sidebar_position: 3
---

# Pipeline V3 — Solution Architecture

**Purpose**: Technical design for merging plan generation into task execution.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Pipeline V3 collapses two LLM sessions (plan generation + execution) into one. The key structural change is moving the planning intelligence from `regen-task.mjs` (a standalone script that calls `/api/ai/text/generate`) into the executor prompt consumed by `/api/ai/implement` (which spawns Claude CLI). The executor agent's first action is writing the task spec (the plan), then executing it, then updating it with actual results. The task file is the artifact — same 10-section format, same project folder, same sidebar rendering.

Three components change: (1) a shared context loader extracted from `regen-task.mjs` so both it and `server.js` can load the same 5 global + 2 project-specific context files; (2) a V3 prompt template that wraps the existing 10-section format in plan→execute→update lifecycle instructions; (3) an upgraded `/api/ai/implement` endpoint that accepts a `projectId`, loads context via the shared module, and sends the V3 prompt to Claude CLI.

Nothing else changes. The SSE streaming, keepalive, container mode, client disconnect handling, deviation reporting, and sidebar rendering all work as-is.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | No new infrastructure — reuse existing context files, endpoints, SSE streaming, and deviation format |
| Adapter pattern (shared context) | Context loading extracted into one module; both `regen-task.mjs` and `server.js` import the same adapter |
| Not-yet-built is the right state | No `--review-first` flag, no parallel execution, no plan scoring — defer until a real user asks |
| Executor Protocol contract | V3 produces the same 10-section format; deviation-report.mjs and sidebar work without changes |
| One agent, one pass | Planning and execution are the same LLM session — no lossy intermediary between planner and executor |

---

## Component Design

### Task 1: Shared Context Loader

**Purpose**: Eliminate duplication between `regen-task.mjs` and `server.js` for loading context files.

**Components**:
- `scripts/context-loader.mjs` **(new)** — Exports context-loading functions extracted from regen-task.mjs

**Public Interface**:
```javascript
// scripts/context-loader.mjs
export function loadGlobalContext()
// Returns: { builder, principles, codebase, references, caveats }
// Reads from repo root: builder.md, principles.md, codebase.md, references.md, caveats.md

export function loadProjectContext(projectId)
// Returns: { epic, architecture, projectCaveats }
// Reads from projects/{projectId}/: epic.md, architecture.md, caveats.md (optional)

export function loadPriorTasksSummary(projectDir, taskNum)
// Returns: string (markdown summary of completed tasks 1..taskNum-1)

export function getContextBlock(name, content)
// Returns: formatted prompt block (e.g., "## BUILDER CONTEXT\n{content}")
// Replaces: getBuilderBlock(), getPrinciplesBlock(), getCaveatsBlock(), etc.
```

**Extraction Source**: `regen-task.mjs` lines 93–166 (helper functions) and lines 627–688 (context loading in main flow).

**Patterns**: Adapter — one module, provider-agnostic interface. `regen-task.mjs` calls `loadGlobalContext()` instead of inlining `fs.readFileSync()` calls. `server.js` does the same.

### Task 2: V3 Executor Prompt Template

**Purpose**: Single prompt that instructs the executor to plan, execute, and document in one session.

**Components**:
- `scripts/v3-prompt.mjs` **(new)** — Exports `buildV3ExecutorPrompt(task, context)` function

**Prompt Structure**:
```
[1. Role + ONE Job statement — "You are an executor agent. Your job: plan, execute, document."]
[2. Builder Context block — from context-loader]
[3. Principles block — non-negotiable patterns]
[4. Caveats block — environment quirks]
[5. Codebase Context block — real paths from scan]
[6. References block — code to port]
[7. Prior Tasks block — already shipped]
[8. Phase 0: PLAN — "Write task-N.v2.md with the 10-section format"]
  [8a. 10-section template (reused from regen-task.mjs:360-524)]
  [8b. Hard rules (no absolute paths, no stubs, no placeholders)]
  [8c. "Save this file to {projectDir}/task-{num}-{slug}.v2.md"]
[9. Phase 1-N: EXECUTE — "Follow your own plan. Commit per commit plan."]
  [9a. Deviation logging protocol — "Deviation: <category> -- <desc>" in commit body]
  [9b. Deviation categories: stale-context, UX-silent, env-gap, commit-drift, positive-review-absorption]
[10. Final Phase: DOCUMENT — "Update task-N.v2.md with Actual Results appendix"]
  [10a. Actual commits (SHAs + messages)]
  [10b. Deviation summary (count per category)]
  [10c. Final test results (pass count, delta from pre-flight baseline)]
[11. Task-specific context from epic]
[12. Architecture excerpt (full)]
[13. Output format — first character must be #]
```

**Key Difference from V2 Prompt**: The V2 prompt (`buildImplementationGuidePrompt`, regen-task.mjs:350) produces a plan document only. The V3 prompt wraps the same 10-section format in a lifecycle: write the plan to disk → execute it → update it with actuals. The executor sees the plan as *its own working document*, not a spec delivered from elsewhere.

**Token Budget**: The V3 prompt is ~15% longer than the V2 generation prompt (adds ~2K chars for lifecycle instructions). But total pipeline tokens per task drop from ~120K (60K generate + 60K execute) to ~75K (one pass with richer context).

### Task 3: Upgraded /api/ai/implement Endpoint

**Purpose**: Replace the bare-bones implement prompt with V3's rich context + lifecycle prompt.

**Components**:
- `server.js` — Modified `/api/ai/implement` handler (lines 1313–1518)

**Changes**:
1. Accept `projectId` in request body (in addition to existing `projectContext`)
2. When `projectId` is present, call `loadGlobalContext()` + `loadProjectContext(projectId)` from context-loader
3. Extract task details from epic via `extractTasksFromEpic()` (ported from regen-task.mjs)
4. Build prompt via `buildV3ExecutorPrompt()` instead of the inline template
5. Add `v3: true` flag to request body for opt-in (default remains V2 for backwards compatibility)

**Preserved Behavior**: SSE headers, keepalive timer, `sendEvent()` helper, container mode branching, mock mode, client disconnect handler — none of these change.

**Request Body (V3)**:
```json
{
  "taskNum": 3,
  "taskName": "Photoshoot route",
  "projectId": "bubls2-1776263128609",
  "v3": true,
  "workspaceId": "optional-for-container-mode"
}
```

### Task 4: Post-Execution Task File Update

**Purpose**: Ensure the task file contains actual results after execution completes.

**Components**:
- `server.js` — Modified `onComplete` handler within `/api/ai/implement`

**Logic**: The executor (Claude CLI) has filesystem access and writes `task-N.v2.md` during its Plan phase (Step 0). It also updates the file during the Document phase (Final step). The `onComplete` handler's job is verification, not writing:

1. Read `projects/{projectId}/task-{num}-*.v2.md` from disk
2. Verify all 10 sections are present (regex scan for `## 1. Context` through `## 10. Out of Scope`)
3. Verify "Actual Results" appendix exists (added by executor in Final phase)
4. If the appendix is missing (executor didn't get to the final step — e.g., CLI timeout), parse the SSE output buffer for any `## Actual Results` content and append it to the file
5. Include task file path and section count in the SSE `done` event payload

**Fallback**: If the executor fails before writing the plan (Step 0 never completes), no task file exists. The `done` event reports `success: false` with no task file path. This is the same behavior as V2 — a failed execution produces no artifact.

### Task 5: Integration Tests

**Purpose**: Prove V3 works end-to-end with the mock provider.

**Components**:
- `server.integration.test.js` — Extended with V3 test cases

**Test Cases**:

| Test | What It Proves |
|------|---------------|
| `contextLoader_loadGlobalContext_returns5blocks` | Shared module reads all context files |
| `contextLoader_loadProjectContext_readsEpicAndArch` | Project-specific files loaded correctly |
| `contextLoader_missingCaveats_returnsFallback` | Per-project caveats falls back to global |
| `v3Prompt_includesLifecyclePhases` | Prompt contains Plan, Execute, Document phases |
| `v3Prompt_includes10SectionTemplate` | All 10 required sections present in prompt |
| `apiImplement_withProjectId_loadsContext` | Endpoint uses context-loader when projectId provided |
| `apiImplement_v3Flag_usesV3Prompt` | V3 prompt template selected when `v3: true` |
| `apiImplement_noV3Flag_usesLegacyPrompt` | Backwards compatibility: V2 prompt when flag absent |
| `onComplete_verifiesTaskFileSections` | Post-execution hook checks for 10 sections |
| `deviationReport_parsesV3Commits` | deviation-report.mjs works on V3 commit format |

---

## Execution Flow

```
[Phase 1: Foundation]
   Task 1 (context-loader.mjs) ──→  Task 2 (v3-prompt.mjs)
   Extract context loading           Build V3 prompt template
   from regen-task.mjs               Reuse 10-section format
              │                              │
[Phase 2: Integration]               ────────┘
              ▼
   Task 3 (upgrade /api/ai/implement)
   Wire context loader + V3 prompt
   Add projectId + v3 flag
              │
[Phase 3: Polish]
              ▼
   Task 4 (post-execution update) ──→ Task 5 (integration tests)
   Verify task file on disk            Prove end-to-end with mock
   Append actuals if needed            Prove deviation compatibility
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Shared module vs inline duplication | Shared `scripts/context-loader.mjs` | Context loading logic is 100+ lines in regen-task.mjs; duplicating into server.js doubles maintenance surface. One module, two consumers |
| V3 prompt in separate file vs inline | Separate `scripts/v3-prompt.mjs` | Prompt is ~200 lines; inline in server.js would push it past 1800 lines. Separate file enables testing the prompt in isolation |
| Opt-in via `v3: true` flag vs default | Opt-in flag | V2 callers (if any) keep working. V3 is additive. Remove the flag and make V3 default after validation |
| Executor writes plan to disk vs server writes | Executor writes (Claude CLI has filesystem access) | The executor needs to reference its own plan during execution. Writing it as Step 0 means the plan is on disk when the executor starts coding. Server doesn't need to parse stdout for plan content |
| Post-execution verification vs trust executor | Verify on disk, append actuals if missing | Executor may timeout before the Final phase. Verification catches partial execution. But it's lightweight — just a regex check, not re-generation |
| Keep regen-task.mjs alive vs deprecate | Keep alive, no changes except import refactor | regen-task.mjs is battle-tested for V2 projects. Breaking it for V3 serves no one. The shared context loader means it gets *simpler*, not broken |

---

## Data Flow

```
Request:
  { projectId, taskNum, taskName, v3: true }
          │
          ▼
  context-loader.mjs
  ┌─────────────────────────────┐
  │ loadGlobalContext()         │ → builder, principles, codebase, references, caveats
  │ loadProjectContext(id)      │ → epic, architecture, projectCaveats
  │ loadPriorTasksSummary(dir,n)│ → prior tasks markdown
  └─────────────────────────────┘
          │
          ▼
  v3-prompt.mjs
  ┌─────────────────────────────┐
  │ buildV3ExecutorPrompt(      │
  │   task, context             │
  │ )                           │
  └─────────────────────────────┘
          │
          ▼
  Claude CLI (claude -p --output-format text)
  ┌─────────────────────────────┐
  │ Step 0: Write plan to disk  │ → projects/{id}/task-N-{slug}.v2.md
  │ Steps 1-N: Execute plan     │ → code changes + commits with Deviation: lines
  │ Final: Update plan with     │ → append Actual Results appendix to task file
  │        actual results       │
  └─────────────────────────────┘
          │
          ▼
  onComplete handler
  ┌─────────────────────────────┐
  │ Verify task file on disk    │ → 10 sections + Actual Results present?
  │ Append actuals if missing   │ → fallback for executor timeout
  │ Send SSE done event         │ → { success, taskFilePath, sectionCount }
  └─────────────────────────────┘
```

---

## File Inventory

### New Files
| File | Purpose | Size Estimate |
|------|---------|---------------|
| `scripts/context-loader.mjs` | Shared context loading for regen-task.mjs and server.js | ~150 lines |
| `scripts/v3-prompt.mjs` | V3 executor prompt builder | ~250 lines |

### Modified Files
| File | Change |
|------|--------|
| `scripts/regen-task.mjs` | Replace inline context loading with imports from context-loader.mjs. ~60 lines removed, ~10 lines of imports added |
| `server.js` | Upgrade `/api/ai/implement` handler: add projectId support, V3 prompt, post-execution verification. ~80 lines modified |
| `server.integration.test.js` | Add 10 V3-specific test cases. ~120 lines added |

### Unchanged Files
| File | Why |
|------|-----|
| `scripts/deviation-report.mjs` | V3 commits use the same `Deviation:` format — no changes needed |
| `specs/system-prompts.md` | Document the V3 prompt in v3-prompt.mjs, not in the legacy prompt reference |
| `src/app/` | Frontend components render task files from disk — format doesn't change |
| `server/walker.ts` | Codebase scanning is orthogonal to V3 |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
- [Timeline](./timeline.md)

