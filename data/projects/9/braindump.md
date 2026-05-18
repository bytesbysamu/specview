# Constellation — Braindump

## What it is

Constellation is a multi-layer platform with two distinct instantiations across three repos:

1. **`/Users/sam/Projects/constellation/`** — The original monorepo SaaS boilerplate: Spring Boot 3.2 (Java 21) backend + Angular 19 + Ionic 8 + Capacitor 7 frontend. Full-stack: JWT + OAuth2 auth, Stripe payments, SendGrid email, Ollama/LangChain4j AI, PostgreSQL + pgvector. This is the reusable boilerplate that other projects (Bubls, trendfy) fork from.

2. **`/Users/sam/Projects/2026/constellation/`** — The docs/strategy layer. Docusaurus documentation site covering capabilities, strategy, roadmap, and spec-doc patterns. Currently powers the product thinking for humaniz.me and the opportunity intelligence system.

3. **`/Users/sam/Projects/2026/constellation-api/`** — Flask-based API extracted from humanize-me, extended with a provider-agnostic LLM layer and planned Opportunity Intelligence System (Reddit monitoring → scoring → daily reports).

## Problem it solves

**Boilerplate (original constellation):** Eliminates the 2-4 week setup cost for new SaaS products. Spring Boot + Ionic with auth, payments, email, AI, CI/CD, mobile native all pre-wired. Fork → configure → ship.

**Constellation-API / Opportunity Intelligence:** humaniz.me ($195K MRR validated market) has no distribution. People ask about AI detection on Reddit/Twitter daily — the system finds them, scores opportunities, and surfaces actionable leads for manual outreach. The human engages; the system finds and ranks. Automated replies are explicitly prohibited.

**Strategy layer (2026/constellation docs):** Frames Constellation as a "product factory" — shared capabilities that compound across products. Each new capability multiplies the number of launchable products without rebuilding infrastructure. Text Operations → Intelligence (Fetch + Analyze + Report) → Products.

## Current state

**Original boilerplate (`/Users/sam/Projects/constellation/`):**
- 189 commits on the frontend. Full feature set: Angular 19 + Ionic 8 + Capacitor 7, push notifications, RevenueCat, Transloco i18n, @ngneat/elf state, standalone components with OnPush.
- Spring Boot backend: JWT + Google OAuth2, Stripe webhooks + customer portal, SendGrid, Ollama embeddings + RAG, pgvector, Flyway migrations.
- Used as source for Bubls (forked the Capacitor scaffold), trendfy.me (Angular patterns).
- CHANGELOG.md is empty — no versioning discipline.
- iOS: RevenueCat requires `purchases-capacitor` kept updated; iOS target >= 16.0 to avoid `SubscriptionPeriod` ambiguity.

**Constellation-API (`/Users/sam/Projects/2026/constellation-api/`):**
- Foundation layer complete: Flask API, Supabase auth, Stripe, usage tracking, Redis cache, streaming, provider-agnostic LLM (Anthropic/OpenAI/Groq/Ollama switchable via env var).
- Intelligence layer mostly complete: Reddit fetch adapter, Posts table, Analyze (insights extraction works), Report generation works.
- **Broken**: `opportunity_score` always null — scoring is the core value prop and it doesn't work.
- Missing: UI dashboard, shareable report links (the distribution mechanism).
- Phase 5 (Distribution) is the current focus per Roadmap 2.0.

**Strategy docs (`/Users/sam/Projects/2026/constellation/`):**
- Roadmap 2.0 (Feb 2026): Phases 1-4 complete, Phase 5 (Distribution) current, Phase 6 (Validation) next.
- Key metric: $500 MRR by week 8 from launch is the go/no-go gate.
- Critical prerequisite before launch: platform compliance verification (Reddit ToS for commercial use).

## Key decisions made

- **Distribution is architecture**: Products without distribution mechanism don't get built. Every capability needs a distribution answer.
- **Intelligence layer = distribution**: Fetch → Analyze → Report creates shareable outputs. Text Operations alone don't distribute.
- **Manual engagement always**: The system surfaces, the human engages. Automated replies are permanently out of scope.
- **Opportunity score fix before UI**: Core feature must work before spending time on UI.
- **Platform compliance before launch**: Reddit API ToS must be verified before going public. Existential risk if not.
- **LLM provider abstraction**: Switch via `LLM_PROVIDER` env var — no code changes. Factory pattern. Groq for speed/cost in dev.
- **Revenue targets are concrete**: $500 MRR by week 8. Not "let's see what happens."
- **Boilerplate: executor pattern**: Dev work happens inside Docker container via `docker exec`. Never `docker compose down/restart`. (`/Users/sam/Projects/constellation/` likely has this setup per memory notes on Trendfy.)
- **Spec-aware development**: The 2026/constellation docs repo has `.claude/rules/spec-awareness.md` — Claude must read epic/architecture before implementing. Status tracking belongs only in `timeline.md`.
- **Doc structure is strict**: Analysis (problems) → Epic (scope + tasks) → Architecture (design, no code) → Implementation (code patterns). No mixing.

## Open questions

- Is the Reddit API usage compliant for commercial use? This is the launch blocker.
- What's the actual UI for the opportunity dashboard — a new frontend app, or embedded in the existing humanize-me Next.js frontend?
- Are shareable report links public (no auth) or gated? What's the distribution model — send the link to a prospect, embed on a page, something else?
- Does the opportunity intelligence system need its own Stripe product, or does it share humanize-me's subscription?
- Is `/Users/sam/Projects/2026/constellation/` (docs site) actually deployed anywhere, or is it dev-only Docusaurus?
- cbtBuddy inside `/Users/sam/Projects/constellation/` — what's its status? (iOS app for CBT therapy, appears to be a separate product within the monorepo.)

## Next steps

**Immediate (constellation-api):**
1. Verify Reddit API ToS for commercial use — do this first, it's existential
2. Fix `opportunity_score` null bug (1-2 days)
3. Build basic UI dashboard — view opportunities, view reports (3-4 days)
4. Add shareable report links with public access (1-2 days)
5. Launch to validation cohort; target first paying customer within 14 days

**Medium-term:**
6. If $500 MRR by week 8: add Twitter/X adapter, email digest delivery
7. If not: pivot product using same capabilities (Extract, Detect, Summarize use same infrastructure)

**Boilerplate:**
- Keep updating as Bubls and trendfy diverge from it — capture improvements back upstream
- Fix empty CHANGELOG.md if versioning matters for downstream projects
