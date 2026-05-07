# Implementation Guide: Landing Page — Visual Simplification

**Project**: Landing Page v2 — Less Clutter, More White Space
**Date**: 2026-05-07
**Status**: Ready to execute

---

## Context

The landing page at `landing/index.html` + `landing/style.css` needs:
- Two redundant sections removed (output cards, demo strip)
- One new section added (metrics bar)
- Pullquotes replaced with a single visceral user-outcome quote
- More breathing room (padding increases)

The following edits were already applied in a prior partial run — do NOT repeat:
- `<span class="masthead-edition">` is already empty (was "Builder Tools")
- `<a href="#output">Output</a>` is already removed from the nav

Design system: `/Users/sam/Projects/specview/docs/design-system.md`
- Font tokens: `var(--serif)`, `var(--body)`, `var(--sans)` only
- No `box-shadow`, no `border-radius` on structural elements
- No new files, no new `<link>` or `<script>` tags

---

## Task 1 — Remove output cards section

**Agent**: spec-frontend
**Files**: `landing/index.html`

### Steps

Remove the entire block from `<!-- Output docs -->` through `</section>`:

```html
  <!-- Output docs -->
  <div class="section-heading" id="output">What Spec Doc generates</div>

  <section class="output-grid">
    ...all 4 output-card divs...
  </section>
```

This starts at the comment `<!-- Output docs -->` and ends at the `</section>` closing the `.output-grid`. Remove the section-heading div and the entire section element.

### Verify

- [ ] `grep -n "output-grid\|output-card\|id=\"output\"" landing/index.html` returns zero results
- [ ] `grep -n "What Spec Doc generates" landing/index.html` returns zero results

---

## Task 2 — Remove demo strip section

**Agent**: spec-frontend
**Files**: `landing/index.html`

### Steps

Remove the entire block from `<div class="section-heading">The tool</div>` through `</div><!-- end demo-strip -->`:

```html
  <div class="section-heading">The tool</div>

  <div class="demo-strip">
    ...the entire demo-strip-inner content...
  </div>
```

This starts at `<div class="section-heading">The tool</div>` and ends at the closing `</div>` of `demo-strip`.

### Verify

- [ ] `grep -n "demo-strip\|demo-masthead\|demo-body\|The tool" landing/index.html` returns zero results

---

## Task 3 — Add metrics bar

**Agent**: spec-frontend
**Files**: `landing/index.html`, `landing/style.css`

### Step 1 — Insert HTML

Insert immediately after the closing `</section>` of the `.lede` hero section and before `<!-- Output docs -->` (or before `<!-- How it works -->` if Task 1 already removed the output section):

```html
  <!-- Metrics bar -->
  <div class="metrics-bar">
    <span>764<span class="metrics-plus">+</span> tests passing</span>
    <span class="metrics-sep">·</span>
    <span>433 commits</span>
    <span class="metrics-sep">·</span>
    <span>36 projects generated</span>
    <span class="metrics-sep">·</span>
    <span>0 human code lines written</span>
  </div>
```

### Step 2 — Append CSS to `landing/style.css`

Append at the very end of `landing/style.css`:

```css
/* ── Metrics Bar ───────────────────────────────── */
.metrics-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 14px 40px;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.metrics-bar span {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-light);
}

.metrics-sep {
  color: var(--border) !important;
  font-weight: 400;
}

.metrics-plus {
  color: var(--ink-muted);
  font-weight: 400;
}
```

### Verify

- [ ] `grep -n "metrics-bar" landing/index.html` returns one result
- [ ] `grep -n "metrics-bar" landing/style.css` returns the CSS block

---

## Task 4 — Replace pullquotes with single centered quote

**Agent**: spec-frontend
**Files**: `landing/index.html`, `landing/style.css`

### Step 1 — Replace HTML

Replace the entire `<section class="pullquote-row">` block (both pullquotes + divider) with:

```html
  <!-- Pullquote -->
  <section class="pullquote-row pullquote-single">
    <div class="pullquote">
      <div class="pullquote-mark">"</div>
      <p class="pullquote-text">
        I wrote 3 paragraphs about a feature. 47 seconds later I had an analysis,
        an epic, an architecture doc, and an implementation guide with test bodies.
        Human code lines written: 0.
      </p>
      <div class="pullquote-attr">What using Spec Doc feels like</div>
    </div>
  </section>
```

### Step 2 — Append CSS to `landing/style.css`

Append after the metrics-bar CSS (or at end of file):

```css
/* ── Single centered pullquote ─────────────────── */
.pullquote-single {
  display: block;
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
  padding: 0;
}

.pullquote-single .pullquote {
  padding: 56px 40px;
}

.pullquote-single .pullquote-mark {
  font-size: 72px;
  color: var(--border);
}

.pullquote-single .pullquote-text {
  font-size: 26px;
  max-width: 680px;
  margin: 0 auto 16px;
  color: var(--ink);
}
```

### Verify

- [ ] `grep -n "chain-conventions\|adapter boundary\|pullquote-divider" landing/index.html` returns zero results
- [ ] `grep -n "pullquote-single" landing/index.html` returns one result
- [ ] `grep -n "Human code lines" landing/index.html` returns one result

---

## Task 5 — Increase breathing room

**Agent**: spec-frontend
**Files**: `landing/style.css`

### Steps

In `landing/style.css`, find and update these values:

**Hero/lede** — increase vertical padding:
```css
/* Find: */
.lede {
  ...
  padding: 40px;
}
/* Change padding to: */
  padding: 56px 40px;
```

**Steps** — increase vertical padding per step:
```css
/* Find: */
.step {
  padding: 32px 40px;
  ...
}
/* Change to: */
  padding: 48px 40px;
```

**Step code blocks** — more space above:
```css
/* Find: */
.step-code {
  margin-top: 14px;
  ...
}
/* Change to: */
  margin-top: 24px;
```

### Verify

- [ ] `grep -n "padding: 56px 40px" landing/style.css` returns one result (.lede)
- [ ] `grep -n "padding: 48px 40px" landing/style.css` returns one result (.step)
- [ ] `grep -n "margin-top: 24px" landing/style.css` returns one result (.step-code)

---

## Task 6 — QA pass

**Agent**: spec-frontend
**Files**: read-only

### Checks

```bash
# No output section remnants
grep -n "output-grid\|output-card\|id=\"output\"" landing/index.html

# No demo strip remnants
grep -n "demo-strip\|The tool" landing/index.html

# Metrics bar present
grep -n "metrics-bar" landing/index.html

# New pullquote present
grep -n "Human code lines" landing/index.html

# No forbidden CSS
grep -n "box-shadow\|border-radius\|--font-" landing/style.css | grep -v "pre-existing"

# Font tokens correct
grep -n "var(--serif)\|var(--body)\|var(--sans)" landing/style.css | tail -20
```

### Visual checklist

- [ ] Nav: What | How it works | Pricing (no Output)
- [ ] Hero has proper breathing room — not cramped
- [ ] Metrics bar visible between hero and "How it works"
- [ ] Steps feel more spacious
- [ ] Single centered pullquote with the "47 seconds" quote
- [ ] No horizontal scroll at 375px
