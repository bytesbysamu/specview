# 🔍 Landing Page — Analysis

## The Problem
Landing page only offers self-host, with no path for visitors who want hosted sign-up. Adding a hosted option above self-host: hero gets two CTAs ("Try it free" → Specview auth, "Self-host" → scroll), plus a pricing section (Free 3 projects/month, Pro $29/mo via Stripe).

## Hard Constraints
- Newspaper Design System tokens are canonical — no shadows, no radius (except 2px pill tags), three-font stack required
- Pro tier price fixed at $29/month
- Free tier limit fixed at 3 projects/month
- "Try it free" must link to deployed Specview auth page (URL TBD)
- Stripe checkout link is the payment path (not a custom billing page)

## Open Questions
- **Specview auth URL?** — production subdomain / external app URL / placeholder until deploy
- **Stripe product ID for $29/mo?** — needs to be created or located before checkout link works
- **Where does signup/login live?** — existing Specview app route / new route on this landing / handled entirely by Specview side
- **What does "3 projects/month" meter?** — projects created / specs generated / resets monthly vs lifetime cap
- **Pricing section placement?** — between hero and self-host / below self-host / its own nav anchor
- **Logged-in state on landing?** — does the page detect auth and swap CTA to "Open app", or stay static
- **Annual pricing tier?** — brain dump says monthly only; confirm no annual discount needed for v1

## Dependencies & Sequencing
- Stripe product creation blocks the Pro CTA wiring
- Specview auth route must exist and be deployable before "Try it free" links anywhere real
- Pricing section copy depends on confirming what the project meter actually counts
- Design tokens (already canonical) block nothing — reuse as-is

## Explicitly Out of Scope
- Custom billing/account page on landing — Stripe checkout handles it; trigger to re-scope = need for plan changes/cancellation UI
- Team/Enterprise tier — only Free + Pro for v1; trigger = inbound enterprise interest
- Annual pricing toggle — monthly only; trigger = conversion data showing demand
- In-page auth forms — auth lives in Specview app, landing just links out; trigger = Specview auth not ready by ship date
- Usage dashboard / project counter UI on landing — belongs in Specview app
- A/B testing infrastructure for CTA copy — ship one version first