# 🏗️ Solution Architecture: Landing & App Polish — Phase 3

## Architecture Overview

Phase 3 operates on two surfaces — a static HTML/CSS landing page and an Angular SPA — but shares a single governing contract: `style.css` and its live playground at `localhost:8096`. The design system is complete. The gap is instantiation: dozens of CSS classes, semantic color tokens, and layout primitives exist in the stylesheet and are verified in the playground, but the HTML on both surfaces has not yet consumed them. The primary architectural move is promotion — replacing locally-invented inline styles, arbitrary opacity values, and semantically-misused tokens with the classes that were built for exactly those purposes.

The two surfaces are not independent. The landing is the visual contract; the app must converge to it. When the landing uses `.gen-status-bar` and the app uses `.inline-gen-status`, the same component exists in two incompatible implementations. Every such divergence adds a surface-specific override that must be maintained separately in perpetuity. Phase 3 closes those divergences by making both surfaces draw from the same class definitions, the same token values, and the same component semantics.

A security boundary runs through the app work. Three computed signals bypass Angular's sanitizer with no upstream purification. These are correctness failures, not polish gaps, and they gate all app visual work: if the XSS surface is open when visual changes ship, any later rollback of visual work risks accidentally reopening a patched vulnerability. The security fix and type-safety corrections therefore form a separate, mergeable unit that unblocks app visual work rather than running alongside it.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P1 — Adapter Boundary** | `style.css` is the style adapter. All visual state lives in token variables and class rules; no component invents its own values inline. Inline styles are a bypass of the adapter — treated identically to importing a provider directly. |
| **P2 — Thin HTTP Layer** | `projects.service.ts` poll responses must carry concrete TypeScript interfaces, not `any`. The HTTP boundary's contract is as important as its thinness. |
| **P3 — Async 202 + Polling** | No change in Phase 3; existing pattern governs spec generation. The XSS fix applies to content that arrives through this pipeline — sanitization happens at the render boundary, not the fetch boundary. |
| **P4 — No Speculative Abstractions** | `.section-page--compact` is added because the inline override already appears twice, making the pattern concrete, not speculative. `thinking-pulse` is deferred because color tokens already carry state semantics — a second animation axis solves a problem that doesn't exist. |
| **P7 — File Size & Structure** | All CSS changes land in `landing/style.css` and `web-ng/src/styles.css` respectively. No new `<style>` blocks are introduced in HTML. The hard target governs: if a component file is approaching 200 lines, the signal hygiene refactor (converting plain fields to signals, extracting computed from effect) is the mechanism for keeping it in range. |

---

## Component Design

### Security Gate

**Purpose**: Eliminate the XSS surface in `app.component.ts` and restore TypeScript's type contract in `projects.service.ts` before any visual change reaches the app.

The three `bypassSecurityTrustHtml` call sites (`parsedContent`, `diffHtmlUnified`, `parsedAiResult`) pass raw API content through `marked.parse()` directly into Angular's DOM. DOMPurify is the purification boundary — it must wrap every `marked.parse()` call before the result reaches `bypassSecurityTrustHtml`. The architectural principle here is the same as P1: the sanitizer is the security adapter; calling `bypassSecurityTrustHtml` without routing through DOMPurify first is semantically identical to calling a provider directly without going through the adapter.

The `http.get<any>` pattern at poll endpoints defeats TypeScript's ability to reason about data shape. Concrete interfaces for poll response shapes are not speculative abstraction — they are the type contract the HTTP boundary is supposed to enforce. Defining them closes the gap between what the API guarantees and what the Angular component believes it receives.

This unit ships as a standalone, mergeable commit. Its success criteria are binary and code-reviewable: DOMPurify present at all three call sites, zero `any` at the two poll endpoints.

### Landing Markup Promotion

**Purpose**: Replace every inline style in `landing-v2.html` with the design system class or token it was approximating, with no net-new CSS invented.

The inline style problem and the `bypassSecurityTrustHtml` problem share an architectural cause: both are local shortcuts that bypass an abstraction built to handle exactly that case. `color: var(--border)` as a text color uses the border token as an ink token — semantically wrong and dark-mode-unsafe, because `--border` in dark mode resolves to `#2E2E2E`, which produces near-invisible text on `#141414`. The correct token is `--ink-muted`, which was designed for secondary and faded text states and has dark-mode-correct values baked in.

Arbitrary opacity values (`0.5`, `0.85`, `0.6`) on text spans are the inline style version of the same mistake: inventing a value rather than consuming the token designed for that semantic. The design system encodes opacity into the color tokens themselves — `--ink-muted`, `--ink-light` — so opacity on text elements is not the pattern.

The `.section-page--compact` modifier is introduced here rather than deferred, because two identical inline overrides (`min-height: auto; padding: 40px`) already exist. The class name carries intent that the inline override does not: "compact" signals a deliberate layout decision, not a local hack. Adding it now costs nothing and eliminates a third inevitable inline occurrence.

The button hierarchy correction — Free tier to `.btn-secondary`, Pro tier retaining `.btn-primary` — is a conversion architecture decision. The landing's purpose is to route traffic to Pro. When both CTAs are visually equal, the Pro tier loses its primary signal. Making Free secondary and Pro primary uses the existing button system to encode conversion intent without touching CSS.

### Landing Section Instantiation

**Purpose**: Bring five defined-but-absent sections into `landing-v2.html`, completing the editorial conversion sequence.

The metrics bar is the highest-leverage addition: "Claude Sonnet 4.5 · 5 files · avg 44.5s · Markdown output — you own the files · Open source" is the entire value proposition in one line. Its location between the stat strip and "What ships" turns the stat strip from a data display into an opening argument that the metrics bar closes. The `.metrics-bar` class is already defined and playground-verified — this is instantiation, not design.

The aside-list replacement eliminates 30-plus lines of inline-styled `div`/`span` elements in the hero aside and replaces them with a semantic `<ul class="aside-list">`. The architectural value is twofold: dark mode correctness is automatic (the class carries token-aware styles) and the hero file-timing display becomes a first-class system component rather than a bespoke inline construction.

The two-column pull quote row and the update banner are editorial structure and conversion urgency respectively. The pull quote row bridges the comparison table (rational argument) and pricing (decision point) with a human register. The update banner above the footer creates the "early adopter window" framing that makes the $29/mo Pro price feel time-bounded without being dishonest about it. Both classes are playground-verified; the decision is where in the editorial sequence they land, not how they look.

Context cards ("Who it's for") go between FAQ and footer: landing only, not app. The architectural reason is audience. People reading context cards are pre-purchase — they need to see themselves in the product before they decide. People inside the app have already decided. The app's equivalent of that framing is empty-state copy, which requires a different voice and a different scope.

### App Signal Hygiene

**Purpose**: Bring `app.component.ts` into compliance with Angular 17's signals contract.

Three signal violations are in scope. First, `effect()` writing to signals without `allowSignalWrites: true` — the correct fix is conversion to `computed()`, which is the right primitive for derived state: `toolbarFloating = computed(() => !!(this.activeProject() && this.currentSpec()))`. Effects are for side effects; computed values are for derived state. Using an effect to derive a signal value is using the wrong primitive, which is why Angular requires the opt-in flag. Second, `knownCount` as a plain class field mutated outside change detection — converting to a signal makes the mutation visible to Angular's reactivity system and eliminates the possibility of a stale read. Third, the `pulsingSections` effect, which also writes to a signal and needs the same treatment.

The constructor injection refactor (`inject()` at field declaration) is an Angular 17 convention issue. It has no runtime impact but matters for consistency — the entire codebase should read as Angular 17 idiomatic code, not a mix of patterns from different major versions.

The `isAdditivOp` typo is renamed to `isAdditiveOp` globally. Typos in computed signal names become permanent when the signal name is used in templates — find-replace with verification against the template is the only safe fix.

### App Design Alignment

**Purpose**: Close the visual gap between app and landing on op chips, status bar, expanded meta, and section group headers.

Op chips adopt `<span class="btn-icon">` with Unicode approximations, consistent with how `✦`, `←`, `×`, `☾`, and `☀` are already used in the template. The architectural decision is Unicode over inline SVG: the existing pattern is established, the icon set is small and stable, and Unicode eliminates the SVG-loading complexity and accessibility overhead for what are essentially decorative glyphs in a product-internal UI.

The `.inline-gen-status` → `.gen-status-bar.gen-status-bar--active` unification is the most structurally important app change. Two implementations of the same component means two diverging maintenance surfaces. The correct resolution is always convergence: the landing's class is the source of truth (it's the visual contract), and the app adopts it. The internals — `.gen-status-track`, `.gen-status-content` — are already correct; only the wrapper class changes.

The expanded-meta editorial line (project name · word count) requires a `wordCount` pipe. A character-count approximation is rejected because approximations become maintenance debt the moment the displayed value is used for anything beyond decoration — and a word count in an editorial product is a credibility signal. A proper Angular pipe is the right primitive: reusable across any spec display surface, accurate, and ten lines of implementation.

The three missing CSS class definitions — `.text-ops-billing`, `.sidebar-status-retry`, `.error-state` — are added to `styles.css` from the playground verbatim. These render with zero styling currently because the classes exist in the template but not in the stylesheet. The fix is mechanical, not architectural, but it is a prerequisite for the visual alignment work that follows.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Landing HTML | Static HTML5 in `landing/landing-v2.html` | No framework needed for a marketing page; nginx serves it directly; the design system lives entirely in CSS |
| Landing CSS | `landing/style.css` (single file, shared with playground) | The playground is the live reference — both surfaces read from the same stylesheet, making divergence immediately visible |
| App frontend | Angular 17 (standalone components, signals) | Established; Phase 3 does not change the framework; it brings the implementation into compliance with Angular 17 idioms |
| App security | DOMPurify (npm) + `bypassSecurityTrustHtml` | DOMPurify is the standard HTML sanitization library for browser environments; it runs synchronously on the parse output before Angular sees it |
| App type safety | TypeScript interfaces (no new libraries) | Concrete poll response interfaces replace `any` — this requires no new dependency, only correct use of the type system already present |
| Container | nginx:alpine for landing, existing Docker Compose config | Unchanged; `docker compose build landing && docker compose up -d landing` is the build gate |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Security fix ships as a separate mergeable unit before app visual work** | Git history becomes honest: the correctness fix is clearly isolated and cannot be accidentally reverted if Phase 3 visual changes are rolled back. The XSS vulnerability is a pre-condition for app work, not a component of it. | Adds one merge cycle before app visual tasks begin. Acceptable given that the fix is small and the isolation has permanent value. |
| **`thinking-pulse` animation deferred** | The design system already encodes state semantics in color tokens — `--status-running` (green), `--status-active` (amber), `--red`. Adding a second animation creates a second semantic axis that competes with color rather than extending it. Let color carry state meaning; let animation signal that something is happening. | The distinction between "thinking" and "running" states loses its visual expression. Acceptable because the color distinction remains. |
| **Context cards land in landing only** | Pre-purchase persona framing belongs before the decision point, not inside the product. The app's equivalent is empty-state copy — different voice, different scope, different phase. | Users who need orientation inside the app don't get a structured "who this is for" framing. Mitigated by the fact that signed-in users have already self-selected. |
| **`.section-page--compact` added now** | Two identical inline overrides constitute a concrete pattern, not a speculative one. The class name carries intent the inline attribute cannot; it documents that compact sections are a deliberate layout choice. | One more class in the stylesheet. Negligible cost; clear value. |
| **Unicode icon approximations for op chips over inline SVG** | The existing template already uses Unicode for all other icon-like elements (`✦`, `←`, `×`, `☾`, `☀`). Consistency with the established pattern is more valuable than precision icon rendering for chips that are used by a single operator. | Unicode glyphs are font-dependent and may not render identically across platforms. Acceptable for a product-internal UI with a controlled type stack. |
| **`wordCount` pipe built properly** | Approximations (`charCount / 5`) become maintenance debt and undermine credibility in a product whose value claim is editorial quality. A 10-line Angular pipe is the right primitive: accurate, reusable, and idiomatic. | A small amount of implementation work. No meaningful trade-off. |
| **`.inline-gen-status` replaced by `.gen-status-bar`** | The landing is the visual contract. The app must converge to it, not invent a parallel implementation. Two implementations of the same component create two diverging maintenance surfaces — the only correct resolution is elimination of one. | Template change required in `app.component.html`. The internals are already correct; only the wrapper class changes. |
| **`rise` animation on output cards scoped to landing only** | The landing output cards are static — they animate once on page load and carry no interactive state. App output cards are dynamically generated and interactive; staggered load animation adds complexity without the editorial payoff present on the landing. | Landing and app output cards behave differently on load. Acceptable given that the app's editorial register is already established through typography, not motion. |
| **Per-task acceptance criteria over post-phase audit** | The Phase 2 → Phase 3 carryover pattern is a missing definition-of-done, not a backlog problem. A five-point checklist per task (inline styles eliminated, token usage correct, dark mode verified, class parity with playground, no new CSS invented outside `style.css`) costs ten minutes per task and stops the accumulation. | Adds overhead per task. The overhead is lower than the cost of inheriting a Phase 4 with ten unresolved items. |

---

## Related Documents

- [Analysis](./analysis.md) — Problems driving this design
- [Epic](./epic.md) — Scope, tasks, and success criteria
- [Timeline](./timeline.md) — Status tracking