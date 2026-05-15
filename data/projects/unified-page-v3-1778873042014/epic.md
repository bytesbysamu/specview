# 🎯 Epic: Unified Page V3

## Business Value

The newspaper aesthetic isn't a skin — it's spec-doc's entire value proposition. V2's component refactor was the right architectural move, but it fractured the product's visual identity: the landing pitch, playground, and app workspace render as three different products glued onto one page. Users scrolling from the polished pitch into a generic-looking app section experience a bait-and-switch that undermines trust and kills conversion. Worse, the upgrade button currently logs users out — a trust-destroying bug that makes paying customers disappear at the exact moment they signal purchase intent.

V3 reunifies the product by merging V1's proven newspaper rendering with V2's clean component architecture. The strategic bet is that "the demo IS the product" — a visitor's first braindump in the playground should feel identical to their 50th as a paying subscriber. When the three sections (pitch, playground, workspace) share one visual language, the page scroll itself becomes the onboarding funnel. No separate routes, no visual seams, no "sign up to see the real thing." This directly impacts signup conversion, retention through the upgrade flow, and the perceived quality that justifies a subscription.

The work is scoped to 4 days of execution plus a 1-week soak period. Every phase is independently shippable, and V1 remains untouched at `/` as a safety net until pixel-parity is proven. The cost of NOT doing this is continuing to ship a product whose app section contradicts its own marketing — every day the visual disconnect persists, it erodes the brand the landing pitch works to build.

## Scope

### What This Epic Covers

- **Upgrade-button logout fix** – Users clicking "upgrade" are logged out instead of routed to the upgrade flow; blocks all other work because it destroys trust at the payment boundary
- **Visual parity between V1 and V2** – V2's app workspace renders pixel-identical to V1's newspaper aesthetic (card padding, grid sizing, fonts, masthead, animations, usage meter, word count) using V2's decomposed component architecture
- **Test migration to V2 DOM** – All 155 Karma unit tests and the E2E suite pass against V2's component structure without regressing V1
- **Route cutover with escape hatch** – `/` serves V2, `/v1` preserves V1 as a rollback path for a 1-week soak period
- **Dead code cleanup** – V1-only files, duplicate CSS, and the `/v1` escape hatch removed after soak period confirms stability

### What This Epic Does NOT Cover

- ❌ **Playground braindump → first project on signup** — Backend feature requiring localStorage persistence and auth-triggered migration; revisit after V3 route cutover is stable
- ❌ **Live front page / scroll-driven narrative / progressive disclosure** — Product redesign, not a refactor; revisit as V4 after V1 retirement completes
- ❌ **Transform playground into "new project" workspace for auth users** — Feature work hiding inside a refactor; for V3, hide or collapse the playground for authenticated users; revisit post-cutover
- ❌ **Kill the playground as a separate concept** — Requires rethinking onboarding flow; trigger: V3 stable for 2+ weeks with no rollbacks
- ❌ **Speculative token alias file (`_token-bridge.css`)** — Only relevant if CSS strategy picks the bridge approach over porting V1 HTML; do not build without a decision

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Fix upgrade-button logout bug** | None | — | 0.5 days | High |
| 2 | **Achieve visual parity: V1 rendering in V2 components** | Task 1; masthead + CSS strategy decisions resolved | — | 1.5 days | High |
| 3 | **Migrate test suite to V2 DOM structure** | Task 2 | — | 1.5 days | High |
| 4 | **Route cutover with `/v1` escape hatch** | Task 3 | — | 0.5 days | High |
| 5 | **V1 dead code cleanup** | Task 4 + 1-week soak with zero rollbacks | — | 0.5 days | Low |

## Success Criteria

- ✅ Upgrade button navigates to upgrade flow — no logout, no session loss
- ✅ V2 grid, cards, spacing, and typography are pixel-identical to V1 (verified by screenshot overlay at 50% opacity)
- ✅ V2 masthead, panel slide animation (`@panelEnter`), usage meter, and word count pipe all render correctly
- ✅ All 155 Karma unit tests pass against V2 components; E2E suite passes against both `/` and `/v1` during transition
- ✅ `ng build --configuration production` passes at every phase boundary
- ✅ V1 remains untouched and accessible at `/v1` for the full 1-week soak period
- ✅ Landing pitch, playground, and app workspace share one visual language — no CSS variable fallback to browser defaults
- ✅ Zero V1 rollbacks during the 1-week soak triggers dead code cleanup

## Related Documents

- [Analysis](./analysis.md) – CSS token misalignment root cause, open design decisions, and dependency sequencing driving this epic
- [Solution Architecture](./architecture.md) – CSS strategy decision, component boundary mapping, and V1→V2 HTML porting approach
- [Timeline](./timeline.md) – Phase-by-phase status tracking across the 4-day budget + 1-week soak