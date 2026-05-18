# 🏗️ Solution Architecture: UX — Reader, Text Ops & Navigation

## Architecture Overview

The reader is being inverted, not redesigned. Today the sidebar holds navigation while the floating bottom toolbar holds both the AI op triggers and the AI op results — creating a spatial split where the user clicks at the bottom and the result materialises at the top. The architectural move is to make the **sidebar the single command centre** (navigation + triggers + per-op state) and demote the toolbar to a **result-display zone** (Apply / Copy / Dismiss for the active AI result). Every other change in this epic — taxonomy, teasers, status bar, animations — is a consequence of that one structural decision: state lives where the user looks, not where the framework happened to put it.

The mental model is editorial. The sidebar is the masthead's table of contents — it tells you what's available, what's running, and what's done. The main content area is the article. The bottom bar is the publication's signal box — connection state, current operation, audit-log detail. None of these zones overlap in responsibility, and each one has a single source of truth: the section taxonomy is **derived from file state** (not project-id strings), the status display is **derived from the chain adapter's job snapshot** (not from two parallel loading flags), and the project teaser is **derived from a scan of the lead spec file** (not from an arbitrary 100-char slice).

The key insight: the existing Angular signal architecture already supports this — `specGenLoading()`, `aiLoading()`, `currentSpec()`, `aiResult()` are all signals. The fix is to **collapse parallel state**, **add small derived signals** for taxonomy and teaser, and **move presentation** to where the trigger lives. No new framework, no new state library, no backend rewrite. The chain adapter, the 202+polling pattern, and the in-process job dict all stay exactly as they are.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P1 — Adapter Boundary** | Status bar consumes the chain adapter's existing job snapshot shape; no new provider plumbing. The status display is a view over `snapshot(job_id)`, not a parallel state machine. |
| **P2 — Thin HTTP Layer** | This epic is frontend-only. No new Flask routes. The `/status/{job_id}` endpoint already exists; the status bar is a richer renderer of the same payload. |
| **P3 — Async 202 + Polling** | The per-file dot, the status bar, and the section taxonomy all read from polled job state. No connection held open, no new transport. |
| **P4 — No Speculative Abstractions** | Five hardcoded sections, not a registry. Five hardcoded teaser variants, not a strategy pattern. The animation is two `@trigger`s, not a generic motion system. Build the one shape that exists. |
| **P7 — File Size & Structure** | Sidebar grows in responsibility; it must split into focused child components (file list, action group, op chip row, status row) rather than become a god component. Each child stays under 200 lines. |
| **Single source of truth for status** | The `sidebar-status` row is removed. Exactly one status indicator exists in the DOM at any time. This is enforced structurally — the sidebar component does not import the status display. |
| **Result lives where the trigger lives** | Triggers move to the sidebar; the result toolbar collapses to result-only. Style presets render adjacent to the Style chip in the same chip row, not at the top of the main content area. |

## Component Design

### Sidebar Command Centre
**Purpose**: Becomes the single zone for project navigation, AI op triggering, and per-file status. Owns four logical regions: file list, primary actions (Generate Specs / Generate Guide / Undo), op chip row (formerly the floating toolbar's chip row), and a Style preset expansion that opens inline below the Style chip.

**Why**: The current architecture scatters the user's interaction surface across four zones (masthead, sidebar, floating toolbar, fixed bottom bar). The sidebar is the only zone that's always visible and always project-scoped. Consolidating triggers there resolves the trigger/result inversion at the structural level — the toolbar no longer needs to be both trigger and display, so it can shrink to a single job.

**Boundaries**: The sidebar does not render results, does not show global app status (that's the bottom bar), and does not contain code that knows about specific AI ops beyond their chip metadata. It emits intent events; a sibling service translates intent into adapter calls.

### Result Toolbar (renamed from Editor Toolbar)
**Purpose**: Sticky element above the main content that shows the active AI result's actions: Apply (full-width, weighted), Copy (ghost), Dismiss (icon). Shows latency badge when a result is present. Renders nothing when no result is active.

**Why**: Today the toolbar is two things — trigger and result display — and toggles between modes via `aiResult()`. Splitting this into "trigger lives in sidebar" and "result-only toolbar in main panel" removes the modal toggle entirely. The toolbar is now stateless across triggers; it only knows about the current result.

**Trade-off**: The floating-on-scroll behaviour stays (the result toolbar still floats), but it has only three buttons. This makes the floating affordance clearer — "this is what you do with the result" — rather than an ambiguous mix of triggers and actions.

### Section Taxonomy Service
**Purpose**: Computes a project's section membership from its file list and recent activity, returning exactly one of `Active | Ready to build | Specced | Braindumps | Archive`. Replaces the existing `categorise(p.id)` string-matching function.

**Why**: The current taxonomy is a leaky abstraction — it derives meaning from project ID prefixes that users could rename at any time, and the section labels (`saas`, `specview`) are private naming conventions, not user-facing categories. The new taxonomy is **state-derived**: every project lands in exactly one section based on what files exist and whether work is in progress. This is computable, deterministic, and doesn't depend on naming hygiene.

**Decision**: Five sections, hardcoded. No registry, no extensibility hook. P4 — when a sixth section is genuinely needed, we'll add it; we don't need a plugin model for one consumer.

**Edge cases**: A project with implementation-guide.md plus active spec generation lands in `Active` (in-progress wins over Ready-to-build). Archive is opt-in (project-level flag), not derived from age.

### Project Teaser Resolver
**Purpose**: Returns the right teaser string for a project card given its current state. Five variants: braindump-only ("Braindump — ready to generate"), in-progress (live step from job snapshot, e.g. "generating architecture…"), specced (first non-heading sentence of lead file via scan), implementation-guide-ready ("Implementation guide ready · N tasks"), archive (date archived).

**Why**: The current `teaser(content.slice(0, 100))` is a content-agnostic substring — it shows whatever happens to be at the top of the first file, which is almost always a heading mid-truncation. The replacement scans for the first non-heading, non-bullet, non-empty line and takes the first sentence. This is editorially meaningful — it's the teaser a human editor would pick.

**Trade-off**: We deliberately defer the AI-emitted `insight` field (a generation-pipeline change). The scan-based fallback is good enough to ship now and gives us a working teaser without changing the spec generation contract. When `insight` lands later, the resolver gets one extra branch — Specced state prefers `project.insight` if present, falls back to scan.

**Boundary**: The resolver is pure — given a project descriptor and the lead file's content, it returns a string. No I/O, no signals. The caller (the project card component) holds the signal and re-evaluates when state changes.

### Unified Status Bar
**Purpose**: Single bottom-fixed bar always visible. Four states with strict color semantics: green (success flash, fades), amber (in-progress), red (failure / API unreachable, with retry), neutral (idle, shows connection heartbeat). Renders endpoint, job_id, current step, attempt count, and elapsed seconds when active. In idle state shows connection state and last health-check sync.

**Why**: The current architecture has two status indicators — the sidebar `sidebar-status` row and the fixed `gen-status-bar` — both reading the same signals (`specGenLoading`, `aiLoading`). This is duplication: the same truth rendered in two places, with no single source of truth for which one is canonical. The fix is structural — the sidebar status row is removed entirely, and the bottom bar becomes the single status surface. The sidebar's contribution to status becomes per-file dots (a different signal: which file is being operated on), not a global state mirror.

**Decision — system health vs. operation status**: The bar serves both roles. In idle it's a heartbeat ("● connected · specview api · last sync 2s ago"); in active it's an operation log ("● generating · bootstrap-project · step: architecture · 32s · attempt 7"). One bar, two render modes, derived from the same connection-state + job-state signals.

**Trade-off**: Showing endpoint paths and job IDs is dev-grade detail in a user-facing surface. We accept this — Sam is the user, dogfooding daily, and audit-grade visibility is more valuable than visual minimalism. Future work might gate the verbose detail behind a power-user toggle.

### Per-File Status Dots
**Purpose**: A small colored dot rendered next to each file entry in the sidebar when an AI op is targeting that file. Yellow pulsing while running, green flash on success, red persistent on failure (until acknowledged or the user re-triggers).

**Why**: Status visible in the sidebar even when the user has scrolled the main content away. The bottom status bar tells you something is happening globally; the per-file dot tells you which file specifically. This is the only piece of status presentation that lives in the sidebar — and it earns its place because it's file-scoped, not global.

**Source**: Reads from the same job snapshot as the status bar. The job snapshot already carries `target_file` (or can be extended to). The dot is a derived signal — `dotColor(file) = colorFor(snapshot.where(j => j.target_file === file.path))`.

### Panel Open/Close Animation
**Purpose**: 250ms directional enter when a project is opened from the grid; 150ms reverse on close. Sidebar enters 40ms before main content (translateX from -8px); main content rises in place (translateY from 8px). No bounce, no spring physics.

**Why**: The current cut from grid → expanded panel is jarring at viewport scale. A short directional transition gives spatial context — the user's mental model of "I clicked that card and it became this panel" gets reinforced. The staggered enter (sidebar first) reinforces the two-column structure at the moment of assembly.

**Decision — Angular `@trigger` vs. CSS classes**: We pick `@trigger`. Angular animations integrate cleanly with `@if` enter/leave and don't require manual class lifecycle management. The CSS-class approach was considered but adds a `--entering` class that must be removed on a timer; that's stateful CSS, which is a bug surface.

**Trade-off**: Adds an `@trigger` to the root expanded panel components. Compile cost is negligible; bundle cost is a few kB of `@angular/animations`. Worth it for the perceived quality lift.

### Brainstorm Visibility Predicate
**Purpose**: `isBraindump()` returns true only when the open file's name is exactly `braindump.md`. The Brainstorm chip uses this predicate for visibility.

**Why**: The current implementation `!!currentSpec()` is structurally always-true whenever any file is open. This is a one-line bug fix that has been mis-classified as a feature decision. Fixing it removes the Brainstorm chip from spec files where its presence implies "brainstorm this spec" — a confusing semantic. Brainstorm is a planning op for raw ideas; it belongs only on `braindump.md`.

**Boundary**: This predicate is a single computed signal in the file-context service. It is not a registry of "which ops apply to which file types" — that abstraction is deferred (P4). When the second file-scoped op appears, we add a second predicate; we do not generalise.

### Style Chip Inline Presets
**Purpose**: Style preset buttons (Concise, Technical, Executive, Narrative, Punchy) render adjacent to the Style chip in the same chip row, not at the top of `.expanded-main`. In the sidebar-first model, both the Style chip and its presets live in the sidebar; the presets expand inline below or beside the Style entry.

**Why**: Today the presets render in the main content area, spatially detached from the chip that triggered them. This reproduces the trigger/result inversion at a smaller scale. Co-locating them resolves it. The chip row already has horizontal space (or a wrap line); the presets extend that row when active.

**Trade-off**: The chip row gets visually busier when Style is active. We accept this — busier-but-co-located beats cleaner-but-detached, because attention cost is more expensive than visual cost.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend framework | Angular 17, standalone components, signals | Already in use; signals fit the derived-state pattern (taxonomy, teaser, status) cleanly. No new dependency. |
| Animation | Angular `@trigger` | First-party, integrates with `@if` enter/leave, scope-local. Avoids manual CSS class lifecycle bugs. |
| State | Local component signals + existing services (no NgRx) | Per P4 and existing project conventions. Section taxonomy and teaser resolver are pure functions invoked from signals; no store. |
| Status data source | Existing chain adapter `snapshot(job_id)` via the existing `/status` endpoint | P1: adapter is the single AI boundary. The status bar is a renderer over snapshot output; no new transport. |
| Backend | No changes in this epic | All work is frontend re-composition over existing signals and existing endpoints. Future `insight` field is explicitly deferred to a separate pipeline change. |
| Per-file dot transport | Existing job polling | The dot is a derived view of the same job snapshot the status bar consumes. No additional polling, no new endpoint. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Sidebar owns triggers; toolbar owns result actions only** | Resolves the trigger/result spatial inversion at the structural level, not by adding a "scroll to result" hack. Single command centre matches the editorial mental model. | Sidebar grows in responsibility and width; must be split into focused child components to stay under the 200-line file ceiling. Toolbar real estate shrinks (acceptable — three buttons is clearer than seven). |
| **Single status bar; remove the sidebar status row** | Two status indicators reading the same signal is duplication, not redundancy. One source of truth, one rendering surface. | The sidebar loses a familiar element. Mitigated by per-file dots, which carry a different signal (per-file scope) and earn their sidebar placement. |
| **State-derived sections (5 hardcoded)** over **ID-prefix matching** | The taxonomy must mean something to the user. State-derived sections are computable from data the API already returns; ID-prefix sections leak naming conventions into the UI. | No user-defined sections. When this becomes a real constraint we'll revisit; for now hardcoding five is the right shape (P4). |
| **Scan-based teaser fallback now; AI `insight` field deferred** | We can ship a meaningful teaser this epic without changing the spec generation contract. The pipeline change is bigger and lives elsewhere. | The teaser is a heuristic, not editorial. Sometimes the first non-heading sentence is still suboptimal. Acceptable until `insight` lands. |
| **Strict color semantics for status** (green/amber/red/neutral) | Color is a data channel; using it consistently turns the status bar into a glanceable signal. Inconsistent color makes color noise. | We commit to never using these four colors elsewhere for unrelated UI roles. Editorial styling already keeps the color palette small, so this is cheap. |
| **Verbose status detail (endpoint, job_id, attempt, elapsed)** | Sam is the primary user and a developer; audit-grade detail is more valuable than minimalism. The status bar becomes a debugging tool, not just a spinner. | Looks dev-grade to a future non-developer user. If/when that user exists, gate detail behind a power-user toggle. Not worth designing for them now. |
| **Angular `@trigger` for the panel animation** | First-party, integrates with `@if`, no manual class lifecycle. | Pulls in `@angular/animations` (small bundle increment). Worth it. |
| **Fix `isBraindump()` as a one-line predicate, not a registry** | The bug is a one-line fix. A registry of file→op mappings is speculative for one rule. | When the second file-scoped op appears, we add a second predicate. We do not pre-build a system. |
| **Style presets inline in chip row, not in main content** | Resolves the same trigger/result spatial inversion the sidebar move resolves at a larger scale. Consistent rule: the affordance lives where the trigger lives. | Chip row gets visually denser when Style is active. Accepted. |
| **Per-file dots over a single global "current file" indicator** | A global indicator answers "is anything happening?"; the dots answer "to which file?". The latter is the question the user actually has when scrolled away from the content. | Adds one more visual element to the sidebar. Mitigated by the dot being small and only present when a job targets that file. |
| **Animation values are small and fast** (250ms enter, 150ms exit, 8–12px translate) | These are editorial documents; the motion language should feel like turning a page, not opening a drawer. | No dramatic spatial metaphor. Accepted — drama would fight the editorial identity. |
| **No keyboard shortcuts in this epic** | Per the braindump's own "fix first" list — keyboard nav is a second pass. Shipping the structural fixes first prevents shortcuts being designed against the wrong layout. | Power users wait one more iteration. |
| **No thread/chain result model in this epic** | Owned by the `text-ops-thread-ui` braindump; this epic is the structural prerequisite (sidebar-first) that the thread model lands on top of. | The trigger/result inversion is partially resolved (triggers and actions are now co-located in/near the sidebar) but full result-adjacent rendering waits for the thread epic. Acceptable — sequencing matters. |

## Related Documents
- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking