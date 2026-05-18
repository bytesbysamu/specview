# 🔍 SaaS Phase 2b: Billing UI & Stripe Activation — Analysis

## The Problem
Stripe billing backend is complete (checkout, webhooks, usage limits, portal) but entirely unreachable — no credentials configured, zero Angular UI to trigger checkout or handle the 429→upgrade funnel. Users hit free-tier walls with no way to pay.

## Hard Constraints
- Backend billing code is mostly frozen — three changes needed: (1) `verify-session` endpoint for post-checkout race condition, (2) `lapsed` plan state in webhook handler + OpenAPI enum, (3) `X-Usage-Remaining` header in usage decorator
- `User.plan` written ONLY by webhook handlers (test-enforced boundary)
- No custom payment forms — Stripe Checkout and Customer Portal handle all PCI-scoped surfaces
- 146 frontend tests must not regress; new services need co-located `.spec.ts` + `.mock.ts`
- Depends on Phase 2a isolation (billing status is per-user)

## Open Questions
- **Post-checkout race condition**: User returns from Stripe before webhook fires → sees "Free plan." Use `?session_id=` param for immediate verification, or poll, or go optimistic?
- **Plan model**: `'free'|'pro'` can't distinguish "never paid" from "payment failed." Add `'lapsed'`? This ripples into interceptor logic, upgrade page copy, and SubscriptionService types. Decide first.
- **Usage meter data source**: 429-body-only is a non-starter (data arrives after you're blocked). Dedicated endpoint adds requests; `X-Usage-Remaining` response header piggybacks existing traffic but needs interceptor extraction. Pick one.
- **429 interceptor location**: Extending `auth.interceptor.ts` mixes three unrelated concerns. Separate `billing.interceptor.ts` is cleaner and independently testable — but is the extra file worth it at this scale?

## Dependencies & Sequencing
- Stripe account + env vars unblock everything — must be first (config, not code)
- `lapsed` state decision must precede SubscriptionService, interceptor, and upgrade page (type model flows downstream)
- SubscriptionService must exist before upgrade page or usage meter can consume plan state
- Usage header approach requires backend decorator change before frontend interceptor can read it
- Post-checkout `session_id` verification requires a new backend code path — contradicts "no new backend code" framing

## Explicitly Out of Scope
- **Soft wall / 80% warning** — UX nicety, not launch-blocking; revisit after first conversion data
- **Inline upgrade modal** (vs full-page `/upgrade`) — better UX but doubles the surface area; scope to post-launch
- **Revenue metrics endpoint** — want it week one, but it's admin tooling, not user-facing billing
- **Checkout-without-auth** (Trendfy pattern) — explicitly deferred; design SubscriptionService to not preclude it
- **Cancellation feedback** — Stripe portal config, zero code, but not in the critical path
- **`stripe listen` as docker-compose sidecar** — dev ergonomics, not shipping software

---

> **Cross-references**: → [Solution Architecture](./architecture.md) for signal-based state design, interceptor separation, and session_id verification pattern. → [Epic](./epic.md) for success criteria and business justification. → Implementation guides for step-by-step build instructions.