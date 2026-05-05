---
sidebar_position: 2
---

# Pipeline V3 — Epic

**Purpose**: Define scope and tasks for merging plan generation into task execution.

**Source Analysis**: See [Analysis](./analysis.md) for the bottleneck analysis that drives this work.

---

## Business Value

The spec-doc pipeline's throughput is gated by task spec generation. Each task burns 60K tokens and 3–5 minutes on a plan that the executor re-discovers anyway. For a 20-task epic, that's 1.2M tokens and 60–100 minutes of pure overhead — tokens and time that produce a document nobody reads because the executor agent builds its own mental model from the epic and architecture regardless.

Pipeline V3 eliminates this overhead by making the executor write its own plan as Step 0 of execution. The plan is the same 10-section format, lives in the same project folder, appears in the same sidebar — but it's written by the agent who will use it, not by a throwaway generation step. The token cost for pre-generation drops from 60K per task to zero. The task file becomes a living document: plan before execution, actual results after.

This is the difference between writing a recipe and cooking from it versus having the chef write the recipe as they cook. The chef's recipe is grounded in what they actually see in the kitchen.

---

## Scope

### What This Epic Covers

- V3 executor prompt template that merges plan-write, execution, and post-execution documentation
- Shared context loader module extracted from `regen-task.mjs` for reuse in `server.js`
- Upgraded `/api/ai/implement` endpoint with rich context injection (builder, principles, codebase, references, caveats, prior tasks)
- Post-execution task file update with actual commits, deviations, and test results
- Integration tests proving V3 produces valid task files and compatible deviation reports

### What This Epic Does NOT Cover

- Parallel task execution (multiple Claude CLI sessions against the same workspace)
- `--review-first` flag for interruptible plan review before execution
- Deprecation or removal of `regen-task.mjs` (it remains available for V2 workflows)
- Frontend redesign (sidebar already shows task files; no new components)
- Container mode changes (V3 changes the prompt, not the execution substrate)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Extract shared context loader** | None | — | 0.5 day | High |
| 2 | **Build V3 executor prompt template** | None | 1 | 1 day | High |
| 3 | **Upgrade /api/ai/implement endpoint** | 1, 2 | — | 1 day | High |
| 4 | **Wire post-execution task file update** | 3 | — | 0.5 day | Medium |
| 5 | **Integration tests and validation** | 3, 4 | — | 0.5 day | Medium |

### Task Details

#### Task 1: Extract shared context loader

Extract the context-loading logic from `regen-task.mjs` (lines 627–688) into a standalone module `scripts/context-loader.mjs`. This module exports functions to load the 5 global context files (builder.md, principles.md, codebase.md, references.md, caveats.md), project-specific files (epic.md, architecture.md), and prior-task summaries. `regen-task.mjs` is refactored to import from the shared module instead of inlining the logic. The existing `getBuilderBlock()`, `getPrinciplesBlock()`, `getCaveatsBlock()`, `getCodebaseBlock()`, `getReferencesBlock()`, and `getPriorTasksBlock()` helper functions (lines 93–166) also move into the shared module.

#### Task 2: Build V3 executor prompt template

Write the V3 executor prompt that merges plan generation, execution, and documentation into a single agent session. The prompt instructs the executor to: (1) **Step 0 — Plan**: write `task-N.v2.md` in the 10-section format (Context, Pre-flight, Files, Implementation Steps, Tests, Commit Plan, Verification, Rollback, Deviations Allowed, Out of Scope) to the project folder before touching any code; (2) **Steps 1–N — Execute**: follow its own plan, committing per the commit plan, logging `Deviation: <category> -- <description>` in commit bodies when reality diverges from plan; (3) **Final — Document**: update `task-N.v2.md` with an "Actual Results" appendix containing the real commit SHAs, deviation summary, and final test counts. The prompt inherits the 10-section template from `buildImplementationGuidePrompt()` (regen-task.mjs:350–544) but wraps it in the plan→execute→update lifecycle. It receives the same context blocks as the current generation prompt: builder, principles, codebase, references, caveats, prior tasks, epic excerpt, and full architecture.

#### Task 3: Upgrade /api/ai/implement endpoint

Modify the `/api/ai/implement` endpoint (server.js:1313–1518) to accept a `projectId` parameter instead of (or in addition to) raw `projectContext`. When `projectId` is provided, use the shared context loader from Task 1 to load all context files. Replace the current bare-bones implement prompt (server.js:1351–1381) with the V3 executor prompt from Task 2. Preserve the existing SSE streaming, keepalive, container mode, and client disconnect handling. Add a `v3` query parameter or request body flag so the old prompt remains available for backwards compatibility during transition.

#### Task 4: Wire post-execution task file update

After the executor's Claude CLI process exits successfully, parse the SSE output stream for the task file content. The executor writes `task-N.v2.md` to disk during execution (Step 0), but the "Actual Results" appendix written in the Final step may need to be captured from stdout if the executor can't write to the project folder directly. Add a post-execution hook in the `onComplete` handler (server.js:1416–1458) that reads the task file from disk, verifies it contains the 10 required sections, and — if the executor streamed an "Actual Results" section in stdout — appends it to the file. Log the task file path and section count in the SSE `done` event.

#### Task 5: Integration tests and validation

Add integration tests that verify the V3 pipeline end-to-end: (1) shared context loader returns all 5 global context blocks plus project-specific files; (2) V3 prompt template includes the plan→execute→update lifecycle instructions and the 10-section format; (3) `/api/ai/implement` with `projectId` produces valid SSE events; (4) task file written by executor contains all 10 sections; (5) `deviation-report.mjs` successfully parses commits from a V3 execution (same format compatibility). Use the mock AI provider (`AI_PROVIDER=mock`) for deterministic test execution. Extend `server.integration.test.js` with the new test cases.

---

## Success Criteria

- V3 execution produces a `task-N.v2.md` with all 10 required sections, written by the executor agent
- Total LLM calls per task drops from 2+ (generate via regen-task.mjs + execute via /api/ai/implement) to 1 (execute via /api/ai/implement with V3 prompt)
- `deviation-report.mjs` produces valid reports from V3 execution commits without modification
- Existing V2 workflow (`regen-task.mjs` → separate execution) continues to work unchanged
- Context loading is shared: `regen-task.mjs` and `server.js` both use `scripts/context-loader.mjs` with zero duplication
- Task file includes an "Actual Results" appendix with real commit SHAs, deviations, and test counts after execution completes

---

## Non-Goals

- Replacing or removing `regen-task.mjs` — it stays for V2 projects
- Parallel execution of multiple tasks (concurrent Claude CLI sessions)
- `--review-first` flag for human review between plan and execution
- Auto-review scoring of the executor's plan (quality is measured post-execution)
- Any frontend component changes — wiring only

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

