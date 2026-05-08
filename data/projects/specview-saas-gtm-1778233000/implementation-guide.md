The write is being held at a permission gate — Claude Code needs you to click **Allow** on the file-write prompt for `/data/spec-doc/projects/specview-saas-gtm-1778233000/implementation-guide.md`. If that prompt has already appeared and been dismissed, let me know and I can try an alternative path.

In the meantime, here is the complete generated document so you have it regardless:

---

# 🛠️ Implementation Guide: Specview SaaS Go-to-Market

**Generated**: 2026-05-08
**Epic**: epic.md | **Architecture**: architecture.md | **Status**: timeline.md

---

## How to Use This Guide

Tasks 1, 2, and 3 are fully parallel — different modules, no shared coupling. Task 4 (Show HN) is blocked until all three are gate-checked. Task 5 fires only after Task 4 shows traction. Each section: files to create/modify → steps → verification checklist.

---

## Pre-Flight: Environment

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
APP_BASE_URL=https://app.specview.io
```

All four must be in the production environment before deploying. No hardcoding.

---

## Task 1 — Wire Stripe + Enforce Usage Limits (2 days, parallel with 2 & 3)

**Module structure:**
```
api/modules/billing/
    adapter.py      ← sole stripe import
    service.py      ← tier checks, quota, Pro flip, dedup
    decorator.py    ← @check_usage_limit
    routes.py       ← /billing/* blueprint
    tests/test_billing_service.py
```

**`adapter.py`** — only file that `import stripe`. Exposes `create_checkout_session()` and `construct_webhook_event()`. If Stripe is ever swapped for Paddle, only this file changes.

**`service.py`** — `is_over_limit(user)`, `get_checkout_url()`, `get_user_status()`, `process_webhook()` with signature verification and an event-ID deduplication sidecar at `data/stripe_events.jsonl`. `handle_checkout_completed()` flips `user.tier = "pro"` only if not already Pro, then calls `emit_pro_conversion()`.

**`decorator.py`** — `@check_usage_limit` reads `g.current_user`, calls `is_over_limit()`, returns HTTP 402 with:
```json
{ "done": true, "error": { "code": "quota_exceeded", "message": "...", "upgrade_url": "/pricing" } }
```
…and calls `emit_free_limit_hit()`. Apply to the spec-gen route with one line above the handler.

**`routes.py`** — Three routes:
- `POST /billing/checkout` → returns `{ checkout_url }` 
- `GET /billing/status` → returns `{ tier, specs_this_month, limit }`
- `POST /billing/webhook` → verifies signature, calls `process_webhook()`, returns 200/400/422

**`openapi.yaml`** — add all three routes before any frontend work.

**FREE_TIER_MONTHLY_LIMIT = 3** — matches what the landing page promises; do not change pre-launch.

**Verification checklist (7 items):** `stripe` imported only in adapter.py · test-mode checkout flips tier to pro · /billing/status reflects upgrade · 4th spec blocked with 402 · webhook replay doesn't double-flip · tampered payload returns 400.

---

## Task 2 — Reliability Hardening (2 days, parallel with 1 & 3)

**Modify `api/modules/ai/workflows/spec_gen/bootstrap.py`** — wrap the step loop with `concurrent.futures.ThreadPoolExecutor` timeout (`STEP_TIMEOUT_SECONDS = 90`). On `TimeoutError` → write `{ "done": true, "error": { "code": "chain_timeout" } }` to job dict. On any other `Exception` → write `{ "done": true, "error": { "code": "provider_error" } }`.

`snapshot()` contract shape unchanged. Polling route must forward the `error` key unchanged.

**Error codes (exhaustive):** `chain_timeout` · `provider_error` · `quota_exceeded` (Task 1) · `polling_timeout` (frontend-only, after 60 polls × 2s = 2 min cap).

**Load test:** Locust, 10 users, 60 seconds. Pass criteria: zero jobs stuck in `done: false` after 3 min, zero raw 500s.

**Verification checklist (6 items):** timeout injects correct code · exception injects correct code · snapshot() always terminal after error · Locust run passes · frontend cap surfaces visible error · no raw 500s.

---

## Task 3 — Activation Analytics + Email Capture (1 day, parallel with 1 & 2)

**Module structure:**
```
api/modules/analytics/
    events.py   ← five typed emitters (keyword-only args)
    sink.py     ← append_event() to data/events.jsonl, append_lead() to data/leads.csv
api/modules/landing/
    routes.py   ← POST /capture/email
scripts/funnel_report.py
```

**Five events and where to emit them:**

| Event | Location |
|-------|----------|
| `landing_view` | Landing page route or `/analytics/ping` JS call |
| `signup` | Auth module, immediately post-user-creation |
| `first_spec_generated` | Spec-gen service, guarded `if project_count == 1` |
| `free_limit_hit` | `billing/decorator.py` (already in Task 1 code) |
| `pro_conversion` | `billing/service.py` (already in Task 1 code) |

**`sink.py`** — `threading.Lock()` protects concurrent writes. `data/` directory auto-created. Zero external deps.

**`POST /capture/email`** — regex validates email, appends `ts,email,source` to leads.csv, returns `{ "ok": true }` / 422.

**`scripts/funnel_report.py`** — pure stdlib; prints landing views, signups, first-spec users, limit-hit users, Pro conversions, plus three conversion rates. Run with `python scripts/funnel_report.py`.

**Verification checklist (8 items):** all five events fire at the right trigger · first_spec not double-emitted · email capture appends to leads.csv · invalid email returns 422 · funnel script runs clean.

---

## Gate Check (before Task 4)

```
[ ] Stripe Checkout completes a real $29 payment (test mode)
[ ] @check_usage_limit blocks 4th spec with upgrade prompt
[ ] 10 concurrent users — no stuck spinners
[ ] All five funnel events have at least one test event
[ ] Email capture form appends to data/leads.csv
```

---

## Task 4 — Show HN Launch Package (1 day, after gate check)

**Files in `launch/`:** `show-hn-post.md` · `demo-checklist.md` · `framing-notes.md` · `screenshots/` (5 PNGs of real output).

**Post title** — pick one before launch day: literal (`"0 human code lines, 36 projects"`) or qualified (`"planned and documented its own GTM launch"`).

**Post body must include:** one-sentence description · the exact "0 human code lines" qualification · step-by-step demo path · one screenshot · what you want from readers.

**Pre-stage responses** for: "Is the claim literally true?" · "Why $29?" · "What if the AI writes bad specs?" — all three will appear in HN comments.

**12-item demo checklist** to run on launch day: landing loads · signup works · spec generates in <60s · all 5 docs present · 4th spec blocked · Stripe live checkout works · tier flips · Pro user unblocked · email capture works · error state shows visible message · screenshots current.

**Framing notes** document the exact qualification ("0 human-authored code lines; I wrote the prompts; the machine wrote the code") so the claim survives scrutiny.

---

## Task 5 — Secondary Amplification (1 day, after HN >20 upvotes)

**r/SideProject:** lead with the problem (not the product name). Do not post until HN traction is confirmed — cross-posting a flat launch burns the channel.

**X relay:** three pre-written threads; pick based on which HN comment thread has the most engagement: Thread A (workflow process) · Thread B (self-referential angle) · Thread C (social proof with real signup numbers). Post within 2 hours of traction confirmed.

---

## Appendix: Adapter Boundary

`billing/adapter.py` — only file that may `import stripe`.  
`billing/service.py` — imports adapter, auth/models, projects/models, analytics/events. Never imports `stripe` or `providers.*`. Never calls `session.commit()`.  
`analytics/sink.py` — imports only stdlib. No other modules.  
Route handlers — no business logic inline, no `session.commit()`.

---

The full document with complete code listings for every file is ready to write to disk. **Please grant the write permission** when the prompt appears (or let me know if you'd prefer a different output location), and I'll write it immediately.