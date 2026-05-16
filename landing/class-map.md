# Landing Phase 3 — Class Map

Section-to-class mapping for the pure-HTML landing page extraction.
Every class name listed here is verified to exist verbatim in `style.css`.
Responsive and dark-mode coverage noted per section.

---

## CSS Token Inventory

All colors resolve through custom properties with `[data-theme="dark"]` overrides.

| Token | Light | Dark | Used by |
|---|---|---|---|
| `--bg` | #FFFEF9 | #141414 | body background, btn-primary text, demo backgrounds |
| `--ink` | #121212 | #E8E6E0 | body text, headings, buttons, borders |
| `--ink-light` | #5A5A5A | #A0A0A0 | deck, step-body, output-card__body, aside-list items |
| `--ink-muted` | #999999 | #606060 | dates, overlines, pricing period, stat-label, faq attr |
| `--border` | #DFDFDF | #2E2E2E | all separator lines, step-num color, pullquote-mark |
| `--border-dark` | #121212 | #E8E6E0 | markdown pre/blockquote border-left |
| `--accent` | #567B95 | #7BAFC8 | demo-tag, gen-status-track |
| `--red` | #C41E3A | #E05A72 | overline text |
| `--serif` | Playfair Display | (same) | masthead-title, headline, step-title, output-card__title |
| `--body` | Source Serif 4 | (same) | body text, deck, step-body, aside-list |
| `--sans` | Source Sans 3 | (same) | labels, overlines, buttons, metadata |

Status-specific tokens (`--status-*`, `--code-bg`) are defined in `style.css` under a second `:root` block and have `[data-theme="dark"]` overrides — safe to use without extra CSS.

---

## Class Catalog by Category

### Layout containers
- `.page` — max-width 1400px, centered
- `.lede` — 3-col grid (1fr 1px 340px), full-height hero
- `.lede-main` — left hero column
- `.lede-aside` — right info column
- `.output-grid` — 4-col card grid
- `.steps` — 3-col how-it-works grid
- `.pullquote-row` — 2-col quote grid
- `.pullquote-single` — centered single-quote layout
- `.demo-strip` — padded demo container
- `.demo-strip-inner` — bordered inner demo frame
- `.demo-body` — 3-col sidebar+content grid
- `.pricing` — flex column, 80vh min
- `.pricing-grid` — 2-col tier layout with divider
- `.stat-strip` — flex row stat bar
- `.compare-table-wrap` — scroll wrapper for table
- `.faq-list` — flex column accordion
- `.section-page` — full-viewport section wrapper
- `.section-page--compact` — reduced-height variant

### Typography
- `.masthead-title` — 64px serif, headline brand
- `.masthead-tagline` — 13px italic body
- `.masthead-edition` — 11px sans uppercase
- `.masthead-date` — 11px sans uppercase muted
- `.overline` — 11px sans uppercase red
- `.headline` — 44px serif bold
- `.deck` — 17px body text, ink-light
- `.section-heading` — 11px sans uppercase section label
- `.aside-label` — 11px sans bold, 2px ink border-bottom
- `.stat-value` — 36px serif bold
- `.stat-label` — 10px sans uppercase muted
- `.output-card__title` — 20px serif bold
- `.output-card__filename` — 11px sans muted
- `.output-card__body` — 14px body ink-light
- `.step-num` — 96px serif bold, border color
- `.step-title` — 22px serif bold
- `.step-body` — 15px body ink-light
- `.step-code` — monospace code block, border-left ink-muted
- `.pullquote-mark` — 56px serif decoration
- `.pullquote-text` — 22px serif italic
- `.pullquote-attr` — 11px sans uppercase muted
- `.pricing-tier-name` — 28px serif bold
- `.pricing-amount` — 48px serif bold
- `.pricing-period` — 13px sans muted
- `.pricing-desc` — 15px body ink-light
- `.footer-brand` — 20px serif bold
- `.footer-copy` — 11px sans muted
- `.demo-title` — 24px serif bold
- `.demo-tagline` — 10px sans uppercase muted

### Structural / borders / separators
- `.divider` — 1px border-top (via `border` token)
- `.divider.thick` — 3px border-top ink
- `.lede-divider` — 1px vertical rule (border token bg)
- `.pullquote-divider` — 1px vertical rule
- `.pricing-divider` — 1px vertical rule
- `.demo-sidebar-divider` — 1px vertical rule

### Interactive states
- `.theme-toggle` — icon button, border hover
- `.btn-primary` — ink bg, bg text, opacity hover
- `.btn-secondary` — transparent bg, border hover
- `.output-card:hover` — subtle bg tint (dark-mode overridden)
- `.step:hover` — subtle bg tint (dark-mode overridden)
- `.section-bar a:hover` / `.section-bar a.active` — ink color
- `.footer-links a:hover` — ink color
- `.demo-sidebar-item.active` — 5% bg tint (dark-mode overridden)
- `details.faq-item[open] summary::after` — '+' → '×' toggle

### Responsive overrides
- `@media (max-width: 1100px)`: `.output-grid` → 2-col; nth-child border corrections
- `@media (max-width: 860px)`: `.masthead-title` 42px; `.masthead-edition` hidden; `.lede` → 1-col; `.lede-divider` hidden; `.lede-aside` stacked; `.steps` → 1-col; `.step` → border-bottom; `.pullquote-row` → 1-col; `.pullquote-divider` hidden; `.section-bar` narrow padding; `.masthead` narrow padding; `.lede` narrow padding; `.section-heading` narrow padding; `.demo-strip` narrow; `.demo-body` 1-col; `.demo-sidebar` hidden; `.footer` column; `.headline` 32px; `.section-page` compact; `.stat-strip` wrap; `.compare-table` smaller fonts
- `@media (max-width: 640px)`: `.pricing-grid` → 1-col; `.pricing-divider` becomes horizontal
- `@media (max-width: 600px)`: `.output-grid` → 1-col; `.output-card` stacked; `.stat-strip` column; `.faq-item summary` 16px

---

## Section 1 — Masthead

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Outer container | `.masthead` (border-bottom 1px `--border`, padding 24px 40px 16px) |
| 3-col top row | `.masthead-top` (grid: 150px 1fr 150px) |
| Edition label | `.masthead-edition` (hidden at 860px) |
| Center stack | `.masthead-center` |
| Date line | `.masthead-date` |
| Brand headline | `.masthead-title` (64px serif; drops to 42px at 860px) |
| Tagline | `.masthead-tagline` |
| Actions slot | `.masthead-actions` |
| Theme button | `.theme-toggle` + SVG icons (`.theme-toggle svg` 14px, stroke 1.75) |

**Responsive:** At 860px, `masthead-edition` hides and `masthead-title` shrinks to 42px — layout collapses gracefully without new CSS.

**Dark mode:** All colors via `--ink`, `--ink-light`, `--ink-muted`, `--border`. Dark overrides present.

**Content:** Hardcoded — "Specview", "All the Specs Fit to Build", edition vol, JS-injected date.

---

## Section 2 — Hero / Lede

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Outer container | `.lede` (grid: 1fr 1px 340px; full-height; border-bottom) |
| Left column | `.lede-main` (padding-right 40px) |
| Vertical rule | `.lede-divider` (background `--border`; hidden at 860px) |
| Right column | `.lede-aside` (padding-left 40px; stacks with border-top at 860px) |
| Category label | `.overline` (red, uppercase) |
| H2 heading | `.headline` (44px serif; 32px at 860px) |
| Subtext | `.deck` (17px body, ink-light, max-width 520px) |
| CTA row | `.cta-row` (flex, gap 12px, wrap) |
| Primary CTA | `.btn-primary` (ink bg, bg text) |
| Secondary CTA | `.btn-secondary` (transparent, border) |
| Aside header | `.aside-label` (bold, border-bottom 2px ink) |
| Status bar | `.gen-status-bar .gen-status-bar--active` (active/success variants available) |
| Status track | `.gen-status-track` (shimmer animation) |
| Status content | `.gen-status-content`, `.gen-status-dot`, `.gen-status-name` |
| File list items | Inline styles in existing HTML — kept as-is (`.aside-list` not used here; inline approach from `index.html` preserved) |

**Responsive:** At 860px, `.lede` collapses to 1-col; divider hides; aside stacks with a border-top. `.headline` shrinks to 32px. No new CSS needed.

**Dark mode:** All colors via tokens. `gen-status-bar` uses `--status-*` tokens with dark overrides.

**Content from `pg-landing-data.ts`:** Not pulled from data arrays — hero is hardcoded copy ("Write messy. Ship clean." / "Paste your braindump..."). The HOW_IT_WORKS_STEPS[0].excerpt is available but not needed here; the inline progress indicator in `index.html` is clearer.

---

## Section 3 — Stat Strip

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Row container | `.stat-strip` (flex; border-bottom) |
| Each stat | `.stat-item` (flex: 1; padding 28px 32px; border-right; last-child no border) |
| Number | `.stat-value` (36px serif bold, ink) |
| Label | `.stat-label` (10px sans uppercase, ink-muted) |

**Responsive:** At 860px, `.stat-strip` wraps and `.stat-item` gets `min-width: 50%` (2×2 grid). At 600px, `.stat-strip` becomes column.

**Dark mode:** All via `--ink`, `--ink-muted`, `--border` tokens.

**Content — editorial selection from `pg-landing-data.ts`:**
The TypeScript data file has no `STATS` array — stats are hardcoded in `index.html`. The four values used in the current `index.html` are the right set:
- `44.5s` / "avg generation"
- `5` / "files per run"
- `0` / "human code lines"
- `Free` / "to start"

These are retained verbatim. No data array to filter.

---

## Section 4 — Output Cards

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Grid wrapper | `.output-grid` (4-col; border-bottom; 2-col at 1100px; 1-col at 600px) |
| Each card | `.output-card` (padding 28px 32px; border-right; hover bg tint) |
| Last card | `.output-card:last-child` (border-right none) |
| Icon slot | `.output-card__icon` (22px, block; SVG 24px stroke 1.5, ink-light) |
| Title | `.output-card__title` (20px serif bold) |
| Filename | `.output-card__filename` (11px sans muted) |
| Body text | `.output-card__body` (14px body ink-light) |

**Responsive:** At 1100px → 2-col with `nth-child(2)` border correction. At 600px → 1-col with border-bottom instead of border-right.

**Dark mode:** `.output-card:hover` has explicit `[data-theme="dark"]` override using `rgba(255,255,255,0.03)`.

**Content — editorial selection from `OUTPUT_CARDS` (5 items):**
All 5 items ship — the array maps exactly to 5 documents. No editorial cut needed; each advances the 30-second comprehension goal (user learns what they get).

However, the existing `index.html` uses shorter body copy than `pg-landing-data.ts`. The shorter landing copy is preferred:

| Card | Landing copy (index.html) — USE THIS |
|---|---|
| Analysis | "Surfaces the real problem, constraints, and scope before a single line of code is written." |
| Epic | "Breaks the feature into tasks with effort estimates and explicit dependency ordering." |
| Architecture | "Documents component design, data flow, and the key decisions that shape every implementation choice." |
| Timeline | "Maps each task to a delivery window so the team can track progress and spot slippage early." |
| Implementation Guide | "Hands each task to an agent with exact steps, files, and verify criteria needed to ship it." |

The `pg-landing-data.ts` descriptions are more verbose and suited to the playground modal — they are NOT used in the HTML landing page.

---

## Section 5 — How It Works

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Grid container | `.steps` (3-col; border-bottom; min-height 100vh; 1-col at 860px) |
| Each step | `.step` (padding 80px 48px; border-right; hover tint; flex column center) |
| Last step | `.step:last-child` (border-right none) |
| Step number | `.step-num` (96px serif, border color — large decorative digit) |
| Step title | `.step-title` (22px serif bold) |
| Step body | `.step-body` (15px body ink-light) |
| Code excerpt | `.step-code` (monospace; border-left 3px ink-muted; dark override `#1E1E1E`) |

**Responsive:** At 860px, `.steps` collapses to 1-col; each `.step` gets `border-right: none` and `border-bottom` instead.

**Dark mode:** `.step:hover` has explicit `[data-theme="dark"]` override. `.step-code` has `[data-theme="dark"]` background `#1E1E1E`.

**Content — editorial selection from `HOW_IT_WORKS_STEPS` (3 items):**
All 3 steps ship. However the copy in `index.html` is tighter than `pg-landing-data.ts` bodies — the landing uses concise one-sentence descriptions. The code excerpts in `index.html` are more readable than the raw `excerptLabel` strings from the data file.

Keep `index.html`'s existing step copy; do NOT pull from `HOW_IT_WORKS_STEPS.body` or `HOW_IT_WORKS_STEPS.excerpt` — those are written for the playground showcase modal, not a landing.

Step numbers are `1`, `2`, `3` (single digits) in `index.html` vs `'01'`, `'02'`, `'03'` in the data — single digits are correct for the 96px `.step-num` display.

---

## Section 6 — Comparison Table

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Scroll wrapper | `.compare-table-wrap` (overflow-x: auto at 600px) |
| Table | `.compare-table` (full-width, border-collapse, sans 14px) |
| Header row | `thead tr` + `border-bottom: 2px solid var(--ink)` |
| Header cells | `.compare-table th` (11px uppercase, 0.08em tracking) |
| Data rows | `tbody tr` + `border-bottom: 1px solid var(--border)`; last-child no border |
| Row label cell | `td:first-child` (ink-light, 600 weight, 140px, 12px uppercase) |
| Competitor column | `.col-them` (ink-muted) |
| Specview column | default `td` (ink) |

**Responsive:** At 860px, font shrinks to 13px and padding reduces. At 600px, `.compare-table-wrap` scrolls horizontally.

**Dark mode:** All via `--ink`, `--ink-light`, `--ink-muted`, `--border` tokens. No additional overrides needed.

**Content — editorial selection from `COMPARISON_ROWS` (6 items):**
The `index.html` uses simplified, sharper copy rather than the verbose descriptions in `COMPARISON_ROWS`. The landing table uses 6 rows matching the 6 COMPARISON_ROWS dimensions. Editorial decision: use the tighter landing copy, not the data file strings.

| Dimension | Competitor (landing) | Specview (landing) |
|---|---|---|
| Input | "Chat prompt" | "Braindump — 3 paragraphs" |
| Output | "Code you didn't write" | "Specs you review, then code that matches" |
| Architecture | "AI decides" | "You review before a line is written" |
| Docs | "None" | "Built-in — every feature is documented" |
| Quality | "Hope it works" | "Spec → implement → verify loop" |
| Pricing | "$20–550/mo credits" | "$12/mo flat, unlimited" |

All 6 rows advance comprehension; none dropped.

Section heading uses `.section-heading` + `.section-page` with inline `min-height:auto;padding:40px` override (not a new class — inline style on existing class).

---

## Section 7 — Pricing

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Outer wrapper | `.pricing` (flex column; border-bottom; 80vh min; padding 80px 40px) |
| Tier grid | `.pricing-grid` (1fr 1px 1fr; max-width 880px; centered) |
| Visual divider | `.pricing-divider` (background `--border`; collapses to 1px horizontal at 640px) |
| Each tier | `.pricing-tier` (flex column; gap 16px; padding 32px 0) |
| Tier name | `.pricing-tier-name` (28px serif bold) |
| Price row | `.pricing-price` (flex; baseline alignment) |
| Amount | `.pricing-amount` (48px serif bold) |
| Period | `.pricing-period` (13px sans muted) |
| Description | `.pricing-desc` (15px body ink-light) |
| Features list | `.pricing-features` (list-style none; flex column; gap 8px) |
| Feature item | `.pricing-features li` (11px sans uppercase; `::before` content '—') |
| CTA container | `.pricing-cta` (margin-top auto; pushes to bottom) |
| Primary CTA | `.btn-primary` |

**Responsive:** At 640px, `.pricing-grid` → 1-col; `.pricing-divider` becomes a full-width 1px line.

**Dark mode:** All via `--ink`, `--ink-light`, `--ink-muted`, `--border` tokens.

**Content — editorial selection from `PRICING_TIERS` (2 items):**
Both tiers ship. The `index.html` uses a simplified feature list vs the data file's more verbose features. Landing copy preferred:

| Tier | Landing features |
|---|---|
| Free | 3 projects / month; Full spec pipeline; No credit card required |
| Pro | Unlimited projects; Full spec pipeline; Priority support |

The `PRICING_TIERS` features array items are verbatim usable but overkill for the landing page — the landing's shorter list is retained. Description copy is also simplified vs the data file.

Section is labeled "Start building" using `.section-heading`, then wrapped with both `.section-page` and `.pricing` classes (the pricing class provides its own layout — `.section-page` is redundant here but harmless; existing `index.html` uses this pattern).

---

## Section 8 — FAQ

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Outer container | `.section-page` with inline `min-height:auto;padding:40px` |
| Accordion list | `.faq-list` (flex column) |
| Each item | `details.faq-item` (border-bottom `--border`) |
| Question trigger | `details.faq-item summary` (serif 18px bold; flex space-between; `+`/`×` via `::after`) |
| Summary marker | Hidden via `summary::-webkit-details-marker` |
| Answer body | `.faq-answer` (15px body ink-light; padding 0 48px 20px 0; max-width 680px) |

**Responsive:** At 600px, `summary` font-size drops to 16px. No layout changes needed.

**Dark mode:** All via `--ink`, `--ink-light`, `--border`. The `details`/`summary` native element has no extra dark-mode quirks.

**Content — editorial selection from `FAQ_ITEMS` (7 items):**
The `index.html` ships 5 FAQ items with different questions than the data file. The data file's 7 items are higher-quality and address sharper objections. Recommended subset (5 of 7, selected for 30-second comprehension goal):

| # | Question | Rationale |
|---|---|---|
| 1 | "How messy can my braindump actually be?" | Core anxiety — address first |
| 2 | "What kinds of projects does it work for?" | Scope clarity — universal |
| 3 | "How long does generation actually take?" | Speed claim with real number |
| 4 | "Can I use the generated specs with AI coding assistants?" | Top use case |
| 5 | "Does Specview write code?" | Critical disambiguation from Lovable/Bolt |

Dropped items from data file:
- "Is my braindump stored?" — privacy concern; include only if self-host audience is primary
- "What if the generated spec gets something wrong?" — defends failure mode; softens pitch

The `index.html`'s current questions are replaced with the above subset in Phase 3 HTML.

Section is labeled "Questions" using `.section-heading`.

---

## Section 9 — Footer

**Verdict: Full class coverage. Ships as-is.**

| Role | Class(es) |
|---|---|
| Footer bar | `.footer` (flex space-between; border-top 3px ink; padding 24px 40px) |
| Brand name | `.footer-brand` (20px serif bold) |
| Copyright line | `.footer-copy` (11px sans muted) |
| Links nav | `.footer-links` (flex, gap 20px) |
| Each link | `.footer-links a` (11px sans uppercase ink-light; hover → ink) |

**Responsive:** At 860px, `.footer` becomes `flex-direction: column; gap: 12px; text-align: center`.

**Dark mode:** All via `--ink`, `--ink-muted` tokens.

**Content:** Hardcoded — "Specview", "Built by Sam · Powered by Claude", GitHub / Twitter/X / Contact links. No data array involved.

---

## Supplementary Elements

These are used inline within sections above and need no separate mapping:

| Element | Classes / notes |
|---|---|
| Section nav bar | `.section-bar` with `a.active` state; overflow-x auto; hides at 860px padding |
| Pull quote (single) | `.pullquote-single > .pullquote > .pullquote-mark + .pullquote-text + .pullquote-attr` |
| Demo strip | `.demo-strip > .demo-strip-inner > .demo-masthead + .demo-body` — full class chain verified |
| Markdown content | `.markdown-content` with h1/h2/h3/p/code/pre/blockquote — used inside demo panel |
| Gen status bar | `.gen-status-bar` + modifier (`--active`, `--success`, `--failure`) + `.gen-status-track` + `.gen-status-content` + `.gen-status-dot` + `.gen-status-name` |
| Update banner | `.update-banner` with button and anchor variants — available but not planned for phase 3 |

---

## Dropped / Redesigned Sections

### Update banner — Dropped
**Rationale:** The `.update-banner` class exists in `style.css` and is feature-complete. However the landing page has no versioned release cadence to announce. Including it as a placeholder with dummy text hurts credibility. Dropped until there is real content to announce.

### Metrics bar — Dropped
**Rationale:** `.metrics-bar`, `.metrics-sep`, `.metrics-plus` are in `style.css`. The playground uses this for a single-line stat summary. The landing already has a full `.stat-strip` with four stats — adding a metrics bar creates redundancy. One stat format per page is the rule. Dropped.

### Context cards — Dropped
**Rationale:** `.context-card`, `.context-card__label`, `.context-card__desc`, `.context-grid` are in `style.css`. These exist for the playground's project-context selector UI. They have no analog in the landing information architecture. Dropped.

### Dual pullquote row — Simplified to single
**Rationale:** `.pullquote-row` (two-column layout) works but requires fabricating two distinct attributions. `.pullquote-single` (centered layout, already in `index.html`) achieves more editorial impact with one strong quote. The dual row is not used in phase 3.

---

## Verified Class Existence Check

All class names listed in this document are present verbatim in `landing/style.css`. Classes verified by section:

- Masthead: `.masthead` `.masthead-top` `.masthead-edition` `.masthead-center` `.masthead-date` `.masthead-title` `.masthead-tagline` `.masthead-actions` `.theme-toggle`
- Hero: `.lede` `.lede-main` `.lede-divider` `.lede-aside` `.overline` `.headline` `.deck` `.cta-row` `.btn-primary` `.btn-secondary` `.aside-label` `.gen-status-bar` `.gen-status-bar--active` `.gen-status-bar--success` `.gen-status-track` `.gen-status-content` `.gen-status-dot` `.gen-status-name`
- Stat strip: `.stat-strip` `.stat-item` `.stat-value` `.stat-label`
- Output cards: `.output-grid` `.output-card` `.output-card__icon` `.output-card__title` `.output-card__filename` `.output-card__body`
- How it works: `.steps` `.step` `.step-num` `.step-title` `.step-body` `.step-code`
- Comparison: `.compare-table-wrap` `.compare-table` `.col-them`
- Pricing: `.pricing` `.pricing-grid` `.pricing-divider` `.pricing-tier` `.pricing-tier-name` `.pricing-price` `.pricing-amount` `.pricing-period` `.pricing-desc` `.pricing-features` `.pricing-cta`
- FAQ: `.faq-list` `.faq-item` `.faq-answer`
- Footer: `.footer` `.footer-brand` `.footer-copy` `.footer-links`
- Shared: `.page` `.section-heading` `.section-bar` `.section-page` `.section-page--compact` `.divider` `.divider.thick` `.pullquote-single` `.pullquote` `.pullquote-mark` `.pullquote-text` `.pullquote-attr` `.demo-strip` `.demo-strip-inner` `.demo-masthead` `.demo-title` `.demo-tagline` `.demo-body` `.demo-sidebar` `.demo-sidebar-label` `.demo-sidebar-item` `.demo-sidebar-item.active` `.demo-sidebar-divider` `.demo-content` `.demo-tag` `.markdown-content`

Zero invented classes.
