# Implementation Guide: landing-v2-playground

## Overview
This epic delivers a from-scratch `landing/landing-v2.html` that consumes the playground as a frozen pattern library and applies it to a real editorial newspaper landing page — masthead, lede with output-grid, four overline sections, three-step grid, demo strip, pull quote, pricing, and footer. Tasks sequence as a single linear arc with two parallel branches: Task 1 inventories the playground patterns, Task 2 establishes the masthead and lede skeleton, then Tasks 3 (overline sequence), 4 (demo strip through footer), and 5 (script port) run in parallel against that skeleton. The result ships alongside `landing/index.html` with zero CSS changes and no new JavaScript authored.

## Shared Pre-flight
- Confirm working directory is the repo root and that `landing/index.html`, `landing/playground.html`, and `landing/style.css` all exist and are readable.
- Open `landing/playground.html` in a browser at `http://localhost:8096/playground.html` to confirm the static container is serving the `landing/` directory.
- Skim `landing/style.css` to internalize which class hooks exist; treat the stylesheet as read-only for the duration of this epic.
- Verify `landing/index.html` has not been modified — it must remain unchanged through every task.
- Decide once that placeholder editorial copy is acceptable: paragraph counts and line lengths matter, exact words do not.
- Keep a scratch list of every class name added to `landing-v2.html` so it can be cross-checked against `style.css` at the end.
- Do not introduce any `style="..."` attributes, any `<i data-lucide>` references, or any CDN script/style tags beyond what `index.html` already loads.
- Do not create `.step-code` blocks or code-mockup chrome of any kind.

---

## Task 1: Pattern Inventory  [Effort: 0.25 days]

### What
Build an allow-list of every CSS class the new landing will consume, by reading `landing/style.css` directly and treating `landing/index.html` as the reference application of landing-specific patterns. **Important:** `landing/playground.html` is a web-app component playground — it does not contain `.lede`, `.output-grid`, `.demo-strip`, `.pricing-grid`, or any landing-page patterns. Use `style.css` as the source of truth and `index.html` as the usage reference for those classes.

### Files
- **Modify**: none — this task produces no file output; the allow-list is mental/scratch only.

### Steps
1. Read `landing/style.css` end-to-end and enumerate every class relevant to the epic: masthead, lede, output-grid/output-card, overline, section-heading, headline, steps, demo-strip and its sub-elements, pullquote-row/pullquote-single, pricing, footer.
2. For each class, verify a matching selector exists in `style.css`; mark absent classes as red-flagged and drop the depending section from the plan rather than adding new CSS.
3. Read `landing/index.html` to see how landing-specific patterns (lede, output-grid, demo-strip, pricing) are composed in actual markup — this is the reference application, not the playground.
4. Confirm the demo-strip nesting: `.demo-strip` > `.demo-strip-inner` > `.demo-masthead` + `.demo-body` (which contains `.demo-sidebar` + `.demo-content`).
5. Confirm `.steps` provides `.step-num`, `.step-title`, `.step-body` — and that `.step-code` is intentionally excluded from the allow-list for this epic.
6. Note the output-grid layout: `grid-template-columns: repeat(4, 1fr)` — five cards means the 5th card wraps to a second row. This is accepted behaviour; document it as known.

### Verify
- Every class on the allow-list resolves to a real selector in `landing/style.css`.
- Demo-strip nesting (`.demo-strip-inner`, `.demo-body`) is documented.
- `.step-code` is excluded; the 5-card/4-column grid wrap is acknowledged as accepted.
- `landing/style.css` has not been edited.

---

## Task 2: Masthead + Lede Structure  [Effort: 0.5 days]

### What
Create `landing/landing-v2.html` as a new file and lay down the document shell, masthead, and lede sections so subsequent tasks have a stable skeleton to attach to. The masthead must function as a real `<header>` and the lede must include the two-column structure plus an `.output-grid` of five `.output-card` elements.

### Files
- **Create**: `landing/landing-v2.html` — the new from-scratch landing page; this task seeds it with the document shell, masthead, and lede.

### Steps
1. Create `landing/landing-v2.html` with an HTML5 doctype, `<html>` element, a `<head>` that loads `landing/style.css` exactly the way `landing/index.html` loads it, and a `<title>` reflecting the Spec Doc landing page.
2. Mirror the favicon, meta viewport, and any font preconnect or preload tags that `landing/index.html` declares so typography and theme behavior match the existing landing.
3. In `<body>`, add a `<header>` that uses the masthead pattern from `landing/playground.html` — newspaper title in Playfair, italic tagline in Source Serif, edition label, a placeholder element for the dynamic date label, an anchor nav, and a placeholder element for the theme toggle button (icons added in Task 5).
4. Add the lede section directly after the masthead using `.lede` as the wrapper, `.lede-main` for the headline + deck + primary CTA, `.lede-divider` between columns, and `.lede-aside` for the right column.
5. Inside `.lede-aside`, add an `.output-grid` containing exactly five `.output-card` elements representing the spec artifacts (analysis, epic, architecture, timeline, implementation guide) with placeholder editorial filler that respects the card's typographic shape.
6. Reserve anchor `id` attributes on the lede and on the four upcoming overline sections so the masthead nav has consistent targets when Task 3 fills them in.

### Verify
- `landing/landing-v2.html` exists and renders at `http://localhost:8096/landing-v2.html` with no console errors.
- The masthead is a real `<header>` element with no meta-labels like "here is the masthead" anywhere in copy.
- The lede contains exactly five `.output-card` elements inside a single `.output-grid` and uses `.lede`, `.lede-main`, `.lede-aside`, `.lede-divider`.
- No `style="..."` attributes appear in the file and no new classes are introduced beyond those already in `landing/style.css`.

---

## Task 3: Overline Section Sequence (What / How / See / Start)  [Effort: 0.75 days]

### What
Add the four overline-led major sections — *what it does*, *how it works*, *see it in action*, *start building* — including the three-column `.steps` grid that lives inside the *how it works* section.

**Class note:** `.section-heading` is a Source Sans 11px nav-bar divider (used as a full-width section break). It is NOT a Playfair heading. For an editorial section title use `<h2 class="headline">` (Playfair 44px). The correct pattern per `landing/index.html` is: `.section-heading` bar (full-width divider) followed by the section's editorial content — the `.overline` red flag appears inside the section's body, not above the `.section-heading` bar.

### Files
- **Modify**: `landing/landing-v2.html` — append the four overline sections plus the steps grid after the lede.

### Steps
1. After the lede in `landing/landing-v2.html`, add a section for *what it does* using a `<div class="section-heading">` as the full-width divider bar (matching `index.html` usage), then an `.overline` + `<h2 class="headline">` pair as the editorial opener, followed by body copy.
2. Add a section for *how it works* with the same `.section-heading` divider + `.overline` + `.headline` opening, then nest a three-column `.steps` grid containing exactly three step cells; each cell uses `.step-num`, `.step-title`, and `.step-body` only — explicitly do not include any `.step-code` block or code-mockup chrome.
3. Populate the three steps with placeholder copy that walks the methodology arc (braindump → spec set → implementation) at body-copy weight, keeping each step's body within the line-length envelope visible in the playground.
4. Add a section for *see it in action* with `.section-heading` divider + `.overline` + `.headline` opener; leave space below for the demo strip that Task 4 will insert.
5. Add a section for *start building* with `.section-heading` divider + `.overline` + `.headline` opener; leave space below for the pricing block that Task 4 will insert.
6. Wire the masthead anchor nav targets from Task 2 to the four section `id`s so navigation works without JavaScript.

### Verify
- All four overline sections are present in order; each uses a `.section-heading` divider bar, an `.overline` flag, and an `<h2 class="headline">` title — not `.overline` + `.section-heading` as a pair.
- The steps grid has exactly three cells and contains zero `.step-code` blocks (`grep step-code landing/landing-v2.html` returns no matches).
- Anchor links from the masthead nav resolve to the four sections without console errors.
- Body copy paragraph counts visibly match the playground's overline-section rhythm — no section is empty or oversized.

---

## Task 4: Demo Strip + Pull Quote + Pricing + Footer  [Effort: 0.5 days]

### What
Fill in the page's transactional and proof-point regions: a real spec excerpt rendered in the `.demo-strip` (inside the *see it in action* section), a single editorial pull quote between sections, the pricing block (inside the *start building* section), and the footer that mirrors `landing/index.html`'s footer pattern verbatim.

### Files
- **Modify**: `landing/landing-v2.html` — insert the demo strip, pull quote, pricing block, and footer.

### Steps
1. Inside the *see it in action* section, add a `.demo-strip` with the correct nesting: `.demo-strip` > `.demo-strip-inner` > `.demo-masthead` (first child), then `.demo-body` > `.demo-sidebar` + `.demo-content`. The `.demo-body` element is the three-column grid (`200px 1px 1fr`); without it the sidebar and content will not lay out correctly. Populate with a miniature spec excerpt using only structural markup — no labels like "demo" anywhere in copy.
2. After the *see it in action* section closes, add `<div class="pullquote-row pullquote-single">` (both classes required — `pullquote-single` is the centered single-quote variant; `pullquote-row` alone creates a two-column grid that leaves one column empty). Contain exactly one `.pullquote` with editorial copy about the methodology.
3. Inside the *start building* section, add the pricing block using the playground's pricing pattern: an overline + section-heading already present from Task 3, followed by tier cards and a primary CTA reusing the existing class hooks for those elements.
4. Add a `<footer>` at the end of `<body>` whose markup matches `landing/index.html`'s footer verbatim in structure and class hooks, adjusted only for the placeholder editorial filler rather than the live copy.
5. Re-scan the file for any `style="..."` attributes, `<i data-lucide>` references, `.step-code` blocks, or CDN script/style tags introduced inadvertently and remove anything that surfaces.

### Verify
- The demo strip nesting is `.demo-strip` > `.demo-strip-inner` > `.demo-masthead` + `.demo-body` > `.demo-sidebar` + `.demo-content`; no direct-child shortcuts.
- Exactly one `pullquote-row pullquote-single` element exists; no bare `.pullquote-row` without `pullquote-single`.
- The pricing block lives inside the *start building* section and reuses existing tier-card and primary-CTA classes from `landing/style.css`.
- The footer in `landing/landing-v2.html` matches the structural shape of the footer in `landing/index.html` and the page renders to the bottom without console errors at `http://localhost:8096/landing-v2.html`.

---

## Task 5: Theme Toggle + Date Label Port  [Effort: 0.25 days]

### What
Port the existing theme toggle and date label scripts from `landing/index.html` into `landing/landing-v2.html` verbatim, including the inline sun/moon SVG glyphs the toggle button consumes. No new JavaScript is authored — this is a copy-paste with the toggle and date-label hooks wired to the placeholder elements reserved in Task 2.

### Files
- **Modify**: `landing/landing-v2.html` — add inline sun/moon SVGs into the theme toggle button, copy the theme toggle handler script, and copy the date label population script.

### Steps
1. Open `landing/index.html`, locate the inline sun/moon SVG markup used by its theme toggle button, and copy that markup into the placeholder theme-toggle element reserved in the masthead during Task 2.
2. Locate the theme toggle handler script block in `landing/index.html` and copy it verbatim into `landing/landing-v2.html` at the same relative position (typically just before `</body>`), confirming the element selectors it targets match the masthead toggle button's `id` and class hooks.
3. Locate the date label population script in `landing/index.html` and copy it verbatim into `landing/landing-v2.html` immediately after the theme toggle script, confirming its target element matches the date placeholder reserved in the masthead during Task 2.
4. Reload `http://localhost:8096/landing-v2.html` and click the theme toggle to confirm light/dark switching works and the date label populates on initial load.
5. Confirm no other JavaScript was authored — the only `<script>` blocks in `landing/landing-v2.html` are the two ported ones, and the file loads no CDN scripts beyond what `landing/index.html` already loads.

### Verify
- Theme toggle switches the page between light and dark modes when clicked.
- Date label renders the current date on initial page load with no console errors.
- `grep -c "<script" landing/landing-v2.html` returns `1` — one inline `<script>` block containing the theme toggle and date label, nothing else.
- `landing/index.html` is byte-identical to its pre-epic state and `landing/style.css` is unchanged.