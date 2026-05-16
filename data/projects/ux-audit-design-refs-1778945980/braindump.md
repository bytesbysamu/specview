# UX Audit — Design References Collection

All UX-related documents, design references, and design system files across all projects. Single source of truth for design decisions.

## Design System Core

| File | Lines | What |
|------|-------|------|
| `docs/design-system.md` | — | Canonical newspaper design system (Dieter Rams + editorial layout) |
| `landing/style.css` | 1,224 | Landing page CSS tokens + classes |
| `web-ng/src/styles.css` | 1,769 | App CSS tokens + all component classes |

**Shared design language:** warm off-white bg (#FFFEF9), near-black ink (#121212), muted slate blue accent (#567B95), red (#C41E3A). Typography: Playfair Display (headlines), Source Serif 4 (body), Source Sans 3 (labels/UI). Layout: max-width 1400px, newspaper grid with borders, no shadows, square elements.

## Executed UX Epics (8 projects)

| Project | What | Exec summary |
|---------|------|-------------|
| `ux-grid-polish-1778368175` | Grid layout polish | ✓ done |
| `ux-landing-grid-polish-1778450371` | Landing + grid polish | ✓ done |
| `ux-polish-newspaper-1778238000` | Newspaper design pass | ✓ done |
| `ux-reader-textops-1778237000` | Reader panel + text ops | ✓ done |
| `landing-phase3-polish-1778355280` | Landing page phase 3 | ✓ done |
| `playground-design-system-1778915990` | Design system in playground | ✓ done |
| `playground-phase2-missing-sections-1778919412` | 12 remaining demos | ✓ done |
| `live-component-playground-1778879053` | Live interactive playground | ✓ done |

## Design Reference PDFs

| File | Location |
|------|----------|
| Groad Food Ordering UI/UX Case Study (Behance) | `docs/design-references/Groad - Food Ordering System - UI_UX Case Study __ Behance.pdf` |

## Landing Page HTML Files

| File | What |
|------|------|
| `landing/index.html` | Main landing page |
| `landing/landing-v2.html` | V2 polished version |
| `landing/app-overview.html` | App overview page |
| `landing/wireframe.html` | Static wireframe |
| `landing/playground.html` | Original static design playground (2,304 lines) |
| `landing/specview-landing-wireframe.jsx` | JSX wireframe component |

## Sibling Project Design Docs

| File | What |
|------|------|
| `clawboi/docs/design-system.md` | ClawBoi design system (same tokens as specview) |
| `constellation/backend/docs/docs/colors-and-themes.md` | Ionic theming (light/dark, CSS custom properties) |
| `constellation/cbtBuddy/docs/CBT_Buddy_Comprehensive_UX_UI_Plan.md` | CBT app UX/UI plan |
| `constellation/cbtBuddy/docs/UI_Mockups_Professional_Design.md` | CBT professional mockups |
| `constellation/cbtBuddy/docs/chat-ui-implementation.md` | Chat UI implementation guide |

## Ionic UI References

| Directory | What |
|-----------|------|
| `ionic/UI-Challenges/ionic-restrant-app/` | Restaurant app (Ionic 5 + Angular 9, food SVGs) |
| `ionic/UI-Challenges/ionic-car-rental/` | Car rental app |
| `ionic/UI-Challenges/ionic-flowers-store/` | Flowers store app |
| `ionic/UI-Challenges/ionic-movies/` | Movies app |
| `ionic/UI-Challenges/ionic-pokedex/` | Pokedex app |
| `ionic/UI-Challenges/ionic-project-management/` | Project management app |
| `ionic/Ionic-UI-Templates/` | Reusable UI component templates |

## Design Assets

| File | What |
|------|------|
| `templates/able-pro-v9.fig` | Able Pro Figma template |
| `ionic/templates/conference-app/resources/icon.psd` | PSD icon file |

## Products using the newspaper design system
1. Specview — landing page + app
2. ClawBoi — dashboard
3. Constellation CBTBuddy — mobile/web (extends with Ionic theming)

## How this connects to the playground

The live playground at `/playground` is the interactive version of this audit. It renders real components with the design tokens documented here. The playground's sections (tokens, borders, animations, state matrix, component demos) are derived from the same source files listed above.

Future: the playground can reference this audit to add demos for cross-product patterns (Ionic theming from Constellation, food ordering UI patterns from Groad, etc.).

---

# Playground 2.0 — Specview Case Study (Groad-style)

## The idea

The Groad PDF tells a food ordering app's story in 12 pages: problem → design process → branding → journey map → user flow → screens → patterns. We do the same for Specview — a live, scrollable case study at `/playground` that tells the product's story using real Angular components. Not a component reference (that's Phase 1/2), but a narrative walkthrough.

## Source material

### Active inputs (7 files from UX audit)
- `groad-analysis.md` — the narrative structure template
- `design-system.md` — newspaper design philosophy + tokens
- `static-playground-original.html` — 2,304 lines of component demos + CSS snippets
- `landing-v2.html` — polished landing page (hero, stats, steps, pull quote)
- `landing-index.html` — original landing for comparison
- `specview-landing-wireframe.jsx` — wireframe showing layout decisions
- `clawboi-design-system.md` — heritage story (ClawBoi → Specview)

### Reference (inform decisions, don't appear directly)
- `constellation-colors-themes.md` — Ionic dark/light theming patterns
- `cbtbuddy-ux-plan.md` — UX planning methodology
- `cbtbuddy-ui-mockups.md` — professional mockup approach

## The Groad-to-Specview mapping

| Groad | Specview |
|-------|---------|
| Hero: "Food Delivery App" | Hero: "Write messy. Ship clean." |
| Problem statement | Why braindumps → engineering docs matters |
| Design process (5 stages) | Pipeline: braindump → analysis → epic → architecture → impl guide |
| Branding (logo, colors, type) | Newspaper aesthetic: Playfair Display, warm cream, muted blue, borders not shadows |
| User interview / goals | Solo dev needs: think before code, automated specs |
| Journey map | Paste braindump → watch generation → read specs → iterate with AI ops |
| User flow diagram | Anonymous → playground → signup → create → generate → read → share |
| Onboarding screens | Landing pitch → "Try it free" → first braindump |
| Discovery & browse | Project grid with taxonomy (Active, Ready to build, Specced, Braindumps) |
| Restaurant detail | Expanded reader: sidebar file nav + newspaper 2-column markdown |
| Cart & payment | Billing: free tier → upgrade → Stripe checkout → Pro |
| Order tracking | Spec gen: status bar → step progress → file-by-file incremental save |
| Rating/review | AI text ops: brainstorm, expand, compress, diff view, apply/dismiss |
| Driver interface (dark) | Dark mode toggle across all components |
| Design patterns summary | Border system, animations, component state matrix |

## The narrative sections (scrollable page)

### 1. Hero
"Write messy. Ship clean." with a live generation demo running in the background — the status bar animating, files appearing one by one. The visitor sees the product working before reading a word.

### 2. The Problem
Why spec generation exists. Before/after: a messy braindump on the left, five structured documents on the right. The transformation IS the value prop.

### 3. The Pipeline
Five steps visualized as a horizontal flow: braindump → analysis → epic → architecture → implementation guide. Each step is a live component showing its output. Click a step, see the document.

### 4. Design Language
The newspaper aesthetic origin story. How Dieter Rams minimalism + editorial layout became the product's identity. Live token swatches that flip with dark mode. Typography specimens. Border catalog. "We use borders, not shadows. We use ink, not color."

### 5. The Journey
User flow from anonymous to power user: land on page → see the pitch → try the playground → sign up → create first project → generate specs → read in newspaper layout → iterate with AI ops → upgrade to Pro → share specs publicly.

### 6. Screen Gallery
Every major screen rendered as a live component, not a screenshot:
- Landing pitch (the marketing page)
- Project grid (newspaper-style with section grouping)
- Expanded reader (sidebar + 2-column markdown)
- Status bar in all 4 states
- AI ops: brainstorm result, diff view, follow-up input
- Create modal with form
- Billing: upgrade page, usage meter

### 7. Design Patterns
Already built in Phase 1/2 — borders, animations, state matrix, interaction states. This section exists, just needs the narrative wrapper.

### 8. Dark Mode
Full-page toggle. Every section flips simultaneously. A token diff table shows --ink: #121212 → #E8E6E0 etc.

### 9. Heritage
ClawBoi → Specview evolution. The newspaper grid, the editorial voice, the Playfair Display headlines — where they came from and why they stayed.

## What already exists vs what's new

| Section | Status |
|---------|--------|
| 1. Hero | Exists (landing-pitch component) — needs narrative context |
| 2. The Problem | NEW — text + before/after layout |
| 3. The Pipeline | NEW — horizontal step flow with live docs |
| 4. Design Language | Exists (pg-tokens, pg-borders) — needs narrative wrapper |
| 5. The Journey | NEW — user flow diagram |
| 6. Screen Gallery | Exists (Sections 1-5 of playground) — needs narrative labels |
| 7. Design Patterns | Exists (Sections A-D) — needs narrative wrapper |
| 8. Dark Mode | Exists (Section 6) — needs token diff table |
| 9. Heritage | NEW — ClawBoi origin story |

4 new sections, 5 existing sections wrapped with narrative.

## Success criteria
- Scrollable case study at `/playground` that tells the Specview story
- Every Groad section has a Specview equivalent
- All components are live (not screenshots)
- A visitor who reads top to bottom understands what Specview does, how it's built, and why it looks the way it does
- Dark mode works across the entire narrative

---

## Source collection

All source files are collected in the UX audit project: `ux-audit-design-refs-1778945980` (23 files). That project is the archive — this braindump references it, doesn't duplicate it.

### Active inputs → use directly
- `ux-audit.../groad-analysis.md` — narrative template
- `ux-audit.../design-system.md` — design philosophy + tokens
- `ux-audit.../static-playground-original.html` — component demos + CSS snippets
- `ux-audit.../landing-v2.html` — polished landing page
- `ux-audit.../landing-index.html` — original landing
- `ux-audit.../specview-landing-wireframe.jsx` — wireframe
- `ux-audit.../clawboi-design-system.md` — heritage story

### Archived (reference only, stay in UX audit project)
- `ux-audit.../constellation-colors-themes.md` — Ionic theming (dark mode inspiration)
- `ux-audit.../cbtbuddy-ux-plan.md` — UX methodology reference
- `ux-audit.../cbtbuddy-ui-mockups.md` — mockup patterns reference
- `ux-audit.../cbtbuddy-chat-ui.md` — chat UI reference
- `ux-audit.../wireframe.html` — early wireframe (before/after)
- `ux-audit.../app-overview.html` — app overview structure
- 6 exec-summary files — completed work, historical
- 2 braindump files — executed, historical

---

## Groad → Specview Cross-Reference Analysis

Source: Groad Food Ordering UI/UX Case Study (Behance, 12 pages, PDF at docs/design-references/)
Cross-referenced with: design-system.md, clawboi-design-system.md, landing-v2.html, static-playground-original.html, specview-landing-wireframe.jsx

---

## 1. How Groad tells its story (the template)

Groad follows a classic Behance case study arc:

1. **Hero** — product name + tagline + hero screenshot
2. **Problem** — one paragraph framing the need
3. **Process** — 5-stage design process (Understand → Research → Sketch → Design → Implement → Evaluate)
4. **Branding** — logo grid + color palette + type specimen
5. **Research** — user interview goals (project goals vs user goals), target user persona
6. **Journey map** — horizontal timeline: trigger → browsing → ordering → waiting → delivery → follow-up
7. **User flow** — branching diagram: Discovery & Choose → Pay → Verify
8. **Screen gallery** — every major screen with annotation labels
9. **Patterns** — UI themes (light/dark), infinite scroll, payment methods
10. **Closing** — logo + follow button

**Key insight:** Groad doesn't just show screens — it explains WHY each screen exists by linking it back to the journey map. Every screen is a station on the user's path.

---

## 2. What Specview already has (from our collected files)

### From landing-v2.html
- Hero: "Write messy. Ship clean." + file generation aside showing analysis.md, epic.md generating in real time
- Stat strip: 44.5s avg generation, 5 files per run, 0 human code lines, Free to start
- "What ships" section with 5-file breakdown
- "See it" section (live demo placeholder)
- Pull quote: "I wrote 3 paragraphs. 47 seconds later I had an analysis, an epic, and an architecture doc."
- Steps: Braindump → Generate → Read & Build

### From design-system.md (the philosophy)
- Dieter Rams minimalism + editorial newspaper layout
- "Information density without clutter"
- "Typography does the heavy lifting — no decorative UI chrome"
- "Borders and whitespace as structure, not decoration"
- "Ink on paper: cream background, near-black ink, no shadows"
- "Interaction is quiet — hover states are barely-there"

### From clawboi-design-system.md (the heritage)
- Identical tokens to specview — shared lineage
- ClawBoi dashboard was the first implementation
- Newspaper grid, editorial voice, Playfair Display headlines originated here
- Specview inherited and extended the system

### From static-playground-original.html (2,304 lines)
- Complete component catalog: 17 subsections
- CSS code snippets for every component
- "App vs Landing" comparison table
- "ClawBoi Origin vs Specview" heritage table
- Live animation demos with Replay buttons
- Every component in every state

### From specview-landing-wireframe.jsx
- Section-based scroll architecture
- Sticky header with progress
- 6 sections: hero, what, how, see-it, pricing, footer

---

## 3. Groad vs Specview — Design language contrast

| Aspect | Groad | Specview |
|--------|-------|---------|
| **Philosophy** | Friendly, approachable, food = comfort | Editorial, authoritative, newspaper = trust |
| **Corners** | Rounded (16px radius) | Sharp (0-2px radius) |
| **Elevation** | Card shadows throughout | Borders only, zero shadows (except modal intentionally) |
| **Color strategy** | Warm coral accent (#FF6B6B), multi-color payment cards | Muted slate blue (#567B95), monochrome with red for alerts |
| **Typography** | SF Pro Text (single family, 3 weights) | 3-font stack: Playfair Display, Source Serif 4, Source Sans 3 |
| **Layout** | Card grid with generous padding | Newspaper grid with hairline borders as dividers |
| **Nav pattern** | Bottom tab bar (mobile-first) | Section pill bar with count badges (desktop-first) |
| **Onboarding** | Illustration-heavy (3 splash screens) | Content-first (landing pitch IS the onboarding) |
| **Dark mode** | Driver dashboard only | Full-page toggle, every component flips |
| **Empty states** | Illustrations + friendly copy | Minimal text only |
| **Status indicators** | Color-coded dots + progress bars | 4-state status bar with CSS animation |
| **Data density** | Low — generous whitespace, one action per screen | High — newspaper column layout, multi-file sidebar, metadata overlines |

---

## 4. What to steal from Groad (adapt to newspaper aesthetic)

### Narrative structure ✅ steal
Groad's problem → process → branding → journey → screens arc is universal. Specview's playground should follow the same narrative flow, just with newspaper styling instead of card-based mobile UI.

### Journey map ✅ steal
Groad's horizontal timeline (trigger → browsing → ordering → waiting → delivery) maps directly to Specview's pipeline (braindump → analysis → epic → architecture → impl guide). Visualize this as a horizontal newspaper-style timeline.

### Before/after transformation ✅ steal
Groad shows raw ingredients → finished dish. Specview shows messy braindump → structured documents. The transformation IS the value prop. Show it explicitly.

### Screen annotation pattern ✅ steal
Groad labels every screen with what it does and why. The playground's screen gallery should annotate each component: "This is the reader panel — it renders specs in a 2-column newspaper layout because information density matters for engineers reading technical docs."

### Process visualization ✅ steal
Groad's 5-stage process bar is clean and scannable. Specview's 5-step pipeline (braindump → analysis → epic → architecture → impl guide) should be visualized the same way — horizontal, with icons, clickable.

### Design token showcase ✅ already built
Groad shows its color palette and type specimens. Our pg-tokens component already does this — just needs narrative context.

### User goals framing ✅ steal
Groad splits into "Project Goals" and "User Goals." For Specview:
- **Product goal:** Generate structured engineering docs from unstructured input
- **User goal:** Think before coding without the friction of writing formal documents

---

## 5. What NOT to steal from Groad

### Mobile-first patterns ❌
Bottom nav bar, full-screen modals, swipe gestures — Specview is desktop-first. Keep the section nav bar, modal overlays, and click interactions.

### Illustration-heavy onboarding ❌
Groad uses 3 splash screens with custom illustrations. Specview's landing pitch IS the onboarding — the product demonstrates itself. No illustrations needed.

### Rounded corners ❌
Sharp corners are a core design principle. "No radius" is part of the newspaper identity.

### Shadow elevation ❌
"Borders and whitespace as structure, not decoration." The modal's intentional shadow is the only exception.

### Warm/friendly tone ❌
Groad is comfort food. Specview is a broadsheet newspaper. The editorial voice stays.

---

## 6. The narrative arc for Playground 2.0

Combining Groad's structure with Specview's design language:

### Act 1: The Hook (above the fold)
**Groad equivalent:** Hero + problem statement
**Specview:** "Write messy. Ship clean." + live generation demo running in background. Stat strip: 44.5s / 5 files / 0 code / Free.

### Act 2: The Method (how it works)
**Groad equivalent:** Design process + branding
**Specview:** The 5-step pipeline visualized as a horizontal newspaper-style flow. Each step is clickable — shows the actual document. Below: the design language section (tokens, typography, borders) with the philosophy quote.

### Act 3: The Journey (user flow)
**Groad equivalent:** Journey map + user flow diagram
**Specview:** The path from anonymous visitor to power user. Land → try playground → sign up → create project → generate → read → iterate → upgrade → share. Each station is a mini-demo.

### Act 4: The Product (screen gallery)
**Groad equivalent:** All screens annotated
**Specview:** Every major screen as a live component with editorial annotation. Project grid, expanded reader, status bar states, AI ops, billing flow. "This is the reader panel — it uses a 2-column newspaper layout because..."

### Act 5: The System (design patterns)
**Groad equivalent:** UI themes + patterns summary
**Specview:** Border catalog, animation gallery, state matrix, dark mode toggle. Already built — just needs the narrative wrapper.

### Act 6: The Heritage (where it came from)
**Groad equivalent:** (doesn't have this — we add it)
**Specview:** ClawBoi → Specview evolution. The newspaper grid's origin. Why Playfair Display. Why no shadows. The design system as a living document.

---

## Newspaper Design System (canonical reference)

> Canonical reference for the shared aesthetic across ClawBoi dashboard and Specview landing.
> Preserve and extend from this. Do not drift from these tokens without updating this doc.

---

## Philosophy

**Dieter Rams minimalism + editorial newspaper layout.**

- Information density without clutter
- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace as structure, not decoration
- Ink on paper: cream background, near-black ink, no shadows
- Interaction is quiet — hover states are barely-there, not flashy

---

## Design Tokens

These are identical across ClawBoi and Specview landing. Single source of truth.

### Colors

```css
/* Light mode */
--bg:          #FFFEF9   /* warm off-white, not pure white */
--ink:         #121212   /* near-black, not pure black */
--ink-light:   #5A5A5A   /* secondary text */
--ink-muted:   #999999   /* labels, meta, timestamps */
--border:      #DFDFDF   /* light rule lines */
--border-dark: #121212   /* thick section breaks */
--accent:      #567B95   /* muted slate blue — used sparingly */
--red:         #C41E3A   /* overline labels, badges, alerts */

/* Dark mode */
--bg:          #141414
--ink:         #E8E6E0
--ink-light:   #A0A0A0
--ink-muted:   #606060
--border:      #2E2E2E
--border-dark: #E8E6E0
--accent:      #7BAFC8
--red:         #E05A72
```

### Typography

Three-font stack — each with a clear role:

| Variable | Font | Role |
|----------|------|------|
| `--serif` | Playfair Display | Headlines, titles, pull quotes, numbers |
| `--body`  | Source Serif 4   | Body copy, paragraphs, reading text |
| `--sans`  | Source Sans 3    | Labels, metadata, UI chrome, uppercase tags |

**Rules:**
- Playfair = signal. Use for things that should feel editorial/important.
- Source Serif = reading. Body text, multi-sentence content.
- Source Sans = function. Anything small, uppercase, spaced, or UI-adjacent.
- Never use system fonts for visible content — always assign explicitly.

### Type Scale

```
Masthead title:   56–64px  Playfair 700, tracking -0.02em
Hero headline:    44px     Playfair 700, tracking -0.01em
Section title:    28–36px  Playfair 700
Card title:       18–22px  Playfair 700
Body:             15–17px  Source Serif, line-height 1.65–1.75
Label:            11–12px  Source Sans 600, uppercase, tracking 0.08–0.12em
Meta/muted:       11px     Source Sans 400, tracking 0.04–0.06em
```

---

## Layout System

### Container

```css
.page {
  max-width: 1400px;
  margin: 0 auto;
}
```
- ClawBoi: `padding: 20px 40px`
- Specview landing: no padding on `.page`, padding lives on each section

### Grid Patterns

**Masthead** — 3-column grid, forces perfect title centering:
```css
grid-template-columns: 150px 1fr 150px;
align-items: flex-end; /* bottom-align for editorial feel */
```

**Newspaper column grid** (ClawBoi memory items):
```css
grid-template-columns: repeat(3, 1fr);
/* columns separated by border-right: 1px solid var(--border) */
```

**Hero/Lede** (Specview landing — two-column only):
```css
/* .lede — always two-column: main | 1px divider | aside */
grid-template-columns: 1fr 1px 340px;
/* Children: .lede-main (padding-right: 40px) + .lede-divider + .lede-aside (padding-left: 40px) */
/* min-height: calc(100vh - 100px); align-items: center */
```

**Single-column hero** — no class exists for this. Use a plain `<section>` and place
`.overline` + `.headline` + `.deck` + `.cta-row` directly inside. Do NOT use `.lede`
with only `.lede-main` — it will leave the right 40% of the grid empty.

**Output cards** (Specview landing):
```css
grid-template-columns: repeat(4, 1fr);
/* each card: border-right, last has none */
```

**Lead + sidebar** (ClawBoi):
```css
grid-template-columns: 1fr 300px;
```

### Spacing

- Section padding: `40px` horizontal, `32–40px` vertical
- Component padding: `24–32px`
- Dense lists: `10–12px` vertical padding per item
- Gap between grid columns: `0` (borders do the work) or `24–32px`

---

## Border System

The entire visual hierarchy is built on borders, not cards or shadows.

| Use | Rule |
|-----|------|
| Masthead bottom | `1px solid var(--border)` |
| Section nameplate break | `3px solid var(--ink)` (top of section-bar) |
| Between sections | `1px solid var(--border)` |
| Footer top | `3px solid var(--ink)` |
| Widget title underline | `2px solid var(--ink)` |
| Column dividers | `1px solid var(--border)` (border-right on grid children) |
| Expanded panel top | `3px solid var(--ink)` |
| `<hr>` thick | `3px solid var(--border-dark)` |

**Rule:** 3px ink = major structural break. 2px ink = section label underline. 1px border = content divider.

---

## Component Inventory

### Masthead

Both products share this structure:

```
[ Edition/label ]  [ Date / TITLE / Tagline ]  [ Actions ]
                      grid: 150px 1fr 150px
```

- Edition: 11px Source Sans, uppercase, `var(--ink-muted)`
- Date: 11–12px Source Sans, uppercase, `var(--ink-light)`
- Title: 56–64px Playfair 700, tracking -0.02em
- Tagline: 12–13px Source Sans, **italic** (not uppercase)
- Theme toggle: `border: 1px solid var(--border)`, square (no border-radius)

### Section Navigation Bar

```css
display: flex;
justify-content: center;          /* centered, newspaper-authentic */
border-top: 3px solid var(--ink); /* nameplate rule above */
border-bottom: 1px solid var(--border);
```

Links: 11px Source Sans 600, uppercase, tracking 0.08em, `border-right: 1px solid var(--border)` between items.

### Section Heading Label

```css
font: 11px/700 Source Sans, uppercase, tracking 0.12em
padding: 12px 40px
border-bottom: 1px solid var(--border)
```

Used as a full-width label strip before content sections.

### Widget Title (ClawBoi sidebar)

```css
font: 11px/600 Source Sans, uppercase, tracking 0.1em
color: var(--ink-muted)
border-bottom: 2px solid var(--ink)  /* the underline rule */
padding-bottom: 6px
```

### Overline / Badge

```css
/* Overline (Specview) */
font: 11px/600 Source Sans, uppercase, tracking 0.12em
color: var(--red)
display: block
margin-bottom: 14px

/* Badge (ClawBoi badge-new) */
background: var(--red)
color: white
font: 9px/600 Source Sans, uppercase, tracking 0.05em
padding: 2px 6px
border-radius: 2px
```

### Hover State (universal)

```css
transition: background 0.15s;

:hover {
  background: rgba(0,0,0,0.02);   /* light mode */
}

[data-theme="dark"] :hover {
  background: rgba(255,255,255,0.03);
}
```
Used on: memory items, output cards, steps, headline items. Never a border change or scale — just a whisper of background.

### Pull Quote

```css
/* ClawBoi — centered, full-width */
text-align: center;
padding: 32px 60px;
/* decorative " via ::before — 72px Playfair, color: var(--border) */

.pull-quote-text: 24px Playfair italic, line-height 1.4

/* Specview — two variants, both use .pullquote-row as base */

/* Two-column (2 quotes side by side): */
<section class="pullquote-row">

/* Single centered quote: MUST use BOTH classes */
<section class="pullquote-row pullquote-single">
/* .pullquote-single overrides the grid to a centered single column */
/* Using .pullquote-row alone with one quote leaves the right column empty */

/* Inner structure (same for both variants): */
.pullquote-mark: 56px Playfair 700, color: var(--border)
.pullquote-text: 22px Playfair italic
.pullquote-attr: 11px Source Sans uppercase, var(--ink-muted)
```

### Expanded Panel (ClawBoi only)

Frameless inline expansion — inserts into page flow, not a modal:
```css
border-top: 3px solid var(--ink);
border-bottom: 1px solid var(--border);
padding: 40px 0;

.expanded-title: 36px Playfair, max-width 900px
.expanded-body: 16px Source Serif, line-height 1.8
                column-count: 2; column-gap: 48px;
                column-rule: 1px solid var(--border);
```

Close button: `×` character, 32px, `color: var(--ink-muted)`, no border.

### Chat Panel (ClawBoi only)

Fixed bottom-right floating panel:
- Mode toggle: ⚡ Haiku (fast) / 🦁 Sonnet (full context)
- Input: `→` send button (arrow character)
- Not a modal — overlaps page, dismissable

### 2-Column Body Text (ClawBoi)

Used in lead story and expanded panel:
```css
column-count: 2;
column-gap: 32–48px;
column-rule: 1px solid var(--border);
```
Authentic newspaper column layout for long-form content.

### Section Heading Label vs. Overline — Critical Distinction

These are two different things. Do not confuse them.

| Class | Font | Role | Placement |
|-------|------|------|-----------|
| `.section-heading` | 11px Source Sans, uppercase | Full-width structural divider bar between sections | Block-level, outside `<section>` |
| `.overline` | 11px Source Sans, uppercase, `color: var(--red)` | Editorial opener inside a section, above the headline | Inside `<section>`, before `<h2 class="headline">` |

Correct pattern:
```html
<div class="section-heading" id="how">How it works</div>
<section>
  <span class="overline">The Methodology</span>
  <h2 class="headline">...</h2>
```

### Demo Strip (Specview landing)

Miniaturized newspaper layout used as a live product preview. Exact nesting is required —
skipping any wrapper breaks the CSS grid layout.

```html
<div class="demo-strip">
  <div class="demo-strip-inner">                          <!-- required wrapper -->
    <div class="demo-masthead">                           <!-- newspaper nameplate -->
      <div class="demo-title">Project Spec</div>
      <div class="demo-tagline">...</div>
    </div>
    <div class="demo-body">                               <!-- 3-col grid: 200px 1px 1fr -->
      <div class="demo-sidebar">
        <div class="demo-sidebar-label">Artifacts</div>
        <div class="demo-sidebar-item">analysis</div>
        <div class="demo-sidebar-item active">architecture</div>
        <!-- etc. -->
      </div>
      <div class="demo-sidebar-divider"></div>            <!-- 1px column rule -->
      <div class="demo-content">
        <span class="demo-tag">architecture</span>
        <h3>...</h3>
        <p>...</p>
      </div>
    </div>
  </div>
</div>
```

**Nesting rule:** `.demo-strip` → `.demo-strip-inner` → `.demo-masthead` + `.demo-body` → `.demo-sidebar` + `.demo-sidebar-divider` + `.demo-content`. No shortcuts.

### Step Numbers (Specview landing)

```css
font: 64px/1 Playfair 700
color: var(--border)  /* intentionally faint — decorative, not informational */
```

### Code/Terminal Blocks (Specview landing)

```css
font-family: 'SF Mono', Consolas, monospace;
font-size: 12px;
background: var(--border);
border-left: 3px solid var(--ink-muted);
padding: 10px 14px;
```

### Mood Chart (ClawBoi only)

Bar chart of historical moods:
```css
display: flex; align-items: flex-end; gap: 4px; height: 60px;
/* bars: var(--mood-10) #2E7D32 → var(--mood-0) #C62828 */
/* tooltip via ::after on hover */
```

### Person/Tag Pills (ClawBoi sidebar)

```css
font: 12px Source Sans
padding: 4px 10px
border: 1px solid var(--border)
border-radius: 2px   /* only place radius appears */
background: var(--bg)
```

### Markdown Headings (ClawBoi expanded content)

```css
h1: 24px Playfair 700
h2: 20px Playfair 700
h3: 13px Source Sans 600, uppercase, tracking 0.05em, color: var(--ink-light)
```
H3 deliberately uses sans — signals a sub-label, not a headline.

---

## Interaction Principles

1. **No shadows** — depth comes from borders and typography size, not elevation
2. **No border-radius on structural elements** — buttons, inputs, panels are square
3. **2px radius only on pill tags** — the one exception, for inline labels
4. **Transitions: 0.15s max** — subtle, never animated
5. **Hover = `rgba` fill** — never a border change, color change, or movement
6. **Close/dismiss = `×` character** — not an icon, 28–32px, weight 300
7. **Theme toggle = icon in button** — square border, no background fill

---

## Specview Landing vs ClawBoi — Where They Differ

| Aspect | ClawBoi | Specview Landing |
|--------|---------|-----------------|
| Purpose | Live app dashboard | Static marketing page |
| Container | `max-width: 1400px` `.page` wrapper | Same, added 2026-05 |
| Masthead border | `1px solid var(--border)` | `1px solid var(--border)` (aligned 2026-05) |
| Nameplate rule | `div.divider.thick` below nav | `border-top: 3px` on `.section-bar` |
| Tagline | Italic | Italic (aligned 2026-05) |
| Section nav | Centered | Centered (aligned 2026-05) |
| Content | Dynamic JS-rendered data | Static HTML |
| Chat panel | Floating bottom-right | Not present |
| 2-col body text | Yes (lead + expanded) | Not present |
| Expanded panel | Inline frameless | Not present |
| Icons | Emoji (chat mode toggles) | Inline SVGs (Lucide CDN removed 2026-05) |

---

## Do Not

- Do not use `box-shadow` anywhere
- Do not add border-radius to cards, buttons, or panels
- Do not use color for hierarchy — use font-weight and font-size
- Do not use `--accent` (#567B95) heavily — it is a one-off highlight color
- Do not replace `--red` with a softer color — it is intentional for overlines/badges
- Do not change the font stack — all three fonts are load-bearing
- Do not use `font-weight: 400` for Playfair headlines — always 700
- Do not animate layout — transitions on `background` only

---

## Enhancements to Consider

- **2-column body text** in Specview landing lede (matches ClawBoi lead-body)
- **`section-badge`** count pattern on section headings (ClawBoi: gray pill `border-radius: 2px`)
- **Inline expansion** pattern for output cards (click → expand in place, no modal)
- **Time-labeled grids** ("This Week" / "Earlier") for any chronological content
- **Inline SVG set** — create a shared SVG sprite or include file so icons don't need to be copy-pasted per page (currently duplicated across `index.html`, `playground.html`, `landing-v2.html`)
- **Single-column hero class** — `.lede` is two-column only; a `.hero` or `.lede--full` variant would be a genuine design system addition when needed

---

*Snapshot taken: 2026-05-07. Last updated: 2026-05-09 — landing-v2 audit: Lucide CDN removed, pullquote-single variant documented, demo strip nesting documented, single-column hero gap noted, overline vs. section-heading distinction added.*

---

## ClawBoi Design System (heritage)

> Canonical reference for the shared aesthetic across ClawBoi dashboard and Specview landing.
> Preserve and extend from this. Do not drift from these tokens without updating this doc.

---

## Philosophy

**Dieter Rams minimalism + editorial newspaper layout.**

- Information density without clutter
- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace as structure, not decoration
- Ink on paper: cream background, near-black ink, no shadows
- Interaction is quiet — hover states are barely-there, not flashy

---

## Design Tokens

These are identical across ClawBoi and Specview landing. Single source of truth.

### Colors

```css
/* Light mode */
--bg:          #FFFEF9   /* warm off-white, not pure white */
--ink:         #121212   /* near-black, not pure black */
--ink-light:   #5A5A5A   /* secondary text */
--ink-muted:   #999999   /* labels, meta, timestamps */
--border:      #DFDFDF   /* light rule lines */
--border-dark: #121212   /* thick section breaks */
--accent:      #567B95   /* muted slate blue — used sparingly */
--red:         #C41E3A   /* overline labels, badges, alerts */

/* Dark mode */
--bg:          #141414
--ink:         #E8E6E0
--ink-light:   #A0A0A0
--ink-muted:   #606060
--border:      #2E2E2E
--border-dark: #E8E6E0
--accent:      #7BAFC8
--red:         #E05A72
```

### Typography

Three-font stack — each with a clear role:

| Variable | Font | Role |
|----------|------|------|
| `--serif` | Playfair Display | Headlines, titles, pull quotes, numbers |
| `--body`  | Source Serif 4   | Body copy, paragraphs, reading text |
| `--sans`  | Source Sans 3    | Labels, metadata, UI chrome, uppercase tags |

**Rules:**
- Playfair = signal. Use for things that should feel editorial/important.
- Source Serif = reading. Body text, multi-sentence content.
- Source Sans = function. Anything small, uppercase, spaced, or UI-adjacent.
- Never use system fonts for visible content — always assign explicitly.

### Type Scale

```
Masthead title:   56–64px  Playfair 700, tracking -0.02em
Hero headline:    44px     Playfair 700, tracking -0.01em
Section title:    28–36px  Playfair 700
Card title:       18–22px  Playfair 700
Body:             15–17px  Source Serif, line-height 1.65–1.75
Label:            11–12px  Source Sans 600, uppercase, tracking 0.08–0.12em
Meta/muted:       11px     Source Sans 400, tracking 0.04–0.06em
```

---

## Layout System

### Container

```css
.page {
  max-width: 1400px;
  margin: 0 auto;
}
```
- ClawBoi: `padding: 20px 40px`
- Specview landing: no padding on `.page`, padding lives on each section

### Grid Patterns

**Masthead** — 3-column grid, forces perfect title centering:
```css
grid-template-columns: 150px 1fr 150px;
align-items: flex-end; /* bottom-align for editorial feel */
```

**Newspaper column grid** (ClawBoi memory items):
```css
grid-template-columns: repeat(3, 1fr);
/* columns separated by border-right: 1px solid var(--border) */
```

**Hero/Lede** (Specview landing):
```css
grid-template-columns: 1fr 1px 340px; /* main | divider | aside */
```

**Output cards** (Specview landing):
```css
grid-template-columns: repeat(4, 1fr);
/* each card: border-right, last has none */
```

**Lead + sidebar** (ClawBoi):
```css
grid-template-columns: 1fr 300px;
```

### Spacing

- Section padding: `40px` horizontal, `32–40px` vertical
- Component padding: `24–32px`
- Dense lists: `10–12px` vertical padding per item
- Gap between grid columns: `0` (borders do the work) or `24–32px`

---

## Border System

The entire visual hierarchy is built on borders, not cards or shadows.

| Use | Rule |
|-----|------|
| Masthead bottom | `1px solid var(--border)` |
| Section nameplate break | `3px solid var(--ink)` (top of section-bar) |
| Between sections | `1px solid var(--border)` |
| Footer top | `3px solid var(--ink)` |
| Widget title underline | `2px solid var(--ink)` |
| Column dividers | `1px solid var(--border)` (border-right on grid children) |
| Expanded panel top | `3px solid var(--ink)` |
| `<hr>` thick | `3px solid var(--border-dark)` |

**Rule:** 3px ink = major structural break. 2px ink = section label underline. 1px border = content divider.

---

## Component Inventory

### Masthead

Both products share this structure:

```
[ Edition/label ]  [ Date / TITLE / Tagline ]  [ Actions ]
                      grid: 150px 1fr 150px
```

- Edition: 11px Source Sans, uppercase, `var(--ink-muted)`
- Date: 11–12px Source Sans, uppercase, `var(--ink-light)`
- Title: 56–64px Playfair 700, tracking -0.02em
- Tagline: 12–13px Source Sans, **italic** (not uppercase)
- Theme toggle: `border: 1px solid var(--border)`, square (no border-radius)

### Section Navigation Bar

```css
display: flex;
justify-content: center;          /* centered, newspaper-authentic */
border-top: 3px solid var(--ink); /* nameplate rule above */
border-bottom: 1px solid var(--border);
```

Links: 11px Source Sans 600, uppercase, tracking 0.08em, `border-right: 1px solid var(--border)` between items.

### Section Heading Label

```css
font: 11px/700 Source Sans, uppercase, tracking 0.12em
padding: 12px 40px
border-bottom: 1px solid var(--border)
```

Used as a full-width label strip before content sections.

### Widget Title (ClawBoi sidebar)

```css
font: 11px/600 Source Sans, uppercase, tracking 0.1em
color: var(--ink-muted)
border-bottom: 2px solid var(--ink)  /* the underline rule */
padding-bottom: 6px
```

### Overline / Badge

```css
/* Overline (Specview) */
font: 11px/600 Source Sans, uppercase, tracking 0.12em
color: var(--red)
display: block
margin-bottom: 14px

/* Badge (ClawBoi badge-new) */
background: var(--red)
color: white
font: 9px/600 Source Sans, uppercase, tracking 0.05em
padding: 2px 6px
border-radius: 2px
```

### Hover State (universal)

```css
transition: background 0.15s;

:hover {
  background: rgba(0,0,0,0.02);   /* light mode */
}

[data-theme="dark"] :hover {
  background: rgba(255,255,255,0.03);
}
```
Used on: memory items, output cards, steps, headline items. Never a border change or scale — just a whisper of background.

### Pull Quote

```css
/* ClawBoi — centered, full-width */
text-align: center;
padding: 32px 60px;
/* decorative " via ::before — 72px Playfair, color: var(--border) */

.pull-quote-text: 24px Playfair italic, line-height 1.4

/* Specview — 2-column grid */
grid-template-columns: 1fr 1px 1fr;
.pullquote-mark: 56px Playfair 700, color: var(--border)
.pullquote-text: 22px Playfair italic
.pullquote-attr: 11px Source Sans uppercase, var(--ink-muted)
```

### Expanded Panel (ClawBoi only)

Frameless inline expansion — inserts into page flow, not a modal:
```css
border-top: 3px solid var(--ink);
border-bottom: 1px solid var(--border);
padding: 40px 0;

.expanded-title: 36px Playfair, max-width 900px
.expanded-body: 16px Source Serif, line-height 1.8
                column-count: 2; column-gap: 48px;
                column-rule: 1px solid var(--border);
```

Close button: `×` character, 32px, `color: var(--ink-muted)`, no border.

### Chat Panel (ClawBoi only)

Fixed bottom-right floating panel:
- Mode toggle: ⚡ Haiku (fast) / 🦁 Sonnet (full context)
- Input: `→` send button (arrow character)
- Not a modal — overlaps page, dismissable

### 2-Column Body Text (ClawBoi)

Used in lead story and expanded panel:
```css
column-count: 2;
column-gap: 32–48px;
column-rule: 1px solid var(--border);
```
Authentic newspaper column layout for long-form content.

### Step Numbers (Specview landing)

```css
font: 64px/1 Playfair 700
color: var(--border)  /* intentionally faint — decorative, not informational */
```

### Code/Terminal Blocks (Specview landing)

```css
font-family: 'SF Mono', Consolas, monospace;
font-size: 12px;
background: var(--border);
border-left: 3px solid var(--ink-muted);
padding: 10px 14px;
```

### Mood Chart (ClawBoi only)

Bar chart of historical moods:
```css
display: flex; align-items: flex-end; gap: 4px; height: 60px;
/* bars: var(--mood-10) #2E7D32 → var(--mood-0) #C62828 */
/* tooltip via ::after on hover */
```

### Person/Tag Pills (ClawBoi sidebar)

```css
font: 12px Source Sans
padding: 4px 10px
border: 1px solid var(--border)
border-radius: 2px   /* only place radius appears */
background: var(--bg)
```

### Markdown Headings (ClawBoi expanded content)

```css
h1: 24px Playfair 700
h2: 20px Playfair 700
h3: 13px Source Sans 600, uppercase, tracking 0.05em, color: var(--ink-light)
```
H3 deliberately uses sans — signals a sub-label, not a headline.

---

## Interaction Principles

1. **No shadows** — depth comes from borders and typography size, not elevation
2. **No border-radius on structural elements** — buttons, inputs, panels are square
3. **2px radius only on pill tags** — the one exception, for inline labels
4. **Transitions: 0.15s max** — subtle, never animated
5. **Hover = `rgba` fill** — never a border change, color change, or movement
6. **Close/dismiss = `×` character** — not an icon, 28–32px, weight 300
7. **Theme toggle = icon in button** — square border, no background fill

---

## Specview Landing vs ClawBoi — Where They Differ

| Aspect | ClawBoi | Specview Landing |
|--------|---------|-----------------|
| Purpose | Live app dashboard | Static marketing page |
| Container | `max-width: 1400px` `.page` wrapper | Same, added 2026-05 |
| Masthead border | `1px solid var(--border)` | `1px solid var(--border)` (aligned 2026-05) |
| Nameplate rule | `div.divider.thick` below nav | `border-top: 3px` on `.section-bar` |
| Tagline | Italic | Italic (aligned 2026-05) |
| Section nav | Centered | Centered (aligned 2026-05) |
| Content | Dynamic JS-rendered data | Static HTML |
| Chat panel | Floating bottom-right | Not present |
| 2-col body text | Yes (lead + expanded) | Not present |
| Expanded panel | Inline frameless | Not present |
| Icons | Emoji (chat mode toggles) | Lucide SVG (added 2026-05) |

---

## Do Not

- Do not use `box-shadow` anywhere
- Do not add border-radius to cards, buttons, or panels
- Do not use color for hierarchy — use font-weight and font-size
- Do not use `--accent` (#567B95) heavily — it is a one-off highlight color
- Do not replace `--red` with a softer color — it is intentional for overlines/badges
- Do not change the font stack — all three fonts are load-bearing
- Do not use `font-weight: 400` for Playfair headlines — always 700
- Do not animate layout — transitions on `background` only

---

## Enhancements to Consider

- **2-column body text** in Specview landing lede (matches ClawBoi lead-body)
- **`section-badge`** count pattern on section headings (ClawBoi: gray pill `border-radius: 2px`)
- **Inline expansion** pattern for output cards (click → expand in place, no modal)
- **Time-labeled grids** ("This Week" / "Earlier") for any chronological content
- **Lucide icons** replacing remaining emoji in ClawBoi (chat mode toggles, chat button)

---

*Snapshot taken: 2026-05-07. Last aligned: Specview landing ← ClawBoi patterns.*
