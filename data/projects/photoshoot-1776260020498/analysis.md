# 🔍 Analysis: Photoshoot

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-04-15

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 5 |
| MEDIUM | 4 |

---

## The Core Problem

The /photoshoot feature promises instant, personalized AI photo enhancement — but the entire experience depends on a pre-trained LoRA model existing for each user before they ever open the app. This creates a hard ceiling: user #16 gets nothing. The manual pre-training approach (collect selfies via WhatsApp, train overnight on Replicate) is deliberately unscalable, which means the feature's value proposition — "your personal AI makes your photos beautiful" — breaks the moment it succeeds beyond 15 people.

Underneath this ceiling sits a second problem: identity. The app doesn't know who a user is until auth is wired, and it can't map a user to their LoRA model without that identity layer. Auth approach is explicitly unresolved (magic link vs. Supabase), and this decision cascades into payments, feature gating, and session management. Every downstream feature in the super app inherits whatever tradeoff is made here.

The third structural problem is latency. Replicate LoRA inference involves cold starts that can exceed 30 seconds. A user takes a selfie, taps a button, and then... waits. In a native camera app context, users expect near-instant feedback. The gap between expectation and reality is where abandonment lives.

Consider: It's like opening a restaurant where only 15 people have reservations, the kitchen takes 45 minutes per dish, and the host hasn't decided whether to check IDs at the door.

---

## Symptoms

Users experience:

- New users beyond the first 15 cannot use the feature at all — no model, no generation
- Unclear wait times after submitting a photo for AI processing
- No feedback mechanism if generation fails silently on the backend
- No way to retry or understand why a result didn't arrive
- Potential confusion about what the feature actually does (no onboarding, no explanation)
- Before/after comparison requires both images to load, but original may be local while result is remote
- Gallery shows past results but storage location and retrieval path are undefined
- iOS camera permissions prompt with no app-level context for why access is needed

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No path for user #16+ — manual LoRA pre-training caps the user base at 15 | Brain dump explicitly states "deliberately unscalable" and "no self-serve LoRA training" for Month 1 | Task: define onboarding boundary |
| Auth approach unresolved — magic link vs. Supabase decision blocks user identity, payments, and feature gating | Brain dump lists this as an open "decision point" with tradeoffs in both directions | Task: auth decision |
| No user-to-model mapping exists — per-user LoRA lookup (user_id → model_id) is new and unbuilt | Brain dump identifies this as "what's new" distinct from existing Trendfy infrastructure | Task: user-model mapping |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Replicate cold-start latency — LoRA inference can take 30-60+ seconds with no warm-up guarantee | Known Replicate behavior; brain dump doesn't mention latency mitigation | Task: latency expectations |
| No error handling for failed generations — Replicate failures, timeout, or model errors have no user-facing recovery | Brain dump describes only the happy path (photo in → result out) | Task: failure states |
| Image storage strategy undefined — where originals and results are persisted (Neon blob, S3, Replicate URLs) is unspecified | Brain dump mentions storing URLs in Neon but not the actual image hosting | Task: storage design |
| Camera plugin untested in super app context — Capacitor Camera plugin works in Bubls but hasn't been validated inside a tab-routed Ionic shell | Bubls used a different app structure; camera permissions and plugin lifecycle may differ | Task: camera integration validation |
| Trendfy verdict (May 1) injects architectural uncertainty — LoRA infrastructure may shift, merge, or be killed in 2 weeks | Brain dump: "These may diverge or converge depending on the verdict" | Task: isolation boundary |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Single default style with no user choice — users who dislike the output have no recourse | Brain dump: "No style picker for v1. One default style. Ship." — risk of low satisfaction if default doesn't land | Task: style validation |
| No generation cost tracking — Replicate inference costs per call aren't monitored or capped | Brain dump estimates $75-150 for training but doesn't address ongoing inference costs | Task: cost monitoring |
| No offline or poor-connectivity handling — every action requires network round-trip to Flask + Replicate | Native app context (iOS) where users expect some offline resilience; no mention of offline states | Task: connectivity states |
| No progress indication during generation — user submits photo and enters a void until result returns | Brain dump describes flow as "photo sent → result returned" with no intermediate states | Task: loading UX |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Self-serve LoRA training pipeline | Explicitly deferred — Month 1 is manual pre-training only |
| Android support | iOS-only for Month 1 via Capacitor; Android deferred |
| Style picker / multiple output styles | Deferred to post-v1 iteration |
| Analytics dashboard | "Check Neon directly" is the Month 1 approach |
| Social features (sharing to platforms) | Out of scope for Month 1 |
| Web-specific optimizations | iOS is primary; web works but isn't optimized separately |
| Onboarding wizard | Explicitly cut — "email + done" |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview