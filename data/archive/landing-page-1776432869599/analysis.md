---
sidebar_position: 1
---

# 🔍 Bubls Landing Page – Analysis

**Purpose**: Surface decisions and constraints before the epic inflates.

**Date**: 2026-04-17

---

## Problem

Bubls has no web presence. Distribution experiments (Reddit, Twitter, DMs) need a clickable URL. Without a landing page, traffic from any post evaporates — there's no way to capture interest, show the product, or link to TestFlight. This is a hard blocker for every distribution channel.

---

## Hard Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Neon Postgres only for email capture | Architecture Principles | No Mailchimp, no Supabase, no third-party email services. One table, one endpoint |
| Coolify on Trendfy VPS | Existing infrastructure | Deployment target is already provisioned. No new servers |
| Ship in < 1 week | Builder profile | Single-page site should ship in 1-2 days, not stretch into a project |
| Three screenshots from TestFlight build | Braindump | Photoshoot result, text rewrite, onboarding — must be captured from the running iOS app |
| No framework magic | Architecture Principles | Static HTML is the correct choice for a single page with no dynamic routing |

---

## Open Questions

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **Domain** | `bubls.app`, `bubls.ch`, repurpose `trendfy.me` | `bubls.app` — cleanest brand match, `.app` signals mobile-native, enforces HTTPS. `bubls.ch` is geo-locked to Swiss perception. Repurposing `trendfy.me` weakens both brands |
| 2 | **One-liner** | Needs to be under 10 words | Builder decides. Candidates: "AI that makes your photos, text, and picks better" / "Three AI tools. One app." / "Your photos. Your words. Upgraded." |
| 3 | **Static HTML vs Next.js** | Static HTML (zero deps, instant deploy) vs Next.js (reusable for future pages) | Static HTML. One page doesn't need a framework. Migration to Next.js is cheap if a second page ever materializes — and per principles, not-yet-built is the right state for infrastructure nobody's asked for |
| 4 | **Screenshot format** | PNG vs WebP vs both | WebP with PNG fallback via `<picture>`. WebP cuts ~30% payload on mobile |

---

## Dependencies

| Dependency | Blocks | Status |
|------------|--------|--------|
| Domain registration + DNS propagation | Everything except screenshot capture | Not started |
| TestFlight build with all 3 features working | Screenshot capture | Assumed live (UX revamp in progress) |
| Neon Postgres access | Email capture endpoint | Available (shared instance, EU Central 1) |
| Coolify VPS | Deployment | Provisioned (Trendfy VPS) |

---

## Explicitly Out of Scope

- Analytics / tracking pixels — add after first distribution experiment, not before
- Blog or content pages — this is one page, not a site
- A/B testing the one-liner — ship one, change it later based on signal
- SEO optimization — the page exists for direct link traffic, not organic search
- Custom email sequences or drip campaigns — capture the email, that's it
- App Store links — TestFlight only until public launch

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

