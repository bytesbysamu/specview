# Implementation Guide: UX Polish — Newspaper Feel, Phase 2

## Overview
This epic closes the visual gap between Specview's landing page and the in-app experience by aligning typography, structural rules, overline patterns, icons, dark-mode contrast, and sidebar ordering inside `web-ng/`. Task 1 lands the foundation (overline utility class plus any minor token confirmations) that Tasks 2–5 consume in parallel; Task 6 (sidebar ordering) is independent and may run alongside any other task. The work converges on a single test: a side-by-side screenshot of the landing masthead and the app masthead being visually indistinguishable.

## Shared Pre-flight
- Confirm `web-ng/` builds cleanly with `ng build --configuration production` before making any change so regressions are attributable.
- Open the live playground at `http://localhost:8096/playground.html` in one tab and the running app in another for verbatim visual reference.
- Locate the global stylesheet entrypoint under `web-ng/src/styles/` and identify the typography, color-token, and dark-mode partial files.
- Verify the existing color tokens (`--ink`, `--ink-light`, `--ink-muted`, `--status-running`, `--border-dark`, `--accent-red`) are present and unchanged from the 2026-05-05 sync.
- Ensure Lucide icon imports are available in the components that render op chips, status indicators, and content icons.
- Keep every touched component file under 200 lines per principle P7; split prose if a file is approaching the limit.
- Treat the playground CSS as the contract — copy values verbatim (no rounding, no "close enough").
- After each task, take a focused screenshot in both light and dark mode to confirm intent before moving on.

---

## Task 1: Token & Overline Foundation  [Effort: 0.5 days]

### What
Establish the single overline utility class in the global stylesheet so downstream tasks have one canonical consumer for the red, uppercase, tracked overline pattern. Confirm any required tokens already exist; do not introduce a `--status-attention` token or a `--shadow-modal-dark` token.

### Files
- **Modify**: `web-ng/src/styles/typography.css` — add the `.overline` utility class with red color, uppercase transform, tracking, weight, and size copied verbatim from the playground
- **Modify**: `web-ng/src/styles/tokens.css` — verify presence of `--accent-red`, `--ink`, `--ink-light`, `--ink-muted`, `--border-dark`, `--status-running`; no additions

### Steps
1. Open the playground stylesheet and locate the overline rule (red text, `text-transform: uppercase`, `letter-spacing: 0.12em`, font-weight, font-size). Note the exact values without alteration.
2. Add a single `.overline` class to the global typography partial that mirrors those values verbatim, applying `color: var(--accent-red)` and using the existing typographic tokens.
3. Audit `web-ng/src/styles/tokens.css` to confirm every token referenced in the architecture doc exists; do not add new tokens (per scope: no `--status-attention`, no shadow tokens).
4. Run a quick search across `web-ng/src/` for ad-hoc overline styling (uppercase + red) to enumerate sites that Task 3 will migrate to the new class.
5. Commit the foundation as a discrete change so parallel tasks can branch from it cleanly.

### Verify
- The `.overline` class is defined exactly once in `web-ng/src/styles/typography.css`.
- No new tokens were added; `--status-attention` and shadow tokens remain absent.
- `ng build --configuration production` succeeds.
- A scratch element with `class="overline"` renders identical to the playground's overline in both modes.

---

## Task 2: Masthead & Nameplate Typography  [Effort: 1 day]

### What
Bring the app masthead into pixel parity with the landing masthead — 64px Playfair title, Source Serif italic 13px tagline, `align-items: flex-end` — and place the 3px `--ink` `border-top` nameplate rule on the section nav so it travels with the sticky behavior.

### Files
- **Modify**: `web-ng/src/app/components/masthead/masthead.component.html` — adjust markup so title and tagline sit on a flex row aligned to flex-end
- **Modify**: `web-ng/src/app/components/masthead/masthead.component.css` — set title to 64px Playfair, tagline to Source Serif italic 13px, container `align-items: flex-end`
- **Modify**: `web-ng/src/app/components/section-nav/section-nav.component.css` — add `border-top: 3px solid var(--ink)` so the nameplate rule belongs to the sticky nav

### Steps
1. In the masthead template, ensure the title and tagline live in a flex container with no extraneous wrappers; the tagline should be a sibling of the title for baseline-friendly alignment.
2. In the masthead component CSS, set the title to 64px Playfair Display with the weight used by the landing, the tagline to Source Serif 4 italic at 13px, and the container's `align-items` to `flex-end` so the tagline sits on the title's baseline ledge.
3. Remove any leftover bottom border, shadow, or rule from the masthead component itself; the nameplate rule does not live here.
4. In the section-nav component CSS, add a 3px solid `--ink` `border-top` and confirm it persists when the nav is in its sticky state.
5. Open both light and dark modes and compare the app masthead with the landing masthead for spacing, weight, and the nameplate rule's position when the page is scrolled.
6. Keep both component files under 200 lines; refactor only as needed to stay within budget.

### Verify
- Inspecting the title shows `font-family: "Playfair Display"` and `font-size: 64px`; tagline shows Source Serif italic 13px.
- The masthead container computes `align-items: flex-end`.
- Scrolling the app shows the 3px `--ink` rule traveling with the sticky section nav, not anchored to the masthead bottom.
- `ng build --configuration production` succeeds.

---

## Task 3: Overline Adoption Across App  [Effort: 1 day]

### What
Apply the foundation `.overline` class at three concrete sites — section group headers in the project grid, the file-type label above the spec reader title, and error-state messaging — replacing any duplicated overline styling so the class has one definition and three consumers.

### Files
- **Modify**: `web-ng/src/app/components/project-grid/project-grid.component.html` — bind `class="overline"` on group header elements
- **Modify**: `web-ng/src/app/components/spec-reader/spec-reader.component.html` — render a file-type label above the title using the overline class
- **Modify**: `web-ng/src/app/components/spec-reader/spec-reader.component.ts` — derive the file-type string (e.g., "ARCHITECTURE") from the filename
- **Modify**: `web-ng/src/app/components/error-banner/error-banner.component.html` — apply the overline class to the leading error label
- **Modify**: any component CSS files where ad-hoc overline styling existed — delete the local rules

### Steps
1. In the project-grid template, locate the group header markup and apply the `overline` class; remove any local color, tracking, or uppercase rules from the corresponding component CSS.
2. In the spec-reader template, add a small label element above the spec title and bind it to a derived file-type string; apply the `overline` class to that label.
3. In the spec-reader component class, compute the file-type label from the filename (e.g., strip extension, uppercase) — keep this a pure pipe or getter, no service.
4. In the error-banner template, wrap or replace the leading error label with an element carrying the `overline` class so error states announce themselves with the same editorial flag.
5. Search for any remaining inline overline styling (red + uppercase + tracking) across `web-ng/src/` and remove it; the class is now the only source.
6. Confirm visually that all three call sites render identically in both modes and at the same color, tracking, and weight.

### Verify
- `grep` shows no component-level CSS defining `text-transform: uppercase` together with red color outside `typography.css`.
- The reader displays a red "ARCHITECTURE" / "EPIC" / "ANALYSIS" label above the spec title corresponding to the filename.
- Project grid section headers and the error banner's leading label render with the same overline treatment.
- `ng build --configuration production` succeeds.

---

## Task 4: Icon System Standardization & Op Chip Mapping  [Effort: 1 day]

### What
Standardize content icons at 13px / stroke-width 1.75 with semantic color by context, and wire the static op-chip-to-Lucide mapping (expand → arrow-up-down, compress → minimize-2, clarify → help-circle, simplify → feather, tldr → align-left, bullets → list, brainstorm → sparkles, style → palette, undo → rotate-ccw, redo → rotate-cw) so every operation in the chain renders its mapped icon.

### Files
- **Create**: `web-ng/src/app/components/op-chip/op-icon-map.ts` — static constant mapping op name to Lucide icon name
- **Modify**: `web-ng/src/app/components/op-chip/op-chip.component.html` — render the mapped icon alongside the op label, inheriting `currentColor`
- **Modify**: `web-ng/src/app/components/op-chip/op-chip.component.ts` — import and consume the mapping constant
- **Modify**: `web-ng/src/app/components/spec-reader/spec-reader.component.css` — set content icons to 13px / stroke-width 1.75 with `--ink-light` color
- **Modify**: `web-ng/src/app/components/editor-toolbar/editor-toolbar.component.css` — apply the same 13px / 1.75 standard with semantic context colors
- **Modify**: any component using `font-size: 1em` for icons — replace with explicit 13px

### Steps
1. Create a single TypeScript constant exporting the op-name to Lucide-icon-name lookup with all ten mappings listed in the architecture doc; do not export it as a registry or service.
2. In the op-chip component class, import the constant and resolve the icon name from the chip's op input; render it in the template next to the label and let the icon inherit `currentColor` so chip state colors propagate naturally.
3. Audit every Lucide icon usage in the spec reader, editor toolbar, and any inline content position; set explicit `width="13"`, `height="13"`, and `stroke-width="1.75"` attributes (or the component-equivalent inputs).
4. Apply semantic color per context: status icons take their parent status token, navigational icons stay at `--ink-muted`, content/state-bearing icons use `--ink-light` to clear the 3:1 dark-mode floor.
5. Search for any remaining `font-size: 1em` patterns on icon containers and replace with the explicit 13px size to eliminate inheritance.
6. Verify each op in a sample chain (expand, compress, clarify, simplify, tldr, bullets, brainstorm, style, undo, redo) renders the correct mapped icon.

### Verify
- All ten op chips display their mapped Lucide icon in a sample chain.
- Inspecting a content icon shows computed `width: 13px`, `height: 13px`, `stroke-width: 1.75`.
- No `1em` icon sizing remains in `web-ng/src/`.
- `ng build --configuration production` succeeds.

---

## Task 5: Dark-Mode Contrast Fixes  [Effort: 1 day]

### What
Apply four targeted dark-mode fixes — modal elevation via a single sanctioned shadow (scoped inside the modal component), sticky editor toolbar border weight, section nav structural edge using `--border-dark`, and the icon contrast floor at `--ink-light` for meaningful icons — without introducing new tokens.

### Files
- **Modify**: `web-ng/src/app/components/modal/modal.component.css` — add a dark-mode-only `box-shadow` rule local to this component
- **Modify**: `web-ng/src/app/components/editor-toolbar/editor-toolbar.component.css` — strengthen the dark-mode border so the sticky toolbar edge reads
- **Modify**: `web-ng/src/app/components/section-nav/section-nav.component.css` — set the nav's structural edge to `--border-dark` in dark mode
- **Modify**: `web-ng/src/styles/dark-mode.css` (or the equivalent dark partial) — ensure meaningful icons resolve to at least `--ink-light` while navigational icons may stay at `--ink-muted`

### Steps
1. Inside the modal component CSS, add a `:host-context(.dark)` (or equivalent) block with a single `box-shadow` value chosen to elevate the modal cleanly above the dimmed backdrop; keep the rule local and document it as the one sanctioned shadow exception.
2. In the editor-toolbar component CSS, upgrade the dark-mode bottom or top border so the sticky toolbar visibly anchors against the editor surface; do not add a shadow here.
3. In the section-nav component CSS, set the dark-mode separator (the structural edge below the nameplate rule, if any) to use `var(--border-dark)` so it reuses the existing high-contrast token.
4. Audit the dark-mode partial for any rule that lets meaningful icons (status, content) drop below `--ink-light`; raise them to the floor while leaving navigational chrome (back, close, menu) free to remain at `--ink-muted`.
5. Verify that `--status-running` is still `#22A66A` everywhere and that no rule in this task introduces amber for any state.
6. Confirm gray (`--ink-muted`) is not being used to communicate any state — only for absence-of-state.

### Verify
- In dark mode, opening the modal shows clear visual separation from the dimmed backdrop via the local shadow.
- The sticky editor toolbar reads as a distinct horizontal break in dark mode.
- The section nav's structural edge in dark mode uses `--border-dark` and reads at the same hierarchy as the nameplate rule.
- All meaningful icons in dark mode meet or exceed `--ink-light` (`#A0A0A0`); `--status-running` is unchanged green.
- `ng build --configuration production` succeeds.

---

## Task 6: Spec File Sidebar Ordering  [Effort: 0.5 days]

### What
Force the spec file sidebar to render in canonical methodology order (braindump → analysis → epic → architecture → timeline → implementation-guide) regardless of filesystem order, with unknown files appended after the canonical set. The sort happens client-side in the Angular SPA so the Flask API stays neutral.

### Files
- **Modify**: `web-ng/src/app/services/spec-files.service.ts` (or the existing sidebar service) — apply a static canonical-order sort to the file list returned by the API
- **Modify**: `web-ng/src/app/components/spec-sidebar/spec-sidebar.component.ts` — consume the sorted list without re-sorting

### Steps
1. In the sidebar service, define a static array constant containing the canonical sequence (braindump, analysis, epic, architecture, timeline, implementation-guide) — no config, no manifest.
2. After fetching the file list from the Flask API, map each filename to its index in the canonical array; treat unmatched filenames as a higher index so they sort after the known set.
3. Sort the list by canonical index, breaking ties for unknown files alphabetically so their order is stable.
4. Ensure the component template renders the sorted list as-is and does not apply a secondary sort.
5. Test with a project containing all six canonical files plus one unknown file to confirm the canonical six lead and the unknown follows.

### Verify
- A project with files created out of order on disk renders in the canonical sequence in the sidebar.
- Unknown files appear after the canonical list, alphabetically among themselves.
- The Flask API response is unchanged (no server-side sorting added).
- `ng build --configuration production` succeeds.