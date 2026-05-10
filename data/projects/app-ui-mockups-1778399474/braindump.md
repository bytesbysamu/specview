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
