Compiled May 4, 2026 from full multi-agent sweep of all claude-ai memory, spec-doc, bubls, constellation, and Projects directories.

**Why:** Sam asked for a deep-read across everything so future agents have full context.
**How to apply:** Reference this for full project context; verify current state via git/files before acting on specifics.

---

## TIMELINE

### 2020–2024: Learning & Templates
- Angular + Ionic mobile development (selfLearning, ng-bubls experiments)
- Springular: Spring Boot + Angular full-stack boilerplate — first template-first project
- howDays: iOS + web app, production-proven, exports 5 infrastructure patterns still used today (Capacitor base service, ErrorParserService, RevenueCat, SQLite layer, Live Updates)
- Early event discovery app experiment (put on hold — PMF not found, lessons fed into Bubls)

### 2025
- **Constellation**: Internal SaaS product factory / boilerplate. Spring Boot (Java 21) + Angular 19 + Ionic 8. Has auth, Stripe, multi-tenant, CI/CD, Docusaurus docs, Claude Code slash commands. Powers humaniz.me. Phase 1 (text ops) and Phase 2 (Speedback Pro) complete.
- **Speedback Pro**: AI-powered feedback collection SaaS for agencies/freelancers. Angular + Flask + PostgreSQL + OpenAI. LIVE.
- **Humaniz.me**: AI text humanizer (humanize, rewrite, polish). Flask + Next.js 15 + Supabase + Stripe. LIVE IN PRODUCTION. Current primary revenue target. Freemium ($5/$12/$25/mo).

### 2026 (Jan–May)
- **Trendfy** (wardrobai.io → glamfit.ai → trendfy.me): AI fashion photoshoot. LoRA pipeline: Claude Vision → remove-bg → IDM-VTON → ESRGAN/CodeFormer. 4-day MVP sprint, 41 commits, 83 images, 3 LoRA models (v3a best: rank 16, all layers, 28 photos, 2000 steps). Co-founder Isabella (50/50, 4-yr vest/1-yr cliff). May 1 kill date (zero paying users = pivot/absorb).
- **Bubls**: Event discovery + social coordination system. Two versions: (a) OpenClaw automation MVP (scrapes zuri.net, moods.ch, email newsletters, first run 19 events, confidence 75-100%, March 4 2026) and (b) Super App (Angular 19 + Ionic 8 + Capacitor 8, 3 features: /humanize, /photoshoot, /picks, deployed iOS TestFlight + web via Coolify).
- **Relationship Wrapped / check-in**: Personal project analyzing Sam/Lea WhatsApp chats via RAG + dual-LLM simulation. Became concept for couples check-in app (10-question self-assessment, both partners submit independently, trend tracking, divergence alerts, local-first SQLite). POC on ionstarter.
- **Spec-Doc**: Documentation-first dev methodology product. Brain Dump → Specs → Claude Code → Working Product. Full SaaS stack built (764+ tests, Flask API 46 endpoints, Stripe, Neon Auth magic-link JWT, SQLite+git-backed storage, observability). ~3-4 days from first paying user per status doc.

---

## PROJECTS IN DETAIL

### spec-doc (~/Projects/2026/spec-doc)
- **Purpose**: IDE for specification-driven development. Specs are the source code; code is derived.
- **Core UX**: Jupyter notebook metaphor — spec blocks that execute independently against Claude Code in Docker (`--dangerously-skip-permissions`), output streams back to browser.
- **Frontend**: Angular 17, Monaco editor, dark theme, SSE streaming
- **Backend**: Flask (4-package modular: ai/, runtime/, data/, quality/), OpenAPI-first, generated DTOs, SQLModel + Alembic, git-backed per-project content (pygit2), Neon Postgres
- **AI**: Anthropic SDK (prod) / Claude CLI (dev) via adapter pattern. Single chain/adapter.py boundary. No feature module imports providers directly.
- **Quality**: Pre-emit linter (9 rules), coherence pass (8 invariants), structured prior-task contracts
- **SaaS**: Stripe Checkout, 6-event webhook, magic-link auth (Neon Auth, RS256 JWT), usage metering (free: 3 bootstraps/20 task-gen/10 spec-gen per day), 202+polling async bootstrap (15-25 min jobs)
- **Status**: 764+ tests, 0 failing. Blocking prod issues: missing <router-outlet>, no environment.prod.ts, repositories not wired in create_app.py, Alembic not auto-run. Fix = ~3-4 days.
- **SaaS pricing**: Free / $5 / $12 / $25 per month

### Bubls super app (~/Projects/bubls)
- **Architecture**: Angular 19 + Ionic 8 + Capacitor 8. Feature = bounded context (lazy-loaded route, own models/service/mock/tests). Module registry via routes. Signals for state. No NgRx. data-test selectors only.
- **Features shipped**: /humanize (text rewriting, 3 modes), /photoshoot (LoRA inference via Replicate), /picks
- **Backend**: Flask + Neon Postgres (pgvector enabled). Magic-link auth (email + UUID). No Supabase/Firebase.
- **Mobile**: TestFlight (iOS) + Coolify (web). GitHub Actions + Fastlane CI.
- **Monetization**: Free tier (10 rewrites/day), Pro ($4.99/mo or $39.99/yr), Stripe Checkout (not IAP)
- **Bubls automation MVP**: OpenClaw-based. Scrapes events from zuri.net, moods.ch, email newsletters. Smart matching. Friend mapping. First run March 4, 2026 — 19 events, 7 people indexed.

### ionstarter (~/Projects/ionstarter)
- Angular + Ionic + SQLite starter template v2.1.3. Proven TestFlight pipeline. Capacitor 8. TanStack Query. Standalone components, OnPush, signals. SQLite with upgrade migrations. Used as foundation for relationship check-in POC and future products.

### howDays (~/Projects/howDays)
- Production iOS + web app. Proven infrastructure. 5 patterns being ported to Bubls: Capacitor Base Service, ErrorParserService, RevenueCat, SQLite layer, Live Updates module.

### Constellation (~/Projects/constellation)
- Internal product factory. Spring Boot (Java 21) + Angular 19 + Ionic 8. Docusaurus docs, Claude Code slash commands, auth, Stripe, multi-tenant, Docker Compose, CI/CD. Powers humaniz.me. Phase 3 in progress: job scheduler, queue processor, OAuth manager — enables ProposalPilot, ContentPilot, OutreachPilot product pipeline.

### clawboi / openclaw (~/Projects/clawboi, ~/Projects/openclaw)
- Sam's personal OpenClaw setup + ClawMemory dashboard. Memory system (25 files, 84 chunks). Max plan with quota management (5-hr rolling bucket, ~65% cost reduction via system prompt override).

### designmcp / mobbin-mcp (~/Projects/tools/designmcp, ~/Projects/mobbin-mcp)
- MCP server for UI inspiration. Python FastMCP, TinyFish/Mobbin API, LLM query parsing via OpenRouter. Claude Desktop integration.

---

## KEY PERSONAL CONTEXT

- Based in Zürich, Switzerland. Solo technical founder.
- Spec Doc is his meta-methodology: everything he builds uses it.
- Working style: brain dump → AI structures → ship. Pushes back on over-engineering. Frontend with mock data first.
- Co-founder Isabella (Trendfy): originator of fashion idea, handles distribution/marketing, Sam handles all tech.
- Sam and Lea: 4-year relationship, separated December 2025, planned meetup May 3, 2026.
- Physical injury affecting activity level (context for energy/capacity).

---

## TECH STACK CONSTANTS

- **Web frontend**: Next.js 15 OR Angular 19 + Tailwind + shadcn/ui (or Ionic 8)
- **Mobile**: Angular 19 + Ionic 8 + Capacitor 8
- **Backend**: Flask (Python) — ~150 line thin layers
- **Auth**: Neon Auth magic-link (JWT RS256) or Supabase (legacy)
- **DB**: Neon Postgres (pgvector enabled) or Supabase (humaniz.me legacy)
- **AI**: Claude API + Replicate (IDM-VTON $0.025/run, Flux LoRA, ESRGAN)
- **Deploy**: Docker Compose → Nginx → Coolify → Traefik, GitHub Actions CI/CD
- **CLAUDE.md rules**: named exports, one component per file, <200 lines per file, one file at a time with build verification

---

## OPEN QUESTIONS (May 4, 2026)

- Trendfy May 1 kill date: did it get paying users? Absorb into Bubls or continue?
- Lea meetup May 3: how did it go?
- humaniz.me: early traction?
- spec-doc: 3-4 day fix sprint — when is Sam starting this?
