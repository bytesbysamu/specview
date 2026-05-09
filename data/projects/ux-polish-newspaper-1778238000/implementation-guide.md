# Implementation Guide: UX Polish — Newspaper Feel, Phase 2

## Overview
Minimal, surgical CSS/template edits to `app.component.html`, `app.component.ts`, and `web-ng/src/styles.css`. No component extraction. No new libraries. The playground at `http://localhost:8096/playground.html` is the visual contract — copy values verbatim.

**Actual file paths (monolithic architecture):**
- All styles → `web-ng/src/styles.css`
- All markup → `web-ng/src/app/app.component.html`
- All logic → `web-ng/src/app/app.component.ts`
- HTTP service → `web-ng/src/app/services/projects.service.ts`

## Shared Pre-flight
- Build passes: `ng build --configuration production`.
- Open `http://localhost:8096/playground.html` alongside the app — it is the Figma.
- Dark mode selector throughout the codebase is `[data-theme="dark"]` (not `.dark`).

---

## Task 1: Token & Overline Foundation  [Effort: 0.5 days]

### What
Add `.overline` utility class to `styles.css`. Verify the six required tokens exist. Token name correction: the token is `--red`, not `--accent-red`.

### Files
- **Modify**: `web-ng/src/styles.css`

### Steps
1. Open the playground at `#pg-comp-overline` — copy the overline rule verbatim (red, uppercase, `0.12em` tracking, weight, size).
2. Add a single `.overline` class to `styles.css` using `color: var(--red)` (not `--accent-red` — that token does not exist).
3. Confirm these six tokens are present and unchanged: `--red`, `--ink`, `--ink-light`, `--ink-muted`, `--border-dark`, `--status-running`.
4. Search `app.component.html` and `styles.css` for ad-hoc uppercase + red styling to enumerate Task 3 migration sites.

### Verify
- `.overline` defined once in `styles.css`, uses `var(--red)`.
- No new tokens added.
- `ng build --configuration production` passes.

---

## Task 2: Masthead & Nameplate Typography  [Effort: 1 day]

### What
Bring the app masthead to pixel parity with the landing masthead: 64px Playfair title (currently 56px), Source Serif italic 13px tagline, `align-items: flex-end`. Add 3px `--ink` `border-top` nameplate rule to the section nav.

Visual reference: `http://localhost:8096/playground.html#pg-comp-masthead` and `http://localhost:8096/index.html`.

### Files
- **Modify**: `web-ng/src/styles.css` — `.masthead-title`, `.masthead-tagline`, `.masthead` container, `.section-nav`
- **Modify**: `web-ng/src/app/app.component.html` — verify flex structure of masthead

### Steps
1. In `styles.css`, set `.masthead-title` to `font-size: 64px` Playfair Display. Current value is 56px.
2. Set `.masthead-tagline` to Source Serif 4 italic at 13px — match the playground tagline verbatim.
3. Set `.masthead` container `align-items: flex-end`.
4. Add `border-top: 3px solid var(--ink)` to `.section-nav` (not to `.masthead`) so the nameplate rule travels with the sticky nav.
5. Remove any bottom border or shadow from the masthead itself.

### Verify
- `.masthead-title` computes `font-size: 64px`, Playfair Display.
- `.masthead-tagline` computes Source Serif 4 italic, 13px.
- Scrolling shows the 3px rule traveling with the sticky nav.
- `ng build --configuration production` passes.

---

## Task 3: Overline Adoption Across App  [Effort: 1 day]

### What
Apply `.overline` class at three sites in `app.component.html`: section group headers in the project grid, the file-type label above the spec reader title, and error-state messaging. Remove any duplicated local overline styling.

Visual reference: `http://localhost:8096/playground.html#pg-comp-overline`.

### Files
- **Modify**: `web-ng/src/app/app.component.html`
- **Modify**: `web-ng/src/app/app.component.ts` — derive file-type string from filename
- **Modify**: `web-ng/src/styles.css` — delete ad-hoc overline rules if any

### Steps
1. In the project-grid section headers markup, add `class="overline"` and remove any local color/tracking/uppercase rules from `styles.css`.
2. Add a file-type label element above the spec title in the reader markup; bind it to a computed getter in `app.component.ts` that derives the label from the filename (e.g. `architecture.md` → `"ARCHITECTURE"`). Apply `.overline` class.
3. Apply `.overline` to the leading error label in any error state markup.
4. Grep for remaining uppercase + red combinations in `styles.css` and remove them — `.overline` is now the only source.

### Verify
- No component-level rule defines `text-transform: uppercase` alongside red color outside `styles.css`.
- Reader shows "ARCHITECTURE" / "EPIC" etc. above the spec title.
- `ng build --configuration production` passes.

---

## Task 4: Remove Lucide CDN — Replace with Emojis  [Effort: 0.5 days]

### What
Remove the Lucide CDN dependency entirely. Replace op-chip icons with plain emoji, matching the approach used in ClawBoi and the landing page (no external icon library). Remove the `lucide.createIcons()` call.

Visual reference: ClawBoi source and `http://localhost:8096/index.html` for emoji usage patterns.

### Files
- **Modify**: `web-ng/index.html` — remove Lucide CDN `<script>` tag
- **Modify**: `web-ng/src/app/app.component.ts` — remove `lucide.createIcons()` call and the `declare const lucide` declaration
- **Modify**: `web-ng/src/app/app.component.html` — replace all `<i data-lucide="...">` elements with emoji equivalents
- **Modify**: `web-ng/src/styles.css` — remove any Lucide-specific SVG overrides

### Op emoji mapping
| Op | Emoji |
|----|-------|
| expand | ↕ |
| compress | ⊡ |
| clarify | ? |
| simplify | ✦ |
| tldr | ≡ |
| bullets | • |
| brainstorm | ✦ |
| style | ✎ |
| undo | ↩ |
| redo | ↪ |

Adjust emoji choices to match whatever ClawBoi uses — ClawBoi is the canonical reference.

### Steps
1. Remove the Lucide CDN `<script>` from `web-ng/index.html`.
2. Remove `lucide.createIcons()` from `ngAfterViewChecked` in `app.component.ts` and remove the `declare const lucide` at the top.
3. Replace every `<i data-lucide="icon-name">` in the template with a plain text emoji span.
4. Remove any global `svg { width: 1em; height: 1em; }` rules that were only there for Lucide SVGs, if they conflict with other usage.

### Verify
- No Lucide CDN request in Network tab.
- Op chips display emoji labels.
- No console errors about `lucide` being undefined.
- `ng build --configuration production` passes.

---

## Task 5: Dark-Mode Contrast Fixes  [Effort: 1 day]

### What
Four targeted fixes using `[data-theme="dark"]` selectors (the actual selector used in this codebase — not `.dark`). Visual reference: `http://localhost:8096/playground.html#pg-states` and `#pg-comp-toolbar`.

### Files
- **Modify**: `web-ng/src/styles.css`

### Steps
1. Modal elevation: inside the `[data-theme="dark"] .modal` (or equivalent) rule block, add a `box-shadow` matching the playground's dark modal treatment. This is the only sanctioned shadow in the system.
2. Editor toolbar: strengthen the dark-mode border on `.editor-toolbar` so the sticky edge reads — match playground value verbatim.
3. Section nav edge: set `.section-nav` border to `var(--border-dark)` under `[data-theme="dark"]`.
4. Icon contrast: any meaningful icon (status, content) in dark mode should resolve to at least `var(--ink-light)` (`#A0A0A0`). Navigational icons may stay at `--ink-muted`.
5. Confirm `--status-running` is still `#22A66A` — do not change it.

### Verify
- Dark mode modal has visible elevation above backdrop.
- Sticky toolbar reads as a distinct horizontal break in dark mode.
- Section nav structural edge uses `--border-dark`.
- No amber color introduced anywhere.
- `ng build --configuration production` passes.

---

## Task 6: Spec File Sidebar Ordering  [Effort: 0.5 days]

### What
Force canonical reading order (braindump → analysis → epic → architecture → timeline → implementation-guide) in the sidebar, regardless of API response order. Client-side sort in `projects.service.ts`; unknown files append alphabetically.

### Files
- **Modify**: `web-ng/src/app/services/projects.service.ts` — apply canonical sort after fetching file list

### Steps
1. In `projects.service.ts`, after the file list is returned by the API, define a static canonical array: `['braindump', 'analysis', 'epic', 'architecture', 'timeline', 'implementation-guide']`.
2. Map each filename (strip `.md`) to its canonical index; unmatched files get a high index.
3. Sort by index; break ties for unknown files alphabetically.
4. The template in `app.component.html` renders the list as-is — no secondary sort.

### Verify
- Sidebar renders in canonical order regardless of API response order.
- Unknown files appear after canonical set, alphabetically.
- Flask API response unchanged.
- `ng build --configuration production` passes.
