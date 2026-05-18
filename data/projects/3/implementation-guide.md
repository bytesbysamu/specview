# Implementation Guide: App UI Mockups

## Overview
Apply the validated design decisions from `landing/app-overview.html` mockup to the live Angular app (`web-ng/`). The mock and app diverge significantly in grid layout, card styling, section headers, typography, and color system. This guide brings the app in line with the mock.

**Key insight**: The Angular app does NOT import `landing/style.css`. All changes go directly into `web-ng/src/styles.css` and `web-ng/src/app/app.component.html`.

## Shared Pre-flight
- Confirm Docker API is running: `curl -s http://localhost:8095/api/health`
- Open `landing/app-overview.html` at `http://localhost:8097/app-overview.html` as visual reference
- Open `http://localhost:8095/` (live app via Docker) for comparison
- Read `web-ng/src/styles.css` and `web-ng/src/app/app.component.html` before any edits

---

## Task 1: Grid System + Card Styling  [Effort: 0.5 days]

### What
Update `.section-group-cards` grid and `.file-item` card styling in the app to match the mockup: wider cards (280px min), no grey background fill, vertical-only card separators, more padding.

### Agent
spec-frontend

### Files
- **Modify**: `web-ng/src/styles.css` — update `.section-group-cards`, `.file-item`, `.file-item:hover`

### Steps
1. In `web-ng/src/styles.css`, find `.section-group-cards` and change:
   - `grid-template-columns: repeat(auto-fill, minmax(240px, 1fr))` → `repeat(auto-fill, minmax(280px, 1fr))`
   - `gap: 1px` → `column-gap: 0; row-gap: 0`
   - Remove `background: var(--border)` (this caused grey fill on empty columns)
2. Find `.file-item` and change:
   - `padding: 12px 8px` → `padding: 20px 24px`
   - `margin: 0 -12px` → remove (no negative margin)
   - `border-bottom: 1px solid var(--border)` → `border-left: 1px solid var(--border)`
   - Remove `border-left: 3px solid var(--section-accent, transparent)` if present (state not category)
3. Add `.file-item:first-child { border-left: none; }` — no border on first card in each row
4. Update `.file-item:hover`:
   - `background: rgba(0,0,0,0.025)` → `rgba(0,0,0,0.02)` (subtler)
   - Remove any `margin` or `padding` changes on hover
5. Update dark mode hover: `rgba(255,255,255,0.04)` → `rgba(255,255,255,0.03)`

### Verify
- Cards show vertical separators only (no horizontal borders between cards)
- No grey background fill on sections with fewer cards than columns
- Cards have generous 20px 24px padding
- No colored left border on cards

---

## Task 2: Section Headers + Dividers  [Effort: 0.5 days]

### What
Update section group headers to use colored overline with 2px ink underline spanning title text only. Add section dividers between groups.

### Agent
spec-frontend

### Files
- **Modify**: `web-ng/src/styles.css` — update `.section-group`, `.section-group-header`, `.section-group-title`
- **Modify**: `web-ng/src/styles.css` — add section color tokens and `[data-section]` selectors
- **Modify**: `web-ng/src/app/app.component.html` — add `[attr.data-section]` to section groups if not present

### Steps
1. Add section color tokens to `:root` in `styles.css`:
   ```css
   --color-active:    #22A66A;
   --color-specced:   #567B95;
   --color-ready:     #7B6BAE;
   --color-braindump: #A08060;
   ```
   And dark mode equivalents.
2. Add `[data-section]` attribute selectors:
   ```css
   .section-group[data-section="Active"]         { --section-color: var(--color-active); }
   .section-group[data-section="Specced"]        { --section-color: var(--color-specced); }
   .section-group[data-section="Ready to build"] { --section-color: var(--color-ready); }
   .section-group[data-section="Braindumps"]     { --section-color: var(--color-braindump); }
   ```
3. Update `.section-group`: add `padding-bottom: 24px; border-bottom: 1px solid var(--border)` and `:last-child` override.
4. Update `.section-group-header`: set `align-items: center; gap: 8px; border-bottom: none; margin-bottom: 16px`.
5. Update `.section-group-title`: add `display: inline-block; border-bottom: 2px solid var(--ink); padding-bottom: 4px; color: var(--section-color, var(--ink-muted))`.
6. Update `.section-group-count` to use pill badge style: `background: var(--border); color: var(--ink-light); padding: 2px 8px; border-radius: 2px; font-size: 10px`.
7. Verify `app.component.html` has `[attr.data-section]="group.section"` on `.section-group` divs (was added in previous exec-guide).

### Verify
- Section header titles show in their section's color
- 2px ink underline spans only the title text (not full width)
- 1px border divider between sections
- Count badges are grey pills

---

## Task 3: Typography — Serif Teasers  [Effort: 0.5 days]

### What
Change teaser font to Source Serif 4 at 14px. Add featured first-card styling.

### Agent
spec-frontend

### Files
- **Modify**: `web-ng/src/index.html` — add Source Serif 4 to Google Fonts if missing
- **Modify**: `web-ng/src/styles.css` — update `.file-item-teaser`, add featured `:first-child` rules

### Steps
1. Check `web-ng/src/index.html` Google Fonts link. If Source Serif 4 is missing, add it. If present, verify it includes weights 400 and 600.
2. In `styles.css`, update `.file-item-teaser`:
   - `font-family: 'Source Serif 4', Georgia, serif`
   - `font-size: 14px` (was 13px)
3. Add featured first card rules:
   ```css
   .section-group-cards .file-item:first-child .file-item-title { font-size: 17px; }
   .section-group-cards .file-item:first-child .file-item-teaser { -webkit-line-clamp: 3; }
   ```

### Verify
- Teaser text renders in serif font (visually distinct from Source Sans)
- First card in each section has larger title (17px vs 15px) and 3-line teaser clamp

---

## Task 4: Status Bar Colors  [Effort: 0.5 days]

### What
Update the generation status bar to use playground 5.7 colors instead of the current styling.

### Agent
spec-frontend

### Files
- **Modify**: `web-ng/src/styles.css` — update `.gen-status-bar` state modifiers and add status tokens

### Steps
1. Add status color tokens to `:root` if not present:
   ```css
   --status-idle:    #1a6b30;
   --status-active:  #7a5800;
   --status-success: #1a6b30;
   --status-failure: #C41E3A;
   ```
   And dark mode equivalents.
2. Update `.gen-status-bar` to use white text: `color: #fff`.
3. Update state modifiers to use the new tokens:
   - `--idle`: `background: var(--status-idle)`
   - `--active`: `background: var(--status-active)`
   - `--success`: `background: var(--status-success)`
   - `--failure`: `background: var(--status-failure)`
4. Ensure consistent height across all states — same padding `8px 16px` on all.
5. Add shimmer track styling for active state if not present:
   ```css
   .gen-status-bar--active .gen-status-track {
     position: absolute; top: 0; left: 0; right: 0; height: 2px;
     background: linear-gradient(90deg, transparent, var(--accent), #fff, var(--accent), transparent);
     background-size: 200% 100%;
     animation: gen-shimmer 1.6s linear infinite;
   }
   ```

### Verify
- Status bar shows dark amber (#7a5800) when active, dark green when idle/success, red when failure
- Shimmer track animates on active state
- All 4 states have identical height

---

## Task 5: Badge System  [Effort: 0.5 days]

### What
Add badge CSS classes for count pills and state badges (NEW, COMPLETE, READY).

### Agent
spec-frontend

### Files
- **Modify**: `web-ng/src/styles.css` — add `.badge`, `.badge--new`, `.badge--complete`, `.badge--ready`

### Steps
1. Add badge base class:
   ```css
   .badge {
     display: inline-block; font-size: 9px; font-weight: 600;
     font-family: 'Source Sans 3', sans-serif;
     text-transform: uppercase; letter-spacing: 0.05em;
     padding: 2px 6px; border-radius: 2px;
     background: var(--border); color: var(--ink-light);
     vertical-align: middle;
   }
   ```
2. Add state variants:
   ```css
   .badge--new      { background: var(--red); color: white; }
   .badge--complete { background: var(--status-success-bg); color: white; }
   .badge--ready    { background: var(--accent); color: white; }
   ```
3. Add dark mode opacity for colored badges:
   ```css
   [data-theme="dark"] .badge--new,
   [data-theme="dark"] .badge--complete,
   [data-theme="dark"] .badge--ready { opacity: 0.85; }
   ```

### Verify
- `.badge` renders as a grey pill with count text
- `.badge--new` is red, `.badge--complete` is green, `.badge--ready` is accent blue
- All badges visible in both light and dark themes
