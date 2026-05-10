# Epic: UX — Landing & Grid Polish

## Business Value

Specview's core narrative is "opening the app feels like opening a newspaper." The app-ui-mockups project locked the design decisions that deliver that feeling — card sizing, section headers, typography, status colors. Most of those decisions now live in `web-ng/src/styles.css`. This epic closes the remaining gaps.

Three categories of impact:

1. **Perceptual authority** — the status bar moving from a fixed overlay to an inline newsroom ticker, the section count badges rendering as structured pills, and the overline micro-labels dropping to muted 9px transforms the app from "generic SPA" to "editorial tool." These are small CSS changes with outsized perceptual effect.

2. **Content fidelity** — the teaser window increase from 300 to 500 characters means real prose replaces empty fallbacks for braindump-heavy projects. Empty teasers undermine the newspaper illusion; real teasers reward it.

3. **Landing page editorial quality** — the output card grid, demo strip, step editorial bodies, and masthead tagline fix bring the landing page into alignment with the design system validated in the mockup. The landing page is the first thing a prospective user sees; it should reflect the same editorial authority as the app.

---

## Full Scope

### In Scope

- **Task 1 — Fix `.section-count` pill badge styling** (App CSS, `web-ng/src/styles.css`)
- **Task 2 — Fix `.overline` app-context styling** (App CSS, `web-ng/src/styles.css`)
- **Task 3 — Increase `teaser_chars` from 300 to 500** (API, `api/modules/data/projects/service.py`)
- **Task 4 — Status bar: move inline, always visible** (App CSS + Angular, `web-ng/src/styles.css` + `app.component.html`)
- **Task 5 — Landing: output card grid** (Landing HTML, `landing/index.html`)
- **Task 6 — Landing: demo strip section** (Landing HTML, `landing/index.html`)
- **Task 7 — Landing: step editorial bodies** (Landing HTML, `landing/index.html`)
- **Task 8 — Landing: masthead tagline font** (Landing CSS, `landing/style.css`)
- **Task 9 — Landing: section nav "Demo" link** (Landing HTML, `landing/index.html`, depends on Task 6)
- **Task 10 — Class name consistency check** (App CSS + Angular templates — cosmetic, low priority)

### Out of Scope

- Hero grid `2fr 1fr 1fr` for Active section — deferred, requires Angular template changes
- Dark mode new work — existing tokens only
- Mobile/responsive changes — not intentionally changed
- E2E test additions — no behavior flow changes
- New CSS design decisions — all classes already exist

---

## Task Breakdown

| # | Task | Layer | Effort | Priority | Dependencies |
|---|------|-------|--------|----------|--------------|
| 1 | Fix `.section-count` pill badge | App CSS | 0.25 days | High | None |
| 2 | Fix `.overline` app-context overline | App CSS | 0.25 days | High | None |
| 3 | Increase `teaser_chars` 300 → 500 | API | 0.25 days | High | None |
| 4 | Status bar: inline, always visible | App CSS + Angular | 0.5 days | High (highest perceptual impact) | None |
| 5 | Landing: output card grid | Landing HTML | 0.5 days | Medium | None |
| 6 | Landing: demo strip section | Landing HTML | 0.75 days | Medium | None |
| 7 | Landing: step editorial bodies | Landing HTML | 0.25 days | Medium | None |
| 8 | Landing: masthead tagline font | Landing CSS | 0.25 days | Medium | None |
| 9 | Landing: section nav "Demo" link | Landing HTML | 0.25 days | Medium | Task 6 |
| 10 | Class name consistency check | App CSS + Angular | 0.25 days | Low | None |

**Total estimated effort: ~3.5 days**

Tasks 1–3 are independent CSS/API edits. Task 4 has the highest perceptual return and should run early. Tasks 5–9 are all landing page work and can run in sequence after Task 6 is done. Task 10 is cosmetic and deferred to available capacity.

---

## Success Criteria

- Section count badges render as grey pills (`background: var(--border); border-radius: 2px; padding: 1px 5px`) in every section header, replacing plain muted text.
- `.overline` in app context renders at `9px` in `var(--ink-muted)` — not red, not 11px. Landing page overlines remain red (separate CSS file).
- Projects with braindumps whose first prose sentence falls between characters 300–500 now show a real teaser instead of an empty fallback.
- Status bar renders between the section nav and the search bar, inline in page flow (`position: relative`), always visible. Idle state shows green "idle — ready". No layout shift when generation starts.
- Landing page `.lede-aside` shows 5 output cards in `.output-grid` — not a flat `<ul>`.
- Landing page "How it works" each step has a `<p class="step-body">` sentence above its `.step-code` block.
- Landing page has a `.demo-strip` section between "How it works" and "Pricing".
- Landing page section nav has a fourth "Demo" link.
- `.masthead-tagline` in `landing/style.css` uses `font-family: var(--body)` (Source Serif 4 italic at 13px).
- `ng build --configuration production` passes with zero errors.
- `pytest api/` passes with no regressions.

---

## Related Documents

- [Analysis](./analysis.md) — Gap inventory, constraints, open questions
- [Architecture](./architecture.md) — Design principles, component design, exact CSS values
- [Timeline](./timeline.md) — Task status tracking
- [Implementation Guide](./implementation-guide.md) — Step-by-step execution for every task
