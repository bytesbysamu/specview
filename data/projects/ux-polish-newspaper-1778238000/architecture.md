# 🏗️ Solution Architecture: UX Polish — Newspaper Feel, Phase 2

## Architecture Overview

This is a **CSS-and-template alignment epic**, not a system redesign. The mental model: the app already has the right tokens (color sync happened on 2026-05-05) but the structural and typographic chrome that consumes those tokens has drifted from the ClawBoi/landing reference. We are not adding new architecture — we are tightening the seam between the design system that already exists in `web-ng/src/styles/` and the components that render the masthead, section nav, reader, and editor toolbar.

The key insight: **the playground is the architecture**. `playground.html` is a live, inspectable Figma — every component, token, state, and animation already exists in working form. The architecture decision is therefore not "what do we build" but "how do we propagate the playground's verbatim CSS into the Angular SPA without inventing parallel implementations." This collapses the work to four boundaries: a token/utility layer (where the overline class lives once), the masthead component, the section nav component, and the reader/toolbar surfaces that consume icons.

The five primary tasks (foundation, masthead, overline adoption, icons, dark mode) plus the sidebar ordering task are intentionally parallel after the foundation lands. They touch disjoint files, share only the design tokens, and converge on a single visual outcome: the side-by-side screenshot test where landing masthead and app masthead are visually indistinguishable.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P4 — No Speculative Abstractions** | The overline is one CSS class with one consumer pattern. No mixin engine, no theme registry, no token transformer. Three usages of the same class is the design. |
| **P7 — File Size & Structure** | Every touched component stays under 200 lines. The masthead, section nav, and reader-header components are already small; the work is surgical edits, not rewrites. |
| **References as Single Source of Truth** | The playground is the contract. Color tokens, spacing, and overline tracking must match playground values verbatim — no rounding, no "close enough." |
| **Semantic-only color** | Color exists to communicate state. `--ink-muted` gray is the absence of state, never a state itself. This rule constrains every contrast fix in dark mode. |
| **Borders over shadows** | The single allowed shadow exception is the dark-mode modal elevation. Every other structural break — nameplate rule, sticky nav edge, toolbar anchor — is a border. |
| **Typography does the chrome** | No new icons, no new components, no decorative UI. Every gap is closed by changing a font, weight, size, or border specification. |

## Component Design

### Token & Overline Foundation
**Purpose**: Establish the single CSS class and any missing tokens that downstream tasks consume. The overline pattern (red, uppercase, `0.12em` tracking) is defined exactly once in the global stylesheet and applied via class binding at three call sites (section group headers, reader file-type label, error states). This is the dependency that unblocks tasks 2–5.

**Architectural decision**: The overline lives as a utility class in the global typography layer, not as a component. A component would imply structure and state; the overline is pure presentation. Defining it once enforces the "no duplicated overline styling" success criterion architecturally — there is nowhere else for it to live.

### Masthead & Nameplate
**Purpose**: Match the landing's masthead specification exactly — 64px Playfair title, Source Serif italic 13px tagline, `align-items: flex-end`. The nameplate rule (3px `--ink` `border-top`) attaches to the section nav directly below, not to the masthead itself, so that the rule scrolls naturally as a structural divider between publication head and section navigation.

**Architectural decision**: The nameplate rule belongs to the section nav component (not the masthead) because it is sticky behavior. When the nav sticks, the nameplate rule must travel with it; modeling the rule as a property of the masthead's bottom edge would detach it during scroll and break the "you are here in the publication" semantic.

### Overline Adoption Surface
**Purpose**: Three concrete consumers of the foundation class — project group headers in the grid, file-type label in the spec reader, error state messaging. Each consumer adds the class to existing markup; no consumer redefines color, tracking, or weight.

**Architectural decision**: The reader's file-type label is rendered above the spec title (not in the sidebar) because the sidebar already shows the filename. The reader view's job is to declare *category* — the overline is the editorial flag that says "ARCHITECTURE" or "EPIC" before you read the content. This separates filename (sidebar identity) from content type (reader semantic).

### Icon System
**Purpose**: Standardize icon rendering across the app at 13px, stroke-width 1.75, with semantic color by context. Defines the op chip → Lucide name mapping (expand → arrow-up-down, compress → minimize-2, clarify → help-circle, simplify → feather, tldr → align-left, bullets → list, brainstorm → sparkles, style → palette, undo → rotate-ccw, redo → rotate-cw).

**Architectural decision**: Icon size and stroke are set explicitly per usage site, not via a global icon wrapper component. Adding a wrapper would be a speculative abstraction (P4) — there are exactly two icon contexts (toolbar chips and inline content icons) and both are simple enough that explicit attributes beat a wrapper indirection. The op chip mapping is a static lookup, not a registry; one constant, one consumer.

**Color responsibility**: Icons inherit `currentColor` inside op chips so chip state (idle, hover, active) drives icon color naturally. Status icons take their parent status token. Navigational icons take `--ink-muted`; content icons take `--ink-light` to clear the 3:1 dark-mode floor.

### Dark-Mode Contrast Layer
**Purpose**: Four targeted fixes — modal elevation (the single sanctioned shadow exception), sticky toolbar border weight, section nav structural edge, and the icon contrast floor at `--ink-light` for meaningful icons.

**Architectural decision**: We do not introduce a `--shadow-modal-dark` token. The modal shadow is a one-shot pragmatic exception, scoped inside the modal component's dark-mode block. Tokenizing it would imply a shadow system that does not and should not exist. The fix is local; the rule (no shadows elsewhere) stays absolute.

The sticky nav's structural edge in dark mode comes from upgrading its border to `--border-dark` (which tracks `--ink`), not from adding a new color. This reuses the existing token contract: `--border-dark` is *defined* as the high-contrast structural break color in both modes.

### Spec File Sidebar Ordering
**Purpose**: Force the canonical reading sequence (braindump → analysis → epic → architecture → timeline → implementation-guide) regardless of filesystem order, so the sidebar reflects the methodology, not the directory listing.

**Architectural decision**: The ordering is enforced client-side in the Angular sidebar service — not in the Flask API. The API returns the file list as discovered; the SPA imposes the canonical sort. This keeps the API surface unopinionated (other consumers might want filesystem order) and localizes the methodology assumption to the SPA, where it belongs. The canonical order is a static array, not config — there is one correct sequence and no reason to make it variable.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend framework | Angular 17 (existing `web-ng/`) | No change. Standalone components and signals already in place. |
| Styling | Global CSS + component styles (existing) | Token system already established; this epic consumes it, doesn't extend it. |
| Icons | Lucide (existing) | Already shipped; this epic standardizes size/stroke/mapping, not the library. |
| Typography | Playfair Display + Source Serif 4 + Source Sans 3 (existing) | Source Serif italic adoption for tagline is already-loaded font, new usage. |
| Build verification | `ng build --configuration production` | P7 requirement; gates every commit. |
| Visual contract | `playground.html` | Verbatim source for tokens, classes, structural rules. |
| Backend | None touched | This is an `web-ng/`-only epic; Flask API is out of scope. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Overline as a single utility class, not a component | One CSS rule, three consumers, zero state. A component would imply structure that does not exist. | Cannot encapsulate variant logic later — but no variants are planned. |
| Nameplate rule attaches to the section nav, not the masthead | The rule is part of "where you are in the publication" — it must travel with the sticky nav, not stay anchored to the masthead bottom. | Slightly less obvious from reading the masthead component; documented in component design. |
| Modal shadow is a local dark-mode exception, not a tokenized system | Tokenizing implies a shadow system. The rule (no shadows) must remain absolute outside this one case. | Future modal restyles must remember the exception lives in the modal component; acceptable given file size constraint. |
| Icon size/stroke set explicitly at usage, not via wrapper component | Two contexts, simple attributes. A wrapper would be P4 violation. | Slight repetition across templates — acceptable; replacement is mechanical if a wrapper ever becomes justified. |
| Op chip icon mapping is a static constant, not a registry | One concrete consumer (the chip rendering), one mapping, no plugin model. | Adding a new op requires editing the constant — desired; new ops should be deliberate. |
| Sidebar ordering enforced in SPA, not API | Methodology assumption belongs to the SPA; API stays a neutral file-list provider. | Other clients (none today) would re-implement; acceptable until a second consumer exists (P4). |
| Reuse `--border-dark` for sticky nav dark-mode edge | Token already defined as high-contrast structural break; semantically correct without new tokens. | None — this is the token's intended use. |
| Icon contrast floor at `--ink-light` for meaningful icons only | Navigational chrome (back, close) can stay quieter at `--ink-muted`; content/state-bearing icons must clear 3:1. | Two-tier rule must be documented per usage; mitigated by the per-context table. |
| Tasks 2–5 run in parallel after foundation | Disjoint files, shared only on tokens. Foundation is the only true dependency. | Requires a final integration pass (the side-by-side masthead screenshot) to confirm cohesion; explicitly listed in success criteria. |
| `--status-attention` token deferred | Not in scope; reserved name only. Building it now would invent a feature without a consumer. | Amber stays absent from the system; if stale-spec detection ships, this token is the first task of that epic. |
| No animation system changes | Existing pulsing dot for `--status-running` already conveys positive motion correctly. | None — additions would be P4 violations. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking