# 🎯 Epic: Landing Page

## Business Value

The landing page is live but offers only a self-host path — clone-the-repo friction filters out the majority of visitors who arrived ready to click "sign up." Every visitor today either commits to a local install or bounces. Adding a hosted tier with a one-click signup converts the warm traffic that's already landing on the page into Specview accounts and, eventually, Pro subscribers.

This epic introduces the revenue surface for Specview. A two-tier model — Free (3 projects/month) and Pro ($29/month via Stripe) — captures hobbyist exploration without giving away unlimited use, while pricing Pro at a self-serve impulse-buy point that doesn't require a sales conversation. Stripe checkout handles the entire billing flow, so there's no custom billing UI to build or maintain.

The buyer is a solo developer or small-team PM who wants AI-structured spec docs without standing up infrastructure. Pro at $29/mo is a single-seat decision that sits below typical SaaS expense-approval thresholds, so adoption depends on the landing page making the value obvious in under five seconds and the signup path being one click away.

## Scope

### What This Epic Covers
- Hero CTAs — dual buttons: "Try it free" → Specview auth, "Self-host" → scrolls to existing section
- Pricing section — Free tier (3 projects/month) and Pro tier ($29/month) cards, side-by-side
- Stripe checkout link — Pro CTA links directly to hosted Stripe checkout (no custom billing UI)
- Specview auth link wiring — "Try it free" routes to deployed Specview signup/login URL
- Newspaper Design System adherence — all new sections use existing tokens (no shadows, no radius except 2px pills, three-font stack)

### What This Epic Does NOT Cover
- ❌ In-page auth forms — auth lives in the Specview app; landing only links out
- ❌ Custom billing/account UI — Stripe checkout owns the entire payment flow
- ❌ Annual pricing toggle — monthly only for v1
- ❌ Team/Enterprise tier — Free + Pro only; revisit on inbound enterprise interest
- ❌ Logged-in state detection on landing — page stays static; no "Open app" CTA swap
- ❌ Usage dashboard / project counter UI — belongs in the Specview app, not the marketing page
- ❌ A/B testing infrastructure for CTA copy — ship one version first

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Stripe Pro Product Setup** | None | — | 0.5 days | High |
| 2 | **Hero Dual-CTA Block** | None | with #1, #3 | 1 day | High |
| 3 | **Pricing Section (Free + Pro Cards)** | None | with #1, #2 | 1.5 days | High |
| 4 | **Wire CTAs to Live URLs** | #1, #2, #3 | — | 0.5 days | High |
| 5 | **Responsive + Cross-Browser QA** | #4 | — | 0.5 days | Low |

## Success Criteria

- ✅ Hero displays two CTAs: "Try it free" links to deployed Specview auth URL; "Self-host" smooth-scrolls to existing self-host section
- ✅ Pricing section renders two tiers — Free (3 projects/month) and Pro ($29/month) — using Newspaper Design System tokens (no shadows, no border-radius beyond 2px tags)
- ✅ Pro CTA opens Stripe-hosted checkout for the $29/month product in a new tab or same window per Stripe convention
- ✅ All new typography uses the three-font stack (Playfair Display, Source Serif 4, Source Sans 3) with correct roles
- ✅ Section structure uses border-driven hierarchy (3px ink for major breaks, 1px border for content dividers)
- ✅ Page remains static HTML — no auth-state detection, no client-side routing added
- ✅ Layout holds at mobile (≤640px), tablet, and desktop breakpoints without horizontal scroll
- ✅ Lighthouse performance score does not regress from current baseline

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking