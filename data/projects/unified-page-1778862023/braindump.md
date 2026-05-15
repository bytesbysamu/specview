# Unified Page — Landing + Playground + App

I want to brain dump mixing the landing page, the playground, and the app into one page. So we just create one template that includes the app and the landing page and also the playground. It just reuses one route that combines all of them and shows them on one page at /.

It's kind of like the app page but seeds a braindump — save the braindump on the page. If possible create a new page and then we switch to that one, like you can call it app-v2 or whatever.

The idea: one unified page that is the landing page, the playground (live demo), AND the app — all in one. No separate routes, no separate containers. A visitor lands on / and sees everything: the product pitch, a live playground where they can paste a braindump and see it generate in real time, and if they're logged in, their full project list. Three experiences, one page, one route.

---

## 6. V2 Visual Analysis (from rendered screenshots, 2026-05-15)

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

## 7. V2 Brainstorm (2026-05-15, post-screenshot analysis)

### 1. Key Themes

The design system IS the product — The newspaper aesthetic isn't a skin; it's the entire value proposition. When the app section drops it, users don't see "a different theme" — they see a different product. The V1 app already proved that the playground design works as a real UI. V2 broke that proof by introducing a parallel CSS universe.

Component decomposition vs. visual coherence — a false trade-off — V2 made the right architectural move (5 reusable sub-components) but the wrong aesthetic move (generic CSS vars). These are independent axes. You can have clean input/output contracts AND --ink/--bg/--serif. The refactor confused "modular code" with "framework-default styling."

One route as product philosophy — This isn't just a routing decision. It's a statement: the demo IS the product, the product IS the demo. There's no "sign up to see the real thing" bait-and-switch. A visitor's first braindump in the playground should feel identical to their 50th braindump as a paying user. The route boundary was always artificial.

CSS token misalignment is the single highest-leverage bug — Every visual complaint (white background, system fonts, transparent modals, flat status bars) traces back to one root cause: V2 components reference --bg-primary, --text-primary, --border-default while the design system defines --ink, --bg, --border. Fix the token mapping and 80% of the visual problems vanish in one pass.

The upgrade button calling logout() is a trust-destroying bug — This isn't a footnote. A user clicks "upgrade" and gets logged out. That's the kind of bug that makes people never come back. It needs to be fixed before any visual work.

### 2. Hidden Connections

The playground is a Trojan horse onboarding flow. If the playground uses the same CSS as the app, then a visitor who pastes a braindump into the playground has already completed onboarding. They've learned the UI, seen their own content rendered in the newspaper aesthetic, and formed muscle memory — all before creating an account.

V1's masthead solves V2's identity crisis. The masthead isn't decoration — it's the persistent frame that tells the user "you're still in the same product." Without it, scrolling from the landing pitch into the app section feels like navigating to a different site. The masthead is the connective tissue that makes one-route work.

The modal transparency bug reveals a deeper coupling problem. If --bg-primary is undefined and modals go transparent, it means V2 components aren't just visually wrong — they're structurally dependent on variables that don't exist in the host page. Every V2 component is a potential rendering bomb if any of its assumed CSS vars are missing.

The 4-column newspaper grid and the project list are the same data, presented at different confidence levels. V1's grid treats projects like newspaper stories (featured, teaser, section). V2's compressed list treats them like database rows. The grid format actually communicates project status and priority through layout — it's information architecture, not just aesthetics.

### 3. Open Questions

How does the page transition from anonymous to authenticated without a page reload or jarring re-render?
- Option A: Conditional @if blocks that swap landing pitch for project grid
- Option B: CSS-only transition — landing pitch slides up/collapses, app workspace fades in below
- Option C: The landing pitch never disappears — it becomes a collapsible "about" section
- Recommended: Option B

Should the playground braindump persist and become the user's first project on signup?
- Option A: Yes — auto-save to localStorage, migrate on signup
- Option B: No — playground is ephemeral
- Option C: Prompt the user
- Recommended: Option A

Do V2's 5 sub-components get re-skinned with V1 classes, or do you port V1's HTML structure into V2's component boundaries?
- Option A: Keep V2 HTML, replace CSS var references
- Option B: Take V1's HTML/CSS wholesale, break it into V2's component boundaries
- Option C: Hybrid — V2 structure, V1 templates inside each component
- Recommended: Option B. V1's HTML was written FOR the newspaper design system.

What happens to the design playground section for authenticated users?
- Option A: Hide it
- Option B: Keep it collapsed by default
- Option C: Transform it into a "create new project" workspace
- Recommended: Option C

### 4. Ideas to Explore

Token alias file (_token-bridge.css): maps --bg-primary: var(--bg), --text-primary: var(--ink), etc. Instant visual fix.

"Live front page" concept: unified page IS a newspaper front page. Anonymous users see pitch as lead story + playground as feature section. Authenticated users see their projects as lead stories. Same layout, different content.

Scroll-driven narrative: top = editorial voice, middle = interactive playground, bottom = your workspace. The scroll IS the onboarding funnel.

Kill the playground as a separate concept: if the app uses the same CSS, then opening a new project IS the playground.

Ship token bridge + logout bug fix TODAY before V3.

Use V1 screenshot as V3 acceptance test: overlay at 50% opacity, if app sections don't align, V3 isn't done.

Progressive disclosure via newspaper sections: FRONT PAGE (pitch), FEATURES (playground), OPINION (projects). The information architecture IS the design system.
