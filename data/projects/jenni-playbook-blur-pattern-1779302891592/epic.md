# 🎯 Epic: Jenni Playbook Blur Pattern

## Business Value

Jenni AI proved the economics: $10M ARR, 8 people, bootstrapped, by nailing one niche and one conversion mechanic. The mechanic is suspension-based — show partial value, blur the rest, let psychological tension do the selling. Jenni blurred citations; Specview blurs the spec suite. A visitor pastes a brain dump, gets a real analysis in under a minute, then sees four more documents (epic, architecture, timeline, implementation guide) with visible titles and section headers but blurred content. The value is proven. The itch is created. The paywall converts.

This epic exists because Specview currently has no conversion funnel. Every visitor gets everything or nothing. The blur pattern creates a free tier (analysis only) and a pro tier (full five-document suite) with a psychological bridge between them. Jenni iterated conversion from 1% to 4% before spending a dollar on marketing. Specview must hit 3% anonymous-analyze → signup before burning the Show HN channel. This epic builds the infrastructure to create, measure, and optimize that funnel.

The moat Jenni lacked is the reason this is worth building at all. Jenni was inline autocomplete — a GPT wrapper anyone could replicate once ChatGPT shipped. Specview's value is a multi-document pipeline where each spec builds on the previous with compounding context. Copying one document generator is trivial. Copying an interconnected five-doc pipeline with codebase context injection and a correction loop is architecture, not a feature. The blur pattern monetizes that architecture by letting the free tier prove the pipeline works — the analysis references the epic, the epic references the architecture — and the blurred cross-references make the interconnection visible without being readable.

## Scope

### What This Epic Covers

- **Anonymous analysis generation** — No-auth brain dump → analysis document; the free tier hook that proves instant time-to-value
- **Blur-wall document preview** — Visible section headers with blurred content for epic, architecture, timeline, and implementation guide; the suspension trigger
- **Conversion analytics** — Anonymous session tracking from first pageview through analyze → signup → payment; the 3% measurement gate
- **Auth and payment integration** — Signup flow and Stripe checkout that sits between the blur wall and the full spec suite; the monetization layer
- **Pro tier unlock delivery** — Post-payment reveal of the full five-document spec suite; the payoff that justifies the purchase

### What This Epic Does NOT Cover

- ❌ **Show HN launch** — Gated behind 3% conversion proof; re-scope when metric is hit
- ❌ **Content marketing and SEO** — Conversion before virality; Jenni's sequencing applies here
- ❌ **Codebase context injection buildout** — The moat narrative, but separate architectural work; does not block the blur funnel
- ❌ **Multi-tenant teams or collaboration** — Solo users only until pricing is validated
- ❌ **Mobile or Telegram spec delivery** — Different surface, different UX; after web converts
- ❌ **Non-engineering spec types** — No Life OS, no business plans, no weekly reviews; engineering specs only until $5K MRR

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Anonymous Analysis Hook** — No-auth brain dump submission that generates and displays the analysis document; proves time-to-value in under 60 seconds | None | — | 3 days | High |
| 2 | **Blur-Wall Spec Preview** — Render section headers and structure for the four locked document types with blurred content; upgrade CTA per document | Task 1 | ∥ with Task 3 | 3 days | High |
| 3 | **Conversion Analytics Pipeline** — Anonymous session ID, event tracking (land → analyze → view-blur → signup → pay), and a dashboard to read the funnel before Show HN | None | ∥ with Task 2 | 2 days | High |
| 4 | **Auth + Stripe Payment Gate** — Signup flow and Stripe Checkout integration; converts blur-wall CTA into paid access; resolves auth-before-or-during-blur decision | Tasks 2, 3 | — | 3 days | High |
| 5 | **Pro Unlock and Full Suite Delivery** — Post-payment generation (or reveal) of epic, architecture, timeline, and implementation guide; resolves generate-vs-fake architectural decision | Task 4 | — | 2 days | High |

## Success Criteria

- ✅ Anonymous visitor submits a brain dump and receives a rendered analysis document with no authentication required
- ✅ Four locked document types display visible titles and section headers with blurred body content on the same results page
- ✅ Anonymous-analyze → signup conversion rate is measurable end-to-end with no manual data assembly
- ✅ 3% anonymous-analyze → signup conversion rate achieved (gate for Show HN)
- ✅ Stripe payment completes and full five-document spec suite is accessible within one interaction
- ✅ Token cost per free-tier analysis generation is measured and documented — sustainable at 100+ free runs/day
- ✅ Engineering specs only — no non-engineering spec type is reachable from any UI surface

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design for blur wall, auth, payments, and generation strategy
- [Timeline](./timeline.md) — Status tracking and delivery sequence