# Analysis: UX — Landing & Grid Polish

## The Problem

The app-ui-mockups project validated design decisions in `landing/app-overview.html`. Most decisions were applied to `web-ng/src/styles.css`, but specific gaps remain between the static mockup and the live application. In parallel, the landing page (`landing/index.html`) needs to adopt the same grid and editorial improvements validated in the mockup. This project closes both gap sets in a single focused pass.

---

## Problem Inventory

### App CSS Gaps

**Gap 1 — Section count badge styling (`.section-count`)**

The mock renders section count badges as grey pill badges: `background: var(--border); border-radius: 2px; padding: 1px 5px`. The live app renders `.section-count` as plain text with `opacity: 0.7; margin-left: 2px`. This makes counts read as muted annotations rather than structured data labels. The pill badge communicates "curated count in a named slot"; plain muted text communicates "faded footnote." Every section header is affected simultaneously.

**Gap 2 — Overline color in app context (`.overline`)**

The base `.overline` class is set to `color: var(--red); font-size: 11px` for the landing page (marketing emphasis — correct there). The mock uses `font-size: 9px; color: var(--ink-muted)` for section header overlines in the app — muted micro-labels, not marketing emphasis. The app's `.section-group-title` has its own color via `--section-color`, but if the base `.overline` rule bleeds through in any app context, the result is red overlines in a tool that should feel neutral and editorial. The app is a tool, not a publication — overlines should provide quiet structure above section headers, not steal attention.

**Gap 3 — Teaser window too narrow (300 → 500 chars)**

The `spec.teaser` field is built by `firstNonHeadingSentence()`, which skips lines beginning with `#`, `-`, `*`, `>`, or `|`. Many braindumps open with a markdown title, then a subheading, then a list — the first prose sentence may arrive after character 300 in the raw string, causing the teaser to return an empty fallback instead of real content. `teaser_chars=300` in `api/modules/data/projects/service.py` needs to increase to 500. Empty teasers break the newspaper illusion — "UI with missing data" not "editorial layout."

**Gap 4 — Class name inconsistency (`.file-item-meta-sep` vs `.sep`)**

The app uses `.file-item-meta-sep` for the separator glyph between metadata items. The mock uses `.sep`. Styling is identical; naming diverges. Not a visual issue but it makes mock-to-app diffs harder and indicates implementation drift.

**Gap 5 — Status bar placement (fixed bottom vs inline)**

The live app renders `.gen-status-bar` as `position: fixed; bottom: 0; left: 0; right: 0; z-index: 2000` — a floating overlay visible only during active generation. The mock places it as `position: relative` in normal page flow, between the section nav and the search bar, always visible. The idle state shows a green "idle — ready" indicator. The inline placement communicates "live newsroom ticker" as part of the editorial structure. The fixed-bottom placement communicates "web app notification overlay." This is the highest-impact remaining perceptual change — the status bar moving inline gives the app its live newsroom quality. The change requires both a CSS change in `web-ng/src/styles.css` and a DOM relocation in `web-ng/src/app/app.component.html`.

### Landing Page Gaps

**Gap 6 — Output card grid not wired**

The `.lede-aside` hero section contains a flat `<ul>` listing the five deliverable types. CSS classes `.output-grid` and `.output-card` already exist in `landing/style.css` from the `landing-polish-newspaper` architecture. The HTML in `landing/index.html` has not been updated — the deliverables are not rendered as cards.

**Gap 7 — Demo strip section not wired**

A miniaturized newspaper-style app UI mockup section (`.demo-strip`) is specified to appear between "How it works" and "Pricing". CSS classes exist: `.demo-strip`, `.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content`. The HTML section has not been written into `landing/index.html`.

**Gap 8 — Step editorial bodies missing**

The "How it works" 3-column section goes directly from step heading to `.step-code` block, creating an abrupt rhythm. A `<p class="step-body">` sentence above each code block adds the editorial transition the design requires. The `.step-body` class is already styled in `landing/style.css`.

**Gap 9 — Masthead tagline font (landing)**

`.masthead-tagline` in `landing/style.css` uses `font-family: var(--sans)` (Source Sans 3 italic). The correct value per the newspaper editorial decision is `font-family: var(--body)` (Source Serif 4, 13px italic) — an editorial deck, not a UI label.

**Gap 10 — Section nav missing "Demo" link**

The landing page section nav has three links. After the demo strip section is added, a fourth nav link ("Demo") pointing to the new section must be added.

---

## Constraints

- All CSS classes for output cards, demo strip, step bodies, and masthead tagline already exist in `landing/style.css` — this is HTML wiring and single-property CSS changes only, not new design work.
- `web-ng/src/styles.css` `.overline` changes must be scoped to not break the landing page's intentional use of red overlines for marketing.
- Status bar relocation requires coordinated changes: `web-ng/src/styles.css` (position change) and `web-ng/src/app/app.component.html` (DOM relocation between nav and search bar). The Angular component must always render the status bar, including in idle state.
- `teaser_chars` change is a backend-only edit; no frontend or migration work required.
- The hero grid (`2fr 1fr 1fr` Active section layout) is explicitly deferred — it requires Angular template changes to detect section type and apply a different grid template column count. Out of scope for this project per the locked design decisions table.
- Class name unification (`.file-item-meta-sep` → `.sep`) is cosmetic and lower priority. In scope only if effort permits.

---

## Open Questions

1. **`.overline` bleed-through in Angular templates**: Are there app contexts where `.overline` is used outside of `.section-group-title`? A search of Angular templates for direct usage of the `.overline` class is required before altering the base rule to determine whether a scoped override is needed.

2. **Status bar Angular component structure**: Does `app.component.html` currently wrap the status bar in a conditional `@if` that hides it when no job is running? The idle state requires always-on rendering. The Angular component's idle rendering path needs to be confirmed before DOM relocation.

3. **Demo strip content**: The demo strip uses `.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content` but the specific editorial copy populating each area is not specified in the braindump. Implementer writes copy consistent with the Specview narrative and cross-references `landing/app-overview.html` for tone.

4. **Step body copy**: The three "How it works" steps need one editorial sentence each above the code block. Exact sentences are not specified. Implementer writes copy consistent with existing step headings.

5. **Output card display format**: The 5 output cards (Analysis, Epic, Architecture, Timeline, Implementation Guide) — icon characters, step numbers, or label-only? Implementer follows the existing `.output-card` CSS class definition in `landing/style.css`.

---

## Dependencies

| Dependency | Required By | Status |
|---|---|---|
| `.output-grid` / `.output-card` CSS in `landing/style.css` | Gap 6: Output card grid | Already exists |
| `.demo-strip` / `.demo-*` CSS in `landing/style.css` | Gap 7: Demo strip | Already exists |
| `.step-body` CSS in `landing/style.css` | Gap 8: Step bodies | Already exists |
| `.gen-status-bar` CSS in `web-ng/src/styles.css` | Gap 5: Status bar | Exists, needs position change |
| `app.component.html` DOM structure | Gap 5: Status bar | Must be read before editing |
| `api/modules/data/projects/service.py` line ~101 | Gap 3: Teaser chars | Exists, needs value change |

---

## Explicitly Out of Scope

- **Hero grid `2fr 1fr 1fr` for Active section** — Deferred. Requires Angular template logic to detect section type and switch grid columns. Excluded per the locked design decisions table.
- **Class name unification (`.file-item-meta-sep` → `.sep`)** — Cosmetic. Deferred unless effort permits; a rename touches Angular templates and carries refactor risk.
- **Dark mode new work** — Changes use existing dark-mode-aware CSS custom properties only.
- **Mobile/responsive changes** — Not in scope. Existing responsive behavior is not intentionally changed.
- **Angular component refactoring** — Status bar placement change is DOM relocation + CSS, not a component logic refactor.
- **New CSS design work** — All CSS classes referenced here already exist. No new design decisions required.
- **E2E test updates** — Visual changes do not alter application behavior flows tested by e2e.
