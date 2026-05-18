# 🏗️ Solution Architecture: Side Income Strategy

## Architecture Overview

This architecture treats Sam's project portfolio as a system with a single bottleneck: distribution. The system has abundant build capacity — five shipped projects prove that coding, deploying, and maintaining production services is a solved problem. What the system lacks is a reliable funnel that converts strangers into paying customers without ongoing manual effort. Every design decision in this document optimizes for one variable: **time-to-first-dollar per hour of Sam's attention**, not technical elegance or market size.

The core architectural insight is that marketplaces are infrastructure. Chrome Web Store, Shopify App Store, and MCP server registries are not just storefronts — they are search engines, trust engines, and distribution engines that work while Sam sleeps. A product listed in a marketplace with decent keywords and three good reviews will generate impressions indefinitely at zero marginal cost. A product marketed through content creation, SEO, or cold outreach requires ongoing labor that directly competes with the day job. The architecture therefore treats "marketplace-native" as a hard constraint, not a preference.

The system has three phases that execute sequentially: **triage** (free attention by killing or parking projects), **selection** (lock one channel, one product, one price), and **launch** (ship the minimum viable listing and iterate on conversion). Each phase produces a written artifact that constrains the next phase. There is no parallel track, no hedge, and no Plan B running alongside — the entire point is to force focus onto a single revenue path and prove or disprove it before diversifying.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | One product, one marketplace, one revenue model. No "platform" thinking, no multi-channel hedging. Prove distribution works for one thing before building anything else. |
| P1 — Adapter Boundary | The revenue product must be decoupled from Sam's personal infrastructure. If it runs through OpenClaw or spec-doc, those become dependencies a paying customer didn't sign up for. The product ships standalone. |
| P6 — Skills First | Product validation starts as lightweight research (marketplace search, competitor gap analysis) before any build step. Graduate to an MVP only after validation passes. No building to learn — learn first, then build. |
| Distribution-First Design | Every product candidate is evaluated by its distribution channel before its feature set. A mediocre product in a high-discovery channel beats a brilliant product that requires hustle to find customers. |
| Attention Budget Constraint | Sam has roughly 10–15 hours per week of non-day-job time. Architecture must account for this as a hard ceiling on all activities — building, listing optimization, and support combined. |

## Component Design

### Portfolio Triage Engine

**Purpose**: Reclaim cognitive bandwidth and weekly hours before adding any new commitment.

The triage produces exactly one verdict per project: **kill**, **keep-passive**, or **keep-active**. "Keep-passive" means the project stays deployed but receives zero development hours — if it breaks, it stays broken or gets archived. "Keep-active" is reserved for at most two projects: the revenue product and one infrastructure project that directly supports it.

Triage criteria are weighted toward distribution reality, not sunk cost or technical quality:

- **Does this project have a marketplace-native distribution channel today?** If no, it cannot be keep-active.
- **Has this project generated any revenue or inbound interest in the last 90 days?** If no, the default verdict is kill unless maintenance cost is literally zero.
- **Does maintaining this project consume more than 2 hours per week?** If yes and it has no revenue path, it must be killed or moved to passive.

The expected outcome based on the epic's scope: humanize-me moves to passive (deployed, no dev time — it lives in a saturated consumer market with no marketplace distribution), Trendfy is killed (kill date already passed), Bubls moves to passive or killed (consumer mobile app requiring sustained marketing in a local market), and spec-doc stays as internal tooling with zero revenue expectation. This frees the entire weekly attention budget for the revenue product.

### Distribution Channel Selector

**Purpose**: Lock exactly one marketplace before any product ideation begins.

This is the most consequential decision in the entire epic because it constrains the product space. Choosing Chrome Web Store means building browser extensions. Choosing Shopify means building merchant tools. Choosing an MCP registry means building AI developer tools. The channel is chosen first; the product is designed to fit the channel — not the reverse.

Three channels are evaluated against five criteria:

| Criteria | Chrome Web Store | Shopify App Store | MCP Server Registry |
|----------|-----------------|-------------------|---------------------|
| **Review cycle speed** | 1–3 days (automated review for most extensions) | 5–15 business days (manual review, iterative feedback) | Emerging — no formal review for most registries yet |
| **Willingness-to-pay ceiling** | Low ($1–$10/mo typical for productivity extensions) | High ($10–$99/mo; merchants treat apps as business expenses) | Unknown — market is pre-revenue for most listings |
| **Competition density** | Very high in popular categories; long-tail niches exist | High but fragmented; many apps are poorly maintained | Very low — greenfield, but demand is unproven |
| **Discovery mechanism** | Keyword search + category browse + "Featured" editorial | Keyword search + category + Shopify admin recommendations | Registry search; word-of-mouth in developer communities |
| **Stack alignment** | JavaScript/TypeScript (browser APIs) — moderate fit | Typically Node.js or Ruby; Flask possible via embedded app pattern | Python/TypeScript — strong fit with Sam's existing stack |

**Recommended channel: Chrome Web Store** as the primary bet, with MCP registry as a trailing option if the Chrome product validates.

Rationale: Chrome Web Store has the fastest feedback loop (ship → listed → installs within days), the lowest review friction, and a discovery mechanism that rewards keyword optimization over audience building. The WTP ceiling is lower than Shopify, but the time-to-first-dollar is dramatically shorter — and the goal is proving distribution works, not maximizing ARPU on day one. Shopify's 5–15 day review cycle and merchant-specific domain knowledge create friction that slows iteration for a solo dev learning a new channel. MCP registries are too early — the install base is small, monetization norms don't exist yet, and "first-mover" in an unproven market is not an advantage for someone optimizing for income, not influence.

The trade-off is explicit: Sam gives up Shopify's higher price ceiling and MCP's stack alignment in exchange for Chrome's speed-to-market and self-serve discovery. If the Chrome product hits $500/mo, the architecture does not expand to a second channel — it doubles down on the one that works.

### Product Selection Framework

**Purpose**: Filter candidate products through distribution-feasibility criteria before evaluating technical feasibility.

Product candidates are scored on four dimensions, in this priority order:

1. **Search demand signal** — Are people actively searching for this category in the Chrome Web Store? Measurable via autocomplete suggestions, competitor install counts, and review velocity on existing extensions.
2. **Competitor gap** — Do the top 3–5 existing extensions in this niche have obvious quality problems (bad UX, abandoned updates, missing features, low ratings)? A gap means Sam can win on execution without needing a novel idea.
3. **Build complexity relative to attention budget** — Can an MVP ship in ≤5 focused days (roughly one week of side-project time)? If the MVP requires backend infrastructure, persistent storage, or ongoing data pipelines, it fails this filter.
4. **Retention mechanics** — Does the product create a habit or ongoing need, or is it a one-time use? Subscription revenue requires products people use weekly, not once.

Products that require Sam to create content, build an audience, or do outbound sales are rejected regardless of their scores on other dimensions. The framework explicitly excludes "viral-by-output" products unless Sam has already committed to being a visible creator — and the epic scoping confirms he has not.

### Revenue Model Architecture

**Purpose**: Define the pricing and billing structure before building anything.

The revenue model is freemium with a usage gate:

- **Free tier**: Core functionality with a visible but non-annoying limitation (e.g., N uses per day, or basic features only). The free tier must be genuinely useful — it is the top of the funnel and the source of organic reviews.
- **Paid tier**: $5–$15/month, unlocking the limitation. Pricing sits in the impulse-buy range for a professional — low enough that no procurement approval is needed, high enough that 100–300 paying users hit a meaningful income target.
- **Payment processing**: Chrome Web Store's built-in payments API or Stripe via a lightweight backend. The Chrome payments API has lower friction (no redirect, no account creation) but takes a 5% cut on top of Google's 15% store fee. Stripe requires a backend but gives better margins and portability.

Design decision: **Start with Stripe + a minimal Flask backend** rather than Chrome's built-in payments. The 20% combined fee on Chrome payments is aggressive at low revenue, and a Flask backend is trivially deployable using Sam's existing Docker + Coolify pattern. The backend handles license verification only — it is not a feature backend.

### Marketplace Listing as a Product Surface

**Purpose**: Treat the Chrome Web Store listing itself as a designed artifact, not an afterthought.

The listing is the product's entire sales team. It needs to be designed with the same rigor as the product UI:

- **Title**: Keyword-leading, under 45 characters. The primary search term appears in the first three words.
- **Description**: First sentence is the value proposition. Bullet points for features. No jargon. Written for the person searching, not for Sam.
- **Screenshots**: 3–5 annotated screenshots showing the extension in action on a real webpage. Annotations call out the key action, not the UI chrome.
- **Category and tags**: Selected based on where competitors with high install counts are listed, not based on how Sam categorizes the product internally.
- **Rating velocity plan**: The free tier exists partly to generate a volume of installs that produces organic reviews. A polite, non-intrusive review prompt appears after the user has completed their third successful action (not on first use, not on a timer).

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Extension runtime | TypeScript + Chrome Extensions Manifest V3 | Required by Chrome Web Store; Manifest V3 is mandatory for new submissions as of 2024 |
| Extension UI | Vanilla TypeScript or lightweight framework (Preact/Solid) | Extension popups and sidepanels must be tiny; Angular and React are oversized for this context |
| License backend | Flask (Python) | Sam's strongest backend stack; thin layer pattern from humanize-me; handles Stripe webhooks and license checks only |
| Payment processing | Stripe Checkout + Customer Portal | Better margin than Chrome payments API; portable if Sam later sells outside Chrome Web Store; Sam controls the billing relationship |
| Deploy | Docker Compose → Coolify | Existing deployment pattern; single gunicorn worker since license state is in-process |
| Monitoring | Stripe Dashboard + Chrome Web Store Developer Dashboard | No custom analytics needed at launch; both platforms provide install counts, revenue, and conversion metrics |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Kill or park all consumer-marketed projects before starting** | Every hour spent maintaining humanize-me or Bubls is an hour not spent on the one product that has a distribution channel. Sunk cost is not a reason to continue. | Emotional cost of archiving shipped work. Risk that a parked project had untapped potential — mitigated by the 90-day-no-traction test. |
| **Choose the marketplace before the product** | The channel constrains what can be sold. Choosing a product first and then hunting for a channel leads to the same distribution problem Sam already has. | Eliminates products that might be great but don't fit the chosen marketplace. Accepted because distribution feasibility outweighs product brilliance for this goal. |
| **Chrome Web Store over Shopify App Store** | Faster review cycle, lower domain-knowledge barrier, simpler onboarding for a first marketplace product. Sam can ship, learn, and iterate in days, not weeks. | Lower WTP ceiling ($5–$15 vs $20–$99). Accepted because the goal is first paid customer, not maximum revenue per user. Shopify becomes a future option once marketplace selling is a proven skill. |
| **Chrome Web Store over MCP registry** | MCP has better stack alignment but no proven monetization norms and a tiny install base. Betting on an unproven channel when the goal is income is a timing mismatch. | Gives up first-mover advantage in MCP ecosystem. Accepted because first-mover advantage in a market with no buyers is worth nothing. Revisit when MCP registries show $1M+ in third-party revenue. |
| **Freemium with Stripe, not Chrome payments API** | 20% combined fee (Google 15% + Chrome payments 5%) erodes margin at low revenue. Stripe gives 2.9% + $0.30 and lets Sam own the billing relationship. | Adds a backend dependency (Flask license server). Accepted because Sam can deploy a Flask service in hours and the margin difference funds the next product. |
| **No backend features in the MVP extension** | The extension must work entirely client-side for core functionality. The only backend call is license verification. This eliminates infrastructure as a scaling bottleneck and keeps the free tier functional even if the backend is down. | Limits the product to features achievable in-browser. Accepted because the most successful Chrome extensions in the $5–$15 range are client-side productivity tools, not SaaS frontends. |
| **Single product, single channel, no hedging** | Splitting attention across two products or two channels recreates the exact portfolio fragmentation problem this epic exists to solve. | If the chosen product fails, Sam has to start over rather than falling back to a parallel bet. Accepted because a focused failure teaches more about marketplace selling than two half-efforts. |

## Risk Considerations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| **Chosen product niche is too competitive** | Medium | Product selection framework requires competitor gap analysis before commitment. If the top 5 extensions all have 4.5+ stars, 10k+ users, and active maintenance — pick a different niche, not a different channel. |
| **Chrome Web Store changes review policies or fees** | Low | Stripe-based billing means the payment relationship is portable. The extension itself can be distributed outside the store (direct install) as a fallback, though discovery would suffer. |
| **Free tier attracts users who never convert** | High | Expected and acceptable. Free users generate reviews and install count, which improve search ranking, which brings more users including paid converters. A 2–5% free-to-paid conversion rate is the realistic target. |
| **Sam loses motivation after portfolio triage** | Medium | The triage is emotionally hard — killing projects feels like failure. Mitigation: frame triage as a prerequisite for the exciting part (shipping something that makes money), not as the point of the exercise. Do triage and channel selection in the same day. |

## Constraints and Boundaries

- The revenue product must not depend on OpenClaw, spec-doc, or sam-plugin at runtime. These are development tools, not production dependencies for paying customers.
- The license-checking backend must follow P2 (thin HTTP layer) and P3 (if license verification ever becomes slow, which it should not). No business logic in route handlers.
- The product must be shippable to the Chrome Web Store within the 5-day MVP build window defined in the epic. If a product candidate cannot meet this, it fails the selection framework regardless of other scores.
- No multi-product ambitions until the first product reaches $500/mo sustained for two consecutive months. This is the gate for the "different epic" mentioned in the epic scope.

## Related Documents

- [Analysis](./analysis.md) – Problems driving this architecture: distribution bottleneck, portfolio fragmentation, and the attention budget constraint
- [Epic](./epic.md) – Scope, tasks, and success criteria including first paid customer milestone
- [Timeline](./timeline.md) – Status tracking for triage, selection, build, and launch phases