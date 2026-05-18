# 🎯 Epic: landing-polish-newspaper

## Business Value

The spec-doc landing page is the first surface a prospective user (likely a fellow solo founder or small-team engineer) sees before deciding whether the documentation-first methodology is worth their time. A generic SaaS-template aesthetic signals "another tool"; a deliberate editorial/newspaper aesthetic signals point of view — that this product treats specs as serious written artifacts, not boilerplate. The polish converts curious visitors into trial users by matching the visual register to the product thesis.

The reference bundle `ux-polish-newspaper-1778238000` already contains the design intent (typography scale, grid rules, editorial cues) and was applied successfully to the playground surface. Reusing those tokens on the landing page is the highest-leverage UI work available: the design decisions are already paid for, only application remains. No new backend, no new product surface — just visual conversion lift on the page that already gets every inbound click.

For Sam (solo, multi-project), the payoff is twofold: (1) a landing page that actually reflects the product's tone, and (2) consolidation of newspaper design tokens into shared Angular primitives that future spec-doc surfaces (and potentially humaniz.me) can pull from without re-deriving the system.

## Scope

### What This Epic Covers
- **Reference ingestion** – read every file in `ux-polish-newspaper-1778238000` and extract the design tokens, type scale, grid rules, and component patterns that define the newspaper aesthetic
- **Current landing audit** – inventory the existing spec-doc landing page (Angular :4201) sections, components, and copy blocks so polish targets are concrete, not hypothetical
- **Playground reconciliation** – diff the playground's already-applied newspaper styling against the landing page to identify shared primitives vs. landing-only adaptations
- **Newspaper token application** – restyle existing landing sections (typography, rules, grid, spacing, color) using the reference bundle's tokens without restructuring information architecture
- **Responsive verification** – confirm editorial layout degrades gracefully from desktop down to mobile widths, since landing is web-only but must not break on phones

### What This Epic Does NOT Cover
- ❌ **Backend/API changes** — landing is presentational; Flask :3101 stays untouched
- ❌ **Information architecture redesign** — section order, copy, and CTAs remain as-is; this is polish, not rewrite
- ❌ **New sections** (pricing, testimonials, blog) — polish operates only on what currently exists
- ❌ **Auth/onboarding funnel changes** — visual treatment only, no flow rework
- ❌ **Cross-project rollout** to humaniz.me, trendfy.me, Bubls — single landing page in scope
- ❌ **Mobile app surfaces** (Telegram, Ionic) — different channel, different constraints
- ❌ **Playground re-styling** — playground is treated as reference, not target

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Extract Newspaper Design Tokens from Reference Bundle** | None | — | 0.5 days | High |
| 2 | **Audit Current Landing Page & Playground Application** | None | Parallel with #1 | 0.5 days | High |
| 3 | **Define Shared Newspaper Primitives (Angular)** | 1, 2 | — | 1 day | High |
| 4 | **Apply Newspaper Treatment to Landing Sections** | 3 | — | 1.5 days | High |
| 5 | **Responsive Pass & Visual QA** | 4 | — | 0.5 days | Low |

## Success Criteria

- ✅ All design tokens from `ux-polish-newspaper-1778238000` (type scale, rules, grid, spacing, color) are codified in the spec-doc frontend as reusable Angular primitives
- ✅ Every existing landing page section renders with the newspaper aesthetic — no section left in the prior style
- ✅ Visual parity (where intentional) between playground and landing — shared primitives produce identical output across both surfaces
- ✅ Landing page passes `ng build --configuration production` with zero new warnings
- ✅ Layout remains usable at 360px width (smallest realistic mobile) — no horizontal scroll, no truncated CTAs
- ✅ No new backend endpoints, no changes to Flask :3101
- ✅ All touched component files remain under 200 lines (P7)
- ✅ Information architecture (section order, copy, CTAs) unchanged from pre-polish state

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking