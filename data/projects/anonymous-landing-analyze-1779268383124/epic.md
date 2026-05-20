# 🎯 Epic: Anonymous Landing Analyze

## Business Value

Specview's current landing page is a brochure. Visitors read *about* structured analysis — what it does, why it matters — and then leave. Conversion depends entirely on copy persuasion, which means every iteration is a guessing game: lead with pain? Lead with features? Lead with testimonials that don't exist yet? The fundamental problem isn't the copy. It's that the visitor never touches the product.

An unauthenticated analysis box changes the economics of the landing page. A visitor pastes their own messy thinking — a startup idea, a feature plan, a half-formed strategy — and gets back a structured analysis in under a minute. Problems surfaced, contradictions caught, scope drawn, open questions listed. This is not a demo of someone else's output. It's *their* thinking, returned to them better than they wrote it. The conversion moment shifts from "do I believe this copy?" to "I just saw this work on my own problem." No SaaS landing page copy can compete with that.

The business case is straightforward: every anonymous analysis that impresses a visitor is a warm lead for the full five-document pipeline. The visitor has already experienced the lowest-risk step. The CTA — "Want the full spec? Epic, architecture, timeline, implementation guide" — lands on someone who already knows the product delivers. This turns the landing page from a funnel leak into a product-led acquisition channel, and it does it with one route, one textarea, and one rate limiter.

## Scope

### What This Epic Covers

- **Public analysis endpoint** — Single unauthenticated Flask route that runs only the analysis step of the existing pipeline against a visitor's brain dump
- **IP-based rate limiting** — In-process rate limiter (3 requests/day/IP) to cap AI cost exposure before the route goes live
- **Landing page analyze box** — Static HTML textarea + vanilla JS on the existing landing page; no Angular, no SPA routing
- **Conversion CTA after analysis** — Post-analysis prompt that directs the visitor toward signup and the full spec pipeline
- **Input boundary enforcement** — Character cap on brain dump input to bound token cost per anonymous request

### What This Epic Does NOT Cover

- ❌ **Full five-document generation for anonymous users** — Brain dump explicitly scopes this to one call, one document; revisit only if free-tier conversion data demands it
- ❌ **Angular integration or SPA routing** — Static page; pulling it into the Angular build adds complexity for zero user benefit
- ❌ **Email capture before analysis** — Zero-friction is the thesis; adding a gate before the result kills the experiment
- ❌ **Streaming / SSE response** — Adds complexity to a vanilla-JS page; revisit only if user testing shows abandonment during the wait
- ❌ **Authentication or signup flow buildout** — If auth doesn't exist yet, the CTA links to a placeholder or waitlist; building auth is a separate epic
- ❌ **Prompt iteration for the analysis step** — The existing pipeline's analysis prompt must already work reliably; this epic exposes it, not improves it

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **IP Rate Limiter Module** | None | — | 0.5 days | High |
| 2 | **Public Analysis Endpoint** | Task 1 | — | 1 day | High |
| 3 | **Landing Page Analyze Box** | Task 2 | — | 1.5 days | High |
| 4 | **Conversion CTA & Signup Handoff** | Task 3 | — | 0.5 days | High |
| 5 | **Input Guardrails & Abuse Hardening** | Task 2 | Parallel with 3, 4 | 0.5 days | Low |

## Success Criteria

- ✅ A visitor with no account can paste text and receive a structured analysis without signing up
- ✅ Rate limiter rejects the 4th request from the same IP within a 24-hour window with a clear message
- ✅ Brain dump input is capped at a defined character limit; oversized input is rejected before reaching the AI adapter
- ✅ Analysis response renders as formatted HTML below the textarea within 60 seconds of submission
- ✅ Post-analysis CTA is visible immediately after every successful analysis and links to a functioning next step (signup or waitlist)
- ✅ An unprotected `/api/public/analyze` endpoint never exists in production — rate limiter ships before or with the route

## Related Documents

- [Analysis](./analysis.md) — Problems, constraints, and open questions driving this epic
- [Solution Architecture](./architecture.md) — System design and technical decisions
- [Timeline](./timeline.md) — Status tracking and delivery sequence