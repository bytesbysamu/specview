# 🏗️ Solution Architecture: Generate Next Task

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The system adds a single sidebar action to an existing action-dispatch pattern without introducing any new service, endpoint, or data model. `ImplementationGuideService.generateNextTask()` already encapsulates the full prompt-build → AI call → file-write cycle; the gap is a named action that routes through the sidebar's existing `(action)` event output to `AppComponent`'s handler switch. Every structural layer already exists — this architecture extends the type union, renders one button, and adds one case to the router.

The key insight is that the sidebar is a dumb emitter: it fires typed action strings and exposes `@Input()` bindings for state that the host (`AppComponent`) owns. This separation is what makes the change minimal — the sidebar never knows whether generation succeeded or what project is active; it only receives `canGenerateTask` and `generatingTask` flags computed upstream. `AppComponent` is the only consumer of both the service call and the sidebar's new inputs.

The component graph is deliberately flat: `SidebarComponent` → `(action)` → `AppComponent` → `ImplementationGuideService` → (existing) `AiService` adapter → CLI provider. No new intermediary, no new pipe, no new service boundary. The architecture earns its simplicity by trusting that the service contract is already correct.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Don't abstract a single concrete case | `canGenerateTask` is computed directly in `AppComponent`, not promoted to a shared predicate service — there is exactly one consumer |
| Sidebar is a dumb emitter | The sidebar holds no business logic; enabled and busy state flow in via `@Input()`, not derived inside the component |
| Single Source of Truth for task generation | `ImplementationGuideService` owns all prompt-build and file-write logic; `AppComponent` only orchestrates the call, never re-implements it |
| Floor before ceiling on UX | Inline status text reuses the existing status slot; streaming and toasts are deferred until latency feedback confirms the need |
| ELA Adapter boundary for AI | `AiService` remains the sole AI adapter boundary; `ImplementationGuideService` calls it without coupling to any provider directly |

---

## System Boundaries

### What This System Includes

- Extension of the `SidebarAction` string union in `sidebar.component.ts` to add `'generate-task'` as a first-class typed action
- Two new `@Input()` bindings on `SidebarComponent` — `canGenerateTask` and `generatingTask` — that control the button's enabled and busy states
- A "Generate Next Task" button rendered inside the existing sidebar actions block, consuming the two new inputs
- A `case 'generate-task'` branch in `AppComponent`'s action router that sets the busy flag, calls the service, refreshes project state, selects the generated file, and surfaces an inline status message for success, null (all tasks done), and error outcomes
- A `canGenerateTask` predicate computed in `AppComponent` — true when an active project with an `epic.md` exists
- A Karma unit spec covering action emission from the button and disabled-state rendering when `generatingTask` is true

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Per-task targeting picker | The service API is "next missing task"; a picker requires a `generateTaskByNum()` extension and a confirmed user need for out-of-order regeneration. Re-scope if the user requests it explicitly. |
| `generateTaskByNum()` service extension | No caller in this epic; the service change is minor but the picker UI that would drive it is unconfirmed. |
| SSE / streaming progress | The `/api/ai/text/generate` endpoint is request/response; adding streaming requires endpoint changes that are out of scope. A spinner satisfies the floor. |
| E2E coverage additions | The E2E2 epic is in flight; extending page objects or specs mid-cycle introduces merge risk with no proportionate benefit. Log as a follow-up after E2E2 closes. |
| Bootstrap loop modifications | The loop already calls `ImplementationGuideService.generateNextTask()` correctly; touching it for this epic changes tested behavior with no new consumer benefit. |

---

## Component Design

### SidebarAction Union Extension

**Purpose**: Establishes the typed contract between sidebar and host so that `'generate-task'` is indistinguishable from existing actions in terms of type safety and routing. Tasks 2 and 3 both depend on this boundary existing before they can proceed.

**Key Parts**:
- `SidebarAction` union in `sidebar.component.ts` — the discriminated string union that `AppComponent`'s switch statement pattern-matches against; adding `'generate-task'` here is the single change that unblocks all downstream work

**Patterns**: Discriminated union / exhaustive switch — the same pattern used for `'implement'`, `'copy'`, `'new-project'`, and the remaining five existing actions

### Sidebar Button

**Purpose**: Renders the user-facing entry point and faithfully reflects the host-computed state. The sidebar component is responsible for rendering and emitting; it is not responsible for knowing when generation is appropriate.

**Key Parts**:
- `SidebarComponent` (`sidebar.component.ts`) — the component that renders the button inside the existing `sidebar-actions` block and emits `'generate-task'` via the `(action)` output; consumed by the Karma unit spec (Task 4) and by `AppComponent` at runtime
- `canGenerateTask` input — a boolean pushed down from `AppComponent`; when false, the button is disabled regardless of any other state
- `generatingTask` input — a boolean pushed down from `AppComponent`; when true, the button is disabled and its label switches to an in-progress variant

**Patterns**: Presentational component — all state flows in via `@Input()`, nothing is derived internally. This pattern is already established by the existing action buttons in `sidebar.component.ts:73–92`.

### AppComponent Handler

**Purpose**: The single host that translates the sidebar's `'generate-task'` event into a service call, manages the transient `generatingTask` flag, and distributes outcomes — success, null, error — to the inline status slot. This component is the only place that knows about the active project context and the service return shape.

**Key Parts**:
- `case 'generate-task'` branch in `app.component.ts` — the action router case that calls `ImplementationGuideService.generateNextTask()` with the active project's ID and name, handles the three outcome paths, and resets the busy flag in the finally path regardless of outcome
- `canGenerateTask` predicate — computed in `AppComponent` and passed to `SidebarComponent`; depends on `activeProjectId` being non-null and the active project's file list containing `epic.md`
- `generatingTask` flag — a single boolean on `AppComponent` that synchronizes the sidebar button's busy state and prevents concurrent calls; passed as the `generatingTask` input to `SidebarComponent`

**Patterns**: Action-router pattern — the existing switch on sidebar action strings in `app.component.ts`; this case follows the identical structure of the `'implement'` and `'copy'` cases. The predicate-as-input pattern is already used for other conditional sidebar controls.

### Karma Unit Spec

**Purpose**: Provides automated verification of the two behaviors the sidebar component introduces — action emission on click and disabled-state rendering when busy — without requiring the full `AppComponent` host or a running service.

**Key Parts**:
- Sidebar spec file — tests `SidebarComponent` in isolation, consistent with the existing pattern for sidebar action specs; consumed by the CI test run and by future contributors as a behavioral reference

**Patterns**: Isolated component test — mount with inputs set directly, assert on output events and DOM state; the same pattern used by existing sidebar action specs

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Angular + TypeScript | Existing codebase; discriminated union + exhaustive switch is idiomatic Angular/TS and requires no new framework surface |
| Component testing | Karma + Angular Testing Library | Existing test infrastructure; sidebar action specs already establish the pattern |
| AI adapter | `AiService` (ELA Pattern #1) | The sole adapter boundary for AI provider calls; `ImplementationGuideService` calls it without knowing which provider is behind it |
| AI provider | CLI provider via `chain/providers/cli.py` | Existing provider; the subprocess deadlock fix (`a130fb3`) is already in place |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| "Next missing" task, not "highlighted task" | `ImplementationGuideService.generateNextTask()` defines this as its contract (docstring at `implementation-guide.service.ts:26`); implementing a picker in v1 would require extending the service signature and adding UI surface for a use case not yet confirmed by the user | A user who wants to regenerate Task 3 specifically, with Task 4 already present, cannot do so in v1 — they must delete Task 4 first |
| `canGenerateTask` computed in `AppComponent`, not sidebar | `AppComponent` owns active project state; computing the predicate in the sidebar would require passing project data down rather than a scalar boolean, coupling the sidebar to the project model | The predicate logic lives one level up from where it is rendered, which requires reading two files to understand the full enabled condition |
| Inline status, not toast | Inline status reuses an existing slot with no new infrastructure; a toast system would require new service injection and a new DOM target | Inline messages may be missed if the user's eyes are on the editor; revisit if user feedback confirms the need |
| Busy flag on `AppComponent`, not sidebar | `AppComponent` controls when generation is in flight; the sidebar only reflects state it receives. Placing the flag in the sidebar would allow the component to drift from host-authoritative state | `AppComponent` carries one more piece of transient UI state; acceptable given it already owns all other action-in-flight flags |
| No streaming in v1 | The `/api/ai/text/generate` endpoint is request/response; streaming would require endpoint changes and a new SSE client — scope that exceeds the gap being closed | Generation can take 30–90 seconds on the CLI provider; the spinner conveys activity but gives no progress granularity. If wait-time complaints surface, streaming is the natural upgrade |

---

## Patterns

### Sidebar Action Dispatch

**When to use**: Any new user-initiated operation that originates in the sidebar and requires host-level context — active project, services, state flags — to execute.

**How it works**: `SidebarComponent` emits a typed `SidebarAction` string via its `(action)` output. `AppComponent` receives it in a handler that pattern-matches on the string and dispatches to the appropriate branch. The sidebar never holds the logic for what happens next — it only holds the rendering and the emission.

**Example**: `'generate-task'` is emitted by the new button, received by `AppComponent`'s switch, which then calls `ImplementationGuideService.generateNextTask()` with the host-owned project context.

### Input-Driven Disabled State

**When to use**: When a sidebar button's enabled or busy state depends on host-level context that the sidebar component should not derive itself.

**How it works**: The host computes a boolean predicate and passes it as an `@Input()` to the sidebar. The sidebar binds it directly to the button's disabled attribute. State flows in one direction; the sidebar emits events in the other.

**Example**: `canGenerateTask` (requires active project with `epic.md`) and `generatingTask` (generation in flight) are both computed in `AppComponent` and passed as inputs. The sidebar applies them without knowing what they represent.

### ELA Adapter Boundary (AI)

**When to use**: Any feature that needs to call an AI provider.

**How it works**: `AiService` is the single adapter boundary. Features call `AiService.generate()` and receive text; they never import a provider directly. Provider selection, retries, and transport details are encapsulated behind the adapter.

**Example**: `ImplementationGuideService.generateNextTask()` calls `AiService.generate()` without any reference to the CLI provider. The sidebar button path inherits this boundary transitively — `AppComponent` calls the service, the service calls the adapter, the adapter calls the provider.

---

## Execution Flow

```
[Phase 1 — Unblock]
  Task 1: Extend SidebarAction union
          │
          ├──────────────────────────────┐
          ▼                              ▼
[Phase 2 — Parallel]           [Phase 2 — Parallel]
  Task 2: Add sidebar button    Task 3: Add AppComponent handler
          │                              │
          └──────────────┬───────────────┘
                         ▼
              [Phase 3 — Verify]
               Task 4: Karma unit spec
```

Task 1 is the only strictly serial step: its single type addition is the shared boundary that both Task 2 (sidebar template and inputs) and Task 3 (handler and predicate) reference. Tasks 2 and 3 can be developed in parallel once Task 1 lands. Task 4 depends on the component shape established by Task 2 and the handler contract established by Task 3 — it cannot be written meaningfully until both are stable.

The parallel window between Tasks 2 and 3 is safe because the two files are independent (`sidebar.component.ts` vs. `app.component.ts`) and the only shared surface is the `SidebarAction` string literal `'generate-task'`, which Task 1 locks in first.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview