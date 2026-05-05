---
sidebar_position: 1
---

# 🔍 Bubls App Store Launch – Analysis

**Purpose**: Identify the problems blocking Bubls from generating revenue and reaching organic users.

**Date**: 2026-04-18

---

## Summary

- **Total Issues**: 6
- **Critical**: 2
- **High**: 3
- **Medium**: 1

---

## Issue Breakdown

### Revenue Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No payment infrastructure — app is free, API costs are unbounded, zero revenue despite validated $195K MRR market | CRITICAL | Task 1 (Stripe backend), Task 2 (Paywall UI) |
| No usage enforcement — free-tier users can call chain modes and single-shot rewrites without limit, making cost unpredictable | CRITICAL | Task 3 (Usage metering) |

### Distribution Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| TestFlight-only distribution — capped at 10K testers, no organic discovery, no App Store search ranking | HIGH | Task 6 (App Store submission) |
| No sharing — text results, photoshoot images, and picks have no share sheet; viral loop is broken at the output | HIGH | Task 5 (Share sheet) |

### Differentiation Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No voice input — every competitor already does text-to-text rewriting; Bubls has no unique input modality to earn a distinct position | HIGH | Task 4 (Voice input) |

### Compliance Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Missing App Store metadata — no screenshots, no privacy labels, no review-guidelines audit; submission would be rejected | MEDIUM | Task 6 (App Store submission) |

---

## Hard Constraints

| Constraint | Source | Impact |
|-----------|--------|--------|
| Neon Postgres only — no Supabase, no Firebase | Architecture principles | Subscription state, usage counters, receipt validation all go in Neon |
| Magic link auth — no passwords, no OAuth | Architecture principles | Stripe customer linked to magic-link user via email, no session cookies |
| Server enforces, client hints | Architecture principles | Usage limits checked server-side; 429 response drives paywall UI |
| ORM always — no raw SQL | Architecture principles | Subscription and usage models via SQLAlchemy/SQLModel + Alembic |
| Feature guard → paywall, never 404 | Architecture principles | Blocked Pro features show upgrade page with pricing, not an error |

## Open Questions

| Question | Decision needed by | Default if unresolved |
|----------|-------------------|----------------------|
| Stripe Checkout (server-hosted) vs. in-app purchase (StoreKit 2)? | Task 1 start | Stripe Checkout — Apple takes 30% on IAP; web-first billing avoids the cut. Risk: Apple may reject apps that redirect to web for payment. Mitigation: offer both, default to web. |
| Web Speech API vs. Capacitor community speech-recognition plugin vs. Whisper API? | Task 4 start | Capacitor community plugin (`@capacitor-community/speech-recognition`) — native on-device, no API cost, works offline. Web Speech API is Chrome-only; Whisper adds latency + cost. |
| Annual pricing ($39.99/yr) at launch or post-launch? | Task 1 start | At launch — annual subscribers have higher LTV and lower churn; offer both from day one. |

## Dependencies

| Dependency | Status | Impact if missing |
|-----------|--------|-------------------|
| Stripe account with webhook signing secret | Not provisioned | Task 1 blocked — need account + API keys |
| Apple Developer account with App Store Connect access | Provisioned (existing) | Task 6 ready |
| Privacy policy URL | Not published | Task 6 blocked — App Store requires privacy policy link |
| App Store screenshots (6.7" + 6.1" + iPad) | Not captured | Task 6 blocked — need 3 device sizes minimum |

## Explicitly Out of Scope

- Push notifications for Picks (post-launch engagement feature)
- Analytics dashboard UI (tracking data is collected; dashboard is a separate capability)
- Offline mode / multi-device sync (post-PMF infrastructure)
- A/B testing pricing tiers (optimize after first 200 users)
- Refund handling (manual via Stripe dashboard until volume justifies automation)

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

