---
sidebar_position: 4
---

# 📅 Bubls — Timeline

**Purpose**: Track task status. This is the ONLY place for status tracking.

---

## Progress

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Supabase schema + project setup | backlog | Two tables: subscribers, picks. RLS with token-based access. |
| 2 | Landing page + signup flow | backlog | City + interests + email → redirect to dashboard. Depends on Task 1. |
| 3 | Dashboard page | backlog | /picks/[token] — 5 event cards, interests editor, countdown. Depends on Task 1. |
| 4 | Event ingestion worker | backlog | Ticketmaster + Eventbrite APIs → normalized event pool. Depends on Task 1. |
| 5 | Claude curation pipeline | backlog | Raw events + interests → 5 ranked picks with summaries. Depends on Task 4. |
| 6 | Email delivery system | backlog | Resend — Thursday 6pm email with 5 picks + dashboard link. Depends on Tasks 3, 5. |
| 7 | Engagement tracking | backlog | Email opens, dashboard visits, link clicks. Depends on Tasks 2, 3, 6. |
| 8 | Thursday cron scheduling | backlog | GitHub Actions cron (4pm UTC / 6pm CET). Depends on Tasks 5, 6. |
| 9 | Production deployment | backlog | Vercel + Supabase prod + env vars + custom domain. Depends on all. |
| 10 | Initial distribution | backlog | Reddit, Facebook groups, expat WhatsApp, personal network. Ongoing post-launch. |

---

## Status Legend

- `backlog` — Not started
- `in_progress` — Currently working
- `done` — Completed
- `blocked` — Waiting on dependency

---

## Milestones

| Milestone | Target | Criteria |
|-----------|--------|----------|
| 🔑 API keys acquired | Day 0 | Ticketmaster Developer Portal + Eventbrite API access approved. Start before coding — can take 1-3 days. |
| 🏗️ Foundation complete | Day 2 | Tasks 1–3 done. Signup works, dashboard renders with mock data. |
| 🔄 Pipeline working | Day 4 | Tasks 4–5 done. Real Zürich events curated by Claude. |
| 📧 First email sent | Day 5 | Task 6 done. End-to-end: signup → picks → email received. |
| 🚀 Production launch | Day 6 | Task 9 done. Live at bubls.ch with cron running. |
| 📊 First validation data | Week 2 | 4 Thursday emails sent. Open rate, CTR, retention measurable. |
| 🎯 PMF signal | Week 5 | 200 subscribers, >40% open rate, >60% 4-week retention. |

---

## History

| Date | Task | Change | Notes |
|------|------|--------|-------|
| 2026-04-14 | All | Created | Initial spec generation from brain dump |