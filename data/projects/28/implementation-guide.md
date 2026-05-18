# Implementation Guide: SaaS Phase 2b — Billing UI & Stripe Activation

## Overview
This epic activates the existing Stripe billing backend by configuring credentials, introducing a tri-state plan model (`free | pro | lapsed`), building a signal-based Angular subscription service, adding a dedicated 429 billing interceptor, and delivering an upgrade page with contextual CTAs. Tasks sequence linearly: environment activation and backend schema changes first (Task 1), then the reactive service layer (Task 2), then the interceptor and upgrade page in parallel (Task 3), then the passive usage meter (Task 4), and finally end-to-end verification (Task 5). The total effort is 1.75 days.

## Shared Pre-flight
- Confirm Stripe test-mode account exists and dashboard is accessible; create the "Specview Pro" product ($29/mo recurring) and note the resulting Price ID
- Verify the existing backend billing endpoints respond: `GET /api/billing/status`, `POST /api/billing/create-checkout-session`, `POST /api/billing/webhook`
- Confirm the existing `auth.interceptor.ts` is registered in `app.config.ts` via `withInterceptors()` and is untouched throughout this epic
- Run the existing 146 frontend tests and confirm a green baseline before any changes
- Run `billing-gate.feature` E2E scenario to establish its current pass/fail state
- Confirm `openapi.yaml` is the source of truth for Angular DTO generation and locate the codegen command
- Confirm `.env` is gitignored and that per-environment secrets are managed via Coolify, not version control
- Locate `api/modules/usage/` to identify the `@check_usage_limit` decorator file for Task 1 header emission

---

## Task 1: Stripe Activation & Lapsed State  [Effort: 0.25 days]

### What
Configures the four Stripe environment variables so the existing billing backend becomes operational, extends the plan model from binary to tri-state by adding `lapsed`, emits usage-remaining headers from the backend decorator, and adds the session verification endpoint that closes the post-checkout race condition.

### Files
- **Modify**: `.env` — add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, and `FRONTEND_URL` with test-mode values
- **Modify**: `openapi.yaml` — extend the Plan enum from `[free, pro]` to `[free, pro, lapsed]` and add the `GET /api/billing/verify-session` endpoint schema with `session_id` query parameter and response shape
- **Modify**: `api/modules/billing/service.py` — update the `invoice.payment_failed` webhook handler to write `plan='lapsed'` instead of `plan='free'`; add a `verify_session(session_id, user_id)` method that calls `stripe.checkout.sessions.retrieve()` and validates `metadata.user_id`
- **Modify**: `api/modules/billing/routes.py` — register the `GET /api/billing/verify-session` route with `@require_auth` and user_id ownership check
- **Modify**: the `@check_usage_limit` decorator file in `api/modules/usage/` — after the limit check passes, add the `X-Usage-Remaining` header to the response with the remaining count and daily cap

### Steps
1. Set the four environment variables in `.env` using test-mode values obtained from the Stripe dashboard: the secret key (prefixed `sk_test_`), the webhook signing secret (prefixed `whsec_`), the Price ID for the Specview Pro product, and the frontend URL for checkout redirects.
2. Open `openapi.yaml` and add `lapsed` as a third value in the Plan enum, then define the `GET /api/billing/verify-session` endpoint with a required `session_id` query parameter and a response schema containing the plan state.
3. Run the OpenAPI codegen command to regenerate Angular DTOs so the frontend type system reflects the tri-state plan and the new endpoint.
4. In the billing service file, locate the `invoice.payment_failed` handler and change the value written to `User.plan` from `free` to `lapsed`.
5. Add a `verify_session` method to the billing service that accepts a session ID, retrieves the session from Stripe, checks that `metadata.user_id` matches the authenticated user, and returns the resulting plan state.
6. Register the verify-session route in `routes.py` with `@require_auth`, calling the new service method and returning the plan state.
7. In the `@check_usage_limit` decorator, after the limit check passes and before the response returns, add the `X-Usage-Remaining` header containing the remaining count and daily cap as a structured value.
8. Verify webhook delivery by running `stripe listen --forward-to localhost:5001/api/billing/webhook` and triggering a test event from the Stripe CLI.

### Verify
- `stripe trigger invoice.payment_failed` results in the target user's plan being set to `lapsed` in the database, not `free`
- `curl -H "Authorization: Bearer <token>" "localhost:5001/api/billing/verify-session?session_id=cs_test_xxx"` returns a JSON response with the plan state and rejects requests where the session's user_id does not match the authenticated user
- A request to any usage-limited endpoint returns the `X-Usage-Remaining` header in the response
- Regenerated Angular DTOs include `lapsed` in the Plan type union

---

## Task 2: SubscriptionService + Tests  [Effort: 0.5 days]

### What
Builds the signal-based Angular service that is the single source of truth for billing state across the application, providing reactive plan state, a computed `isPro` accessor, checkout initiation via redirect, and post-checkout session verification to close the webhook race condition.

### Files
- **Create**: `web-ng/src/app/services/subscription.service.ts` — writable signal holding `free | pro | lapsed`, computed `isPro` accessor, `startCheckout()` method, `refresh()` method, and `verifySession(sessionId)` method
- **Create**: `web-ng/src/app/services/subscription.service.spec.ts` — unit tests covering plan state transitions, checkout initiation, session verification, and the `isPro` computed accessor for all three plan states
- **Create**: `web-ng/src/app/services/subscription.service.mock.ts` — mock implementation with settable plan state for use in downstream component tests

### Steps
1. Create the service file with `@Injectable({ providedIn: 'root' })` and declare a writable signal initialized to `free` for the plan state.
2. Add a computed signal `isPro` that derives `true` when the plan value is `pro` and `false` otherwise.
3. Implement a `refresh()` method that calls `GET /api/billing/status` using the generated API client, reads the plan from the response, and updates the writable signal.
4. Implement `startCheckout()` which calls `POST /api/billing/create-checkout-session`, receives the Stripe Checkout URL from the response, and performs a full-page redirect via `window.location.href`.
5. Implement `verifySession(sessionId: string)` which calls `GET /api/billing/verify-session` with the session ID, reads the resulting plan state, and updates the writable signal — this is the race condition mitigation path called exactly once after checkout redirect.
6. Wire the service to call `refresh()` on initialization so the plan state is populated when the app boots.
7. Create the spec file with tests for: initial state is `free`, `refresh()` updates the signal from the API response, `isPro` returns `true` only for `pro`, `verifySession` updates plan state on success, and `startCheckout` triggers a redirect.
8. Create the mock file exporting a class with the same public interface but backed by a manually settable signal, suitable for injection in component-level tests.

### Verify
- `ng test --include='**/subscription.service.spec.ts'` passes all tests
- The mock file exports a class with `plan`, `isPro`, `startCheckout`, `refresh`, and `verifySession` matching the real service interface
- The service is tree-shakeable via `providedIn: 'root'` with no module registration required
- Manually calling `refresh()` in the browser console after injecting the service updates the plan signal from the billing status endpoint

---

## Task 3: Billing Interceptor + Upgrade Page  [Effort: 0.5 days]

### What
Delivers two parallel artifacts gated on Task 2: a dedicated HTTP interceptor that catches 429 responses and routes users to the upgrade page with contextual messaging, and the upgrade page itself with conditional CTAs based on plan state, post-checkout verification handling, and Stripe Customer Portal integration.

### Files
- **Create**: `web-ng/src/app/interceptors/billing.interceptor.ts` — functional interceptor catching 429 responses, extracting usage context from the response body, reading plan state from SubscriptionService, and navigating to `/upgrade` with appropriate query parameters
- **Create**: `web-ng/src/app/interceptors/billing.interceptor.spec.ts` — tests for 429 handling across all three plan states, non-429 passthrough, and usage header extraction
- **Create**: `web-ng/src/app/components/upgrade/upgrade.component.ts` — standalone component with pricing comparison, conditional CTA rendering, and post-checkout session verification state
- **Modify**: `web-ng/src/app/app.config.ts` — register the billing interceptor in the `withInterceptors()` array after the auth interceptor
- **Modify**: `web-ng/src/app/app.routes.ts` — add the `/upgrade` route pointing to the upgrade component

### Steps
1. Create the billing interceptor as a functional interceptor (Angular 17 style) that inspects every HTTP response in the pipeline.
2. For non-429 responses, the interceptor passes through unchanged but reads the `X-Usage-Remaining` header if present and writes the value into a signal on an injectable usage state holder for the usage meter to consume in Task 4.
3. For 429 responses, the interceptor reads the structured response body to extract the feature name, daily cap, and reset time provided by the `@check_usage_limit` decorator.
4. The interceptor reads the current plan state from `SubscriptionService` to determine navigation context: for `free` users, navigate to `/upgrade` with a query parameter indicating "limit reached" and the feature name; for `lapsed` users, navigate to `/upgrade` with a query parameter indicating "payment lapsed"; for `pro` users (should not occur), log the anomaly and do not navigate.
5. Register the interceptor in `app.config.ts` by adding `billingInterceptor` to the `withInterceptors()` array, positioned after `authInterceptor` so requests already carry auth tokens.
6. Create the upgrade component as a standalone Angular component that injects `SubscriptionService` and reads query parameters from the activated route.
7. Implement the template with three conditional sections based on plan state: for `free` users, show a feature comparison table between Free and Pro tiers with a primary "Upgrade to Pro — $29/mo" button that calls `startCheckout()`; for `lapsed` users, show payment recovery messaging ("Update your payment method to restore Pro access") with a button that opens the Stripe Customer Portal URL from the billing status response; for `pro` users, show an active plan confirmation with a "Manage subscription" button linking to the Customer Portal.
8. Add post-checkout handling: when the URL contains a `session_id` query parameter, display a brief verification state, call `SubscriptionService.verifySession()` with the session ID, and transition to a "Welcome to Pro" confirmation upon success.
9. Reconcile the `success_url` in the backend `service.py` to redirect to `/upgrade?session_id={CHECKOUT_SESSION_ID}` so the upgrade component handles both the pre-checkout and post-checkout flows on a single route.
10. Add the `/upgrade` route to `app.routes.ts` pointing to the upgrade component.
11. Write interceptor tests covering: 429 with `free` plan navigates to `/upgrade` with limit-reached context, 429 with `lapsed` plan navigates with payment-lapsed context, 429 with `pro` plan logs but does not navigate, non-429 responses pass through unchanged, and `X-Usage-Remaining` header is extracted when present.

### Verify
- `ng test --include='**/billing.interceptor.spec.ts'` passes all tests
- Navigating to `/upgrade` in the browser renders the pricing comparison for a free-tier user
- Simulating a 429 response (via browser dev tools or a test endpoint) redirects to `/upgrade` with the correct query parameters
- The "Manage subscription" button for a pro user opens the Stripe Customer Portal in a new tab

---

## Task 4: Usage Meter (Header-Based)  [Effort: 0.25 days]

### What
Adds a passive usage meter pill component to the application header that shows remaining daily API calls per feature, driven entirely by response headers extracted by the billing interceptor with zero additional network requests, and hidden for Pro users.

### Files
- **Create**: `web-ng/src/app/components/usage-meter/usage-meter.component.ts` — standalone pill component reading from the usage signal populated by the billing interceptor, displaying remaining count against daily cap with warning styling at low counts
- **Create**: `web-ng/src/app/components/usage-meter/usage-meter.component.spec.ts` — tests for display formatting, warning state at remaining count of one or fewer, and hidden state for Pro users
- **Modify**: the app shell or header component that provides persistent navigation — add the usage meter component to the template

### Steps
1. Create the usage meter as a standalone component that injects `SubscriptionService` for the `isPro` check and the usage state holder (populated by the billing interceptor in Task 3) for the remaining-count signal.
2. Implement the template as a small pill element that displays the remaining count against the daily cap in a format like "3/10 remaining".
3. Add conditional styling that shifts the pill to a warning visual treatment (red or similar) when the remaining count drops to one or fewer.
4. Wrap the entire component template in a conditional that hides it when `isPro` is `true`, since Pro users have no usage caps.
5. Place the component in the app shell or header layout so it is visible across all pages.
6. Write tests covering: correct display of remaining count and cap, warning styling triggers at remaining count of one, warning styling triggers at remaining count of zero, component is not rendered when `isPro` is `true`, and component handles the initial state before any API response has populated the usage signal.

### Verify
- `ng test --include='**/usage-meter.component.spec.ts'` passes all tests
- Making an API call to a usage-limited endpoint causes the meter to update in the header with the correct remaining count
- Setting plan to `pro` via the mock service causes the meter to disappear from the UI
- The meter shows warning styling when remaining count reaches one or zero

---

## Task 5: E2E Verification & Regression Suite  [Effort: 0.25 days]

### What
Performs a full end-to-end verification of the Stripe billing flow in test mode, confirms the lapsed state produces correct upgrade page copy, and runs the complete frontend test suite plus the billing-gate E2E scenario to catch any regressions introduced by Tasks 1 through 4.

### Files
- **Modify**: E2E test files related to `billing-gate.feature` — update or extend steps if the new `/upgrade` route or `lapsed` plan state require additional scenario coverage

### Steps
1. Start the full application stack (backend and frontend) with Stripe test-mode credentials configured from Task 1.
2. Run `stripe listen --forward-to localhost:5001/api/billing/webhook` in a terminal to forward webhook events during testing.
3. As a free-tier test user, trigger a usage-limited endpoint until a 429 is returned and confirm the billing interceptor navigates to the `/upgrade` page with "limit reached" messaging.
4. On the upgrade page, click the "Upgrade to Pro" button and complete the Stripe Checkout flow using test card number `4242424242424242` with any future expiry and CVC.
5. After redirect back to the app, confirm the post-checkout verification shows a brief loading state followed by "Welcome to Pro" confirmation and that the plan signal updates to `pro` immediately without waiting for the webhook.
6. Confirm the $29 charge appears in the Stripe test-mode dashboard and that the webhook fires and writes `plan='pro'` to the database, matching the session verification result.
7. Verify the usage meter disappears from the header now that the user is on the Pro plan.
8. Simulate an `invoice.payment_failed` event via `stripe trigger invoice.payment_failed` for the test user and confirm the plan transitions to `lapsed`, the upgrade page shows "Update your payment method to restore Pro access" messaging, and the CTA opens the Stripe Customer Portal.
9. On the upgrade page as a `lapsed` user, confirm the "Manage subscription" button opens the Customer Portal successfully.
10. Run the full frontend test suite to confirm zero regressions across all 146 existing tests plus the new spec files from Tasks 2 through 4.
11. Run the `billing-gate.feature` E2E scenario against the live billing routes and confirm it passes.

### Verify
- `ng test` passes with zero failures across all existing and new test files
- The `billing-gate.feature` E2E scenario passes against real billing routes
- Stripe test-mode dashboard shows a $29 charge for the Specview Pro product with the correct test user metadata
- The `lapsed` plan state produces "Update your payment method" copy on the upgrade page, not "Upgrade to Pro"