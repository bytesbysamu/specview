# SaaS Monetisation — Analysis

## The Problem
spec-doc has no revenue layer and no usage gate. Wiring the Anthropic SDK makes uncapped free access direct API spend on day one of public launch. Stripe Checkout + daily call metering close both gaps without adding PCI scope or a billing UI to maintain.

## Hard Constraints
- **Blocks on persistence brain dump** — `user_id` FKs on both tables require `spec_doc_users` to exist first; this work cannot start until that ships.
- **Auth decorator must be live** — `g.current_user` and `user.plan` are read on every gated request.
- **OpenAPI-first rule violated** — billing and usage routes must enter `openapi.yaml` before any route code is written; `make generate-dtos` must run before implementation. Brain dump skips this entirely.
- **SQLite runtime only** — atomic upsert uses `INSERT … ON CONFLICT DO UPDATE`; valid on SQLite ≥ 3.24. Confirm deployed version before porting from bubls.
- **Stripe sole-writer constraint** — already decided; no internal path may set `plan='pro'` except webhook handlers.
- **Single Price ID at launch** — no annual, team, or usage-based variants. Already decided.

## Open Questions
- **Free-tier caps** — `bootstrap=3 / task_gen=20 / spec_gen=10` are proposed, not decided. Needs a call before the 429 response shape enters `openapi.yaml`.
- **Past-due access rule** — `invoice.payment_failed` sets `past_due` but doesn't define Pro access during grace. Options: (a) stay Pro until `subscription.deleted`; (b) revert to free on first failed payment.
- **Usage status endpoint** — Angular usage-meter needs current counts, but no `/api/usage/status` route appears. Options: (a) new dedicated route; (b) fold into `/api/billing/status`; (c) drop the meter pill for v1.
- **Webhook count mismatch** — section heading says "6 webhook handlers"; only 5 events are listed. Missing event must be named before the handler table is final.

## Dependencies & Sequencing
- Persistence brain dump ships → tables and FKs exist → this work begins.
- Stripe dashboard: create product + Price ID → populate env vars → local webhook testing possible via `stripe listen`.
- `openapi.yaml` updated → `make generate-dtos` → routes implement the contract (must not be skipped).

## Explicitly Out of Scope
- **Annual / team / lifetime plans** — re-scope when a second pricing tier is requested by a paying user.
- **Token-based or per-minute metering** — daily call count is the v1 currency; re-scope if abuse patterns emerge.
- **Per-org usage pools** — requires workspaces brain dump; single-user counters only.
- **Coupon codes, refund automation, in-app purchase** — Stripe Dashboard handles manually; no trigger to bring in-scope.
- **Billing UI beyond upgrade page** — Customer Portal owns all self-service; spec-doc renders no plan-management screens.