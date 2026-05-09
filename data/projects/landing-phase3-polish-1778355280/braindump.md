# Landing Page Polish — Phase 3

> **Visual reference:** [Design Playground](http://localhost:8096/playground.html) — use this as Figma. Every component, token, state, and animation is live and inspectable.
> **App reference:** `ux-polish-newspaper-1778238000` — Phase 2 closed the app↔landing gap. Phase 3 closes the remaining gaps on the landing itself and ensures Phase 2 app changes are reflected in the landing too.
> **WIP file:** `landing/landing-v2.html` — this is the active landing page under development. NOT `landing/index.html` (old baseline) and NOT `landing/wireframe.html` (layout scratch pad).

---

## Origin and Phase History

**Phase 1** — ClawBoi established the newspaper aesthetic: masthead, overline, section tabs, 3-column grid, Playfair + Source Serif + Source Sans, borders not shadows, cream/ink.

**Phase 2** — `ux-polish-newspaper-1778238000` closed the gap between the Angular app (`web-ng/`) and the landing. Six tasks: overline foundation, masthead typography, overline adoption, dark-mode contrast, icon system, sidebar ordering. Executed 2026-05-09. All 6 tasks complete.

**Phase 3 (this epic)** — Polish the landing page (`landing/landing-v2.html`) to the same editorial standard. The landing is *more* complete than it was after Phase 2 app work — new sections were added (stat strip, steps, comparison table, FAQ, how-it-works) — but many design system details are still missing or inconsistent. Phase 3 also introduces a second pull quote and the update banner.

**Current WIP URL:** `http://localhost:8096/landing-v2.html`

---

## Design philosophy (unchanged from Phase 2)

**Dieter Rams minimalism + editorial newspaper layout.**

- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace create structure; shadows do not exist
- Ink on paper: cream (`#FFFEF9`) not white, near-black (`#121212`) not black
- Interaction is quiet — hover is a whisper of `rgba` background, nothing more
- Density without clutter: if it doesn't communicate something, it doesn't exist

→ [All design tokens live](http://localhost:8096/playground.html#pg-tokens)

---

## Current state of landing-v2.html

### What exists

After Phase 2 app work and the session work that preceded this epic, `landing-v2.html` has:

1. **Masthead** — Playfair 64px title, Source Serif italic tagline (✓ matches app after Phase 2), theme toggle, edition label, date
2. **Section bar** — What | What ships | See it | Start | FAQ
3. **Hero / lede** — two-column: overline + headline + deck + CTA row | 1px divider | aside (gen-status-bar + inline file list)
4. **Stat strip** — 4 stat-items: 44.5s / 5 files / 0 human code lines / Free to start
5. **What ships** — full `.output-grid` with 5 `.output-card` elements (Analysis, Epic, Architecture, Timeline, Implementation Guide)
6. **How it works** — `.steps` 3-column: Braindump / Generate / Read & Build, each with `.step-code` terminal block
7. **See it** — `.gen-status-bar--success` + `.demo-strip` with `.markdown-content` 2-column newspaper layout
8. **Pull quote** — single centered `.pullquote-single`
9. **Comparison table** — `.compare-table`: Specview vs Lovable/Bolt/Kiro across 6 dimensions
10. **Start building / Pricing** — Free + Pro, `.pricing-grid` column layout
11. **FAQ** — 5 `<details class="faq-item">` accordion items
12. **Footer** — brand / copy / GitHub + Twitter/X + Contact

### CSS classes defined in style.css but NOT yet used in landing-v2.html

From the playground component map:
- `.aside-list` — semantic file-timing list for hero aside (replacing inline-styled div/span pile)
- `.metrics-bar` — pipe-separated ticker strip (defined, never instantiated in v2)
- `.context-card` / `.context-card__label` / `.context-card__desc` — "Who it's for" section
- `.update-banner` — full-bleed ink bar with CTA above footer
- `.pullquote-row` (two-column variant with `.pullquote-divider`) — `landing-v2.html:259` has `class="pullquote-row pullquote-single"` on the same element, which breaks the `1fr 1px 1fr` grid (one child, no divider). Remove `.pullquote-row` from the single-quote element OR promote it to a real two-column row with a second quote and `.pullquote-divider`.
- `thinking-pulse` animation — only `dot-pulse` used in hero aside (accent-colored distinction missing)
- `rise` animation — not applied to output-card stagger

---

## Typography gaps

### 1. Hero aside file list — wrong markup

The hero aside uses a wall of `<div style="display:flex;...">` inline-styled elements for the file list. The design system has `.aside-list` — a semantic `<ul>` with `display: flex; justify-content: space-between` rows showing filename + timing side by side. Using `.aside-list` would:
- Remove 30+ lines of inline styles
- Give each row the proper Source Sans treatment
- Allow dark mode to work correctly without per-element overrides

→ [Aside list demo](http://localhost:8096/playground.html#pg-comp-masthead)

### 2. Step titles — missing overline

The `.step-num` (96px Playfair at `var(--border)` opacity) is decorative only. But no `.overline` label announces the step category. The app Phase 2 added `.overline` to section group headers. The landing steps should have `<span class="overline">Step 1</span>` above each `.step-title` — same red editorial voice as the hero.

→ [Overline demo](http://localhost:8096/playground.html#pg-comp-overline)

### 3. Section headings — no overline kicker

The full-width `.section-heading` divider bars (e.g. "What ships", "How it works", "See it") are plain Source Sans uppercase on `--bg`. In the app, section group headers now use `.overline`. The landing section headings should get a matching treatment — either a red `.overline` kicker above the `.section-heading`, or the `.section-heading` itself adopts `color: var(--red)` (currently `var(--ink-light)`). The design-system doc says `.overline` is for use inside sections; the `.section-heading` can carry its own accent.

### 4. FAQ answers — wrong body font

`.faq-answer` uses `font-family: var(--body)` (Source Serif 4) — correct for paragraph reading text. But the FAQ questions in `summary` use `font-family: var(--serif)` (Playfair Display) at 18px. This is correct — Playfair for questions (editorial, scannable) and Source Serif for answers (reading). Verify this is rendering correctly; the CSS definition should match.

### 5. Step-code in FAQ self-host answer

The FAQ "Can I self-host?" answer has inline `<code>git clone</code>` and `<code>docker compose up</code>`. These should be a `<div class="step-code">` block — giving the CLI sequence the same 3px left border + monospace treatment as the How-it-works steps. Currently they read as plain inline code.

---

## Color issues

### 1. `color: var(--border)` as text color

In the hero aside, `timeline.md` and `implementation-guide.md` (not-yet-generated files) use `color: var(--border)` (`#DFDFDF`) for text. This is the border color used as ink — semantically wrong. The correct token for "unavailable/not-generated" is `--ink-muted` at reduced opacity, or just `--border` for the icon, but not for text. These files should use `color: var(--ink-muted)` with `opacity: 0.5` — still faded, semantically consistent.

### 2. gen-status-bar dot color — not a bug

The `.gen-status-dot` has an explicit `background: #fff` in style.css — it is always white regardless of bar state. White on any colored bar (amber active, green success, red failure) is correct and readable. No change needed here. The Phase 2 rule (`--status-running` is green, never amber) applies to the BAR background modifier class, not the dot.

### 3. Inline style opacity values — non-standard

The hero aside uses `opacity: 0.5`, `opacity: 0.85`, `opacity: 0.6` as inline attributes on spans. These are arbitrary. The design system uses:
- `var(--ink-muted)` for secondary text (~60% of ink visually)
- `var(--ink-light)` for tertiary text (~45%)
- `var(--border)` for truly faded/unavailable

Replace inline opacities with proper color tokens. Opacity on text is not the design system pattern — color tokens are.

### 4. Comparison table `.col-them` column

The competitor column uses `color: var(--ink-muted)`. This is correct — `--ink-muted` = no semantic meaning = neutral competitor data. Good. Verify it renders correctly in dark mode.

---

## Button uniformity

### Current state

Both `.btn-primary` and `.btn-secondary` are defined once in style.css and used consistently throughout landing-v2.html. No inline button overrides exist. This is correct.

```css
/* From style.css — verbatim */
.btn-primary {
  background: var(--ink);
  color: var(--bg);
  border: 1px solid var(--ink);
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 10px 24px;
  transition: opacity 0.15s;
}
.btn-secondary {
  background: none;
  color: var(--ink);
  border: 1px solid var(--border);
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 10px 24px;
  transition: border-color 0.15s;
}
```

### Gap: FAQ self-host answer has no button

The FAQ "Can I self-host?" answer says "git clone, docker compose up, done." — this is a trigger for a `.btn-secondary` linking to the GitHub repo. A secondary CTA there closes the loop: question → answer → action. Not strictly a button issue, just a missing CTA.

### Gap: Update banner button uses inline style

The `.update-banner` has a nested `.update-banner button` rule in style.css — this is correct. But the current landing doesn't have an update banner at all. When it's added, the button MUST use the class rule, not inline style.

### Gap: Pricing Pro tier has `.btn-primary` for both

Free tier and Pro tier both use `.btn-primary`. The Free tier CTA ("Try it free") could use `.btn-secondary` to create visual hierarchy — the Pro tier is the action you want, the Free tier is the fallback. Or keep both `.btn-primary` — the current design system is ambiguous on this. Recommendation: Free = `.btn-secondary` (matches the secondary nature), Pro = `.btn-primary`.

---

## Missing sections (to add)

### 1. Metrics bar (high priority)
Between stat-strip and "What ships". Uses existing `.metrics-bar` class. Content:
```html
<div class="metrics-bar">
  <span>Claude Sonnet 4.5</span>
  <span class="metrics-sep">·</span>
  <span>5 files per run</span>
  <span class="metrics-sep">·</span>
  <span>avg 44.5s</span>
  <span class="metrics-sep">·</span>
  <span>Markdown output — you own the files</span>
  <span class="metrics-sep">·</span>
  <span class="metrics-plus">Open source</span>
</div>
```

### 2. Aside-list in hero aside (high priority)
Replace the 30 lines of inline-styled div/span pile in `.lede-aside` with:
```html
<ul class="aside-list">
  <li><strong>analysis.md</strong> <span>12.3s</span></li>
  <li><strong>epic.md</strong> <span>18.1s</span></li>
  <li><strong>architecture.md</strong> <span style="color:var(--ink-muted)">generating…</span></li>
  <li style="opacity:0.35"><strong>timeline.md</strong> <span>—</span></li>
  <li style="opacity:0.35"><strong>implementation-guide.md</strong> <span>—</span></li>
</ul>
```

### 3. Context cards "Who it's for" (medium)
Three `.context-card` blocks in 3-column grid, between FAQ and footer. Solo Founder / Small Team / Consulting.

### 4. Two-column pull quote (medium)
Replace existing single pullquote-single OR add a second pullquote section using full `.pullquote-row` grid (two quotes + `.pullquote-divider`). Between comparison table and pricing.

### 5. Update banner (medium)
Full-bleed ink bar above footer. **Prerequisite:** `.update-banner` is NOT in `landing/style.css` — it exists only in `playground.html`'s inline `<style>` block and in `web-ng/src/styles.css`. Must port the CSS to `landing/style.css` first, then instantiate:
```html
<div class="update-banner">
  Spec Doc is in early access — pricing locks in at $29/mo.
  <button onclick="location.href='https://app.specview.io/signup'">Get started</button>
</div>
```

### 6. Rise animation on output cards (low)
Add staggered `animation: rise 0.35s ease both; animation-delay: Xms` to each `.output-card`. 5 cards × 70ms stagger. Makes the pipeline feel like it's filling in.

---

## Spacing and rhythm tightness issues

### 1. Step horizontal padding inconsistency
`.step` uses `padding: 80px 48px`. All other major sections use `padding: 80px 40px` or `80px 40px`. The 8px mismatch breaks the horizontal rhythm. Fix: `.step { padding: 80px 40px; }`.

### 2. Section-page `min-height: calc(100vh - 130px)` on compare + faq
The comparison table and FAQ sections override `.section-page` with inline `style="min-height:auto;padding:40px;"`. These overrides break the class contract and should move into modifier classes or be driven by the standard class. Add `.section-page--compact { min-height: auto; padding: 40px; }` to style.css and use that class instead of inline overrides.

### 3. Hero aside inline styles — 30+ lines
The entire `.lede-aside` file list is inline-styled `div > span` elements. This should be `.aside-list` (semantic markup, zero inline styles). The CSS class already exists.

### 4. Demo strip inner padding
`.demo-masthead` uses `padding: 12px 20px`, `.demo-sidebar` uses `padding: 16px`, `.demo-content` uses `padding: 24px 28px`. The internal demo-strip padding uses 4 different values (12, 20, 16, 24, 28). These should standardize to `16px` horizontal everywhere inside the strip.

---

## Dark mode audit (landing-specific)

Phase 2 fixed dark mode in the app. The landing has its own dark mode that needs the same scrutiny:

1. **`color: var(--border)` text** — `--border` in dark mode is `#2E2E2E`. Text at `#2E2E2E` on `#141414` is ~1.2:1 contrast — invisible. Must fix (see color issues above).
2. **`.step-code` in dark mode** — has a specific override `background: #1E1E1E`. Correct.
3. **`.gen-status-bar--active`** — `background: var(--status-active)` = amber in dark. This is the amber issue — see color issue #2 above.
4. **Comparison table** — `tbody tr border-bottom: 1px solid var(--border)`. In dark mode `--border` = `#2E2E2E` on `#141414` — very low contrast. May be acceptable for table row dividers (structure, not meaning). Verify.

---

## Hard constraints (same as Phase 2)

- All CSS changes go in `landing/style.css` — no new `<style>` blocks in HTML
- No shadows anywhere
- No new font families — Playfair Display, Source Serif 4, Source Sans 3 are the complete set
- `.overline` class definition stays unchanged — only usage sites change
- `--status-running` is green (`#22A66A`). Never amber for a running state.
- `docker compose build landing && docker compose up -d landing` must pass before any PR
- No JS beyond the existing theme toggle script
- Inline styles are a last resort — use CSS classes for anything that repeats more than once

---

## What excellent looks like

Opening `http://localhost:8096/landing-v2.html` should feel like opening the front page of a tech newspaper that happens to be selling a product. The masthead declares editorial authority. The section nav has the thick nameplate rule above it. Scrolling through is reading — each section is a different story about why Spec Doc matters: the hero tells it in two sentences, the stat strip proves it in four numbers, the steps show how it works, the demo strip shows what you get, the comparison table names who this isn't for, the pull quotes give it a human voice, the pricing makes the decision easy.

Every `.overline` label (red, uppercase, 11px) that appears — in the hero, above each step — carries the same editorial voice. The `.step-code` terminal blocks feel like real output, not placeholder text. The FAQ reads like a knowledgeable founder answering honestly.

Dark mode inverts the cream/ink relationship cleanly. No text disappears against its background. The gen-status bar's running dot is green (not amber). The demo strip's markdown content renders in two clean columns.

The page is complete. Every section earns its place. The interface recedes. The product argument advances.

→ [Full playground reference](http://localhost:8096/playground.html)
→ [App Phase 2 reference](data/projects/ux-polish-newspaper-1778238000/)
→ [Design system doc](docs/design-system.md)

---

# App (web-ng) Polish — Phase 3

> **Scope:** `web-ng/src/app/app.component.ts`, `app.component.html`, `styles.css`, `services/projects.service.ts`, `index.html`
> **Relationship to landing:** The landing page (`landing-v2.html`) is the visual contract — if the landing has it and the app doesn't, that's a gap to close. Phase 2 aligned masthead, nameplate rule, overline, dark-mode contrast, and sidebar ordering. Phase 3 finishes what Phase 2 left open and extends from what the landing now demonstrates.
> **Playground:** `http://localhost:8096/playground.html` — all component states, tokens, CSS verbatim.

---

## Phase 2 leftovers — must fix first

Phase 2 ran 6 tasks and left 4 criticals and 6 warnings unresolved. These carry forward into Phase 3 as pre-conditions.

### Criticals (block merge, fix first)

**1. XSS — `bypassSecurityTrustHtml` without DOMPurify**
`app.component.ts:241,263,270` — three computed signals (`parsedContent`, `diffHtmlUnified`, `parsedAiResult`) all call `this.sanitizer.bypassSecurityTrustHtml(marked.parse(...) as string)` on raw API content. If the API returns malicious markdown, the XSS lands directly in the DOM. Fix: wrap every `marked.parse()` call with `DOMPurify.sanitize()` before passing to `bypassSecurityTrustHtml`. DOMPurify must be imported (`npm install dompurify @types/dompurify`).

```ts
// Before (unsafe)
this.sanitizer.bypassSecurityTrustHtml(marked.parse(content) as string)

// After (safe)
import DOMPurify from 'dompurify';
this.sanitizer.bypassSecurityTrustHtml(DOMPurify.sanitize(marked.parse(content) as string))
```

**2. `http.get<any>` defeats TypeScript**
`services/projects.service.ts:85,111` — poll responses typed as `any`. Define concrete interfaces for the poll response shapes and replace `any`. This is both a type safety issue and an Angular convention violation.

**3. Inline `[style.display]` binding**
`app.component.html:80` — `<div class="divider thick" [style.display]="showGrid() ? '' : 'none'">`. Angular convention: never use `[style.*]` for conditional visibility. Replace with `@if (showGrid()) { <div class="divider thick"> }`.

**4. Inline `[style.bottom]` binding**
`app.component.html:287` — `[style.bottom]="specGenLoading() || aiLoading() ? '42px' : null"` on the editor toolbar. Replace with a CSS modifier class: `[class.editor-toolbar--elevated]="specGenLoading() || aiLoading()"` + `.editor-toolbar--elevated { bottom: 42px; }` in styles.css.

---

### Warnings (fix in Phase 3)

**5. Typo: `isAdditivOp` → `isAdditiveOp`**
`app.component.ts:274` — the computed signal is named `isAdditivOp`. It is used in the template at `@if (isAdditivOp())`. Rename everywhere (find-replace): the correct English is `isAdditiveOp`. Low risk, high polish.

**6. `knownCount` should be a signal**
`app.component.ts:119` — `knownCount = 0` is a plain class field, not a signal. It's mutated outside Angular's change detection. Convert to `knownCount = signal(0)` and update all read/write sites.

**7. Missing CSS: `text-ops-billing`, `sidebar-status-retry`, `error-state`**
`styles.css` — three classes used in the template with no CSS definition:
- `.text-ops-billing` — billing gate message (template: `app.component.html:311`)
- `.sidebar-status-retry` — retry button in failure state (template: `app.component.html:204`)
- `.error-state` — top-level polling error (template: `app.component.html:56`)

These render with zero styling. From the playground:

```css
/* sidebar-status-retry — mirrors .modal-cancel micro-button */
.sidebar-status-retry {
  margin-left: auto;
  background: none;
  border: 1px solid rgba(255,255,255,0.4);
  color: inherit;
  font-family: var(--sans);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 2px 8px;
  cursor: pointer;
}

/* error-state — full-width polling error banner */
.error-state {
  background: var(--red);
  color: #fff;
  font-family: var(--sans);
  font-size: 12px;
  padding: 8px 40px;
  display: flex;
  align-items: center;
  gap: 12px;
}

/* text-ops-billing — billing gate message in expanded main */
.text-ops-billing {
  border: 1px solid var(--red);
  padding: 16px 20px;
  margin-bottom: 16px;
}
```

**8. Constructor injection instead of `inject()`**
`services/projects.service.ts:49` — Angular 17+ convention is `inject()` at field declaration, not constructor injection. Refactor `ProjectsService` constructor to use `private http = inject(HttpClient)` etc.

**9. Missing `crossorigin` on fonts.gstatic.com preconnect**
`web-ng/src/index.html` — the preconnect for `fonts.gstatic.com` is missing the `crossorigin` attribute. Required for cross-origin font preloading:
```html
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
```

**10. `effect()` writing to signal without `allowSignalWrites: true`**
`app.component.ts:337` — `effect(() => { this.toolbarFloating.set(...); })` writes to a signal inside an effect without the required option. Either add `{ allowSignalWrites: true }` or (better) convert to `computed()`:
```ts
// Replace effect() + signal with:
toolbarFloating = computed(() => !!(this.activeProject() && this.currentSpec()));
```

---

## Design gaps — app vs landing Phase 3

### 1. Op chips have no icons (Phase 2 incomplete)

Phase 2's Task 4 removed the Lucide CDN and replaced all `<i data-lucide>` with emoji spans (`✦ × ← ⚡`). But the **op chips** — Expand, Compress, Clarify, Simplify, TL;DR, Bullets, Style — were left text-only. The Phase 2 epic specified these icon mappings verbatim:

```
expand     → ↕  (arrow-up-down)
compress   → ⊡  (minimize-2)
clarify    → ?  (help-circle)
simplify   → ◁  (feather)
tldr       → ≡  (align-left)
bullets    → ≔  (list)
brainstorm → ✦  (sparkles — already present)
style      → ◈  (palette)
undo       → ↩  (rotate-ccw — already used)
redo       → ↻  (rotate-cw — already used)
```

Since the Lucide CDN is gone and inline SVGs are the pattern, each op chip needs an inline SVG prepended to its label. They can be tiny (13px, `stroke-width: 1.75`). Alternatively, use the Unicode approximations above as `<span class="btn-icon">` — consistent with how `✦`, `←`, `×`, `☾`, `☀` are already used throughout the template.

The playground at `#pg-comp-toolbar` shows the intended appearance: icon + label, not label-only.

**Recommendation:** Use `<span class="btn-icon">` with Unicode approximations — no SVG complexity, matches existing pattern:
```html
<button class="op-chip" [class.active]="activeOp() === 'expand'" (click)="toggleOp('expand')">
  <span class="btn-icon">↕</span> Expand
</button>
```

→ [Op chips demo](http://localhost:8096/playground.html#pg-comp-toolbar)

### 2. `inline-gen-status` is not `.gen-status-bar`

`app.component.html:326-340` uses a custom `.inline-gen-status` class with `.gen-status-track` and `.gen-status-content` internals. This is the same visual pattern as `.gen-status-bar` used on the landing page — but uses a different wrapper class, so it gets none of the `.gen-status-bar--active` color or the correct font treatment.

Fix: replace `.inline-gen-status` wrapper with `.gen-status-bar.gen-status-bar--active`. The internals (`.gen-status-track`, `.gen-status-content`) are already correct.

```html
<!-- Before -->
<div class="inline-gen-status">
  <div class="gen-status-track"></div>
  ...

<!-- After -->
<div class="gen-status-bar gen-status-bar--active">
  <div class="gen-status-track"></div>
  ...
```

→ [Status bar demo](http://localhost:8096/playground.html#pg-comp-statusbar)

### 3. The `expanded-title` has no subtitle/meta line

The spec reader shows `<h2 class="expanded-title">{{ expandedTitle() }}</h2>` at the top of `.expanded-main`. Below the `overline` file-type label and above the title, there's no date, no project name, no word count — no editorial meta line. The landing's demo strip shows `demo-tagline` below the title. The app reader needs a similar meta line:
```html
<span class="overline">{{ activeFileType() }}</span>
<div class="expanded-meta" style="font-family:var(--sans);font-size:11px;color:var(--ink-muted);margin-bottom:8px;">
  {{ activeProject()?.name }} · {{ currentSpec()?.content?.length | wordCount }} words
</div>
<h2 class="expanded-title">{{ expandedTitle() }}</h2>
```

This is the editorial "deck" line — present in every newspaper article, missing from the spec reader.

### 4. Section nav has no project count in the `all` tab

The section nav shows counts for Active, Specced, etc. but the `all` tab shows no count badge. The `sectionCounts()` computed already calculates `counts['all']`. The template conditionally renders counts for sections that have `sectionCounts()[s.id] !== undefined` — but `all` is in `sectionCounts`. Check whether the badge renders for `all`. If not, it's a template `@if` condition issue.

### 5. File grid `section-group` uses no `.section-heading` pattern

In the "all" view, projects are grouped into sections (`Active`, `Specced`, etc.) with `.section-group-header > span.section-group-title.overline`. The `.overline` is already applied (Phase 2 Task 3). But `.section-group-header` has no bottom border — the landing's `.section-heading` uses `border-bottom: 1px solid var(--border); padding: 12px 40px`. The section-group headers in the app should have the same bottom rule to visually separate them from the cards beneath.

```css
/* Add to styles.css */
.section-group-header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
  margin-bottom: 12px;
}
```

### 6. Teaser hierarchy — ClawBoi pattern missing

ClawBoi dashboard (`clawboi/dashboard/style.css`) established the newspaper card hierarchy that Specview's file grid should inherit:

- **Line-clamp:** featured card (first per section) → 3-line teaser at slightly larger font; normal cards → 2-line clamp. Currently no clamp at all.
- **Negative-margin hover bleed:** on hover, `margin: 0 -8px; padding: 12px 8px` makes cards feel like newspaper columns bleeding into gutters. Current `.file-item:hover` is background-only.
- **`expanded-meta` line:** ClawBoi's `expanded-meta` shows `section · date` in Source Sans 11px uppercase — exactly what the braindump calls for in the spec reader (`project name · word count`). Port this class to `web-ng/src/styles.css`.
- **`.badge-new`** — `var(--red)` badge for projects that just had specs generated. 9px, uppercase, tight padding. Free win on the file grid.

The teaser body should be Source Serif 4 italic at 13px, `color: var(--ink-light)`, with a Source Sans meta line below. Featured cards get one extra line.

### 7. Context cards missing hover border treatment

`app.component.html:89` — `.context-card` has `(click)="openContext(f.key)"` but the playground's `.context-card:hover` treatment (`border-color: var(--ink); box-shadow: 0 2px 8px rgba(0,0,0,0.06)`) — the only shadow exception in the system — creates a "hover = selection imminent" signal. Verify this is in `styles.css`. If missing, add it from playground verbatim.

---

## Angular signal hygiene

These are state management issues that don't manifest visually but violate the Angular 17 signals contract.

### Signal writes inside `effect()` — two instances

1. `app.component.ts:337` — `effect(() => { this.toolbarFloating.set(...) })` — fix: convert to `computed()` (covered above in warning #10)
2. Verify no other `effect()` blocks write to signals. The `pulsingSections` effect at line 342 uses `this.pulsingSections.set(...)` inside an effect — this also needs `{ allowSignalWrites: true }` or a different pattern.

### `knownCount` mutation pattern

`knownCount = 0` is read in polling logic to detect new projects. When `projects.length > knownCount`, a badge pulses. Converting to `knownCount = signal(0)` means the comparison logic should use `this.knownCount()` for reads and `this.knownCount.set(...)` for writes — no `if` checks on a plain field.

---

## What the app should feel like after Phase 3

Opening Specview should feel like opening a newspaper with a task manager attached. The masthead is authoritative — 64px Playfair, editorial tagline in Source Serif italic, thick nameplate rule above the section nav. Navigating between sections (Active / Specced / Braindumps) feels like turning to a section of a paper — red overline headers, clean file-item cards, counts that pulse when something changes.

Opening a spec reads like opening an article. The overline declares the document type (`ARCHITECTURE`, `EPIC`). The title is Playfair at 36px. The body is two-column Source Serif — real reading text, not a developer log. Code spans in `code-bg`, pre blocks spanning both columns.

The AI op chips feel purposeful. `↕ Expand` says what it does before the word registers. The running dot is green — work is happening and going well. Success flashes deep green. Failure is red with a retry button styled to be usable.

The XSS vulnerability doesn't exist. Type safety is enforced. Effects don't secretly write to signals. The codebase is correct, not just functional.

→ [Playground reference](http://localhost:8096/playground.html)
→ [Phase 2 completed work](data/projects/ux-polish-newspaper-1778238000/exec-guide-summary.md)
→ [Design system](docs/design-system.md)

---

## Phase 3 Pre-Analysis

*Source: AI analysis generated 2026-05-09 from the braindump above.*

### 1. Key Themes

The design system is ahead of the HTML. CSS classes like `.aside-list`, `.metrics-bar`, `.update-banner`, `.pullquote-row`, and `.context-card` are fully defined and playground-tested — the gap is purely instantiation. Phase 3 is less "design work" and more "promotion of existing system into live markup."

Inline styles are the entropy metric. Every inline style, arbitrary opacity, and `color: var(--border)`-as-text is a measurement of how far a component has drifted from the design system. The spec is essentially an audit of that drift — the fix is almost always "use the class that already exists."

Phase 2 carried forward 10 unresolved issues. Six tasks marked complete, ten issues (4 criticals, 6 warnings) promoted into Phase 3's pre-conditions. The completion criteria were too loose. This is a process problem masquerading as a backlog problem.

The newspaper metaphor is load-bearing, not decorative. The editorial framing — masthead, overlines, section nav as section fronts, spec reader as article view — isn't aesthetic preference. It is the product argument: Specview produces documents worth reading, not developer logs. Every typography gap weakens the argument.

Security and correctness precede polish. The XSS vulnerability (`bypassSecurityTrustHtml` without DOMPurify) and the `http.get<any>` type erasure are correctness failures inside a spec about visual polish. They don't belong in the same phase — they belong before it.

### 2. Hidden Connections

The XSS bypass and the inline style problem are the same failure at different layers. `bypassSecurityTrustHtml` says "trust this content, skip the system." Inline `opacity: 0.85` says "trust this value, skip the token system." Both are local shortcuts that accumulate into systemic fragility. The fix in both cases is identical in spirit: route through the abstraction that exists for this purpose.

`color: var(--border)` as text color mirrors `bypassSecurityTrustHtml` semantically. The border token is not a text color — using it as one bypasses the semantic contract of the token system the same way bypassing Angular's sanitizer bypasses the security contract. Both are tools used for a purpose they weren't designed for.

`.inline-gen-status` (app) vs `.gen-status-bar` (landing) is the same problem as inline styles. Local naming to avoid touching the shared class. The divergence compounds with every phase. The spec identifies this pattern repeatedly without naming it: component-level solutions that prevent system-level consistency.

The FAQ self-host answer is a conversion funnel hidden inside a support document. The people reading "Can I self-host?" are developers evaluating trust, not users asking for help. A `.btn-secondary` GitHub link at the end of that answer is a repo-star trigger. The FAQ isn't support copy — it's a second sales page for a different buyer persona.

The playground-as-Figma decision creates an interesting constraint: the design system is live, inspectable, and correct by definition. Every gap in the HTML is measurable against a running reference. This inverts the normal design → dev handoff: the CSS contract is the source of truth, not a Figma file that drifts.

The "newspaper" metaphor and the SaaS pricing page are in tension. Newspapers don't upsell. The pricing grid and update banner are product-page conventions that the editorial framing has to absorb without breaking. The pull quote row and the comparison table are doing that bridging work — they're the "editorial" wrapper around what is functionally a conversion sequence.

### 3. Open Questions

**Should the XSS fix and type safety issues be extracted into a zero-scope "Phase 2.5" before Phase 3 begins?**
- Option A: Fix criticals first, lock them in a separate commit, then start Phase 3 work
- Option B: Fix criticals as the first tasks of Phase 3, blocking all other app work until done
- Option C: Treat criticals as parallel-track work, unblocking landing while app criticals are fixed
- **Recommended: Option A.** The XSS fix is a correctness issue, not a polish issue — committing it separately makes the git history honest and ensures it isn't accidentally reverted if Phase 3 is rolled back.

**What is Phase 3's definition of done — and how do you prevent a Phase 4 inheriting another 10-issue backlog?**
- Option A: Add explicit acceptance criteria per task (zero inline styles, dark mode verified, CSS class used not invented)
- Option B: Run a post-phase audit checklist against playground parity before closing
- Option C: Keep the current format; accept that phases carry forward issues
- **Recommended: Option A.** The carryover pattern isn't a backlog problem — it's a missing definition-of-done. A 5-point checklist per task (inline styles, token usage, dark mode, class parity, no new CSS invented) costs 10 minutes and stops the accumulation.

**Where does the "Who it's for" context card section belong — landing only, or app too?**
- Option A: Landing only — it's acquisition copy, irrelevant once you're inside the product
- Option B: App onboarding screen — first-run users need the same framing
- Option C: Both, but with different content (landing: persona pitch; app: feature discovery)
- **Recommended: Option A.** Context cards are pre-purchase framing. Inside the app, the equivalent is empty-state copy — which should be written separately and not try to reuse the landing's acquisition voice.

**Should `.section-page--compact` be added to `style.css` now, or is it premature abstraction?**
- Option A: Add it now — the inline override already exists twice, the third use is guaranteed
- Option B: Wait until a third instance appears organically
- Option C: Remove the two existing overrides and use `min-height: auto` as an explicit layout intent
- **Recommended: Option A.** Two instances of identical inline overrides is already a pattern. The class name documents intent (compact = no forced viewport height), the inline style does not.

**Is the `thinking-pulse` animation functionally distinct from `dot-pulse`, or is this a visual-only differentiation?**
- Option A: Functionally distinct — `thinking-pulse` signals "model is reasoning" vs `dot-pulse` signals "task is running"; surface both
- Option B: Visual-only — one animation for all async states, consistent and simpler
- Option C: Use color to differentiate states (accent vs green vs amber) and keep one animation
- **Recommended: Option C.** The design system already uses color tokens for state semantics. Adding a second animation creates a second semantic axis that competes with color. Let color carry state; let animation signal that something is happening.

**Does the `expanded-meta` line (project name · word count) require a `wordCount` pipe that doesn't exist yet?**
- Option A: Build the `wordCount` pipe as part of this task — it's a 10-line Angular pipe
- Option B: Use character count divided by 5 as a cheap approximation without a custom pipe
- Option C: Skip word count, show only project name and file type
- **Recommended: Option A.** A proper `wordCount` pipe is reusable across any spec display surface and takes 10 minutes. Approximations become maintenance debt. The editorial meta line is incomplete without an accurate count.

### 4. Ideas to Explore

**Write a design-system compliance script.** A Node script that scans `landing-v2.html` and `app.component.html` for: (1) `style=` attributes with more than one property, (2) `color: var(--border)` used as text, (3) `opacity:` as inline text treatment, (4) CSS classes used in HTML but not defined in `style.css`. Run it as a pre-commit hook.

**Create a "dead CSS" audit** as a companion to the component map. Every class in `style.css` should map to at least one live HTML usage. Unused classes are either aspirational (promote them) or vestigial (delete them).

**Use the dark mode audit as a visual regression baseline.** Screenshot `landing-v2.html` in both light and dark mode before Phase 3 starts. After each task, diff. Puppeteer + pixelmatch is 50 lines.

**The FAQ is an underutilized conversion surface** — treat it as a second landing page. Each FAQ answer should end with a micro-CTA: self-host → GitHub button, pricing → Pro tier link, what it generates → demo strip anchor. Pattern: question → honest answer → action.

**The Phase 2 → Phase 3 carryover pattern suggests epics need a "must-not-carry" rule.** Any issue tagged Critical must ship in the same phase that found it, or it gates the next phase from opening.

**The `.metrics-bar` pipe-separated strip is the spec's best conversion beat.** "Claude Sonnet 4.5 · 5 files · avg 44.5s · Markdown output — you own the files · Open source" is the entire value prop in one sentence. Animate on scroll with staggered `rise` — each item fades in as the user reaches it.

**The "newspaper" metaphor could become explicit product positioning against Lovable/Bolt/Kiro.** "We make specs, not scaffolding" is the line. Lovable/Bolt generate running apps — ephemeral, hard to version, hard to own. Specview generates documents — persistent, versionable, yours.

**Consider `IntersectionObserver` for the `rise` animation on output cards** rather than page load. Five cards staggering at `animation-delay: 0–280ms` on load animate before most users scroll to them. Observer-triggered animation makes the pipeline "fill in" as the user reads down.
