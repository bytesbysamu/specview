# 🎯 Epic: TennisPartner FindEm

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Finding tennis partners is a persistent problem for recreational players. Unlike team sports where you show up to a scheduled practice, tennis requires actively coordinating with another person of similar skill level and compatible schedule. Most players rely on texting friends, posting in WhatsApp groups, or hoping someone shows up at public courts—all inefficient methods that lead to missed playing opportunities.

The market is underserved. Existing solutions are either too broad (general sports apps), too complex (league management systems), or abandoned side projects. A focused app that does one thing well—connect tennis players for casual matches—has room to grow. Monetization can follow standard paths: premium features for serious players, court booking partnerships, or coaching marketplace integration.

**Value Proposition**: Find a tennis partner near you, at your level, when you want to play.

---

## Scope

### What This Epic Covers

- **Player profiles** – Skill level, location, availability preferences
- **Match discovery** – Find compatible players nearby who want to play
- **Connection flow** – Request, accept, and coordinate matches
- **Basic messaging** – In-app chat to finalize logistics

### What This Epic Does NOT Cover

- ❌ Court booking integration — Future capability after core matching works
- ❌ Tournament/league management — Different product entirely
- ❌ Coaching marketplace — Post-MVP monetization opportunity
- ❌ Social features (feeds, comments) — Focus on utility first

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Player profile system** | None | — | 3 days | High |
| 2 | **Location-based discovery** | 1 | 3 | 4 days | High |
| 3 | **Availability matching** | 1 | 2 | 3 days | High |
| 4 | **Connection requests** | 2, 3 | — | 3 days | High |
| 5 | **In-app messaging** | 4 | — | 2 days | Low |

### Task 1: Player Profile System

Create user profiles with essential tennis-specific attributes: self-assessed skill level (beginner/intermediate/advanced/competitive), playing style preferences (singles/doubles/both), typical availability windows, and home court location. Keep it minimal—just enough info to enable good matches.

### Task 2: Location-Based Discovery

Implement geospatial search to find players within a configurable radius. Display results sorted by distance and compatibility score. Must work efficiently with growing user base—index early, don't query entire database.

### Task 3: Availability Matching

Allow players to set recurring availability (e.g., "weekday evenings", "Saturday mornings") and one-time openings ("free this Thursday 6pm"). Match algorithm should surface players whose availability overlaps with the searcher's open slots.

### Task 4: Connection Requests

Build the request/accept flow for initiating matches. Player A finds Player B, sends request with proposed time/location. Player B accepts, declines, or counter-proposes. Keep state simple: pending → accepted/declined.

### Task 5: In-App Messaging

Basic chat between connected players to finalize details. No need for rich features—text messages suffice. Consider push notifications for new messages but can defer to post-MVP.

---

## Success Criteria

This epic is complete when:

- ✅ Users can create profiles with skill level, location, and availability
- ✅ Users can search for players within 25km filtered by skill and availability
- ✅ Users can send and respond to match requests
- ✅ Two matched users can message each other to coordinate
- ✅ At least 3 real test users successfully arrange a match through the app

---

## Non-Goals

- ❌ Rating/review system — Adds social pressure, assess need after MVP
- ❌ Payment processing — No monetization in v1
- ❌ Multi-sport support — Tennis only, do one thing well
- ❌ Native mobile apps — Web-first, mobile apps after validation

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview