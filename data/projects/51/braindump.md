# UX — Reader, Text Ops & Navigation

## Skill comparison first: brainstorm vs superpower brainstorm

There are two brainstorm skills in this repo and they serve completely different jobs.

`plugin/skills/brainstorm/SKILL.md` — the **editor brainstorm** — is a text-ops skill invoked from the floating toolbar when you're reading a spec. It runs on whatever file is open. It returns four markdown sections (Key Themes, Hidden Connections, Open Questions, Ideas to Explore). Output is additive — the brainstorm appears above the original content as a `.brainstorm-result` div. You can run follow-ups with a question input. You can apply the result to overwrite the file. It's a thinking-aid, not a planning tool.

`.claude/skills/brainstorm/SKILL.md` — the **superpower brainstorm** — is a Claude Code skill invoked with `/brainstorm`. It's a three-pass process designed specifically to sharpen a raw project idea before spec generation: read and map, generate questions with options and recommendations, then rewrite the braindump into a clean version ready for spec-pipeline. It outputs structured JSON with a rewritten_braindump field. It's a planning tool.

The critical observation: the superpower brainstorm **already had the options + recommendation pattern** that we just added to the editor brainstorm. The editor brainstorm had shallow open questions — "what is X?" with no answer offered. Now both skills present options. But the jobs are different enough that this isn't redundancy — the editor brainstorm surfaces questions about the content you're reading; the superpower surfaces questions about the project you're planning.

One gap: the editor brainstorm has no connection to spec-pipeline unless you're on a braindump file. The superpower is explicitly designed to feed spec-pipeline. The `/spec-pipeline` SKILL.md now calls the editor brainstorm as a pre-analysis step — this is the first explicit connection between the two. That's worth thinking about more.

---

## What a user actually sees: the full UX map

I read the entire `app.component.html` template and `styles.css`. Here is what exists and how it actually works.

### Home screen — the project grid

The masthead is a newspaper header: "Spec Doc" in a small left label, date centered, "Specview" as a serif title, "All the Specs Fit to Read" as a tagline, and three action buttons top-right (New, theme toggle, Sign out). This is distinctive and gives the app a strong editorial identity.

Below it: a section nav with tabs. Each tab has a count badge. The tabs categorize projects into sections. Below that: a search bar with live filtering. Then: a multi-column file grid laid out like a newspaper front page. The first item in each column is "featured" (larger title, larger teaser text). Each project card shows: project name, teaser (first 100 chars of first file), file count, and a category label.

The grid is the right UX for a project list. The newspaper visual language is clear and intentional.

**Problems on the home screen:**
- The teaser only shows the first file's content. Most projects have `analysis.md` as the first file — so every teaser is the beginning of the analysis doc. That's actually useful. But it only shows ~100 chars, which is usually the first sentence of a heading, truncated mid-word. It looks like a preview but doesn't actually preview anything meaningful.
- The category labels come from `categorise(p.id)` — this is derived from the project ID string. So projects named `saas-monetisation-1777...` get categorised as "saas". Projects named `specview-phase4-...` get "specview". This is implicit taxonomy, not user-defined. Users with different naming conventions would get broken categories.
- The section nav tabs + search bar + column headers = three levels of navigation/filtering. That's a lot of chrome for a list. A new user doesn't know what the sections mean.

### Project open — the expanded panel

Clicking a project opens the two-column panel: sticky sidebar on the left, main content area on the right. The sidebar has: back button, project name, file list (as button nav), Generate Specs / Generate Guide buttons, and a status indicator row.

**The sidebar is good.** Fixed position, always visible during scroll, file switching is one click. The Generate Specs button only shows when the project has a braindump but no generated specs — that's a smart context-aware action.

**The main content area** shows: editor toolbar (sticky, floating at bottom when user scrolls), then spec content rendered as markdown.

The editor toolbar has two states:
1. Chips only (default) — the AI op buttons
2. Chips + Actions — when an AI result exists (adds latency badge, Apply, Copy, Dismiss)

The toolbar becomes floating (fixed to bottom of viewport with shadow) when `toolbarFloating()` is true — triggered by a scroll sentinel. This is smart interaction design.

### The AI text ops — how they actually work

When you click an op chip (Expand, Compress, Clarify, Simplify, TL;DR, Bullets, Style...) it fires immediately. No confirmation. The op reads the current file's content and posts to the API. The toolbar shows thinking dots. Result arrives.

There are two result modes:

**Additive ops (Brainstorm, TL;DR):** Result appears as `.brainstorm-result` ABOVE the original content. The original content stays visible below. You can run a follow-up question. If on a braindump file, you can generate specs from the brainstorm result.

**Rewriting ops (Expand, Compress, Clarify, Simplify, Bullets, Style):** The original content DISAPPEARS and is replaced by a paragraph-level diff view. Red background blocks = removed paragraphs. Green background blocks = added paragraphs. The diff is between the original and the result.

Both modes show Apply / Copy / Dismiss in the toolbar actions row.

Clicking the same chip again dismisses the result (toggle behavior — `toggleOp` sets activeOp to null and clears aiResult if it was already active).

---

## The real UX problems

### 1. Result placement is inverted

For additive ops (brainstorm/tldr), the result appears ABOVE the original. The toolbar is at the BOTTOM. So: you click a chip at the bottom of the screen, the AI works, and the result materialises at the TOP of the document. The user's eye is at the bottom (where they clicked) and the result appeared somewhere above them.

This is the core UX inversion: the action is at the bottom, the result is at the top. There's no scroll-to-result behavior. The `thinking...` indicator shows below the toolbar but it doesn't tell you where the result will appear.

The thread/chain model we designed (text-ops-thread-ui braindump) directly addresses this — results stack below the current content, which is where the user's attention is after clicking the toolbar.

### 2. The diff view hides the original

For rewriting ops, the original content is replaced by the diff. You can't see the full rewritten text — only which paragraphs changed. If a paragraph was lightly edited, both the removed and added versions appear, which doubles the content. This makes it harder to read the result as a whole document.

What you actually want to do after running Expand is: read the expanded version as a clean document, see roughly where it grew. The current diff shows changes but not the gestalt. The result could be shown clean, with removed blocks shown inline as strikethrough or in a collapsible section.

### 3. Op chips are always visible and always active

All 8 chips show the moment a file is open. On an architecture.md file that's 3000 words, "Bullets" and "Simplify" make sense. "Brainstorm" might not be what the user intends. There's no framing — the toolbar just appears with 8 unlabeled options.

The `isBraindump()` computed is supposed to conditionally show the Brainstorm chip, but it's currently `computed(() => !!this.currentSpec())` — which returns true for any open file, not just braindump.md. So Brainstorm shows on all files. This is either a bug or an intentional decision. The Brainstorm op on an architecture.md is actually useful (brainstorm the ideas in the architecture), but the naming is confusing — "Brainstorm" on a spec feels like you're running it on the spec, not getting new ideas from it.

### 4. Toggle-to-dismiss is invisible

Clicking an active chip dismisses the result. But there's also a "✕" Dismiss button in the actions row. Two ways to dismiss, neither obviously the "main" one. And the toggle behavior on chips is not discoverable — there's no visual affordance that says "click again to close."

### 5. Apply feels lightweight for a write operation

"✓ Apply" is a small button styled similarly to Copy and Dismiss. But Apply writes to disk and changes the spec file permanently. It should feel more consequential — bigger button, clearer label ("Save this version"), or a confirmation on large edits.

The undo stack (`canRevert`, `undoVersion`) exists, but the Undo chip only appears in the toolbar after Apply. So if you apply and immediately want to undo, you'd need to scan the toolbar to find the new Undo chip. It should be more prominent.

### 6. No keyboard navigation

The entire interaction model is mouse-only. No keyboard shortcuts for:
- Opening/switching files (arrow keys or J/K navigation in sidebar)
- Running the current op (Enter)
- Dismissing a result (Escape)
- Apply (Cmd+Enter or Cmd+S)
- Next/previous file (Cmd+] / Cmd+[)

A spec reader is a reading environment. Keyboard navigation is table-stakes for a reading experience. VI-style navigation (j/k for sections, enter to expand) would make power users extremely fast.

### 7. Two status indicators for the same thing

There's a `sidebar-status` row inside the sidebar (shows when specGenLoading or aiLoading) AND a `gen-status-bar` fixed to the bottom of the viewport (same conditions). Both show when an AI op is running. The bottom bar shows project name + step. The sidebar shows the same thing with a pulsing dot.

This is visual noise. One status indicator is enough. The bottom bar (always visible, even when in the project grid) is more useful — it answers "is anything happening right now?" from anywhere in the app. The sidebar status could be removed, or simplified to a small dot that links to the bottom bar.

### 8. The "Generate Specs" button is buried

For a new project with only a braindump.md, the primary action is Generate Specs. This button is in the sidebar, below the file list, below the Generate Guide button if it shows, below the file nav. For a braindump-only project the file nav has one item (braindump.md), so the button is visible. But it looks the same as "Generate Guide" — same styling, same position logic. The distinction between them is not obvious.

Generate Specs and Generate Guide should be visually different from each other and from the file nav buttons.

### 9. The modal textarea is a blank void

The new project modal has a project name input and a 14-row textarea for the braindump. The placeholder text explains what to put there. But a blank textarea with a placeholder is still intimidating — there's no example, no structure hint, no minimum required. 

First-time users don't know what a "good" braindump looks like. The superpower brainstorm exists to help shape a rough idea, but it's only accessible from Claude Code — not from the in-app modal. A user coming through the landing page CTA → signup → new project modal has no guide.

### 10. File switching clears the AI result

If you run Brainstorm on analysis.md, see the result, then accidentally click architecture.md in the sidebar, the result disappears. The file switch calls `selectFile()` which calls `aiResult.set(null)`. There's no warning. A user who got a valuable brainstorm result and is exploring the other files to compare loses the result permanently (without Apply).

---

## Navigation patterns that are missing

**Within a file:** The sidebar shows filenames. But long spec files (architecture.md at 3000+ words) have H2 sections. There's no in-file section navigation — no anchor jump, no TOC panel, no scroll-to-section. The user has to scroll manually through the entire document.

**Between projects:** You can't go from project A's analysis.md directly to project B's analysis.md. You have to: close expanded panel → find project B in grid → click → wait for it to open → click analysis.md. Four steps. A cross-project comparison is a common reading pattern ("how did I structure the architecture for project X vs project Y?").

**Spec file ordering:** The sidebar lists files in whatever order `project.specs` returns them. The natural reading order is analysis → epic → architecture → timeline → implementation-guide. If this order is correct, it's implicit. If it's wrong (implementation-guide appears before analysis), the reading flow breaks.

**Breadcrumb:** When you're in the expanded panel reading architecture.md, you can see the project name in the sidebar and the filename in the expanded title. But "Text Ops Thread UI → Architecture" is not shown as a navigational path. The ← All button just says "All" with no project context reminder.

---

## What "intuitive and reliable" requires

**Intuitive:**
- Results appear near where you triggered them, not across the screen
- Every action has a visible consequence that lands in the right place
- Primary actions (Generate Specs, Apply, Dismiss) are sized and styled to their weight
- The op chips have a clear affordance — clicking one should feel like pressing a button, not arming a mode
- There is exactly one place the status of an AI op lives — not two
- The diff view is scannable as a reading surface, not just as a change log

**Reliable:**
- You don't lose work accidentally (file switch warning, or result persists until explicitly dismissed)
- Apply is reversible with one click (Undo chip should be persistent and visible, not discoverable)
- Loading states are predictable — "Thinking…" with three dots should tell you roughly how long (brainstorm takes 8s, generate takes 90s — same indicator for both is misleading)
- Errors are recoverable — "Could not reach AI" offers a retry button, not just a message

---

## Ideas that would move the needle

**1. Result-adjacent rendering (thread model — see text-ops-thread-ui braindump)**
The most important single change. Results appear below the triggering text, scroll into view, and persist as a chain. File switching prompts "You have an unsaved result — dismiss or save?" before clearing.

**2. Persistent section nav inside the reader**
A secondary nav inside the expanded main panel that shows H2 headings of the current file. Clicking a heading scrolls to it. This turns the reader into a spec explorer, not just a document viewer.

**3. Weighted action buttons**
Apply = full-width solid button. Copy = small ghost. Dismiss = ✕ icon only. The weight of each button matches the weight of the action.

**4. Op chips as a single menu for non-brainstorm files**
Instead of 8 chips always visible, a single "AI ▾" button that expands to the chip row on hover/click. Or a compact row that shows Brainstorm prominently and collapses the rest into "More ops →". This reduces visual noise for first-time users who don't know what each op does.

**5. Keyboard shortcuts**
Escape = dismiss result. Cmd+Enter = apply. J/K = navigate between files. / = focus search. These are standard enough that power users would try them and be surprised they don't work.

**6. Brainstorm starter in the new project modal**
The new project modal should have a "✦ Help me brainstorm this" link that takes the user's partial braindump, runs the superpower brainstorm via the API, and rewrites it inline. This connects the superpower brainstorm to the in-app experience for the first time.

**7. Single persistent status indicator**
Keep the sidebar status row (positioned just below the file nav, inside the expanded panel sidebar) — this is the right location because it is always visible while reading and anchored to the project context. Remove the fixed bottom viewport bar. Add a small pulsing dot on the sidebar file entry that is currently being operated on.

**8. Cross-project file jump**
A keyboard shortcut (Cmd+K) opens a command palette that shows all projects × all files. Type to filter. Enter to jump. This is the fastest way to navigate a growing library of specs.

---

## What to fix first

The three changes with the highest UX return for lowest code effort:

1. **Thread model (text-ops-thread-ui)** — already designed, just needs implementing. Fixes problems 1, 2, and 10 simultaneously.
2. **Weighted Apply button** — one CSS change. Makes the most important action feel most important.
3. **Fix `isBraindump()`** — it's currently always true. Should only be true when the current file is `braindump.md`. One line of code. Removes Brainstorm from files where it's confusing.

Everything else — keyboard shortcuts, section nav TOC, command palette, modal brainstorm helper — is a second pass after the core reading and text-ops experience is right.

---

## Append: panel open animation, smarter grid, unified sidebar, live status

### Panel open animation

When you click a project card the expanded panel replaces the grid. Right now this is instant — the grid disappears and the two-column panel appears. There is no transition. At viewport scale this feels like a jarring cut.

The right animation is minimal and directional. The card that was clicked should feel like it expands into the panel — not a generic fade, a spatial metaphor. The panel should feel like it came from that card.

Concrete approach: the clicked `.file-item` card scales up slightly and its border radius collapses (200ms ease-out), while the grid fades out (150ms). The `.expanded-panel` enters from opacity 0, translateY(12px) to full (200ms ease-out, starting 50ms after grid begins fading). Net duration: ~250ms total. That's fast enough to feel instant, slow enough to give spatial context.

The sidebar should enter slightly before the main content — staggered by 40ms. This reinforces the two-column structure at the moment of assembly, not after. The sidebar slides in from the left (translateX(-8px) → 0). The main content rises in place (translateY(8px) → 0). Small values — this is not a dramatic animation, it's a spatial hint.

On close (← All), the reverse: panel fades to 0 and translateY(8px) while grid fades back in. 150ms each. The newspaper grid coming back into view should feel like "returning to the front page."

No bounce, no spring physics, no cubic-bezier that overshoots. These are editorial documents, not a social app. The animation should feel like turning a page, not opening a drawer.

Implementation: Angular `@trigger` animation or CSS classes toggled by `showExpanded()`. Angular animations handle enter/leave cleanly and are the right tool here. The `.expanded-panel` and `.file-grid` both need `@if` animation triggers. CSS approach: add `.expanded-panel--entering` class on mount, remove after 250ms. Simpler but less composable.

---

### The project grid teaser needs to surface insight, not just first-line text

The current teaser is `teaser(p.specs[0].content || '')` — the first 100 characters of the first file's content. For a project with analysis.md as the first file, this is the beginning of `# 🔍 ProjectName — Analysis`, truncated. That is not useful as a teaser. It tells you nothing about what the project is.

A newspaper front-page teaser is not the first sentence of the article — it's the editor's chosen hook. The piece of content that makes you want to read more. It answers "why does this matter, right now?"

For specview, the equivalent is: what is the sharpest sentence that describes what this project is and why it exists? That lives in different places depending on the project phase:
- Analysis-stage projects: The Problem section, first sentence ("What exists today, why it's broken")
- Epic-stage projects: The Business Value section, first sentence
- Architecture-stage projects: the opening decision paragraph
- Braindump-only projects: the braindump itself, first meaningful sentence (skip headings)

The algorithm: scan the first file for the first non-heading, non-empty, non-bullet paragraph. Take the first sentence only. This is almost always more informative than `content.slice(0, 100)`.

Better still: during spec generation, extract a one-sentence "insight" field into the project metadata. Something the analysis step could emit as part of its output — the single sharpest thing about this project. Store it in the project record. Show it as the teaser. This is not a search indexing problem, it's a generation problem. The AI already knows the sharpest insight — it just never surfaces it in a machine-readable field.

The teaser should also adapt to project state:
- No specs yet (braindump only): "Braindump — ready to generate"
- Specs generated, not yet acted on: the insight sentence
- Specs in progress (spec gen running): show live step ("generating architecture…")
- Has implementation guide: "Implementation guide ready · N tasks"

Each project card should communicate its current state without the user having to click into it.

The "featured" first card in each column gets a larger teaser (2-3 sentences, maybe the first paragraph of The Problem). Regular cards get one sentence. This is exactly how newspaper front pages work — the lead story has more editorial real estate.

---

### Section nav: dynamic badges and smarter categorisation

The section nav tabs currently show counts. The count is a static number — it tells you "3 projects in this section" but not what those projects are or whether anything has changed.

Newspaper sections work because readers know what to expect in each section. "Business" means a predictable content type. The current sections in specview are derived from project ID prefixes (saas-, specview-, etc.) — that's implicit and breaks with any naming convention.

The section nav should be explicit and meaningful:
- **Active** — projects with spec generation in progress or recently touched (< 7 days)
- **Ready to build** — projects with implementation guide generated
- **Specced** — projects with full analysis + epic + architecture but no implementation guide
- **Braindumps** — projects with only braindump.md
- **Archive** — archived projects

These are state-derived sections, not name-derived. Every project can be classified into exactly one of these states from its files list. The API already knows which files exist per project. This taxonomy is computed, not manual.

The count badge on each tab should pulse/animate when its count changes. If a spec generation completes and moves a project from "Braindumps" to "Specced", the "Specced" badge should flash once. This is subtle but reinforces that the system is alive and updating.

---

### The sidebar should be the single command centre

Currently buttons and actions are scattered:
- **Top right masthead**: New, Theme toggle, Sign out
- **Sidebar**: Generate Specs, Generate Guide, file nav, status indicator
- **Editor toolbar** (floating bottom): all AI text ops, Apply, Copy, Dismiss, Undo/Redo
- **Fixed bottom bar**: running status (spec gen or AI op)
- **Brainstorm result area**: follow-up input, Generate Specs from this brainstorm

A user who doesn't know where things live has to scan 4 different zones to find what they want. That's not a newspaper — a newspaper has a fixed structure (masthead, section labels, bylines) that readers learn once. The current layout makes the user re-discover the structure every time.

The sidebar should own all actions relevant to the current project:

```
┌─────────────────────┐
│ ← All               │
│                     │
│ PROJECT NAME        │
│                     │
│ — Files —           │
│  braindump.md       │
│  analysis.md   ●    │  ← current file, dot = active AI op
│  epic.md            │
│  architecture.md    │
│                     │
│ — Actions —         │
│  ✦ Generate Specs   │  ← only if applicable
│  ✦ Generate Guide   │  ← only if applicable
│  ✦ Run Text Op ▾    │  ← expands to op chips in sidebar
│  ↩ Undo             │  ← only if canRevert()
│                     │
│ — Status —          │
│  ● generating…      │  ← color-coded live status
│    analysis · 12s   │
└─────────────────────┘
```

The AI text op chips move from the floating bottom toolbar into the sidebar. The toolbar becomes the result-display area only — Apply/Copy/Dismiss for the current AI result — not the trigger area. This inverts the current model but resolves the "action is at the bottom, result is at the top" inversion problem simultaneously.

The sidebar actions are always visible, always in the same place. The user scans the sidebar, sees what's available, clicks once. No scrolling to find the toolbar.

This does mean the sidebar needs to be wider than it currently is to accommodate the op chips. The newspaper analogy supports this — sidebars in newspapers are content-rich columns, not just navigation rails.

---

### Status bars: color, detail, and explicit API semantics

The current status system is binary: either something is loading (dots animate) or nothing is. The color system is also binary: normal ink color, or red for errors.

This is not enough. The app is making live API calls — spec generation, AI text ops, polling for job status. Each of these has distinct states with distinct meanings. The user should see all of them, not just "something is happening."

**Color semantics (strict and consistent):**

- **Green** (`#2E7D32` or the existing `--accent` shifted warm) — completed successfully. Spec generation finished. AI result ready. File saved. This color should flash briefly on the relevant element and fade — not persist, just acknowledge.
- **Yellow / amber** (`#F59E0B`) — in progress or polling. Something is running. The dots are yellow. The status text is yellow. This is "I'm working on it."
- **Red** (`var(--red)`) — failed or unreachable. API error, skill timeout, CLI exit 1. The status turns red and stays red until acknowledged or retried. Includes a specific error description, not just "error."
- **Neutral** — idle. No color, just the default ink. Nothing is happening.

**Explicit API call display:**

Right now the status bar shows `specGenStep() ?? 'starting…'` and `aiOpLabel()`. These are high-level labels. The user knows "something is generating" but not what API call is running, how far it is, or why it's slow.

The status bar should show the actual operation in progress with as much detail as the API returns:

```
● generating  ·  bootstrap-project  ·  step: architecture  ·  32s elapsed  ·  streaming…
```

For AI text ops:
```
● ai op  ·  brainstorm  ·  POST /api/brainstorm  ·  waiting for response…
```

For polling:
```
● polling  ·  job_id: abc123  ·  GET /api/ai/text/bootstrap-project/status  ·  attempt 7
```

This level of detail is what a developer and product builder wants to see. It turns the status bar into an audit log, not just a spinner. When something is slow, you see "attempt 14 · 28s elapsed" and immediately know if it's stuck. When something fails, you see the exact endpoint and can diagnose quickly.

The job ID should be visible and copyable. If you need to check container logs, knowing the job ID lets you grep precisely.

The "connected" state matters too. The app polls `/api/health` via `pollOk()`. If the API becomes unreachable, the status bar should show red with "API unreachable · last seen 12s ago" and a retry button. Not just `!pollOk()` hiding somewhere in the sidebar.

**The sidebar status row is the right home for live status.**

The `sidebar-status` row — positioned just below the file nav inside the expanded panel sidebar — stays. It is anchored to the project context, always visible while reading, and doesn't compete with page content. The fixed bottom viewport bar (`gen-status-bar`) is removed — it duplicates the sidebar and competes with the floating toolbar.

The sidebar status row should always be visible when inside a project, not just when something is loading. Idle state: `● connected · last sync 2s ago` — green dot, small text, same sidebar typography. This tells the user the system is alive continuously, not just when a job runs.

Active state (yellow): `● generating · bootstrap-project · step: architecture · 34s`. Running job name, current step, elapsed time. Clickable — opens a detail drawer or expands inline.

Error state (red): `● failed · brainstorm · POST /api/brainstorm · 500`. Stays red and persists. Includes a retry button inline.

**Per-file status dots in the sidebar file nav:**

Each file entry in `sidebar-nav` gets a small dot on the right. Dot states: no dot (idle/clean), yellow pulse (AI op running on this file), green flash-then-disappear (op completed), red persistent (op failed). This makes the sidebar a live map of file-level AI state, visible even when you're on a different file.

---

### Newspaper analogy — go deeper

The current newspaper styling (Playfair Display header, Source Serif 4 body, column grid) establishes the aesthetic but doesn't push the analogy as far as it can go.

In a real newspaper:
- **Every story has a dateline** — when was this written, by which correspondent. In specview: when was this spec generated, how long did it take, which model produced it. This metadata should appear as a small dateline at the top of each spec file: `Generated 3 May 2026 · 94s · claude-sonnet-4-6`.
- **Section headers are editorial** — "TECHNOLOGY", "BUSINESS", "ANALYSIS". In specview the section tabs should use this vocabulary, all-caps, serif, authoritative.
- **The front page signals status through placement** — above the fold = important and current. Below the fold = background. Projects currently generating should appear "above the fold" in the grid — first card, largest teaser, pulsing yellow status dot.
- **Pull quotes** — a highlighted sentence pulled out of the article body to draw readers in. In specview: a pulled quote from the spec's sharpest insight, shown larger in the project card. Not the first sentence — the best sentence.
- **Breaking news banner** — when a spec generation completes while the user is looking at the grid, a temporary banner at the top: "✦ ProjectName — spec generation complete". This is the equivalent of a live update banner in digital news. It fades after 4 seconds.

These are not cosmetic changes — they deepen the conceptual model. Specview is a publication system for project thinking. The newspaper analogy makes that concrete. Every interaction should reinforce it.

---

### Style chip placement is broken

When you click the Style… chip, the preset options (Concise, Technical, Executive, Narrative, Punchy) appear as a separate `.style-presets` row rendered at the very top of the `.expanded-main` area — above the title, above the content, above the result area. They are completely disconnected from the Style chip that triggered them.

The user clicks "Style…" in the floating toolbar at the bottom of the screen, and the options appear at the top of the screen. Same spatial inversion problem as the brainstorm result. The user's eye is at the bottom, the affordance appeared at the top.

The style presets should appear immediately adjacent to the Style chip — as an inline expansion within the toolbar chip row, or as a small popover anchored to the Style button. The chip row already has horizontal space. The presets could flow inline after the Style chip when active:

```
[Brainstorm] [Expand] [Compress] … [Style ▾] → [Concise] [Technical] [Executive] [Narrative] [Punchy]
```

Or as a floating row just above the chip that triggered it (popover above the Style button, not above the entire document). Either is better than rendering at the top of the main content area.

In the sidebar-first model where AI ops move to the sidebar, the Style chip and its presets both live in the sidebar — the presets expand inline below the Style entry, which is the most natural placement of all.
