# 🏗️ Solution Architecture: SaaS Phase 2b — Billing UI & Stripe Activation

## Architecture Overview

Phase 2b is an activation problem, not a build problem. The Stripe billing backend — checkout sessions, webhook handlers for six events, usage limits with daily caps, pro plan bypass — ships as dead code because no credentials are configured and no Angular components exist to surface it. The architecture therefore focuses on three thin integration layers: a signal-based reactive service that bridges backend plan state to the Angular component tree, a dedicated HTTP interceptor that converts raw 429 responses into upgrade navigation, and a single upgrade page that delegates all payment and subscription management surfaces to Stripe-hosted UI. No custom payment forms, no card inputs, no PCI-scoped surfaces touch this codebase.

The key architectural insight is that the most important moment in the entire billing system is not checkout — it is the 429 interruption. A user who just hit their free-tier wall is maximally motivated to pay. The transition from "you're blocked" to "here's how to unblock" must be instant, contextual, and distinguish between three states: never subscribed, actively subscribed, and payment lapsed. This tri-state model — `free`, `pro`, `lapsed` — is the spine that every downstream component reads from. Getting it wrong means showing "Upgrade to Pro" to someone whose card just expired, which is both confusing and insulting.

The second insight is the webhook-redirect race condition. Stripe Checkout redirects the user back to the app before the webhook has necessarily fired. Without mitigation, a user who just paid $29 lands on a page that says "Free plan." The architecture closes this gap with a `session_id` verification pattern: the redirect URL carries the Stripe session identifier, the backend retrieves the session directly from Stripe's API for immediate confirmation, and the webhook remains the canonical write path for `User.plan`. This gives instant UX without sacrificing data integrity.

## Design Principles

| Principle | Application in Phase 2b |
|-----------|------------------------|
| P1 — Adapter Boundary | Stripe calls already isolated in `api/modules/billing/service.py`. No new adapter needed. Frontend billing API calls flow through auto-generated DTOs from OpenAPI codegen — the generated layer is the adapter boundary on the client side. |
| P2 — Thin HTTP Layer | One new backend endpoint: `GET /api/billing/verify-session` for post-checkout race condition mitigation (see Integration Points). The one other backend change (lapsed state) modifies the webhook handler's service call. Additionally, the `@check_usage_limit` decorator needs a one-line change to emit the `X-Usage-Remaining` response header. |
| P3 — Async 202 + Polling | Not applicable — no long-running operations in this phase. Checkout is a redirect, not a background job. Session verification is a synchronous Stripe API call under 500ms. |
| P4 — No Speculative Abstractions | Single plan tier at launch. No tier registry, no pricing engine, no plan comparison framework. The `SubscriptionService` exposes three literal plan states and two actions. Multi-tier support is explicitly deferred. |
| P5 — OpenAPI-First | DTOs already generated. The one new response shape (session verification) must be added to `openapi.yaml` first, then regenerated. The usage header is transport-level, not a DTO concern. |
| P7 — File Size & Structure | Each new frontend artifact is a single file under 200 lines: one service, one interceptor, one page component, one meter component. No barrel files, no shared billing module aggregating unrelated concerns. |

## Component Design

### SubscriptionService (Signal-Based Plan State)

**Purpose**: Single source of truth for the current user's billing state across the entire Angular application. Every component that needs to know "is this user Pro?" reads from this service rather than making its own API call or inspecting local storage.

The service holds a writable signal with three possible values representing the plan lifecycle: never paid, actively subscribed, and payment lapsed. A computed accessor derives the boolean "is Pro" check that most consumers actually need. The service initializes by calling the existing `GET /api/billing/status` endpoint and refreshes after checkout redirect and on app foreground resume.

The critical method is checkout initiation: it calls the backend to create a Stripe Checkout session, receives a URL, and performs a full-page redirect. When the user returns, the redirect URL carries a `session_id` query parameter. The service detects this parameter, calls a verification endpoint that retrieves the session directly from Stripe, and updates plan state immediately — before the webhook has necessarily fired. This closes the race condition window from seconds to zero.

The tri-state model (`free | pro | lapsed`) is deliberately minimal but solves a real UX problem. When `invoice.payment_failed` fires, the backend writes `lapsed` instead of `free`. This lets every downstream consumer — the interceptor, the upgrade page, the usage meter — distinguish "you should upgrade" from "your payment method needs updating." The cost is one additional string value in a union type. The alternative — collapsing lapsed back to free — forces the upgrade page to make a secondary API call to determine which CTA to show, and risks showing "Upgrade to Pro" to someone who is already a subscriber with a billing issue.

### Billing Interceptor (Dedicated, Not Shared)

**Purpose**: Catches 429 responses from usage-limited endpoints and converts them into contextual navigation to the upgrade page. Separate from the auth interceptor.

The existing `auth.interceptor.ts` handles token injection and 401 refresh flows. Adding 429 handling to it would create a god interceptor mixing three unrelated concerns: authentication, token lifecycle, and billing enforcement. A bug in 429 handling could break auth flows. The billing interceptor is a separate file, separately registered in the providers array, and independently testable. The cost is one additional file and one additional provider registration — trivial against the benefit of isolation.

The interceptor reads the 429 response body, which already contains structured data from the `@check_usage_limit` decorator: the feature that was limited, the cap, the reset time, and an upgrade URL. It also reads the plan state from `SubscriptionService` to determine navigation context. For `free` users, navigation goes to the upgrade page with "You've used all N daily generations" messaging. For `lapsed` users, navigation goes to the same page but with "Your payment method needs updating" messaging. For `pro` users, a 429 should never occur — but if it does due to a backend bug, the interceptor logs the anomaly and does not navigate.

A secondary responsibility of this interceptor is passive usage extraction. Every API response that passes through a usage-limited endpoint carries an `X-Usage-Remaining` header (added by the backend decorator). The interceptor reads this header and writes it into a signal on a lightweight usage state holder. This piggybacks usage data on existing traffic with zero additional requests.

### Upgrade Page

**Purpose**: Single conversion surface for free-tier users hitting limits and for existing subscribers managing their billing.

The page renders conditionally based on plan state from `SubscriptionService`. For `free` users: pricing copy, a feature comparison between free and Pro tiers, and a primary CTA button that triggers `startCheckout()`. For `lapsed` users: the same layout but with messaging focused on payment recovery ("Update your payment method to restore Pro access") and a CTA that opens the Stripe Customer Portal rather than initiating a new checkout. For `pro` users who navigate here directly: a confirmation of their active plan and a "Manage subscription" button opening the Customer Portal.

The page also handles the post-checkout return state. When the URL contains a `session_id` parameter, the page shows a brief verification state while the `SubscriptionService` confirms the session with the backend, then transitions to a "Welcome to Pro" confirmation. This is the moment that must feel instant — the session verification call typically completes in under 500ms because it is a direct Stripe API retrieval, not a webhook wait.

All payment UI beyond this page is delegated to Stripe-hosted surfaces. No card input fields, no invoice tables, no cancellation flows exist in this codebase. The Stripe Customer Portal handles payment method updates, plan cancellation, and invoice history. This keeps PCI scope at zero and reduces the component surface area to one page.

### Usage Meter (Passive, Header-Driven)

**Purpose**: Shows remaining daily API calls per feature so users see their limit approaching before they hit the wall.

The meter is a small pill component rendered in a persistent UI location. It reads from a signal populated by the billing interceptor's header extraction. Because the data arrives passively on every API response, the meter updates naturally as the user works — no polling, no dedicated endpoint, no additional network requests. The display shows the remaining count against the daily cap, and the visual treatment shifts to a warning state when remaining calls drop to one or fewer. The entire component is hidden for Pro users since caps do not apply.

The design deliberately avoids a dedicated usage endpoint. Option A (explicit `GET /api/usage/remaining`) would add a request per page load per feature, creating unnecessary load for data that is already computed server-side on every limited request. Option C (429-body-only) would mean the meter only updates after the user is already blocked, defeating its purpose. The header-piggybacking approach is the right balance: zero extra requests, data freshness tied to actual usage, and a one-line backend change to emit the header from the existing `@check_usage_limit` decorator.

### Lapsed Plan State (Backend Webhook Modification)

**Purpose**: Distinguishes "never subscribed" from "payment failed" so the frontend can show the correct recovery action.

Today, `invoice.payment_failed` sets `User.plan = 'free'`, which is indistinguishable from a user who never paid. This creates a silent lockout: a Pro user's card expires, their plan reverts to free, they hit a 429, and the app tells them to "Upgrade to Pro" — but they already are a subscriber with a billing issue. The fix is a one-value change: the webhook handler writes `lapsed` instead of `free` on payment failure. The `@check_usage_limit` decorator already treats any non-`pro` plan as limited, so `lapsed` users are correctly gated without decorator changes. The 0-day grace period (no grace — immediate lockout on payment failure) is a locked decision from Phase 1 that this architecture does not revisit.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend framework | Angular 17 with signals | Already in use. Signals provide reactive plan state propagation without RxJS subscription management overhead. |
| Plan state management | Writable signal + computed accessor | Matches the project's existing signal patterns (no NgRx). Plan state is a single scalar value, not a complex object graph — signals are the right granularity. |
| Payment UI | Stripe Checkout + Stripe Customer Portal | Zero PCI scope. All card handling, payment forms, cancellation, and invoice management are Stripe-hosted. No payment-related DOM in this codebase. |
| Post-checkout verification | Stripe Sessions API (server-side retrieve) | Closes the webhook-redirect race condition without polling. Backend calls `stripe.checkout.sessions.retrieve()` synchronously — sub-500ms response. |
| Usage data transport | HTTP response headers (`X-Usage-Remaining`) | Piggybacks on existing API traffic. Zero additional requests. Backend decorator already computes the value. |
| HTTP interception | Dedicated `billing.interceptor.ts` | Single-responsibility separation from auth. Independently testable. Registered as a separate provider. |
| Backend plan model | String union: `free`, `pro`, `lapsed` | Minimal extension to distinguish payment failure from never-subscribed. No enum class, no tier registry — three literal strings. |
| Local dev billing | Frontend mock service + Stripe test mode for integration | `subscription.service.mock.ts` enables UI development without Stripe. Real test-mode keys used for integration and E2E verification. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Separate billing interceptor instead of extending auth interceptor | Auth interceptor handles token injection and 401 refresh — two concerns already. Adding 429 routing creates a three-concern god interceptor where a billing bug could break auth. Separate file is independently testable and follows single-responsibility. | One additional file and provider registration. Two interceptors in the chain instead of one. Marginal startup cost. |
| Tri-state plan model (`free / pro / lapsed`) instead of binary (`free / pro`) | Binary model cannot distinguish "never paid" from "payment failed." This forces the upgrade page to either show the wrong CTA or make a secondary API call to check subscription history. The `lapsed` state costs one string value and solves the UX problem at the model level. | Every consumer that pattern-matches on plan state must handle three cases instead of two. The `@check_usage_limit` decorator is unaffected because it only checks for `pro`. |
| Session-based post-checkout verification instead of polling or optimistic UI | Polling adds 2–10 seconds of spinner time at the most emotionally charged moment in the billing flow. Optimistic UI risks showing "Pro activated" when the webhook fails. Session retrieval is synchronous, sub-500ms, and authoritative — Stripe knows the payment succeeded before the webhook fires. | Adds one endpoint and one Stripe API call per checkout completion. The webhook still fires and remains the canonical write for `User.plan`, creating two write paths to the same field (session verify writes, webhook writes). Idempotency of the plan update prevents conflicts. |
| Response header for usage data instead of dedicated endpoint | The `@check_usage_limit` decorator already computes remaining usage on every gated request. Emitting it as a header is one line of backend change and zero additional HTTP requests. A dedicated endpoint would add a request per page load per feature — unnecessary network cost for data that already exists in the response pipeline. | Headers are invisible to casual debugging. The meter only updates when the user makes an API call to a limited endpoint — if they sit idle, the count is stale. Acceptable because usage only changes when they make calls. |
| Full-page redirect to Stripe Checkout instead of embedded payment form | Stripe Checkout is PCI-compliant out of the box with zero frontend code. Embedded forms (Stripe Elements) require JavaScript SDK integration, DOM mounting, error handling, and PCI SAQ-A-EP compliance. For a single $29/mo plan with no customization needs, the hosted page is strictly superior. | User leaves the app during checkout. Context is lost. If they abandon at Stripe, there is no recovery hook in the app. Acceptable for launch; an inline modal upgrade path is noted as a post-launch iteration. |
| Stripe Customer Portal for subscription management instead of custom UI | Portal handles payment method updates, cancellation, cancellation reasons, invoice downloads, and plan changes. Building any of this in-house would be weeks of work for a solo developer. The portal URL is already generated by `GET /api/billing/status`. | User leaves the app for management actions. No custom branding beyond what Stripe portal settings allow. Cannot add custom retention flows or cancellation surveys beyond Stripe's built-in options. |
| No soft wall or 80% warning at launch | The soft wall (warning at 80% usage) improves conversion UX but doubles the interceptor's conditional logic and adds a notification component. The hard 429 is already well-structured and the upgrade path is clear. Soft wall is a conversion optimization, not a launch requirement. | Users discover limits abruptly. The usage meter partially mitigates this by showing remaining count, but there is no proactive notification. First-week conversion data will determine whether the soft wall is worth adding. |
| No inline upgrade modal at launch | A modal that overlays the current page preserves user context better than navigating to `/upgrade`. But it doubles the component surface: one modal for inline interruption, one page for direct navigation. Both need the same conditional CTA logic, plan-state reading, and checkout initiation. | Users lose their place when redirected to the upgrade page mid-workflow. If they were mid-generation, the failed request is lost. The 429 body includes the feature name, which the upgrade page can reference for contextual messaging, partially compensating for the context loss. |

## Integration Points

### Stripe ↔ Backend (Existing, Activation Only)

The billing service adapter at `api/modules/billing/service.py` already encapsulates all Stripe SDK calls behind the P1 adapter boundary. Four environment variables activate it: the secret key, the webhook signing secret, the price ID for the Pro product, and the frontend URL for checkout redirects. No code changes to the adapter — only configuration. The webhook endpoint at `POST /api/billing/webhook` already verifies signatures and routes six event types. The one modification is to the `invoice.payment_failed` handler, which writes `lapsed` instead of `free`.

### Backend ↔ Frontend (Existing Endpoints, One New)

Three existing endpoints serve the billing UI: `GET /api/billing/status` returns plan, subscription status, period end, and portal management URL. `POST /api/billing/create-checkout-session` creates a Stripe session and returns the redirect URL. `POST /api/billing/webhook` is Stripe-facing only. One new endpoint is needed: a `GET /api/billing/verify-session` that accepts a `session_id` query parameter, retrieves the session from Stripe, and returns the resulting plan state. This endpoint must be `@require_auth` and must verify that the session's `metadata.user_id` matches `g.current_user.id` before returning plan state — otherwise any user who guesses a valid session ID could query it. This endpoint exists solely to close the webhook-redirect race condition and is called exactly once per checkout completion. It must be added to `routes.py` and `openapi.yaml`.

### Usage Decorator ↔ Billing Interceptor (New Header Contract)

The `@check_usage_limit` decorator at `api/modules/usage/` already computes remaining daily calls for each feature on every gated request. A new responsibility: after the limit check passes, the decorator adds an `X-Usage-Remaining` response header with the remaining count and daily cap. The billing interceptor on the frontend reads this header from every response and writes it into a signal that the usage meter component consumes. This is a passive data flow with no dedicated request-response cycle.

### SubscriptionService ↔ Component Tree (Signal Propagation)

The `SubscriptionService` exposes its plan signal and computed `isPro` accessor. Consumers include: the upgrade page (conditional CTA rendering), the billing interceptor (contextual 429 messaging), the usage meter (visibility toggle), and any future feature-gated components. The service is injectable and mockable — the co-located mock file provides a fixture version for component tests that need plan state without HTTP calls.

## Scope Boundaries

### Deferred by Design

The `SubscriptionService` interface should not assume authenticated context in its type signature, preserving a future path for Trendfy-style checkout-before-signup. However, no code is written for this path now — P4 prohibits speculative abstractions for flows that do not exist yet.

The soft wall (80% usage warning) and inline upgrade modal are conversion optimizations that should be driven by first-week data. The architecture supports both — the usage signal already carries remaining-count data for a soft wall, and the `SubscriptionService.startCheckout()` method is callable from any component including a future modal — but neither is built at launch.

Revenue metrics (`GET /api/admin/metrics` for MRR, subscriber count, churn) are operationally important within the first week but are admin tooling, not user-facing billing. They belong in a separate task and should not gate the billing UI launch.

The `stripe listen` development sidecar improves local webhook testing ergonomics but is developer tooling, not shipping software. It should be documented in a development setup guide, not architected as infrastructure.

## Risk Mitigation

| Risk | Mitigation | Residual |
|------|------------|----------|
| Webhook-redirect race condition: user sees "Free plan" after paying | Session verification endpoint retrieves payment status directly from Stripe on redirect. Plan is updated before the page renders. Webhook still fires as canonical write. | If Stripe's session retrieval API is slow (rare), there is a brief verification state. Acceptable — the user sees "Verifying your purchase" rather than stale data. |
| Lapsed user shown wrong CTA | Tri-state plan model distinguishes `lapsed` from `free` at the data level. Every UI surface reads plan state, not a boolean. | Requires every new consumer of plan state to handle three cases. Mitigated by the computed `isPro` accessor which collapses the check for the common "can they use this feature" question. |
| Auth interceptor regression from billing changes | Billing interceptor is a separate file with separate tests. Auth interceptor is untouched. No shared state between them. | Two interceptors in the HTTP pipeline adds ordering sensitivity. The billing interceptor must run after auth (so the request has a token) but the two do not interact otherwise. |
| Stripe test-mode credentials leaked to production | Environment variables are configured per-environment. Production keys are set in Coolify, not in version-controlled files. `.env` is gitignored. | Human error during Coolify configuration. Mitigated by Stripe's key prefix convention: test keys start with `sk_test_`, live keys start with `sk_live_`. A runtime log on startup could warn if test keys are detected in production. |
| 146-test regression from new providers and interceptors | New components include co-located spec files. The billing interceptor is registered in providers but does not modify existing interceptor behavior. E2E verification task explicitly runs the full test suite. | New interceptor could theoretically affect request timing in existing tests. Mitigated by the interceptor only acting on 429 responses, which existing tests do not produce. |

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this architecture
- [Epic](./epic.md) — Scope, tasks, success criteria, and effort estimates
- [Timeline](./timeline.md) — Delivery schedule and status tracking