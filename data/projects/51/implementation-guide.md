# 📋 Implementation Guide: UX — Reader, Text Ops & Navigation

This guide walks through the five tasks in the epic in dependency order. Each task is sized to be shippable independently behind whatever review gate the team uses; tasks 1 and 2 can run in parallel, then 3 unblocks 4 and 5.

Total budget: **5.5 days**. Surface area: Angular reader components only — no backend changes.

---

## Pre-flight

Before starting any task:

1. Confirm the existing chain adapter exposes `snapshot(job_id)` with at least `{ status, endpoint, step, attempt, elapsed_ms, started_at, target_file? }`. Tasks 4 and 5 assume this shape; if `target_file` is missing, that adapter extension is the first sub-task of Task 4.
2. Verify `ng build --configuration production` is currently green — every task lists this as the merge gate.
3. Identify the current reader composition root (likely `expanded-project.component.ts` or similar). All five tasks edit children of this root; locate it once.
4. Skim `categorise()`, `teaser()`, and `isBraindump()` in their current homes — these names are referenced throughout this guide and you'll edit each.

---

## Task 1 — Quick Wins (0.5 days)

**Goal**: Three independent one-line-to-one-component fixes that unblock perception of progress and remove a confusing affordance. No dependencies; ship first.

### 1.1 `isBraindump()` predicate fix

**Where**: The file-context service / signal that exposes `isBraindump`. Today it returns `!!currentSpec()` — always true when any file is open.

**Change**:

```ts
readonly isBraindump = computed(() => {
  const spec = this.currentSpec();
  if (!spec) return false;
  return spec.filename === 'braindump.md';
});
```

**Consumer check**: Find every template binding to `isBraindump()` (sidebar chip row primarily). The Brainstorm chip's `@if (isBraindump())` now correctly hides on architecture.md, epic.md, etc.

**Test**: Open a project, click through `braindump.md` → Brainstorm chip visible. Click `architecture.md` → chip hidden. Click back → chip returns.

### 1.2 Weighted Apply button

**Where**: The result toolbar component (currently the editor toolbar) where Apply / Copy / Dismiss render.

**Change**: Apply gets a solid filled style, full-width or visibly heavier than its siblings. Copy and Dismiss stay as ghost / icon styles. Concretely, in the component's SCSS:

```scss
.action-apply {
  background: var(--ink);          // or whatever the primary ink token is
  color: var(--paper);
  font-weight: 600;
  flex: 1 1 auto;                  // take remaining width when toolbar is wide
  min-width: 9rem;
}
.action-copy { /* existing ghost */ }
.action-dismiss { /* existing icon-only */ }
```

If the toolbar layout is currently `gap: x; flex: 0`, give Apply `flex: 1` so it visually dominates.

**Test**: Trigger any AI op, see result render in toolbar, confirm Apply is visually the primary action (heavier than Copy, distinct from Dismiss).

### 1.3 Style chip placement fix

**Where**: Today, the Style preset buttons (Concise / Technical / Executive / Narrative / Punchy) render at the top of `.expanded-main`. They must render adjacent to the Style chip in the sidebar chip row.

**Change**: This is a partial preview of Task 3 — but it's fine to land the visual co-location now using the existing markup location. Move the `<style-presets>` template block from `.expanded-main` into the same template region as the Style chip. In the meantime they may render above the chip row; in Task 3 they'll fold into the sidebar entirely.

If moving the markup feels premature given Task 3 will rewrite the layout, an acceptable interim is: render the presets immediately below the chip row using a position-relative wrapper around the chip row. The non-negotiable is that they no longer render at the top of `.expanded-main`.

**Test**: Click Style chip → presets appear adjacent to it. Click again → presets close.

### 1.4 Verification

- `ng build --configuration production` passes.
- Manual smoke: braindump-only project, specced project, in-progress project — Brainstorm chip visibility correct on each; Apply button weight correct after each AI op; Style presets adjacent.

---

## Task 2 — State-Derived Section Taxonomy + Smarter Teaser (1 day)

**Goal**: Replace ID-prefix `categorise()` with a pure function over file state. Replace the `content.slice(0, 100)` teaser with a scan that picks the first non-heading sentence and a state-aware variant set.

Independent of Task 1; can run in parallel.

### 2.1 Section taxonomy service

Create a pure function that maps a project descriptor to one of `Active | Ready to build | Specced | Braindumps | Archive`.

**Inputs the function needs** (from the project descriptor that the project list endpoint already returns):
- `files: { filename, ... }[]` — what files exist.
- `archived: boolean` — opt-in archive flag.
- `activeJob?: { ... }` — derived from the live job snapshot map keyed by project id.

**File**: `web-ng/src/app/services/section-taxonomy.service.ts` (new).

```ts
export type Section = 'Active' | 'Ready to build' | 'Specced' | 'Braindumps' | 'Archive';

export function sectionFor(p: ProjectDescriptor, hasActiveJob: boolean): Section {
  if (p.archived) return 'Archive';
  if (hasActiveJob) return 'Active';

  const names = new Set(p.files.map(f => f.filename));
  if (names.has('implementation-guide.md')) return 'Specced';
  if (names.has('architecture.md') || names.has('epic.md')) return 'Ready to build';
  if (names.has('braindump.md')) return 'Braindumps';
  return 'Braindumps'; // empty/unknown defaults here; revisit if real
}
```

**Edge cases** (per architecture):
- Active wins over Specced when a job is in flight, even if `implementation-guide.md` exists.
- Archive is the project's `archived` flag, not derived from age or last-modified.

### 2.2 Wire the taxonomy into project list grouping

In the project list component, replace `categorise(p.id)` with `sectionFor(p, hasActiveJob(p.id))`. Group projects into the five sections; render section headers in the canonical order above.

Remove `categorise()` entirely once no callers remain. Grep for `categorise` after the change to confirm.

### 2.3 Pulse animation on tab count change

The success criterion calls for a single pulse when a section's count changes due to a state transition.

**Approach**: A directive or simple `@trigger` on the count badge that fires when the bound number changes. Minimal version:

```ts
@Component({
  selector: 'section-tab',
  template: `<span [@countPulse]="count()">{{ count() }}</span>`,
  animations: [
    trigger('countPulse', [
      transition('* => *', [
        animate('200ms ease-out', keyframes([
          style({ transform: 'scale(1)', offset: 0 }),
          style({ transform: 'scale(1.18)', offset: 0.5 }),
          style({ transform: 'scale(1)', offset: 1 }),
        ]))
      ])
    ])
  ]
})
```

Bind `count` as a signal so it triggers on transition only.

### 2.4 Project teaser resolver

Pure function. Five branches, in priority order.

**File**: `web-ng/src/app/services/project-teaser.ts` (new).

```ts
export function projectTeaser(args: {
  section: Section;
  activeStep?: string;          // from job snapshot, e.g. 'architecture'
  leadFileContent?: string;     // first paragraph or two of the lead file
  taskCount?: number;           // for implementation-guide-ready
  archivedAt?: string;          // ISO date for archive
}): string {
  const { section, activeStep, leadFileContent, taskCount, archivedAt } = args;

  if (section === 'Active' && activeStep) {
    return `generating ${activeStep}…`;
  }
  if (section === 'Specced' && taskCount != null) {
    return `Implementation guide ready · ${taskCount} task${taskCount === 1 ? '' : 's'}`;
  }
  if (section === 'Specced' && leadFileContent) {
    const sentence = firstNonHeadingSentence(leadFileContent);
    if (sentence) return sentence;
  }
  if (section === 'Braindumps') {
    return 'Braindump — ready to generate';
  }
  if (section === 'Archive' && archivedAt) {
    return `Archived ${formatDate(archivedAt)}`;
  }
  return '';
}

function firstNonHeadingSentence(md: string): string | null {
  const lines = md.split('\n');
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('#')) continue;            // headings
    if (line.startsWith('-') || line.startsWith('*')) continue; // bullets
    if (line.startsWith('>')) continue;            // blockquotes
    if (line.startsWith('|')) continue;            // table rows
    // Take the first sentence: up to the first . ! ? followed by space or EOL.
    const m = line.match(/^(.+?[.!?])(\s|$)/);
    return (m ? m[1] : line).trim();
  }
  return null;
}
```

**Boundary**: Pure. No signals, no I/O. The project card component holds the signals and re-evaluates this on input change.

### 2.5 Lead file selection

For Specced projects the lead file is `implementation-guide.md`; for Ready-to-build it's `architecture.md`; for Braindumps it's `braindump.md`. Compute lead-file content lookup once in the project card component using the project descriptor.

If the project list endpoint doesn't already include enough of the lead file's content to scan, this is the one place the architecture allows extending the existing endpoint — but check first; existing projects may already return the first ~500 chars.

### 2.6 Verification

- Each existing project lands in exactly one section. Spot-check 3+ projects in different states.
- Braindump-only project shows "Braindump — ready to generate".
- Specced project shows a sentence (not a heading, not a bullet, not a slice mid-word).
- Trigger spec generation on a braindump project; teaser flips to "generating …" and the project moves to Active. Section count badges pulse.
- `categorise()` and `teaser(content.slice(0, 100))` no longer exist (grep returns nothing).
- `ng build --configuration production` passes.

---

## Task 3 — Sidebar-First Command Centre (2 days)

**Depends on Task 1.** Largest task. Decomposes the sidebar into focused children, migrates op chips out of the floating toolbar, and demotes the toolbar to a result-only zone.

### 3.1 Sidebar component decomposition

Per P7 and the 200-line ceiling, split the current sidebar into four child components. Names suggested; align with project conventions.

| Child | Responsibility |
|-------|----------------|
| `sidebar-file-list` | Renders the file entries; emits file selection. **Owns per-file dot rendering** (Task 4 wires the dot signal here). |
| `sidebar-action-group` | Generate Specs / Generate Guide / Undo. Primary actions. |
| `sidebar-op-chips` | Op chip row migrated from the floating toolbar. Owns Style chip + inline preset expansion. |
| `sidebar-status-row` | **Delete this**. Per architecture, single-source-of-truth for status moves to the bottom bar. Remove the file, remove its template usage. |

The composed sidebar component imports these children and lays them out vertically. Verify each child stays under 200 lines.

**Important**: The sidebar component must not import the global status display component. This is the structural enforcement of "single status indicator in the DOM".

### 3.2 Migrate op chips into the sidebar

The chips currently in the floating toolbar (e.g. Rewrite, Brainstorm, Style, Tighten, etc.) move into `sidebar-op-chips`. Steps:

1. Lift the chip metadata array (chip id, label, icon, predicate for visibility) into the new component or its co-located metadata file.
2. Move the `(click)` handlers — these emit op-intent events. The handlers should call the same service methods they call today; only their template host moves.
3. The `isBraindump()` gate on the Brainstorm chip moves with it. Other per-chip predicates (if any) move with their chip.
4. Style chip retains its expansion behaviour. The preset row, which Task 1.3 placed adjacent to the chip, now lives properly inside `sidebar-op-chips` — render the presets as a wrap-line below the chip row when Style is active.

### 3.3 Result toolbar reduction

Rename `editor-toolbar` → `result-toolbar` (or similar) to reflect the new responsibility.

**Strip** from the toolbar template:
- Op chip row.
- Style preset row (now in sidebar).
- Any conditional rendering that toggled between trigger-mode and result-mode.

**Keep**:
- `@if (aiResult())` wrapper around the entire toolbar — toolbar renders nothing when no result is active.
- Apply / Copy / Dismiss buttons (with Task 1.2 weighting).
- Latency badge.
- Sticky/floating-on-scroll behaviour.

The toolbar is now stateless across triggers. It only knows about the active result.

### 3.4 Intent event flow

The architecture says: "the sidebar emits intent events; a sibling service translates intent into adapter calls."

If a sibling service already exists (e.g. an `AiOpService` that today the floating toolbar calls), the sidebar children call it directly — no event indirection needed. If today the floating toolbar component is calling the chain adapter directly, this is the moment to extract that into a service so the sidebar doesn't grow that responsibility.

Keep the extraction minimal: a class with one method per op that wraps the adapter call. No event bus, no command pattern.

### 3.5 Verification

- Click any op chip in the sidebar → result renders in the result toolbar at the top of the main content. Eye does not cross the viewport.
- Floating toolbar at the bottom now shows only Apply / Copy / Dismiss when a result is active, nothing otherwise.
- Style chip + presets are entirely in the sidebar; nothing renders at the top of `.expanded-main`.
- Sidebar `sidebar-status` row is gone (grep should find no usage).
- Each new sidebar child is under 200 lines.
- `ng build --configuration production` passes.

---

## Task 4 — Unified Status Bar + Per-File Dots (1.5 days)

**Depends on Task 3** (sidebar-status row must be gone first).

### 4.1 Adapter snapshot shape

Confirm `snapshot(job_id)` returns at least:

```
{
  status: 'idle' | 'running' | 'success' | 'failure' | 'unreachable',
  endpoint: string,           // e.g. '/api/specs/architecture'
  job_id: string,
  step: string,               // e.g. 'architecture'
  attempt: number,
  started_at: number,         // epoch ms
  target_file?: string,       // path of the file being operated on
  last_health_check?: number, // epoch ms
}
```

If `target_file` is missing, add it adapter-side. This is a one-field extension, allowed because the per-file dot can't function without it. No new endpoint.

### 4.2 Connection state signal

Create a derived signal in a connection-state service:

```ts
readonly connection = computed<'connected' | 'unreachable'>(() => {
  const last = this.lastHealthCheck();
  if (!last) return 'unreachable';
  return Date.now() - last < 30_000 ? 'connected' : 'unreachable';
});
```

The status bar reads this for the idle render.

### 4.3 Status bar component

Single bottom-fixed component. Replaces the existing `gen-status-bar`. Four render modes driven by a single computed `mode()`:

```ts
readonly mode = computed<'idle' | 'active' | 'success-flash' | 'failure'>(() => {
  const job = this.activeJob();
  if (job?.status === 'running') return 'active';
  if (job?.status === 'failure') return 'failure';
  if (this.recentSuccess()) return 'success-flash'; // 2s window after job completes
  return 'idle';
});
```

**Templates** (one per mode, gated by `@switch`):

- **idle**: `● connected · specview api · last sync {{ syncAgo }}s ago` — neutral color (or green dot, neutral text).
- **active**: `● {{ step }} · {{ endpoint }} · job {{ shortId }} · {{ elapsed }}s · attempt {{ attempt }}` — amber.
- **success-flash**: `✓ {{ step }} done in {{ elapsed }}s` — green; auto-fade to idle after 2s via a `setTimeout` that clears `recentSuccess`.
- **failure**: `✕ {{ step }} failed · {{ message }}` + retry button — red; persists until acknowledged or retried.

**Color tokens**: Use four CSS custom properties (`--status-idle`, `--status-active`, `--status-success`, `--status-failure`) so the strict semantics live in one place. Don't reuse these tokens elsewhere — see the Design Decision in the architecture about color as a data channel.

### 4.4 Health-check polling

If a periodic `/health` (or equivalent) call doesn't already exist, add a small interval-based check (every 10s) that updates `lastHealthCheck`. If the existing job-polling implicitly proves connection, you can derive `lastHealthCheck` from the most recent successful poll instead — preferred, since it avoids a second poll loop.

### 4.5 Per-file status dots

In `sidebar-file-list`, each file row gets:

```html
<span class="file-dot" [style.--dot-color]="dotColor(file)" [class.pulsing]="isPulsing(file)"></span>
<span class="file-name">{{ file.filename }}</span>
```

`dotColor(file)` derives from the active job snapshot:

```ts
dotColor(file: FileEntry): 'transparent' | 'amber' | 'green' | 'red' {
  const jobs = this.allJobs();
  const j = jobs.find(j => j.target_file === file.path);
  if (!j) {
    const recent = this.recentlyCompleted(file.path);
    if (recent === 'success') return 'green'; // brief
    if (recent === 'failure') return 'red';   // until acknowledged
    return 'transparent';
  }
  return j.status === 'running' ? 'amber' : 'transparent';
}
```

`isPulsing` is true when the dot is amber (running). Implement the pulse with CSS — a 1s `animation: pulse 1s ease-in-out infinite` keyframe scaling 0.85 ↔ 1.

Green-on-success is brief (1.5s, then transparent). Red-on-failure persists until the user clicks the file or retriggers.

### 4.6 Single-source-of-truth audit

Search the codebase for `sidebar-status` and `gen-status-bar`. Only one status component should remain in the DOM tree. Document the audit in the PR description ("grep for status indicators returns: status-bar.component only").

### 4.7 Verification

- Open project, no job running → idle copy in bar; small connected dot.
- Trigger op → bar flips to amber, shows endpoint, job id, step, attempt, elapsed counter ticking.
- Op completes → green flash for ~2s, then idle.
- Kill the API (stop the server) → bar flips to red "unreachable" with retry. Retry button retries the most recent op.
- Per-file dot: trigger an op against `epic.md` → yellow pulsing dot next to `epic.md` in sidebar. Scroll main content; dot still visible. On success → green flash → fades. On failure → red persists until you click the file.
- Exactly one status component in the DOM (inspect element).
- `ng build --configuration production` passes.

---

## Task 5 — Panel Open/Close Animation (0.5 days)

**Depends on Task 3** (the panel structure must be settled first); can run in parallel with Task 4.

### 5.1 Add Angular animations

If `@angular/animations` isn't already a dependency, add it and import `provideAnimations()` into the application bootstrap (or the relevant standalone provider list).

### 5.2 Define triggers

In the expanded-project panel component:

```ts
import { trigger, transition, style, animate, query, group, stagger } from '@angular/animations';

animations: [
  trigger('panelEnter', [
    transition(':enter', [
      group([
        query('.sidebar', [
          style({ opacity: 0, transform: 'translateX(-8px)' }),
          animate('250ms 0ms ease-out', style({ opacity: 1, transform: 'translateX(0)' })),
        ]),
        query('.main', [
          style({ opacity: 0, transform: 'translateY(8px)' }),
          animate('250ms 40ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
        ]),
      ]),
    ]),
    transition(':leave', [
      group([
        query('.sidebar', [
          animate('150ms 0ms ease-in', style({ opacity: 0, transform: 'translateX(-8px)' })),
        ]),
        query('.main', [
          animate('150ms 0ms ease-in', style({ opacity: 0, transform: 'translateY(8px)' })),
        ]),
      ]),
    ]),
  ]),
],
```

Apply to the root expanded-panel element:

```html
<div class="expanded-panel" @panelEnter>
  <aside class="sidebar">…</aside>
  <main class="main">…</main>
</div>
```

The 40ms delay on `.main` produces the staggered enter the architecture calls for. No bounce, no spring — `ease-out` enter, `ease-in` exit.

### 5.3 Coordinate with `@if` driving the panel

The panel component must enter and leave via `@if` (not `[hidden]`) for `:enter` / `:leave` transitions to fire. If today the panel is always rendered and toggled via display rules, swap to `@if`.

### 5.4 Verification

- Open project from grid → 250ms directional entry; sidebar visibly leads main by ~40ms.
- Close project → 150ms reverse.
- No bounce, no overshoot at any viewport size.
- Animation does not trigger on internal navigation (file switches inside the panel) — only on panel mount/unmount.
- `ng build --configuration production` passes.

---

## Cross-Task Verification

Run after Task 5 (or each task before merging):

- ✅ All success criteria in `epic.md` checked manually.
- ✅ `categorise()`, `teaser(content.slice(0, 100))`, the `sidebar-status` row, and the trigger-mode toolbar branch are gone — grep returns nothing.
- ✅ Every affected Angular component is under 200 lines.
- ✅ `ng build --configuration production` passes.
- ✅ Smoke test on at least: a braindump-only project, a Ready-to-build project, a Specced project, an in-progress project, and an archived project. Each shows the right teaser, the right section, and the right chip set.
- ✅ Status bar exhibits all four color states (drive failure by stopping the API briefly).

## Out of Scope Reminders

If during implementation any of these come up, **don't expand scope** — log them and route to the appropriate follow-up:

- Thread/chain result model → `text-ops-thread-ui` epic.
- Keyboard shortcuts / command palette → second-pass.
- AI-emitted `insight` field → separate pipeline epic; the resolver will gain one branch when it lands.
- New project modal brainstorm helper → separate epic.
- Mobile / Ionic parity → not this epic.

## Sequencing Recap

```
Day 0.5  ┐ Task 1 (quick wins)         ┐
Day 1.5  ┘ Task 2 (taxonomy + teaser)  ┘  parallel
Day 3.5  → Task 3 (sidebar-first)       depends on 1
Day 5.0  ┐ Task 4 (status bar + dots)  ┐
Day 5.5  ┘ Task 5 (animation)          ┘  parallel after 3
```

Single-developer worst case: 5.5 days. With Tasks 1+2 and 4+5 parallelised across a pair: ~4 days.