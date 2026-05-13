# E2E: SaaS Happy Paths (Isolation + Billing)

> **Priority**: P1 — these are the core user journeys that must work for specview to be a real SaaS product.
> **Effort**: ~1 day for Gherkin + step definitions.
> **Depends on**: Phase 2a (isolation) and Phase 2b (billing) merged. Test Phase 2 (Gherkin infra) for step definition wiring.

## The problem

We implemented project isolation (Phase 2a) and billing UI (Phase 2b) but the E2E test suite doesn't cover any of it. The existing 5 feature files test brainstorm, bootstrap pipeline, epic guide, billing gate, and pro check — all pre-isolation, pre-billing-UI flows. None verify that multi-tenancy works, that the checkout flow completes, or that the upgrade funnel converts.

These are the highest-value E2E scenarios to add because they test the revenue path end-to-end.

---

## Happy paths to cover

### Project Isolation (from Phase 2a)

**User-scoped project listing:**
A logged-in user sees only their own projects. A second user registers and sees an empty list. Creating a project as the second user shows only that one project.

**Ownership enforcement:**
User B tries to access User A's project by slug — gets 403 "access denied", not the project content. Same for delete and edit attempts.

**Frontend access denied state:**
When a user navigates to a project they don't own (e.g. via direct URL), the UI shows "You don't have access to this project" with a back button — not a broken page or raw JSON error.

**Project creation dual-write:**
Creating a new project via the UI results in both a DB row (with correct user_id) and a filesystem directory. The project appears in the list immediately.

### Billing & Upgrade (from Phase 2b)

**Free tier limit → upgrade prompt:**
A free-tier user generates specs until they hit the daily limit. The 429 response triggers navigation to the `/upgrade` page with a contextual message ("You've used all N daily generations"). The usage meter in the masthead shows "0/N remaining" with warning styling.

**Stripe checkout flow:**
From the upgrade page, clicking "Upgrade to Pro" redirects to Stripe Checkout. After completing payment (test card 4242...), the user returns to the app, sees a brief verification state, then "Welcome to Pro" confirmation. The plan signal updates immediately.

**Pro user bypasses limits:**
After upgrading, generating specs works without limits. The usage meter is hidden. No 429 responses.

**Lapsed state — payment failure:**
When `invoice.payment_failed` fires (simulated via Stripe CLI), the user's plan becomes `lapsed`. The upgrade page shows "Update your payment method" messaging with a Customer Portal CTA — not "Upgrade to Pro".

**Manage subscription:**
A Pro user navigating to `/upgrade` sees "You're on Pro" with a "Manage subscription" button that opens the Stripe Customer Portal.

---

## Existing E2E infrastructure

- `e2e/features/` — 5 Gherkin feature files, 10 scenarios
- `e2e/steps/common_steps.py` — shared Given/When/Then step definitions
- `e2e/pages/app_page.py` — page object (load, enter_text, click, is_visible, wait_visible)
- `e2e/conftest.py` — session fixtures spinning up Flask (port 5001, CHAIN_PROVIDER=mock) + Angular dev server (port 4201)
- `product-behavior.md` — 5 core flows mirrored 1:1 by existing features

The existing `billing-gate.feature` already tests the 429 → billing gate message flow. The new scenarios extend this to cover the full upgrade funnel and add isolation coverage that doesn't exist yet.

Note: the CI E2E step currently collects 0 tests and is `continue-on-error`. The step definitions need a running app (docker compose). This braindump's scope includes wiring the step definitions so CI can run them.

---

## Relationship to Test Phase 2

The Test Phase 2 braindump (`test-phase2-gherkin-e2e-1778592996`) covers overview page E2E tests (navigation, status bar, search, grid, polling). This braindump covers SaaS-specific flows (isolation, billing, upgrade). They're complementary — both contribute to the same `e2e/features/` directory and share step definitions.

## Testing baseline

Phase 3 established 146 frontend unit tests + 819 backend tests. These E2E scenarios add a new layer on top — they verify user-visible behavior through a real browser, not unit-level logic. They should not duplicate what unit tests already cover (e.g. the ownership decorator logic is tested in `test_project_ownership.py`).
