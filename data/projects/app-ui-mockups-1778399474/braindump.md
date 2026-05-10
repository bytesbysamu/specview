# App UI Mockups — Pure HTML Design Iteration

## Purpose

Build static HTML mockups of the Specview app pages directly inside `landing/`, reusing `style.css`. No Angular, no TypeScript, no build step. Open in browser, edit HTML, refresh — instant iteration.

The goal is to move fast on visual decisions without the overhead of the Angular app. Once a design is validated in the mockup, the Angular template gets updated to match.

---

## Why this approach

- The Angular app (`web-ng`) requires a build or dev server for every change
- `playground.html` proved this works well for components — same concept but for full pages
- `landing/style.css` already has all tokens, typography, borders, components
- The landing nginx container (port 8096) serves any `.html` file in `landing/` instantly
- No framework complexity — just HTML + CSS, pure design iteration

---

## What we have built so far (as of 2026-05-10)

### Design system (`landing/style.css`)
All tokens, components, and patterns are defined here and shared between landing page and playground:

- **Color tokens**: `--ink`, `--ink-light`, `--ink-muted`, `--border`, `--border-dark`, `--accent`, `--red`, `--bg`, `--status-running`, `--status-success-bg`, `--status-failure`
- **Typography**: Playfair Display (headlines), Source Serif 4 (body), Source Sans 3 (UI/meta)
- **Dark mode**: `[data-theme="dark"]` attribute on `<html>`

### Components already in `style.css` (from playground + landing work)
| Class | Description |
|-------|-------------|
| `.masthead` | Editorial newspaper-style header |
| `.section-nav` / `.section-link` | Tab navigation bar |
| `.file-grid` | 3-column newspaper grid |
| `.file-column` | Column with header + file items |
| `.file-item` / `.file-item.featured` | Project card (normal + featured sizes) |
| `.file-item-title` / `.file-item-teaser` / `.file-item-meta` | Card content |
| `.section-group` / `.section-group-cards` | Grouped grid (all-sections view) |
| `.section-group-title` / `.section-group-count` | Group header |
| `.sidebar-status` / `.sidebar-status-dot` / `.sidebar-status-text` | Status row |
| `.gen-status-bar` / `.gen-status-bar--active` / `.gen-status-track` | Generation bar |
| `.search-bar` | Search input |
| `.update-banner` | Dark banner strip |
| `.btn-primary` / `.btn-secondary` / `.new-project-btn` | Buttons |
| `.op-chip` / `.op-chip--accent` | Text operation chips |
| `.modal` / `.modal-backdrop` | Modal overlay |
| `.overline` | Small caps section label |
| `.section-count-pulse` | Animated count badge |
| `.context-card` / `.context-grid` | Context file cards |

### Design decisions already made
- Newspaper editorial aesthetic — borders do the work, no cards/shadows (one exception: modal)
- Playfair Display for all titles, Source Sans 3 for all meta/UI
- `--status-running` (green) = Active, `--accent` (blue) = Specced, `--ink-muted` = Braindumps
- Left border accent on cards keyed to section state (3px, semantic color)
- Featured card: first item in a group gets 18px title, 3-line teaser clamp
- Negative-margin hover bleed on column cards (`margin: 0 -12px; padding: 16px 12px`)
- No shadows except: modal box-shadow, context-card hover (intentional exceptions)

### Pages in playground (`landing/playground.html`)
Component-level demos, not full pages. Sections: Design Tokens, Border System, Components, Animations, States, App vs Landing comparison.

---

## Pages to build

### Page 1: Overview (project grid)

**File:** `landing/app-overview.html`
**Serve at:** `http://localhost:8096/app-overview.html`

The main landing view of the app — the project grid before any project is selected.

#### Layout wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│  Specview                                    [☀/☾]  [Sign out]  │  ← slim app header
├──────────────────────────────────────────────────────────────────┤
│  All  Active  Ready to build  Specced  Braindumps  Archive  [+]  │  ← section nav + new btn
│  ● generating analysis… — UX: App Grid Polish                    │  ← action status strip
├──────────────────────────────────────────────────────────────────┤
│  [🔍 Filter projects…]                                           │  ← search bar
│                                                                  │
│  ACTIVE  1                                                       │  ← green title (--status-running)
│  ┌──────────────┬──────────────┬──────────────┐                  │
│  │▌▌ UX Polish  │▌ Auth Flow  │              │                  │  ← green left border, featured = wider title
│  │  Big title   │              │              │                  │
│  │  3-line tsr  │              │              │                  │
│  └──────────────┴──────────────┴──────────────┘                  │
│                                                                  │
│  SPECCED  2                                                      │  ← blue title (--accent)
│  ┌──────────────┬──────────────┬──────────────┐                  │
│  │▌ Landing v2  │▌ ClawBoi    │              │                  │  ← blue left border
│  └──────────────┴──────────────┴──────────────┘                  │
│                                                                  │
│  BRAINDUMPS  3                                                   │  ← muted, no title tint
│  ┌──────────────┬──────────────┬──────────────┐                  │
│  │▌ Grid Polish │▌ CI Quality  │▌ Icons       │                  │  ← muted border, real teaser
│  │  First sent  │  First sent  │  First sent  │                  │
│  └──────────────┴──────────────┴──────────────┘                  │
│                                                                  │
│  READY TO BUILD  1                                               │
│  ┌──────────────┐                                                │
│  │  Specview v2 │                                                │  ← no border
│  └──────────────┘                                                │
└──────────────────────────────────────────────────────────────────┘
```

#### Key design decisions to validate

1. **App header style**: Slim single-line (logo left, actions right) vs the editorial masthead in landing. App should NOT use the big editorial header — it's a tool, not a publication. Decide: just wordmark + icon buttons, or add a subtle date/build label?

2. **Nav tabs with/without icons**: Show both variants. Tab bar currently text-only (icons were removed with Lucide). Mockup both: text-only and text + icon (using inline SVG or Unicode placeholder).

3. **Action status strip**: New element below the nav bar — always present, shows current operation. States to mock:
   - Idle: no strip (hidden), OR subtle "● connected" in muted ink
   - Active: green dot + step name + project name
   - Success: green "done" (brief)
   - Failure: red dot + error text + retry link

4. **Section group header**: `ACTIVE` in green overline vs neutral overline with colored count badge vs full row with colored left rule.

5. **Card sizes**: Show `12px 8px` (old) vs `16px 12px` (new) side by side in a callout comment.

6. **Empty section groups**: Should sections with 0 projects be hidden or shown as collapsed headers?

7. **New project button**: Placement — in the nav bar (right side), or floating, or as a section at the bottom of the grid?

8. **Search bar**: Full-width below nav, or inline in the nav bar right side?

#### Mockup content (real project names to use)

Use actual project names from `data/projects/`:
- Active: "UX: App Grid Polish" (generating analysis…)
- Specced: "Landing v2", "ClawBoi Ecosystem"
- Braindumps: "App UI Mockups", "CI & Test Quality", "UX: Newspaper Polish"
- Ready to build: "Specview Auth"
- Archive: (collapsed or hidden)

---

### Page 2: Project reader (future)

**File:** `landing/app-reader.html`

The expanded panel view — sidebar file list + main markdown content area. Not started yet.

---

## References

### Design system source
- `landing/style.css` — all tokens and components
- `landing/playground.html` — component-level demos and documentation

### Inspiration
- `clawboi/dashboard/style.css` — newspaper grid, memory-item patterns, column layout
- `landing/landing-v2.html` — newspaper editorial aesthetic in action

### App source (for structure reference only — not for copying code)
- `web-ng/src/app/app.component.html` — current Angular template structure
- `web-ng/src/styles.css` — app-specific CSS (some classes not in landing/style.css)

### Key differences: app CSS vs landing CSS
Some classes exist in `web-ng/src/styles.css` but NOT in `landing/style.css`. These need to be added inline or to `style.css` when building mockups:
- `.sidebar-status`, `.sidebar-status-dot`, `.sidebar-status-text`, `.sidebar-status--active/success/failure`
- `.section-group`, `.section-group-cards`, `.section-group-header`, `.section-group-title`, `.section-group-count`
- `.expanded-meta`, `.section-group-header border-bottom` rule
- Semantic color rules: `[data-section]` attribute selectors + `--section-accent`

---

## Build approach

1. Create `landing/app-overview.html`
2. `<link rel="stylesheet" href="style.css">` — reuse landing CSS
3. Add a `<style>` block for any app-specific rules not yet in `style.css`
4. Once a rule is validated and stable → promote to `style.css`
5. Iterate: edit HTML → refresh browser at `http://localhost:8096/app-overview.html`
6. When the design is locked, update Angular template to match

---

## What this is NOT

- Not a prototype with JavaScript interactions (except theme toggle, which is already in playground)
- Not a replacement for the Angular app
- Not a deliverable — it's a design scratchpad
- Not committed with every change — only commit when a design decision is locked

---

## Build log

### 2026-05-10 — `landing/app-overview.html` created

**File:** `landing/app-overview.html`
**Serve at:** `http://localhost:8096/app-overview.html`

#### What was built

Three variants on one page for rapid comparison:

**Variant A — Full overview (all sections)**
- Slim app header (wordmark left, theme toggle + sign out right) — not the editorial masthead
- Text-only section nav tabs with count badges, `+ New` button pushed right
- Action status strip below nav — active state with animated green dot + project name + step
- Search bar with project count
- All four section groups: Active (1), Specced (2), Braindumps (3), Ready to build (1)
- Semantic left borders: green (Active), blue (Specced), muted (Braindumps), transparent (Ready)
- Section titles colored for Active (green) and Specced (blue) only
- Featured card (first in each group): 18px Playfair title, 3-line teaser clamp
- Real teaser copy from actual project descriptions

**Variant B — Nav with inline SVG icons + status strip states**
- Same header, nav tabs with 12×12 SVG icons (no external dependency)
- All four status strip states side by side: idle (empty), active, success, failure with retry button

**Variant C — Single section column view**
- Braindumps tab active
- 3-column `file-grid` with left border on first column (muted accent)
- Shows real teaser content per card

#### CSS approach

All app-specific rules live in a `<style>` block in the HTML file:
- `.app-header`, `.app-wordmark`, `.app-signout` — slim header
- `.action-status-strip` + `--idle/active/failure` modifiers + `@keyframes poll-pulse`
- `.section-group`, `.section-group-cards`, `.section-group-header` — taxonomy grouping
- `[data-section]` attribute selectors + `--section-accent` custom property
- `.file-item` overrides (16px 12px padding, 0 -12px margin, featured sizes)

#### Design decisions captured in mockup

| Decision | What the mockup shows |
|---|---|
| Header style | Slim single-line — wordmark + icon buttons only, no editorial date/tagline |
| Nav icons | Both: text-only (A) and inline SVG icons (B) — pick one |
| Status strip placement | Below nav, above search — full width, 32px min-height |
| Status strip idle state | Empty strip (no dot, no text) — not "connected" |
| Section title tint | Only Active (green) and Specced (blue); others neutral overline |
| Featured card | First card in each group gets 18px title, 3-line clamp |
| Empty section groups | Hidden (not shown in mock — only sections with projects rendered) |
| New project button | Right-aligned in nav bar, not floating |
| Search bar | Below nav + status strip, full-width left-aligned |

#### Open questions for next iteration

1. Nav icons: inline SVG vs Unicode vs no icons — which reads better at 12px?
2. Status strip idle: truly hidden, or show a faint "● connected" in ink-muted?
3. Should Active section cards show the generation progress bar inside the card itself?
4. Column view: should only one column be populated, or all three with overflow?
5. Count badge on nav tabs: inside the tab button (current) or as a superscript dot?

---

## Grid/Overview Design Research — 2026-05-10

Cross-referenced: Specview git history, ClawBoi dashboard, landing design system.

### What the git history shows

The overview has gone through three distinct phases:

**Phase 1 — `9fd2968` (original Angular port)**
Fixed 3-column `.file-grid` with vertical column separators (`border-right: 1px solid var(--border)`), `gap: 0`, `padding: 24px`. All projects shown in one undifferentiated grid. No section grouping.

**Phase 2 — `932c88d` / `678c942` (UX overhaul)**
Introduced `.section-group-cards` with `repeat(auto-fill, minmax(240px, 1fr))` and `gap: 1px` (border-as-divider). Section taxonomy introduced. Two separate systems coexist: auto-fill grid for "All" view, fixed 3-column for single-section view.

**Phase 3 — `80c5b18` (current, newspaper aesthetic)**
Lucide icons removed, `.overline` applied to section headers, sidebar reordering. Grid structure unchanged from Phase 2.

**Key observation:** Every redesign has kept the 3-column newspaper grid for the single-section column view. The `section-group-cards` auto-fill grid is newer (Phase 2) and less developed visually.

---

### What ClawBoi does differently

ClawBoi (`clawboi/dashboard/style.css`) uses a richer hierarchy in three tiers:

**Tier 1 — Headlines (above the fold)**
`display: grid; grid-template-columns: 2fr 1fr 1fr` — one large hero + two secondary cards side by side. Hero (`headline-main`): 32px Playfair title, 16px body teaser, 4-line clamp, `border-right: 1px solid var(--border)`. Secondary (`headline-secondary`): 18px title, 14px teaser, 3-line clamp.

**Tier 2 — Newspaper grid (below the fold)**
`display: grid; grid-template-columns: repeat(3, 1fr); gap: 0` — three equal columns, each a `section-column` with `padding: 0 20px` and `border-right`. Items are `memory-item` with `padding: 12px 0` (column provides horizontal padding).

**Tier 3 — Memory items**
`memory-item`: 12px vertical padding, `border-bottom`. Hover: `margin: 0 -8px; padding: 12px 8px` — negative-margin bleed activates on hover only (not at rest). Featured: 17px title vs 15px, 3-line clamp vs 2-line.

**Key observation:** ClawBoi's above-the-fold 2fr/1fr/1fr hero system has NO equivalent in the Specview app. This is the richest unexploited pattern.

---

### Ranked design directions

#### 1. Hero + Grid hybrid (highest impact)

**What:** Apply ClawBoi's `2fr 1fr 1fr` above-the-fold hero layout to the Active section — the currently-generating or most-recently-active project gets a large hero card, the next two get secondary cards. All other sections use the standard auto-fill grid below.

**Key CSS:**
```css
.section-group--hero .section-group-cards {
  grid-template-columns: 2fr 1fr 1fr;
  gap: 0;
  background: none;
}
.section-group--hero .file-item.hero-main {
  padding: 20px 24px 20px 0;
  border-right: 1px solid var(--border);
}
.section-group--hero .file-item.hero-main .file-item-title { font-size: 24px; -webkit-line-clamp: 4; }
.section-group--hero .file-item.hero-secondary { padding: 12px 16px; border-right: 1px solid var(--border); }
.section-group--hero .file-item.hero-secondary:last-child { border-right: none; }
```
**Gain:** Strong visual hierarchy, newspaper-editorial feel, Active section immediately commands attention.
**Lose:** Only works well when Active has 2–3 projects. Single or zero items look orphaned. Needs fallback.

---

#### 2. Breathing room on current system (lowest risk, high ROI)

**What:** Keep everything, increase spacing only. Column padding `24px → 32px`, card padding `12px 8px → 16px 12px`, section group margin `24px → 32px`, grid min-width `240px → 280px`.

**Key CSS:**
```css
.file-column { padding: 0 32px; }
.section-group { margin-bottom: 32px; }
.section-group-cards { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.file-item { padding: 16px 12px; margin: 0 -12px; }
.section-group-cards .file-item { padding: 16px; margin: 0; }
```
**Gain:** Premium feel, no structural change, easy to A/B compare in mockup. Matches ClawBoi's column padding.
**Lose:** Fewer cards above fold, more scroll.

---

#### 3. ClawBoi hover bleed on column cards

**What:** Adopt ClawBoi's hover pattern exactly — at rest, cards have `padding: 12px 0` with no horizontal padding; hover triggers `margin: 0 -8px; padding: 12px 8px`. The column itself provides horizontal padding. This means cards visually "expand" into the column gutter on hover.

**Key CSS:**
```css
/* Column provides horizontal padding */
.file-column { padding: 0 20px; }
.file-column:first-child { padding-left: 0; }
.file-column:last-child { padding-right: 0; }

/* Cards have no horizontal padding at rest */
.file-item { padding: 12px 0; margin: 0; border-bottom: 1px solid var(--border); }

/* On hover: bleed into column padding */
.file-item:hover { background: rgba(0,0,0,0.025); margin: 0 -8px; padding: 12px 8px; }
```
**Gain:** Satisfying hover feedback, matches ClawBoi's exact interaction model, requires no layout change.
**Lose:** At rest, cards look spacious but horizontally flush — different from current style. Works only in column view (grid cards can't use negative-margin bleed).

---

#### 4. Single unified grid (simplification)

**What:** Remove the dual-system (auto-fill for "All", 3-column for single section). Use `repeat(auto-fill, minmax(280px, 1fr))` everywhere. Section grouping in "All" view; no section grouping in single-section view.

**Key CSS:**
```css
.file-grid, .section-group-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1px;
  background: var(--border);
}
.file-item { background: var(--bg); padding: 16px; margin: 0; }
```
**Gain:** One CSS system, fully responsive, consistent across all views.
**Lose:** Newspaper column aesthetic lost in single-section view. Less editorial feel.

---

#### 5. Masonry with variable card heights

**What:** Use CSS `grid-template-rows: masonry` (or JS fallback) to allow cards with longer teasers to take more height without leaving blank space. Featured cards still first in flow.

**Gain:** Denser packing, more organic editorial feel, teasers never truncated.
**Lose:** Browser support is experimental (`masonry` not in all browsers). Inconsistent row heights make scanning harder. Not aligned with the clean grid aesthetic.

---

### Recommendation for next mockup iteration

**Implement in `app-overview.html`:**

1. **Direction 2 first** — increase spacing to match ClawBoi (`32px` column padding, `16px 12px` card padding). Low risk, high visual payoff. Compare side-by-side with current in mockup.

2. **Direction 1 second** — try the `2fr 1fr 1fr` hero grid for the Active section only. Leave all other sections as auto-fill. This preserves simplicity while adding hierarchy where it matters most.

3. **Direction 3 third** — try the ClawBoi hover bleed on the single-section column view. Adds interactivity with no structural change.

Avoid directions 4 (too much simplification) and 5 (browser support) for now.

### CSS values to steal directly from ClawBoi

| ClawBoi value | Current Specview | Proposed |
|---|---|---|
| Column padding: `0 20px` | `0 24px` | `0 24px` (already close) |
| Memory-item padding: `12px 0` | `12px 8px` | Try `12px 0` with column-provided padding |
| Hover bleed: `margin: 0 -8px` | Same | Same but triggered on hover only |
| Featured title: `17px` | `18px` | Already better |
| Featured clamp: `3` | `3` | Match |
| Hero title: `32px` | Not used | New hero card pattern |
| Hero summary clamp: `4` | Not used | New hero card pattern |
| Column rule: `1px solid var(--border)` | Same | Same |

---

## ClawBoi vs Mock C — Gap Analysis (2026-05-10)

Comparing our promoted working mock (C: hero grid + section colors + breathing room) against ClawBoi's production dashboard. Focus: grid, spacing, organization, typography, color.

### Grid & space

| Property | ClawBoi | Mock C | Gap / Experiment |
|---|---|---|---|
| Hero grid gap | `gap: 24px` | `gap: 0` + `border-right` + padding | Try `gap: 24px` — removes need for card `border-right` and complex padding, cleaner |
| Hero main title | `32px` 700 | `26px` 700 | Bump to `28px` or `30px` — ours is undersized vs the 2fr column width |
| Hero main teaser | `16px`, 4-line | `15px`, 4-line | Bump to `16px` for parity |
| Standard card padding | `12px 0` (column provides horiz.) | `20px 20px 20px 17px` | Our cards carry their own horizontal padding; ClawBoi delegates to column. Try `16px 0` in standard grid with column-provided padding? |
| Column internal padding | `0 20px` on center/right columns | N/A (no column layout in All view) | Only applies if we add a single-section column view mock |
| Section bottom margin | Divider-based (`16px margin`) | `32px` (margin only, no divider) | Add a 1px `var(--border)` rule between sections, reduce margin to `24px` — tighter + more structured |

### Typography

| Property | ClawBoi | Mock C | Gap / Experiment |
|---|---|---|---|
| Body/teaser font | `Source Serif 4` (serif) | `Source Sans 3` (sans) | **Big miss.** ClawBoi uses serif for all body text — teasers, summaries, descriptions. We use sans-serif everywhere. Try `Source Serif 4` on `.file-item-teaser` — strengthens newspaper feel significantly |
| Masthead title | `56px` Playfair | `64px` Playfair | Ours is larger — intentional, app has fewer competing elements |
| Section header border | `2px solid var(--ink)` | `1px solid var(--border)` | **Weak headers.** ClawBoi uses ink-weight bottom border on section labels. Try `2px solid var(--ink)` — more authoritative |
| Section header style | `inline-block` (underline only spans text) | Full-width `border-bottom` | ClawBoi's `inline-block` trick: underline only spans the label text, not full width. More editorial. Try it. |
| Markdown h3 styling | `13px 600 uppercase, letter-spacing: 0.05em` | N/A | Not applicable in overview mock |
| Overline letter-spacing | `0.1em` (widget-title) | `0.12em` | Close enough — leave as-is |

### Color & semantics

| Property | ClawBoi | Mock C | Gap / Experiment |
|---|---|---|---|
| Section color system | None — all sections same color | 4 colors: green (Active), blue (Specced), purple (Ready), brown (Braindumps) | **Our advantage.** ClawBoi has no section differentiation. Keep this. |
| Mood color scale | 6-step green → red (`--mood-10` to `--mood-0`) | Not applicable | Could adapt as a project health/completeness indicator (how many specs generated?) |
| Badge system | `.badge-new`: red bg, white text, 9px, `padding: 2px 6px`, `border-radius: 2px` | None | **Missing.** Add badges for states like "NEW", "3 specs", or file count. Experiment with `--section-color` bg instead of red. |
| Status dot | None | Animated green pulse (`.status-dot`) | **Our advantage.** Keep — ClawBoi doesn't have this. |
| Accent usage | Links only (`--accent`) | Links + Specced section color | Same variable, expanded use. Good. |
| Hover color | `rgba(0,0,0,0.02)` | `rgba(0,0,0,0.025)` | Nearly identical. Fine. |

### Card patterns & interaction

| Property | ClawBoi | Mock C | Gap / Experiment |
|---|---|---|---|
| Hover bleed | `margin: 0 -8px; padding: 12px 8px` on hover only | Background color change only | **Missing.** Add negative-margin hover bleed to standard grid cards. At rest: flush. On hover: card expands into gutter. Satisfying tactile feedback. |
| Inter-section dividers | `.divider.thick`: 3px, `var(--border-dark)` between major sections | None — just margin space | **Missing.** Add a thin horizontal rule between section groups. `1px solid var(--border)` after each `.section-group` except last. |
| Featured card distinction | 17px title (vs 15px regular), 3-line clamp | No featured cards in standard grid | Add `featured` class back to first card in each section — larger title, longer teaser clamp |
| Card border radius | `2px` (inputs/buttons only) | None | Match — no radius on cards. Clean. |
| Empty state | `13px italic Source Sans 3, color: var(--ink-muted), padding: 20px 0` | Not shown | Worth adding to Archive section — "No archived projects yet" |

### Organization

| Property | ClawBoi | Mock C | Gap / Experiment |
|---|---|---|---|
| Thick top rule | `3px solid var(--border-dark)` above nav | `3px solid var(--ink)` above nav | Same concept — ours uses `--ink` which is correct |
| Section count display | `font-size: 9px; opacity: 0.6` inline with nav | `font-size: 9px; background: var(--border); padding: 1px 5px` as pill badge | Different approaches. Both work. Ours is slightly more visible — keep. |
| Sidebar widgets | Stacked vertically with `margin-bottom: 24px; padding-bottom: 20px; border-bottom` | N/A (no sidebar in overview mock) | Not applicable yet — relevant for page 2 (project reader) |
| Column-count for body | `column-count: 2; column-gap: 32px; column-rule: 1px solid var(--border)` | N/A | Not applicable in overview — relevant for expanded reader view |

---

### Experiment queue for next mockup iteration

Priority ordered. Each experiment can be toggled independently.

#### E1 — Serif teasers (high impact, zero risk)
Change `.file-item-teaser` to `font-family: 'Source Serif 4', Georgia, serif`. Already loaded via Google Fonts link. Biggest single-change improvement for newspaper feel.

#### E2 — Inter-section dividers (medium impact)
Add `border-bottom: 1px solid var(--border); padding-bottom: 24px` to `.section-group`. Reduce `margin-bottom` from `32px` to `24px`. Creates visual rhythm between sections.

#### E3 — Heavier section headers (medium impact)
Change `.section-group-header` from `border-bottom: 1px solid var(--border)` to `border-bottom: 2px solid var(--ink)`. Make `display: inline-block` so underline only spans the label text, not the full width.

#### E4 — Hero grid gap (medium impact)
Change `.hero-grid` from `gap: 0` to `gap: 24px`. Remove `border-right` from hero cards. Simpler CSS, more whitespace between columns.

#### E5 — Hero title size bump (low risk)
Increase `.hero-main .file-item-title` from `26px` to `28–30px`. Increase teaser from `15px` to `16px`.

#### E6 — Hover bleed on standard cards (interactive)
At rest: `padding: 16px 0`. On hover: `margin: 0 -8px; padding: 16px 8px; background: rgba(0,0,0,0.025)`. Only works in standard grid, not hero grid.

#### E7 — Featured first card per section (visual hierarchy)
First `.file-item` in each `.section-group-cards` gets: title `17–18px`, teaser `14px`, clamp `3` lines. CSS: `.section-group-cards .file-item:first-child .file-item-title { font-size: 17px; }`.

#### E8 — Status badge pill (additive)
Add a small pill badge to cards showing file count or status. CSS: `.badge { background: var(--section-color); color: white; font-size: 9px; padding: 2px 6px; border-radius: 2px; text-transform: uppercase; letter-spacing: 0.05em; }`

#### E9 — Empty state for Archive (polish)
Add an Archive section with italic muted text: "No archived projects."

#### E10 — Teaser font size 14px for standard cards
Currently 13px. Bump to 14px for standard (non-hero) cards to match ClawBoi's secondary headline summary size.

---

## Playground Color Audit — 2026-05-10

Studied 4 playground sections to understand how color is used in the established design system, then compared against the overview mock.

### How the playground uses color

#### Generation Status Bar (5.7) — color = state, full commitment

4 states, each a **full opaque background fill** with white text:

| State | Background | CSS variable |
|---|---|---|
| Idle | `#1a6b30` (dark green) | `--status-idle` |
| Active | `#7a5800` (dark amber) | `--status-active` |
| Success | `#1a6b30` (dark green) | `--status-success` |
| Failure | `#C41E3A` (red) | `--status-failure` |

Plus a `gen-shimmer` animation track (2px gradient sweep) on the Active state. Color here is **bold, opaque, full-width** — it IS the bar. No subtlety.

**Principle: when color means "something is happening right now," go full saturation.**

#### Diff Blocks (5.12) — color = semantic operation, subtle + border

| Type | Background | Border-left |
|---|---|---|
| Remove | `rgba(196,30,58,0.05)` — barely visible | `3px solid var(--red)` |
| Add | `rgba(46,125,50,0.06)` — barely visible | `3px solid var(--status-success-bg)` |

Pattern: **ghost background tint + strong left border**. The border does all the work. The background is a whisper. Remove also gets `line-through` + `opacity: 0.65`.

**Principle: left border = semantic meaning, background tint = ambient context.**

#### Overline + Badges (5.16) — color is minimal and earned

- **Overline**: no color — just `var(--ink-muted)` uppercase, 9px, 0.12em letter-spacing. Completely neutral.
- **Count badge**: `background: var(--border)`, `color: var(--ink-light)` — grey, no semantic color. Just a number.
- **NEW badge**: `background: var(--red)`, `color: white` — only badge that uses color, and only because "new" is an attention state.

**Principle: color is earned. Count badges are neutral. Only status-meaning badges get color.**

#### Animations (section) — color maps to state, never to category

| Animation | Color used | Meaning |
|---|---|---|
| `poll-pulse` | `var(--status-running)` green | Active/running |
| `thinking-pulse` | `var(--accent)` blue | Processing/thinking |
| `dot-pulse` | `var(--ink-muted)` grey | Idle/loading |
| `count-pulse` | `var(--border)` bg, `var(--ink)` text | Neutral, no state |
| `status-success-flash` | `var(--status-success)` green | Done |

**Principle: animation color = current state. Never used for category identity.**

---

### The disconnect with our overview mock

The playground uses color for **state** (running / success / failure / idle). The overview mock uses color for **category** (Active / Specced / Ready / Braindumps). These are fundamentally different philosophies.

**Current mock's category color usage:**

| Element | Color source | Problem |
|---|---|---|
| Left border on every card | `--section-color` (green/blue/purple/brown) | Redundant — section header already identifies category |
| Section header title | `--section-color` | Acceptable — quick scan aid, analogous to overline |
| Hero grid top border | `--section-color` | Acceptable — marks the hero region |
| Badge background | `--section-color` | Wrong — badges should use status color (playground) or neutral |

**What the playground would do instead:**
- Cards get left border **only when they have a state**: running = green, error = red, done = green flash
- Cards with no active state: **no color border** — just the grid lines
- Section header title color: keep for scan-ability (low-key, like a colored overline)
- Badges: neutral grey for counts, red only for "NEW", green only for "COMPLETE/DONE"
- Category differentiation comes from **section grouping and position**, not from per-card color

### Color rethink — applied to overview mock

#### Remove
- `border-left: 3px solid var(--section-color)` from all standard grid cards — redundant
- Category-colored badge backgrounds — replace with state-appropriate colors

#### Keep
- Section header title in `--section-color` — subtle, useful for scanning
- Hero grid `border-top: 3px solid var(--section-color)` — marks the hero region
- Status dot animation (green pulse) — state-based, matches playground
- Hero overline in `--section-color` — matches section identity

#### Change badges to state color
- "NEW" → `background: var(--red)` (attention, matches playground)
- "COMPLETE" → `background: var(--status-success-bg)` (done state)
- "READY" → `background: var(--accent)` (info/action state)
- Count badges → `background: var(--border); color: var(--ink-light)` (neutral)

#### Result
Color in the overview now means the same thing as in the playground: **state, not category.** Category is communicated by section grouping + header. State is communicated by card-level color (border, badge, dot).

---

## Playground + UX Audit — Improvement Plan (2026-05-10)

### Problem: grey fill on empty grid space

**Root cause:** `section-group-cards` uses `gap: 1px; background: var(--border)` — a CSS trick that creates hairline separators by showing the container's background through 1px grid gaps. When a section has fewer cards than columns, empty columns fill with grey.

**Sections affected:**
- Ready to build: 1 card → 3 empty grey columns on 1400px viewport
- Specced: 2 cards → 2 empty grey columns
- Braindumps: 4 cards → may fill, depends on viewport width

**Fix applied:** Switched to `column-gap: 24px; row-gap: 0; background: none`. Cards use `border-bottom: 1px solid var(--border)` for separation instead. Empty columns now show page background (`--bg`), not grey. Also added ClawBoi hover bleed: `margin: 0 -8px; padding: 16px 8px` on hover.

**Before → After:**
```
Before:                          After:
┌──────┬──────┬██████┬██████┐   ┌──────┐
│ Card │ Card │ GREY │ GREY │   │ Card │  24px  │ Card │
└──────┴──────┴██████┴██████┘   └──────┘        └──────┘
```

### Playground patterns NOT yet in overview — ranked by value

| Priority | Pattern | Playground § | What it adds |
|---|---|---|---|
| **HIGH** | Button hover fills | 5.11 | `+ New` button: accent border → hover fills with accent bg + white text. More interactive, matches playground. |
| **MEDIUM** | Search count | 5.15 | Show "9 projects" count next to search input — `font-size: 11px; color: var(--ink-muted); text-transform: uppercase`. |
| **MEDIUM** | Update banner | 5.13 | Dark ink-colored banner: "New specs ready — 3 files updated. [Reload]". Could sit between nav and search when updates are available. |
| **LOW** | Context card hover | 5.14 | `border-color: var(--ink); box-shadow: 0 2px 8px rgba(0,0,0,0.06)` — only place shadows are intentional. Could apply to file-item hover for richer feedback. |
| **LOW** | Generation status bar | 5.7 | Full-width bar below nav with shimmer animation. Already have status dot in hero cards — bar would be redundant unless we show global generation state. |
| **N/A** | Diff blocks, modal, toolbar, pullquote, steps, markdown | 5.6–5.12, 5.17 | Not applicable to overview page — these belong in expanded panel / reader. |

### Button hover improvement (applied)

Playground shows `+ New` button hover as: `background: var(--accent); color: var(--bg)` — accent fill replaces transparent. Applied to mock.

### Hover bleed on standard cards (applied)

ClawBoi pattern: at rest, `padding: 16px 0`. On hover, `margin: 0 -8px; padding: 16px 8px; background: rgba(0,0,0,0.02)`. Cards visually expand into surrounding space on hover — satisfying tactile feedback. Applied to mock.

### Remaining improvements (applied 2026-05-10)

All 5 items from the original list have been applied:
1. Search count — "9 projects" label next to search input
2. Generation status bar — replaced update banner with proper 5.7 status bar (4 states)
3. Status dot size — standardized to 7px
4. Featured card distinction — larger title + 3-line teaser (top border removed to reduce line clutter)
5. Archive empty state — "No archived projects. Archive a project →"

---

## Final Mock Summary — `app-overview.html` (2026-05-10)

### What was built

A working HTML mockup at `landing/app-overview.html` that represents the target design for the Specview overview page. Served at `http://localhost:8097/app-overview.html`.

### Design decisions locked in the mock

| Decision | Value | Source |
|---|---|---|
| **Grid system** | `repeat(auto-fill, minmax(280px, 1fr))`, column-gap: 0, no background fill | ClawBoi + grey-space fix |
| **Card separation** | Vertical rules only (`border-right: 1px solid var(--border)`) — no horizontal card borders | Matches hero grid |
| **Card padding** | `20px 24px` all sides | Breathing room, matches hero |
| **Section separation** | `1px solid var(--border)` divider + 24px margin | Rhythm between sections |
| **Section headers** | Colored overline + 2px ink underline spanning title text only + grey count pill | ClawBoi + playground 5.16 |
| **Color philosophy** | State not category. Cards have no color border. Badges use status colors (red=NEW, green=COMPLETE, blue=READY). Section header title stays colored for scan-ability. | Playground audit |
| **Teaser font** | Source Serif 4, 14px | ClawBoi body font |
| **Title font** | Playfair Display, 15px (17px featured, 28px hero) | Existing system |
| **Status bar** | Playground 5.7: idle=#1a6b30, active=#7a5800+shimmer, success=#1a6b30, failure=#C41E3A. White dot, white text, consistent height. | Playground 5.7 |
| **Hover** | Subtle background tint only (`rgba(0,0,0,0.02)`), no margin/padding shift | Simplified from ClawBoi |
| **Badges** | Neutral grey for counts. State-colored for status: `badge--new` (red), `badge--complete` (green), `badge--ready` (accent blue) | Playground 5.16 |
| **Hero grid** | `2fr 1fr 1fr`, gap 24px, Active section only. Vertical rule via `border-left` on secondary cards. | ClawBoi headlines |
| **Nav** | Sticky, 3px ink top border, tab filter with count pill badges. Functional JS filtering. | Existing system |
| **Search** | Input with underline + "9 projects" count label. Functional JS filtering. | Playground 5.15 |
| **Animations** | 7 keyframes available: gen-shimmer, poll-pulse, count-pulse, status-success-flash, rise, dot-pulse, poll-pulse-white | Playground §6 |

### Horizontal lines — final inventory

```
 #  Element                    Weight       Purpose
─── ─────────────────────────  ──────────   ────────────────────────
 1  Nav top                    3px ink      Editorial anchor
 2  Nav bottom                 1px border   Closes nav
 3  Status bar                 solid block  Generation state (not a line)
 4  Search bar bottom          1px border   Closes header zone
 5  Search input underline     1px border   Input affordance
 6  Section header underlines  2px ink ×5   Section identity
 7  Section dividers           1px border   Rhythm between sections
 8  Card vertical rules        1px border   Column separation
```

Removed: hero grid top border, lead card top borders, card bottom borders.

---

## Plan: Apply to Specview App

### Overview — what needs to change in `web-ng/`

The mock validates all design decisions. To apply to the Angular app:

#### Task 1: Grid system (`web-ng/src/styles.css`)

**Current:** `.section-group-cards` uses `gap: 1px; background: var(--border)` (grey fill on empty columns).

**Target:**
```css
.section-group-cards {
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  column-gap: 0;
  row-gap: 0;
  background: none;
}
.section-group-cards .file-item {
  padding: 20px 24px;
  border-right: 1px solid var(--border);
  border-bottom: none;
}
```

#### Task 2: Teaser font (`web-ng/src/styles.css`)

**Current:** `.file-item-teaser` uses `Source Sans 3`, 13px.

**Target:**
```css
.file-item-teaser {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 14px;
}
```

Also add `Source Serif 4` to the Google Fonts import in `index.html`.

#### Task 3: Section headers (`web-ng/src/styles.css`)

**Current:** Full-width `border-bottom: 1px solid var(--border)` on header.

**Target:**
```css
.section-group-header { border-bottom: none; }
.section-group-title {
  display: inline-block;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 4px;
}
```

#### Task 4: Remove card left borders (`web-ng/src/styles.css`)

**Current:** `border-left: 3px solid var(--section-accent)` on every card.

**Target:** Remove. Color = state, not category. Section header color stays.

#### Task 5: Badge system (`web-ng/src/styles.css` + `app.component.html`)

**Current:** No badges on cards.

**Target:** Add grey count pill + status badges to `file-item-meta`:
```css
.badge { background: var(--border); color: var(--ink-light); font-size: 9px; padding: 2px 6px; border-radius: 2px; }
.badge--new { background: var(--red); color: white; }
.badge--complete { background: var(--status-success-bg); color: white; }
```

#### Task 6: Generation status bar (`web-ng/src/styles.css` + `app.component.html`)

**Current:** Uses `--ink` background for all states.

**Target:** Match playground 5.7 colors:
```css
.gen-status-bar--idle    { background: #1a6b30; }
.gen-status-bar--active  { background: #7a5800; }
.gen-status-bar--success { background: #1a6b30; }
.gen-status-bar--failure { background: #C41E3A; }
```
Add shimmer track overlay on active state.

#### Task 7: Hero grid for Active section (`web-ng/src/styles.css` + `app.component.html`)

**Current:** Active section uses same auto-fill grid as other sections.

**Target:** When section is "Active" and has items, use `2fr 1fr 1fr` hero grid. First item gets 28px title, 16px serif teaser, 4-line clamp. Requires template change to add `.hero-grid` class conditionally.

#### Task 8: Featured first card (`web-ng/src/styles.css`)

**Current:** All cards same size.

**Target:**
```css
.section-group-cards .file-item:first-child .file-item-title { font-size: 17px; }
.section-group-cards .file-item:first-child .file-item-teaser { -webkit-line-clamp: 3; }
```

### Execution approach

Create a new braindump project for the Angular implementation — do NOT edit the app code directly from this plan. Run through `/spec-pipeline` → `/impl-guide` → `/exec-guide`.
