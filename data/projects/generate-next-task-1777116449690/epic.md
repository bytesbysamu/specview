# 🎯 Epic: Generate Next Task

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

`ImplementationGuideService.generateNextTask()` has been production-ready since the bootstrap loop shipped, but it has no explicit per-project caller. During the E2E2 epic, a bootstrap timeout forced the user to write a task by hand — not because the AI couldn't produce it, but because the only available trigger (the bootstrap loop) regenerates *all* tasks together, making partial retry impossible. The subprocess deadlock that caused the timeout has since been fixed, yet the gap remains: there is no way to generate a single missing task without rerunning the entire bootstrap.

This epic closes that gap with the smallest possible surface: one sidebar button that calls the service the user already has. The payoff is immediate — any time a task file is absent, stale, or manually deleted for a redo, the user can regenerate it in one click without touching the new-project flow. That directly supports the dogfooding workflow where spec-doc is built *with* spec-doc, and iteration on any single task should be cheap.

The value is not a new AI capability but the availability of an existing one at the right moment. Faster iteration on individual tasks reduces the friction between "epic defined" and "implementation guide in editor", which is the core loop the tool is designed to accelerate.

**Value Proposition**: One sidebar button makes per-task generation a first-class action, turning a bootstrap-only operation into an on-demand retry at any point in a project's lifecycle.

---

## Scope

### What This Epic Covers

- **`SidebarAction` union extension** — adds `'generate-task'` as a typed action, establishing the shared contract between sidebar and host
- **Sidebar button with disabled and busy states** — visible when a project is selected; disabled when no `epic.md` exists or generation is in flight; shows an in-progress label during the call
- **AppComponent handler** — routes the action to the service, refreshes project state on success, selects the new file, and surfaces inline status for success, "all tasks done", and error outcomes
- **Karma unit spec** — covers action emission from the button and the service-call shape, consistent with existing sidebar action specs

### What This Epic Does NOT Cover

- ❌ **Per-task targeting UI (picker)** — the service finds the *next missing* task; a picker for regenerating a specific task number requires a separate UI surface and a confirmed user need. Re-scope when the user explicitly requests it.
- ❌ **`generateTaskByNum()` service extension** — no caller yet; the service extension is minor but the UI surface to drive it is not confirmed. Defer until the picker is in scope.
- ❌ **Streaming / SSE progress** — the existing `/api/ai/text/generate` endpoint is request/response; a spinner with a label is the correct floor. Upgrade if wait-time complaints surface.
- ❌ **E2E test additions** — the E2E2 epic is in flight; extending it mid-cycle is explicitly ruled out. Log as a follow-up after E2E2 closes.
- ❌ **Bootstrap loop refactor** — the loop already calls the service; nothing to change. Any modification here is scope inflation with no current consumer benefit.

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Extend SidebarAction union** | None | — | 0.5 days | High |
| 2 | **Add sidebar button** | 1 | 3 | 0.5 days | High |
| 3 | **Add AppComponent handler** | 1 | 2 | 1 day | High |
| 4 | **Add Karma unit spec** | 2, 3 | — | 0.5 days | High |

### Task 1: Extend SidebarAction Union

Adds `'generate-task'` to the `SidebarAction` union type in `sidebar.component.ts`, establishing the shared type boundary that Tasks 2 and 3 depend on. This is the only change required to unblock parallel frontend work. No component logic, no template changes, no new inputs — the single type addition is the entire deliverable.

**Port budget**: ~1 line in `sidebar.component.ts`; deliberately excludes any input properties, template markup, or handler stubs — those belong to Tasks 2 and 3 respectively.

### Task 2: Add Sidebar Button

Renders a "Generate Next Task" button inside the existing `<div class="sidebar-actions">` block and wires two new `@Input()` bindings — `canGenerateTask` and `generatingTask` — that control its enabled and busy states. The button emits the `'generate-task'` action on click. This task owns everything the sidebar component is responsible for and nothing the host is responsible for.

**Port budget**: ~15 lines in `sidebar.component.ts` (template + two inputs); excludes `canGenerateTask` logic (computed in AppComponent, not sidebar) and excludes any state management beyond the two inputs.

### Task 3: Add AppComponent Handler

Adds a `case 'generate-task'` branch to the existing sidebar action router in `app.component.ts`. The handler sets a `generatingTask` flag, calls the service with the active project's ID and name, and on completion refreshes the project file list, selects the generated file in the editor, and surfaces an inline status message. The `canGenerateTask` predicate — true when an active project with an `epic.md` exists — is also computed here and passed down as the sidebar input added in Task 2. Error and "all tasks done" paths each produce a distinct status message.

**Port budget**: ~40 lines in `app.component.ts` (handler + predicate + `generatingTask` flag); excludes any new service methods (service is complete), excludes toast infrastructure changes (inline status reuses an existing slot), and excludes post-generation routing beyond selecting the returned filename.

### Task 4: Add Karma Unit Spec

Covers the two testable behaviors introduced by this epic: (a) clicking the button with `canGenerateTask = true` emits `'generate-task'` from the sidebar's `(action)` output, and (b) rendering with `generatingTask = true` disables the button and updates its label. Follows the pattern of existing sidebar action specs. Does not cover the AppComponent handler — that path is covered by the integration of Tasks 2 and 3 in the running app, and mid-E2E2 test extension is out of scope.

**Port budget**: ~15 lines in a sidebar spec file; excludes AppComponent handler tests and excludes any new page-object additions (E2E2 is in flight).

---

## Success Criteria

This epic is complete when:

- ✅ The "Generate Next Task" button is visible in the sidebar whenever a project is selected
- ✅ The button is disabled when no project is active, when the active project has no `epic.md`, or when a generation call is in flight
- ✅ Clicking the button on a project with a missing task produces a new `task-N-*.md` file, selects it in the editor, and shows a success status — without touching any other project files
- ✅ Clicking the button when all epic tasks already have guides shows "All epic tasks already have implementation guides" rather than erroring
- ✅ An error response from the service surfaces a readable message in the same status slot, not a console-only log
- ✅ The Karma spec passes: action emission and disabled-state assertions both green

---

## Non-Goals

- ❌ **Per-task regeneration picker** — "next missing" is the correct v1 because the service already defines it that way; a picker adds UI surface for a use case that has not been explicitly requested post-analysis.
- ❌ **Streaming progress indicator** — the transport is request/response; a spinner satisfies the floor. Streaming would require endpoint changes not in scope.
- ❌ **E2E coverage** — E2E2 is in flight; adding page objects or specs mid-epic introduces merge risk with no proportionate gain.
- ❌ **Bootstrap loop modification** — the loop already shares the service correctly; touching it for this epic would change tested behavior with no new consumer benefit.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview