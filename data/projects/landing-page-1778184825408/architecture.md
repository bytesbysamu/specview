# 🏗️ Solution Architecture: Landing Page

## Architecture Overview

The landing page is a **static HTML artifact** served from `landing/` via an nginx:alpine container. This epic preserves that posture: no build step, no client-side router, no auth detection, no API calls. The page links out to two external systems — the deployed Specview app for auth, and Stripe-hosted checkout for billing — and otherwise remains a flat document. This is the architecture's most important property: marketing speed (edit HTML, redeploy) stays uncompromised by the introduction of a paid tier.

The mental model is **a newspaper with two outbound links**. The hero reads like a front-page lede with two CTAs that hand the visitor off — "Try it free" to Specview's signup URL, "Self-host" to an in-page anchor. The pricing section is a two-column editorial block that uses Newspaper Design System tokens (border-driven hierarchy, three-font stack, no shadows, no radius) to render Free and Pro side by side; the Pro CTA is a plain anchor pointing at a Stripe-hosted checkout URL. There is no billing logic, no signup form, no session state on the marketing surface.

The boundary discipline is deliberate: the landing page never knows whether a visitor is logged in, never holds a Stripe key, never proxies a payment, never reads or writes user data. Authentication lives in the Specview app. Billing lives in Stripe. The marketing page's only job is to convert attention into a click on one of those two URLs.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | Stripe and Specview auth are external services accessed only through outbound URLs configured at build/edit time. The landing page never imports a Stripe SDK, never calls Stripe's API, never embeds an auth widget. |
| P2 — Thin HTTP Layer | nginx serves static HTML — no handlers, no middleware, no rewrites for auth. All "logic" is anchor `href` values pointing at the two external systems. |
| P4 — No Speculative Abstractions | Two pricing tiers means two card elements, not a `pricing-tier` partial system. One Pro CTA means one Stripe link, not a product catalog or env-driven price registry. Three CTAs across hero and pricing means three anchors, not a CTA component. |
| P7 — File Size & Structure | New sections appended into existing `landing/index.html` (or its current shape); no new files unless the existing file would breach the size target. CSS additions extend the already-loaded design tokens — no new stylesheets. |
| Newspaper Design System adherence | All new typography uses the three-font stack with assigned roles (Playfair for tier names and prices, Source Serif for descriptions, Source Sans for labels and feature lists). All hierarchy is border-driven (3px ink for the section break, 1px border between cards, no shadows, no radius beyond 2px on pill tags). |
| Static-first conversion surface | The page stays cacheable, indexable, and instant. No JS bundle weight added for the new sections. Smooth scroll for the "Self-host" anchor uses native CSS `scroll-behavior`, not a script. |

## Component Design

### Hero Dual-CTA Block
**Purpose**: Replace the single existing hero affordance with a two-button row that splits the audience by intent. The primary CTA ("Try it free") routes warm traffic to Specview signup. The secondary CTA ("Self-host") preserves the existing self-host audience by anchoring to the section already on the page.

**Composition**: An overline label, a Playfair headline, a Source Serif sub-paragraph, and a horizontal CTA row containing two anchors. The primary anchor is filled-ink with cream text; the secondary anchor is bordered with no fill. Both are square (no border-radius) per system rules. The CTAs sit inside the existing hero/lede grid (`1fr 1px 340px`) without restructuring the grid — they replace the current single-CTA slot.

**Boundary**: This component owns layout and copy only. The destination URL for "Try it free" is a single config-time string (the deployed Specview auth URL); the "Self-host" target is a same-page hash anchor (`#self-host`) that already exists.

### Pricing Section (Free + Pro Cards)
**Purpose**: Make the value/cost decision obvious in a five-second glance. Two columns, side by side, with clear price anchoring (Free vs $29/month) and a feature list per tier that frames the Free tier as a trial, not a forever-free product.

**Composition**: A section heading label strip (full-width 11px Source Sans uppercase, 1px border-bottom) introduces the section. The body is a two-column grid (`1fr 1fr`) with a single 1px column divider — no card backgrounds, no card borders, no shadows. Each column has: a tier name in Playfair, a price in large Playfair (with `/month` in Source Sans muted), a Source Serif paragraph describing the audience, a Source Sans uppercase feature list, and a CTA at the bottom of the column. Free's CTA mirrors the hero's primary "Try it free" link; Pro's CTA is a Stripe-hosted checkout anchor.

**Boundary**: The component encodes pricing copy and structure. It does not know how Stripe checkout works — only that the Pro CTA is an anchor with an external `href`. Changing the Stripe price ID is a one-line edit to that `href`.

### CTA Routing Layer
**Purpose**: Centralise the three external link targets in one place so they are easy to find and update. There are exactly three: hero "Try it free" → Specview auth, pricing Free CTA → Specview auth (same URL), pricing Pro CTA → Stripe checkout.

**Composition**: A small block at the top of the HTML file (or in a `<head>` data layer / commented config block) that documents the three URLs in one place. In practice this is plain anchor `href` attributes — there is no abstraction layer, no `data-cta` registry. The "centralisation" is editorial: same URL appears in two anchors and a comment marks where to update both. Three concrete strings beats a config system for one consumer.

**Boundary**: This is not a component in the technical sense. It is a maintenance convention. The trade-off is accepted: if the auth URL changes, two `href` attributes get edited; this is cheaper than introducing templating.

### Stripe Product (External, Configuration-Only)
**Purpose**: Hosts the entire payment flow so the landing page never touches money. The product is created once in the Stripe dashboard and produces a hosted checkout URL that lives in a single anchor.

**Composition**: A Stripe product called "Specview Pro" with a recurring $29/month price. Stripe-hosted checkout is enabled. The output of setup is one URL string. No webhook is needed for v1 because the landing page does not need to know about successful payments — provisioning happens in the Specview app on the auth side, downstream of this epic.

**Boundary**: Stripe owns checkout, payment method capture, receipts, tax handling, and subscription lifecycle. The landing page is a referrer.

### Newspaper Design System Tokens (Reused, Not Extended)
**Purpose**: Ensure the new sections look native to the existing landing page. No new tokens, no new fonts, no new colors.

**Composition**: All new elements pull from the existing CSS custom properties (`--bg`, `--ink`, `--ink-light`, `--ink-muted`, `--border`, `--border-dark`, `--red`, the three font variables). The pricing section uses the existing border-system rules (3px ink for the major section break above pricing, 1px border between the two tier columns, 2px ink under the section label if used). Hover states use the universal `rgba(0,0,0,0.02)` whisper.

**Boundary**: This epic adds zero new tokens. If a new visual need arises (e.g., a "most popular" pill badge), it is implemented with the existing 2px-radius pill pattern from the design system, not a new badge token.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Markup | Static HTML in `landing/` | Already deployed via nginx:alpine. No build step, no JS framework, no SSR. The page is editable, cacheable, indexable — the cheapest possible conversion surface. |
| Styling | Existing CSS with Newspaper Design System tokens | Reuse the loaded stylesheet. New sections add rules that compose existing tokens; no new files, no new fonts. Keeps the page weight unchanged. |
| Serving | nginx:alpine container (existing) | Already in place. Static file serving with no app server needed. |
| Auth handoff | External link to deployed Specview app | Auth UI lives where the user data lives. The landing page does not own session state; linking out keeps the marketing page static and avoids duplicating auth flows. |
| Billing | Stripe-hosted checkout (anchor link) | Stripe owns PCI scope, tax, receipts, and subscription lifecycle. A hosted checkout URL is a single string the landing page references — no SDK, no webhook on the marketing side, no custom billing UI to maintain. |
| Smooth scroll | Native CSS `scroll-behavior: smooth` on `html` (or existing equivalent) | No JS needed for the "Self-host" anchor. Browser-native, accessible, free. |
| Analytics | Whatever is already on the page (none added by this epic) | Out of scope. Conversion measurement can be layered on later via Stripe's checkout session metadata or a downstream Specview event — not this epic. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Link out to Specview auth instead of embedding a signup form | Auth UI belongs with the application that owns the user, not the marketing page. Embedding an auth form would force the static page to take on session state, CSRF handling, and error UI — all of which already exist in Specview. | One extra navigation hop. Mitigated because Specview auth is a single page and the user's intent is already captured by the click. |
| Stripe-hosted checkout via plain anchor (no Stripe.js) | Stripe Checkout handles payment methods, 3DS, tax, receipts, and subscription state with zero code on our side. Embedding Stripe Elements would require a JS bundle, a server-side intent endpoint, and a webhook listener — none of which the landing page architecture should host. | Less visual control over the checkout page. Acceptable: Stripe's hosted page is well-designed and consistent with the minimalist aesthetic. |
| Two tiers only — Free and Pro, monthly only | Match the buyer profile: solo developer or small-team PM making a single-seat decision below approval thresholds. Annual or team tiers add decision friction and require more pricing-page real estate. | We will leave money on the table from users who would have taken annual at a discount. Acceptable for v1; revisit when conversion data exists. |
| Page stays static — no logged-in state detection | Detecting auth state would require either a JS call to a Specview endpoint (introduces a runtime dependency and a latency tax on every page load) or shared cookies (introduces a same-origin constraint). Neither is worth a CTA swap on a marketing page. | A logged-in user lands on "Try it free" instead of "Open app." Acceptable: the click still goes to the right place because Specview's auth handler will recognise their session and route through. |
| No A/B testing infrastructure for v1 | Adding split-testing requires either client-side JS with a flag service or edge-side rendering — both contradict the static-page posture. Ship one version, watch conversion, decide later. | We can't compare CTA copy variants pre-launch. Acceptable: Stripe checkout completion is the conversion signal that matters, and one version with clear copy is better than two versions with no learning loop yet. |
| Pricing copy hard-coded in HTML (no CMS, no JSON config) | One product, two tiers, prices that change rarely. A templating layer or content config would be a speculative abstraction (P4). | Pricing changes require an HTML edit and a redeploy. Acceptable given how rarely pricing moves and how cheap a redeploy is. |
| Reuse existing border-system for the pricing layout — no card chrome | Newspaper Design System forbids shadows and structural radius. Two columns with a 1px divider matches the system's editorial language and avoids introducing a card pattern that doesn't exist elsewhere on the page. | Visual contrast between tiers comes from typography weight and spacing rather than card backgrounds. Intentional — this is the design system's whole posture. |
| "Most popular" or visual emphasis on Pro deferred | The system has a 2px-radius pill pattern available, but flagging Pro before we have any signal that emphasis improves conversion is premature. | Pro and Free read as visually equal weight. Can be added later with the existing pill pattern if needed. |
| No webhook on the landing side for Stripe events | The landing page does not provision accounts, send emails, or update databases. Provisioning belongs in the Specview app and happens via Stripe's webhooks delivered to the Specview backend, not the marketing surface. | Out-of-scope-by-design — this is the right boundary. The Specview-side webhook integration is a separate concern handled outside this epic. |
| Lighthouse performance must not regress | The current page's speed is a conversion asset. Adding fonts, scripts, or large images for the pricing section would erode it. | We accept tighter constraints on what the new sections can contain. The three-font stack is already loaded, so new typography is free; no new assets needed. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking