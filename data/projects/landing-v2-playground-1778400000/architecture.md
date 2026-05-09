# 🏗️ Solution Architecture: landing-v2-playground

## Architecture Overview

The mental model is **"playground as Figma, landing as shipped design"**. The playground file (`landing/playground.html`) is treated as a frozen pattern library — a complete inventory of every class, token, and structural recipe that `landing/style.css` supports. The new `landing/landing-v2.html` is the *application* of that library to a single editorial narrative. There is no component layer between them, no template engine, no shared partials. The translation is done by hand, once, from playground patterns to landing sections.

The key architectural insight is **inversion of demonstration**: the current `index.html` narrates its own design system ("here is the masthead, here is the step grid"), which is appropriate for a playground but corrosive on a landing page. The new file removes every meta-label and lets each pattern carry editorial weight as itself — a masthead is a masthead, a lede is a lede, a demo strip is a real spec rendered in miniature. This collapses the gap between "design system exists" and "design system is in production use," which is the entire payload of a documentation-first methodology tool's front door.

Three boundaries hold the design clean: (1) **CSS is read-only** — `style.css` is not modified; if a section's required class is absent, the section is dropped, never invented; (2) **JavaScript is minimal and ported, not authored** — only the existing theme toggle and date label move over verbatim; (3) **Content is placeholder editorial filler** — paragraph counts and line lengths must respect the typographic patterns, but the real copy pass is a separate epic. These boundaries make the architecture a single static HTML artifact with zero new surface area in any other file.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P4 — No Speculative Abstractions** | Single hand-authored HTML file. No template engine, no partials, no component system. The one concrete case is one landing page. |
| **P7 — File Size & Structure** | One file, one purpose. The 200-line guideline applies to logic files; static markup is allowed to exceed it because there is no logic to factor. |
| **Read-Only CSS Boundary** | `landing/style.css` is treated as an immutable pattern library. Missing class → drop the section, never add the class. |
| **Reference-as-Source-of-Truth** | The playground is the single source of pattern shapes. Where playground and current `index.html` disagree, playground wins. |
| **Inversion of Demonstration** | Patterns are used, not labelled. No "here is the X" framing anywhere in markup or copy. |
| **Parallel, Not Replacement** | Ships alongside `index.html`. The swap to `index.html` is a separate decision under a separate epic. |
| **Channel-Aware Output** | Landing is a web channel — relies entirely on `style.css` responsive rules. No mobile-specific overrides authored here. |

## Component Design

### Pattern Inventory Pass
**Purpose**: Verify before building. Every class hook the new file will use must already exist in `landing/style.css`. The inventory is a one-shot grep pass over the playground's class list cross-checked against the stylesheet, producing a gate: green-listed classes are usable; anything else gets the section dropped.

**Output**: An informal allow-list of class names. The playground file itself is the enumerated reference — no separate document is produced. This pass is purely defensive against the failure mode of "playground had a stale class that style.css no longer ships."

### Masthead Section
**Purpose**: Functions as the page's actual `<header>`, not a demonstration of header patterns. Contains the newspaper title in Playfair, italic tagline in Source Serif, edition label, dynamic date, anchor nav, and theme toggle. Inline SVGs for the sun/moon glyphs — no Lucide, no icon font, no CDN.

**Trade-off**: Inline SVG bloats the HTML compared to icon-font references, but eliminates a network dependency and matches the existing `index.html` icon strategy. The cost is acceptable for a static landing page where bytes don't compound across a session.

### Lede Section
**Purpose**: The editorial hero. Two-column layout (`.lede` / `.lede-main` / `.lede-aside` / `.lede-divider`) where the left column carries headline + deck + primary CTA and the right column carries an `.output-grid` of five `.output-card` elements representing the spec artifacts (analysis, epic, architecture, timeline, implementation guide).

**Why a card grid instead of a bullet list**: The card grid *is* the artifact enumeration. A `<ul>` would be a fallback to a content-first idiom that the design system has explicitly replaced with cards. Choosing the card grid keeps the editorial integrity intact even when copy is placeholder.

### Overline Section Sequence
**Purpose**: Four major sections — *what it does*, *how it works*, *see it in action*, *start building* — each opening with the `.overline` (red uppercase) + `.section-heading` (Playfair display) pair. The overline sequence acts as the document's table of contents in disguise; readers track position by typographic rhythm rather than explicit nav state.

**Trade-off**: Four sections is a deliberate ceiling. Adding a fifth would dilute the rhythm; dropping to three would shorten the editorial arc below newspaper plausibility. The count is tuned to the design, not to content volume.

### Steps Component
**Purpose**: Three-column `.steps` grid with large Playfair numerals (`.step-num`), `.step-title`, and `.step-body` only. Describes the methodology arc — braindump → spec set → implementation — at body-copy weight. Critically, **no `.step-code` blocks**: code mockups belong to the playground as a pattern showcase, not to a landing page that is selling the methodology rather than the artifacts.

**Why no code mockups**: A landing page that shows code samples shifts the reader's frame from "this is a methodology" to "this is a code generator." Spec Doc's value is editorial discipline applied to specs; code samples on the front door undercut that positioning.

### Demo Strip
**Purpose**: A miniaturized but real spec rendered inline using `.demo-strip` / `.demo-masthead` / `.demo-sidebar` / `.demo-content`. The reader sees the newspaper layout applied to a spec excerpt, in situ, mid-scroll. This is the strongest single proof point on the page: the methodology produces *this*, and *this* is what you are looking at right now.

**Trade-off**: The demo strip in the playground is labelled as a demo. Stripping the label changes its meaning — it becomes a sample of the product rather than a sample of the component. This is the correct reading for a landing, but it does mean the same markup serves two purposes across the two files. We accept that ambiguity because both readings rely on identical structure.

### Pull Quote
**Purpose**: A typographic breather. `.pullquote-row` with one editorial pull quote about the methodology. No chrome — pure typography on the page.

**Why one, not many**: Multiple pull quotes turn a landing into a testimonial wall. One pull quote functions as an editorial pause, which is what newspaper layout uses pull quotes for; this aligns the visual idiom with the design system's stated grammar.

### Pricing & Footer
**Purpose**: Existing patterns from `style.css` reused with correct token usage. Pricing leads with overline + tier cards + primary CTA. Footer matches current landing's footer pattern verbatim.

**Why reuse, not redesign**: These sections are the least editorial and the most transactional. The playground already settled their shape; relitigating them on this epic would expand scope without improving the editorial argument the upper sections make.

### Theme Toggle & Date Label
**Purpose**: Verbatim port from `index.html` — same sun/moon SVG icons, same toggle handler, same date-label population script. No new JavaScript is authored.

**Trade-off**: Copying the script blocks rather than extracting them to a shared file means duplication between `index.html` and `landing-v2.html` while both exist. We accept this because (a) the duplication window is bounded — when `landing-v2.html` is promoted, `index.html` becomes `index-old.html` and the duplication ends; (b) extracting to a shared file would touch both files, expanding blast radius beyond this epic; (c) the script is small enough that duplication cost is lower than coordination cost.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Markup | Static HTML5 | Static, deployed by nginx. No runtime, no template engine — the single concrete case principle (P4) makes any abstraction speculative. |
| Styling | Existing `landing/style.css` (read-only) | The stylesheet is the contract. Treating it as immutable forces the new page to live within the design system rather than extending it. |
| Icons | Inline SVG + emoji | Matches the existing landing's strategy. No CDN, no icon font, no `data-lucide`. Keeps the page self-contained and offline-renderable. |
| JavaScript | Two ported scripts (theme toggle, date label) | Smallest possible JS surface. Both already exist in `index.html` and have no dependencies. |
| Tooling | None | No bundler, no preprocessor, no build step. The file is editable by hand and serves as-is. |
| Hosting | nginx:alpine (existing landing container) | Reuses the static-serving setup already configured for `landing/`. Reachable at `http://localhost:8096/landing-v2.html`. |
| Backend | None | Pure static. No Flask routes, no API, no analytics, no forms. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Build a parallel `landing-v2.html` rather than modifying `index.html` | Allows side-by-side comparison and zero-risk iteration. The current landing keeps working while the new one matures. | Two landings exist temporarily; the swap to `index.html` is deferred to a later decision. |
| Treat `style.css` as immutable for this epic | Forces design discipline — if a section can't be built from existing patterns, the section is wrong, not the stylesheet. | Some sections that *could* be sharper with a tweak are constrained to existing forms. The constraint is the point. |
| Use placeholder editorial copy, not real product copy | Separates the design pass from the content pass. Reviewing structure with placeholder text is faster and cleaner than reviewing structure entangled with copy. | The page won't be shippable as the real landing until the content epic runs. That's expected. |
| Drop sections rather than add classes | If a playground pattern depends on a class that's missing in `style.css`, the section is omitted, never patched. | Some envisioned sections may not appear in v1. This is a feature — it surfaces stylesheet gaps as scope decisions, not silent additions. |
| Inline SVG icons rather than icon font / CDN | Zero external dependencies. Matches existing landing strategy. Renders offline. | Markup is heavier than `<i class="...">`; tolerable for a single page. |
| Port the theme toggle script verbatim instead of extracting | Smaller blast radius — touches one new file, not two. The duplication window closes when `landing-v2.html` replaces `index.html`. | Temporary duplication of ~20 lines of JS across two files. |
| Single HTML file, no partials or templates | P4 — one concrete case. Templating for one consumer is a speculative abstraction. | If a third landing variant is ever needed, copy-and-edit again. We pay that cost only if it ever happens. |
| Rely on `style.css` for all responsive behaviour | The stylesheet already encodes the responsive grammar of the design system. Authoring page-specific media queries would fragment that grammar. | If a section breaks on mobile due to a stylesheet gap, the fix lives in a separate stylesheet epic, not here. |
| Four overline sections, exactly | Tuned to the editorial arc length. Three feels truncated; five dilutes rhythm. | Fixed structure constrains content planning — the content epic must fit the methodology story into four sections. |
| No code blocks anywhere on the page | A landing page showing code reframes the product as a code generator. Spec Doc's pitch is editorial discipline; code samples undercut that. | Visitors who want to see code output won't see it on the landing. They see it once they're in the product. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking