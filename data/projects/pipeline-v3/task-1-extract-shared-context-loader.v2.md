# Task 1: Extract Shared Context Loader

## 1. Context
The context-loading logic (builder, principles, codebase, references, caveats, epic, architecture, prior tasks) is duplicated — `regen-task.mjs` has it inline, `server.js` has a separate version. Extract into `scripts/context-loader.mjs` so both consumers share one module.

**Trade-offs**: separate npm package (overkill), copy to server/ (wrong — scripts/ is the tooling layer), shared module in scripts/ (right — both consumers are Node scripts).

## 2. Pre-flight
- `git status` — confirm clean
- Verify `scripts/regen-task.mjs` lines 93-166 (helper functions) and 430-440 (context loading)

## 3. Files
**Create:** `scripts/context-loader.mjs`
**Modify:** `scripts/regen-task.mjs` (import from context-loader instead of inline)
**Leave alone:** `server.js` (Task 3 wires it there)

## 4. Implementation Steps
1. Create `scripts/context-loader.mjs` — export: `loadGlobalContext(repoRoot)`, `loadProjectContext(projectDir)`, `loadPriorTasks(projectDir, currentTaskNum)`, plus all `get*Block()` formatters
2. Refactor `regen-task.mjs` — replace inline helpers + loading with imports from context-loader
3. Verify: `node scripts/regen-task.mjs --help` still works

## 5. Tests
- Existing `regen-task.test.mjs` must still pass
- Add `scripts/context-loader.test.mjs`: loadGlobalContext returns all 5 blocks, loadProjectContext reads epic+arch, get*Block formatters handle null/empty

## 6. Commit Plan
1. `refactor(pipeline): extract context-loader.mjs from regen-task.mjs`

## 7. Verification
`node --test scripts/context-loader.test.mjs && node --test scripts/regen-task.test.mjs`

## 8. Rollback
Revert the single commit.

## 9. Deviations Allowed
If helper function signatures differ slightly, adapt. If regen-task has logic beyond simple loading (e.g. rescan), keep that in regen-task, only extract pure loading.

## 10. Out of Scope
Do NOT modify server.js. Do NOT change the prompt template. Do NOT touch the CLI provider.
