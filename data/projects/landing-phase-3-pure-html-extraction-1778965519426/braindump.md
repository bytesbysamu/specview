# Landing Page Phase 3 — Pure HTML Extraction from Playground

The playground is the superset. The landing page is a curated extract — pick the strongest sections, strip the fat, ship clean HTML that follows the original UX design system to the letter.

## The Vision

Rewrite `landing/landing-v2.html` from scratch. Not a patch — a clean extraction informed by the playground components we just built (pg-landing-showcase, pg-hero, pg-problem). Same `style.css`, same nginx container, same deployment. But this time: strict design system compliance, less text, more editorial restraint.

The landing page should feel like a one-page newspaper front — you scan it in 30 seconds, understand the product, see the value, get started. No walls of text. No decorative flourishes. Typography and borders do all the work.

## Source Material

All content lives in `web-ng/src/app/pg-landing-data.ts` — output cards, how-it-works steps, comparison rows, pricing tiers, FAQ items, pull quotes. Hardcode this data directly into the HTML. No JavaScript data binding, no templates. Just HTML with the content baked in.

The design system is `landing/style.css` (1224 lines). Every class needed already exists. Zero new CSS should be written — only instantiate what's already defined. If a pattern isn't in style.css, it doesn't ship.

## Sections to Include (Pick and Choose)

Not everything from the playground ships. The landing page is editorial — it curates. Include:

**Masthead** — the newspaper header. "Vol. II", "Specview" in 64px Playfair, "All the Specs Fit to Build" tagline. Theme toggle. Sets the entire tone.

**Hero/Lede** — two-column split. Left: overline + headline ("Paste a braindump. Get production-ready specs.") + one-sentence deck + CTA. Right: generation status visualization with file list. The file list shows the five deliverables appearing with timing data. Keep it tight — three lines max for the deck.

**Stat strip** — four numbers in a row: 44.5s average, 5 files, 0 code written, Free tier. Borders between. Playfair numbers, sans labels. Punchy.

**Output cards** — what ships. Five cards in a grid: analysis.md, epic.md, architecture.md, timeline.md, implementation-guide.md. Icon + filename + one-line description. That's it. No paragraph explanations.

**How it works** — three steps. Giant Playfair numbers (96px), title, one sentence body, and a code-style excerpt showing real output. Braindump → Generate → Implement. The excerpts sell it — show actual spec content.

**Comparison table** — Specview vs Lovable/Bolt/Kiro across six dimensions. Full-width table, serif headers, muted competitor column. This is where the positioning lands. Input (braindump vs prompt), Output (5 specs vs code), Architecture (explicit vs implicit), Docs (complete vs none), Quality (spec-reviewed vs YOLO), Pricing (free vs $20+/mo).

**Pricing** — Free and Pro side by side. Simple. Dash-bullet features. One CTA each. No marketing fluff.

**FAQ** — native `<details>/<summary>` elements. 5-7 questions. Playfair headings, Source Serif answers. Concise answers — two sentences max each.

**Footer** — brand, year, links (GitHub, contact). Minimal.

## Sections to OMIT

- Demo strip (too complex for static HTML, better experienced in the app)
- Context cards / "who it's for" (adds length without selling)
- Pull quotes (we don't have real testimonials yet — feels fake)
- Update banner (no update to announce)

## Design System Compliance (Fix These Violations)

The current landing-v2.html has violations that the new version must fix:

- **No border-radius anywhere** — not on badges, not on dots, not on buttons. Square everything.
- **No box-shadow** — remove hover shadows on cards. Use border-color change or subtle background shift instead.
- **Three fonts only** — Playfair Display, Source Serif 4, Source Sans 3. No SF Mono. Code excerpts use Source Sans 3 at reduced size with a background color, or just use the system monospace stack without declaring a named font.
- **No decorative animations** — the shimmer, the dot-pulse, the flash animations violate "typography and borders only." The hero status bar can show static state (files listed, one marked as "generating") without animation. If animation is essential for the hero, it must be CSS-only and purely functional (a simple opacity transition at most).
- **No inline styles** — every style should come from a class in style.css. If there's no class for it, the element doesn't belong.
- **All colors via tokens** — var(--ink), var(--bg), var(--border), var(--red), var(--accent). No hardcoded hex, no rgba except in hover states already defined in style.css.

## Tone and Copy

Less is more. The playground can be verbose because it's a case study. The landing page is a pitch — every word earns its place.

- Headlines: 5-8 words max
- Deck sentences: one sentence, under 20 words
- Card descriptions: one line
- FAQ answers: two sentences max
- No marketing superlatives ("revolutionary", "game-changing", "powerful")
- Voice: direct, confident, slightly editorial. Like a newspaper editor writing a headline.

## Dark Mode

Same implementation as playground: `[data-theme="dark"]` attribute on `<html>`, toggled via 10 lines of vanilla JS that persists to localStorage. All tokens in style.css already have dark mode overrides. The HTML just needs to instantiate elements that use token-based colors — dark mode comes free.

## Responsive

Mobile-first. Breakpoints at 768px and 1100px (already in style.css). The grid patterns (output cards, steps, pricing) automatically reflow at these breakpoints via existing media queries. The hero splits to single-column on mobile. Masthead centers. No new responsive CSS needed.

## What Success Looks Like

A single `index.html` file that:
- Loads in under 1 second (it's just HTML + one CSS file + Google Fonts)
- Scans in 30 seconds on first visit
- Communicates: "paste braindump, get specs, free"
- Looks like a newspaper front page (cream, ink, red accents, editorial typography)
- Works perfectly in dark mode
- Has zero design system violations
- Uses only existing style.css classes
- Is under 300 lines of HTML (lean, no bloat)
