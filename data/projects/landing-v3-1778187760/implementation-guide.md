# Implementation Guide: Landing Page v3 — Full-Screen Sections

**Project**: Landing Page v3 — Full viewport sections, less text, more whitespace
**Date**: 2026-05-07
**Status**: Ready to execute

---

## Context

`landing/index.html` and `landing/style.css` need a layout overhaul:
- Each major section should fill (or nearly fill) the viewport
- Step paragraphs removed — code blocks tell the story
- Hero and pricing copy trimmed aggressively
- All padding dramatically increased

Design system: `/Users/sam/Projects/specview/docs/design-system.md`
- Font tokens: `var(--serif)`, `var(--body)`, `var(--sans)` only
- No `box-shadow`, no `border-radius` on structural elements
- No new files, no new `<link>` or `<script>` tags

---

## Task 1 — Trim text content in HTML

**Agent**: spec-frontend
**Files**: `landing/index.html`

### Steps

Read the file first. Then make these four text changes:

**1a. Hero deck — trim to 2 sentences.**

Find:
```html
      <p class="deck">
        Write everything you know about a feature — raw and unfiltered.
        Spec Doc generates the structured documents your team needs to build it:
        analysis, epic, architecture, and an executor-ready implementation guide.
        No more blank-page paralysis. No more re-briefing the AI every session.
      </p>
```
Replace with:
```html
      <p class="deck">
        Write everything you know — raw and unfiltered.
        Spec Doc generates the engineering docs your team needs to build it.
      </p>
```

**1b. Remove all three `.step-body` paragraphs from the steps section.**

Remove (step 1):
```html
      <p class="step-body">
        Write everything you know about the feature — raw, unfiltered, unstructured.
        Problems, constraints, prior art, open questions. The messier the better.
        Spec Doc handles the structure.
      </p>
```

Remove (step 2):
```html
      <p class="step-body">
        One click. Spec Doc runs a three-step AI chain:
        analysis → epic → architecture.
        Each file appears on disk as it completes.
        You can read the analysis while the architecture is still generating.
      </p>
```

Remove (step 3):
```html
      <p class="step-body">
        Open the implementation guide in Claude Code.
        Every task has concrete steps, real file paths, full test bodies, and a commit plan.
        No re-briefing. No context rebuilding. Just execute.
      </p>
```

**1c. Trim Free tier pricing description.**

Find:
```html
        <p class="pricing-desc">
          For developers exploring AI-structured spec docs. Three projects a month
          gives you room to evaluate the workflow before committing.
        </p>
```
Replace with:
```html
        <p class="pricing-desc">
          Three projects a month to evaluate before committing.
        </p>
```

**1d. Trim Pro tier pricing description.**

Find:
```html
        <p class="pricing-desc">
          For solo developers and small-team PMs who want unlimited spec generation
          without managing infrastructure. One seat, one decision.
        </p>
```
Replace with:
```html
        <p class="pricing-desc">
          Unlimited spec generation. One seat, one decision.
        </p>
```

### Verify

- [ ] `grep -c "step-body" landing/index.html` returns 0
- [ ] `grep -n "No more blank-page" landing/index.html` returns no results
- [ ] `grep -n "One seat, one decision" landing/index.html` returns 1 result (trimmed version)

---

## Task 2 — Full-screen sections in CSS

**Agent**: spec-frontend
**Files**: `landing/style.css`

### Steps

Read `landing/style.css` first. Make these targeted changes to existing rules:

**2a. Hero — full viewport height, vertically centered.**

Find the `.lede` rule:
```css
.lede {
  display: grid;
  grid-template-columns: 1fr 1px 340px;
  gap: 0;
  border-bottom: 1px solid var(--border);
  padding: 56px 40px;
}
```
Replace with:
```css
.lede {
  display: grid;
  grid-template-columns: 1fr 1px 340px;
  gap: 0;
  border-bottom: 1px solid var(--border);
  padding: 80px 40px;
  min-height: calc(100vh - 100px);
  align-items: center;
}
```

**2b. Steps — full viewport height, centered content per step.**

Find the `.steps` rule:
```css
.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-bottom: 1px solid var(--border);
}
```
Replace with:
```css
.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-bottom: 1px solid var(--border);
  min-height: 100vh;
}
```

Find the `.step` rule:
```css
.step {
  padding: 48px 40px;
  border-right: 1px solid var(--border);
  position: relative;
  transition: background 0.15s;
}
```
Replace with:
```css
.step {
  padding: 80px 48px;
  border-right: 1px solid var(--border);
  position: relative;
  transition: background 0.15s;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
```

Find the `.step-num` rule:
```css
.step-num {
  font-family: var(--serif);
  font-size: 64px;
  font-weight: 700;
  color: var(--border);
  line-height: 1;
  margin-bottom: 12px;
  display: block;
}
```
Replace with:
```css
.step-num {
  font-family: var(--serif);
  font-size: 96px;
  font-weight: 700;
  color: var(--border);
  line-height: 1;
  margin-bottom: 20px;
  display: block;
}
```

**2c. Pricing — tall section with centered grid.**

Find the `.pricing` rule:
```css
.pricing {
  border-bottom: 1px solid var(--border);
  padding: 0 40px 40px;
}
```
Replace with:
```css
.pricing {
  border-bottom: 1px solid var(--border);
  padding: 80px 40px;
  min-height: 80vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
```

Find the `.pricing-grid` rule:
```css
.pricing-grid {
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  gap: 0 40px;
}
```
Replace with:
```css
.pricing-grid {
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  gap: 0 40px;
  max-width: 880px;
  width: 100%;
  margin: 0 auto;
}
```

**2d. Pullquote — tall centered section.**

Find the `.pullquote-single` rule (appended at end of file):
```css
.pullquote-single {
  display: block;
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
  padding: 0;
}
```
Replace with:
```css
.pullquote-single {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 60vh;
  border-bottom: 1px solid var(--border);
}
```

Find the `.pullquote-single .pullquote` rule:
```css
.pullquote-single .pullquote {
  padding: 56px 40px;
}
```
Replace with:
```css
.pullquote-single .pullquote {
  padding: 80px 40px;
  max-width: 800px;
}
```

### Verify

- [ ] `grep -n "min-height: calc(100vh" landing/style.css` returns 1 result (.lede)
- [ ] `grep -n "min-height: 100vh" landing/style.css` returns 1 result (.steps)
- [ ] `grep -n "min-height: 80vh" landing/style.css` returns 1 result (.pricing)
- [ ] `grep -n "min-height: 60vh" landing/style.css` returns 1 result (.pullquote-single)
- [ ] `grep -n "font-size: 96px" landing/style.css` returns 1 result (.step-num)

---

## Task 3 — QA pass

**Agent**: spec-frontend
**Files**: read-only

### Checks

```bash
# No step-body text remaining
grep -n "step-body" landing/index.html

# No forbidden CSS
grep -n "box-shadow\|--font-" landing/style.css

# Min-height rules all present
grep -n "min-height" landing/style.css

# Font tokens correct in new rules
grep -n "var(--serif)\|var(--body)\|var(--sans)" landing/style.css | tail -20
```

### Visual checklist

- [ ] Hero fills nearly the full viewport on load
- [ ] Steps section spans full viewport height — 3 tall columns
- [ ] Step body paragraphs gone — just number, title, code block
- [ ] Pricing section is tall with centered two-column grid
- [ ] Pullquote is a tall centered section with the "47 seconds" quote
- [ ] No horizontal scroll at any width
