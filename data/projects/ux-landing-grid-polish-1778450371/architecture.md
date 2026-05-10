# Architecture: UX — Landing & Grid Polish

## Overview

Two independent surfaces — the Angular app (`web-ng/`) and the static landing page (`landing/`) — each receive targeted CSS and HTML edits to match the validated mockup design. The app and landing page have separate stylesheets (`web-ng/src/styles.css` vs `landing/style.css`) so changes to one do not affect the other. The API receives one constant change (`teaser_chars`). No new components, no new services, no new files beyond HTML markup additions.

## Design Principles

| Principle | Application |
|---|---|
| **Dieter Rams + newspaper** | Typography does the heavy lifting. Borders and whitespace create structure. Shadows do not exist (one modal exception). Density without clutter. |
| **State not category** | Color communicates current operational state (running/done/error/idle), never section taxonomy. Category comes from position and grouping. |
| **Playground is the contract** | All component values copy verbatim from `playground.html`. No values are derived or invented. |
| **No speculative abstractions** | Each change fixes one specific gap. No new CSS systems, no wrapper components, no configuration. |

## Component Design

### Status Bar Relocation (App)

**Current:** `position: fixed; bottom: 0; left: 0; right: 0; z-index: 2000`. Only visible during generation.

**Target:** `position: relative`. Inline flow between section nav and search bar. Always visible — idle state shows green `#1a6b30` with "idle — ready" text.

**CSS change** (`web-ng/src/styles.css`):
```css
.gen-status-bar {
  /* Remove: position: fixed; bottom: 0; left: 0; right: 0; z-index: 2000; */
  position: relative;
  color: #fff;
  font-family: 'Source Sans 3', sans-serif;
  font-size: 12px;
  letter-spacing: 0.03em;
  overflow: hidden;
}
```

**Template change** (`web-ng/src/app/app.component.html`):
Move the `.gen-status-bar` element from its current position to immediately after `.section-nav` and before `.search-bar`. Remove any `@if` that hides the bar when idle — it should always render.

### Section Count Pill Badges (App)

**Current:** `.section-count { font-size: 9px; opacity: 0.7; margin-left: 2px; }`

**Target:**
```css
.section-count {
  font-size: 9px;
  background: var(--border);
  border-radius: 2px;
  padding: 1px 5px;
  color: var(--ink-muted);
  font-weight: 400;
}
```

### Overline Override (App)

**Current:** `.overline { font-size: 11px; color: var(--red); }` — shared between landing (correct) and app (wrong).

**Target:** In `web-ng/src/styles.css` only, override to `font-size: 9px; color: var(--ink-muted)`. Landing keeps `var(--red)` in its own `landing/style.css`.

### Teaser Window (API)

**Current:** `teaser_chars=300` in `api/modules/data/projects/service.py`.

**Target:** `teaser_chars=500`. Ensures `firstNonHeadingSentence()` has enough text to find a prose sentence past markdown headings and lists.

### Output Card Grid (Landing)

Replace the `<ul>` in `.lede-aside` with 5 `.output-card` elements:
- Analysis, Epic, Architecture, Timeline, Implementation Guide
- Each card: icon (Unicode glyph), Playfair title, monospace filename, body sentence
- Uses existing `.output-grid` / `.output-card` CSS from `landing/style.css`

### Demo Strip (Landing)

New section between "How it works" and "Pricing". Composes:
- `.demo-strip` container
- `.demo-masthead` — miniaturized newspaper masthead
- `.demo-body` — flex container
- `.demo-sidebar` — file list mock
- `.demo-content` — markdown content mock

All CSS classes already exist in `landing/style.css`.

### Step Bodies (Landing)

Add `<p class="step-body">` above each `.step-code` in the "How it works" 3-column section. One editorial sentence per step. Class already styled.

### Masthead Tagline Font (Landing)

**Current:** `.masthead-tagline { font-family: var(--sans); }`

**Target:** `font-family: var(--body);` — Source Serif 4 italic reads as editorial deck, not UI label.

### Section Nav Demo Link (Landing)

Add 4th anchor link "Demo" to `.section-nav` pointing to the demo strip section. Depends on demo strip HTML landing first.

## Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| App CSS | `web-ng/src/styles.css` | Direct edits. No preprocessor. |
| Landing CSS | `landing/style.css` | Separate stylesheet. Changes don't cross. |
| Landing HTML | `landing/index.html` | Static markup. No build step. |
| API | `api/modules/data/projects/service.py` | One constant change. |
| Template | `web-ng/src/app/app.component.html` | Status bar relocation only. |

## Design Decisions

| Decision | Rationale |
|---|---|
| Status bar inline, not fixed bottom | Editorial ticker vs web app download bar. Always visible communicates system readiness. Prevents layout shift on generation start. |
| Overline muted in app, red in landing | App is a tool (quiet structure). Landing is marketing (attention-grabbing). Separate stylesheets make this safe. |
| teaser_chars=500 not unlimited | 500 chars covers 2-3 paragraphs of markdown — enough to find first prose sentence past headings. Unlimited would send entire files on the list endpoint. |
| Output cards not list | Cards give editorial weight per artifact. Reuse existing CSS. Converts enumeration into demonstration. |
| Demo strip as static HTML | Guarantees aesthetic parity, loads instantly. No auth, no dev server dependency. |
