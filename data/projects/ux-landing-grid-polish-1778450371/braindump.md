# UX: Landing & Grid Polish

## What this is

Final alignment pass across the landing page and app overview grid. The app-ui-mockups project validated design decisions in a static HTML mockup (`landing/app-overview.html`). Most of those decisions have been applied to `web-ng/src/styles.css`. This project addresses the remaining gaps — both in the app overview and the landing page (`landing/index.html`).

## Problems

### App overview — remaining gaps

The mock (`app-overview.html`) and live app (`web-ng/`) still diverge in several places:

1. **Nav count badges** — Mock uses grey pill badges (`background: var(--border); border-radius: 2px; padding: 1px 5px`). App uses plain text with `opacity: 0.7`. The `.section-count` class needs the pill styling.

2. **Overline styling** — Mock uses `font-size: 9px; color: var(--ink-muted)` for section header overlines. App's `.overline` is `font-size: 11px; color: var(--red)` — red and larger. The section-group-title has its own styled overline via `--section-color`, but the base `.overline` class is still wrong for app context. The landing page uses red overlines intentionally (marketing emphasis) but the app should use muted overlines (tool, not publication).

3. **Teaser still showing fallback for some projects** — The `spec.teaser` field (first 300 chars) is now used, but `firstNonHeadingSentence()` skips lines starting with `#`, `-`, `*`, `>`, `|`. Many braindumps start with `# Title` then `## Section` then a list — the first prose sentence may be past the 300-char teaser window. Consider increasing `teaser_chars` from 300 to 500 in the API.

4. **`.file-item-meta-sep`** — App uses this class name. Mock uses `.sep`. Same styling, different name. Not a visual issue but inconsistent.

### Landing page — grid layout improvements needed

The landing page (`landing/index.html`) needs to adopt the same grid improvements validated in the mockup:

1. **Output card grid** — The hero aside currently has a flat `<ul>`. The `landing-polish-newspaper` architecture doc specifies replacing it with `.output-grid` / `.output-card` (5 cards: Analysis, Epic, Architecture, Timeline, Implementation Guide). CSS classes already exist in `style.css`.

2. **Demo strip** — A miniaturized newspaper-style app UI mockup between "How it works" and "Pricing". CSS classes exist (`.demo-strip`, `.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content`). HTML not wired yet.

3. **Step editorial bodies** — The "How it works" 3-column section jumps from heading to code mockup. A `<p class="step-body">` sentence above each code block creates editorial rhythm. Class already styled.

4. **Masthead tagline font** — Currently `Source Sans 3 italic`. Should be `Source Serif 4 italic 13px` (editorial deck, not UI label). Single CSS rule change in `.masthead-tagline`.

5. **Section nav** — Landing needs a 4th link ("Demo") after the demo strip section lands.

## Design decisions already locked (from previous projects)

These are NON-NEGOTIABLE — do not re-litigate:

| Decision | Value | Source |
|---|---|---|
| Grid min-width | `minmax(280px, 1fr)` | app-ui-mockups |
| Card padding | `20px 24px` | app-ui-mockups |
| Card borders | Vertical only (`border-left`), first-child: none | app-ui-mockups |
| Teaser font | Source Serif 4, 14px | ClawBoi gap analysis |
| Featured first card | 17px title, 3-line clamp | app-ui-mockups |
| Section header | Colored title, 2px ink underline inline-block | app-ui-mockups |
| Section dividers | `1px solid var(--border)` between groups | app-ui-mockups |
| Color philosophy | State not category. Grey for counts, red for attention, green for done, blue for action | Playground audit |
| Status bar | Playground 5.7 colors: idle=#1a6b30, active=#7a5800, success=#1a6b30, failure=#C41E3A | Playground 5.7 |
| Badge system | `.badge` (grey), `--new` (red), `--complete` (green), `--ready` (blue) | Playground 5.16 |
| Nav icons | Text-only (no inline SVG) | app-ui-mockups |
| Hero grid | `2fr 1fr 1fr` for Active section (deferred — needs Angular template changes) | ClawBoi research |

## What to build

### App CSS fixes (small, direct edits to `web-ng/src/styles.css`)

1. **Fix `.section-count`** — add pill badge styling: `background: var(--border); border-radius: 2px; padding: 1px 5px`. Remove `opacity: 0.7; margin-left: 2px`.

2. **Add app-context `.overline` override** — The landing `.overline` uses `color: var(--red)` (correct for marketing). The app needs an override for section headers: the `.section-group-title` already has `color: var(--section-color)` which overrides it. Verify this works — if `.overline` color bleeds through, scope it.

3. **Increase `teaser_chars`** in API — `api/modules/data/projects/service.py` line 101: change `teaser_chars=300` to `teaser_chars=500`.

### Landing page improvements (HTML edits to `landing/index.html`)

4. **Output card grid** — Replace the `<ul>` in `.lede-aside` with 5 `.output-card` elements. Use existing CSS classes.

5. **Demo strip section** — Add a new section with `.demo-strip` between "How it works" and "Pricing". Compose from `.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content`.

6. **Step bodies** — Add `<p class="step-body">` above each `.step-code` in the 3-column "How it works" section.

7. **Masthead tagline** — In `landing/style.css`, change `.masthead-tagline` font-family from `var(--sans)` to `var(--body)`.

8. **Section nav "Demo" link** — Add 4th nav link after demo strip lands.

## References

- Mock reference: `landing/app-overview.html` (served at `http://localhost:8097/app-overview.html`)
- Playground: `landing/playground.html` (component reference)
- Landing: `landing/index.html` (served at `http://localhost:8096/`)
- App CSS: `web-ng/src/styles.css`
- API teaser: `api/modules/data/projects/service.py` line 101
- Previous projects:
  - `data/projects/app-ui-mockups-1778399474/` — mockup design decisions
  - `data/projects/ux-grid-polish-1778368175/` — semantic color, breathing room, teasers
  - `data/projects/ux-polish-newspaper-1778238000/` — newspaper feel, icon mapping
  - `data/projects/landing-polish-newspaper/` — landing polish architecture
  - `data/projects/landing-v2-playground-1778400000/` — playground design system
