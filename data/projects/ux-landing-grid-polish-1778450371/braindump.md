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

## Original UX vision — Dieter Rams + newspaper (from ux-polish-newspaper)

"Dieter Rams minimalism + editorial newspaper layout."

**Core principles:**
- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace create structure; shadows do not exist (one modal exception)
- Ink on paper: cream (`#FFFEF9`) not white, near-black (`#121212`) not black
- Interaction is quiet — hover is a whisper of background, nothing more
- Density without clutter: if it doesn't communicate something, it doesn't exist
- The reader should focus entirely on content and ideas

**What excellent looks like (quoted from the braindump):**
> Opening the app should feel like opening a newspaper. The masthead carries editorial authority (64px Playfair, cream, near-black). The section nav tabs have a nameplate rule above them — that thick 3px bar that says "you are here in the publication." Section group headers are red overlines, not neutral gray labels.

### Card grid — where we diverge from the vision

The original vision describes a **newspaper column layout** — 3 equal columns, each a vertical stack of items separated by borders. ClawBoi uses `repeat(3, 1fr)` with column dividers (`border-right: 1px solid var(--border)`), vertical items within each column (`padding: 12px 0`, `border-bottom: 1px`).

Our current app uses `auto-fill` grid with `minmax(280px, 1fr)` — a responsive card grid. This is fundamentally different from a newspaper column layout:

| Newspaper columns (ClawBoi) | Card grid (current app) |
|---|---|
| Fixed 3 columns, items flow vertically within each | Responsive N columns, items fill left-to-right |
| Vertical dividers between columns | Vertical dividers between cards (no column concept) |
| Items per column vary by count | All items in flat grid, wrapping |
| Column header at top of each column | Section header above entire grid |
| Feels like reading a newspaper | Feels like browsing a catalog |

**The key tension:** The newspaper column layout works beautifully for the **single-section view** (e.g. viewing only "Specced" projects) — that's the 3-column `.file-grid` layout. But the **all-sections view** (grouped by section) needs a different layout because sections have variable counts.

**Current approach:** Section groups with auto-fill card grid works well for the all-sections view. But the cards themselves don't feel editorial — they feel like a generic card grid. The newspaper feel comes from:

1. **Typography hierarchy** — first card (lead story) visibly larger than the rest ✅ Applied (17px vs 15px)
2. **Vertical rhythm** — items stacked with border-bottom separators, not side-by-side cards ❌ We removed horizontal borders
3. **Column dividers** — thin vertical rules between columns, not between individual cards ⚠️ We have `border-left` on cards, but it separates cards not columns
4. **Content density** — teasers that give you a reason to click ✅ Applied (Source Serif 14px, real content)
5. **Masthead authority** — nameplate rule, editorial headings ✅ Applied (3px top, Playfair headings)

### The grid improvement opportunity

For sections with 3+ cards, the auto-fill grid creates a newspaper-like multi-column layout naturally. The issue is:
- **Sections with 1-2 cards** look sparse — one card with empty space to the right
- **Cards side-by-side** read as tiles, not as stories in a newspaper column

**Possible directions:**
1. **Column-first layout for small sections** — 1-2 cards span full width (single column, more teaser text)
2. **Stacked layout for small sections** — cards stack vertically at full width, not in a grid
3. **Variable column widths** — first card gets `2fr`, rest get `1fr` (hero + standard, like the mock's Active section)
4. **Border-bottom separators within columns** — restore horizontal rules between cards in the same column, while keeping vertical rules between columns

## Mock UI enumeration — `app-overview.html` top to bottom

```
#  ELEMENT                         POSITION              NOTES
── ──────────────────────────────── ──────────────────── ─────────────────────────
 1  Masthead                        Top                  3-col grid: edition | title+date+tagline | actions
    ├── edition label                Left                "Spec Doc" — 11px uppercase muted
    ├── date                         Center              "Sunday, May 10, 2026" — 12px uppercase
    ├── title                        Center              "Specview" — 64px Playfair 700
    ├── tagline                      Center              "All the Specs Fit to Read" — 13px italic
    ├── + New button                 Right               accent border, fills accent on hover
    ├── theme toggle                 Right               ☾ button
    └── Sign out                     Right               muted uppercase

 2  Section nav                      Sticky               3px ink top border, 1px bottom
    ├── All (9)                      Tab                  Grey pill count badge
    ├── Active (2)                   Tab
    ├── Specced (2)                  Tab
    ├── Ready to build (1)           Tab
    ├── Braindumps (4)               Tab
    └── Archive                      Tab (no count)

 3  Generation status bar            Below nav            CLICK TO CYCLE 4 STATES
    ├── Active state                 amber #7a5800        shimmer track + pulsing white dot + project name + step
    ├── Success state                green #1a6b30        dot + project name + "done — 5 files generated"
    ├── Failure state                red #C41E3A          dot + project name + "error — chain timed out" + Retry
    └── Idle state                   green #1a6b30        dot + "specview" + "idle — ready"

 4  Search bar                       Below status bar     input + "9 projects" count label + 1px bottom border

 5  Active section (hero grid)       2fr 1fr 1fr          Green "ACTIVE" header + 2px ink underline + pill count
    ├── Hero main card               2fr column           28px title, 16px serif teaser, 4-line clamp, status dot
    └── Hero secondary card          1fr column           16px title, 3-line clamp, border-left divider

 6  Specced section (standard grid)  auto-fill 280px      Blue "SPECCED" header + pill count
    ├── Card 1 (featured)            17px title           3-line teaser clamp, badge "COMPLETE" (green)
    └── Card 2                       15px title           2-line clamp, border-left divider

 7  Ready to build section           auto-fill            Purple "READY TO BUILD" header + pill count
    └── Card 1 (featured)            17px title           badge "READY" (accent blue)

 8  Braindumps section               auto-fill            Brown "BRAINDUMPS" header + pill count
    ├── Card 1 (featured)            17px title           badge "NEW" (red)
    ├── Card 2                       15px title           border-left divider
    ├── Card 3                       15px title           border-left divider
    └── Card 4                       15px title           border-left divider

 9  Archive section                  Empty state          Muted "ARCHIVE" header + "0" pill
    └── "No archived projects."      Italic muted         + "Archive a project →" accent link

10  --- Design reference divider --- Dashed line          "Design reference" label
11  Iteration A (baseline)           Old grid             240px, 12px pad, sans teasers, grey fill
12  Iteration B (breathing room)     Old grid             280px, 20px pad, sans teasers, grey fill
```

### Status bar placement — mock vs app

| | Mock | Live app |
|---|---|---|
| Position | `position: relative` (inline flow, between nav and search) | `position: fixed; bottom: 0` (pinned to viewport bottom) |
| Layout | `display: flex; padding: 8px 16px` | `position: fixed; bottom: 0; left: 0; right: 0; z-index: 2000` |
| Visibility | Always visible (idle state shows green "idle — ready") | Only visible during generation |
| Color | State-specific: amber/green/red per playground 5.7 | `background: var(--ink)` base with state modifiers |

**Decision: match the mock.** Status bar is inline — `position: relative`, part of the page flow between nav and search. Always visible. Idle state shows green "idle — ready". This is part of the editorial structure, not a floating overlay. The 32px vertical cost is acceptable — it communicates system readiness and prevents layout shift when generation starts.

**Change needed in app:** `web-ng/src/styles.css` — change `.gen-status-bar` from `position: fixed; bottom: 0; left: 0; right: 0; z-index: 2000` to `position: relative`. Move the element in `app.component.html` from its current position to between the section nav and search bar. Always render it (not conditionally hidden when idle).

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
