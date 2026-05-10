# Implementation Guide: UX: Landing & Grid Polish

## Overview

Code inspection (see architecture.md) shows that 6 of 8 original tasks are already complete: the output-card grid, demo strip, step bodies, section nav link, masthead tagline font, and `.section-count` pill badge were all applied in prior sessions. Two targeted edits remain — one CSS rule change and one Python constant. Total remaining effort: ~30 minutes across 2 files.

## Pre-flight

Before starting:
1. Confirm you are in the `specview` working directory.
2. Verify `web-ng/src/styles.css` line 1516 contains `.overline { ... color: var(--red); ... font-size: 11px; }` — this is the value that needs changing.
3. Verify `api/modules/data/projects/service.py` line 101 contains `teaser_chars=300` — this is the value that needs changing.

---

## Task 1: Fix `.overline` Color and Size in App Context

**File:** `/Users/sam/Projects/specview/web-ng/src/styles.css`

**Why:** The base `.overline` class uses `color: var(--red)` and `font-size: 11px`. In the app, this causes section group header overlines to render in marketing-red and at a size that competes with section titles. The mock specifies `color: var(--ink-muted)` and `font-size: 9px` for app context. The landing page has its own separate `landing/style.css` file with its own `.overline` rule (`color: var(--red)`, `font-size: 11px`) — changing `web-ng/src/styles.css` does not affect the landing page.

**Change:** In the `.overline` rule block (around line 1516), change two property values:
- `font-size: 11px` → `font-size: 9px`
- `color: var(--red)` → `color: var(--ink-muted)`

**Exact before:**
```css
.overline {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--red);
  margin-bottom: 14px;
  display: block;
}
```

**Exact after:**
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

### Verify

- Open the app in a browser. Navigate to the All sections view. Section group headers (Active, Specced, Ready to build, Braindumps) must not show red overlines.
- Inspect a `.overline` element in browser dev tools — `color` must compute to the `--ink-muted` value (`#999999` light mode / `#606060` dark mode) and `font-size` must compute to `9px`.
- Confirm the landing page at localhost:8096 is unaffected — its overlines (`span.overline` in `.lede-main`) should still render in red. These are governed by `landing/style.css`, not `web-ng/src/styles.css`.
- Run `ng build --configuration production` from `web-ng/` and confirm zero errors.

---

## Task 2: Expand Teaser Character Window from 300 to 500

**File:** `/Users/sam/Projects/specview/api/modules/data/projects/service.py`

**Why:** The `firstNonHeadingSentence()` function in the frontend skips lines starting with `#`, `-`, `*`, `>`, `|`. Many braindumps open with a title heading then a section heading then a bullet list — the first real prose sentence may not appear until character 320–450. A 300-char teaser window captures only the heading block, causing the frontend to fall back to empty teaser display. Expanding to 500 chars covers the common braindump pattern.

**Change:** On line 101, change `teaser_chars=300` to `teaser_chars=500`.

**Exact before:**
```python
            "specs": _read_specs(d, include_content=False, teaser_chars=300),
```

**Exact after:**
```python
            "specs": _read_specs(d, include_content=False, teaser_chars=500),
```

### Verify

- Identify a project whose braindump begins with `# Title\n\n## Section\n\n- item` before any prose paragraph — i.e., a project whose first real sentence starts after character 300.
- Hit `GET /api/projects` and inspect the `specs[].teaser` field for that project. Confirm it contains a real prose sentence, not empty or heading-only text.
- Confirm projects with short braindumps (first prose within 300 chars) still return correct teasers — the `content[:500]` slice is safe for all lengths.
- Restart the API server and confirm it starts without errors.
- Run `pytest api/` to confirm no test regressions.

---

## Deferred Items (Do Not Implement)

These items were analyzed but excluded from this epic. Do not implement them here.

| Item | Why Deferred |
|------|-------------|
| Status bar `position: relative` + always-render | Requires Angular template edit (`app.component.html`) — different build surface from CSS-only scope |
| Hero grid `2fr 1fr 1fr` for Active section | Angular template change; deferred per braindump |
| `.file-item-meta-sep` → `.sep` rename | Not a visual issue; deferred to a cleanup pass |
| Newspaper column-first layout for small sections | No direction chosen; research phase |
