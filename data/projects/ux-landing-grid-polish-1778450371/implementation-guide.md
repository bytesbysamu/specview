# Implementation Guide: UX: Landing & Grid Polish

## Overview
This epic closes the remaining mockup-to-production gaps across two surfaces — the Angular app's CSS and the static landing page HTML — without introducing new components, classes, or Angular template changes. After code inspection, most tasks described in the original braindump are already shipped; the net remaining work is two targeted edits (overline color/size fix in the app stylesheet and teaser character window expansion in the API service). Tasks 1 and 2 have no dependencies and can run in parallel. Task 4 depends on Task 3. Task 5 is independent and can run alongside any other task.

## Shared Pre-flight
- Confirm the design-reference mockup at `landing/app-overview.html` is accessible and reflects the validated visual decisions
- Verify CSS custom-property tokens (`--border`, `--ink-muted`, `--red`, `--body`, `--sans`) are defined in both `web-ng/src/styles.css` and `landing/style.css`
- Ensure the Angular dev server starts cleanly with `ng serve` from `web-ng/`
- Open the landing page locally (static file serve from `landing/`) to confirm baseline rendering
- Confirm `api/modules/data/projects/service.py` is reachable and the `_read_specs` function is at approximately line 101
- Review the locked design-decisions table in the architecture doc — grid min-width, card padding, and color philosophy values are non-negotiable and must not be altered
- Have at least one braindump-heavy test project available whose first prose sentence falls between characters 300 and 500, for verifying Task 2

---

## Task 1: App CSS Alignment  [Effort: 0.5 days]

### What
Fixes the `.overline` base color in the app stylesheet so section-group headers render in muted grey instead of marketing red, and reduces the font size from 11px to 9px to match the validated mockup's micro-label treatment. The `.section-count` pill badge and `.masthead-tagline` font were verified as already correct during architecture review — no changes needed for those. The `.file-item-meta-sep` / `.sep` class name should be checked for consistency and normalized if divergent.

### Files
- **Modify**: `web-ng/src/styles.css` — change the `.overline` rule's `color` from `var(--red)` to `var(--ink-muted)` and `font-size` from `11px` to `9px`

### Steps
1. Open `web-ng/src/styles.css` and locate the `.overline` rule block.
2. Change the `color` property value from `var(--red)` to `var(--ink-muted)`.
3. Change the `font-size` property value from `11px` to `9px` to match the mockup's micro-label specification.
4. Confirm that `landing/style.css` has its own `.overline` rule that independently sets `color: var(--red)` and `font-size: 11px` for the marketing context — this file is separate and should not be touched.
5. Search `web-ng/src/styles.css` for both `.file-item-meta-sep` and `.sep` selectors. If both exist with identical rules, consolidate to one canonical class name. If only one exists, confirm the templates reference the matching name.
6. Verify that `.section-count` already has `background: var(--border)`, `border-radius: 2px`, and `padding: 1px 5px` — no change expected, just confirmation.

### Verify
- Run `ng build --configuration production` from `web-ng/` and confirm zero errors
- Serve the app locally, navigate to a project with multiple sections, and confirm overline text above section groups renders in muted grey at 9px — not red at 11px
- Confirm nav count badges still render as grey pills (no regression from the overline change)
- Open `landing/index.html` in a browser and confirm the landing page overlines still render in red — no cross-file contamination

---

## Task 2: Teaser Window Expansion  [Effort: 0.5 days]

### What
Increases the teaser character window from 300 to 500 in the API service layer so that braindump-heavy projects whose first real prose sentence begins after character 300 surface a meaningful teaser instead of falling back to empty or symbol-only text.

### Files
- **Modify**: `api/modules/data/projects/service.py` — change the `teaser_chars` argument from `300` to `500` in the `_read_specs` call

### Steps
1. Open `api/modules/data/projects/service.py` and locate the line (approximately line 101) where `_read_specs` is called with `teaser_chars=300`.
2. Change the literal `300` to `500`.
3. Confirm that `_read_specs` uses a simple `content[:teaser_chars]` slice internally and that no other code path references or constrains this value.

### Verify
- Run the API test suite to confirm no regressions
- Start the API server and issue a `GET /api/projects` request for a project whose braindump starts with headings and bullets — confirm the teaser field now contains real prose rather than markdown symbols or empty text
- Confirm the JSON payload size increase is negligible (at most ~4KB for a 20-project list)

---

## Task 3: Landing: Output Card Grid & Step Bodies  [Effort: 1 day]

### What
Replaces the flat unordered list in the hero's `.lede-aside` with five `.output-card` elements arranged in the `.output-grid`, and adds `<p class="step-body">` editorial paragraphs above each `.step-code` block in the "How it works" section. Architecture review confirmed these elements are already wired in the current `landing/index.html` — this task requires verification only, not new markup.

### Files
- **Modify**: `landing/index.html` — verify that the `.lede-aside` contains an `.output-grid` wrapper with five `.output-card` children (Analysis, Epic, Architecture, Timeline, Implementation Guide) and that each "How it works" step has a `<p class="step-body">` element above its `.step-code` block

### Steps
1. Open `landing/index.html` and locate the `.lede-aside` element within the hero section.
2. Confirm it contains a container with the class `.output-grid` and exactly five child elements each carrying the class `.output-card`, with labels matching: Analysis, Epic, Architecture, Timeline, and Implementation Guide.
3. Scroll to the "How it works" section and confirm each of the three steps contains a `<p class="step-body">` paragraph positioned above the corresponding `.step-code` block.
4. If any element is missing or misnamed, add or correct it using the existing CSS classes defined in `landing/style.css` — do not invent new classes.
5. Cross-reference the card labels and step-body copy against the content in `landing/app-overview.html` to ensure editorial consistency.

### Verify
- Open `landing/index.html` in a browser and confirm five output cards render in a grid layout within the hero aside, not as a bulleted list
- Confirm each "How it works" step shows a prose sentence above its code mockup block
- Inspect the DOM and confirm no new CSS classes were introduced — only existing `.output-grid`, `.output-card`, and `.step-body` classes are used
- Resize the browser to mobile width and confirm the card grid and step bodies reflow gracefully

---

## Task 4: Landing: Demo Strip & Section Nav  [Effort: 1 day]

### What
Wires the `.demo-strip` HTML section between the "How it works" and "Pricing" sections and adds a fourth section-nav link ("Demo") pointing to the new section's anchor. Architecture review confirmed these elements are already present in the current `landing/index.html` — this task requires verification only, not new markup.

### Files
- **Modify**: `landing/index.html` — verify that the `.demo-strip` section exists between "How it works" and "Pricing", and that the section nav contains a fourth link targeting the demo section's anchor

### Steps
1. Open `landing/index.html` and locate the "How it works" section and the "Pricing" section.
2. Confirm a section with the class `.demo-strip` exists in the DOM between these two sections, containing child elements with classes `.demo-masthead`, `.demo-body`, `.demo-sidebar`, and `.demo-content`.
3. Locate the section navigation (typically a `<nav>` or list of anchor links at the top of the page) and confirm it contains exactly four links, with the fourth being "Demo" and its `href` pointing to the demo strip section's `id`.
4. If the demo strip section or the nav link is missing, insert it using the existing CSS classes from `landing/style.css` and populate the demo content by referencing `landing/app-overview.html`.

### Verify
- Open `landing/index.html` in a browser and scroll to confirm the demo strip appears between "How it works" and "Pricing"
- Click the "Demo" link in the section nav and confirm smooth scroll to the demo strip section
- Confirm the demo strip renders with the masthead, sidebar, and content areas laid out according to the existing CSS grid rules
- Confirm all four section nav links are visible and functional

---

## Task 5: Masthead Tagline Font  [Effort: 0.5 days]

### What
Ensures the `.masthead-tagline` element renders in Source Serif 4 italic at 13px by using `font-family: var(--body)` instead of `var(--sans)`. Architecture review confirmed this rule is already correct in `landing/style.css` — this task requires verification only.

### Files
- **Modify**: `landing/style.css` — verify that the `.masthead-tagline` rule uses `font-family: var(--body)`, `font-size: 13px`, and `font-style: italic`

### Steps
1. Open `landing/style.css` and locate the `.masthead-tagline` rule block (approximately lines 132–137).
2. Confirm the `font-family` property is set to `var(--body)`, not `var(--sans)`.
3. Confirm `font-size` is `13px` and `font-style` is `italic`.
4. If any value is incorrect, update it to match the specification. Do not change `color: var(--ink-light)` or any other property in this rule.

### Verify
- Open `landing/index.html` in a browser and inspect the masthead tagline element
- Confirm the computed font family resolves to Source Serif 4 (or the font mapped to `--body`), not Source Sans 3
- Confirm the text renders in italic at 13px with the muted ink color