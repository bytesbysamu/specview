# Timeline: UX: Landing & Grid Polish

## Epic Status

**As of: 2026-05-10**

After code inspection (see architecture.md), the scope has narrowed significantly. Most tasks described in the braindump were already applied in prior sessions. Only 2 targeted edits remain across 2 files.

| Metric | Value |
|--------|-------|
| Total original tasks | 8 |
| Already complete | 6 |
| Remaining | 2 |
| Estimated remaining effort | ~30 minutes |
| Blocking dependencies | None |

---

## Task Board

### Done

| # | Task | File(s) | Completed By |
|---|------|---------|-------------|
| T3a | Output card grid (5 `.output-card` in `.lede-aside`) | `landing/index.html` | Prior session |
| T3b | Step bodies (`<p class="step-body">` above each `.step-code`) | `landing/index.html` | Prior session |
| T4a | Demo strip section HTML | `landing/index.html` | Prior session |
| T4b | Section nav "Demo" link | `landing/index.html` | Prior session |
| T5 | Masthead tagline font (`var(--sans)` → `var(--body)`) | `landing/style.css` | Prior session |
| T1a | `.section-count` pill badge styling | `web-ng/src/styles.css` | Prior session |

### Backlog

| # | Task | File | Effort | Priority | Notes |
|---|------|------|--------|----------|-------|
| T1b | Fix `.overline` — change `color: var(--red)` → `var(--ink-muted)`, `font-size: 11px` → `9px` | `web-ng/src/styles.css` | 15 min | High | Red overlines leak marketing context into the tool. The landing page's own `style.css` has a separate `.overline` rule — no cross-file risk. |
| T2 | Expand `teaser_chars` from `300` to `500` | `api/modules/data/projects/service.py` line 101 | 15 min | High | Braindump-heavy projects with a heading block in the first 300 chars show no prose teaser. Backend service only — no route or template changes. |

### Deferred (Out of Scope)

| Task | Reason | Re-scope When |
|------|--------|---------------|
| Status bar relocation (`position: fixed` → `position: relative`, always-render) | Requires Angular template change in `app.component.html` | Separate ticket for app-component UI pass |
| Hero grid `2fr 1fr 1fr` for Active section | Angular template change + conditional rendering | Single-section view work begins |
| Newspaper column-first layout for 1–2 card sections | No direction chosen; research only | After UX review of low-card section feel |
| `.file-item-meta-sep` → `.sep` rename | Not a visual issue; class name already works | Low-risk cleanup pass |

---

## Effort Breakdown

| Task | Estimate | Type |
|------|----------|------|
| T1b — `.overline` CSS fix | 15 min | CSS edit (2 property values) |
| T2 — `teaser_chars` expansion | 15 min | Python edit (1 integer constant) |
| **Total remaining** | **30 min** | — |

---

## Delivery Sequence

Both remaining tasks are independent and can be executed in either order. No dependencies between them.

```
T1b  web-ng/src/styles.css       ─── 15 min ──── ✓
T2   api/modules/data/...        ─── 15 min ──── ✓
```

---

## Progress Metrics

| Metric | Value |
|--------|-------|
| Tasks complete | 6 / 8 (75%) |
| Files touched (done) | `landing/index.html`, `landing/style.css`, `web-ng/src/styles.css` (partial) |
| Files remaining | `web-ng/src/styles.css`, `api/modules/data/projects/service.py` |
| CSS rules changed | 3 (`.section-count` ✓, `.masthead-tagline` ✓, `.overline` pending) |
| HTML elements added | ~40 (5 output cards, 3 step bodies, 1 demo strip, 1 nav link) |
| Python constants changed | 0 of 1 |
| Angular template changes | 0 (none in scope) |
