---
sidebar_position: 4
---

# 📅 Bubls App Store Launch – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Est. Effort | Notes |
|---|------|--------|-------------|-------|
| 1 | Stripe subscription backend | backlog | 2 days | Requires Stripe account + API keys provisioned |
| 2 | Paywall UI + feature guard | backlog | 1.5 days | Blocked by Task 1 |
| 3 | Usage metering enforcement | backlog | 1.5 days | Blocked by Task 1 |
| 4 | Voice input on Text page | backlog | 2 days | Independent — can start immediately |
| 5 | Share sheet integration | backlog | 1 day | Independent — can start immediately |
| 6 | App Store submission | backlog | 1.5 days | Blocked by Tasks 2, 3, 4, 5 |

**Total estimated effort**: 9.5 days (6.5 days on critical path: 1 → 2+3 → 6)

---

## Parallel Execution Plan

```
Day 1-2:  Task 1 (Stripe) | Task 4 (Voice) | Task 5 (Share)
Day 3:    Task 2 (Paywall) | Task 3 (Usage) | Task 4 (Voice, cont.)
Day 4:    Task 2 (cont.)   | Task 3 (cont.)
Day 5-6:  Task 6 (App Store submission)
```

With three parallel streams, the critical path compresses to ~6 working days.

---

## Status Legend

- `backlog` - Not started
- `in_progress` - Currently working
- `done` - Completed
- `blocked` - Waiting on dependency

---

## Pre-flight Checklist

| Item | Status | Notes |
|------|--------|-------|
| Stripe account provisioned | pending | Need `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| Stripe price IDs created (monthly + annual) | pending | $4.99/mo, $39.99/yr |
| Privacy policy page written | pending | Host at `humaniz.me/bubls/privacy` |
| App Store Connect app record created | pending | Bundle ID, app name reserved |
| `@capacitor-community/speech-recognition` installed | pending | `npm install` + `npx cap sync` |
| `@capacitor/share` installed | pending | `npm install` + `npx cap sync` |
| Screenshots captured (3 device sizes × 3 features × 2 modes) | pending | 18 screenshots minimum |

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-18 | All | Created | Initial epic generation from product spec braindump |

===END===