# Architecture: UX: Landing & Grid Polish

## Design Principles

1. **No new abstractions.** Every change is a leaf-node edit — a CSS rule value, an HTML element insertion, or a Python constant. No new components, no new CSS classes, no new API endpoints.
2. **CSS classes already exist.** The `landing/style.css` already defines `.output-grid`, `.output-card`, `.demo-strip`, `.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content`, `.step-body`. HTML changes wire these up; they do not invent them.
3. **Verified source of truth is `landing/app-overview.html`.** Every visual decision is already locked in the mock. Implementation reads the mock and reproduces it — it does not design.
4. **One concern per diff.** Each task touches exactly one file and one concern. CSS edits do not co-travel with HTML edits.
5. **Color philosophy: state not category.** Grey for counts, red for attention, green for done, blue for action. No re-categorization of colors is permitted.

---

## Component Design

### Component 1: App CSS — `.section-count` Pill Badge

**File:** `web-ng/src/styles.css`

**Current state (verified):**
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

**Status: Already correct.** The pill badge styling (`background: var(--border)`, `border-radius: 2px`, `padding: 1px 5px`) is already applied. The braindump described this as a needed change, but inspection of the live CSS shows it was applied in a prior session. No change required.

---

### Component 2: App CSS — `.overline` Color in App Context

**File:** `web-ng/src/styles.css`

**Current state (verified):**
```css
.overline {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--red);          ← WRONG for app context
  margin-bottom: 14px;
  display: block;
}
```

**Problem:** The base `.overline` class uses `color: var(--red)`. On the landing page this is intentional (marketing emphasis). In the app, `.section-group-title` inherits this and renders red overlines, while the mock specifies `color: var(--ink-muted)` at `9px`.

**Investigation result:** The `.section-group-title` rule sets `color: var(--section-color, var(--ink-muted))` on the title text itself. However, if `.overline` is applied as a child of or alongside `.section-group-title`, the `color: var(--red)` bleeds through because `.section-group-title` does not scope the overline.

**Fix:** Change the base `.overline` rule to use `var(--ink-muted)`. The landing page overlines (in `.lede-main span.overline`) rely on the red for marketing emphasis — those must be explicitly re-scoped to red.

**Revised `.overline`:**
```css
.overline {
  font-family: var(--sans);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-muted);
  margin-bottom: 14px;
  display: block;
}
```

**Note:** This change only applies to `web-ng/src/styles.css`. The landing page has its own `.overline` rule in `landing/style.css` which already correctly defines `color: var(--red)` and `font-size: 11px` for marketing context. These are separate files — no cross-contamination risk.

---

### Component 3: API — Teaser Character Window

**File:** `api/modules/data/projects/service.py`

**Current state (verified at line 101):**
```python
"specs": _read_specs(d, include_content=False, teaser_chars=300),
```

**Problem:** `firstNonHeadingSentence()` in the frontend skips heading lines (`#`, `-`, `*`, `>`, `|`). Many braindumps start with a title, then a section heading, then a bulleted list — the first real prose sentence may start at character 320–450. A 300-char teaser window captures only the heading block, so the teaser field is empty or contains only markdown symbols, triggering a fallback.

**Fix:** Change `teaser_chars=300` to `teaser_chars=500`.

**Boundary:** `_read_specs()` already handles the truncation correctly via `content[:teaser_chars]`. No other code changes are needed. The service function, not the route handler, owns this — consistent with the convention that service functions own data shaping.

**Risk:** Slightly larger JSON payload on `GET /api/projects`. The delta is at most 200 chars × number of projects. For a typical 20-project list, this adds ~4KB — negligible.

---

### Component 4: Landing CSS — Masthead Tagline Font

**File:** `landing/style.css`

**Current state (verified at lines 132–137):**
```css
.masthead-tagline {
  font-family: var(--body);
  font-size: 13px;
  font-style: italic;
  color: var(--ink-light);
}
```

**Status: Already correct.** The tagline already uses `var(--body)` (Source Serif 4 italic). The braindump described this as a needed change, but inspection shows it was already applied. No change required.

---

### Component 5: Landing HTML — Output Card Grid

**File:** `landing/index.html`

**Current state (verified):** The `.lede-aside` section already contains an `.output-grid` with five `.output-card` elements (Analysis, Epic, Architecture, Timeline, Implementation Guide). The braindump described this as a needed change, but inspection shows it was already wired. No change required.

---

### Component 6: Landing HTML — Demo Strip & Section Nav

**File:** `landing/index.html`

**Current state (verified):** The demo strip section is already wired between "How it works" and "Pricing" using `.demo-strip`, `.demo-masthead`, `.demo-body`, `.demo-sidebar`, and `.demo-content`. The section nav already contains the fourth "Demo" link. No change required.

---

### Component 7: Landing HTML — Step Bodies

**File:** `landing/index.html`

**Current state (verified):** All three "How it works" steps already contain `<p class="step-body">` paragraphs above their `.step-code` blocks. No change required.

---

## Summary of Actual Remaining Work

After code inspection, the gap between the braindump's task list and current state is narrower than described. The following table reflects verified current state:

| Task | Described As Needed | Actual State | Action |
|------|--------------------|-----------|----|
| `.section-count` pill badge | Change needed | Already correct | None |
| `.overline` muted in app | Verify + fix if needed | Red bleeds through | Fix: change base color to `var(--ink-muted)`, reduce to `9px` |
| `teaser_chars` 300→500 | API change needed | Still at 300 | Fix: change to `500` |
| Masthead tagline font | CSS change needed | Already correct | None |
| Output card grid | HTML change needed | Already wired | None |
| Demo strip HTML | HTML change needed | Already wired | None |
| Step bodies | HTML change needed | Already wired | None |
| Section nav "Demo" link | HTML change needed | Already present | None |

**Net remaining work: 2 targeted edits across 2 files.**

---

## Technology Stack

| Layer | Technology | Note |
|-------|-----------|------|
| App CSS | CSS custom properties on vanilla CSS | No preprocessor; var() tokens only |
| Landing CSS | Same token vocabulary (`landing/style.css`) | Separate file — does not share the app's `.overline` rule |
| API service | Python 3.11 — pure function, no ORM interaction | `teaser_chars` is a scalar passed to a single `content[:n]` slice |
| HTML | Static HTML5 in `landing/index.html` | No framework; edits are text insertions |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Change base `.overline` color, not add a scoped override | Simpler; the app CSS has no use for red overlines anywhere | Red overlines are a landing-page concern; the landing page has its own CSS file |
| Reduce `.overline` font-size from 11px to 9px | Matches the mock's `font-size: 9px` spec | 11px overlines are too prominent for app section headers; the 9px value matches the mock's micro-label treatment |
| `teaser_chars=500` not a config variable | The value is stable and semantics are self-documenting as a literal | Avoids env-var proliferation for a single tuning constant |
| No Angular template changes | Out of scope per epic definition | Status bar relocation and hero grid require `app.component.html` edits; deferred to a separate ticket |
