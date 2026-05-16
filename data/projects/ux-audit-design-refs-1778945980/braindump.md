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
