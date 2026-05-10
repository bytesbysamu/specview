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
