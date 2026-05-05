---
sidebar_position: 4
---

# 📅 Bubls Landing Page – Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Domain + DNS | backlog | Decision needed: bubls.app vs bubls.ch vs trendfy.me subdomain |
| 2 | Screenshot capture | backlog | Needs TestFlight build with photoshoot, text, onboarding working |
| 3 | Email capture backend | backlog | Neon table + Flask endpoint |
| 4 | Landing page build | backlog | Blocked by Task 2 (screenshots) |
| 5 | Coolify deploy + SSL | backlog | Blocked by Tasks 1, 3, 4 |

---

## Status Legend

- `backlog` - Not started
- `in_progress` - Currently working
- `done` - Completed
- `blocked` - Waiting on dependency

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-17 | All | Spec generated | Ready for execution |

===END===

---

Five files, all specific to the Bubls landing page. Key decisions surfaced:

| Decision | Recommendation |
|----------|---------------|
| Domain | `bubls.app` — clean brand, `.app` enforces HTTPS |
| Framework | Static HTML — one page doesn't need Next.js |
| Email | Neon table + 30-line Flask endpoint |
| Hosting | Coolify on Trendfy VPS (already provisioned) |

**Three things you need to decide before Task 1 starts:**
1. Domain — `bubls.app`, `bubls.ch`, or `bubls.trendfy.me`?
2. The one-liner (under 10 words)
3. Which three screenshots to capture from the TestFlight build

Total estimated effort: ~8 hours across 5 tasks, with Tasks 1-3 parallelizable.