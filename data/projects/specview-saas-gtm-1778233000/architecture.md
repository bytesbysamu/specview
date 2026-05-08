# 🏗️ Solution Architecture: Specview SaaS Go-to-Market

## Architecture Overview

This is a go-to-market epic, not a greenfield build. The architecture leans on systems already shipping in specview (chain adapter, async 202 polling, JWT auth, projects CRUD) and adds three thin slices: a **monetisation gate** (Stripe + `@check_usage_limit`), a **reliability envelope** around the existing async generator (timeouts, structured errors, retry caps), and an **observability layer** (funnel events + email capture) that converts launch-day traffic into queryable signal.

The mental model is a **funnel pipeline** where each stage is independently instrumented and independently fail-safe. Landing visit → email captured (or signup) → first spec generated → free limit hit → Pro conversion. Each transition is a measurable event; each downstream stage assumes the upstream stage may have failed and degrades gracefully. The Show HN post is treated as a **traffic shock event**, not a feature — the architecture's job is to absorb a 100-concurrent-user burst without producing the stuck-spinner first impression that kills HN posts.

The key insight is that almost nothing here is new code. Stripe is a Flask blueprint behind the existing JWT auth. Usage enforcement is a decorator on existing routes. Reliability hardening is timeout and error-envelope work on the existing `bootstrap.py` chain. Analytics is event emission from existing handlers. The launch package itself is content, not code. Treating GTM as a thin instrumentation layer over a working product — rather than a rebuild — is what makes a one-week launch tractable for a solo founder.

## Design Principles

| Principle | Application |
|-----------|-------------|
| **P1 — Adapter Boundary** | Stripe access lives in a single `modules/billing/adapter.py`. Routes never import `stripe` directly. Same pattern as the chain adapter. |
| **P2 — Thin HTTP Layer** | Stripe webhook, checkout-session, and usage-status routes validate input, call billing service, return JSON. No business logic in routes. |
| **P3 — Async 202 + Polling** | Already in place for spec generation. Reliability hardening adds timeouts and a structured error envelope to the existing `snapshot()` contract — does not change the contract shape. |
| **P4 — No Speculative Abstractions** | One Stripe price, one decorator, one funnel dashboard. No generic "billing provider" interface. No event bus — analytics writes go directly to a single sink. |
| **P5 — OpenAPI-First** | New billing and analytics routes added to `openapi.yaml` first; DTOs regenerate from the contract. |
| **P7 — File Size & Structure** | Billing module split into `adapter.py`, `service.py`, `routes.py`, `decorator.py` — each under 200 lines. |
| **Reuse over rewrite** | The launch surface is built almost entirely from existing modules. New code is the gate, not the engine. |
| **Fail visible, not silent** | Every long-running call returns either a success envelope or a structured error envelope with a code. No raw 500s, no indefinite spinners. |

## Component Design

### Billing Module (`modules/billing/`)
**Purpose**: Convert the landing page's pricing section from aspirational to live. Owns Stripe Checkout session creation, the webhook that flips a user to Pro on `checkout.session.completed`, and the `@check_usage_limit` decorator that gates the spec-generation route at the free-tier ceiling.

**Why a dedicated module**: Stripe is a distinct external service with its own failure modes (webhook signature verification, idempotency, replay). Isolating it behind an adapter means the rest of the codebase reasons about "is this user Pro?" without knowing Stripe exists. If we ever swap Stripe for Paddle or Lemon Squeezy, only `adapter.py` changes.

**Why a decorator, not inline checks**: The free-tier ceiling applies to exactly one operation today (spec generation). A decorator keeps the gate one line at the route layer, lets the route stay thin, and makes the policy auditable in one place. Inline checks would scatter the same logic across handlers.

### Reliability Envelope (existing chain, hardened)
**Purpose**: Make the existing `workflows/spec_gen/bootstrap.py` chain safe to expose to a Show HN traffic spike. Adds three things: a per-step timeout, a structured error envelope returned from `snapshot()` when a job fails, and a max-retries cap on the frontend polling loop so a stuck job surfaces as a visible error rather than an infinite spinner.

**Why hardening, not rewriting**: The chain works. The 4-step bootstrap shipped 36 projects. The risk surface under launch-day load is unbounded latency and unhandled exceptions inside the worker thread, both of which manifest the same way to the user — a spinner that never resolves. A timeout per step plus a try/except that writes `{ done: true, error: { code, message } }` into the job dict closes both gaps without touching the chain logic.

**Why the error envelope is structured, not free-text**: The frontend needs to distinguish "retry might help" from "this will always fail" from "you hit your free tier limit." A `code` field (e.g. `chain_timeout`, `provider_error`, `quota_exceeded`) lets the UI render the right message and the right CTA. Free-text errors force the UI to string-match, which always rots.

### Funnel Analytics (`modules/analytics/`)
**Purpose**: Emit a small fixed set of events — `landing_view`, `signup`, `first_spec_generated`, `free_limit_hit`, `pro_conversion` — to a queryable sink so the post-launch funnel dashboard exists at all. Without this layer, we ship blind.

**Why a fixed event set, not a generic tracking abstraction**: P4. We need exactly five questions answered. Five named events with typed payloads is faster to build, faster to query, and impossible to misuse than a generic `track(event, props)` API.

**Why server-side, not client-side**: Three of the five events (`first_spec_generated`, `free_limit_hit`, `pro_conversion`) are state transitions the server already observes. Emitting them server-side from the same handler that performs the transition guarantees they fire. Client-side analytics drops events on ad blockers, slow networks, and tab closes.

**Sink choice**: A single append-only events table (or JSONL file in `data/`) is sufficient for the launch-week scale. No analytics SaaS dependency for week one — querying the funnel is a pandas notebook on the events log. Upgrade only if data volume forces it.

### Email Capture (landing page)
**Purpose**: Convert non-signup landing visitors into a list we can re-engage. The Show HN spike will produce a long tail of curious-but-not-ready visitors; without capture, that tail is lost.

**Why on the landing page, not the app**: Capturing email from someone who already signed up is redundant. The capture target is bounce traffic — visitors who looked, didn't convert, and would otherwise be unreachable. The form lives on `landing/`, posts to a single Flask endpoint that appends to a list.

**Why minimal, not a full waitlist product**: One field (email), one endpoint, one list. No double opt-in flow, no segmentation, no broadcast tooling. The list is an asset for a future hand-rolled email; building broadcast infrastructure before we have anything to broadcast is P4 violation.

### Show HN Launch Package (content)
**Purpose**: A pre-staged set of artifacts — post title, post body, demo URL, screenshots of the five-document output, the "0 human code lines" framing with its precise qualifications — so the launch is a publish action, not an authoring session under stress.

**Why pre-staged**: The post is the highest-leverage single event in this epic. Composing it in real time during a live launch invites typos, wrong claims, and weak titles. Pre-staging means the launch-day decision is "post now or wait" — not "what should the post say."

**Why the framing is part of the architecture**: The "0 human code lines" claim will be interrogated in HN comments. The framing must be precise enough to survive scrutiny ("the product logic is AI-generated from AI-written specs; the AI was prompted by a human") without burying the lede. Getting this wrong turns the headline into a liability.

### Secondary Amplification (r/SideProject + X relay)
**Purpose**: Pre-staged crosspost content ready to publish once HN traction is observed. r/SideProject post leads with the problem, not the product. X content shares process artifacts (the five documents, the architecture spec the tool wrote for itself) rather than announcing.

**Why dependent on the HN launch, not parallel**: Cross-posting before HN traction is observed risks burning channels on a flat launch. Crossposting after HN momentum amplifies a known signal. The dependency is sequencing, not technology.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Billing provider | Stripe Checkout (hosted) | Hosted Checkout removes PCI scope, handles 3DS/SCA, and ships with one Flask blueprint. Custom checkout UI is unjustified pre-revenue. |
| Webhook handling | Flask blueprint + signature verification | Standard pattern. Idempotency via Stripe's event ID stored in `data/`. |
| Usage gate | Python decorator (`@check_usage_limit`) | One-line gate at the route layer. Reads user tier and current-period count, raises `QuotaExceededError` mapped to 402 with structured envelope. |
| Reliability | Inline timeouts + structured error envelope | Matches existing async 202 contract. No new framework. |
| Analytics sink | Append-only events log (`data/events.jsonl`) | Sufficient for launch-week volume. Queryable with pandas. P4 — no analytics SaaS until volume forces it. |
| Funnel dashboard | Static HTML rendered from the events log | No live BI tool. A daily-regenerated page is enough to read the funnel for week one. |
| Email capture | Flask endpoint + flat-file list (`data/leads.csv`) | Minimal, reversible. Migrate to a real ESP only when there's outbound to send. |
| Distribution | Show HN (primary) → r/SideProject + X (secondary) | Ranked by expected yield for a zero-audience founder. Product Hunt deferred — gated on post-launch onboarding polish. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Ship monetisation, reliability, analytics in parallel before launch | All three are launch gates. Serialising them adds calendar days without reducing risk. They touch different modules and don't conflict. | Three concurrent workstreams in one head — solo cognitive load. Mitigated by each being a thin slice over existing code. |
| Hosted Stripe Checkout, not embedded | Removes PCI scope, fastest path to a real payment. | Less control over the checkout UX. Acceptable — first $29 matters more than checkout polish. |
| Webhook-driven Pro flip, not redirect-driven | Webhook is the authoritative signal Stripe sends. Redirect URL can be tampered with or missed if the user closes the tab. | Requires a publicly reachable webhook URL and signature verification. One-time setup cost. |
| Server-side analytics events, not a client SDK | Three of five events are server-observed state transitions. Server-side guarantees delivery. | Loses client-only signal (scroll depth, time-on-page). Acceptable for a funnel dashboard; out of scope for week one. |
| Append-only JSONL events log instead of Postgres or an analytics SaaS | Launch-week volume is small. A flat file is queryable, debuggable, and zero-dependency. Aligns with "no Postgres" constraint. | Doesn't scale past tens of thousands of events. Acceptable — we'll know if we need to upgrade. |
| Structured error envelope on `snapshot()`, not raw exceptions | Frontend can render specific copy and CTAs per error code. Surfaces failure visibly instead of as a stuck spinner. | Adds a small contract surface to maintain. Worth it — stuck spinners are a fatal HN first impression. |
| Defer no-auth playground, $99 team tier, $9 one-time pack | All three are product changes responding to data we don't yet have. Pre-launch, they're guesses. Post-launch, free→paid conversion data will tell us which (if any) to build. | Possibly leaves activation friction (signup required) on the table for week one. Accepted — measure first. |
| Defer Product Hunt | PH audience skews non-developer; launch quality bar is higher; onboarding polish is the gate. Lower expected yield than HN for the launch-week effort. | Misses a structured launch-day event. Re-runnable later when onboarding is polished. |
| Single primary distribution event (Show HN), secondary channels gated on traction | A scattered launch across five channels at once dilutes signal and saturates none. HN-first concentrates traction; other channels amplify a known win. | If HN flops, the secondary channels still need to fire — but now without momentum. Mitigated by having r/SideProject and X content pre-staged regardless. |
| Pre-stage the launch post and the "0 human code lines" framing as architecture artifacts | The post is the highest-leverage single deliverable in this epic. Treating it as content-on-the-day invites failure under stress. The framing's precision determines whether the headline survives scrutiny. | Time spent before launch on copy. Trade is favorable — the post is the product's first impression on its target audience. |
| Free-tier limit enforced at 3 projects/month for launch; revisit post-launch | Matches what the landing page already promises. Changing it pre-launch creates a copy/code mismatch under time pressure. Conversion data will inform the right number. | The right number is unknown. Accepted — picking the wrong number is recoverable; shipping with the landing page lying is not. |
| Retention model is intentionally unresolved | Cannot reason about retention without live data. Building retention features pre-launch is speculation. | First-month churn risk is unmitigated. Acceptable — the alternative is launch delay for a guess. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking