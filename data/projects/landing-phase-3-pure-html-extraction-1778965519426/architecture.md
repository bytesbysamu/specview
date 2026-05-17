# 🏗️ Solution Architecture: Landing Phase 3 — Pure HTML Extraction

## Architecture Overview

This is a subtractive architecture problem, not an additive one. The design system already exists in `landing/style.css` (1224 lines of newspaper-aesthetic classes, tokens, responsive breakpoints, and dark mode overrides). The content already exists in `web-ng/src/app/pg-landing-data.ts` (curated copy for every section). The architecture's job is to define the extraction strategy — which classes map to which sections, which content survives the editorial cut, and how a single HTML file stays under 300 lines while communicating the full product narrative.

The mental model is a newspaper front page rendered as a dependency-free HTML document. One file, one stylesheet, one font import. No build step, no JavaScript framework, no component system. The architectural rigor lives entirely in class selection discipline — every element must map to an existing `style.css` class or it does not ship. This constraint eliminates an entire category of design drift: if you cannot express it with existing vocabulary, the idea is wrong for this page.

The deployment topology is unchanged: the `landing/` directory ships as an nginx:alpine container serving static files. The rewrite replaces `landing-v2.html` with a clean `index.html` that references the same `style.css` already deployed. Zero infrastructure changes, zero build pipeline modifications, zero new dependencies.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | Single HTML file with hardcoded content. No templating system, no data layer, no component extraction for a page that will change quarterly at most. |
| P7 — File Size & Structure | Hard ceiling of 300 lines. Every section must earn its bytes. Sections that push past the budget get cut, not compressed. |
| Design System as Constraint | `style.css` is not a toolkit to extend — it is a closed vocabulary. If a visual pattern requires a class that does not exist, the pattern is rejected. |
| Editorial Curation | The playground is exhaustive; the landing page is selective. Fewer sections, tighter copy, harder cuts. Every element must pass: "does this help someone decide in 30 seconds?" |
| Zero-Violation Compliance | No border-radius, no box-shadow, no inline styles, no hardcoded colors, no unauthorized fonts. Violations are not bugs to fix later — they are architectural failures that block shipping. |

## Component Design

### Section Architecture

**Purpose**: Define the vertical flow of the page as a sequence of semantic sections, each mapping to a proven `style.css` layout pattern.

The page divides into nine sections in strict reading order. Each section is a self-contained HTML block using existing grid or flex utilities from the stylesheet. No section depends on another section's markup — they are vertically independent blocks that happen to share a page. This means sections can be reordered or removed without cascading changes.

The section sequence follows newspaper hierarchy: masthead establishes identity, hero/lede delivers the core proposition, stat strip provides social proof through numbers, then progressively deeper detail (what ships, how it works, versus competitors, pricing, FAQ) for visitors who scroll past the fold.

### Class Mapping Layer

**Purpose**: Bridge between conceptual sections and concrete `style.css` class names.

Before any HTML is written, every planned section must have a verified mapping to existing classes. This is the feasibility gate — if a section concept cannot be expressed with available classes, it gets redesigned or dropped. The audit produces a section-to-class lookup table that becomes the implementation contract.

Key class categories to map: layout containers (grid patterns, max-width wrappers), typography (headline sizes, body text, overlines, labels), structural elements (borders, separators, spacing), interactive states (hover effects already defined), and responsive overrides (breakpoint-specific grid changes).

### Content Extraction Strategy

**Purpose**: Define how copy moves from `pg-landing-data.ts` into static HTML without loss of editorial intent.

Content extraction is a one-way, one-time operation. The TypeScript data file contains structured arrays (output cards, comparison rows, FAQ items, pricing features). Each array maps to a specific HTML section. The extraction preserves the data's hierarchy — a comparison row becomes a table row, an FAQ item becomes a details/summary pair — but all binding is compile-time (human pastes content into markup). No runtime data access.

The editorial filter applies during extraction: not all items in `pg-landing-data.ts` ship. The architecture defines which items from each array survive and why. Items that add length without advancing the 30-second comprehension goal get cut regardless of how complete they are in the source data.

### Dark Mode Implementation

**Purpose**: Ensure visual correctness across both themes with zero additional CSS.

Dark mode is architecturally free because the design system uses CSS custom properties exclusively. Every color in the page resolves through tokens (`--ink`, `--bg`, `--border`, `--red`, `--accent`) that have `[data-theme="dark"]` overrides already defined in `style.css`. The only JavaScript on the page is a theme toggle — approximately ten lines that flip the data attribute and persist the choice to localStorage.

The architectural constraint: no element may use a color value that bypasses the token system. If a section needs a color distinction not available via existing tokens, that section must be redesigned to use a structural distinction (borders, spacing, font weight) instead.

### Performance Architecture

**Purpose**: Guarantee sub-second load time through extreme minimalism.

The performance budget has exactly three network requests beyond the HTML document itself: one CSS file (already cached if the visitor has seen any page on the domain), one Google Fonts request (three families, specific weights), and the favicon. No images, no JavaScript bundles, no third-party scripts, no analytics pixels.

This is not an optimization strategy — it is a structural impossibility of being slow. With no render-blocking JS, no image decoding, and a single stylesheet under 50KB, first contentful paint is bounded by network latency plus HTML parse time. On any modern connection this is well under one second.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Markup | Semantic HTML5 | No framework overhead for a static page. Native elements (details/summary for FAQ, table for comparison) provide accessibility free. |
| Styling | Existing `landing/style.css` | 1224 lines of proven, responsive, dark-mode-ready newspaper aesthetic. Zero additions permitted. |
| Typography | Google Fonts (Playfair Display, Source Serif 4, Source Sans 3) | Three-font editorial system already defined in stylesheet. Single external request, display=swap for no FOIT. |
| Interactivity | Vanilla JS (theme toggle only) | Ten lines for dark mode persistence. No scroll handlers, no intersection observers, no animation triggers. |
| Serving | nginx:alpine container | Existing deployment topology. Static file serving with gzip. No server-side rendering needed. |
| Content source | `pg-landing-data.ts` (extraction, not runtime) | Hardcode curated subset directly into HTML. Source file is reference material, not a dependency. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Hardcode all content instead of JS templating | A 300-line HTML file with baked content loads faster, has no JS failure modes, and is trivially auditable for compliance. The content changes quarterly at most — dynamism has no value here. | Content updates require editing HTML directly. Accepted because updates are rare and the file is small enough to edit confidently. |
| Omit demo strip and interactive elements | Static HTML cannot convincingly demonstrate a generation workflow. A bad demo hurts more than no demo. The hero's static file list (five filenames with timing) communicates output without interaction. | Visitors must click through to the app to see generation in action. Accepted because the comparison table and output cards already communicate the value proposition. |
| Omit testimonials and pull quotes | No real testimonials exist. Fabricated quotes undermine the credibility of a tool that promises rigor. Empty space is more honest than fake social proof. | Page lacks peer validation. Accepted because the comparison table serves as indirect proof of differentiation. |
| Use native details/summary for FAQ | Zero JavaScript. Accessible by default. Styleable with existing classes. Keyboard-navigable. Progressive enhancement — works without CSS loaded. | Cannot animate open/close smoothly in all browsers. Accepted because animation violates the "typography and borders only" principle anyway. |
| Hero shows static file list, not animated generation | Animations (shimmer, pulse, sequential reveals) violate the design system's "no decorative animation" rule. A static list of five files with one marked as in-progress communicates the same information. | Less visually dramatic on first load. Accepted because editorial restraint is the brand — the page should feel calm, not performative. |
| Three-column grid for output cards at desktop, single column on mobile | Existing responsive grid classes handle the reflow. Five cards in a 3+2 layout (three top, two bottom centered) uses standard grid without custom breakpoint logic. | Slight visual asymmetry with five items. Accepted because forcing a 5-column layout would require new CSS or produce unreadably narrow cards. |
| Comparison table as native HTML table element | Tables are the semantically correct choice for tabular comparison data. Screen readers announce row/column relationships. Existing table classes in style.css handle typography and borders. | Tables are harder to make responsive. Accepted because the six-row, three-column structure fits comfortably at 768px minimum width with existing responsive overrides. |
| Single HTML file rather than partials or includes | No build step means no broken includes, no partial-not-found errors, no nginx SSI configuration. One file, readable top-to-bottom, deployable by copying. | Harder to reuse sections across pages. Accepted because there is only one page — reuse is speculative abstraction (P4 violation). |
| Cut any section that pushes past 300-line budget | The line budget is a forcing function for editorial discipline. If nine sections cannot fit in 300 lines, sections get shorter or get removed. The budget is not a suggestion. | Some sections may be more compressed than ideal. Accepted because compression forces better copy — every word that survives the budget earns its place. |

## Section-to-Class Mapping Strategy

The feasibility audit must produce a verified mapping for each section before HTML authoring begins. The mapping follows this structure:

**Masthead** — container class for max-width centering, flex for horizontal layout, Playfair at the largest defined heading size, border-bottom for newspaper rule.

**Hero/Lede** — two-column grid class at desktop, single-column reflow at mobile breakpoint. Left column uses headline class hierarchy (overline, h1, deck paragraph). Right column uses a bordered container with monospace-styled file list.

**Stat Strip** — four-item flex row with border-right separators. Playfair for numbers, sans-serif for labels. Existing stat or metric classes if available; otherwise, heading + label class combination.

**Output Cards** — grid container with defined column count at each breakpoint. Each card uses bordered container class, heading for filename, muted text class for description.

**How It Works** — three-item layout (grid or flex). Giant number uses largest Playfair heading class. Body uses standard paragraph class. Excerpt uses background-color token with reduced-size text class.

**Comparison Table** — table element with existing table classes for header styling, row borders, and alternating emphasis. Muted class for competitor column cells.

**Pricing** — two-column grid. Each tier uses bordered container, heading hierarchy, list with dash-style bullets (if available in stylesheet, otherwise standard list with custom content via existing class).

**FAQ** — vertical stack of details/summary elements. Summary uses Playfair heading class. Content uses standard body text class. Bottom border between items.

**Footer** — centered container, muted text, horizontal link list with separators.

Any section where the audit cannot identify existing classes for all required elements triggers a design decision: simplify the section to fit available vocabulary, or remove it entirely.

## Responsive Strategy

The architecture relies entirely on existing breakpoint definitions in `style.css`:

At 1100px and above: full desktop layout — two-column hero, three-column output grid, three-column how-it-works, two-column pricing, full-width comparison table.

Between 768px and 1100px: tablet adaptation — hero may remain two-column at reduced widths, grids collapse to two columns where defined, table remains full-width with tighter padding.

Below 768px: mobile — all grids single-column, hero stacks vertically (headline above file list), stat strip wraps to 2x2 if defined or stays horizontal with smaller text, table scrolls horizontally if needed (existing overflow-x pattern).

No new media queries are written. If a section's responsive behavior is unsatisfactory with existing breakpoints, the section's desktop design is simplified until the existing responsive rules produce acceptable mobile output.

## Risk Mitigation

**Risk: style.css gaps** — The audit may reveal that certain conceptual sections have no adequate class mapping. Mitigation: the section list is ordered by priority. If gaps appear, lower-priority sections (FAQ, footer) get simplified first. The page ships with fewer sections rather than new CSS.

**Risk: 300-line budget is too tight** — Nine sections with meaningful content may exceed the budget even with minimal markup. Mitigation: the how-it-works excerpts and FAQ items are the most compressible — reduce item count (three FAQ items instead of seven, two how-it-works steps instead of three) before cutting entire sections.

**Risk: Dark mode reveals untested class combinations** — A class that looks correct in light mode may produce insufficient contrast in dark mode. Mitigation: every token-based color pairing has been validated in the playground components. The landing page uses the same token pairs — no new combinations that could produce contrast failures.

## Related Documents

- [Analysis](./analysis.md) — Design system violations and open questions driving this rewrite
- [Epic](./epic.md) — Scope, tasks, success criteria, and effort estimates
- [Timeline](./timeline.md) — Status tracking for all four tasks