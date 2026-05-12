# Implementation Guide: Landing & App Polish — Phase 3

## Overview
Phase 3 closes the gap between a fully-specified design system and the HTML/Angular code that has not yet consumed it. The work sequences as two parallel streams that converge at the app: Task 1 (security gate) and Task 2 (landing markup promotion) run in parallel, Task 3 (landing section completion) unblocks after Task 2, Task 4 (app correctness and signal hygiene) unblocks after Task 1, and Task 5 (app design alignment) follows Task 4. The security gate is a hard prerequisite — it ships as a standalone mergeable commit before any app visual change lands, ensuring the XSS fix cannot be entangled with or accidentally reverted alongside style changes.

## Shared Pre-flight
- Confirm `localhost:8096` playground is running and `landing/style.css` is being served from it — this is the live reference for all class and token names.
- Verify `docker compose build landing && docker compose up -d landing` passes on the current branch before touching any file.
- Verify `ng build --configuration production` passes on the current branch before touching any file.
- Install DOMPurify and its TypeScript types in `web-ng/`: `npm install dompurify @types/dompurify`.
- Confirm `landing/style.css` contains `.metrics-bar`, `.aside-list`, `.pullquote-row`, `.update-banner`, and `.context-cards` by grepping the file before beginning Task 3.
- Confirm `.gen-status-bar` and `.gen-status-bar--active` are defined in `landing/style.css` before beginning Task 5.
- Confirm the playground renders `.section-page--compact` with `min-height: auto` and `padding: 40px` before removing the two inline overrides in Task 2.
- Keep each task's changes in an isolated commit so that any single task can be reverted without touching adjacent tasks.

---

## Task 1: Security Gate  [Effort: 0.5 days]

### What
Wraps every `marked.parse()` output with DOMPurify sanitization before it reaches Angular's `bypassSecurityTrustHtml`, eliminating the XSS surface on three computed signal call sites. Replaces `http.get<any>` at the two poll endpoints in `projects.service.ts` with concrete TypeScript interfaces, restoring the type contract at the HTTP boundary.

### Files
- **Modify**: `web-ng/src/app/app.component.ts` — import DOMPurify and wrap `parsedContent`, `diffHtmlUnified`, and `parsedAiResult` computed signals so each calls `DOMPurify.sanitize()` on the `marked.parse()` result before passing it to `bypassSecurityTrustHtml`
- **Modify**: `web-ng/src/app/projects.service.ts` — define `PollStatusResponse` and `PollResultResponse` interfaces (or equivalents matching the actual API shape) and replace every `http.get<any>` at poll endpoints with those typed generics

### Steps
1. In `web-ng/src/app/app.component.ts`, add `import DOMPurify from 'dompurify'` at the top of the import block.
2. Locate the `parsedContent` computed signal and insert a `DOMPurify.sanitize()` call around the `marked.parse()` result, keeping the result as the argument to `this.sanitizer.bypassSecurityTrustHtml()`.
3. Repeat the same sanitize wrapping for the `diffHtmlUnified` computed signal and the `parsedAiResult` computed signal — all three must go through `DOMPurify.sanitize()` before reaching `bypassSecurityTrustHtml`.
4. In `web-ng/src/app/projects.service.ts`, add a `PollStatusResponse` interface that reflects the fields the status-poll endpoint actually returns, and a `PollResultResponse` interface for the result-poll endpoint.
5. Replace each `http.get<any>(` at the poll endpoint call sites with the matching typed generic (`http.get<PollStatusResponse>(` and `http.get<PollResultResponse>(`).
6. Run `ng build --configuration production` and confirm zero type errors before committing.

### Verify
- Code review shows `bypassSecurityTrustHtml` is never called without a preceding `DOMPurify.sanitize()` in `app.component.ts`.
- `grep -n 'http.get<any>' web-ng/src/app/projects.service.ts` returns no matches.
- `ng build --configuration production` exits 0.
- `docker compose build landing && docker compose up -d landing` exits 0.

---

## Task 2: Landing Markup Promotion  [Effort: 1 day]

### What
Replaces every inline style in `landing/landing-v2.html` with the design system class or semantic token it was approximating, adds the `.section-page--compact` modifier to `landing/style.css`, corrects the `color: var(--border)` misuse to `--ink-muted`, removes arbitrary opacity values from text spans, and demotes the Free tier CTA to `.btn-secondary` so the Pro tier reads as the unambiguous primary conversion action.

### Files
- **Modify**: `landing/landing-v2.html` — remove all `style=` attributes where a design system class exists; change Free tier CTA button from `.btn-primary` to `.btn-secondary`; replace `color: var(--border)` inline rules with the `--ink-muted` token class; remove `opacity` inline values from text spans
- **Modify**: `landing/style.css` — add `.section-page--compact` rule with `min-height: auto` and `padding: 40px`

### Steps
1. Open `landing/style.css` and add a `.section-page--compact` rule after the existing `.section-page` definition, setting `min-height: auto` and `padding: 40px` — this must exist before any inline overrides are removed from the HTML.
2. In `landing/landing-v2.html`, search for every `style="` attribute and evaluate each one against the playground at `localhost:8096`; replace each with its equivalent design system class, removing the `style=` attribute entirely.
3. Locate the two existing `style="min-height: auto; padding: 40px"` inline overrides and replace them with `class="section-page section-page--compact"` (or append `section-page--compact` to the existing class list).
4. Find all instances of `color: var(--border)` used as a text color and replace them with the `--ink-muted` token — either by applying a utility class that uses `--ink-muted` or by correcting the inline to the right token if no class yet covers that case.
5. Remove all `opacity` inline style values from text `<span>` elements — the design system encodes opacity into `--ink-muted` and `--ink-light`, so opacity on text is not the correct pattern.
6. Locate the Free tier pricing CTA button and change its class from `btn-primary` to `btn-secondary`; confirm the Pro tier CTA retains `btn-primary`.
7. Load the landing page in a browser and verify no text has become invisible and the button hierarchy reads Pro as visually dominant.

### Verify
- `grep -n 'style="' landing/landing-v2.html` returns zero matches (or only matches for cases where no design system class covers the property, which must be documented).
- `grep -n 'color: var(--border)' landing/landing-v2.html` returns zero matches.
- The Free tier CTA renders visually secondary to the Pro tier CTA in both light and dark mode.
- `docker compose build landing && docker compose up -d landing` exits 0.

---

## Task 3: Landing Section Completion  [Effort: 1 day]

### What
Instantiates five CSS sections that are fully defined in `landing/style.css` but absent from `landing-v2.html`: the metrics bar, the aside-list file list, the second pull quote row, the update banner, and the context cards. Each addition is a placement decision — the classes are playground-verified and require no new CSS.

### Files
- **Modify**: `landing/landing-v2.html` — add `.metrics-bar` between the stat strip and the "What ships" section; replace the hero aside's inline-styled `div`/`span` cluster with `<ul class="aside-list">`; add a `.pullquote-row` block after the comparison table (additive, not replacing `.pullquote-single`); add `.update-banner` above the footer; add `.context-cards` block between the FAQ section and the footer

### Steps
1. Locate the stat strip section in `landing-v2.html` and insert a `<div class="metrics-bar">` element immediately after it, populating it with the single-line copy: "Claude Sonnet 4.5 · 5 files · avg 44.5s · Markdown output — you own the files · Open source".
2. Find the hero aside that contains the file-timing display built from inline-styled `div` and `span` elements; replace the entire cluster with a `<ul class="aside-list">` where each file-timing entry becomes an `<li>`, preserving the existing text content.
3. Locate the comparison table section and insert a `<div class="pullquote-row">` block immediately after the closing tag of the comparison table — use two quote entries consistent with the product voice; do not remove or alter the existing `.pullquote-single` block.
4. Locate the `<footer>` element and insert a `<div class="update-banner">` immediately before it, with copy framing the $29/mo Pro price as an early-adopter lock-in window.
5. Locate the FAQ section and insert a `<div class="context-cards">` block immediately after it and before the footer, with persona cards for the primary buyer (solo founder or small-team lead who has shipped code before a spec existed).
6. Load the landing page in a browser and walk the full editorial sequence from hero to footer, confirming each new section renders correctly in both light and dark mode.

### Verify
- `grep -n 'metrics-bar\|aside-list\|pullquote-row\|update-banner\|context-cards' landing/landing-v2.html` returns at least one match per class.
- The hero aside no longer contains any inline `style=` attributes.
- The comparison table is followed by a `.pullquote-row` block and the original `.pullquote-single` block remains in place.
- `docker compose build landing && docker compose up -d landing` exits 0.

---

## Task 4: App Correctness & Signal Hygiene  [Effort: 1 day]

### What
Brings `app.component.ts` into full Angular 17 signals compliance by converting signal-writing effects to computed values, converting the `knownCount` plain field to a signal, refactoring constructor injection to `inject()` at field declaration, and renaming the `isAdditivOp` typo globally. Adds the three missing CSS class definitions that exist in the template but not in `styles.css`.

### Files
- **Modify**: `web-ng/src/app/app.component.ts` — convert `toolbarFloating` effect to a `computed()` signal; convert `pulsingSections` effect to `computed()`; convert `knownCount` plain field to a signal; refactor constructor-injected dependencies to `inject()` at field declaration; rename `isAdditivOp` to `isAdditiveOp` everywhere in this file
- **Modify**: `web-ng/src/app/app.component.html` — rename every template reference to `isAdditivOp` to `isAdditiveOp`
- **Modify**: `web-ng/src/styles.css` — add `.text-ops-billing`, `.sidebar-status-retry`, and `.error-state` class definitions copied verbatim from the playground

### Steps
1. In `app.component.ts`, locate the `effect()` that derives `toolbarFloating` from `this.activeProject()` and `this.currentSpec()` and replace it with a `computed()` field declaration: `toolbarFloating = computed(() => !!(this.activeProject() && this.currentSpec()))`, then remove the old effect.
2. Locate the `pulsingSections` effect that writes to a signal and convert it to a `computed()` field that derives the same value reactively, removing the effect and the `allowSignalWrites` opt-in.
3. Locate the `knownCount` plain class field and convert it to a signal using `signal()`, then update every mutation site (assignments like `this.knownCount = ...`) to use `.set()` or `.update()` instead.
4. Refactor each constructor-injected dependency to use `inject()` at the field declaration site, removing the parameters from the constructor signature; if the constructor becomes empty after refactoring, remove it entirely.
5. Perform a global find-replace of `isAdditivOp` → `isAdditiveOp` across `app.component.ts` first, then verify `app.component.html` for any remaining `isAdditivOp` references and rename those too.
6. Open `web-ng/src/styles.css` and add the `.text-ops-billing`, `.sidebar-status-retry`, and `.error-state` rules using the exact property values shown for each in the `localhost:8096` playground.
7. Run `ng build --configuration production` and confirm zero errors or warnings related to signal writes, unresolved class names, or the renamed identifier.

### Verify
- `grep -n 'allowSignalWrites' web-ng/src/app/app.component.ts` returns zero matches.
- `grep -rn 'isAdditivOp' web-ng/src/app/` returns zero matches.
- `grep -n '\.text-ops-billing\|\.sidebar-status-retry\|\.error-state' web-ng/src/styles.css` returns three matches.
- `ng build --configuration production` exits 0.

---

## Task 5: App Design Alignment  [Effort: 1 day]

### What
Closes the visual gap between the app and the landing on four surfaces: op chips get Unicode icons via `<span class="btn-icon">`, the `.inline-gen-status` wrapper is replaced with `.gen-status-bar.gen-status-bar--active` to unify with the landing's implementation, the expanded-meta editorial line (project name · word count) is added using a new `wordCount` pipe, and the section-group-header border rule is added to `styles.css`.

### Files
- **Create**: `web-ng/src/app/word-count.pipe.ts` — Angular pipe that accepts a string and returns the integer word count
- **Modify**: `web-ng/src/app/app.component.html` — add `<span class="btn-icon">` with a Unicode glyph to each op chip element; replace the `.inline-gen-status` wrapper class with `gen-status-bar gen-status-bar--active`; add the expanded-meta line using the `wordCount` pipe
- **Modify**: `web-ng/src/app/app.component.ts` — import and declare `WordCountPipe` in the component's `imports` array
- **Modify**: `web-ng/src/styles.css` — add the `.section-group-header` border rule matching the playground definition

### Steps
1. Create `web-ng/src/app/word-count.pipe.ts` as a standalone Angular pipe named `wordCount` that splits its string argument on whitespace and returns the resulting array length as a number, handling null and empty string inputs by returning zero.
2. In `app.component.ts`, add `WordCountPipe` to the component's `imports` array so the pipe is available in the template.
3. In `app.component.html`, locate each op chip element and prepend a `<span class="btn-icon">` containing the appropriate Unicode glyph for that operation type, consistent with the `✦`, `←`, `×`, `☾`, and `☀` pattern already used elsewhere in the template.
4. In `app.component.html`, find the element using the `.inline-gen-status` class and change its class attribute to `gen-status-bar gen-status-bar--active`, preserving the inner `.gen-status-track` and `.gen-status-content` structure unchanged.
5. In `app.component.html`, locate the metadata display area for the active spec and add an expanded-meta line that renders the project name, a separator character, and the spec content piped through `wordCount` followed by the word "words".
6. In `web-ng/src/styles.css`, add the `.section-group-header` rule with the border property values shown in the `localhost:8096` playground.
7. Run `ng build --configuration production`, then load the app in a browser and confirm the status bar renders with a green running dot in both light and dark mode, op chips show icons, and the expanded-meta line displays a word count.

### Verify
- `grep -n 'inline-gen-status' web-ng/src/app/app.component.html` returns zero matches.
- `grep -n 'btn-icon' web-ng/src/app/app.component.html` returns at least one match per op chip type.
- `grep -n '\.section-group-header' web-ng/src/styles.css` returns at least one match.
- `ng build --configuration production` exits 0 and the browser shows the `--status-running` dot in green under an active generation in both light and dark mode.