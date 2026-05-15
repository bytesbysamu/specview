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
