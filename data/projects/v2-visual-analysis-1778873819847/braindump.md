# V2 Visual Analysis (from rendered screenshots, 2026-05-15)

### What V2 looks like now
Three sections stacked vertically but NOT visually unified:
1. Landing pitch (top) — newspaper aesthetic, Playfair Display, warm cream, looks great
2. Design playground (middle) — same newspaper aesthetic (loaded via fetch), shows all tokens/components
3. App workspace (bottom) — generic UI framework look, system fonts, flat green bars, completely different visual language

### The core CSS problem
The V2 app workspace uses its own CSS vars (`--bg-primary`, `--text-primary`, `--border-default`) which are UNDEFINED in the project's stylesheets. The newspaper design system uses `--ink`, `--bg`, `--border`, `--serif`, `--sans`, `--body`. The V2 components don't reference these — so they render with browser defaults.

### V1 vs V2 app section comparison

| Element | V1 (original app) | V2 app section |
|---------|-------------------|----------------|
| Masthead | Full newspaper: "Spec Doc", date, "Specview", tagline | Missing entirely |
| Fonts | Playfair Display + Source Serif 4 + Source Sans 3 | System defaults |
| Status bar | Dark olive with white text, project name, step, timer | Flat green rectangle, tiny text |
| Project grid | 4-column newspaper grid with featured cards, teasers, section groups | Compressed single-column list |
| Section nav | Pill buttons with count badges, active underline | Generic grey buttons |
| Search | Inline with project count label | Cramped in toolbar row |
| Background | Warm cream (#FFFEF9) | White (undefined var fallback) |

### What's actually unified
Only the landing pitch and design playground share the same visual language (both use landing/style.css). The app workspace is visually disconnected.

### V2 pros
- Component decomposition (5 reusable sub-components: grid, reader, sidebar, status bar, section nav)
- Landing pitch for anonymous users
- Design playground visible on the same page
- Clean input/output contracts between components

### V2 cons
- No masthead / newspaper identity in the app section
- Wrong CSS tokens — generic vars instead of newspaper design system
- Modal is transparent (--bg-primary undefined)
- Upgrade button calls logout() instead of navigateToUpgrade()
- No panel slide animation
- No usage meter
- No word count in reader
- App section looks like a completely different product from the landing/playground above it

### What the user wants for the next iteration
- Keep V2's component decomposition
- Use V1's CSS classes and newspaper design tokens (--ink, --bg, --serif, --sans, --border)
- Keep V1's masthead with edition, date, title, tagline
- Keep V1's panel slide animations
- Keep V1's usage meter and word count
- The design playground CSS should BE the app's CSS — not a separate aesthetic
- The three sections (landing, playground, app) should look like ONE page, not three products glued together
- The V1 app already IS the playground design brought to life — V3 should recognise this

### V3 direction
Take the original V1 app (app.component.html + styles.css) which already uses the newspaper design system. Prepend the landing pitch for anonymous users. Use V2's decomposed components but re-style them with V1's CSS classes. The V1 app IS the playground design — there should be no visual gap between the playground section and the app section.

---
