# Implementation Guide: Landing Phase 3 — Pure HTML Extraction

## Overview
This epic replaces the non-compliant `landing-v2.html` with a single `index.html` that uses only existing `landing/style.css` classes and hardcoded content extracted from `web-ng/src/app/pg-landing-data.ts`. The work sequences as: first audit the stylesheet to confirm class availability and extract content (Task 1), then author the above-the-fold HTML (Task 2) and below-the-fold HTML (Task 3) in parallel against the audit's class map, and finally validate compliance and dark mode correctness (Task 4) once all markup is in place.

## Shared Pre-flight
- Confirm that `landing/style.css` is the canonical stylesheet and note its line count and class inventory structure
- Confirm deployment topology: the `landing/` directory is served by an nginx:alpine container as static files
- Identify the existing breakpoints defined in `style.css` (expected at 768px and 1100px)
- Open `web-ng/src/app/pg-landing-data.ts` and note the exported arrays: output cards, comparison rows, FAQ items, pricing features, how-it-works steps
- Decide the open question on filename: output will be `landing/index.html` per success criteria; verify nginx config serves it at the root route
- Decide CTA target URL (e.g. `/generate`) so links can be hardcoded consistently
- Confirm the three permitted Google Fonts families and weights referenced in the existing font import
- Ensure a browser is available for manual dark mode and responsive verification in Task 4

---

## Task 1: Style.css Audit & Content Extraction  [Effort: 0.5 days]

### What
Audit every class in `landing/style.css` and produce a section-to-class mapping that proves each planned section (masthead, hero, stat strip, output cards, how-it-works, comparison table, pricing, FAQ, footer) can be built with existing vocabulary. Simultaneously extract the curated content subset from `pg-landing-data.ts` that will be hardcoded into the HTML. This task is the feasibility gate — any section without a verified class mapping gets redesigned or dropped before HTML authoring begins.

### Files
- **Create**: `landing/class-map.md` — documents the verified mapping of each section to its concrete `style.css` class names, responsive behavior, and dark mode token usage
- **Modify**: none (this task is research output only; the class map is a reference artifact consumed by Tasks 2 and 3)

### Steps
1. Read `landing/style.css` top to bottom and catalog every class name grouped by category: layout containers, typography, structural elements (borders, separators), interactive states, and responsive overrides.
2. For each of the nine planned sections (masthead, hero/lede, stat strip, output cards, how-it-works, comparison table, pricing, FAQ, footer), identify the specific classes that handle its layout pattern, heading hierarchy, body text, and border/separator treatment.
3. Verify responsive behavior for each mapping by tracing the class through media query blocks at 768px and 1100px breakpoints — confirm the existing rules produce acceptable reflow without new CSS.
4. Confirm every color used in the mapped classes resolves through CSS custom properties (`--ink`, `--bg`, `--border`, `--red`, `--accent`) and has a corresponding `[data-theme="dark"]` override already defined.
5. Open `web-ng/src/app/pg-landing-data.ts` and identify which items from each array (output cards, comparison rows, FAQ items, pricing tiers, how-it-works steps) survive the editorial filter — items must advance the 30-second comprehension goal.
6. Write the section-to-class mapping into `landing/class-map.md` with one section per heading, listing container class, child element classes, typography classes, and any responsive notes.
7. Flag any section where a complete class mapping cannot be established and make the architectural call: simplify the section design or remove it.

### Verify
- `landing/class-map.md` exists and contains a mapping entry for every section that will ship
- Every class name referenced in the map can be found verbatim in `landing/style.css` (search confirms zero invented classes)
- The extracted content subset from `pg-landing-data.ts` is noted per section — no array is used in full without editorial justification
- Any dropped or redesigned sections are documented with rationale in the class map

---

## Task 2: Above-the-Fold HTML (Masthead → Stat Strip)  [Effort: 1 day]

### What
Author the top three sections of `landing/index.html` — the masthead (brand identity and navigation), the hero/lede (headline, deck, and static file list), and the stat strip (four key metrics). These sections must load and communicate the core proposition ("paste braindump, get specs, free") before the visitor scrolls.

### Files
- **Create**: `landing/index.html` — the complete HTML document skeleton including doctype, head (meta, font import, stylesheet link), and the first three body sections
- **Modify**: none (this is the initial creation of the file; Task 3 appends below-the-fold sections)

### Steps
1. Create the HTML5 document structure with doctype, lang attribute, head containing charset meta, viewport meta, title, the Google Fonts import link for Playfair Display, Source Serif 4, and Source Sans 3, and a link to `style.css`.
2. Build the masthead section using the container class identified in the class map for max-width centering, flex for horizontal layout, the largest Playfair heading class for the brand name, and a border-bottom class for the newspaper rule separator.
3. Build the hero/lede section using the two-column grid class at desktop. In the left column, place the overline class element, the h1 headline using the mapped heading class, and a deck paragraph using the identified body text class. In the right column, place a bordered container with a monospace-styled list of five filenames, one marked with a static "Generating..." text label.
4. Build the stat strip section as a four-item flex row using the mapped layout class, with border-right separators between items. Use the Playfair heading class for the numeric values and the sans-serif label class for descriptors. Content for the four stats comes from the extraction done in Task 1.
5. Add the dark mode toggle script at the end of the body — approximately ten lines of vanilla JavaScript that reads localStorage for theme preference, sets the `data-theme` attribute on the document element, and provides a toggle function bound to a button in the masthead.
6. Validate that no inline styles, no hardcoded color values, no border-radius, and no box-shadow appear anywhere in the authored markup.

### Verify
- `landing/index.html` exists with a valid HTML5 structure and renders the masthead, hero, and stat strip when opened in a browser with `style.css` available
- The document head contains exactly one stylesheet link (to `style.css`) and one Google Fonts link
- Grep the file for `style=`, `border-radius`, `box-shadow`, and hardcoded hex/rgb values — all return zero matches
- The dark mode toggle button switches the theme and persists the choice across page reload

---

## Task 3: Below-the-Fold HTML (Cards → Footer)  [Effort: 1 day]

### What
Append the remaining six sections to `landing/index.html` — output cards, how-it-works, comparison table, pricing tiers, FAQ, and footer. These sections provide progressive detail for visitors who scroll past the fold and complete the page's persuasion arc from "what ships" through "how much" to "common questions."

### Files
- **Modify**: `landing/index.html` — append six new section blocks after the stat strip and before the closing body/script tags

### Steps
1. Build the output cards section using the grid container class from the class map with the defined column count (three columns desktop, responsive reflow). Create five card elements each using the bordered container class, a heading for the filename, and muted text class for the one-line description. Content comes from the curated subset of the output cards array identified in Task 1.
2. Build the how-it-works section using a three-item layout (grid or flex as identified in the audit). Each item gets the largest Playfair heading class for the step number, standard paragraph class for the explanation, and a background-token container with reduced-size text class for the representative excerpt. Limit to three steps for budget compliance.
3. Build the comparison table using a native HTML table element with the existing table classes for header row styling, row borders, and cell typography. Three columns: dimension label, spec-doc value, and competitors value (muted class). Six rows extracted from the comparison rows array in `pg-landing-data.ts`.
4. Build the pricing section as a two-column grid. The Free tier and Pro tier each use a bordered container class, heading hierarchy for tier name and price, and a list of features. The CTA button in each tier uses the existing button or link class identified in the audit, pointing to the decided CTA target URL.
5. Build the FAQ section as a vertical stack of native details/summary elements. Each summary uses the Playfair heading class; the expanded content uses standard body text class. Place a bottom border between items using the separator class. Include three to five items from the FAQ array — enough to address top objections without exceeding the line budget.
6. Build the footer as a centered container with muted text class, a horizontal list of links (app link, GitHub if applicable, contact) with separator characters between them, and a copyright line.
7. Count total lines in `landing/index.html` and verify the file remains at or under 300 lines. If over budget, compress the FAQ item count or how-it-works excerpt length until compliant.

### Verify
- `landing/index.html` contains all nine sections (masthead, hero, stat strip, output cards, how-it-works, comparison table, pricing, FAQ, footer) rendering correctly in a browser
- The file is at or under 300 lines (confirm with `wc -l landing/index.html`)
- The comparison table has six rows and three columns with correct content from `pg-landing-data.ts`
- The FAQ details/summary elements open and close natively without JavaScript

---

## Task 4: Compliance Validation & Dark Mode Verification  [Effort: 0.5 days]

### What
Perform a full compliance audit of the finished `landing/index.html` against every success criterion in the epic: zero design system violations, correct font usage, token-only colors, dark mode correctness, responsive behavior at both breakpoints, and sub-second load performance. This task is the quality gate before the page ships.

### Files
- **Modify**: `landing/index.html` — fix any violations discovered during the audit (inline style remnants, incorrect class names, color issues, line count overruns)

### Steps
1. Search the entire file for prohibited patterns: any `style=` attribute, any `border-radius` value, any `box-shadow` value, any hardcoded color (hex codes, rgb/rgba values, named colors other than `inherit` or `currentColor`). Fix every occurrence by replacing with the appropriate class or token reference.
2. Verify font usage by searching for any font-family declaration outside of `style.css` and confirming that only Playfair Display, Source Serif 4, and Source Sans 3 appear in the Google Fonts import. No fourth font family may be referenced anywhere.
3. Cross-reference every class name used in `index.html` against `landing/style.css` — confirm that no class is used that does not exist in the stylesheet. Remove or replace any orphaned classes.
4. Open the page in a browser, activate dark mode via the toggle, and visually inspect every section for contrast failures, invisible text, or borders that disappear against the dark background. Every color must resolve through tokens that have `[data-theme="dark"]` overrides.
5. Resize the browser to 1100px width and verify tablet layout: grids reflow to expected column counts, the hero remains legible, and no horizontal overflow appears. Then resize to 768px and verify mobile layout: all grids single-column, hero stacked vertically, table scrollable if needed.
6. Measure page load performance by opening the page with browser DevTools Network tab on a throttled connection (Fast 3G). Confirm total transfer size is HTML plus one CSS file plus one font request, and that first contentful paint occurs under one second on that throttle.
7. Perform a final line count and confirm the file is at or under 300 lines. If any fixes pushed it over, compress content until compliant.

### Verify
- `grep -c 'style=' landing/index.html` returns 0
- `grep -c 'border-radius' landing/index.html` returns 0 and `grep -c 'box-shadow' landing/index.html` returns 0
- Dark mode toggle produces correct theme in all nine sections with no contrast failures visible on manual inspection
- `wc -l landing/index.html` reports 300 or fewer lines and the page loads in under one second on simulated Fast 3G