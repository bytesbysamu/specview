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
