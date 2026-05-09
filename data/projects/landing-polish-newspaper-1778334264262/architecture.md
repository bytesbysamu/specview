# 🏗️ Solution Architecture: landing-polish-newspaper

## Architecture Overview

The landing page polish is a **purely presentational refactor** that introduces a thin layer of shared "newspaper primitives" between the existing Angular landing components and the design tokens extracted from `ux-polish-newspaper-1778238000`. No new backend, no new routes, no information-architecture rework — the architecture is deliberately small because the work is deliberately bounded.

The mental model is a **three-tier styling pipeline**: (1) raw design tokens (CSS custom properties for type scale, rules, grid, spacing, color) live in a single global stylesheet sourced from the reference bundle; (2) a small set of **shared Angular primitives** (editorial section wrapper, masthead, rule, eyebrow, drop-cap lead) consumes those tokens and exposes them as composable components; (3) the existing landing sections are **rewired to use the primitives**, replacing ad-hoc Tailwind/utility classes with the editorial vocabulary already proven on the playground surface. The playground is treated as an oracle, not a target — its compiled output is the reference for "what shared primitives should produce."

The key insight is that the design system already exists and has already been validated on a sibling surface. The only architectural risk is **divergence**: if landing-only and playground-only versions of the same primitive emerge, the system fragments and the next surface (a future humaniz.me port, per the epic's secondary payoff) will have to choose between two implementations. The architecture therefore prioritizes **primitive extraction** over speed of restyle — primitives are defined first, then both surfaces converge on them.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | N/A for this epic (no external service calls); design tokens play an analogous role — the global stylesheet is the only place raw token values live, and primitives are the only consumers. |
| P2 — Thin HTTP Layer | N/A — Flask :3101 is untouched. Reaffirmed as a non-goal so scope creep is rejected at review time. |
| P4 — No Speculative Abstractions | Primitives are extracted only where the landing page and playground genuinely share a pattern. A pattern that appears once stays inline; we resist building a "newspaper component library" beyond what two surfaces already justify. |
| P6 — Channel-Aware | Landing is web-only; primitives target desktop-first editorial layout but degrade to a single-column phone view. No Telegram/Ionic considerations. |
| P7 — File Size & Structure | Each primitive is its own file with a named export, well under 200 lines. Existing landing section files must remain under 200 lines after the refactor — if a section grows past that during application, it is split before merge. |
| Reference Single-Source-of-Truth | Design tokens live in exactly one stylesheet. Section components never hardcode token values; they consume CSS custom properties or primitive components. |
| Information Architecture Frozen | The architecture explicitly forbids changes to section order, copy, or CTA placement. Polish operates on visual presentation only — this is encoded as a review checklist, not a runtime constraint. |

## Component Design

### Newspaper Token Stylesheet
**Purpose**: Single source of truth for the editorial design system extracted from `ux-polish-newspaper-1778238000`.

Holds the type scale (display, headline, deck, body, caption, eyebrow), rule weights (hairline, medium, bold horizontal rules), grid metrics (column counts, gutter widths, max content width), spacing scale, and the restrained color palette (paper, ink, muted, accent). Loaded globally so any component can reference tokens via CSS custom properties. Tokens are imported verbatim from the reference bundle to guarantee parity with the playground; values are never duplicated inline in components.

### Editorial Section Wrapper
**Purpose**: Replace the generic landing section container with one that enforces newspaper grid rules.

Provides the editorial column structure, top/bottom rule treatment, and section-level vertical rhythm. Existing landing sections (hero, value props, how-it-works, footer) are wrapped in this primitive instead of carrying their own grid CSS. Trade-off: sections lose some bespoke flexibility; gain consistency and one place to tune rhythm globally.

### Masthead / Headline Primitives
**Purpose**: Encode the type-scale ladder so headlines, decks, and eyebrows render identically wherever they appear.

A small set — headline, deck, eyebrow, lead paragraph — backed by the shared type tokens. The hero's primary headline and a how-it-works step heading must produce the same letterforms at the same sizes; primitives enforce this without each section repeating type rules.

### Rule Component
**Purpose**: Editorial horizontal rules (hairline, medium, bold) as a single primitive with a weight prop.

Newspapers use rules constantly to delimit sections and signal hierarchy. Centralizing avoids three slightly-different border-top declarations scattered across sections.

### Drop-Cap Lead (optional, only if reference bundle uses it)
**Purpose**: Editorial opening paragraph treatment, applied to the hero or first content block.

Included only if the reference bundle's playground application uses it; otherwise omitted per P4.

### Landing Section Components (existing, rewired)
**Purpose**: Existing hero, value-proposition, how-it-works, and footer components — same structure, restyled.

These keep their current names, inputs, copy, and order. Their templates change to consume the primitives above; their styles drop ad-hoc utility classes in favor of token-driven editorial styling. No new sections are added; no existing sections are removed.

### Playground Reconciliation Layer
**Purpose**: Not a runtime component — a one-time refactor pass.

Where the playground already implements a newspaper pattern inline, that implementation is **lifted into a shared primitive** and the playground is rewired to consume the primitive. This is the only architectural change to the playground surface, and it exists so both surfaces share one definition of each pattern. Without this step, the epic's success criterion of "visual parity via shared primitives" cannot be verified.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend Framework | Angular 17 standalone components with signals | Already in use at `web-ng/`; matches builder preference; no migration cost. |
| Styling Approach | CSS custom properties + component-scoped styles | Tokens via custom properties give runtime themability and a single source of truth; component-scoped styles keep primitives encapsulated and prevent leakage. |
| Token Source | Verbatim import from `ux-polish-newspaper-1778238000` reference bundle | Reference is treated as canonical; re-deriving values would risk drift from the playground's already-applied system. |
| Build Verification | `ng build --configuration production` | Existing build gate per P7; no new tooling introduced. |
| Backend | Flask :3101 — **untouched** | Epic is presentational; introducing backend changes would violate scope. |
| Responsive Strategy | Desktop-first editorial layout, single-column collapse below ~720px | Newspaper grids are inherently wide; mobile is a graceful fallback, not a co-equal target, since landing traffic on phones still must render but is not the primary conversion surface. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Extract shared primitives instead of restyling sections directly | The playground already proved the design system; landing is the second surface. Two surfaces justify primitives (P4 threshold met). Future surfaces compound the value. | Slightly slower than a direct restyle; requires the playground reconciliation pass to lift inline implementations. Accepted because divergence cost is higher than extraction cost. |
| Tokens as CSS custom properties, not Sass variables or TS constants | Custom properties survive into the runtime DOM, enabling browser-devtools tweaking and future theming; Angular component styles can consume them without import plumbing. | Loses compile-time validation of token names. Mitigated by keeping the token list small and documented in the single global stylesheet. |
| Verbatim token import from reference bundle, not re-interpreted | Guarantees byte-level parity with playground output; eliminates "is this the right shade of muted?" debates. | If the reference bundle has a quirk or typo, it propagates. Accepted because the bundle was already validated on the playground. |
| Lift playground's inline patterns into primitives (reconciliation) | Required for "visual parity via shared primitives" success criterion to be verifiable. Without it, parity is coincidental, not architectural. | Touches a surface (playground) that the epic otherwise treats as reference-only. Justified as a one-time consolidation, not ongoing playground work. |
| Freeze information architecture at the architectural level, not just as policy | Encoding "section order, copy, CTAs unchanged" as a review checklist makes scope creep detectable in PR review rather than discoverable post-merge. | None significant; this is a process decision with negligible runtime cost. |
| Desktop-first with mobile fallback, not mobile-first | Editorial layouts are defined by their wide-grid character; designing mobile-first would force the primitive API to accommodate single-column as the default and treat the newspaper grid as an enhancement, inverting the design intent. | Requires explicit mobile QA at 360px width (encoded in success criteria). Accepted because the design language is fundamentally desktop-native. |
| No new sections (pricing, testimonials, blog) even if the editorial aesthetic invites them | Polish epic, not rewrite epic. Adding sections changes conversion narrative and requires copy work outside scope. | Some natural editorial layouts (e.g., a "front page" with multiple stories) are unrealized. Deferred to a future epic if the polish lands well. |
| Treat playground as oracle, not target | Playground already has the design applied; its compiled output is the spec for "correct." Re-deriving primitives without checking against playground would risk subtle divergence. | Requires the auditor to actually compare rendered output, not just code. Accepted as a one-time cost. |
| No Redis, no background jobs, no async 202 pattern (P3) | This is a frontend-only epic; nothing runs longer than a build. P3 is non-applicable. | None — explicitly noted so reviewers don't expect a job pattern. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking