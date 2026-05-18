# Braindump: Landing V2 — Playground-Inspired, From Scratch

## The Idea

Build a new landing page HTML file from zero. No inheritance from the current `landing/index.html`. The only source of truth is `landing/playground.html` and `landing/style.css`.

This is not a playground. This is not a demo of components. This is a landing page that *is* the design system living — where every section is a design pattern used correctly as real content, not as a demonstration of itself.

The current landing says "here is how the masthead looks." The new landing just *has* a masthead. The difference is enormous.

## The Core Principle

The playground already has every component, token, spacing rule, and interaction state. Instead of documenting those components, we use them — exactly as they were designed — to tell the story of the product. The playground is the Figma. The new landing is the shipped design.

No code blocks. No `<div class="step-code">`. No "here is the X component." Every section is a real page section, styled with the existing design system, containing real content about what Spec Doc does.

## What Gets Built

A single new HTML file — `landing/landing-v2.html` (or replaces `index.html` eventually). It shares `landing/style.css` unchanged. No new CSS. Every visual element is something that already exists in `style.css`.

## Structure (Design-First, Content TBD)

The file establishes the correct structure using every major pattern from the playground. Content comes in the next pass — for now, placeholder editorial text is fine as long as the design system is used correctly.

### Masthead
- Newspaper masthead: Playfair Display title, Source Serif italic tagline, date, edition label
- Section nav with anchor links below it (nameplate rule)
- Theme toggle (sun/moon inline SVGs)
- This is the masthead pattern from the playground used as the actual page header — not shown as a demo

### Hero / Lede
- Two-column lede layout (`.lede`, `.lede-main`, `.lede-aside`, `.lede-divider`)
- Left: editorial headline (`.headline`) + deck paragraph + primary CTA
- Right: `.output-grid` with 5 `.output-card` elements (the artifacts)
- No bullet lists, no `<ul>` — the card grid *is* the artifact enumeration

### Overline Sections
- Each major section uses `.overline` + `.section-heading` pattern
- Red uppercase overline above the section title — exactly as playground shows
- Sections: What it does / How it works / See it in action / Start building

### How It Works (Steps)
- Three-column `.steps` grid using `.step`, `.step-num`, `.step-title`, `.step-body`
- Step numbers as large Playfair numerals
- Body copy only — no `.step-code` blocks, no code mockups
- Steps describe the methodology: braindump → spec set → implementation

### Demo Strip
- Full `.demo-strip` component used as a live section
- Shows a real miniaturized spec inside the page — the newspaper layout in miniature
- `.demo-masthead`, `.demo-sidebar` (artifact nav), `.demo-content` (real spec excerpt)
- This is not a "demo of the demo strip" — it IS the product experience

### Pull Quote
- `.pullquote-row` with one editorial pull quote about the methodology
- Typography-only section, no chrome

### Pricing / CTA
- Existing pricing section reused as-is with correct token usage
- Section with overline, tier cards, primary CTA

### Footer
- Same footer pattern as current landing

## What Is Explicitly Absent

- No `<i data-lucide="...">` or any CDN icon library — inline SVGs or emoji only
- No `.step-code` blocks (code mockups belong to the playground, not the landing)
- No "here is the component" framing — just the component, used
- No new CSS classes — everything from `landing/style.css`
- No inline `style=""` attributes
- No JavaScript beyond the existing theme toggle + date label

## The Visual Contract

Open `http://localhost:8096/playground.html` — every pattern visible there is available. The new landing is what happens when you remove the labels and fill the components with real product content. The playground is the reference; the new landing is the application.

## Relationship to Current Landing

The current `landing/index.html` stays intact. The new file is `landing/landing-v2.html` until it's ready to replace. At that point, `index.html` becomes `index-old.html` and `landing-v2.html` becomes `index.html`.

## Next Step After Braindump

Once analysis + spec + architecture are generated, the implementation guide will map real Spec Doc content into each design system slot — what the hero headline says, what the pull quote says, what the three step descriptions are. That is a content pass, not a design pass. The design is already done in the playground.
