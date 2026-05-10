# UX: App Grid Polish — Semantic Color, Real Teasers, Breathing Room

## What we want

Three related improvements to the project grid in the Angular app (`web-ng`). They are small in code but high in visual impact. Each one independently useful.

---

## 1. Real teasers from file content

**Problem:** Cards in the Braindumps section show the static string `"Braindump — ready to generate"` regardless of what's in the braindump. This means every Braindumps card looks identical and the user gets no signal about what the project is actually about.

**What we have:** `project-teaser.ts` already has `firstNonHeadingSentence(content)` which skips markdown formatting lines and returns the first real prose sentence. It's already used for Specced and Ready-to-build sections. `teaserFor()` in `app.component.ts` already fetches `braindump.md` content into `leadContent` for the Braindumps branch — it just doesn't pass it through because `projectTeaser()` ignores it.

**Fix:** In `project-teaser.ts`, the Braindumps case (line ~83–85) should try `firstNonHeadingSentence(leadFileContent)` before falling back to the static string. Identical pattern to what Specced/Ready-to-build already do.

```ts
// current
if (section === 'Braindumps') {
  return 'Braindump — ready to generate';
}

// desired
if (section === 'Braindumps') {
  if (leadFileContent) {
    const sentence = firstNonHeadingSentence(leadFileContent);
    if (sentence) return sentence;
  }
  return 'Braindump — ready to generate';
}
```

No template changes needed.

---

## 2. Semantic color on section groups and cards

**Problem:** The project grid is monochrome. All sections look the same. There's no at-a-glance way to distinguish Active (generating) from Specced (ready) from Braindumps (needs work).

**Inspiration — ClawBoi:** Uses a 2fr / 1fr / 1fr headline grid with bold vertical rules between columns. The content hierarchy is typography-driven, not color-driven. We want to keep that restraint but add one semantic color signal per section: a left-border accent on each card.

**What we want:**
- **Active** section: green left border (`--status-running`) + green section title
- **Specced** section: blue left border (`--accent`) + blue section title
- **Braindumps** section: muted left border (`--ink-muted`), no title color change
- **Ready to build** / **Archive**: no left border (transparent, keeps spacing consistent)

**Implementation approach:**
- Add `[attr.data-section]="group.section"` to `.section-group` div in the grouped (all) view template
- Add `[attr.data-section]="activeSection()"` to `.file-column` in the single-section column view
- Define CSS custom property `--section-accent` via `[data-section]` attribute selectors
- Apply `border-left: 3px solid var(--section-accent, transparent)` on `.file-item` scoped by context (grid vs column)
- Color section-group title for Active and Specced only

**Key CSS concern:** The grid cards (`.section-group-cards`) and column cards (`.file-column`) have different padding/margin logic:
- Grid cards: should use `margin: 0; padding: 16px` (no negative margin in 2D grid)
- Column cards: keep `margin: 0 -Xpx; padding: Xpx` negative-margin hover bleed
Padding-left must be reduced by 3px to keep content alignment after adding the border.

---

## 3. More breathing room — bigger cards

**Problem:** Cards feel cramped at `padding: 12px 8px`. The visual density is high — content feels compressed especially at smaller viewport widths.

**ClawBoi reference values:**
- `memory-item`: `padding: 12px 0` (no horizontal padding; column provides it via `padding: 0 20px`)
- `memory-item:hover`: bleed via `margin: 0 -8px; padding: 12px 8px` — hover state bleeds into column padding
- `featured` memory item: title `font-size: 17px` (vs 15px normal), `-webkit-line-clamp: 3` on summary
- `newspaper-grid` sections: `padding: 0 20px` per column, `gap: 0` between columns, `border-right: 1px solid var(--border)` as column rule

**What we want:**
- Increase base `.file-item` padding: `12px 8px` → `16px 12px`
- Increase negative margin to match: `0 -8px` → `0 -12px`
- In grid (`.section-group-cards`): override to `margin: 0; padding: 16px` (no bleed needed in 2D grid)
- Increase min card width in `.section-group-cards` grid: `minmax(240px, 1fr)` → `minmax(260px, 1fr)`
- Increase section group spacing: `margin-bottom: 24px` → `margin-bottom: 32px`

No layout restructuring — just dimension increases.

---

## Affected files

- `web-ng/src/app/services/project-teaser.ts` — teaser fix (3 lines)
- `web-ng/src/app/app.component.html` — two `[attr.data-section]` bindings
- `web-ng/src/styles.css` — file-item sizing + semantic color CSS

---

---

## 4. Minimal icon library — CSS/SVG only, no TS changes

**Problem:** The app currently uses inline Unicode glyphs for op chip icons (↕ ⊡ ◁ etc.). These are inconsistent, hard to size, and some render poorly across platforms. We need a small, coherent icon set.

**History:** The app previously used Lucide icons via CDN (`<i data-lucide="...">` + `lucide.createIcons()` in `AfterViewChecked`). They were removed in commit `80c5b18` ("Lucide removal") because the CDN approach caused a race condition — icons sometimes failed to render before `createIcons()` ran. The nav section buttons had icons too:

| Section | Lucide icon |
|---------|-------------|
| Context | `ruler` |
| Active | `zap` |
| Ready to build | `hammer` |
| Specced | `check-circle` |
| Braindumps | `brain` |
| Archive | `archive` |

The `s.icon` field still exists in the `NAV_SECTIONS` array in `app.component.ts`, and the template had `@if (s.icon) { <i [attr.data-lucide]="s.icon"></i> }` — both were removed along with the Lucide bootstrap call.

**Restoring nav icons is part of this scope.** The icon library chosen here should cover both op chips and nav section buttons.

**Hard constraints:**
- No new npm packages that require TS/component changes
- No Angular icon component wrappers
- Ideally: drop in a font or SVG sprite and reference via CSS class or HTML attribute only
- Icons must work in dark mode (CSS `currentColor` or filter)

**Options to evaluate:**

1. **Lucide icons — SVG sprite** (`lucide-static`): pre-built `lucide.svg` sprite, use with `<use href="lucide.svg#icon-name">`. Zero JS. One `<svg>` asset. CSS `width/height/color` just work. ~1 kB per icon referenced. **Best fit.**

2. **Phosphor Icons — CSS font** (`@phosphor-icons/web`): load via `<link>` in `index.html`, use `<i class="ph ph-arrow-up">`. No TS, no imports. Heavier (full font file) but zero code change.

3. **Tabler Icons — SVG sprite**: same pattern as Lucide. Slightly more icons, similar weight.

4. **Heroicons — inline SVG copy-paste**: no dependency at all, but requires hand-copying SVG markup into HTML template. Acceptable for small counts (<20 icons).

5. **Bootstrap Icons — CSS font**: `<link>` in `index.html`, `<i class="bi bi-arrow-up">`. Large font file (~300 kB), probably overkill.

**Recommendation:** Evaluate Lucide SVG sprite first. Steps:
1. Download `lucide.svg` sprite (or build from `lucide-static` npm package assets — no TS needed)
2. Place in `web-ng/src/assets/icons/lucide.svg`
3. Reference in templates: `<svg class="icon"><use href="/assets/icons/lucide.svg#arrow-up"></use></svg>`
4. Add `.icon { width: 16px; height: 16px; stroke: currentColor; fill: none; }` to `styles.css`
5. Replace Unicode glyphs in `.btn-icon` spans — HTML-only change, no TS

If Lucide sprite is too heavy, fall back to copy-pasting ~15 Heroicons SVGs directly into a custom sprite file in `assets/`.

**Scope:** HTML template changes to op chips + any other icon-bearing elements. CSS `.icon` utility class. One asset file. Zero TS changes.

---

## What we are NOT doing

- Not changing the overall layout structure (3-column, section grouping)
- Not adding icons or badges to section headers
- Not changing typography beyond what's noted
- No new components, no new services
- No changes to landing page

---

## Design constraints

- Color must be semantic, not decorative: green = active/running, blue = complete output, muted = needs work
- Dark mode must work — all values use existing CSS variables
- Changes must be invisible in `data-section="Ready to build"` and `data-section="Archive"` — transparent border keeps spacing consistent without adding noise
- ClawBoi influence: breathing room and hierarchy, not color overload

---

## 5. Playground patterns not yet used in the app (audit findings)

Cross-referencing `playground.html` against `web-ng/src/styles.css` and `app.component.html`. Ranked most → least impactful for the app specifically.

### High impact — should adopt

**5a. Dashed border on AI-trigger buttons**
- Playground: `1px dashed var(--accent)` on generate/bootstrap buttons
- App today: solid borders on all buttons, no visual distinction between "do a thing" and "trigger AI"
- Proposal: apply dashed accent border to the main "Generate" / "Run" CTAs so users immediately read them as AI actions
- Scope: `styles.css` only — add `.btn-generate` or modifier class, no TS

**5b. Gen-status shimmer animation (active state)**
- Playground: `.gen-status-track` uses a `1.6s linear infinite` gradient sweep animation while generating
- App today: `.gen-status-bar--active` has no animation on the track — it's static
- Proposal: port the `@keyframes gen-shimmer` and apply to the track element during active state
- Scope: `styles.css` only

**5c. Diff block highlights**
- Playground: `.diff-block-remove` (red tint + strikethrough) and `.diff-block-add` (green tint) for inline spec diffs
- App today: no diff coloring in the markdown viewer — all diff text renders flat
- Proposal: add `.diff-block-remove` / `.diff-block-add` CSS rules; apply them in the diff HTML that `diffHtmlUnified` already produces
- Scope: `styles.css` only (the diff HTML is already generated by `app.component.ts`)

**5d. Retry button on gen-status failure state**
- Playground: failure state shows a "Retry" button bottom-right inside the status bar
- App today: `.sidebar-status-retry` class exists in `styles.css` but is not wired to a visible button in the failure flow
- Proposal: confirm the retry button is actually rendered in the template on failure; if not, add it
- Scope: small template addition + existing CSS

**5e. count-pulse animation on section badges**
- Playground: `.section-count-pulse` fires a 200ms scale keyframe when count changes
- App today: the class `section-count-pulse` is in the template but the animation keyframe may not be wired to actual count changes
- Proposal: verify `count-pulse` keyframe is defined in `styles.css` and triggers correctly; if missing, add it
- Scope: `styles.css` verification + possible keyframe add

### Medium impact — polish

**5f. poll-pulse on active status dots**
- Playground: `@keyframes poll-pulse` — box-shadow pulse (0→4px spread) on the green dot while a job is running
- App today: active dots use `dot-pulse` (opacity fade) — different feel; poll-pulse gives a more "live connection" signal
- Proposal: add `poll-pulse` as an alternative animation for the sidebar status dot during active polling
- Scope: `styles.css` keyframe + one rule change on `.status-dot.running` or similar

**5g. Red semantic badge variant**
- Playground: badge with `background: var(--red); color: #fff; font-weight: 600; border-radius: 2px; text-transform: uppercase`
- App today: all count badges use `background: var(--border)` — no error/alert variant
- Proposal: add `.badge--alert` modifier for use in error states or flagged items
- Scope: `styles.css` only

**5h. Context card hover triple**
- Playground: `.context-card:hover` has three simultaneous changes — `border-color: var(--ink)`, `background: rgba(0,0,0,0.015)`, `box-shadow: 0 2px 8px rgba(0,0,0,0.06)` (one of only two intentional shadows in the whole system)
- App today: no context cards in the app UI yet — but if we add a "project detail" card pattern, this is the hover spec
- Scope: future feature, low priority for now

### Lower impact — fine-tuning

**5i. Op-chip hover border subtlety**
- Playground: `.op-chip:hover` → `border-color: var(--ink-light)` (not `var(--ink)`)
- App today: hover may be using `var(--ink)` — a slightly too-heavy border on hover
- Proposal: verify and soften to `var(--ink-light)` on hover only
- Scope: one CSS rule

**5j. Single-active-chip enforcement**
- Playground: JavaScript clears `.active` from all chips before setting it on the clicked one — only one op chip active at a time
- App today: op chips are stateless (no `.active` class toggled) — the active operation is tracked in component state but not reflected as a CSS class on the chip
- Proposal: bind `[class.active]="activeOp() === op"` on each chip button so the active op is visually locked
- Scope: template binding + one CSS rule for `.op-chip.active`

**5k. pg-code unified code block style**
- Playground defines `.pg-code`: monospace, `background: #F5F5F5`, `border-left: 3px solid var(--ink-muted)`, `padding: 12px 16px`
- App today: markdown `<pre>` blocks have their own style in `.markdown-content pre`; in-line code uses a lighter background
- Not a critical gap, but worth unifying if we ever add a code-heavy spec type

---

## 6. Global action status strip — below section nav

**Problem:** When any action runs (spec generation, text ops), the only feedback visible from the grid view is three bouncing dots on the Generate button. There is no persistent status strip showing WHAT is happening and for WHICH project.

**History:** A `sidebar-status` row (dot + step text) exists in the sidebar but is only rendered inside `@if (showExpanded())` → `@if (activeProject())` — i.e., only when a project is already open in the reader. The `gen-status-bar gen-status-bar--active` bar with the animated track is also inside the expanded panel, guarded by `specGenLoading() && activeProject()`. Neither is visible from the grid.

**What we want:** A slim status strip rendered directly below `.section-nav` (in the main layout, not inside the expanded panel), always visible when `mode() !== 'idle'`:

```
[ ● generating analysis… — UX: App Grid Polish ]   ← green, below section tabs
```

- Shows when `mode() === 'active'`: green dot + step text + project name
- Shows when `mode() === 'success-flash'`: green "done" briefly then fades
- Shows when `mode() === 'failure'`: red + error text
- Hidden when `mode() === 'idle'` (default/connected state)
- Also covers text op loading (`aiLoading()`): shows "running [op]…" for the active text operation

**Why not just move sidebar-status up?** The sidebar-status is tied to the expanded panel and uses the sidebar's 16px horizontal margin. A top-level strip needs to span the full content width and sit in the page flow between the section nav and the search bar / grid.

**Implementation approach:**
- Add a new `<div class="action-status-strip">` block directly after `</nav>` (section nav close) in `app.component.html`
- Render it when `mode() !== 'idle' || aiLoading()`
- Reuse `sidebar-status-dot`, `sidebar-status-text` styles or add a `.action-status-strip` rule to `styles.css`
- The existing `mode()` computed signal and `specGenStep()` / `specGenProjectName()` are already available — no new signals needed
- For text ops: show `aiLoading()` condition with `activeOp()` label

**Scope:** `app.component.html` (one new block) + `styles.css` (one new rule). No TS changes.

**Note on nav icons (item 4) and status strip:** Both belong to the nav area. Good to implement together so the nav section gets a single coherent pass.
