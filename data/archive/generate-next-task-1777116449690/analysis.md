# 🔍 Generate Next Task — Analysis

## The Problem
`ImplementationGuideService.generateNextTask()` is complete and documented as serving two callers — the bootstrap loop and a sidebar action. Only the bootstrap loop exists. A user already hit the gap during E2E2, hand-writing a task because the loop couldn't be partially retried. The button is the missing caller, nothing else.

## Hard Constraints
- No new endpoint — existing `/api/ai/text/generate` (request/response, not SSE) is the only permitted transport.
- No new service — `ImplementationGuideService` is the sole service; AppComponent routes the action.
- Follow the existing `SidebarAction` union + handler pattern in `sidebar.component.ts` and `app.component.ts`.
- No modal, no streaming, no E2E test additions mid-E2E2 epic.

## Open Questions
- **Task targeting:** "Next missing task" (what the service does today) vs. "highlighted/specific task" (what original phrasing implied) — which is v1? Options: ship next-missing and defer picker; or block on adding `taskNum` param first.
- **Status surface:** Inline below the button, top-of-editor banner, or toast — which location? Inline is simplest; banner implies a layout slot that may not exist.
- **Post-generation focus:** Auto-jump to the generated file in the editor, or stay on current selection? Determines whether `this.activeFile = result.filename` is required behavior or optional.

## Dependencies & Sequencing
- `SidebarAction` union extension (`'generate-task'`) must land before button or handler — it's the shared type boundary.
- AppComponent handler and Sidebar button can be written in parallel once the type is extended.
- `canGenerateTask` predicate requires confirming the `epic.md` presence check is sufficient (no epic → disable) — verify no edge case where epic exists but is empty.

## Explicitly Out of Scope
- **Per-task picker UI** — no confirmed need for targeting a specific task number; one consumer doesn't justify the UI surface. Re-scope when user explicitly requests regenerating a non-next task.
- **`generateTaskByNum()` service extension** — no caller yet; defer until picker is confirmed in scope.
- **Streaming / SSE progress** — endpoint is request/response; speculative infrastructure. Re-scope if 30–90s waits produce support complaints.
- **E2E test additions** — E2E2 epic is in flight; mid-epic test extension is explicitly ruled out. Re-scope after E2E2 closes.
- **Bootstrap loop refactor** — already shares the service; nothing to change. Any refactor here is scope inflation with no current consumer benefit.