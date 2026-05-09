# UX Polish — Newspaper Feel, Phase 2

> **Visual reference:** [Design Playground](http://localhost:8096/playground.html) — use this as Figma. Every component, token, state, and animation is live and inspectable. Code snippets there are verbatim implementation.

---

## Origin: ClawBoi → Specview landing → Specview app

The newspaper aesthetic did not originate with Specview. It comes from **ClawBoi**, a personal dashboard that established the visual language: masthead with date and edition, section tabs as editorial sections, 3-column grid as column layout, Playfair headlines, Source Serif body copy, borders instead of shadows, cream background, near-black ink.

When the Specview landing page was designed (2026-05), it was explicitly aligned to ClawBoi's patterns. The **app** (`web-ng/`) was built separately and has drifted. Color tokens were aligned on 2026-05-05, but structural and typographic gaps remain.

The goal of this epic: close every gap between the app and the established ClawBoi/landing aesthetic, while extending the system for app-specific patterns (status dots, editor toolbar, AI generation chain).

→ [App vs Landing comparison](http://localhost:8096/playground.html#pg-comparison)

---

## Design philosophy

**Dieter Rams minimalism + editorial newspaper layout.**

- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace create structure; shadows do not exist here
- Ink on paper: cream (`#FFFEF9`) not white, near-black (`#121212`) not black
- Interaction is quiet — hover is a whisper of background, nothing more
- Density without clutter: if it doesn't communicate something, it doesn't exist

The reader should focus entirely on content and ideas. The interface communicates structure through **semantic UX** — visual hierarchy from typography, spatial rhythm, and color used for meaning only.

→ [All design tokens live](http://localhost:8096/playground.html#pg-tokens)

---

## Color system

→ [Token swatches](http://localhost:8096/playground.html#pg-tokens) — all values are live and update with dark mode toggle.

### Core tokens

Identical across ClawBoi, landing, and app. Critical observations:

- `--border-dark` tracks `--ink` — it's `#121212` in light and `#E8E6E0` in dark, always the high-contrast structural break color
- `--bg` and `--ink` invert between modes; the paper-and-ink metaphor holds in both
- `--accent` lightens in dark mode to maintain visual weight
- `--red` lightens similarly, always legible against `--bg`

### Status tokens (app-only)

The app has live states that the landing doesn't: generation running, succeeded, failed.

→ [Status bar all 4 states](http://localhost:8096/playground.html#pg-comp-statusbar)

**Color evolution — important to preserve this rationale:**

`--status-running` went through three versions:
1. `#B8860B` (dark goldenrod) — too similar to error/warning
2. `#F59E0B` (amber) — treated "running" like a caution signal
3. `#22A66A` (current, green) — active generation is a positive-trajectory state

**The correct semantics:** Running = you're getting somewhere, positive motion. Amber = caution, needs attention. Green for running aligns with Slack active status, GitHub Actions, deploy platforms. It reads as "things are happening and going well."

**Do not revert to amber.** Amber is reserved for a future `--status-attention` token (e.g., "stale spec needs regeneration") — not yet implemented.

### Color semantics

| Token | Meaning | Use | Do not use for |
|-------|---------|-----|----------------|
| `--status-running` | Actively running | Running dot, active sidebar row | Idle/default state |
| `--status-success-bg` | Completed | Success dot, diff additions | Anything in progress |
| `--red` | Error, failure, alert | Failure dots, diff removals, overlines | Neutral or positive |
| `--accent` | Primary interactive action | Generate buttons, new project, links | Decoration |
| `--ink` | Primary content | Body text, titles, borders, active states | — |
| `--ink-muted` | Non-semantic, idle, decorative | Meta labels, idle dots, decorative glyphs | Any meaningful state |

**Rule: never use gray for a state.** Gray (`--ink-muted`) means no semantic meaning. Any dot or border that communicates state must use a semantic color. Idle = gray (no state), running = green, done = deep green, failed = red. No ambiguous amber.

---

## Dark mode — what needs fixing

→ [Interaction states in dark mode](http://localhost:8096/playground.html#pg-states)

### 1. Modal elevation

The modal `box-shadow` is nearly invisible on `#141414` background — the modal floats on darkness with no separation. Dark mode needs a stronger shadow. The modal overlay is a pragmatic exception to the no-shadow rule; it needs elevation above the dimmed backdrop.

### 2. Sticky editor toolbar

The floating toolbar's `border-top` (2px `var(--ink)`, which is `#E8E6E0` in dark mode) is thin and easy to miss. Anchored and floating states should feel visually consistent.

→ [Editor toolbar demo](http://localhost:8096/playground.html#pg-comp-toolbar)

### 3. Section nav separation

The section nav is sticky with `background: var(--bg)`. In dark mode, `--border` (`#2E2E2E`) on `#141414` is nearly invisible — content scrolls behind the nav with no clear edge.

### 4. Lucide icon contrast

Icons at `color: var(--ink-muted)` (`#606060`) against `#141414` are ~2.5:1 contrast — below the 3:1 minimum for UI elements. Meaningful icons (back arrow, close, op chips) need `var(--ink-light)` (`#A0A0A0`) as the floor.

---

## Typography gaps — app vs design system

→ [Typography specimens](http://localhost:8096/playground.html#pg-tokens) | [Masthead demo](http://localhost:8096/playground.html#pg-comp-masthead)

### Masthead (three issues)

**1. Title size** — App uses `56px`, landing uses `64px`, design system range is `56–64px`. App should match landing at `64px`.

**2. Tagline font** — App uses Source Sans 3 italic. The vision is Source Serif 4 italic — a sentence-length editorial thought, not a UI label. Source Serif italic at 13px reads as a newspaper deck; Source Sans reads as a UI label.

**3. Masthead align-items** — App uses `center`. Landing uses `flex-end` (bottom-align). Bottom-aligning creates a baseline that feels like the bottom of a printed masthead — more distinctive and authoritative.

### Nameplate rule missing

The landing's section bar has `border-top: 3px solid var(--ink)` — the nameplate rule between masthead and nav. This is how a newspaper section page begins: a thick horizontal rule that says "you are here in the publication." The app's section nav has no `border-top`, so the masthead-to-nav transition feels soft, not authoritative.

→ [Border system reference](http://localhost:8096/playground.html#pg-borders) | [Section nav demo](http://localhost:8096/playground.html#pg-comp-nav)

---

## Missing: overline pattern

The landing uses a red overline above its headline — the most distinctively "newspaper" element. The app has zero usage of this pattern.

→ [Overline + badge demo](http://localhost:8096/playground.html#pg-comp-overline)

Where to add it in the app:

1. **Section group headers in the grid** — above "Active", "Specced" etc. Currently plain gray labels. Red overline + `0.12em` tracking transforms them into proper section flags.
2. **File type label in the spec reader** — above the spec file title (e.g., "ARCHITECTURE" in red above the expanded title). The file name is in the sidebar; the content view should declare its category.
3. **Error states** — already uses `--red`; formalize with the overline class.

This is the single highest-impact typographic change. It immediately makes the app feel like the same product as the landing page.

---

## Icon system

→ [Component states](http://localhost:8096/playground.html#pg-states) | [Op chips demo](http://localhost:8096/playground.html#pg-comp-toolbar)

### Size standard

All content icons: `13px / stroke-width: 1.75`. The app currently inherits `1em` from parent context — inconsistent. Standardize explicitly.

### Color by context

| Context | Color |
|---------|-------|
| Navigational (back, close) | `var(--ink-muted)` |
| Doc type icons in aside/nav | `var(--ink-light)` |
| Op chip icons | `currentColor` (follows chip state) |
| Status icons | Same semantic color as the status |
| Generate/sparkles (accent action) | `var(--accent)` or white on filled |

**Icons can carry color.** This is the most important new rule. The sidebar status dot is already colored semantically — surrounding icons should reinforce the state. A `check` on success = `var(--status-success-bg)` green. An `alert-circle` on error = `var(--red)`.

### Op chip icon mapping

```
expand     → arrow-up-down
compress   → minimize-2
clarify    → help-circle
simplify   → feather
tldr       → align-left
bullets    → list
brainstorm → sparkles  (already present)
style      → palette
undo       → rotate-ccw
redo       → rotate-cw
```

---

## Semantic UX — content-first principle

> "The person will only focus on the content and the idea and less on the syntax. Everything communicates syntax by using semantic UX."

→ [Expanded panel + markdown layout](http://localhost:8096/playground.html#pg-comp-expanded) | [Markdown content](http://localhost:8096/playground.html#pg-comp-markdown)

1. **Interface recedes when reading.** Sidebar, toolbar, status bar — margins on a page. Present but unobtrusive.
2. **Document structure through typography.** H1 = Playfair 26px spanning full width. H2 = Playfair 20px. H3 = Source Sans 12px uppercase — a section label, not a headline. Hierarchy without learning the interface.
3. **Color signals state, not decoration.** Green pulsing dot = work happening. Settled deep green = done. Red = attention needed. No text required.
4. **Diff view feels editorial, not technical.** Red border + faint red background = removed. Green border + faint green background = added. Same semantic colors used everywhere.
5. **2-column markdown.** `column-count: 2` makes long specs feel like articles. H1 and pre/code span both columns. The eye flows naturally down column 1, continues in column 2.

→ [Diff blocks demo](http://localhost:8096/playground.html#pg-comp-diff) | [Animations](http://localhost:8096/playground.html#pg-animations)

### Remaining semantic gaps

- **Op chips** communicate nothing without reading the label. Icons fix this — `minimize-2` conveys "compress" before the word is read.
- **File type not declared** in reader view. An overline (`ARCHITECTURE` in red) immediately contextualizes.
- **Spec file order is random** (alphabetical). Reading should flow: braindump → analysis → epic → architecture → timeline → implementation-guide. The sidebar should reflect this sequence.

---

## What excellent looks like

Opening the app should feel like opening a newspaper. The masthead carries editorial authority (64px Playfair, cream, near-black). The section nav tabs have a nameplate rule above them — that thick 3px bar that says "you are here in the publication." Section group headers are red overlines, not neutral gray labels. The spec reader is two columns of Source Serif at comfortable size, with Playfair headings that feel like article sections.

The status system is unambiguous: green pulsing dot = work is happening and going well. Settled deep green = done. Red = something needs attention. No amber, no gray states, no ambiguity.

Icons earn their place. Compress chips have minimize-2. Clarify has help-circle. Familiar chips don't need labels after the first few sessions.

Dark mode feels like the light-mode equivalent on dark stock — the same paper/ink relationship, inverted. Cream warmth becomes warm dark `#141414` (not pure black). Near-black becomes warm cream `#E8E6E0`. Thick structural borders invert correctly.

The whole experience communicates: this is a tool for thinking with text. The interface steps back. The ideas step forward.

→ [Full playground](http://localhost:8096/playground.html) — all components, all states, all tokens.
