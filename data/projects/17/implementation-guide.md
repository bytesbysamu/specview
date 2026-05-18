# Implementation Guide: landing-polish-newspaper

## Overview
This epic converts the Specview landing page from a brochure into a demonstration by wiring HTML for components the stylesheet already defines: a tagline typography fix, a five-card hero output grid, a demo strip section mirroring the app's newspaper aesthetic, editorial step bodies, and a section-nav/metrics refresh — closed out by a dark-mode parity audit. Tasks 1 and 2 are independent and ship first; Task 3 builds on the hero grid pattern; Task 4 adds the "Demo" nav link only after the demo anchor exists; Task 5 audits all changes against `[data-theme="dark"]` as a final gate before the build verification.

## Shared Pre-flight
- Confirm working directory is the repo root and `landing/index.html` and `landing/style.css` are the only files you intend to edit.
- Open `http://localhost:8096/playground.html` in a browser as the verbatim contract for tokens, component markup patterns, and CSS rule names.
- Run `docker compose up -d landing` and load `http://localhost:8096/` (or the configured landing port) in light and dark themes to capture a baseline.
- Grep `landing/style.css` for `.output-card`, `.output-grid`, `.demo-strip`, `.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content`, `.step-body`, and `.masthead-tagline` to confirm each selector exists before instantiating it in HTML.
- Verify the existing dark-mode rules for each of those selectors are paired with a `[data-theme="dark"]` block so no new dark-mode CSS is required.
- Do not introduce new CSS classes, new font families, inline `style=""` attributes, or new JavaScript — the only `style.css` change in this epic is the tagline rule in Task 1.
- Keep all token references (`var(--body)`, `var(--sans)`, `var(--ink-muted)`, `var(--accent)`, `var(--red)`) consistent with the semantic-color rules from architecture.md — `--red` overlines/errors only, `--accent` interactive only, `--ink-muted` absence-of-state only.
- After every task, rebuild via `docker compose build landing && docker compose up -d landing` and reload the page in both themes before marking it done.

---

## Task 1: Tagline + Step Bodies  [Effort: 0.5 days]

### What
Realign the masthead tagline from `var(--sans)` to `var(--body)` italic so it reads as a newspaper deck rather than a UI label, and insert a one-sentence editorial paragraph above each of the three "How it works" `.step-code` blocks. This is the warm-up task — it ships independent of the hero grid and the demo strip.

### Files
- **Modify**: `landing/style.css` — change the `font-family` declaration inside the `.masthead-tagline` rule from `var(--sans)` to `var(--body)` and ensure `font-style: italic` and `font-size: 13px` remain in effect.
- **Modify**: `landing/index.html` — add a `<p class="step-body">` element above the `.step-code` block in each of the three step columns inside the "How it works" section.

### Steps
1. In `landing/style.css`, locate the `.masthead-tagline` selector and change only its `font-family` value to `var(--body)`, leaving any existing `font-style: italic` and `font-size: 13px` declarations untouched; do not introduce a new selector or override.
2. In `landing/index.html`, find the "How it works" section and identify the three step columns containing the existing `.step-code` blocks.
3. For each step column, insert a `<p class="step-body">` element immediately above its `.step-code` block, with one editorial sentence per step that frames the code mockup as evidence for the step's heading rather than as primary content.
4. Confirm the `.step-body` class is present in `landing/style.css` and that no additional class or wrapper is needed — the markup-only insertion is sufficient.

### Verify
- `docker compose build landing && docker compose up -d landing` succeeds without errors.
- The masthead tagline renders in Source Serif 4 italic at 13px in both light and `[data-theme="dark"]` modes.
- Each of the three "How it works" steps displays exactly one `<p class="step-body">` paragraph above its `.step-code` block.
- No new CSS classes, font families, or inline styles were introduced.

---

## Task 2: Hero Output-Card Grid  [Effort: 1 day]

### What
Replace the flat `<ul>` inside `.lede-aside` with the existing `.output-grid` container holding five `.output-card` instances — one per generated artifact (Analysis, Epic, Architecture, Timeline, Implementation Guide). Each card carries an icon, a Playfair title, a monospace filename, and a body sentence, converting enumeration into demonstration.

### Files
- **Modify**: `landing/index.html` — remove the `<ul>` currently inside `.lede-aside` and insert a `.output-grid` element containing five `.output-card` children, one per generated artifact.

### Steps
1. In `landing/index.html`, locate the `.lede-aside` element in the hero and identify the existing `<ul>` and its list items so the entire flat list can be replaced as a unit.
2. Replace the `<ul>` with a single `.output-grid` container element using the same selector name as the existing CSS rule, with no additional wrapper or modifier classes.
3. Inside `.output-grid`, instantiate five `.output-card` elements in document order — Analysis, Epic, Architecture, Timeline, Implementation Guide — each composed of: an icon element, a Playfair-rendered title, a monospace filename element, and a one-sentence body.
4. Set the filename strings to `analysis.md`, `epic.md`, `architecture.md`, `timeline.md`, and `implementation-guide.md` so each card maps to the actual artifact path used in the project pipeline.
5. Use simple inline SVG icons consistent with editorial weight (no shadows, no new color tokens), keeping stroke colors on existing semantic tokens so the dark-mode override picks them up automatically.
6. Confirm no inline styles are added on the cards and no new classes are introduced — `.output-grid` and `.output-card` are the only selectors used.

### Verify
- The hero aside renders five `.output-card` elements in the existing 2-column `.output-grid` layout in both themes.
- Each card displays an icon, a Playfair title, a monospace filename, and a body sentence.
- Hover state on each card matches the existing CSS rule and remains visible in `[data-theme="dark"]`.
- `docker compose build landing && docker compose up -d landing` succeeds and the page shows no console errors.

---

## Task 3: Demo Strip Section  [Effort: 1.5 days]

### What
Render the existing `.demo-strip` component as a new section between "How it works" and "Pricing", composed of `.demo-masthead`, `.demo-body`, `.demo-sidebar`, and `.demo-content` sub-elements that miniaturize the app's newspaper layout inside the marketing page. This is the highest-conversion change because it collapses the gap between marketing aesthetic and product aesthetic.

### Files
- **Modify**: `landing/index.html` — insert a new `<section id="demo">` containing the `.demo-strip` component and its four sub-elements between the "How it works" section and the "Pricing" section.

### Steps
1. In `landing/index.html`, locate the closing tag of the "How it works" section and the opening tag of the "Pricing" section to position the new demo section between them.
2. Insert a `<section>` element with `id="demo"` so the future "Demo" nav link in Task 4 has an anchor target, and place the `.demo-strip` element as its primary child.
3. Inside `.demo-strip`, compose `.demo-masthead` first (a miniaturized newspaper masthead echoing the app's masthead), then a `.demo-body` element that contains both `.demo-sidebar` and `.demo-content` as siblings.
4. Populate `.demo-masthead` with a stylistic mock — a newspaper-style title and tagline pattern — without copying live app strings, so the demo functions as a stylistic mock rather than a screenshot of current state.
5. Populate `.demo-sidebar` with a short list of artifact-style entries that visually echo the output cards from Task 2, and populate `.demo-content` with a representative editorial body and headline pattern matching newspaper rhythm.
6. Use only the existing `.demo-strip`, `.demo-masthead`, `.demo-body`, `.demo-sidebar`, and `.demo-content` selectors — no inline styles, no new classes, no new font families.
7. Verify the section flows visually under "How it works" and above "Pricing" in both themes, and that anchor scrolling to `#demo` lands at the section start.

### Verify
- A `.demo-strip` section appears between "How it works" and "Pricing" in the rendered DOM, with `id="demo"` on its outer `<section>`.
- The mock displays a `.demo-masthead`, `.demo-sidebar`, and `.demo-content` with newspaper-style content in both light and dark themes.
- Navigating to `#demo` via the URL hash scrolls to the section.
- `docker compose build landing && docker compose up -d landing` succeeds with no console errors and no responsive overflow at 768px width or above.

---

## Task 4: Section Nav + Metrics Refresh  [Effort: 0.5 days]

### What
Add a fourth "Demo" link to the section nav so nav and content stay in sync after Task 3, and update the metrics bar (tests / commits / projects) to reflect current repository counts. Both are content-only edits with no structural impact.

### Files
- **Modify**: `landing/index.html` — insert a "Demo" link into the section nav targeting `#demo`, and update the three numeric values in the metrics bar to match current repository counts.

### Steps
1. Run a fresh count against the repository for tests (test file or test case count, whichever the existing metric tracks), commits (`git rev-list --count HEAD` against the main branch), and projects (count of project directories under the projects root) to determine the new values.
2. In `landing/index.html`, locate the section nav and add a fourth `<a>` element with `href="#demo"` and the visible text "Demo", placed in document order between "How it works" and "Pricing" so the nav order matches the section order on the page.
3. In `landing/index.html`, locate the metrics bar and update each of the three numeric values in place — do not change the surrounding markup, labels, or class names.
4. Confirm the nav remains visually balanced at four items in both themes and that no new CSS rule is required for the four-link layout — the existing rule must hold.

### Verify
- The section nav contains four links (What / How it works / Demo / Pricing) in that order, visually balanced in both themes.
- Clicking the "Demo" link scrolls to the `#demo` section anchor added in Task 3.
- The metrics bar shows current tests / commits / projects counts.
- `docker compose build landing && docker compose up -d landing` succeeds and no console errors appear on load.

---

## Task 5: Dark-Mode Parity Audit  [Effort: 0.5 days]

### What
Verify every new or modified element from Tasks 1–4 against `[data-theme="dark"]` for border contrast, hover-state visibility, icon stroke legibility, and text contrast. This is a verification gate, not a coding task — failures route back into the original component, not into new dark-mode-specific CSS.

### Files
- **Modify**: `landing/index.html` and/or `landing/style.css` — only if the audit surfaces a failure that requires correcting the original markup or tagline rule; no new dark-mode rules are added.

### Steps
1. Build and serve the landing locally via `docker compose build landing && docker compose up -d landing` and load the page in a browser.
2. Toggle to `[data-theme="dark"]` using the existing theme toggle and walk the page top-to-bottom checking the masthead tagline, the `.output-card` grid (default and hover states), each `.step-body` paragraph, the `.demo-strip` section (masthead, sidebar, content), the four-item section nav, and the metrics bar.
3. For each element, confirm border contrast, hover-state visibility, icon stroke legibility, and text contrast match the light-mode counterpart and that no `--ink-muted` text reads as missing-content where state is intended.
4. If any failure is found, route the fix back into the original task's component — adjust the HTML structure or, in the tagline case only, the existing CSS rule — rather than authoring new dark-mode-specific overrides.
5. Repeat the walk in light mode after any fix to confirm parity holds in both directions before signing off.

### Verify
- All five components (tagline, output cards, step bodies, demo strip, nav + metrics) render correctly in `[data-theme="dark"]` with no contrast or hover regressions versus light mode.
- No new `[data-theme="dark"]` rules were added to `landing/style.css` during the audit.
- `docker compose build landing && docker compose up -d landing` succeeds and the browser console is clean in both themes.
- All success criteria from the epic are observable on the rendered page in both themes.